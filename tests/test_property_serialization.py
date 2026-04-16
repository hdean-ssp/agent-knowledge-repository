# Feature: agent-knowledge-repository, Property 13: Serialization round-trip
# Feature: agent-knowledge-repository, Property 14: Pretty-print produces valid JSON
"""Property-based tests for serialization round-trip and pretty-print.

**Validates: Requirements 13.3, 13.4**
"""

from __future__ import annotations

import json

from hypothesis import given, settings

from akr.schema import KnowledgeArtifact
from akr.serialization import (
    deserialize_artifact,
    pretty_print_artifact,
    serialize_artifact,
)
from tests.strategies import valid_artifact


# --- Property 13: Serialization round-trip ---


@given(artifact=valid_artifact())
@settings(max_examples=100)
def test_serialization_round_trip(artifact: KnowledgeArtifact) -> None:
    """Serializing then deserializing must produce identical field values.

    **Validates: Requirements 13.4**
    """
    restored = deserialize_artifact(serialize_artifact(artifact))

    assert restored.id == artifact.id
    assert restored.title == artifact.title
    assert restored.content == artifact.content
    assert restored.tags == artifact.tags
    assert restored.source_context == artifact.source_context
    assert restored.created_at == artifact.created_at
    assert restored.updated_at == artifact.updated_at
    assert restored.metadata == artifact.metadata


# --- Property 14: Pretty-print produces valid JSON ---


@given(artifact=valid_artifact())
@settings(max_examples=100)
def test_pretty_print_valid_json(artifact: KnowledgeArtifact) -> None:
    """Pretty-print output must be valid JSON, contain newlines, and round-trip.

    **Validates: Requirements 13.3**
    """
    pretty = pretty_print_artifact(artifact)

    # Must be valid JSON
    parsed = json.loads(pretty)

    # Must contain newlines (indentation)
    assert "\n" in pretty

    # Round-trip through pretty-print
    restored = deserialize_artifact(pretty)
    assert restored.id == artifact.id
    assert restored.title == artifact.title
    assert restored.content == artifact.content
    assert restored.tags == artifact.tags
    assert restored.source_context == artifact.source_context
    assert restored.created_at == artifact.created_at
    assert restored.updated_at == artifact.updated_at
    assert restored.metadata == artifact.metadata
