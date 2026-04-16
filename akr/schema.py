"""Knowledge artifact data model and schema validation.

Provides the ``KnowledgeArtifact`` dataclass that represents a single
knowledge entry, and ``SchemaValidator`` which validates raw dicts
coming from CLI / JSON input and produces validated artifact instances.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from akr.errors import ValidationError


@dataclass
class KnowledgeArtifact:
    """A single knowledge entry stored in the repository."""

    id: str = ""
    title: str = ""
    content: str = ""
    tags: List[str] = field(default_factory=list)
    source_context: str = ""
    created_at: str = ""
    updated_at: str = ""
    metadata: Optional[Dict[str, str]] = None


class SchemaValidator:
    """Validates raw dicts against the Knowledge Schema."""

    def validate(self, data: dict) -> KnowledgeArtifact:
        """Validate *data* and return a populated ``KnowledgeArtifact``.

        Auto-populates ``id``, ``created_at``, and ``updated_at``.
        Raises ``ValidationError`` with field-level details on invalid input.
        """
        errors: List[Dict[str, str]] = []

        # --- required string fields ---
        for field_name in ("title", "content", "source_context"):
            value = data.get(field_name)
            if value is None:
                errors.append({"field": field_name, "message": f"'{field_name}' is required"})
            elif not isinstance(value, str):
                errors.append({"field": field_name, "message": f"'{field_name}' must be a string"})
            elif not value.strip():
                errors.append({"field": field_name, "message": f"'{field_name}' must not be empty"})

        # --- tags ---
        tags = data.get("tags")
        if tags is None:
            errors.append({"field": "tags", "message": "'tags' is required"})
        elif not isinstance(tags, list):
            errors.append({"field": "tags", "message": "'tags' must be a list"})
        elif len(tags) == 0:
            errors.append({"field": "tags", "message": "'tags' must not be empty"})
        else:
            for i, tag in enumerate(tags):
                if not isinstance(tag, str) or not tag.strip():
                    errors.append({"field": f"tags[{i}]", "message": "each tag must be a non-empty string"})
                    break  # one error is enough

        # --- optional metadata ---
        metadata = data.get("metadata")
        if metadata is not None:
            if not isinstance(metadata, dict):
                errors.append({"field": "metadata", "message": "'metadata' must be a dict"})
            else:
                for k, v in metadata.items():
                    if not isinstance(k, str) or not isinstance(v, str):
                        errors.append({"field": "metadata", "message": "metadata keys and values must be strings"})
                        break

        if errors:
            raise ValidationError("Artifact validation failed", details=errors)

        now = datetime.now(timezone.utc).isoformat()

        return KnowledgeArtifact(
            id=str(uuid.uuid4()),
            title=data["title"],
            content=data["content"],
            tags=list(data["tags"]),
            source_context=data["source_context"],
            created_at=now,
            updated_at=now,
            metadata=dict(metadata) if metadata is not None else None,
        )
