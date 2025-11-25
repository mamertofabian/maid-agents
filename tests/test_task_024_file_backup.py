"""
Behavioral tests for Task-024: File Backup/Restore for Retry Loops

Tests the FileBackupManager class in isolation to ensure proper backup,
restore, and cleanup operations.
"""

from pathlib import Path
from maid_agents.core.file_backup import FileBackupManager


class TestFileBackupManager:
    """Test FileBackupManager backup/restore/cleanup operations."""

    def test_backup_creates_temp_directory(self, tmp_path):
        """Test that backup_files creates a temporary directory."""
        # Create a test file
        test_file = tmp_path / "test.py"
        test_file.write_text("original content")

        # Backup the file
        manager = FileBackupManager(dry_run=False)
        manager.backup_files([str(test_file)])

        # Verify backup is active and temp dir exists
        assert manager.is_active()

        # Cleanup
        manager.cleanup()

    def test_backup_copies_existing_files(self, tmp_path):
        """Test that backup_files copies existing files to temp directory."""
        # Create test files
        file1 = tmp_path / "file1.py"
        file2 = tmp_path / "file2.py"
        file1.write_text("content 1")
        file2.write_text("content 2")

        # Backup files
        manager = FileBackupManager(dry_run=False)
        manager.backup_files([str(file1), str(file2)])

        # Modify original files
        file1.write_text("modified 1")
        file2.write_text("modified 2")

        # Restore should bring back originals
        manager.restore_files()

        assert file1.read_text() == "content 1"
        assert file2.read_text() == "content 2"

        manager.cleanup()

    def test_backup_handles_nonexistent_files(self, tmp_path):
        """Test that backup_files handles non-existent files gracefully."""
        # File doesn't exist yet
        test_file = tmp_path / "nonexistent.py"

        # Backup should not fail
        manager = FileBackupManager(dry_run=False)
        manager.backup_files([str(test_file)])

        # File is tracked but not backed up
        assert manager.is_active()

        manager.cleanup()

    def test_restore_replaces_modified_files(self, tmp_path):
        """Test that restore_files replaces modified files with originals."""
        # Create and backup file
        test_file = tmp_path / "test.py"
        test_file.write_text("original")

        manager = FileBackupManager(dry_run=False)
        manager.backup_files([str(test_file)])

        # Modify file
        test_file.write_text("modified")
        assert test_file.read_text() == "modified"

        # Restore original
        manager.restore_files()
        assert test_file.read_text() == "original"

        manager.cleanup()

    def test_restore_deletes_new_files(self, tmp_path):
        """Test that restore_files deletes files created after backup."""
        # Create existing file
        existing_file = tmp_path / "existing.py"
        existing_file.write_text("original")

        # Prepare path for new file (doesn't exist yet)
        new_file = tmp_path / "new.py"

        # Backup both files - existing file will be backed up, new file will be tracked
        manager = FileBackupManager(dry_run=False)
        manager.backup_files([str(existing_file), str(new_file)])

        # Create new file after backup (simulate failed iteration creating file)
        new_file.write_text("should be deleted")

        # Verify new file exists
        assert new_file.exists()

        # Restore should delete new file
        manager.restore_files()

        # New file should be gone since it didn't exist during backup
        assert not new_file.exists()
        # Existing file should still be there
        assert existing_file.exists()

        manager.cleanup()

    def test_cleanup_removes_backup_directory(self, tmp_path):
        """Test that cleanup removes backup directory."""
        test_file = tmp_path / "test.py"
        test_file.write_text("content")

        manager = FileBackupManager(dry_run=False)
        manager.backup_files([str(test_file)])

        # Backup should be active
        assert manager.is_active()

        # Cleanup
        manager.cleanup()

        # Backup should be inactive
        assert not manager.is_active()

    def test_cleanup_is_idempotent(self, tmp_path):
        """Test that cleanup can be called multiple times safely."""
        test_file = tmp_path / "test.py"
        test_file.write_text("content")

        manager = FileBackupManager(dry_run=False)
        manager.backup_files([str(test_file)])

        # Call cleanup multiple times
        manager.cleanup()
        manager.cleanup()
        manager.cleanup()

        # Should not raise exception
        assert not manager.is_active()

    def test_dry_run_mode_no_operations(self, tmp_path):
        """Test that dry_run mode skips actual file operations."""
        test_file = tmp_path / "test.py"
        test_file.write_text("original")

        # Backup in dry run mode
        manager = FileBackupManager(dry_run=True)
        manager.backup_files([str(test_file)])

        # Modify file
        test_file.write_text("modified")

        # Restore in dry run mode - should not actually restore
        manager.restore_files()

        # File should still be modified (restore was skipped)
        assert test_file.read_text() == "modified"

        # Cleanup should also be no-op
        manager.cleanup()

    def test_multiple_files_backup_and_restore(self, tmp_path):
        """Test backup and restore with multiple files."""
        # Create multiple files
        files = []
        for i in range(5):
            file_path = tmp_path / f"file{i}.py"
            file_path.write_text(f"content {i}")
            files.append(str(file_path))

        # Backup all files
        manager = FileBackupManager(dry_run=False)
        manager.backup_files(files)

        # Modify all files
        for i, file_path_str in enumerate(files):
            Path(file_path_str).write_text(f"modified {i}")

        # Restore all files
        manager.restore_files()

        # Verify all restored
        for i, file_path_str in enumerate(files):
            assert Path(file_path_str).read_text() == f"content {i}"

        manager.cleanup()

    def test_restore_can_be_called_multiple_times(self, tmp_path):
        """Test that restore_files can be called multiple times (for multiple retries)."""
        test_file = tmp_path / "test.py"
        test_file.write_text("original")

        manager = FileBackupManager(dry_run=False)
        manager.backup_files([str(test_file)])

        # First modification and restore
        test_file.write_text("modified 1")
        manager.restore_files()
        assert test_file.read_text() == "original"

        # Second modification and restore
        test_file.write_text("modified 2")
        manager.restore_files()
        assert test_file.read_text() == "original"

        # Third modification and restore
        test_file.write_text("modified 3")
        manager.restore_files()
        assert test_file.read_text() == "original"

        manager.cleanup()

    def test_backup_with_nonexistent_then_create(self, tmp_path):
        """Test backing up nonexistent file, creating it, then restoring."""
        test_file = tmp_path / "new.py"
        # File doesn't exist

        manager = FileBackupManager(dry_run=False)
        manager.backup_files([str(test_file)])

        # Create the file (simulating first iteration)
        test_file.write_text("created content")
        assert test_file.exists()

        # Restore should delete it (since it didn't exist during backup)
        manager.restore_files()
        assert not test_file.exists()

        manager.cleanup()
