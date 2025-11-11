"""Template manager for loading and rendering prompt templates."""

from pathlib import Path
from string import Template
from typing import Dict, Any, Optional


class TemplateManager:
    """Manages loading and rendering of prompt templates for MAID agents."""

    def __init__(self, templates_dir: Optional[Path] = None) -> None:
        """Initialize template manager.

        Args:
            templates_dir: Directory containing template files.
                          Defaults to maid_agents/config/templates/
        """
        if templates_dir is None:
            # Default to templates directory relative to this file
            config_dir = Path(__file__).parent
            templates_dir = config_dir / "templates"

        self.templates_dir = Path(templates_dir)
        self._template_cache: Dict[str, Template] = {}

    def load_template(self, template_name: str) -> Template:
        """Load a template from file.

        Args:
            template_name: Name of template file (without .txt extension)

        Returns:
            string.Template object for rendering

        Raises:
            FileNotFoundError: If template file doesn't exist
            ValueError: If template_name is invalid
        """
        if not template_name:
            raise ValueError("template_name cannot be empty")

        # Check cache first
        if template_name in self._template_cache:
            return self._template_cache[template_name]

        # Load from file
        template_path = self.templates_dir / f"{template_name}.txt"
        if not template_path.exists():
            raise FileNotFoundError(
                f"Template not found: {template_path}. "
                f"Available templates: {self.list_templates()}"
            )

        template_content = template_path.read_text(encoding="utf-8")
        template = Template(template_content)

        # Cache for future use
        self._template_cache[template_name] = template

        return template

    def render(self, template_name: str, **kwargs: Any) -> str:
        """Load and render a template with provided variables.

        Args:
            template_name: Name of template file (without .txt extension)
            **kwargs: Variables to substitute in template

        Returns:
            Rendered template string

        Raises:
            FileNotFoundError: If template file doesn't exist
            KeyError: If required template variable is missing
        """
        template = self.load_template(template_name)

        try:
            return template.substitute(**kwargs)
        except KeyError as e:
            missing_var = str(e).strip("'")
            raise KeyError(
                f"Missing required variable '{missing_var}' for template '{template_name}'. "
                f"Provided variables: {list(kwargs.keys())}"
            ) from e

    def render_safe(self, template_name: str, **kwargs: Any) -> str:
        """Load and render a template with safe substitution (allows missing vars).

        Args:
            template_name: Name of template file (without .txt extension)
            **kwargs: Variables to substitute in template

        Returns:
            Rendered template string with $var placeholders for missing variables
        """
        template = self.load_template(template_name)
        return template.safe_substitute(**kwargs)

    def list_templates(self) -> list[str]:
        """List all available template names.

        Returns:
            List of template names (without .txt extension)
        """
        if not self.templates_dir.exists():
            return []

        return [p.stem for p in self.templates_dir.glob("*.txt") if p.is_file()]

    def clear_cache(self) -> None:
        """Clear the template cache."""
        self._template_cache.clear()

    def get_template_path(self, template_name: str) -> Path:
        """Get the full path to a template file.

        Args:
            template_name: Name of template file (without .txt extension)

        Returns:
            Path to template file
        """
        return self.templates_dir / f"{template_name}.txt"


# Singleton instance for easy access
_default_manager: Optional[TemplateManager] = None


def get_template_manager() -> TemplateManager:
    """Get the default template manager instance.

    Returns:
        Singleton TemplateManager instance
    """
    global _default_manager
    if _default_manager is None:
        _default_manager = TemplateManager()
    return _default_manager


def render_template(template_name: str, **kwargs: Any) -> str:
    """Convenience function to render a template using default manager.

    Args:
        template_name: Name of template file (without .txt extension)
        **kwargs: Variables to substitute in template

    Returns:
        Rendered template string
    """
    manager = get_template_manager()
    return manager.render(template_name, **kwargs)
