"""Shared Hypothesis strategies for AKR property-based tests."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import hypothesis.strategies as st

from akr.schema import KnowledgeArtifact


def non_empty_str(max_size: int = 80) -> st.SearchStrategy[str]:
    """Generate a non-empty, non-whitespace-only string."""
    return st.text(min_size=1, max_size=max_size).filter(lambda s: s.strip())


def valid_tags() -> st.SearchStrategy[list[str]]:
    """Generate a non-empty list of non-empty tag strings."""
    return st.lists(non_empty_str(max_size=50), min_size=1, max_size=5)


@st.composite
def valid_artifact(draw: st.DrawFn) -> KnowledgeArtifact:
    """Generate a random valid KnowledgeArtifact."""
    tags = draw(valid_tags())
    metadata = draw(st.one_of(
        st.none(),
        st.dictionaries(
            keys=non_empty_str(),
            values=non_empty_str(),
            min_size=0,
            max_size=5,
        ),
    ))
    now = datetime.now(timezone.utc).isoformat()
    return KnowledgeArtifact(
        id=str(uuid.uuid4()),
        title=draw(non_empty_str()),
        content=draw(non_empty_str()),
        tags=tags,
        source_context=draw(non_empty_str()),
        created_at=now,
        updated_at=now,
        metadata=metadata,
    )


@st.composite
def invalid_artifact(draw: st.DrawFn) -> dict:
    """Generate a dict that violates the Knowledge Schema in at least one way."""
    base = {
        "title": draw(non_empty_str()),
        "content": draw(non_empty_str()),
        "tags": draw(valid_tags()),
        "source_context": draw(non_empty_str()),
    }

    corruption = draw(st.sampled_from([
        "missing_title",
        "missing_content",
        "missing_tags",
        "missing_source_context",
        "empty_title",
        "empty_content",
        "empty_source_context",
        "empty_tags_list",
        "tags_with_empty_string",
        "tags_not_a_list",
        "title_not_string",
        "content_not_string",
    ]))

    if corruption == "missing_title":
        del base["title"]
    elif corruption == "missing_content":
        del base["content"]
    elif corruption == "missing_tags":
        del base["tags"]
    elif corruption == "missing_source_context":
        del base["source_context"]
    elif corruption == "empty_title":
        base["title"] = "   "
    elif corruption == "empty_content":
        base["content"] = "   "
    elif corruption == "empty_source_context":
        base["source_context"] = "   "
    elif corruption == "empty_tags_list":
        base["tags"] = []
    elif corruption == "tags_with_empty_string":
        base["tags"] = ["valid", "   "]
    elif corruption == "tags_not_a_list":
        base["tags"] = "not-a-list"
    elif corruption == "title_not_string":
        base["title"] = 42
    elif corruption == "content_not_string":
        base["content"] = 42

    return base
