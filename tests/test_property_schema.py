# Feature: agent-knowledge-repository, Property 2: Invalid payloads are rejected by schema validation
"""Property-based test: invalid payloads are always rejected by SchemaValidator.

**Validates: Requirements 1.2, 3.3, 5.1, 5.4**
"""

from __future__ import annotations

from hypothesis import given, settings

from akr.errors import ValidationError
from akr.schema import SchemaValidator
from tests.strategies import invalid_artifact


@given(data=invalid_artifact())
@settings(max_examples=100)
def test_invalid_payloads_rejected(data: dict) -> None:
    """Every invalid payload must be rejected with a ValidationError."""
    validator = SchemaValidator()
    try:
        validator.validate(data)
        raise AssertionError(f"Expected ValidationError but validate() succeeded for: {data}")
    except ValidationError:
        pass  # expected
