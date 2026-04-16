"""Unit tests for AKR configuration loader."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from akr.config import AKRConfig, load_config, validate_config
from akr.errors import ConfigValidationError


class TestDefaults:
    """When no config file exists, load_config returns sensible defaults."""

    def test_default_repo_mode(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        cfg = load_config()
        assert cfg.repo_mode == "user"

    def test_default_top_n(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        cfg = load_config()
        assert cfg.default_top_n == 5

    def test_default_similarity_threshold(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        cfg = load_config()
        assert cfg.similarity_threshold == pytest.approx(0.3)

    def test_default_embedding_model(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        cfg = load_config()
        assert cfg.embedding_model == "BAAI/bge-small-en-v1.5"


class TestFileLoading:
    """Config file is loaded and values are applied correctly."""

    def test_valid_config_loaded(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        config_dir = tmp_path / ".kiro"
        config_dir.mkdir()
        config_file = config_dir / "knowledge-config.json"
        config_file.write_text(json.dumps({
            "repo_mode": "shared",
            "shared_repo_path": "/custom/path/",
            "default_top_n": 10,
            "similarity_threshold": 0.5,
            "embedding_model": "custom-model",
        }))
        monkeypatch.chdir(tmp_path)

        cfg = load_config()
        assert cfg.repo_mode == "shared"
        assert cfg.shared_repo_path == "/custom/path/"
        assert cfg.default_top_n == 10
        assert cfg.similarity_threshold == pytest.approx(0.5)
        assert cfg.embedding_model == "custom-model"

    def test_partial_config_uses_defaults(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        config_dir = tmp_path / ".kiro"
        config_dir.mkdir()
        config_file = config_dir / "knowledge-config.json"
        config_file.write_text(json.dumps({"repo_mode": "both"}))
        monkeypatch.chdir(tmp_path)

        cfg = load_config()
        assert cfg.repo_mode == "both"
        # Everything else should be defaults
        assert cfg.default_top_n == 5
        assert cfg.similarity_threshold == pytest.approx(0.3)
        assert cfg.embedding_model == "BAAI/bge-small-en-v1.5"
        assert cfg.shared_repo_path == "/var/lib/agent-knowledge-repo/"
        assert cfg.user_repo_path == "~/.kiro/knowledge/"

    def test_invalid_config_raises(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        config_dir = tmp_path / ".kiro"
        config_dir.mkdir()
        config_file = config_dir / "knowledge-config.json"
        config_file.write_text(json.dumps({"default_top_n": -1}))
        monkeypatch.chdir(tmp_path)

        with pytest.raises(ConfigValidationError):
            load_config()
