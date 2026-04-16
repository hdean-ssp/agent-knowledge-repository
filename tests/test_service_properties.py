"""Property-based tests for the KnowledgeService layer.

Since fastembed is not installed, we mock EmbeddingEngine to return
deterministic fake embeddings.
"""

from __future__ import annotations

import json
import os
import struct
from datetime import datetime, timezone
from typing import List
from unittest.mock import MagicMock

import hypothesis.strategies as st
import pytest
from hypothesis import given, settings

from akr.config import AKRConfig
from akr.embedding import EmbeddingEngine
from akr.repository import ArtifactRepository
from akr.schema import KnowledgeArtifact
from akr.service import KnowledgeService
from tests.strategies import non_empty_str, valid_tags

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

DIMS = 384


def _fake_embedding(seed: float = 0.1) -> bytes:
    """Return a 384-dim float32 byte vector."""
    return struct.pack(f"<{DIMS}f", *([seed] * DIMS))


def _make_fake_engine() -> EmbeddingEngine:
    """Create a mock EmbeddingEngine that returns deterministic embeddings."""
    engine = MagicMock(spec=EmbeddingEngine)
    _counter = [0]

    def _embed(text: str) -> bytes:
        # Use a simple counter-based seed so different texts get different vectors
        _counter[0] += 1
        seed = (_counter[0] * 0.01) % 1.0
        return _fake_embedding(seed)

    engine.embed = _embed
    engine.embed_batch = lambda texts: [_embed(t) for t in texts]
    engine.dimensions = DIMS
    return engine


def _make_config(tmp_path, repo_mode: str = "user") -> AKRConfig:
    """Build an AKRConfig pointing to tmp directories."""
    user_path = str(tmp_path / "user_repo")
    shared_path = str(tmp_path / "shared_repo")
    return AKRConfig(
        repo_mode=repo_mode,
        shared_repo_path=shared_path,
        user_repo_path=user_path,
        embedding_model="fake-model",
        default_top_n=5,
        similarity_threshold=2.0,  # permissive for testing
    )


def _make_service(tmp_path, repo_mode: str = "user") -> KnowledgeService:
    """Build a KnowledgeService with mocked embedding engine."""
    config = _make_config(tmp_path, repo_mode)
    # Bypass real EmbeddingEngine init by patching __init__
    svc = object.__new__(KnowledgeService)
    svc.config = config
    svc.validator = __import__("akr.schema", fromlist=["SchemaValidator"]).SchemaValidator()
    svc.embedding_engine = _make_fake_engine()
    svc.lock_manager = __import__("akr.locking", fromlist=["FileLockManager"]).FileLockManager()
    svc._repositories = {}

    if config.repo_mode in ("shared", "both"):
        shared_path = os.path.expanduser(config.shared_repo_path)
        os.makedirs(shared_path, exist_ok=True)
        db_path = os.path.join(shared_path, "knowledge.db")
        svc._repositories["shared"] = ArtifactRepository(db_path)

    if config.repo_mode in ("user", "both"):
        user_path = os.path.expanduser(config.user_repo_path)
        os.makedirs(user_path, exist_ok=True)
        db_path = os.path.join(user_path, "knowledge.db")
        svc._repositories["user"] = ArtifactRepository(db_path)

    return svc


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

@st.composite
def valid_payload(draw: st.DrawFn) -> dict:
    """Generate a valid artifact payload dict."""
    return {
        "title": draw(non_empty_str()),
        "content": draw(non_empty_str()),
        "tags": draw(valid_tags()),
        "source_context": draw(non_empty_str()),
        "metadata": draw(
            st.one_of(
                st.none(),
                st.dictionaries(
                    keys=non_empty_str(max_size=30),
                    values=non_empty_str(max_size=30),
                    min_size=0,
                    max_size=3,
                ),
            )
        ),
    }


# ---------------------------------------------------------------------------
# 9.2 — Property 1: Commit round-trip preserves artifact data
# ---------------------------------------------------------------------------


