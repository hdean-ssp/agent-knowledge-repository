"""Unit tests for the audit trail feature (Task 8).

Tests:
- Repository-level: commit, update twice, verify 2 audit records newest-first
- Repository-level: audit on non-existent artifact returns empty list
- Service-level: get_audit_trail delegates correctly
- CLI-level: mock service, verify JSON output structure
"""

from __future__ import annotations

import json
import struct
import time
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

sqlite_vec = pytest.importorskip("sqlite_vec")

from akr.repository import ArtifactRepository
from akr.schema import KnowledgeArtifact

DIMS = 384


def _fake_embedding(value: float = 0.1) -> bytes:
    return struct.pack(f"<{DIMS}f", *([value] * DIMS))


def _make_artifact(**overrides) -> KnowledgeArtifact:
    now = datetime.now(timezone.utc).isoformat()
    defaults = dict(
        id="audit-test-1",
        title="Original Title",
        content="Original content",
        tags=["test"],
        source_context="tests/test_audit.py",
        created_at=now,
        updated_at=now,
        metadata=None,
    )
    defaults.update(overrides)
    return KnowledgeArtifact(**defaults)


@pytest.fixture()
def repo():
    r = ArtifactRepository(":memory:")
    yield r
    r.close()


# ------------------------------------------------------------------
# Repository-level tests
# ------------------------------------------------------------------

class TestAuditTrailRepository:
    def test_two_updates_produce_two_audit_records(self, repo: ArtifactRepository):
        """Commit, update twice → 2 audit records in newest-first order."""
        original = _make_artifact()
        repo.insert_artifact(original, _fake_embedding(0.1))

        # First update
        updated1 = _make_artifact(
            title="Title v2",
            content="Content v2",
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        repo.update_artifact(original.id, updated1, _fake_embedding(0.2))

        # Small delay to ensure distinct timestamps
        time.sleep(0.01)

        # Second update
        updated2 = _make_artifact(
            title="Title v3",
            content="Content v3",
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        repo.update_artifact(original.id, updated2, _fake_embedding(0.3))

        records = repo.get_audit_trail(original.id)
        assert len(records) == 2

        # Newest first
        assert records[0]["changed_at"] >= records[1]["changed_at"]

        # Second record (older) should have original content
        assert records[1]["previous_content"]["title"] == "Original Title"
        assert records[1]["previous_content"]["content"] == "Original content"

        # First record (newer) should have v2 content
        assert records[0]["previous_content"]["title"] == "Title v2"
        assert records[0]["previous_content"]["content"] == "Content v2"

        # All records should reference the correct artifact
        for r in records:
            assert r["artifact_id"] == original.id

    def test_audit_nonexistent_returns_empty(self, repo: ArtifactRepository):
        """Audit trail for non-existent artifact returns empty list."""
        records = repo.get_audit_trail("does-not-exist")
        assert records == []


# ------------------------------------------------------------------
# CLI-level tests (mocked service)
# ------------------------------------------------------------------

_PATCH_CONFIG = "akr.cli.load_config"
_PATCH_SERVICE = "akr.cli.KnowledgeService"


class TestAkrAuditCLI:
    def test_audit_with_records(self, monkeypatch, capsys):
        """akr-audit --id <uuid> outputs JSON array of audit records."""
        monkeypatch.setattr("sys.argv", ["akr-audit", "--id", "uuid-1"])
        mock_svc = MagicMock()
        mock_svc.get_audit_trail.return_value = [
            {
                "artifact_id": "uuid-1",
                "previous_content": {"title": "Old", "content": "Old content"},
                "changed_at": "2024-06-01T00:00:00+00:00",
            },
        ]
        with patch(_PATCH_CONFIG), patch(_PATCH_SERVICE, return_value=mock_svc):
            from akr.cli import akr_audit
            akr_audit()
        out = json.loads(capsys.readouterr().out)
        assert isinstance(out, list)
        assert len(out) == 1
        assert "changed_at" in out[0]
        assert "previous_content" in out[0]
        assert out[0]["previous_content"]["title"] == "Old"

    def test_audit_no_records(self, monkeypatch, capsys):
        """akr-audit with no records outputs empty audit_trail message."""
        monkeypatch.setattr("sys.argv", ["akr-audit", "--id", "uuid-none"])
        mock_svc = MagicMock()
        mock_svc.get_audit_trail.return_value = []
        with patch(_PATCH_CONFIG), patch(_PATCH_SERVICE, return_value=mock_svc):
            from akr.cli import akr_audit
            akr_audit()
        out = json.loads(capsys.readouterr().out)
        assert out["audit_trail"] == []
        assert "No audit records found" in out["message"]

    def test_audit_passes_repo_mode(self, monkeypatch, capsys):
        """akr-audit --repo shared passes repo_mode to service."""
        monkeypatch.setattr("sys.argv", ["akr-audit", "--id", "uuid-1", "--repo", "shared"])
        mock_svc = MagicMock()
        mock_svc.get_audit_trail.return_value = []
        with patch(_PATCH_CONFIG), patch(_PATCH_SERVICE, return_value=mock_svc):
            from akr.cli import akr_audit
            akr_audit()
        mock_svc.get_audit_trail.assert_called_once_with("uuid-1", "shared")
