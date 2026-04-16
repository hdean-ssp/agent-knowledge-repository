"""JSON serialization and deserialization for KnowledgeArtifact."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from akr.schema import KnowledgeArtifact


def _artifact_to_dict(artifact: KnowledgeArtifact) -> Dict[str, Any]:
    """Convert a KnowledgeArtifact to a plain dict."""
    return {
        "id": artifact.id,
        "title": artifact.title,
        "content": artifact.content,
        "tags": list(artifact.tags),
        "source_context": artifact.source_context,
        "created_at": artifact.created_at,
        "updated_at": artifact.updated_at,
        "metadata": dict(artifact.metadata) if artifact.metadata is not None else None,
    }


def _dict_to_artifact(d: Dict[str, Any]) -> KnowledgeArtifact:
    """Reconstruct a KnowledgeArtifact from a plain dict."""
    metadata_raw = d.get("metadata")
    metadata: Optional[Dict[str, str]] = (
        {str(k): str(v) for k, v in metadata_raw.items()}
        if metadata_raw is not None
        else None
    )
    return KnowledgeArtifact(
        id=d["id"],
        title=d["title"],
        content=d["content"],
        tags=list(d["tags"]),
        source_context=d["source_context"],
        created_at=d["created_at"],
        updated_at=d["updated_at"],
        metadata=metadata,
    )


def serialize_artifact(artifact: KnowledgeArtifact) -> str:
    """Serialize a ``KnowledgeArtifact`` to a compact JSON string."""
    return json.dumps(_artifact_to_dict(artifact), ensure_ascii=False)


def deserialize_artifact(json_str: str) -> KnowledgeArtifact:
    """Deserialize a JSON string back to a ``KnowledgeArtifact``."""
    return _dict_to_artifact(json.loads(json_str))


def pretty_print_artifact(artifact: KnowledgeArtifact) -> str:
    """Format a ``KnowledgeArtifact`` as human-readable JSON with 2-space indentation."""
    return json.dumps(_artifact_to_dict(artifact), indent=2, ensure_ascii=False)
