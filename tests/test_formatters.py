"""Unit tests for akr/formatters.py — json, text, and brief output formats."""

from __future__ import annotations

import json

from akr.formatters import (
    format_fetch_brief,
    format_fetch_json,
    format_fetch_text,
    format_list_brief,
    format_list_json,
    format_list_text,
)
from akr.schema import KnowledgeArtifact


def _make_artifact(**overrides) -> KnowledgeArtifact:
    defaults = dict(
        id="abc-123",
        title="Test Artifact",
        content="Some content here",
        tags=["tag1", "tag2"],
        source_context="src/main.py:func",
        created_at="2024-01-01T00:00:00+00:00",
        updated_at="2024-06-15T12:00:00+00:00",
        metadata=None,
    )
    defaults.update(overrides)
    return KnowledgeArtifact(**defaults)


# ------------------------------------------------------------------
# Fetch formatters
# ------------------------------------------------------------------

class TestFormatFetchJson:
    def test_single_result(self):
        a = _make_artifact()
        results = [{"artifact": a, "score": 0.15, "source_repo": "user"}]
        out = json.loads(format_fetch_json(results))
        assert len(out) == 1
        assert out[0]["score"] == 0.15
        assert out[0]["source_repo"] == "user"
        assert out[0]["artifact"]["id"] == "abc-123"
        assert out[0]["artifact"]["title"] == "Test Artifact"

    def test_empty_results(self):
        out = json.loads(format_fetch_json([]))
        assert out == []

    def test_multiple_results(self):
        a1 = _make_artifact(id="id-1", title="First")
        a2 = _make_artifact(id="id-2", title="Second")
        results = [
            {"artifact": a1, "score": 0.1, "source_repo": "user"},
            {"artifact": a2, "score": 0.2, "source_repo": "shared"},
        ]
        out = json.loads(format_fetch_json(results))
        assert len(out) == 2
        assert out[0]["artifact"]["id"] == "id-1"
        assert out[1]["artifact"]["id"] == "id-2"


class TestFormatFetchBrief:
    def test_single_result(self):
        a = _make_artifact()
        results = [{"artifact": a, "score": 0.1500, "source_repo": "user"}]
        out = format_fetch_brief(results)
        assert out == "[abc-123] Test Artifact (score: 0.1500)"

    def test_empty_results(self):
        assert format_fetch_brief([]) == ""

    def test_multiple_results(self):
        a1 = _make_artifact(id="id-1", title="First")
        a2 = _make_artifact(id="id-2", title="Second")
        results = [
            {"artifact": a1, "score": 0.1, "source_repo": "user"},
            {"artifact": a2, "score": 0.25, "source_repo": "shared"},
        ]
        lines = format_fetch_brief(results).split("\n")
        assert len(lines) == 2
        assert "[id-1]" in lines[0]
        assert "[id-2]" in lines[1]


class TestFormatFetchText:
    def test_single_result(self):
        a = _make_artifact()
        results = [{"artifact": a, "score": 0.15, "source_repo": "user"}]
        out = format_fetch_text(results)
        assert "Title: Test Artifact" in out
        assert "Tags: tag1, tag2" in out
        assert "Source: src/main.py:func" in out
        assert "Score: 0.1500" in out
        assert "Content: Some content here" in out

    def test_long_content_truncated(self):
        long_content = "x" * 300
        a = _make_artifact(content=long_content)
        results = [{"artifact": a, "score": 0.1, "source_repo": "user"}]
        out = format_fetch_text(results)
        assert "Content: " + "x" * 200 + "..." in out

    def test_content_exactly_200_no_ellipsis(self):
        content = "y" * 200
        a = _make_artifact(content=content)
        results = [{"artifact": a, "score": 0.1, "source_repo": "user"}]
        out = format_fetch_text(results)
        assert "..." not in out

    def test_empty_results(self):
        assert format_fetch_text([]) == ""


# ------------------------------------------------------------------
# List formatters
# ------------------------------------------------------------------

class TestFormatListJson:
    def test_single_artifact(self):
        a = _make_artifact()
        out = json.loads(format_list_json([a]))
        assert len(out) == 1
        assert out[0]["id"] == "abc-123"
        assert out[0]["tags"] == ["tag1", "tag2"]

    def test_empty_list(self):
        out = json.loads(format_list_json([]))
        assert out == []


class TestFormatListBrief:
    def test_single_artifact(self):
        a = _make_artifact()
        out = format_list_brief([a])
        assert out == "[abc-123] Test Artifact (2024-06-15T12:00:00+00:00)"

    def test_empty_list(self):
        assert format_list_brief([]) == ""

    def test_multiple_artifacts(self):
        a1 = _make_artifact(id="id-1", title="First")
        a2 = _make_artifact(id="id-2", title="Second")
        lines = format_list_brief([a1, a2]).split("\n")
        assert len(lines) == 2
        assert "[id-1]" in lines[0]
        assert "[id-2]" in lines[1]


class TestFormatListText:
    def test_single_artifact(self):
        a = _make_artifact()
        out = format_list_text([a])
        assert "Title: Test Artifact" in out
        assert "Tags: tag1, tag2" in out
        assert "Source: src/main.py:func" in out
        assert "Content: Some content here" in out

    def test_long_content_truncated(self):
        a = _make_artifact(content="z" * 300)
        out = format_list_text([a])
        assert "Content: " + "z" * 200 + "..." in out

    def test_empty_list(self):
        assert format_list_text([]) == ""


# ------------------------------------------------------------------
# CLI integration tests for --format flag
# ------------------------------------------------------------------

