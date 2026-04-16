"""Service layer orchestrating business logic for AKR.

Coordinates validation, embedding generation, repository operations,
and file locking across shared and user repositories.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from akr.config import AKRConfig
from akr.embedding import EmbeddingEngine
from akr.errors import ArtifactNotFoundError, RepositoryError, ValidationError
from akr.locking import FileLockManager
from akr.serialization import _artifact_to_dict
from akr.utils import LARGE_ARTIFACT_THRESHOLD, MIN_FREE_SPACE, disk_space_check
from akr.repository import ArtifactRepository
from akr.schema import KnowledgeArtifact, SchemaValidator


@dataclass
class CommitResult:
    """Result of a successful commit operation."""

    id: str
    status: str = "committed"


@dataclass
class FetchResult:
    """A single search result with source annotation."""

    artifact: KnowledgeArtifact
    score: float
    source_repo: str  # "shared" or "user"


@dataclass
class UpdateResult:
    """Result of a successful update operation."""

    id: str
    status: str = "updated"


@dataclass
class DeleteResult:
    """Result of a successful delete operation."""

    id: str
    status: str = "deleted"


@dataclass
class ListResult:
    """Result of a list operation."""

    artifacts: List[KnowledgeArtifact] = field(default_factory=list)
    total: int = 0


@dataclass
class ImportResult:
    """Result of an import operation."""

    imported: int = 0
    skipped: int = 0
    updated: int = 0


class KnowledgeService:
    """Orchestrates validation, embedding, locking, and repository operations."""

    def __init__(self, config: AKRConfig) -> None:
        self.config = config
        self.validator = SchemaValidator()
        self._embedding_engine: Optional[EmbeddingEngine] = None
        self.lock_manager = FileLockManager()
        self._repositories: Dict[str, ArtifactRepository] = {}

        # Initialize repositories based on config.repo_mode
        if config.repo_mode in ("shared", "both"):
            shared_path = os.path.expanduser(config.shared_repo_path)
            os.makedirs(shared_path, exist_ok=True)
            db_path = os.path.join(shared_path, "knowledge.db")
            self._repositories["shared"] = ArtifactRepository(db_path)

        if config.repo_mode in ("user", "both"):
            user_path = os.path.expanduser(config.user_repo_path)
            os.makedirs(user_path, exist_ok=True)
            db_path = os.path.join(user_path, "knowledge.db")
            self._repositories["user"] = ArtifactRepository(db_path)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_embedding_engine(self) -> EmbeddingEngine:
        """Lazy-initialize and return the embedding engine."""
        if self._embedding_engine is None:
            self._embedding_engine = EmbeddingEngine()
        return self._embedding_engine

    def _get_repos(
        self, repo_mode: Optional[str] = None
    ) -> List[Tuple[str, ArtifactRepository]]:
        """Return list of ``(repo_name, repo)`` based on *repo_mode*.

        Falls back to the config-level ``repo_mode`` when *repo_mode* is
        ``None``.
        """
        mode = repo_mode or self.config.repo_mode
        if mode == "both":
            return list(self._repositories.items())
        if mode in self._repositories:
            return [(mode, self._repositories[mode])]
        # Fallback: return all available repos
        return list(self._repositories.items())

    def _get_write_repo(
        self, repo_mode: Optional[str] = None
    ) -> Tuple[str, ArtifactRepository]:
        """Return the single repo to write to.

        For ``"both"`` mode, writes go to the *user* repo by default.
        """
        mode = repo_mode or self.config.repo_mode
        if mode == "both":
            # Prefer user repo for writes
            if "user" in self._repositories:
                return ("user", self._repositories["user"])
            # Fallback to shared if user not available
            return next(iter(self._repositories.items()))
        if mode in self._repositories:
            return (mode, self._repositories[mode])
        # Fallback
        return next(iter(self._repositories.items()))

    def _db_path_for_repo(self, repo_name: str) -> str:
        """Derive the database file path for a named repository."""
        if repo_name == "shared":
            base = os.path.expanduser(self.config.shared_repo_path)
        else:
            base = os.path.expanduser(self.config.user_repo_path)
        return os.path.join(base, "knowledge.db")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check_duplicates(
        self,
        content: str,
        repo_mode: Optional[str] = None,
        threshold: float = 0.3,
    ) -> List[Dict[str, object]]:
        """Check for existing artifacts similar to *content*.

        Embeds *content*, searches repos with a tight cosine-distance
        *threshold*, and returns a list of similar artifact summaries::

            [{"id": "...", "title": "...", "score": 0.15}, ...]

        An empty list means no duplicates were found.
        """
        query_embedding = self._get_embedding_engine().embed(content)
        repos = self._get_repos(repo_mode)

        similar: List[Dict[str, object]] = []
        for repo_name, repo in repos:
            hits = repo.search_by_vector(query_embedding, 5, threshold)
            for artifact_id, distance in hits:
                artifact = repo.get_artifact(artifact_id)
                if artifact is not None:
                    similar.append(
                        {"id": artifact.id, "title": artifact.title, "score": distance}
                    )

        # Sort by distance ascending (most similar first)
        similar.sort(key=lambda r: r["score"])  # type: ignore[arg-type]
        return similar

    def commit(
        self, artifact_data: dict, repo_mode: Optional[str] = None
    ) -> CommitResult:
        """Validate, embed, acquire lock, store. Return ``CommitResult``."""
        artifact = self.validator.validate(artifact_data)

        # Disk space check for large artifacts
        if len(artifact.content) > LARGE_ARTIFACT_THRESHOLD:
            repo_name_check, _ = self._get_write_repo(repo_mode)
            repo_path = os.path.dirname(self._db_path_for_repo(repo_name_check))
            free = disk_space_check(repo_path)
            if free < MIN_FREE_SPACE:
                free_mb = free / (1024 * 1024)
                min_mb = MIN_FREE_SPACE / (1024 * 1024)
                raise RepositoryError(
                    f"Insufficient disk space: {free_mb:.1f}MB free, "
                    f"{min_mb:.1f}MB required"
                )

        embedding = self._get_embedding_engine().embed(artifact.content)

        repo_name, repo = self._get_write_repo(repo_mode)
        db_path = self._db_path_for_repo(repo_name)

        with self.lock_manager.acquire_write_lock(db_path):
            repo.insert_artifact(artifact, embedding)

        return CommitResult(id=artifact.id)

    def fetch(
        self,
        query: str,
        top_n: Optional[int] = None,
        threshold: Optional[float] = None,
        repo_mode: Optional[str] = None,
    ) -> List[FetchResult]:
        """Embed query, search repos, merge if ``"both"``, sort by distance."""
        effective_top_n = top_n if top_n is not None else self.config.default_top_n
        effective_threshold = (
            threshold if threshold is not None else self.config.similarity_threshold
        )

        query_embedding = self._get_embedding_engine().embed(query)
        repos = self._get_repos(repo_mode)

        results: List[FetchResult] = []
        for repo_name, repo in repos:
            hits = repo.search_by_vector(
                query_embedding, effective_top_n, effective_threshold
            )
            for artifact_id, distance in hits:
                artifact = repo.get_artifact(artifact_id)
                if artifact is not None:
                    results.append(
                        FetchResult(
                            artifact=artifact,
                            score=distance,
                            source_repo=repo_name,
                        )
                    )

        # Sort by distance ascending (most similar first)
        results.sort(key=lambda r: r.score)

        # Trim to top_n after merging
        return results[:effective_top_n]

    def update(
        self,
        artifact_id: str,
        artifact_data: dict,
        repo_mode: Optional[str] = None,
    ) -> UpdateResult:
        """Validate, re-embed, acquire lock, update.

        Raises ``ArtifactNotFoundError`` if not found in any repo.
        """
        validated = self.validator.validate(artifact_data)
        # Preserve the original ID and created_at
        validated.id = artifact_id
        embedding = self._get_embedding_engine().embed(validated.content)

        repos = self._get_repos(repo_mode)
        for repo_name, repo in repos:
            existing = repo.get_artifact(artifact_id)
            if existing is not None:
                # Preserve original created_at
                validated.created_at = existing.created_at
                db_path = self._db_path_for_repo(repo_name)
                with self.lock_manager.acquire_write_lock(db_path):
                    repo.update_artifact(artifact_id, validated, embedding)
                return UpdateResult(id=artifact_id)

        raise ArtifactNotFoundError(artifact_id)

    def delete(
        self, artifact_id: str, repo_mode: Optional[str] = None
    ) -> DeleteResult:
        """Acquire lock, delete.

        Raises ``ArtifactNotFoundError`` if not found in any repo.
        """
        repos = self._get_repos(repo_mode)
        for repo_name, repo in repos:
            db_path = self._db_path_for_repo(repo_name)
            with self.lock_manager.acquire_write_lock(db_path):
                deleted = repo.delete_artifact(artifact_id)
            if deleted:
                return DeleteResult(id=artifact_id)

        raise ArtifactNotFoundError(artifact_id)

    def list_artifacts(
        self,
        tags: Optional[List[str]] = None,
        since: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
        repo_mode: Optional[str] = None,
    ) -> ListResult:
        """List from repos with filters."""
        repos = self._get_repos(repo_mode)

        all_artifacts: List[KnowledgeArtifact] = []
        for _repo_name, repo in repos:
            all_artifacts.extend(
                repo.list_artifacts(
                    tags=tags, since=since, limit=limit, offset=offset
                )
            )

        # Sort by updated_at descending across all repos
        all_artifacts.sort(key=lambda a: a.updated_at, reverse=True)

        # Apply limit after merge
        trimmed = all_artifacts[:limit]
        return ListResult(artifacts=trimmed, total=len(trimmed))

    def get_audit_trail(
        self,
        artifact_id: str,
        repo_mode: Optional[str] = None,
    ) -> List[Dict]:
        """Return audit trail records for *artifact_id* across repos.

        Records are sorted by ``changed_at`` descending (newest first).
        """
        repos = self._get_repos(repo_mode)
        all_records: List[Dict] = []
        for _repo_name, repo in repos:
            all_records.extend(repo.get_audit_trail(artifact_id))
        # Sort combined results newest-first
        all_records.sort(key=lambda r: r["changed_at"], reverse=True)
        return all_records

    def export_artifacts(
        self, repo_mode: Optional[str] = None
    ) -> List[Dict]:
        """Export all artifacts as a list of dicts (no embeddings).

        Calls ``list_artifacts`` with a high limit and serializes each
        artifact via ``_artifact_to_dict``.
        """
        result = self.list_artifacts(limit=100000, repo_mode=repo_mode)
        return [_artifact_to_dict(a) for a in result.artifacts]

    def import_artifacts(
        self,
        artifacts_data: List[Dict],
        strategy: str = "skip",
        repo_mode: Optional[str] = None,
    ) -> ImportResult:
        """Import artifacts from a list of dicts.

        For each artifact dict the method:
        1. Validates required fields (title, content, tags, source_context)
           while preserving existing id, created_at, updated_at from the data.
        2. Generates a fresh embedding.
        3. Checks whether the ID already exists in the target repo.

        Strategies:
        - ``skip``: if ID exists, skip it.
        - ``update``: if ID exists and imported ``updated_at`` is newer,
          overwrite; otherwise skip.

        Returns an ``ImportResult`` with counts.
        """
        counts = ImportResult()
        repo_name, repo = self._get_write_repo(repo_mode)
        db_path = self._db_path_for_repo(repo_name)

        for item in artifacts_data:
            artifact = self._validate_import(item)
            embedding = self._get_embedding_engine().embed(artifact.content)
            existing = repo.get_artifact(artifact.id)

            if existing is None:
                with self.lock_manager.acquire_write_lock(db_path):
                    repo.insert_artifact(artifact, embedding)
                counts.imported += 1
            elif strategy == "skip":
                counts.skipped += 1
            elif strategy == "update":
                if artifact.updated_at > existing.updated_at:
                    with self.lock_manager.acquire_write_lock(db_path):
                        repo.update_artifact(artifact.id, artifact, embedding)
                    counts.updated += 1
                else:
                    counts.skipped += 1

        return counts

    def get_stats(self, repo_mode: Optional[str] = None) -> Dict:
        """Return aggregated repository statistics.

        For each configured repo, queries artifact count, last_updated,
        and tag distribution, then adds the DB file size.  When multiple
        repos are active the counts are summed and tag distributions
        merged.
        """
        repos = self._get_repos(repo_mode)
        total_count = 0
        total_db_size = 0
        last_updated: Optional[str] = None
        merged_tags: Dict[str, int] = {}

        for repo_name, repo in repos:
            stats = repo.get_stats()
            total_count += stats["artifact_count"]

            repo_last = stats["last_updated"]
            if repo_last is not None:
                if last_updated is None or repo_last > last_updated:
                    last_updated = repo_last

            for tag, count in stats["tags"].items():
                merged_tags[tag] = merged_tags.get(tag, 0) + count

            db_path = self._db_path_for_repo(repo_name)
            try:
                total_db_size += os.path.getsize(db_path)
            except OSError:
                pass

        # Sort tags by count descending
        sorted_tags = dict(
            sorted(merged_tags.items(), key=lambda kv: kv[1], reverse=True)
        )

        effective_mode = repo_mode or self.config.repo_mode
        return {
            "artifact_count": total_count,
            "db_size_bytes": total_db_size,
            "last_updated": last_updated,
            "tags": sorted_tags,
            "repo_mode": effective_mode,
        }

    # ------------------------------------------------------------------
    # Import validation helper
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_import(data: Dict) -> KnowledgeArtifact:
        """Validate an imported artifact dict, preserving id/timestamps.

        Performs basic field checks without auto-generating id or timestamps.
        Raises ``ValidationError`` on invalid data.
        """
        errors: List[Dict[str, str]] = []

        for field_name in ("id", "title", "content", "source_context"):
            value = data.get(field_name)
            if value is None:
                errors.append({"field": field_name, "message": f"'{field_name}' is required"})
            elif not isinstance(value, str) or not value.strip():
                errors.append({"field": field_name, "message": f"'{field_name}' must be a non-empty string"})

        tags = data.get("tags")
        if tags is None:
            errors.append({"field": "tags", "message": "'tags' is required"})
        elif not isinstance(tags, list) or len(tags) == 0:
            errors.append({"field": "tags", "message": "'tags' must be a non-empty list"})

        for ts_field in ("created_at", "updated_at"):
            value = data.get(ts_field)
            if value is None:
                errors.append({"field": ts_field, "message": f"'{ts_field}' is required"})
            elif not isinstance(value, str) or not value.strip():
                errors.append({"field": ts_field, "message": f"'{ts_field}' must be a non-empty string"})

        if errors:
            raise ValidationError("Import validation failed", details=errors)

        metadata = data.get("metadata")
        return KnowledgeArtifact(
            id=data["id"],
            title=data["title"],
            content=data["content"],
            tags=list(data["tags"]),
            source_context=data["source_context"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            metadata=dict(metadata) if metadata is not None else None,
        )
