#!/usr/bin/env python3
"""
Script to parse tasks.md and generate GitHub issue creation commands.

This script parses the tasks defined in specs/001-excel-postgressql-excel/tasks.md
and generates GitHub CLI commands to create issues for each task.
"""

import re
import sys
from datetime import datetime
from pathlib import Path


class Task:
    """Represents a single implementation task."""
    
    def __init__(self, task_id: str, title: str, phase: str, parallel: bool = False):
        self.task_id = task_id
        self.title = title
        self.phase = phase
        self.parallel = parallel
        self.dependencies: list[str] = []
        self.file_paths: list[str] = []
        self.description = ""
        self.notes = ""

    def __repr__(self):
        return f"Task({self.task_id}: {self.title})"


class TaskParser:
    """Parser for tasks.md file."""
    
    def __init__(self, tasks_file_path: str):
        self.tasks_file_path = Path(tasks_file_path)
        self.tasks: list[Task] = []
        self.dependencies: dict[str, list[str]] = {}
        
    def parse(self) -> list[Task]:
        """Parse the tasks.md file and extract tasks."""
        if not self.tasks_file_path.exists():
            raise FileNotFoundError(f"Tasks file not found: {self.tasks_file_path}")
            
        content = self.tasks_file_path.read_text(encoding='utf-8')
        
        # Parse tasks
        self._parse_tasks(content)
        
        # Parse dependencies
        self._parse_dependencies(content)
        
        return self.tasks
    
    def _parse_tasks(self, content: str) -> None:
        """Extract tasks from the content."""
        # Regex to match task lines: - [ ] T001 [P] Description
        task_pattern = r'^- \[ \] (T\d+)\s*(\[P\])?\s*(.+)$'
        current_phase = ""
        
        lines = content.split('\n')
        for line in lines:
            # Check for phase headers
            if line.startswith('## Phase'):
                current_phase = line.strip()
                continue
                
            # Check for task lines
            match = re.match(task_pattern, line, re.MULTILINE)
            if match:
                task_id = match.group(1)
                parallel_marker = match.group(2)
                title = match.group(3).strip()
                
                is_parallel = parallel_marker == '[P]'
                
                task = Task(task_id, title, current_phase, is_parallel)
                
                # Extract file paths from title
                task.file_paths = self._extract_file_paths(title)
                
                self.tasks.append(task)
    
    def _extract_file_paths(self, title: str) -> list[str]:
        """Extract file paths from task title."""
        # Look for patterns like `src/path/file.py` or `tests/path/file.py`
        file_pattern = r'`([^`]+\.py|[^`]+\.md|[^`]+\.yaml|[^`]+\.yml|[^`]+\.sh)`'
        matches = re.findall(file_pattern, title)
        return matches
    
    def _parse_dependencies(self, content: str) -> None:
        """Parse the dependencies section."""
        # Find dependencies section
        pattern = r'## Dependencies\s*\n\|[^|]+\|\s*\n\|[^|]+\|\s*\n((?:\|[^|]+\|\s*[^|]+\|\s*\n)*)'
        deps_section_match = re.search(pattern, content)
        if not deps_section_match:
            return
            
        deps_content = deps_section_match.group(1)
        
        # Parse dependency table
        for line in deps_content.split('\n'):
            if line.strip() and line.startswith('|'):
                parts = [p.strip() for p in line.split('|') if p.strip()]
                if len(parts) >= 2:
                    task_id = parts[0].strip()
                    deps_str = parts[1].strip()
                    
                    # Parse dependencies (can be comma-separated or ranges)
                    deps = self._parse_dependency_string(deps_str)
                    if deps:
                        self.dependencies[task_id] = deps
                        
                        # Add to corresponding task
                        task = next((t for t in self.tasks if t.task_id == task_id), None)
                        if task:
                            task.dependencies = deps
    
    def _parse_dependency_string(self, deps_str: str) -> list[str]:
        """Parse dependency string like 'T004-T008' or 'T002,T004,T014'."""
        if not deps_str or deps_str == '-':
            return []
            
        deps = []
        
        # Handle ranges like T004-T008
        range_matches = re.findall(r'T(\d+)-T(\d+)', deps_str)
        for start, end in range_matches:
            for i in range(int(start), int(end) + 1):
                deps.append(f'T{i:03d}')
        
        # Handle individual tasks like T002, T014
        individual_matches = re.findall(r'T\d+', deps_str)
        for match in individual_matches:
            if match not in deps:  # Avoid duplicates from ranges
                deps.append(match)
        
        return deps


