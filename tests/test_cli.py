"""Unit tests for CLI entry points.

Mocks KnowledgeService and load_config since fastembed is not installed.
Tests argument parsing, JSON output structure, and error handling.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from akr.errors import ArtifactNotFoundError, ValidationError
from akr.schema import KnowledgeArtifact
from akr.service import CommitResult, DeleteResult, FetchResult, ListResult, UpdateResult


_MOCK_ARTIFACT = KnowledgeArtifact(
    id="abc-123",
    title="Test",
    content="Some content",
    tags=["test"],
    source_context="ctx",
    created_at="2024-01-01T00:00:00+00:00",
    updated_at="2024-01-01T00:00:00+00:00",
    metadata=None,
)

_PATCH_CONFIG = "akr.cli.load_config"
_PATCH_SERVICE = "akr.cli.KnowledgeService"


# ------------------------------------------------------------------
# akr_commit
# ------------------------------------------------------------------

class TestAkrCommit:
    def test_commit_json_success(self, monkeypatch, capsys):
        monkeypatch.setattr(
            "sys.argv",
            ["akr-commit", "--json", '{"title":"t","content":"c","tags":["x"],"source_context":"sc"}'],
        )
        mock_svc = MagicMock()
        mock_svc.commit.return_value = CommitResult(id="uuid-1")
        with patch(_PATCH_CONFIG), patch(_PATCH_SERVICE, return_value=mock_svc):
            from akr.cli import akr_commit
            akr_commit()
        out = json.loads(capsys.readouterr().out)
        assert out == {"id": "uuid-1", "status": "committed"}

    def test_commit_file_success(self, monkeypatch, capsys, tmp_path):
        payload_file = tmp_path / "artifact.json"
        payload_file.write_text('{"title":"t","content":"c","tags":["x"],"source_context":"sc"}')
        monkeypatch.setattr("sys.argv", ["akr-commit", "--file", str(payload_file)])
        mock_svc = MagicMock()
        mock_svc.commit.return_value = CommitResult(id="uuid-2")
        with patch(_PATCH_CONFIG), patch(_PATCH_SERVICE, return_value=mock_svc):
            from akr.cli import akr_commit
            akr_commit()
        out = json.loads(capsys.readouterr().out)
        assert out["status"] == "committed"

    def test_commit_validation_error(self, monkeypatch, capsys):
        monkeypatch.setattr("sys.argv", ["akr-commit", "--json", '{"title":""}'])
        mock_svc = MagicMock()
        mock_svc.commit.side_effect = ValidationError("bad", details=[{"field": "title", "message": "empty"}])
        with patch(_PATCH_CONFIG), patch(_PATCH_SERVICE, return_value=mock_svc):
            from akr.cli import akr_commit
            with pytest.raises(SystemExit) as exc_info:
                akr_commit()
            assert exc_info.value.code == 1
        out = json.loads(capsys.readouterr().out)
        assert out["error"] == "validation_error"

    def test_commit_unexpected_error(self, monkeypatch, capsys):
        monkeypatch.setattr("sys.argv", ["akr-commit", "--json", '{}'])
        mock_svc = MagicMock()
        mock_svc.commit.side_effect = RuntimeError("boom")
        with patch(_PATCH_CONFIG), patch(_PATCH_SERVICE, return_value=mock_svc):
            from akr.cli import akr_commit
            with pytest.raises(SystemExit) as exc_info:
                akr_commit()
            assert exc_info.value.code == 2
        out = json.loads(capsys.readouterr().out)
        assert out["error"] == "unexpected_error"


# ------------------------------------------------------------------
# akr_fetch
# ------------------------------------------------------------------

class TestAkrFetch:
    def test_fetch_with_results(self, monkeypatch, capsys):
        monkeypatch.setattr("sys.argv", ["akr-fetch", "--query", "test query"])
        mock_svc = MagicMock()
        mock_svc.fetch.return_value = [
            FetchResult(artifact=_MOCK_ARTIFACT, score=0.15, source_repo="user"),
        ]
        with patch(_PATCH_CONFIG), patch(_PATCH_SERVICE, return_value=mock_svc):
            from akr.cli import akr_fetch
            akr_fetch()
        out = json.loads(capsys.readouterr().out)
        assert isinstance(out, list)
        assert len(out) == 1
        assert out[0]["score"] == 0.15
        assert out[0]["source_repo"] == "user"
        assert out[0]["artifact"]["id"] == "abc-123"

    def test_fetch_empty_results(self, monkeypatch, capsys):
        monkeypatch.setattr("sys.argv", ["akr-fetch", "--query", "nothing"])
        mock_svc = MagicMock()
        mock_svc.fetch.return_value = []
        with patch(_PATCH_CONFIG), patch(_PATCH_SERVICE, return_value=mock_svc):
            from akr.cli import akr_fetch
            akr_fetch()
        out = json.loads(capsys.readouterr().out)
        assert out["results"] == []
        assert "No relevant knowledge found" in out["message"]

    def test_fetch_with_options(self, monkeypatch, capsys):
        monkeypatch.setattr(
            "sys.argv",
            ["akr-fetch", "--query", "q", "--top-n", "3", "--threshold", "0.5", "--repo", "shared"],
        )
        mock_svc = MagicMock()
        mock_svc.fetch.return_value = []
        with patch(_PATCH_CONFIG), patch(_PATCH_SERVICE, return_value=mock_svc):
            from akr.cli import akr_fetch
            akr_fetch()
        mock_svc.fetch.assert_called_once_with("q", 3, 0.5, "shared")

    def test_fetch_akr_error(self, monkeypatch, capsys):
        monkeypatch.setattr("sys.argv", ["akr-fetch", "--query", "q"])
        mock_svc = MagicMock()
        mock_svc.fetch.side_effect = ArtifactNotFoundError("x")
        with patch(_PATCH_CONFIG), patch(_PATCH_SERVICE, return_value=mock_svc):
            from akr.cli import akr_fetch
            with pytest.raises(SystemExit) as exc_info:
                akr_fetch()
            assert exc_info.value.code == 1


# ------------------------------------------------------------------
# akr_update
# ------------------------------------------------------------------

class TestAkrUpdate:
    def test_update_success(self, monkeypatch, capsys):
        monkeypatch.setattr(
            "sys.argv",
            ["akr-update", "--id", "uuid-1", "--json", '{"title":"t","content":"c","tags":["x"],"source_context":"sc"}'],
        )
        mock_svc = MagicMock()
        mock_svc.update.return_value = UpdateResult(id="uuid-1")
        with patch(_PATCH_CONFIG), patch(_PATCH_SERVICE, return_value=mock_svc):
            from akr.cli import akr_update
            akr_update()
        out = json.loads(capsys.readouterr().out)
        assert out == {"id": "uuid-1", "status": "updated"}

    def test_update_not_found(self, monkeypatch, capsys):
        monkeypatch.setattr(
            "sys.argv",
            ["akr-update", "--id", "missing", "--json", '{"title":"t","content":"c","tags":["x"],"source_context":"sc"}'],
        )
        mock_svc = MagicMock()
        mock_svc.update.side_effect = ArtifactNotFoundError("missing")
        with patch(_PATCH_CONFIG), patch(_PATCH_SERVICE, return_value=mock_svc):
            from akr.cli import akr_update
            with pytest.raises(SystemExit) as exc_info:
                akr_update()
            assert exc_info.value.code == 1
        out = json.loads(capsys.readouterr().out)
        assert out["error"] == "not_found"


# ------------------------------------------------------------------
# akr_delete
# ------------------------------------------------------------------

class TestAkrDelete:
    def test_delete_success(self, monkeypatch, capsys):
        monkeypatch.setattr("sys.argv", ["akr-delete", "--id", "uuid-1"])
        mock_svc = MagicMock()
        mock_svc.delete.return_value = DeleteResult(id="uuid-1")
        with patch(_PATCH_CONFIG), patch(_PATCH_SERVICE, return_value=mock_svc):
            from akr.cli import akr_delete
            akr_delete()
        out = json.loads(capsys.readouterr().out)
        assert out == {"id": "uuid-1", "status": "deleted"}

    def test_delete_not_found(self, monkeypatch, capsys):
        monkeypatch.setattr("sys.argv", ["akr-delete", "--id", "missing"])
        mock_svc = MagicMock()
        mock_svc.delete.side_effect = ArtifactNotFoundError("missing")
        with patch(_PATCH_CONFIG), patch(_PATCH_SERVICE, return_value=mock_svc):
            from akr.cli import akr_delete
            with pytest.raises(SystemExit) as exc_info:
                akr_delete()
            assert exc_info.value.code == 1
        out = json.loads(capsys.readouterr().out)
        assert out["error"] == "not_found"

    def test_delete_unexpected_error(self, monkeypatch, capsys):
        monkeypatch.setattr("sys.argv", ["akr-delete", "--id", "x"])
        mock_svc = MagicMock()
        mock_svc.delete.side_effect = RuntimeError("disk fail")
        with patch(_PATCH_CONFIG), patch(_PATCH_SERVICE, return_value=mock_svc):
            from akr.cli import akr_delete
            with pytest.raises(SystemExit) as exc_info:
                akr_delete()
            assert exc_info.value.code == 2
        out = json.loads(capsys.readouterr().out)
        assert out["error"] == "unexpected_error"
        assert "disk fail" in out["message"]


# ------------------------------------------------------------------
# akr_list
# ------------------------------------------------------------------

class TestAkrList:
    def test_list_default(self, monkeypatch, capsys):
        monkeypatch.setattr("sys.argv", ["akr-list"])
        mock_svc = MagicMock()
        mock_svc.list_artifacts.return_value = ListResult(artifacts=[_MOCK_ARTIFACT], total=1)
        with patch(_PATCH_CONFIG), patch(_PATCH_SERVICE, return_value=mock_svc):
            from akr.cli import akr_list
            akr_list()
        out = json.loads(capsys.readouterr().out)
        assert isinstance(out, list)
        assert len(out) == 1
        assert out[0]["id"] == "abc-123"

    def test_list_with_tags(self, monkeypatch, capsys):
        monkeypatch.setattr("sys.argv", ["akr-list", "--tags", "bug,arch"])
        mock_svc = MagicMock()
        mock_svc.list_artifacts.return_value = ListResult(artifacts=[], total=0)
        with patch(_PATCH_CONFIG), patch(_PATCH_SERVICE, return_value=mock_svc):
            from akr.cli import akr_list
            akr_list()
        mock_svc.list_artifacts.assert_called_once_with(["bug", "arch"], None, 20, 0, None)

    def test_list_with_all_options(self, monkeypatch, capsys):
        monkeypatch.setattr(
            "sys.argv",
            ["akr-list", "--tags", "x", "--since", "2024-01-01", "--limit", "10", "--offset", "5", "--repo", "user"],
        )
        mock_svc = MagicMock()
        mock_svc.list_artifacts.return_value = ListResult(artifacts=[], total=0)
        with patch(_PATCH_CONFIG), patch(_PATCH_SERVICE, return_value=mock_svc):
            from akr.cli import akr_list
            akr_list()
        mock_svc.list_artifacts.assert_called_once_with(["x"], "2024-01-01", 10, 5, "user")

    def test_list_akr_error(self, monkeypatch, capsys):
        monkeypatch.setattr("sys.argv", ["akr-list"])
        mock_svc = MagicMock()
        mock_svc.list_artifacts.side_effect = ValidationError("bad config")
        with patch(_PATCH_CONFIG), patch(_PATCH_SERVICE, return_value=mock_svc):
            from akr.cli import akr_list
            with pytest.raises(SystemExit) as exc_info:
                akr_list()
            assert exc_info.value.code == 1


# ------------------------------------------------------------------
# akr_commit — duplicate detection
# ------------------------------------------------------------------

class TestAkrCommitDuplicateDetection:
    """Tests for --check-duplicates and --force flags on akr-commit."""

    def test_check_duplicates_no_duplicates_commits(self, monkeypatch, capsys):
        """--check-duplicates with no duplicates found → commits normally."""
        monkeypatch.setattr(
            "sys.argv",
            ["akr-commit", "--json", '{"title":"t","content":"c","tags":["x"],"source_context":"sc"}', "--check-duplicates"],
        )
        mock_svc = MagicMock()
        mock_svc.check_duplicates.return_value = []
        mock_svc.commit.return_value = CommitResult(id="uuid-new")
        with patch(_PATCH_CONFIG), patch(_PATCH_SERVICE, return_value=mock_svc):
            from akr.cli import akr_commit
            akr_commit()
        out = json.loads(capsys.readouterr().out)
        assert out == {"id": "uuid-new", "status": "committed"}
        mock_svc.check_duplicates.assert_called_once_with("c", None)
        mock_svc.commit.assert_called_once()

    def test_check_duplicates_with_duplicates_warns(self, monkeypatch, capsys):
        """--check-duplicates with duplicates found → outputs warning, doesn't commit."""
        monkeypatch.setattr(
            "sys.argv",
            ["akr-commit", "--json", '{"title":"t","content":"c","tags":["x"],"source_context":"sc"}', "--check-duplicates"],
        )
        mock_svc = MagicMock()
        mock_svc.check_duplicates.return_value = [
            {"id": "existing-1", "title": "Similar Article", "score": 0.15},
        ]
        with patch(_PATCH_CONFIG), patch(_PATCH_SERVICE, return_value=mock_svc):
            from akr.cli import akr_commit
            akr_commit()
        out = json.loads(capsys.readouterr().out)
        assert out["warning"] == "similar_artifacts_found"
        assert len(out["similar"]) == 1
        assert out["similar"][0]["id"] == "existing-1"
        assert out["similar"][0]["score"] == 0.15
        mock_svc.commit.assert_not_called()

    def test_check_duplicates_force_commits_anyway(self, monkeypatch, capsys):
        """--check-duplicates --force with duplicates → commits anyway."""
        monkeypatch.setattr(
            "sys.argv",
            [
                "akr-commit", "--json",
                '{"title":"t","content":"c","tags":["x"],"source_context":"sc"}',
                "--check-duplicates", "--force",
            ],
        )
        mock_svc = MagicMock()
        mock_svc.check_duplicates.return_value = [
            {"id": "existing-1", "title": "Similar Article", "score": 0.15},
        ]
        mock_svc.commit.return_value = CommitResult(id="uuid-forced")
        with patch(_PATCH_CONFIG), patch(_PATCH_SERVICE, return_value=mock_svc):
            from akr.cli import akr_commit
            akr_commit()
        out = json.loads(capsys.readouterr().out)
        assert out == {"id": "uuid-forced", "status": "committed"}
        mock_svc.check_duplicates.assert_called_once()
        mock_svc.commit.assert_called_once()

    def test_no_check_duplicates_flag_skips_check(self, monkeypatch, capsys):
        """Without --check-duplicates, duplicate check is not performed."""
        monkeypatch.setattr(
            "sys.argv",
            ["akr-commit", "--json", '{"title":"t","content":"c","tags":["x"],"source_context":"sc"}'],
        )
        mock_svc = MagicMock()
        mock_svc.commit.return_value = CommitResult(id="uuid-skip")
        with patch(_PATCH_CONFIG), patch(_PATCH_SERVICE, return_value=mock_svc):
            from akr.cli import akr_commit
            akr_commit()
        out = json.loads(capsys.readouterr().out)
        assert out == {"id": "uuid-skip", "status": "committed"}
        mock_svc.check_duplicates.assert_not_called()
