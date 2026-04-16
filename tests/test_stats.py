"""Unit tests for the repository stats command (Task 9).

Tests: empty repo stats, repo with artifacts, tag distribution,
and CLI JSON output structure.
"""

from __future__ import annotations

import json
import os
import struct
from unittest.mock import MagicMock, patch

import pytest

from akr.config import AKRConfig
from akr.embedding import EmbeddingEngine
from akr.locking import FileLockManager
from akr.repository import ArtifactRepository
from akr.schema import KnowledgeArtifact, SchemaValidator
from akr.service import KnowledgeService

DIMS = 384
_PATCH_CONFIG = "akr.cli.load_config"
_PATCH_SERVICE = "akr.cli.KnowledgeService"


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


# ------------------------------------------------------------------
# Repository-level get_stats()
# ------------------------------------------------------------------

class TestRepositoryStats:
    def test_empty_repo_stats(self, tmp_path):
        """Empty repo returns count=0, last_updated=None, empty tags."""
        db_path = str(tmp_path / "knowledge.db")
        repo = ArtifactRepository(db_path)
        stats = repo.get_stats()
        assert stats["artifact_count"] == 0
        assert stats["last_updated"] is None
        assert stats["tags"] == {}

    def test_repo_with_artifacts(self, tmp_path):
        """Repo with artifacts returns correct count, last_updated, tags."""
        db_path = str(tmp_path / "knowledge.db")
        repo = ArtifactRepository(db_path)

        a1 = KnowledgeArtifact(
            id="id-1", title="First", content="content one",
            tags=["bug", "python"], source_context="file.py",
            created_at="2024-01-01T00:00:00+00:00",
            updated_at="2024-01-02T00:00:00+00:00",
        )
        a2 = KnowledgeArtifact(
            id="id-2", title="Second", content="content two",
            tags=["bug", "architecture"], source_context="main.py",
            created_at="2024-01-01T00:00:00+00:00",
            updated_at="2024-01-03T00:00:00+00:00",
        )
        repo.insert_artifact(a1, _fake_embedding(0.1))
        repo.insert_artifact(a2, _fake_embedding(0.2))

        stats = repo.get_stats()
        assert stats["artifact_count"] == 2
        assert stats["last_updated"] == "2024-01-03T00:00:00+00:00"
        assert stats["tags"]["bug"] == 2
        assert stats["tags"]["python"] == 1
        assert stats["tags"]["architecture"] == 1

    def test_tag_distribution_ordering(self, tmp_path):
        """Tags are ordered by count descending."""
        db_path = str(tmp_path / "knowledge.db")
        repo = ArtifactRepository(db_path)

        for i in range(3):
            a = KnowledgeArtifact(
                id=f"id-{i}", title=f"Art {i}", content=f"content {i}",
                tags=["common", f"unique-{i}"], source_context="ctx",
                created_at="2024-01-01T00:00:00+00:00",
                updated_at="2024-01-01T00:00:00+00:00",
            )
            repo.insert_artifact(a, _fake_embedding(0.1 * i))

        stats = repo.get_stats()
        tag_keys = list(stats["tags"].keys())
        assert tag_keys[0] == "common"
        assert stats["tags"]["common"] == 3


# ------------------------------------------------------------------
# Service-level get_stats()
# ------------------------------------------------------------------

class TestServiceStats:
    def test_empty_repo_stats(self, tmp_path):
        svc = _make_service(tmp_path)
        stats = svc.get_stats()
        assert stats["artifact_count"] == 0
        assert stats["last_updated"] is None
        assert stats["tags"] == {}
        assert stats["repo_mode"] == "user"
        assert stats["db_size_bytes"] >= 0

    def test_stats_with_artifacts(self, tmp_path):
        svc = _make_service(tmp_path)
        svc.commit({
            "title": "Test", "content": "content",
            "tags": ["bug", "python"], "source_context": "ctx",
        })
        svc.commit({
            "title": "Test2", "content": "more content",
            "tags": ["bug"], "source_context": "ctx2",
        })
        stats = svc.get_stats()
        assert stats["artifact_count"] == 2
        assert stats["last_updated"] is not None
        assert stats["tags"]["bug"] == 2
        assert stats["tags"]["python"] == 1
        assert stats["db_size_bytes"] > 0


# ------------------------------------------------------------------
# CLI akr_stats
# ------------------------------------------------------------------

class TestAkrStatsCli:
    def test_stats_json_output(self, monkeypatch, capsys):
        monkeypatch.setattr("sys.argv", ["akr-stats"])
        mock_svc = MagicMock()
        mock_svc.get_stats.return_value = {
            "artifact_count": 5,
            "db_size_bytes": 12345,
            "last_updated": "2024-06-01T00:00:00+00:00",
            "tags": {"bug": 3, "pattern": 2},
            "repo_mode": "user",
        }
        with patch(_PATCH_CONFIG), patch(_PATCH_SERVICE, return_value=mock_svc):
            from akr.cli import akr_stats
            akr_stats()
        out = json.loads(capsys.readouterr().out)
        assert out["artifact_count"] == 5
        assert out["db_size_bytes"] == 12345
        assert out["last_updated"] == "2024-06-01T00:00:00+00:00"
        assert out["tags"] == {"bug": 3, "pattern": 2}
        assert out["repo_mode"] == "user"

    def test_stats_with_repo_flag(self, monkeypatch, capsys):
        monkeypatch.setattr("sys.argv", ["akr-stats", "--repo", "shared"])
        mock_svc = MagicMock()
        mock_svc.get_stats.return_value = {
            "artifact_count": 0,
            "db_size_bytes": 0,
            "last_updated": None,
            "tags": {},
            "repo_mode": "shared",
        }
        with patch(_PATCH_CONFIG), patch(_PATCH_SERVICE, return_value=mock_svc):
            from akr.cli import akr_stats
            akr_stats()
        mock_svc.get_stats.assert_called_once_with("shared")
        out = json.loads(capsys.readouterr().out)
        assert out["repo_mode"] == "shared"

    def test_stats_error_handling(self, monkeypatch, capsys):
        monkeypatch.setattr("sys.argv", ["akr-stats"])
        mock_svc = MagicMock()
        mock_svc.get_stats.side_effect = RuntimeError("db error")
        with patch(_PATCH_CONFIG), patch(_PATCH_SERVICE, return_value=mock_svc):
            from akr.cli import akr_stats
            with pytest.raises(SystemExit) as exc_info:
                akr_stats()
            assert exc_info.value.code == 2
        out = json.loads(capsys.readouterr().out)
        assert out["error"] == "unexpected_error"
