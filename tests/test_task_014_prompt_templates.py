"""Behavioral tests for Task-014: Prompt Templates."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def test_manifest_creation_template_exists():
    """Test manifest_creation.txt template exists."""
    template_path = Path("maid_agents/config/templates/manifest_creation.txt")
    assert template_path.exists()

    content = template_path.read_text()
    assert len(content) > 0
    assert "manifest" in content.lower() or "MAID" in content


def test_test_generation_template_exists():
    """Test test_generation.txt template exists."""
    template_path = Path("maid_agents/config/templates/test_generation.txt")
    assert template_path.exists()

    content = template_path.read_text()
    assert len(content) > 0
    assert "test" in content.lower()


def test_implementation_template_exists():
    """Test implementation.txt template exists."""
    template_path = Path("maid_agents/config/templates/implementation.txt")
    assert template_path.exists()

    content = template_path.read_text()
    assert len(content) > 0
    assert "implement" in content.lower() or "code" in content.lower()


def test_refactor_template_exists():
    """Test refactor.txt template exists."""
    template_path = Path("maid_agents/config/templates/refactor.txt")
    assert template_path.exists()

    content = template_path.read_text()
    assert len(content) > 0
    assert "refactor" in content.lower() or "improve" in content.lower()


def test_refine_template_exists():
    """Test refine.txt template exists."""
    template_path = Path("maid_agents/config/templates/refine.txt")
    assert template_path.exists()

    content = template_path.read_text()
    assert len(content) > 0
    assert "refine" in content.lower() or "improve" in content.lower()


def test_templates_have_substantial_content():
    """Test templates are not just stubs but have substantial guidance."""
    template_dir = Path("maid_agents/config/templates")
    templates = ["manifest_creation.txt", "test_generation.txt", "implementation.txt"]

    for template_name in templates:
        template_path = template_dir / template_name
        content = template_path.read_text()
        # Should have at least 1000 characters of guidance (not bare minimum)
        assert len(content) > 1000, f"{template_name} should have substantial content"


def test_templates_use_variable_placeholders():
    """Test templates use ${variable} placeholders for substitution."""
    template_dir = Path("maid_agents/config/templates")

    # Check manifest_creation has goal and task_number
    manifest_content = (template_dir / "manifest_creation.txt").read_text()
    assert "${goal}" in manifest_content or "$goal" in manifest_content
    assert "${task_number}" in manifest_content or "$task_number" in manifest_content

    # Check test_generation has required placeholders
    test_content = (template_dir / "test_generation.txt").read_text()
    assert "${manifest_path}" in test_content or "$manifest_path" in test_content
    assert (
        "${artifacts_summary}" in test_content or "$artifacts_summary" in test_content
    )


def test_templates_have_examples():
    """Test templates include examples to guide AI generation."""
    template_dir = Path("maid_agents/config/templates")

    # Check that templates have "example" sections
    for template_name in [
        "manifest_creation.txt",
        "test_generation.txt",
        "implementation.txt",
    ]:
        content = (template_dir / template_name).read_text().lower()
        assert "example" in content, f"{template_name} should have examples"
