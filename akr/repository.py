"""Repository layer for AKR — direct SQLite + sqlite-vec operations.

Provides :class:`ArtifactRepository` which manages a single SQLite database
containing artifacts, vector embeddings, and an audit trail.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from akr.errors import RepositoryError
from akr.schema import KnowledgeArtifact

# Attempt to import sqlite-vec; defer the error to runtime so the module
# remains importable even when the extension is missing.
try:
    import sqlite_vec

    _SQLITE_VEC_AVAILABLE = True
except ImportError:
    _SQLITE_VEC_AVAILABLE = False


class ArtifactRepository:
    """Direct database operations against a single SQLite database."""

    def __init__(self, db_path: str) -> None:
        """Open or create the SQLite database with sqlite-vec loaded.

        Parameters
        ----------
        db_path:
            File-system path to the SQLite database (or ``":memory:"``).

        Raises
        ------
        RepositoryError
            If sqlite-vec is not installed or the database cannot be opened.
        """
        if not _SQLITE_VEC_AVAILABLE:
            raise RepositoryError(
                "sqlite-vec is not installed. Run: pip install sqlite-vec",
                reason="missing_extension",
            )

        try:
            self._conn = sqlite3.connect(db_path)
            self._conn.enable_load_extension(True)
            sqlite_vec.load(self._conn)
            self._conn.enable_load_extension(False)
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
        except Exception as exc:
            raise RepositoryError(
                f"Failed to open database: {exc}", reason=str(exc)
            ) from exc

        self.initialize_schema()

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def initialize_schema(self) -> None:
        """Create tables if not already present."""
        cur = self._conn.cursor()
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS artifacts (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                tags TEXT NOT NULL,
                source_context TEXT NOT NULL,
                metadata TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_artifacts_updated_at
                ON artifacts(updated_at DESC);

            CREATE TABLE IF NOT EXISTS audit_trail (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                artifact_id TEXT NOT NULL,
                previous_content TEXT NOT NULL,
                changed_at TEXT NOT NULL,
                FOREIGN KEY (artifact_id) REFERENCES artifacts(id) ON DELETE CASCADE
            );
            """
        )
        # vec0 virtual tables cannot be created inside executescript
        cur.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS vec_artifacts USING vec0(
                artifact_id TEXT PRIMARY KEY,
                embedding float[384]
            )
            """
        )
        self._conn.commit()

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def insert_artifact(self, artifact: KnowledgeArtifact, embedding: bytes) -> str:
        """Insert artifact row and vector embedding. Returns artifact ID."""
        try:
            cur = self._conn.cursor()
            cur.execute(
                """
                INSERT INTO artifacts
                    (id, title, content, tags, source_context, metadata, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    artifact.id,
                    artifact.title,
                    artifact.content,
                    json.dumps(artifact.tags),
                    artifact.source_context,
                    json.dumps(artifact.metadata) if artifact.metadata is not None else None,
                    artifact.created_at,
                    artifact.updated_at,
                ),
            )
            cur.execute(
                "INSERT INTO vec_artifacts (artifact_id, embedding) VALUES (?, ?)",
                (artifact.id, embedding),
            )
            self._conn.commit()
            return artifact.id
        except Exception as exc:
            self._conn.rollback()
            raise RepositoryError(
                f"Failed to insert artifact: {exc}", reason=str(exc)
            ) from exc

    def get_artifact(self, artifact_id: str) -> Optional[KnowledgeArtifact]:
        """Retrieve a single artifact by ID. Return ``None`` if not found."""
        row = self._conn.execute(
            "SELECT id, title, content, tags, source_context, metadata, created_at, updated_at "
            "FROM artifacts WHERE id = ?",
            (artifact_id,),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_artifact(row)

    def update_artifact(
        self, artifact_id: str, artifact: KnowledgeArtifact, embedding: bytes
    ) -> bool:
        """Replace artifact content and vector. Returns ``True`` if found."""
        existing = self.get_artifact(artifact_id)
        if existing is None:
            return False

        # Record previous state in audit trail
        self.insert_audit_record(
            artifact_id,
            {
                "title": existing.title,
                "content": existing.content,
                "tags": existing.tags,
                "source_context": existing.source_context,
                "metadata": existing.metadata,
                "created_at": existing.created_at,
                "updated_at": existing.updated_at,
            },
        )

        try:
            self._conn.execute(
                """
                UPDATE artifacts
                SET title=?, content=?, tags=?, source_context=?, metadata=?, updated_at=?
                WHERE id=?
                """,
                (
                    artifact.title,
                    artifact.content,
                    json.dumps(artifact.tags),
                    artifact.source_context,
                    json.dumps(artifact.metadata) if artifact.metadata is not None else None,
                    artifact.updated_at,
                    artifact_id,
                ),
            )
            self._conn.execute(
                "DELETE FROM vec_artifacts WHERE artifact_id = ?", (artifact_id,)
            )
            self._conn.execute(
                "INSERT INTO vec_artifacts (artifact_id, embedding) VALUES (?, ?)",
                (artifact_id, embedding),
            )
            self._conn.commit()
            return True
        except Exception as exc:
            self._conn.rollback()
            raise RepositoryError(
                f"Failed to update artifact: {exc}", reason=str(exc)
            ) from exc

    def delete_artifact(self, artifact_id: str) -> bool:
        """Remove artifact and vector. Returns ``True`` if found."""
        cur = self._conn.execute(
            "DELETE FROM artifacts WHERE id = ?", (artifact_id,)
        )
        if cur.rowcount == 0:
            return False
        self._conn.execute(
            "DELETE FROM vec_artifacts WHERE artifact_id = ?", (artifact_id,)
        )
        self._conn.commit()
        return True

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search_by_vector(
        self, query_embedding: bytes, top_n: int, threshold: float
    ) -> List[Tuple[str, float]]:
        """KNN search using vec0 virtual table.

        Returns ``(artifact_id, distance)`` pairs filtered by *threshold*.
        """
        rows = self._conn.execute(
            """
            SELECT artifact_id, distance
            FROM vec_artifacts
            WHERE embedding MATCH ? AND k = ?
            ORDER BY distance
            """,
            (query_embedding, top_n),
        ).fetchall()
        return [(aid, dist) for aid, dist in rows if dist < threshold]

    # ------------------------------------------------------------------
    # List
    # ------------------------------------------------------------------

    def list_artifacts(
        self,
        tags: Optional[List[str]] = None,
        since: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[KnowledgeArtifact]:
        """List artifacts with optional tag/date filters and pagination."""
        conditions: List[str] = []
        params: list = []

        if tags:
            # AND-filter: every requested tag must be present in the artifact's tags
            placeholders = ",".join("?" for _ in tags)
            conditions.append(
                f"""
                (SELECT COUNT(*) FROM json_each(artifacts.tags)
                 WHERE json_each.value IN ({placeholders})) = ?
                """
            )
            params.extend(tags)
            params.append(len(tags))

        if since:
            conditions.append("updated_at >= ?")
            params.append(since)

        where = ""
        if conditions:
            where = "WHERE " + " AND ".join(conditions)

        query = f"""
            SELECT id, title, content, tags, source_context, metadata, created_at, updated_at
            FROM artifacts
            {where}
            ORDER BY updated_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])

        rows = self._conn.execute(query, params).fetchall()
        return [self._row_to_artifact(row) for row in rows]

    # ------------------------------------------------------------------
    # Audit
    # ------------------------------------------------------------------

    def insert_audit_record(self, artifact_id: str, previous_content: dict) -> None:
        """Record previous version in audit trail."""
        self._conn.execute(
            "INSERT INTO audit_trail (artifact_id, previous_content, changed_at) VALUES (?, ?, ?)",
            (
                artifact_id,
                json.dumps(previous_content),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        self._conn.commit()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_artifact(row: tuple) -> KnowledgeArtifact:
        """Convert a database row to a ``KnowledgeArtifact``."""
        (
            aid,
            title,
            content,
            tags_json,
            source_context,
            metadata_json,
            created_at,
            updated_at,
        ) = row
        return KnowledgeArtifact(
            id=aid,
            title=title,
            content=content,
            tags=json.loads(tags_json),
            source_context=source_context,
            metadata=json.loads(metadata_json) if metadata_json is not None else None,
            created_at=created_at,
            updated_at=updated_at,
        )
