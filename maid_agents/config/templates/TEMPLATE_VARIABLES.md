# Template Variable Requirements

This document lists the required variables for each split template to prevent template rendering errors.

## User Templates

### manifest_creation_user.txt
- `task_number` - Task number (e.g., "001")
- `goal` - Task goal description
- `additional_instructions_section` - Optional instructions section (formatted or empty string)

### test_generation_user.txt
- `manifest_path` - Path to manifest file
- `goal` - Task goal
- `artifacts_summary` - Summary of expected artifacts
- `files_to_test` - List of files being tested
- `test_file_path` - Path where test file should be created

### implementation_user.txt
- `manifest_path` - Path to manifest file
- `goal` - Task goal
- `test_output` - Test failure output
- `artifacts_summary` - Summary of expected artifacts
- `files_to_modify` - List of files to create/edit
- `additional_instructions_section` - Optional instructions section (formatted or empty string)

### refactor_user.txt
- `manifest_path` - Path to manifest file
- `goal` - Task goal
- `files_to_refactor` - Formatted list of files with contents
- `test_file` - Path to test file that must pass
- `additional_instructions_section` - Optional instructions section (formatted or empty string)

### refine_user.txt
- `manifest_path` - Path to manifest file
- `test_file_path` - Path to test file
- `goal` - Refinement goal
- `validation_errors` - Validation error messages
- `additional_instructions_section` - Optional instructions section (formatted or empty string)

### test_generation_from_implementation_user.txt
- `implementation_file` - Path to existing implementation
- `manifest_path` - Path to manifest file
- `test_file_path` - Path where test file should be created
- `test_mode` - Mode ("create new", "enhance stub", "improve existing")
- `test_mode_instructions` - Mode-specific instructions
- `artifacts_summary` - Summary of expected artifacts

## Common Issues

1. **Missing variables**: Agent doesn't pass all required variables → KeyError
2. **Wrong variable names**: Agent passes `file_contents` but template expects `files_to_refactor`
3. **Test coverage**: Tests use try/except that swallows errors, preventing detection

## Testing Strategy

Tests should:
1. Actually render templates with real variables (not just check method existence)
2. Validate that KeyError is raised for missing variables
3. Test with minimal viable variable sets
