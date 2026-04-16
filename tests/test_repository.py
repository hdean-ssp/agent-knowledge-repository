"""Unit tests for akr.repository – ArtifactRepository."""

from __future__ import annotations

import json
import struct
from datetime import datetime, timezone

import pytest

sqlite_vec = pytest.importorskip("sqlite_vec")

from akr.repository import ArtifactRepository
from akr.schema import KnowledgeArtifact


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fake_embedding(value: float = 0.1) -> bytes:
    """Return a 384-dim float32 embedding packed as raw bytes."""
    return struct.pack("<384f", *([value] * 384))


def _make_artifact(**overrides) -> KnowledgeArtifact:
    """Create a minimal valid KnowledgeArtifact with optional overrides."""
    now = datetime.now(timezone.utc).isoformat()
    defaults = dict(
        id="test-id-1",
        title="Test Title",
        content="Test content body",
        tags=["python", "testing"],
        source_context="tests/test_repository.py",
        created_at=now,
        updated_at=now,
        metadata={"key": "value"},
    )
    defaults.update(overrides)
    return KnowledgeArtifact(**defaults)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def repo():
    """Yield an in-memory ArtifactRepository and close it after the test."""
    r = ArtifactRepository(":memory:")
    yield r
    r.close()


# ---------------------------------------------------------------------------
# Schema initialisation
# ---------------------------------------------------------------------------

class TestSchemaInitialization:
    """initialize_schema creates the expected tables."""

    def test_artifacts_table_exists(self, repo: ArtifactRepository):
        rows = repo._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='artifacts'"
        ).fetchall()
        assert len(rows) == 1

    def test_vec_artifacts_table_exists(self, repo: ArtifactRepository):
        rows = repo._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='vec_artifacts'"
        ).fetchall()
        assert len(rows) == 1

    def test_audit_trail_table_exists(self, repo: ArtifactRepository):
        rows = repo._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='audit_trail'"
        ).fetchall()
        assert len(rows) == 1

    def test_updated_at_index_exists(self, repo: ArtifactRepository):
        rows = repo._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_artifacts_updated_at'"
        ).fetchall()
        assert len(rows) == 1


# ---------------------------------------------------------------------------
# Insert & retrieve round-trip
# ---------------------------------------------------------------------------

class TestInsertAndRetrieve:
    """insert_artifact + get_artifact round-trip."""

    def test_round_trip_fields_match(self, repo: ArtifactRepository):
        art = _make_artifact()
        emb = _fake_embedding()
        returned_id = repo.insert_artifact(art, emb)

        assert returned_id == art.id

        fetched = repo.get_artifact(art.id)
        assert fetched is not None
        assert fetched.id == art.id
        assert fetched.title == art.title
        assert fetched.content == art.content
        assert fetched.tags == art.tags
        assert fetched.source_context == art.source_context
        assert fetched.metadata == art.metadata
        assert fetched.created_at == art.created_at
        assert fetched.updated_at == art.updated_at

    def test_get_nonexistent_returns_none(self, repo: ArtifactRepository):
        assert repo.get_artifact("does-not-exist") is None

    def test_insert_with_null_metadata(self, repo: ArtifactRepository):
        art = _make_artifact(id="null-meta", metadata=None)
        repo.insert_artifact(art, _fake_embedding())
        fetched = repo.get_artifact("null-meta")
        assert fetched is not None
        assert fetched.metadata is None


# ---------------------------------------------------------------------------
# Update & audit trail
# ---------------------------------------------------------------------------

