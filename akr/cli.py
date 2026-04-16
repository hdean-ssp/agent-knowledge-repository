"""CLI entry points for AKR commands.

Each function is a standalone entry point mapped in pyproject.toml.
Arguments are parsed from sys.argv via argparse. Output is JSON to stdout.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict

from akr.config import load_config
from akr.errors import AKRError
from akr.serialization import _artifact_to_dict
from akr.service import KnowledgeService


def _json_output(data: Any) -> None:
    """Print JSON to stdout."""
    print(json.dumps(data, ensure_ascii=False))


def _handle_error(exc: AKRError) -> None:
    """Format an AKRError as JSON and exit 1."""
    _json_output(exc.to_dict())
    sys.exit(1)


def _handle_unexpected(exc: Exception) -> None:
    """Format an unexpected exception as JSON and exit 2."""
    _json_output({"error": "unexpected_error", "message": str(exc)})
    sys.exit(2)


def _read_payload(args: argparse.Namespace) -> dict:
    """Read JSON payload from --json string or --file path."""
    if args.json is not None:
        return json.loads(args.json)
    with open(args.file, "r", encoding="utf-8") as fh:
        return json.load(fh)


# ------------------------------------------------------------------
# akr-commit
# ------------------------------------------------------------------

def akr_commit() -> None:
    """Store a new knowledge artifact."""
    parser = argparse.ArgumentParser(description="Commit a knowledge artifact")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--json", type=str, help="JSON payload string")
    group.add_argument("--file", type=str, help="Path to JSON file")
    parser.add_argument("--repo", type=str, default=None, help="Repository mode")
    args = parser.parse_args()

    try:
        config = load_config()
        service = KnowledgeService(config)
        payload = _read_payload(args)
        result = service.commit(payload, args.repo)
        _json_output({"id": result.id, "status": result.status})
    except AKRError as exc:
        _handle_error(exc)
    except Exception as exc:
        _handle_unexpected(exc)


# ------------------------------------------------------------------
# akr-fetch
# ------------------------------------------------------------------

def akr_fetch() -> None:
    """Fetch knowledge artifacts by semantic search."""
    parser = argparse.ArgumentParser(description="Fetch knowledge artifacts")
    parser.add_argument("--query", type=str, required=True, help="Search query")
    parser.add_argument("--top-n", type=int, default=None, help="Number of results")
    parser.add_argument("--threshold", type=float, default=None, help="Similarity threshold")
    parser.add_argument("--repo", type=str, default=None, help="Repository mode")
    args = parser.parse_args()

    try:
        config = load_config()
        service = KnowledgeService(config)
        results = service.fetch(args.query, args.top_n, args.threshold, args.repo)
        if not results:
            _json_output({"results": [], "message": "No relevant knowledge found"})
        else:
            _json_output([
                {
                    "artifact": _artifact_to_dict(r.artifact),
                    "score": r.score,
                    "source_repo": r.source_repo,
                }
                for r in results
            ])
    except AKRError as exc:
        _handle_error(exc)
    except Exception as exc:
        _handle_unexpected(exc)


# ------------------------------------------------------------------
# akr-update
# ------------------------------------------------------------------

def akr_update() -> None:
    """Update an existing knowledge artifact."""
    parser = argparse.ArgumentParser(description="Update a knowledge artifact")
    parser.add_argument("--id", type=str, required=True, help="Artifact ID")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--json", type=str, help="JSON payload string")
    group.add_argument("--file", type=str, help="Path to JSON file")
    parser.add_argument("--repo", type=str, default=None, help="Repository mode")
    args = parser.parse_args()

    try:
        config = load_config()
        service = KnowledgeService(config)
        payload = _read_payload(args)
        result = service.update(args.id, payload, args.repo)
        _json_output({"id": result.id, "status": result.status})
    except AKRError as exc:
        _handle_error(exc)
    except Exception as exc:
        _handle_unexpected(exc)


# ------------------------------------------------------------------
# akr-delete
# ------------------------------------------------------------------

def akr_delete() -> None:
    """Delete a knowledge artifact."""
    parser = argparse.ArgumentParser(description="Delete a knowledge artifact")
    parser.add_argument("--id", type=str, required=True, help="Artifact ID")
    parser.add_argument("--repo", type=str, default=None, help="Repository mode")
    args = parser.parse_args()

    try:
        config = load_config()
        service = KnowledgeService(config)
        result = service.delete(args.id, args.repo)
        _json_output({"id": result.id, "status": result.status})
    except AKRError as exc:
        _handle_error(exc)
    except Exception as exc:
        _handle_unexpected(exc)


# ------------------------------------------------------------------
# akr-list
# ------------------------------------------------------------------

def akr_list() -> None:
    """List knowledge artifacts with optional filters."""
    parser = argparse.ArgumentParser(description="List knowledge artifacts")
    parser.add_argument("--tags", type=str, default=None, help="Comma-separated tags")
    parser.add_argument("--since", type=str, default=None, help="Filter by date")
    parser.add_argument("--limit", type=int, default=20, help="Max results")
    parser.add_argument("--offset", type=int, default=0, help="Pagination offset")
    parser.add_argument("--repo", type=str, default=None, help="Repository mode")
    args = parser.parse_args()

    try:
        config = load_config()
        service = KnowledgeService(config)
        tags = [t.strip() for t in args.tags.split(",")] if args.tags else None
        result = service.list_artifacts(tags, args.since, args.limit, args.offset, args.repo)
        _json_output([_artifact_to_dict(a) for a in result.artifacts])
    except AKRError as exc:
        _handle_error(exc)
    except Exception as exc:
        _handle_unexpected(exc)