class IssueGenerator:
    """Generate GitHub issue creation commands."""
    
    def __init__(self, tasks: list[Task], template_path: str):
        self.tasks = tasks
        self.template_path = Path(template_path)
        
    def generate_issue_commands(self, output_file: str) -> None:
        """Generate GitHub CLI commands to create issues."""
        commands = []
        
        for task in self.tasks:
            # Generate issue body from template
            issue_body = self._generate_issue_body(task)
            
            # Generate labels
            labels = self._generate_labels(task)
            
            # Create GitHub CLI command
            title = f"[{task.task_id}] {task.title}"
            
            # Escape quotes and newlines for command line
            escaped_body = issue_body.replace('"', '\\"').replace('\n', '\\n')
            
            labels_str = ",".join(labels)
            cmd = (f'gh issue create --title "{title}" --body "{escaped_body}" '
                   f'--label "{labels_str}"')
            commands.append(cmd)
        
        # Write commands to file
        output_path = Path(output_file)
        output_path.write_text('\n'.join(commands), encoding='utf-8')
        
        print(f"Generated {len(commands)} issue creation commands in {output_file}")
    
    def _generate_issue_body(self, task: Task) -> str:
        """Generate issue body from template."""
        if not self.template_path.exists():
            raise FileNotFoundError(f"Template not found: {self.template_path}")
            
        template = self.template_path.read_text(encoding='utf-8')
        
        # Replace placeholders
        dependencies_str = ', '.join(task.dependencies) if task.dependencies else 'None'
        parallel_status = 'Yes' if task.parallel else 'No'
        files_list = ('\n'.join([f'- `{path}`' for path in task.file_paths]) 
                     if task.file_paths else '- (To be determined)')
        
        body = template.replace('TASK_ID', task.task_id)
        body = body.replace('TASK_TITLE', task.title)
        body = body.replace('TASK_PHASE', task.phase)
        body = body.replace('TASK_DEPENDENCIES', dependencies_str)
        body = body.replace('PARALLEL_STATUS', parallel_status)
        body = body.replace('GENERATION_DATE', datetime.now().strftime('%Y-%m-%d'))
        
        # Replace file list placeholder
        body = body.replace('- `path/to/file.py`', files_list)
        
        return body
    
    def _generate_labels(self, task: Task) -> list[str]:
        """Generate labels for the task."""
        labels = ['task', 'implementation']
        
        # Add phase label
        if 'Setup' in task.phase:
            labels.append('setup')
        elif 'Test' in task.phase:
            labels.append('testing')
        elif 'Model' in task.phase:
            labels.append('models')
        elif 'Core' in task.phase or 'Service' in task.phase:
            labels.append('core')
        elif 'Integration' in task.phase:
            labels.append('integration')
        elif 'Polish' in task.phase or 'Quality' in task.phase:
            labels.append('polish')
        
        # Add parallel label
        if task.parallel:
            labels.append('parallel')
            
        return labels


def main():
    """Main function."""
    if len(sys.argv) > 1:
        tasks_file = sys.argv[1]
    else:
        tasks_file = 'specs/001-excel-postgressql-excel/tasks.md'
    
    template_file = '.github/ISSUE_TEMPLATE/implementation-task.md'
    output_file = 'scripts/create_issues.sh'
    
    try:
        # Parse tasks
        parser = TaskParser(tasks_file)
        tasks = parser.parse()
        
        print(f"Parsed {len(tasks)} tasks from {tasks_file}")
        
        # Generate issue commands
        generator = IssueGenerator(tasks, template_file)
        generator.generate_issue_commands(output_file)
        
        print(f"Issue creation commands written to {output_file}")
        print(f"To create issues, run: chmod +x {output_file} && ./{output_file}")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()