class TestUpdateAndAudit:
    """update_artifact records audit trail and replaces content."""

    def test_update_replaces_content(self, repo: ArtifactRepository):
        original = _make_artifact()
        repo.insert_artifact(original, _fake_embedding(0.1))

        updated = _make_artifact(
            title="Updated Title",
            content="Updated content",
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        result = repo.update_artifact(original.id, updated, _fake_embedding(0.2))
        assert result is True

        fetched = repo.get_artifact(original.id)
        assert fetched is not None
        assert fetched.title == "Updated Title"
        assert fetched.content == "Updated content"

    def test_update_creates_audit_record(self, repo: ArtifactRepository):
        original = _make_artifact()
        repo.insert_artifact(original, _fake_embedding())

        updated = _make_artifact(
            title="New Title",
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        repo.update_artifact(original.id, updated, _fake_embedding(0.5))

        rows = repo._conn.execute(
            "SELECT artifact_id, previous_content, changed_at FROM audit_trail WHERE artifact_id = ?",
            (original.id,),
        ).fetchall()
        assert len(rows) == 1
        aid, prev_json, changed_at = rows[0]
        assert aid == original.id
        prev = json.loads(prev_json)
        assert prev["title"] == original.title
        assert prev["content"] == original.content
        # changed_at should be a valid ISO timestamp
        datetime.fromisoformat(changed_at)

    def test_update_nonexistent_returns_false(self, repo: ArtifactRepository):
        art = _make_artifact(id="ghost")
        assert repo.update_artifact("ghost", art, _fake_embedding()) is False


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

class TestDelete:
    """delete_artifact removes artifact and vector."""

    def test_delete_removes_artifact(self, repo: ArtifactRepository):
        art = _make_artifact()
        repo.insert_artifact(art, _fake_embedding())
        assert repo.delete_artifact(art.id) is True
        assert repo.get_artifact(art.id) is None

    def test_delete_removes_vector(self, repo: ArtifactRepository):
        art = _make_artifact()
        repo.insert_artifact(art, _fake_embedding())
        repo.delete_artifact(art.id)

        vec_rows = repo._conn.execute(
            "SELECT * FROM vec_artifacts WHERE artifact_id = ?", (art.id,)
        ).fetchall()
        assert len(vec_rows) == 0

    def test_delete_nonexistent_returns_false(self, repo: ArtifactRepository):
        assert repo.delete_artifact("nope") is False


# ---------------------------------------------------------------------------
# List with filters
# ---------------------------------------------------------------------------

class TestListArtifacts:
    """list_artifacts with tag and date filters."""

    def _seed(self, repo: ArtifactRepository):
        """Insert three artifacts with different tags and timestamps."""
        a1 = _make_artifact(
            id="a1",
            tags=["python", "testing"],
            updated_at="2024-01-15T00:00:00+00:00",
        )
        a2 = _make_artifact(
            id="a2",
            tags=["python", "docs"],
            updated_at="2024-02-20T00:00:00+00:00",
        )
        a3 = _make_artifact(
            id="a3",
            tags=["rust", "testing"],
            updated_at="2024-03-25T00:00:00+00:00",
        )
        for a in (a1, a2, a3):
            repo.insert_artifact(a, _fake_embedding())

    def test_list_all(self, repo: ArtifactRepository):
        self._seed(repo)
        results = repo.list_artifacts()
        assert len(results) == 3
        # Should be sorted by updated_at DESC
        assert results[0].id == "a3"
        assert results[1].id == "a2"
        assert results[2].id == "a1"

    def test_list_filter_by_single_tag(self, repo: ArtifactRepository):
        self._seed(repo)
        results = repo.list_artifacts(tags=["testing"])
        ids = {r.id for r in results}
        assert ids == {"a1", "a3"}

    def test_list_filter_by_multiple_tags_and_logic(self, repo: ArtifactRepository):
        self._seed(repo)
        results = repo.list_artifacts(tags=["python", "testing"])
        ids = {r.id for r in results}
        assert ids == {"a1"}

    def test_list_filter_by_since(self, repo: ArtifactRepository):
        self._seed(repo)
        results = repo.list_artifacts(since="2024-02-01T00:00:00+00:00")
        ids = {r.id for r in results}
        assert ids == {"a2", "a3"}

    def test_list_limit_and_offset(self, repo: ArtifactRepository):
        self._seed(repo)
        page1 = repo.list_artifacts(limit=2, offset=0)
        assert len(page1) == 2
        page2 = repo.list_artifacts(limit=2, offset=2)
        assert len(page2) == 1

    def test_list_empty_repo(self, repo: ArtifactRepository):
        results = repo.list_artifacts()
        assert results == []


# ---------------------------------------------------------------------------
# Vector search
# ---------------------------------------------------------------------------

class TestSearchByVector:
    """search_by_vector returns results for matching embeddings."""

    def test_search_returns_results(self, repo: ArtifactRepository):
        art = _make_artifact()
        emb = _fake_embedding(1.0)
        repo.insert_artifact(art, emb)

        results = repo.search_by_vector(emb, top_n=5, threshold=2.0)
        assert len(results) >= 1
        ids = [r[0] for r in results]
        assert art.id in ids

    def test_search_respects_threshold(self, repo: ArtifactRepository):
        art = _make_artifact()
        repo.insert_artifact(art, _fake_embedding(1.0))

        # Use a very different embedding and a tight threshold
        query = _fake_embedding(-1.0)
        results = repo.search_by_vector(query, top_n=5, threshold=0.001)
        # With cosine distance, opposite vectors should have distance ~2.0
        # so a threshold of 0.001 should filter them out
        assert len(results) == 0
