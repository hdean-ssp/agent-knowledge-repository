"""Custom exception hierarchy for AKR.

Every exception carries structured detail that can be serialized to JSON
for CLI error output.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class AKRError(Exception):
    """Base exception for all AKR errors."""

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable dict describing the error."""
        return {"error": "akr_error", "message": str(self)}


class ValidationError(AKRError):
    """Raised when artifact payload fails schema validation.

    Contains field-level error details.
    """

    def __init__(self, message: str, details: Optional[List[Dict[str, str]]] = None):
        super().__init__(message)
        self.details: List[Dict[str, str]] = details or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": "validation_error",
            "message": str(self),
            "details": self.details,
        }


class ArtifactNotFoundError(AKRError):
    """Raised when an artifact ID does not exist in the repository."""

    def __init__(self, artifact_id: str):
        super().__init__(f"Artifact not found: {artifact_id}")
        self.artifact_id = artifact_id

    def to_dict(self) -> Dict[str, Any]:
        return {"error": "not_found", "id": self.artifact_id}


class EmbeddingModelError(AKRError):
    """Raised when the ONNX embedding model cannot be loaded.

    Message includes model name and suggested pip install command.
    """

    def __init__(self, model_name: str, suggestion: str = ""):
        msg = f"Failed to load embedding model: {model_name}"
        if suggestion:
            msg += f". {suggestion}"
        super().__init__(msg)
        self.model_name = model_name
        self.suggestion = suggestion

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": "model_error",
            "model": self.model_name,
            "suggestion": self.suggestion,
        }


class RepositoryError(AKRError):
    """Raised when database operations fail (connection, write, read)."""

    def __init__(self, message: str, reason: str = ""):
        super().__init__(message)
        self.reason = reason or message

    def to_dict(self) -> Dict[str, Any]:
        return {"error": "repository_error", "reason": self.reason}


class LockTimeoutError(AKRError):
    """Raised when file lock cannot be acquired within timeout."""

    def __init__(self, path: str):
        super().__init__(f"Could not acquire lock: {path}")
        self.path = path

    def to_dict(self) -> Dict[str, Any]:
        return {"error": "lock_timeout", "path": self.path}


class ConfigValidationError(AKRError):
    """Raised when configuration file contains invalid values.

    Contains field-level error details.
    """

    def __init__(self, message: str, details: Optional[List[Dict[str, str]]] = None):
        super().__init__(message)
        self.details: List[Dict[str, str]] = details or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": "config_error",
            "message": str(self),
            "fields": self.details,
        }
