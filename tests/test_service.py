"""Unit tests for KnowledgeService error handling.

Tests: 9.12 — update/delete non-existent, invalid commit, empty fetch.
"""

from __future__ import annotations

import os
import struct
from unittest.mock import MagicMock, patch

import pytest

from akr.config import AKRConfig
from akr.embedding import EmbeddingEngine
from akr.errors import ArtifactNotFoundError, ValidationError
from akr.locking import FileLockManager
from akr.repository import ArtifactRepository
from akr.schema import SchemaValidator
from akr.service import KnowledgeService

DIMS = 384


def _fake_embedding(seed: float = 0.1) -> bytes:
    return struct.pack(f"<{DIMS}f", *([seed] * DIMS))


def _make_service(tmp_path) -> KnowledgeService:
    config = AKRConfig(
        repo_mode="user",
        shared_repo_path=str(tmp_path / "shared"),
        user_repo_path=str(tmp_path / "user"),
        default_top_n=5,
        similarity_threshold=2.0,
    )
    svc = object.__new__(KnowledgeService)
    svc.config = config
    svc.validator = SchemaValidator()

    engine = MagicMock(spec=EmbeddingEngine)
    _counter = [0]

    def _embed(text: str) -> bytes:
        _counter[0] += 1
        return _fake_embedding((_counter[0] * 0.01) % 1.0)

    engine.embed = _embed
    engine.dimensions = DIMS
    svc._embedding_engine = engine
    svc.lock_manager = FileLockManager()
    svc._repositories = {}

    user_path = os.path.expanduser(config.user_repo_path)
    os.makedirs(user_path, exist_ok=True)
    db_path = os.path.join(user_path, "knowledge.db")
    svc._repositories["user"] = ArtifactRepository(db_path)

    return svc


class TestServiceErrorHandling:
    """9.12 — Unit tests for service error handling."""

    def test_update_nonexistent_raises(self, tmp_path):
        """Update with non-existent ID raises ArtifactNotFoundError."""
        svc = _make_service(tmp_path)
        payload = {
            "title": "t",
            "content": "c",
            "tags": ["x"],
            "source_context": "sc",
        }
        with pytest.raises(ArtifactNotFoundError):
            svc.update("nonexistent-id", payload)

    def test_delete_nonexistent_raises(self, tmp_path):
        """Delete with non-existent ID raises ArtifactNotFoundError."""
        svc = _make_service(tmp_path)
        with pytest.raises(ArtifactNotFoundError):
            svc.delete("nonexistent-id")

    def test_commit_invalid_payload_raises(self, tmp_path):
        """Commit with invalid payload raises ValidationError."""
        svc = _make_service(tmp_path)
        with pytest.raises(ValidationError):
            svc.commit({"title": ""})  # missing required fields

    def test_fetch_empty_repo_returns_empty(self, tmp_path):
        """Fetch on empty repository returns empty list."""
        svc = _make_service(tmp_path)
        results = svc.fetch("anything", top_n=5, threshold=2.0)
        assert results == []


class TestLazyModelLoading:
    """Verify list and delete operations don't trigger embedding model loading."""

    def test_list_artifacts_does_not_load_model(self, tmp_path):
        """list_artifacts() should never instantiate EmbeddingEngine."""
        config = AKRConfig(
            repo_mode="user",
            shared_repo_path=str(tmp_path / "shared"),
            user_repo_path=str(tmp_path / "user"),
            default_top_n=5,
            similarity_threshold=2.0,
        )
        with patch("akr.service.EmbeddingEngine") as MockEngine:
            svc = KnowledgeService(config)
            svc.list_artifacts()
            MockEngine.assert_not_called()

    def test_delete_does_not_load_model(self, tmp_path):
        """delete() should never instantiate EmbeddingEngine."""
        config = AKRConfig(
            repo_mode="user",
            shared_repo_path=str(tmp_path / "shared"),
            user_repo_path=str(tmp_path / "user"),
            default_top_n=5,
            similarity_threshold=2.0,
        )
        with patch("akr.service.EmbeddingEngine") as MockEngine:
            svc = KnowledgeService(config)
            with pytest.raises(ArtifactNotFoundError):
                svc.delete("nonexistent-id")
            MockEngine.assert_not_called()
