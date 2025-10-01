#!/bin/bash
#
# Batch script to create GitHub issues from tasks.md
# 
# Prerequisites:
# 1. GitHub CLI (gh) must be installed and authenticated
# 2. Run this script from the repository root
#
# Usage:
#   ./scripts/batch_create_issues.sh

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "Creating GitHub issues from tasks.md..."
echo "Repository: $(git remote get-url origin)"
echo "Current branch: $(git branch --show-current)"
echo

# Check if gh is installed and authenticated
if ! command -v gh &> /dev/null; then
    echo "Error: GitHub CLI (gh) is not installed."
    echo "Please install it from: https://cli.github.com/"
    exit 1
fi

if ! gh auth status &> /dev/null; then
    echo "Error: GitHub CLI is not authenticated."
    echo "Please run: gh auth login"
    exit 1
fi

# Generate the issue creation script
echo "Generating issue creation commands..."
python scripts/create_task_issues.py

# Make the generated script executable
chmod +x scripts/create_issues.sh

# Confirm before creating issues
echo "Generated 40 issue creation commands."
echo
read -p "Do you want to create all 40 issues? This will create GitHub issues for each task. (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled. You can manually run: ./scripts/create_issues.sh"
    exit 0
fi

echo
echo "Creating GitHub issues..."

# Execute the generated script with error handling
set +e
./scripts/create_issues.sh
exit_code=$?
set -e

if [ $exit_code -eq 0 ]; then
    echo
    echo "✅ Successfully created all GitHub issues!"
    echo "View issues at: https://github.com/$(gh repo view --json owner,name --jq '.owner.login + "/" + .name')/issues"
else
    echo
    echo "❌ Some issues may have failed to create. Check the output above."
    echo "You can retry individual commands from scripts/create_issues.sh"
    exit $exit_code
fi