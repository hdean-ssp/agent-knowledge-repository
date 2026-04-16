"""Unit tests for akr-export and akr-import CLI commands.

Mocks KnowledgeService and load_config since fastembed is not installed.
Tests argument parsing, JSON file I/O, and output structure.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from akr.errors import ValidationError
from akr.schema import KnowledgeArtifact
from akr.service import ImportResult

_PATCH_CONFIG = "akr.cli.load_config"
_PATCH_SERVICE = "akr.cli.KnowledgeService"

_SAMPLE_ARTIFACTS = [
    {
        "id": "abc-123",
        "title": "Test artifact",
        "content": "Some content",
        "tags": ["test"],
        "source_context": "ctx",
        "created_at": "2024-01-01T00:00:00+00:00",
        "updated_at": "2024-01-01T00:00:00+00:00",
        "metadata": None,
    },
    {
        "id": "def-456",
        "title": "Second artifact",
        "content": "More content",
        "tags": ["demo"],
        "source_context": "ctx2",
        "created_at": "2024-02-01T00:00:00+00:00",
        "updated_at": "2024-02-01T00:00:00+00:00",
        "metadata": {"key": "value"},
    },
]


# ------------------------------------------------------------------
# akr_export
# ------------------------------------------------------------------

class TestAkrExport:
    def test_export_writes_json_file(self, monkeypatch, capsys, tmp_path):
        """Export writes correct JSON array to the output file."""
        output_file = tmp_path / "export.json"
        monkeypatch.setattr(
            "sys.argv", ["akr-export", "--output", str(output_file)]
        )
        mock_svc = MagicMock()
        mock_svc.export_artifacts.return_value = _SAMPLE_ARTIFACTS
        with patch(_PATCH_CONFIG), patch(_PATCH_SERVICE, return_value=mock_svc):
            from akr.cli import akr_export
            akr_export()

        # Verify file contents
        written = json.loads(output_file.read_text())
        assert len(written) == 2
        assert written[0]["id"] == "abc-123"
        assert written[1]["id"] == "def-456"

        # Verify stdout output
        out = json.loads(capsys.readouterr().out)
        assert out["status"] == "exported"
        assert out["count"] == 2
        assert out["path"] == str(output_file)

    def test_export_with_repo_mode(self, monkeypatch, capsys, tmp_path):
        """Export passes --repo argument to service."""
        output_file = tmp_path / "export.json"
        monkeypatch.setattr(
            "sys.argv",
            ["akr-export", "--output", str(output_file), "--repo", "shared"],
        )
        mock_svc = MagicMock()
        mock_svc.export_artifacts.return_value = []
        with patch(_PATCH_CONFIG), patch(_PATCH_SERVICE, return_value=mock_svc):
            from akr.cli import akr_export
            akr_export()
        mock_svc.export_artifacts.assert_called_once_with("shared")

    def test_export_empty_repo(self, monkeypatch, capsys, tmp_path):
        """Export on empty repo writes empty JSON array."""
        output_file = tmp_path / "export.json"
        monkeypatch.setattr(
            "sys.argv", ["akr-export", "--output", str(output_file)]
        )
        mock_svc = MagicMock()
        mock_svc.export_artifacts.return_value = []
        with patch(_PATCH_CONFIG), patch(_PATCH_SERVICE, return_value=mock_svc):
            from akr.cli import akr_export
            akr_export()

        written = json.loads(output_file.read_text())
        assert written == []
        out = json.loads(capsys.readouterr().out)
        assert out["count"] == 0

    def test_export_unexpected_error(self, monkeypatch, capsys, tmp_path):
        """Export handles unexpected errors gracefully."""
        output_file = tmp_path / "export.json"
        monkeypatch.setattr(
            "sys.argv", ["akr-export", "--output", str(output_file)]
        )
        mock_svc = MagicMock()
        mock_svc.export_artifacts.side_effect = RuntimeError("boom")
        with patch(_PATCH_CONFIG), patch(_PATCH_SERVICE, return_value=mock_svc):
            from akr.cli import akr_export
            with pytest.raises(SystemExit) as exc_info:
                akr_export()
            assert exc_info.value.code == 2


# ------------------------------------------------------------------
# akr_import — skip strategy
# ------------------------------------------------------------------

class TestAkrImportSkip:
    def test_import_skip_reads_file_and_calls_service(self, monkeypatch, capsys, tmp_path):
        """Import reads JSON file and calls import_artifacts with skip strategy."""
        input_file = tmp_path / "import.json"
        input_file.write_text(json.dumps(_SAMPLE_ARTIFACTS))
        monkeypatch.setattr(
            "sys.argv", ["akr-import", "--input", str(input_file)]
        )
        mock_svc = MagicMock()
        mock_svc.import_artifacts.return_value = ImportResult(imported=2, skipped=0, updated=0)
        with patch(_PATCH_CONFIG), patch(_PATCH_SERVICE, return_value=mock_svc):
            from akr.cli import akr_import
            akr_import()

        # Verify service called with correct args
        call_args = mock_svc.import_artifacts.call_args
        assert call_args[0][0] == _SAMPLE_ARTIFACTS  # data
        assert call_args[0][1] == "skip"  # strategy
        assert call_args[0][2] is None  # repo_mode

        # Verify stdout
        out = json.loads(capsys.readouterr().out)
        assert out == {"status": "imported", "imported": 2, "skipped": 0, "updated": 0}

    def test_import_skip_with_existing_artifacts(self, monkeypatch, capsys, tmp_path):
        """Import with skip strategy reports skipped count."""
        input_file = tmp_path / "import.json"
        input_file.write_text(json.dumps(_SAMPLE_ARTIFACTS))
        monkeypatch.setattr(
            "sys.argv", ["akr-import", "--input", str(input_file), "--strategy", "skip"]
        )
        mock_svc = MagicMock()
        mock_svc.import_artifacts.return_value = ImportResult(imported=1, skipped=1, updated=0)
        with patch(_PATCH_CONFIG), patch(_PATCH_SERVICE, return_value=mock_svc):
            from akr.cli import akr_import
            akr_import()

        out = json.loads(capsys.readouterr().out)
        assert out["imported"] == 1
        assert out["skipped"] == 1
        assert out["updated"] == 0


# ------------------------------------------------------------------
# akr_import — update strategy
# ------------------------------------------------------------------

class TestAkrImportUpdate:
    def test_import_update_calls_service_with_update_strategy(self, monkeypatch, capsys, tmp_path):
        """Import with --strategy update passes 'update' to service."""
        input_file = tmp_path / "import.json"
        input_file.write_text(json.dumps(_SAMPLE_ARTIFACTS))
        monkeypatch.setattr(
            "sys.argv",
            ["akr-import", "--input", str(input_file), "--strategy", "update"],
        )
        mock_svc = MagicMock()
        mock_svc.import_artifacts.return_value = ImportResult(imported=0, skipped=1, updated=1)
        with patch(_PATCH_CONFIG), patch(_PATCH_SERVICE, return_value=mock_svc):
            from akr.cli import akr_import
            akr_import()

        call_args = mock_svc.import_artifacts.call_args
        assert call_args[0][1] == "update"

        out = json.loads(capsys.readouterr().out)
        assert out == {"status": "imported", "imported": 0, "skipped": 1, "updated": 1}

    def test_import_update_with_repo_mode(self, monkeypatch, capsys, tmp_path):
        """Import passes --repo argument to service."""
        input_file = tmp_path / "import.json"
        input_file.write_text(json.dumps(_SAMPLE_ARTIFACTS))
        monkeypatch.setattr(
            "sys.argv",
            ["akr-import", "--input", str(input_file), "--strategy", "update", "--repo", "shared"],
        )
        mock_svc = MagicMock()
        mock_svc.import_artifacts.return_value = ImportResult(imported=2, skipped=0, updated=0)
        with patch(_PATCH_CONFIG), patch(_PATCH_SERVICE, return_value=mock_svc):
            from akr.cli import akr_import
            akr_import()

        call_args = mock_svc.import_artifacts.call_args
        assert call_args[0][2] == "shared"

    def test_import_validation_error(self, monkeypatch, capsys, tmp_path):
        """Import handles AKRError from service."""
        input_file = tmp_path / "import.json"
        input_file.write_text(json.dumps([{"bad": "data"}]))
        monkeypatch.setattr(
            "sys.argv", ["akr-import", "--input", str(input_file)]
        )
        mock_svc = MagicMock()
        mock_svc.import_artifacts.side_effect = ValidationError("bad data")
        with patch(_PATCH_CONFIG), patch(_PATCH_SERVICE, return_value=mock_svc):
            from akr.cli import akr_import
            with pytest.raises(SystemExit) as exc_info:
                akr_import()
            assert exc_info.value.code == 1

    def test_import_unexpected_error(self, monkeypatch, capsys, tmp_path):
        """Import handles unexpected errors gracefully."""
        input_file = tmp_path / "import.json"
        input_file.write_text(json.dumps(_SAMPLE_ARTIFACTS))
        monkeypatch.setattr(
            "sys.argv", ["akr-import", "--input", str(input_file)]
        )
        mock_svc = MagicMock()
        mock_svc.import_artifacts.side_effect = RuntimeError("boom")
        with patch(_PATCH_CONFIG), patch(_PATCH_SERVICE, return_value=mock_svc):
            from akr.cli import akr_import
            with pytest.raises(SystemExit) as exc_info:
                akr_import()
            assert exc_info.value.code == 2
