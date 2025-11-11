"""Context Builder - Prepares context for AI agents."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class AgentContext:
    """Context for AI agent execution.

    Holds all necessary information for an AI agent to perform its task,
    including the manifest data and contents of relevant files.
    """

    manifest_data: dict
    file_contents: dict
    goal: str


class ContextBuilder:
    """Builds context for AI agents from manifests and files.

    This class is responsible for loading and preparing all necessary
    context information that AI agents need to perform their tasks,
    including manifest data and file contents.
    """

    def __init__(self) -> None:
        """Initialize context builder."""
        pass

    def build_from_manifest(self, manifest_path: str) -> AgentContext:
        """Build agent context from manifest file.

        Loads a MAID manifest and all files referenced within it,
        creating a complete context for AI agent execution.

        Args:
            manifest_path: Path to manifest JSON file

        Returns:
            AgentContext with manifest data and loaded files

        Raises:
            FileNotFoundError: If manifest file doesn't exist
            json.JSONDecodeError: If manifest is not valid JSON
        """
        manifest_data = self._load_manifest(manifest_path)

        # Extract and combine all file lists from manifest
        file_paths = self._extract_file_paths(manifest_data)

        # Load contents of all referenced files
        file_contents = self.load_file_contents(file_paths)

        # Extract goal with fallback to empty string
        goal = manifest_data.get("goal", "")

        return AgentContext(
            manifest_data=manifest_data,
            file_contents=file_contents,
            goal=goal,
        )

    def load_file_contents(self, file_paths: list) -> dict:
        """Load contents of multiple files.

        Attempts to read each file in the list. Files that don't exist
        (e.g., files to be created) are marked with None. Read errors
        are captured as error messages.

        Args:
            file_paths: List of file paths to load

        Returns:
            Dict mapping file path to content (or None/error message)
        """
        contents = {}

        for file_path_str in file_paths:
            content = self._read_single_file(file_path_str)
            contents[file_path_str] = content

        return contents

    def _load_manifest(self, manifest_path: str) -> dict:
        """Load and parse manifest JSON file.

        Args:
            manifest_path: Path to the manifest file

        Returns:
            Parsed manifest data as dictionary

        Raises:
            FileNotFoundError: If manifest file doesn't exist
            json.JSONDecodeError: If manifest is not valid JSON
        """
        manifest_file = Path(manifest_path)

        if not manifest_file.exists():
            raise FileNotFoundError(f"Manifest file not found: {manifest_path}")

        with open(manifest_file, "r", encoding="utf-8") as file:
            return json.load(file)

    def _extract_file_paths(self, manifest_data: dict) -> list:
        """Extract all file paths from manifest.

        Combines readonly, editable, and creatable file lists from
        the manifest into a single list.

        Args:
            manifest_data: Parsed manifest dictionary

        Returns:
            Combined list of all file paths
        """
        readonly_files = manifest_data.get("readonlyFiles", [])
        editable_files = manifest_data.get("editableFiles", [])
        creatable_files = manifest_data.get("creatableFiles", [])

        return readonly_files + editable_files + creatable_files

    def _read_single_file(self, file_path_str: str) -> Optional[str]:
        """Read contents of a single file.

        Args:
            file_path_str: Path to the file as string

        Returns:
            File contents if readable, None if doesn't exist,
            or error message if read fails
        """
        file_path = Path(file_path_str)

        # File doesn't exist (likely a creatable file)
        if not file_path.exists():
            return None

        # Path exists but is not a file
        if not file_path.is_file():
            return f"Error reading file: {file_path_str} is not a file"

        # Try to read the file
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                return file.read()
        except PermissionError:
            return f"Error reading file: Permission denied for {file_path_str}"
        except UnicodeDecodeError:
            return f"Error reading file: Unable to decode {file_path_str} as UTF-8"
        except Exception as error:
            return f"Error reading file: {error}"
