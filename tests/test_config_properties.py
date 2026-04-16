# Feature: agent-knowledge-repository, Property 9: Configuration validation rejects invalid values
"""Property-based tests for AKR configuration validation."""

from __future__ import annotations

import hypothesis.strategies as st
from hypothesis import given, settings

from akr.config import validate_config
from akr.errors import ConfigValidationError


# ---------------------------------------------------------------------------
# Strategy: generate a config dict with at least one invalid value
# ---------------------------------------------------------------------------

@st.composite
def invalid_config(draw: st.DrawFn) -> dict:
    """Generate a config dict that contains at least one invalid field."""
    corruption = draw(st.sampled_from([
        "bad_top_n",
        "bad_threshold_negative",
        "bad_threshold_high",
        "bad_repo_mode",
    ]))

    cfg: dict = {}

    if corruption == "bad_top_n":
        # default_top_n must be >= 1; generate <= 0
        cfg["default_top_n"] = draw(st.integers(max_value=0))
    elif corruption == "bad_threshold_negative":
        # similarity_threshold must be in [0, 2]; generate < 0
        cfg["similarity_threshold"] = draw(
            st.floats(max_value=-0.001, allow_nan=False, allow_infinity=False)
        )
    elif corruption == "bad_threshold_high":
        # similarity_threshold > 2
        cfg["similarity_threshold"] = draw(
            st.floats(min_value=2.001, max_value=1e6, allow_nan=False, allow_infinity=False)
        )
    elif corruption == "bad_repo_mode":
        # repo_mode not in ('shared', 'user', 'both')
        cfg["repo_mode"] = draw(
            st.text(min_size=1, max_size=30).filter(
                lambda s: s not in ("shared", "user", "both")
            )
        )

    return cfg


# ---------------------------------------------------------------------------
# Property 9
# ---------------------------------------------------------------------------

# **Validates: Requirements 9.4**
@settings(max_examples=100)
@given(cfg=invalid_config())
def test_invalid_config_rejected(cfg: dict) -> None:
    """validate_config must return errors for every invalid config dict."""
    errors = validate_config(cfg)
    assert len(errors) > 0, f"Expected validation errors for {cfg}"

    # Each error must identify the offending field
    for err in errors:
        assert "field" in err
        assert "message" in err
