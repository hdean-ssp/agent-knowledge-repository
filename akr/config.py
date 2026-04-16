"""Configuration loader for AKR.

Reads ``.kiro/knowledge-config.json`` from the project root (cwd) or
home directory, validates values, and falls back to sensible defaults.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from akr.errors import ConfigValidationError

_VALID_REPO_MODES = ("shared", "user", "both")

_DEFAULTS: Dict[str, Any] = {
    "repo_mode": "user",
    "shared_repo_path": "/var/lib/agent-knowledge-repo/",
    "user_repo_path": "~/.kiro/knowledge/",
    "embedding_model": "BAAI/bge-small-en-v1.5",
    "default_top_n": 5,
    "similarity_threshold": 0.3,
}


@dataclass
class AKRConfig:
    """Runtime configuration for the Agent Knowledge Repository."""

    repo_mode: str
    shared_repo_path: str
    user_repo_path: str
    embedding_model: str
    default_top_n: int
    similarity_threshold: float


def validate_config(raw: Dict[str, Any]) -> List[Dict[str, str]]:
    """Validate a raw config dict and return a list of field-level errors.

    This is intentionally separated from file loading so that property
    tests can exercise validation without touching the filesystem.
    """
    errors: List[Dict[str, str]] = []

    # repo_mode
    if "repo_mode" in raw:
        if not isinstance(raw["repo_mode"], str) or raw["repo_mode"] not in _VALID_REPO_MODES:
            errors.append({"field": "repo_mode", "message": f"'repo_mode' must be one of {_VALID_REPO_MODES}"})

    # shared_repo_path
    if "shared_repo_path" in raw:
        if not isinstance(raw["shared_repo_path"], str):
            errors.append({"field": "shared_repo_path", "message": "'shared_repo_path' must be a string"})

    # user_repo_path
    if "user_repo_path" in raw:
        if not isinstance(raw["user_repo_path"], str):
            errors.append({"field": "user_repo_path", "message": "'user_repo_path' must be a string"})

    # embedding_model
    if "embedding_model" in raw:
        if not isinstance(raw["embedding_model"], str):
            errors.append({"field": "embedding_model", "message": "'embedding_model' must be a string"})

    # default_top_n
    if "default_top_n" in raw:
        if not isinstance(raw["default_top_n"], int) or isinstance(raw["default_top_n"], bool) or raw["default_top_n"] < 1:
            errors.append({"field": "default_top_n", "message": "'default_top_n' must be an integer >= 1"})

    # similarity_threshold
    if "similarity_threshold" in raw:
        val = raw["similarity_threshold"]
        if not isinstance(val, (int, float)) or isinstance(val, bool) or val < 0 or val > 2:
            errors.append({"field": "similarity_threshold", "message": "'similarity_threshold' must be a number in [0, 2]"})

    return errors


def _find_config_file() -> Path | None:
    """Search for ``.kiro/knowledge-config.json`` in cwd then home."""
    candidates = [
        Path.cwd() / ".kiro" / "knowledge-config.json",
        Path.home() / ".kiro" / "knowledge-config.json",
    ]
    for path in candidates:
        if path.is_file():
            return path
    return None


def load_config() -> AKRConfig:
    """Load configuration, validate, and return an ``AKRConfig``.

    Search order:
      1. ``<cwd>/.kiro/knowledge-config.json``
      2. ``~/.kiro/knowledge-config.json``

    Falls back to defaults (user mode) when no file is found.
    Raises ``ConfigValidationError`` for invalid values.
    """
    config_path = _find_config_file()

    if config_path is None:
        raw: Dict[str, Any] = {}
    else:
        with open(config_path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)

    errors = validate_config(raw)
    if errors:
        raise ConfigValidationError("Invalid configuration", details=errors)

    return AKRConfig(
        repo_mode=raw.get("repo_mode", _DEFAULTS["repo_mode"]),
        shared_repo_path=raw.get("shared_repo_path", _DEFAULTS["shared_repo_path"]),
        user_repo_path=raw.get("user_repo_path", _DEFAULTS["user_repo_path"]),
        embedding_model=raw.get("embedding_model", _DEFAULTS["embedding_model"]),
        default_top_n=raw.get("default_top_n", _DEFAULTS["default_top_n"]),
        similarity_threshold=raw.get("similarity_threshold", _DEFAULTS["similarity_threshold"]),
    )
