"""Unit tests for akr/utils.py — disk space checking.

Tests: 6.5 — disk_space_check utility and integration with KnowledgeService.commit().
"""

from __future__ import annotations

import os
import struct
from collections import namedtuple
from unittest.mock import MagicMock, patch

import pytest

from akr.config import AKRConfig
from akr.embedding import EmbeddingEngine
from akr.errors import RepositoryError
from akr.locking import FileLockManager
from akr.repository import ArtifactRepository
from akr.utils import LARGE_ARTIFACT_THRESHOLD, MIN_FREE_SPACE, disk_space_check

DIMS = 384


def _fake_embedding(seed: float = 0.1) -> bytes:
    return struct.pack(f"<{DIMS}f", *([seed] * DIMS))


def _make_service(tmp_path):
    """Create a KnowledgeService wired to a temp directory with a mock embedding engine."""
    from akr.schema import SchemaValidator
    from akr.service import KnowledgeService

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


def _large_content() -> str:
    """Return content that exceeds LARGE_ARTIFACT_THRESHOLD."""
    return "x" * (LARGE_ARTIFACT_THRESHOLD + 1)


def _small_content() -> str:
    """Return content that is below LARGE_ARTIFACT_THRESHOLD."""
    return "small content"


def _valid_payload(content: str) -> dict:
    return {
        "title": "Test artifact",
        "content": content,
        "tags": ["test"],
        "source_context": "test_utils.py",
    }


class TestDiskSpaceCheck:
    """Tests for the disk_space_check() utility function."""

    def test_returns_positive_integer_on_real_path(self, tmp_path):
        """disk_space_check() returns a positive integer for a real path."""
        free = disk_space_check(str(tmp_path))
        assert isinstance(free, int)
        assert free > 0


class TestDiskSpaceIntegration:
    """Tests for disk space checking integrated into KnowledgeService.commit()."""

    def test_large_artifact_low_disk_raises_repository_error(self, tmp_path):
        """Committing a large artifact with insufficient disk space raises RepositoryError."""
        svc = _make_service(tmp_path)
        payload = _valid_payload(_large_content())

        DiskUsage = namedtuple("DiskUsage", ["total", "used", "free"])
        low_space = DiskUsage(total=500_000_000, used=490_000_000, free=10_000_000)

        with patch("akr.service.disk_space_check", return_value=low_space.free):
            with pytest.raises(RepositoryError, match="Insufficient disk space"):
                svc.commit(payload)

    def test_small_artifact_skips_disk_check(self, tmp_path):
        """Committing a small artifact does not trigger disk_space_check."""
        svc = _make_service(tmp_path)
        payload = _valid_payload(_small_content())

        with patch("akr.service.disk_space_check") as mock_check:
            result = svc.commit(payload)
            mock_check.assert_not_called()
            assert result.id  # commit succeeded

    def test_large_artifact_sufficient_space_succeeds(self, tmp_path):
        """Committing a large artifact with sufficient disk space succeeds."""
        svc = _make_service(tmp_path)
        payload = _valid_payload(_large_content())

        plenty_of_space = 500_000_000  # 500 MB, well above MIN_FREE_SPACE

        with patch("akr.service.disk_space_check", return_value=plenty_of_space):
            result = svc.commit(payload)
            assert result.id
            assert result.status == "committed"

    def test_low_disk_error_message_contains_mb_values(self, tmp_path):
        """The RepositoryError message includes free and required MB values."""
        svc = _make_service(tmp_path)
        payload = _valid_payload(_large_content())

        free_bytes = 50_000_000  # ~47.7 MB

        with patch("akr.service.disk_space_check", return_value=free_bytes):
            with pytest.raises(RepositoryError) as exc_info:
                svc.commit(payload)
            msg = str(exc_info.value)
            assert "MB free" in msg
            assert "MB required" in msg
