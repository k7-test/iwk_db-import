# Task to GitHub Issues Conversion

This document explains how to convert the implementation tasks defined in `specs/001-excel-postgressql-excel/tasks.md` into GitHub issues for project management and tracking.

## Overview

The Excel -> PostgreSQL bulk import CLI tool project has 40 implementation tasks organized in 6 phases:

- **Phase 3.1**: Setup / Baseline Adjustments (3 tasks)
- **Phase 3.2**: Tests First (Contract / Integration / Performance) (10 tasks)
- **Phase 3.3**: Domain Models (6 tasks)  
- **Phase 3.4**: Core / Services / Infrastructure Enhancements (8 tasks)
- **Phase 3.5**: Integration / Cross-Cutting (3 tasks)
- **Phase 3.6**: Polish / Quality Gates / Docs (10 tasks)

## Files Created

This solution includes:

1. **`.github/ISSUE_TEMPLATE/implementation-task.md`** - GitHub issue template for implementation tasks
2. **`scripts/create_task_issues.py`** - Python script to parse tasks.md and generate issue creation commands  
3. **`scripts/create_issues.sh`** - Generated shell script with GitHub CLI commands (auto-generated)
4. **`scripts/batch_create_issues.sh`** - Interactive batch script to create all issues
5. **`docs/task-to-issue-conversion.md`** - This documentation

## Prerequisites

Before creating GitHub issues, ensure you have:

1. **GitHub CLI (gh)** installed and authenticated
   ```bash
   # Install GitHub CLI (if not already installed)
   # macOS: brew install gh
   # Ubuntu: apt install gh
   # Windows: choco install gh
   
   # Authenticate with GitHub
   gh auth login
   ```

2. **Repository access** - You need write access to create issues

## Usage

### Option 1: Automated Batch Creation (Recommended)

```bash
# From repository root
./scripts/batch_create_issues.sh
```

This interactive script will:
- Generate issue creation commands
- Show a confirmation prompt
- Create all 40 GitHub issues with proper labels and structure

### Option 2: Manual Steps

```bash
# 1. Generate the issue creation commands
python scripts/create_task_issues.py

# 2. Review the generated script (optional)
less scripts/create_issues.sh

# 3. Execute the commands
chmod +x scripts/create_issues.sh
./scripts/create_issues.sh
```

### Option 3: Individual Issue Creation

```bash
# Generate commands
python scripts/create_task_issues.py

# Execute single commands from scripts/create_issues.sh
# Example:
gh issue create --title "[T001] Verify current structure..." --body "..." --label "task,implementation,setup"
```

## Generated Issue Structure

Each GitHub issue will include:

- **Title**: `[TASK_ID] Description` (e.g., `[T001] Verify current structure...`)
- **Labels**: Automatically assigned based on phase and characteristics:
  - `task` - All issues
  - `implementation` - All issues  
  - Phase-specific: `setup`, `testing`, `models`, `core`, `integration`, `polish`
  - `parallel` - For tasks that can run in parallel
- **Body**: Structured content including:
  - Task description placeholder
  - Phase information
  - Dependencies (parsed from tasks.md)
  - File paths to modify/create
  - Parallel execution status
  - Acceptance criteria
  - Definition of done

## Task Dependencies

The script automatically parses task dependencies from the dependency table in `tasks.md` and includes them in the issue body. This helps with project planning and sequencing.

## Labels and Organization

Issues are automatically labeled for easy filtering:

- **By Phase**: `setup`, `testing`, `models`, `core`, `integration`, `polish`
- **By Type**: `task`, `implementation`
- **By Execution**: `parallel` (for tasks that can run concurrently)

## Verification

After creating issues, verify:

1. **Issue Count**: Should have 40 issues total
2. **Labels**: Each issue should have appropriate labels
3. **Dependencies**: Check a few issues to ensure dependencies are correctly listed
4. **Structure**: Verify issue body follows the template format

## Troubleshooting

### GitHub CLI Not Authenticated
```bash
gh auth login
# Follow the prompts to authenticate with GitHub
```

### Permission Denied
Ensure you have write access to the repository to create issues.

### Script Execution Issues
```bash
# Make sure scripts are executable
chmod +x scripts/batch_create_issues.sh scripts/create_task_issues.py

# Run with explicit python if needed
python3 scripts/create_task_issues.py
```

### Large Number of Issues
Creating 40 issues at once might trigger rate limiting. If this occurs:
- Wait a few minutes between batches
- Use GitHub's web interface to create issues manually using the generated commands as reference

## Customization

### Modifying the Issue Template
Edit `.github/ISSUE_TEMPLATE/implementation-task.md` to customize:
- Issue structure
- Acceptance criteria
- Additional fields

### Changing Labels
Modify the `_generate_labels()` method in `scripts/create_task_issues.py` to:
- Add new label categories
- Change label naming conventions
- Add custom labels based on task content

### Adding Custom Fields
Extend `scripts/create_task_issues.py` to:
- Parse additional task metadata
- Add custom issue body sections
- Include estimated effort or priority

## Integration with Project Management

Once issues are created, you can:

1. **Create Milestones** for each phase
2. **Assign Issues** to team members
3. **Create Project Boards** to track progress
4. **Link Issues** to pull requests for automatic closure
5. **Use Labels** for filtering and reporting

## Maintenance

When `tasks.md` is updated:
1. Re-run the script to generate updated commands
2. Compare with existing issues
3. Create new issues for added tasks
4. Update existing issues if task descriptions change

---

**Note**: This conversion tool is designed specifically for the Excel -> PostgreSQL import CLI project structure. Adapt the parsing logic if your tasks.md format differs significantly.