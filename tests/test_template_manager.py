"""Comprehensive tests for template_manager.py."""

import pytest
import sys
from pathlib import Path
from string import Template

sys.path.insert(0, str(Path(__file__).parent.parent))

from maid_agents.config.template_manager import (
    TemplateManager,
    get_template_manager,
    render_template,
)


def test_template_manager_instantiation():
    """Test TemplateManager can be instantiated."""
    manager = TemplateManager()
    assert manager is not None
    assert isinstance(manager, TemplateManager)


def test_template_manager_with_custom_directory():
    """Test TemplateManager with custom templates directory."""
    manager = TemplateManager(templates_dir=Path("maid_agents/config/templates"))
    assert manager.templates_dir.exists()


def test_load_template_success():
    """Test loading an existing template."""
    manager = TemplateManager()
    template = manager.load_template("manifest_creation")
    assert template is not None
    assert isinstance(template, Template)


def test_load_template_not_found():
    """Test loading non-existent template raises FileNotFoundError."""
    manager = TemplateManager()
    with pytest.raises(FileNotFoundError) as exc_info:
        manager.load_template("nonexistent_template")
    assert "Template not found" in str(exc_info.value)
    assert "nonexistent_template" in str(exc_info.value)


def test_load_template_empty_name():
    """Test loading template with empty name raises ValueError."""
    manager = TemplateManager()
    with pytest.raises(ValueError) as exc_info:
        manager.load_template("")
    assert "template_name cannot be empty" in str(exc_info.value)


def test_render_template_with_variables():
    """Test rendering template with variable substitution."""
    manager = TemplateManager()
    result = manager.render("manifest_creation", goal="Test goal", task_number="001")
    assert isinstance(result, str)
    assert len(result) > 0
    assert "Test goal" in result
    assert "001" in result


def test_render_template_missing_variable():
    """Test rendering template with missing required variable raises KeyError."""
    manager = TemplateManager()
    with pytest.raises(KeyError) as exc_info:
        manager.render("manifest_creation", goal="Test")  # Missing task_number
    assert "Missing required variable" in str(exc_info.value)
    assert "task_number" in str(exc_info.value)


def test_render_safe_allows_missing_variables():
    """Test render_safe allows missing variables."""
    manager = TemplateManager()
    result = manager.render_safe("manifest_creation", goal="Test")
    assert isinstance(result, str)
    assert "Test" in result
    # Should have $task_number placeholder still in output
    assert "$task_number" in result or "${task_number}" in result


def test_list_templates():
    """Test listing available templates."""
    manager = TemplateManager()
    templates = manager.list_templates()
    assert isinstance(templates, list)
    assert (
        len(templates) >= 3
    )  # At least manifest_creation, test_generation, implementation
    assert "manifest_creation" in templates
    assert "test_generation" in templates
    assert "implementation" in templates


def test_list_templates_includes_new_templates():
    """Test list_templates includes refactor and refine templates."""
    manager = TemplateManager()
    templates = manager.list_templates()
    assert "refactor" in templates
    assert "refine" in templates


def test_template_cache():
    """Test template caching works."""
    manager = TemplateManager()

    # Load template first time
    template1 = manager.load_template("manifest_creation")

    # Load same template again - should come from cache
    template2 = manager.load_template("manifest_creation")

    # Should be the exact same object (cached)
    assert template1 is template2


def test_clear_cache():
    """Test clearing template cache."""
    manager = TemplateManager()

    # Load template to populate cache
    template1 = manager.load_template("manifest_creation")

    # Clear cache
    manager.clear_cache()

    # Load again - should be a new object
    template2 = manager.load_template("manifest_creation")

    # Should not be the same object (cache was cleared)
    assert template1 is not template2


def test_get_template_path():
    """Test getting full template path."""
    manager = TemplateManager()
    path = manager.get_template_path("manifest_creation")
    assert isinstance(path, Path)
    assert str(path).endswith("manifest_creation.txt")


def test_get_template_manager_singleton():
    """Test get_template_manager returns singleton instance."""
    manager1 = get_template_manager()
    manager2 = get_template_manager()

    # Should be the same instance (singleton)
    assert manager1 is manager2


def test_render_template_convenience_function():
    """Test convenience render_template function."""
    result = render_template("manifest_creation", goal="Test goal", task_number="042")
    assert isinstance(result, str)
    assert "Test goal" in result
    assert "042" in result


def test_all_required_templates_exist():
    """Test all required templates are present."""
    manager = TemplateManager()
    required_templates = [
        "manifest_creation",
        "test_generation",
        "implementation",
        "refactor",
        "refine",
    ]

    for template_name in required_templates:
        # Should not raise FileNotFoundError
        template = manager.load_template(template_name)
        assert template is not None


def test_manifest_creation_template_has_expected_placeholders():
    """Test manifest_creation template has required placeholders."""
    manager = TemplateManager()
    template = manager.load_template("manifest_creation")
    template_content = template.template

    # Should have goal and task_number placeholders
    assert "$goal" in template_content or "${goal}" in template_content
    assert "$task_number" in template_content or "${task_number}" in template_content


def test_test_generation_template_has_expected_placeholders():
    """Test test_generation template has required placeholders."""
    manager = TemplateManager()
    template = manager.load_template("test_generation")
    template_content = template.template

    # Should have required placeholders
    assert (
        "$manifest_path" in template_content or "${manifest_path}" in template_content
    )
    assert "$goal" in template_content or "${goal}" in template_content
    assert (
        "$artifacts_summary" in template_content
        or "${artifacts_summary}" in template_content
    )


def test_implementation_template_has_expected_placeholders():
    """Test implementation template has required placeholders."""
    manager = TemplateManager()
    template = manager.load_template("implementation")
    template_content = template.template

    # Should have required placeholders
    assert (
        "$manifest_path" in template_content or "${manifest_path}" in template_content
    )
    assert "$goal" in template_content or "${goal}" in template_content
    assert "$test_output" in template_content or "${test_output}" in template_content


def test_refactor_template_has_expected_placeholders():
    """Test refactor template has required placeholders."""
    manager = TemplateManager()
    template = manager.load_template("refactor")
    template_content = template.template

    # Should have required placeholders
    assert "$goal" in template_content or "${goal}" in template_content
    assert (
        "$file_contents" in template_content or "${file_contents}" in template_content
    )


def test_refine_template_has_expected_placeholders():
    """Test refine template has required placeholders."""
    manager = TemplateManager()
    template = manager.load_template("refine")
    template_content = template.template

    # Should have required placeholders
    assert (
        "$refinement_goal" in template_content
        or "${refinement_goal}" in template_content
    )
    assert (
        "$manifest_json" in template_content or "${manifest_json}" in template_content
    )
    assert (
        "$test_contents" in template_content or "${test_contents}" in template_content
    )
    assert (
        "$validation_feedback" in template_content
        or "${validation_feedback}" in template_content
    )