import json as _json
from unittest.mock import MagicMock, patch

import pytest

from akr.service import FetchResult, ListResult

_PATCH_CONFIG = "akr.cli.load_config"
_PATCH_SERVICE = "akr.cli.KnowledgeService"


class TestAkrFetchFormat:
    def test_fetch_json_default(self, monkeypatch, capsys):
        """Default format is json — same as before."""
        monkeypatch.setattr("sys.argv", ["akr-fetch", "--query", "test"])
        a = _make_artifact()
        mock_svc = MagicMock()
        mock_svc.fetch.return_value = [FetchResult(artifact=a, score=0.15, source_repo="user")]
        with patch(_PATCH_CONFIG), patch(_PATCH_SERVICE, return_value=mock_svc):
            from akr.cli import akr_fetch
            akr_fetch()
        out = _json.loads(capsys.readouterr().out)
        assert isinstance(out, list)
        assert out[0]["score"] == 0.15

    def test_fetch_brief_format(self, monkeypatch, capsys):
        monkeypatch.setattr("sys.argv", ["akr-fetch", "--query", "test", "--format", "brief"])
        a = _make_artifact()
        mock_svc = MagicMock()
        mock_svc.fetch.return_value = [FetchResult(artifact=a, score=0.15, source_repo="user")]
        with patch(_PATCH_CONFIG), patch(_PATCH_SERVICE, return_value=mock_svc):
            from akr.cli import akr_fetch
            akr_fetch()
        out = capsys.readouterr().out.strip()
        assert "[abc-123]" in out
        assert "Test Artifact" in out
        assert "score: 0.1500" in out

    def test_fetch_text_format(self, monkeypatch, capsys):
        monkeypatch.setattr("sys.argv", ["akr-fetch", "--query", "test", "--format", "text"])
        a = _make_artifact()
        mock_svc = MagicMock()
        mock_svc.fetch.return_value = [FetchResult(artifact=a, score=0.15, source_repo="user")]
        with patch(_PATCH_CONFIG), patch(_PATCH_SERVICE, return_value=mock_svc):
            from akr.cli import akr_fetch
            akr_fetch()
        out = capsys.readouterr().out
        assert "Title: Test Artifact" in out
        assert "Score: 0.1500" in out

    def test_fetch_empty_json(self, monkeypatch, capsys):
        monkeypatch.setattr("sys.argv", ["akr-fetch", "--query", "nothing", "--format", "json"])
        mock_svc = MagicMock()
        mock_svc.fetch.return_value = []
        with patch(_PATCH_CONFIG), patch(_PATCH_SERVICE, return_value=mock_svc):
            from akr.cli import akr_fetch
            akr_fetch()
        out = _json.loads(capsys.readouterr().out)
        assert out["results"] == []
        assert "No relevant knowledge found" in out["message"]

    def test_fetch_empty_brief(self, monkeypatch, capsys):
        monkeypatch.setattr("sys.argv", ["akr-fetch", "--query", "nothing", "--format", "brief"])
        mock_svc = MagicMock()
        mock_svc.fetch.return_value = []
        with patch(_PATCH_CONFIG), patch(_PATCH_SERVICE, return_value=mock_svc):
            from akr.cli import akr_fetch
            akr_fetch()
        out = capsys.readouterr().out.strip()
        assert out == "No relevant knowledge found"

    def test_fetch_empty_text(self, monkeypatch, capsys):
        monkeypatch.setattr("sys.argv", ["akr-fetch", "--query", "nothing", "--format", "text"])
        mock_svc = MagicMock()
        mock_svc.fetch.return_value = []
        with patch(_PATCH_CONFIG), patch(_PATCH_SERVICE, return_value=mock_svc):
            from akr.cli import akr_fetch
            akr_fetch()
        out = capsys.readouterr().out.strip()
        assert out == "No relevant knowledge found"


class TestAkrListFormat:
    def test_list_json_default(self, monkeypatch, capsys):
        monkeypatch.setattr("sys.argv", ["akr-list"])
        a = _make_artifact()
        mock_svc = MagicMock()
        mock_svc.list_artifacts.return_value = ListResult(artifacts=[a], total=1)
        with patch(_PATCH_CONFIG), patch(_PATCH_SERVICE, return_value=mock_svc):
            from akr.cli import akr_list
            akr_list()
        out = _json.loads(capsys.readouterr().out)
        assert isinstance(out, list)
        assert out[0]["id"] == "abc-123"

    def test_list_brief_format(self, monkeypatch, capsys):
        monkeypatch.setattr("sys.argv", ["akr-list", "--format", "brief"])
        a = _make_artifact()
        mock_svc = MagicMock()
        mock_svc.list_artifacts.return_value = ListResult(artifacts=[a], total=1)
        with patch(_PATCH_CONFIG), patch(_PATCH_SERVICE, return_value=mock_svc):
            from akr.cli import akr_list
            akr_list()
        out = capsys.readouterr().out.strip()
        assert "[abc-123]" in out
        assert "Test Artifact" in out

    def test_list_text_format(self, monkeypatch, capsys):
        monkeypatch.setattr("sys.argv", ["akr-list", "--format", "text"])
        a = _make_artifact()
        mock_svc = MagicMock()
        mock_svc.list_artifacts.return_value = ListResult(artifacts=[a], total=1)
        with patch(_PATCH_CONFIG), patch(_PATCH_SERVICE, return_value=mock_svc):
            from akr.cli import akr_list
            akr_list()
        out = capsys.readouterr().out
        assert "Title: Test Artifact" in out
        assert "Tags: tag1, tag2" in out
