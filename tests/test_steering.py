"""Tests for the steering file structure and content."""

import os
from pathlib import Path

import pytest

STEERING_FILE = Path(".kiro/steering/agent-knowledge.md")


@pytest.fixture
def steering_content():
    """Read the steering file content once for all tests."""
    assert STEERING_FILE.exists(), f"Steering file not found at {STEERING_FILE}"
    return STEERING_FILE.read_text(encoding="utf-8")


class TestSteeringFileExists:
    def test_file_exists_at_expected_path(self):
        assert STEERING_FILE.exists(), (
            f"Expected steering file at {STEERING_FILE}"
        )

    def test_file_is_in_kiro_steering_directory(self):
        assert STEERING_FILE.parent == Path(".kiro/steering")


class TestSteeringFrontmatter:
    def test_contains_inclusion_auto_directive(self, steering_content: str):
        # Frontmatter is delimited by --- lines
        assert steering_content.startswith("---"), (
            "Steering file must start with YAML frontmatter delimiter '---'"
        )
        # Extract frontmatter block
        parts = steering_content.split("---", 2)
        assert len(parts) >= 3, "Steering file must have closing '---' for frontmatter"
        frontmatter = parts[1]
        assert "inclusion: auto" in frontmatter, (
            "Frontmatter must contain 'inclusion: auto'"
        )


class TestSteeringCommandReferences:
    """Verify all five akr-* commands are referenced."""

    @pytest.mark.parametrize("command", [
        "akr-fetch",
        "akr-commit",
        "akr-update",
        "akr-delete",
        "akr-list",
    ])
    def test_contains_command_reference(self, steering_content: str, command: str):
        assert command in steering_content, (
            f"Steering file must reference '{command}'"
        )


class TestSteeringTaggingGuidance:
    def test_contains_tagging_section(self, steering_content: str):
        assert "Tagging" in steering_content or "tag" in steering_content.lower(), (
            "Steering file must contain tagging guidance"
        )

    @pytest.mark.parametrize("tag", [
        "architecture",
        "bug-fix",
        "pattern",
        "dependency",
        "configuration",
    ])
    def test_contains_tag_category(self, steering_content: str, tag: str):
        assert tag in steering_content, (
            f"Steering file must reference tag category '{tag}'"
        )


class TestSteeringDeleteGuidance:
    def test_contains_delete_section(self, steering_content: str):
        assert "When to Delete" in steering_content, (
            "Steering file must contain 'When to Delete Knowledge' section"
        )

    def test_references_akr_delete_in_guidance(self, steering_content: str):
        assert "akr-delete" in steering_content, (
            "Steering file must reference akr-delete command in guidance"
        )