@given(data=valid_payload())
@settings(max_examples=100)
def test_commit_round_trip(data, tmp_path_factory):
    """**Validates: Requirements 1.1, 5.2, 5.3, 6.2**"""
    tmp = tmp_path_factory.mktemp("rt")
    svc = _make_service(tmp)

    result = svc.commit(data)
    assert result.id
    assert result.status == "committed"

    # Retrieve from the write repo
    _name, repo = svc._get_write_repo()
    artifact = repo.get_artifact(result.id)
    assert artifact is not None
    assert artifact.title == data["title"]
    assert artifact.content == data["content"]
    assert artifact.tags == data["tags"]
    assert artifact.source_context == data["source_context"]
    assert artifact.metadata == data.get("metadata")
    # Timestamps populated
    assert artifact.created_at
    assert artifact.updated_at
    # Verify ISO 8601 parseable
    datetime.fromisoformat(artifact.created_at)
    datetime.fromisoformat(artifact.updated_at)

    # Embedding row exists
    rows = repo._conn.execute(
        "SELECT COUNT(*) FROM vec_artifacts WHERE artifact_id = ?",
        (result.id,),
    ).fetchone()
    assert rows[0] == 1


# ---------------------------------------------------------------------------
# 9.3 — Property 3: Committed artifact IDs are unique
# ---------------------------------------------------------------------------


@given(payloads=st.lists(valid_payload(), min_size=2, max_size=8))
@settings(max_examples=50)
def test_committed_ids_unique(payloads, tmp_path_factory):
    """**Validates: Requirements 1.3**"""
    tmp = tmp_path_factory.mktemp("uid")
    svc = _make_service(tmp)

    ids = [svc.commit(p).id for p in payloads]
    assert len(ids) == len(set(ids))
    assert all(isinstance(i, str) and len(i) > 0 for i in ids)


# ---------------------------------------------------------------------------
# 9.4 — Property 4: Fetch results ordered by distance, bounded by top-N
# ---------------------------------------------------------------------------


@given(
    payloads=st.lists(valid_payload(), min_size=1, max_size=6),
    query=non_empty_str(),
    top_n=st.integers(min_value=1, max_value=10),
)
@settings(max_examples=50)
def test_fetch_ordering_and_bounds(payloads, query, top_n, tmp_path_factory):
    """**Validates: Requirements 2.1, 2.4, 6.3**"""
    tmp = tmp_path_factory.mktemp("fetch")
    svc = _make_service(tmp)

    for p in payloads:
        svc.commit(p)

    results = svc.fetch(query, top_n=top_n, threshold=2.0)
    assert len(results) <= top_n
    # Each result has a numeric score
    for r in results:
        assert isinstance(r.score, (int, float))
    # Sorted ascending by distance
    distances = [r.score for r in results]
    assert distances == sorted(distances)


# ---------------------------------------------------------------------------
# 9.5 — Property 5: Update replaces content and embedding
# ---------------------------------------------------------------------------


@given(
    original=valid_payload(),
    updated=valid_payload(),
)
@settings(max_examples=50)
def test_update_replaces_content(original, updated, tmp_path_factory):
    """**Validates: Requirements 3.1**"""
    tmp = tmp_path_factory.mktemp("upd")
    svc = _make_service(tmp)

    commit_result = svc.commit(original)
    aid = commit_result.id

    # Grab original embedding
    _name, repo = svc._get_write_repo()
    orig_emb = repo._conn.execute(
        "SELECT embedding FROM vec_artifacts WHERE artifact_id = ?", (aid,)
    ).fetchone()[0]

    svc.update(aid, updated)

    artifact = repo.get_artifact(aid)
    assert artifact is not None
    assert artifact.title == updated["title"]
    assert artifact.content == updated["content"]
    assert artifact.tags == updated["tags"]
    assert artifact.source_context == updated["source_context"]

    # Embedding should differ (different counter-based seed)
    new_emb = repo._conn.execute(
        "SELECT embedding FROM vec_artifacts WHERE artifact_id = ?", (aid,)
    ).fetchone()[0]
    assert new_emb != orig_emb


# ---------------------------------------------------------------------------
# 9.6 — Property 6: Update records audit trail
# ---------------------------------------------------------------------------


@given(
    original=valid_payload(),
    updated=valid_payload(),
)
@settings(max_examples=50)
def test_update_audit_trail(original, updated, tmp_path_factory):
    """**Validates: Requirements 3.4**"""
    tmp = tmp_path_factory.mktemp("audit")
    svc = _make_service(tmp)

    commit_result = svc.commit(original)
    aid = commit_result.id

    # Grab original artifact state before update
    _name, repo = svc._get_write_repo()
    orig_artifact = repo.get_artifact(aid)

    svc.update(aid, updated)

    # Check audit trail
    row = repo._conn.execute(
        "SELECT previous_content, changed_at FROM audit_trail WHERE artifact_id = ?",
        (aid,),
    ).fetchone()
    assert row is not None
    prev = json.loads(row[0])
    assert prev["title"] == orig_artifact.title
    assert prev["content"] == orig_artifact.content
    # Timestamp is valid
    datetime.fromisoformat(row[1])


