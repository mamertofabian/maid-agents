"""
File backup and restore manager for MAID workflow retry loops.

This module provides the FileBackupManager class which handles backing up files
before retry loops, restoring them before each retry iteration, and cleaning up
temporary backup directories.
"""

import shutil
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Set
import logging

logger = logging.getLogger(__name__)


class FileBackupManager:
    """Manages file backup and restore operations for MAID workflow retry loops.

    Uses Python's tempfile module to create temporary backup directories and
    manages the complete lifecycle of file backups during iterative workflows.

    Attributes:
        dry_run: If True, skips actual file operations (for testing)
        _backup_dir: Path to temporary backup directory
        _backed_up_files: Maps original file path to backup file path
        _files_existed: Set of files that existed before backup
        _is_active: Whether backup is currently active
    """

    def __init__(self, dry_run: bool = False) -> None:
        """Initialize FileBackupManager.

        Args:
            dry_run: If True, log operations without executing them
        """
        self.dry_run = dry_run
        self._backup_dir: Optional[Path] = None
        self._backed_up_files: Dict[str, Path] = {}
        self._files_existed: Set[str] = set()
        self._is_active = False

    def backup_files(self, file_paths: List[str]) -> None:
        """Backup specified files to temporary directory.

        Creates a temporary directory and copies existing files to it.
        Tracks which files existed before backup for proper restoration.

        Args:
            file_paths: List of file paths to backup

        Raises:
            OSError: If backup directory creation fails
        """
        if self.dry_run:
            logger.info(f"[DRY RUN] Would backup {len(file_paths)} files")
            return

        # Create temp directory for backups
        if self._backup_dir is None:
            self._backup_dir = Path(tempfile.mkdtemp(prefix="maid_backup_"))
            logger.debug(f"Created backup directory: {self._backup_dir}")

        # Backup each file that exists
        for file_path_str in file_paths:
            self._backup_single_file(file_path_str)

        self._is_active = True
        logger.info(f"Backed up {len(self._backed_up_files)} existing files")

    def _backup_single_file(self, file_path_str: str) -> None:
        """Backup a single file to the backup directory.

        Args:
            file_path_str: Path to file to backup
        """
        source_path = Path(file_path_str).resolve()

        # Check if file exists
        if not source_path.exists():
            logger.debug(
                f"File does not exist yet, will track for cleanup: {source_path}"
            )
            # Track in backed_up_files with None value to indicate it didn't exist
            self._backed_up_files[str(source_path)] = None
            return

        # Track that this file existed
        self._files_existed.add(str(source_path))

        # Create backup path (preserve directory structure)
        backup_path = self._backup_dir / source_path.name

        # Copy file to backup
        try:
            shutil.copy2(source_path, backup_path)
            self._backed_up_files[str(source_path)] = backup_path
            logger.debug(f"Backed up: {source_path} -> {backup_path}")
        except Exception as e:
            logger.error(f"Failed to backup {source_path}: {e}")
            # Continue with other files

    def restore_files(self) -> None:
        """Restore files from backup to original locations.

        Copies backed up files back to their original locations and deletes
        any files that didn't exist before the backup (cleanup new files from
        failed iterations).

        This method can be called multiple times (for multiple retries).
        """
        if self.dry_run:
            logger.info("[DRY RUN] Would restore files from backup")
            return

        if not self._is_active:
            logger.debug("No active backup, skipping restore")
            return

        # Restore each backed up file
        for original_path_str, backup_path in self._backed_up_files.items():
            self._restore_single_file(original_path_str, backup_path)

        # Delete files that didn't exist before backup
        self._cleanup_new_files()

        logger.info(f"Restored {len(self._backed_up_files)} files from backup")

    def _restore_single_file(
        self, original_path_str: str, backup_path: Optional[Path]
    ) -> None:
        """Restore a single file from backup.

        Args:
            original_path_str: Path to original file location
            backup_path: Path to backup file (None if file didn't exist originally)
        """
        original_path = Path(original_path_str)

        # If backup_path is None, file didn't exist originally - delete it if it exists now
        if backup_path is None:
            if original_path.exists():
                try:
                    original_path.unlink()
                    logger.debug(
                        f"Deleted new file (didn't exist before backup): {original_path}"
                    )
                except Exception as e:
                    logger.error(f"Failed to delete new file {original_path}: {e}")
            return

        try:
            # Ensure parent directory exists
            original_path.parent.mkdir(parents=True, exist_ok=True)

            # Copy backup back to original location
            shutil.copy2(backup_path, original_path)
            logger.debug(f"Restored: {backup_path} -> {original_path}")
        except Exception as e:
            logger.error(f"Failed to restore {original_path}: {e}")
            # Continue with other files

    def _cleanup_new_files(self) -> None:
        """Delete files that didn't exist before backup.

        This removes files created during a failed iteration.
        Note: This is now handled in _restore_single_file, but kept for
        backwards compatibility.
        """
        # This method is now a no-op since cleanup is handled in _restore_single_file
        pass

    def cleanup(self) -> None:
        """Remove backup directory and reset state.

        This method is idempotent and safe to call multiple times.
        Handles cleanup failures gracefully by logging warnings.
        """
        if self.dry_run:
            logger.info("[DRY RUN] Would cleanup backup directory")
            return

        if self._backup_dir is not None and self._backup_dir.exists():
            try:
                shutil.rmtree(self._backup_dir)
                logger.debug(f"Removed backup directory: {self._backup_dir}")
            except Exception as e:
                logger.warning(f"Failed to remove backup directory: {e}")
                # OS will eventually clean temp directory

        # Reset state
        self._backup_dir = None
        self._backed_up_files = {}
        self._files_existed = set()
        self._is_active = False

    def is_active(self) -> bool:
        """Check if backup is currently active.

        Returns:
            True if backup is active, False otherwise
        """
        return self._is_active
