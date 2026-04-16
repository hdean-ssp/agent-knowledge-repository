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
from akr.errors import ArtifactNotFoundError
from akr.locking import FileLockManager
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


class KnowledgeService:
    """Orchestrates validation, embedding, locking, and repository operations."""

    def __init__(self, config: AKRConfig) -> None:
        self.config = config
        self.validator = SchemaValidator()
        self.embedding_engine = EmbeddingEngine(config.embedding_model)
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

    def commit(
        self, artifact_data: dict, repo_mode: Optional[str] = None
    ) -> CommitResult:
        """Validate, embed, acquire lock, store. Return ``CommitResult``."""
        artifact = self.validator.validate(artifact_data)
        embedding = self.embedding_engine.embed(artifact.content)

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

        query_embedding = self.embedding_engine.embed(query)
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
        embedding = self.embedding_engine.embed(validated.content)

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