# ---------------------------------------------------------------------------
# 9.7 — Property 7: Delete removes artifact and embedding
# ---------------------------------------------------------------------------


@given(data=valid_payload())
@settings(max_examples=50)
def test_delete_removes_artifact_and_embedding(data, tmp_path_factory):
    """**Validates: Requirements 4.1, 4.3**"""
    tmp = tmp_path_factory.mktemp("del")
    svc = _make_service(tmp)

    commit_result = svc.commit(data)
    aid = commit_result.id

    delete_result = svc.delete(aid)
    assert delete_result.id == aid
    assert delete_result.status == "deleted"

    _name, repo = svc._get_write_repo()
    assert repo.get_artifact(aid) is None

    vec_count = repo._conn.execute(
        "SELECT COUNT(*) FROM vec_artifacts WHERE artifact_id = ?", (aid,)
    ).fetchone()[0]
    assert vec_count == 0


# ---------------------------------------------------------------------------
# 9.8 — Property 8: Dual-repo fetch annotates source repository
# ---------------------------------------------------------------------------


@given(
    shared_payload=valid_payload(),
    user_payload=valid_payload(),
    query=non_empty_str(),
)
@settings(max_examples=30)
def test_dual_repo_source_annotation(
    shared_payload, user_payload, query, tmp_path_factory
):
    """**Validates: Requirements 8.4**"""
    tmp = tmp_path_factory.mktemp("dual")
    svc = _make_service(tmp, repo_mode="both")

    # Commit to shared repo
    svc.commit(shared_payload, repo_mode="shared")
    # Commit to user repo
    svc.commit(user_payload, repo_mode="user")

    results = svc.fetch(query, top_n=10, threshold=2.0, repo_mode="both")
    for r in results:
        assert r.source_repo in ("shared", "user")


# ---------------------------------------------------------------------------
# 9.9 — Property 10: List sorted by updated_at DESC, bounded by limit
# ---------------------------------------------------------------------------


@given(
    payloads=st.lists(valid_payload(), min_size=1, max_size=8),
    limit=st.integers(min_value=1, max_value=20),
)
@settings(max_examples=50)
def test_list_ordering_and_limit(payloads, limit, tmp_path_factory):
    """**Validates: Requirements 12.1, 12.4**"""
    tmp = tmp_path_factory.mktemp("lst")
    svc = _make_service(tmp)

    for p in payloads:
        svc.commit(p)

    result = svc.list_artifacts(limit=limit)
    assert len(result.artifacts) <= limit
    # Sorted by updated_at descending
    timestamps = [a.updated_at for a in result.artifacts]
    assert timestamps == sorted(timestamps, reverse=True)


# ---------------------------------------------------------------------------
# 9.10 — Property 11: List tag filter AND logic
# ---------------------------------------------------------------------------


@given(
    payloads=st.lists(valid_payload(), min_size=1, max_size=6),
    filter_tag=non_empty_str(max_size=50),
)
@settings(max_examples=50)
def test_list_tag_filter(payloads, filter_tag, tmp_path_factory):
    """**Validates: Requirements 12.2**"""
    tmp = tmp_path_factory.mktemp("tagf")
    svc = _make_service(tmp)

    for p in payloads:
        svc.commit(p)

    result = svc.list_artifacts(tags=[filter_tag])
    for a in result.artifacts:
        assert filter_tag in a.tags


# ---------------------------------------------------------------------------
# 9.11 — Property 12: List date filter
# ---------------------------------------------------------------------------


@given(data=valid_payload())
@settings(max_examples=50)
def test_list_date_filter(data, tmp_path_factory):
    """**Validates: Requirements 12.3**"""
    tmp = tmp_path_factory.mktemp("datef")
    svc = _make_service(tmp)

    svc.commit(data)

    # Use a date in the past — all artifacts should be returned
    since = "2000-01-01T00:00:00+00:00"
    result = svc.list_artifacts(since=since)
    for a in result.artifacts:
        assert a.updated_at >= since

    # Use a date in the far future — nothing should be returned
    future = "2999-01-01T00:00:00+00:00"
    result_future = svc.list_artifacts(since=future)
    assert len(result_future.artifacts) == 0
