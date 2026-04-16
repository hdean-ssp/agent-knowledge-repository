"""Output formatters for akr-fetch and akr-list commands.

Provides json, text, and brief output formats for fetch results
and list results.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

from akr.schema import KnowledgeArtifact
from akr.serialization import _artifact_to_dict


# ------------------------------------------------------------------
# Fetch formatters
# ------------------------------------------------------------------


def format_fetch_json(results: List[Dict[str, Any]]) -> str:
    """Format fetch results as JSON (list of {artifact, score, source_repo}).

    *results* is a list of dicts with keys ``artifact`` (KnowledgeArtifact),
    ``score`` (float), and ``source_repo`` (str).
    """
    payload = [
        {
            "artifact": _artifact_to_dict(r["artifact"]),
            "score": r["score"],
            "source_repo": r["source_repo"],
        }
        for r in results
    ]
    return json.dumps(payload, ensure_ascii=False)


def format_fetch_brief(results: List[Dict[str, Any]]) -> str:
    """One line per result: ``[<id>] <title> (score: <score>)``."""
    lines = []
    for r in results:
        a = r["artifact"]
        lines.append(f"[{a.id}] {a.title} (score: {r['score']:.4f})")
    return "\n".join(lines)


def format_fetch_text(results: List[Dict[str, Any]]) -> str:
    """Multi-line per result: title, tags, source_context, score, first 200 chars of content."""
    blocks = []
    for r in results:
        a = r["artifact"]
        content_preview = a.content[:200]
        if len(a.content) > 200:
            content_preview += "..."
        block = (
            f"Title: {a.title}\n"
            f"Tags: {', '.join(a.tags)}\n"
            f"Source: {a.source_context}\n"
            f"Score: {r['score']:.4f}\n"
            f"Content: {content_preview}"
        )
        blocks.append(block)
    return "\n\n".join(blocks)


# ------------------------------------------------------------------
# List formatters
# ------------------------------------------------------------------


def format_list_json(artifacts: List[KnowledgeArtifact]) -> str:
    """Format list results as JSON (list of artifact dicts)."""
    return json.dumps(
        [_artifact_to_dict(a) for a in artifacts], ensure_ascii=False
    )


def format_list_brief(artifacts: List[KnowledgeArtifact]) -> str:
    """One line per artifact: ``[<id>] <title> (<updated_at>)``."""
    lines = []
    for a in artifacts:
        lines.append(f"[{a.id}] {a.title} ({a.updated_at})")
    return "\n".join(lines)


def format_list_text(artifacts: List[KnowledgeArtifact]) -> str:
    """Multi-line per artifact: title, tags, source_context, first 200 chars of content."""
    blocks = []
    for a in artifacts:
        content_preview = a.content[:200]
        if len(a.content) > 200:
            content_preview += "..."
        block = (
            f"Title: {a.title}\n"
            f"Tags: {', '.join(a.tags)}\n"
            f"Source: {a.source_context}\n"
            f"Content: {content_preview}"
        )
        blocks.append(block)
    return "\n\n".join(blocks)
