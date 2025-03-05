"""
Standalone Dependency Tracker

This module provides core functionality for analyzing and tracking dependencies in Python projects.
It identifies imports between files and helps manage module dependencies without modifying existing code.

Usage:
    Import this module to track dependencies in your project builder or use the standalone
    dependency_checker.py script to check existing projects.
"""

import os
import ast
import sys
import json
import re
import importlib.util
from pathlib import Path
from typing import Dict, Set, List, Tuple, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class Dependency:
    """Represents a single dependency."""
    module_name: str  # The name of the imported module (e.g., "flask")
    source_file: str  # The file that contains the import
    import_type: str = "import"  # "import" or "from-import"
    is_builtin: bool = False  # Whether it's a Python built-in
    is_external: bool = False  # Whether it's an external package
    is_project_module: bool = False  # Whether it's part of the project
    resolved: bool = False  # Whether the dependency is resolved
    priority: int = 1  # Priority for resolution (higher = more important)
    
    def __hash__(self):
        """Make Dependency hashable."""
        return hash((self.module_name, self.source_file, self.import_type))


@dataclass
class DependencyGraph:
    """Tracks all dependencies across the project as it's being generated."""
    project_root: str
    dependencies: Set[Dependency] = field(default_factory=set)
    file_dependencies: Dict[str, Set[str]] = field(default_factory=dict)  # Maps file -> set of files it depends on
    modules_to_files: Dict[str, Set[str]] = field(default_factory=dict)  # Maps module name -> set of files that implement it
    unresolved_dependencies: Set[Dependency] = field(default_factory=set)
    
    # Standard library modules to ignore
    STDLIB_MODULES: Set[str] = field(default_factory=lambda: {
        "abc", "argparse", "ast", "asyncio", "base64", "collections", "configparser",
        "contextlib", "copy", "csv", "dataclasses", "datetime", "decimal", "difflib",
        "enum", "functools", "glob", "hashlib", "hmac", "http", "importlib", "inspect",
        "io", "itertools", "json", "logging", "math", "multiprocessing", "os", "pathlib",
        "pickle", "platform", "pprint", "re", "secrets", "shutil", "signal", "socket",
        "sqlite3", "statistics", "string", "subprocess", "sys", "tempfile", "textwrap",
        "threading", "time", "traceback", "typing", "unicodedata", "unittest", "urllib",
        "uuid", "warnings", "weakref", "xml", "zipfile", "zlib"
    })
    
    def parse_file_dependencies(self, file_path: str, file_content: str) -> List[Dependency]:
        """
        Parse a file to extract its dependencies.
        
        Args:
            file_path: The relative path of the file
            file_content: The content of the file
            
        Returns:
            List of Dependency objects
        """
        file_dependencies = []
        try:
            # For Python files
            if file_path.endswith('.py'):
                tree = ast.parse(file_content)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for name in node.names:
                            module_name = name.name.split('.')[0]
                            dep = self._create_dependency(module_name, file_path, "import")
                            if dep:
                                file_dependencies.append(dep)
                    
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            module_name = node.module.split('.')[0]
                            dep = self._create_dependency(module_name, file_path, "from-import")
                            if dep:
                                file_dependencies.append(dep)
            
            # For JavaScript files
            elif file_path.endswith(('.js', '.jsx', '.ts', '.tsx')):
                # Simple regex-based approach for JS imports
                # Match ES6 imports
                # import X from 'Y' or import { X } from 'Y'
                es6_import_pattern = r"import\s+(?:{[^}]*}|\*\s+as\s+\w+|\w+)\s+from\s+['\"]([^'\"]+)['\"]"
                
                # Match require statements
                # const X = require('Y')
                require_pattern = r"(?:const|let|var)\s+(?:{[^}]*}|\w+)\s*=\s*require\s*\(\s*['\"]([^'\"]+)['\"]"
                
                for match in re.finditer(es6_import_pattern, file_content):
                    module_name = match.group(1).split('/')[0]
                    if module_name.startswith('.'):  # Relative import
                        continue
                    dep = self._create_dependency(module_name, file_path, "import")
                    if dep:
                        file_dependencies.append(dep)
                
                for match in re.finditer(require_pattern, file_content):
                    module_name = match.group(1).split('/')[0]
                    if module_name.startswith('.'):  # Relative import
                        continue
                    dep = self._create_dependency(module_name, file_path, "require")
                    if dep:
                        file_dependencies.append(dep)
            
        except Exception as e:
            print(f"Error parsing dependencies in {file_path}: {str(e)}")
        
        return file_dependencies
    
    def _create_dependency(self, module_name: str, source_file: str, import_type: str) -> Optional[Dependency]:
        """Create a Dependency object with the correct classifications."""
        # Skip standard library modules
        if module_name in self.STDLIB_MODULES:
            return Dependency(
                module_name=module_name,
                source_file=source_file,
                import_type=import_type,
                is_builtin=True,
                resolved=True
            )
        
        # Check if it's an external package
        is_external = self._check_if_external(module_name)
        
        # Check if it's a project module
        is_project_module = self._check_if_project_module(module_name)
        
        # Determine if it's resolved
        resolved = is_external or is_project_module
        
        return Dependency(
            module_name=module_name,
            source_file=source_file,
            import_type=import_type,
            is_builtin=False,
            is_external=is_external,
            is_project_module=is_project_module,
            resolved=resolved
        )
    
    def _check_if_external(self, module_name: str) -> bool:
        """Check if a module is an external package."""
        try:
            return importlib.util.find_spec(module_name) is not None
        except (ImportError, ValueError):
            return False
    
    def _check_if_project_module(self, module_name: str) -> bool:
        """Check if a module is part of the project based on the files we know about."""
        if module_name in self.modules_to_files:
            return True
        
        # Check if there's a directory with this name
        potential_dir = os.path.join(self.project_root, module_name)
        if os.path.isdir(potential_dir):
            # Check if there's an __init__.py
            init_file = os.path.join(potential_dir, "__init__.py")
            return os.path.exists(init_file)
        
        # Check if there's a Python file with this name
        potential_file = os.path.join(self.project_root, f"{module_name}.py")
        return os.path.exists(potential_file)
    
    def add_file(self, file_path: str, file_content: str) -> List[Dependency]:
        """
        Add a file to the dependency graph and returns unresolved dependencies.
        
        Args:
            file_path: The relative path of the file
            file_content: The content of the file
            
        Returns:
            List of unresolved dependencies
        """
        # Parse the file's dependencies
        deps = self.parse_file_dependencies(file_path, file_content)
        
        # Add to the dependency set
        self.dependencies.update(deps)
        
        # Update the file_dependencies map
        if file_path not in self.file_dependencies:
            self.file_dependencies[file_path] = set()
        
        # Extract module name from file path
        if file_path.endswith('.py'):
            module_path = file_path.replace('/', '.').replace('\\', '.').replace('.py', '')
            components = module_path.split('.')
            
            # Handle __init__.py files
            if components[-1] == '__init__':
                components.pop()  # Remove __init__
                
            module_name = components[-1] if components else ""
            
            # Register this file as implementing the module
            if module_name:
                if module_name not in self.modules_to_files:
                    self.modules_to_files[module_name] = set()
                self.modules_to_files[module_name].add(file_path)
        
        # Process dependencies
        unresolved = []
        for dep in deps:
            if not dep.resolved:
                self.unresolved_dependencies.add(dep)
                unresolved.append(dep)
            
            # Record which files this file depends on
            if dep.is_project_module and dep.module_name in self.modules_to_files:
                for impl_file in self.modules_to_files[dep.module_name]:
                    self.file_dependencies[file_path].add(impl_file)
        
        # Update dependency resolution status
        self._update_resolution_status()
        
        return unresolved
    
    def _update_resolution_status(self):
        """Update the resolution status of all dependencies based on current knowledge."""
        # Check if any unresolved dependencies are now resolved
        newly_resolved = set()
        
        for dep in self.unresolved_dependencies:
            # Check if the module is now in our known modules
            if dep.module_name in self.modules_to_files:
                dep.is_project_module = True
                dep.resolved = True
                newly_resolved.add(dep)
            
            # Re-check external modules (in case they were installed)
            elif not dep.is_external and self._check_if_external(dep.module_name):
                dep.is_external = True
                dep.resolved = True
                newly_resolved.add(dep)
        
        # Remove newly resolved dependencies from the unresolved set
        self.unresolved_dependencies -= newly_resolved
    
    def get_unresolved_dependencies(self) -> List[Dependency]:
        """Get the list of unresolved dependencies."""
        return sorted(list(self.unresolved_dependencies), 
                      key=lambda d: (d.priority, d.module_name), reverse=True)
    
    def get_unresolved_for_file(self, file_path: str) -> List[Dependency]:
        """Get unresolved dependencies specific to a file."""
        return [dep for dep in self.unresolved_dependencies if dep.source_file == file_path]
    
    def get_dependency_issues(self) -> Dict[str, Any]:
        """Get a summary of dependency issues."""
        issues = {
            "unresolved_modules": [],
            "files_with_issues": {}
        }
        
        # Group unresolved dependencies by module
        unresolved_by_module = {}
        for dep in self.unresolved_dependencies:
            if dep.module_name not in unresolved_by_module:
                unresolved_by_module[dep.module_name] = []
            unresolved_by_module[dep.module_name].append(dep.source_file)
        
        # Add to issues report
        for module, files in unresolved_by_module.items():
            issues["unresolved_modules"].append({
                "module": module,
                "imported_by": files
            })
            
            # Add to the files with issues
            for file in files:
                if file not in issues["files_with_issues"]:
                    issues["files_with_issues"][file] = []
                issues["files_with_issues"][file].append(f"Unresolved import: {module}")
        
        return issues
    
    def generate_dependency_info_for_llm(self, file_path: str = None) -> str:
        """
        Generate dependency information formatted for the LLM prompt.
        
        Args:
            file_path: If provided, focus on dependencies for this file
            
        Returns:
            Formatted information about dependencies to add to the LLM prompt
        """
        if file_path:
            # Focus on dependencies related to this specific file
            unresolved_for_file = self.get_unresolved_for_file(file_path)
            
            if not unresolved_for_file:
                return "No unresolved dependencies for this file."
            
            result = "# Dependencies to Resolve for This File\n\n"
            result += "This file has the following unresolved import dependencies:\n\n"
            
            # Group by module for clarity
            by_module = {}
            for dep in unresolved_for_file:
                if dep.module_name not in by_module:
                    by_module[dep.module_name] = []
                by_module[dep.module_name].append(dep)
            
            for module, deps in by_module.items():
                result += f"- `{module}` (used in import type: {deps[0].import_type})\n"
            
            result += "\nPlease ensure these modules exist or are properly imported. Options:\n"
            result += "1. Create the missing module in the project\n"
            result += "2. Fix the import statement to use an existing module\n"
            result += "3. Add external dependencies to requirements.txt\n"
        else:
            # General dependency info for the project
            issues = self.get_dependency_issues()
            
            if not issues["unresolved_modules"]:
                return "All dependencies are currently resolved."
            
            result = "# Unresolved Dependencies\n\n"
            result += "The following modules or packages are imported but not yet implemented:\n\n"
            
            for module_info in issues["unresolved_modules"]:
                result += f"## {module_info['module']}\n"
                result += "Imported by:\n"
                for file in module_info['imported_by']:
                    result += f"- `{file}`\n"
                result += "\n"
            
            result += "# Dependency Resolution Notes\n\n"
            result += "When implementing files, please consider these dependencies:\n\n"
            result += "1. Create project-specific modules before the files that import them\n"
            result += "2. For external packages, ensure they're included in requirements.txt or package.json\n"
            result += "3. Use consistent naming between import statements and actual module names\n"
        
        return result
    
    def save_dependency_state(self, output_path: str):
        """Save the current dependency state to a file."""
        # Convert dependencies to list of dicts for JSON serialization
        deps = [asdict(dep) for dep in self.dependencies]
        
        # Prepare the state
        state = {
            "dependencies": deps,
            "file_dependencies": {k: list(v) for k, v in self.file_dependencies.items()},
            "modules_to_files": {k: list(v) for k, v in self.modules_to_files.items()},
            "unresolved_dependencies": [asdict(dep) for dep in self.unresolved_dependencies]
        }
        
        # Save to file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2)
    
    def load_dependency_state(self, input_path: str):
        """Load dependency state from a file."""
        if not os.path.exists(input_path):
            print(f"Warning: Dependency state file {input_path} does not exist.")
            return
        
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                state = json.load(f)
            
            # Reconstruct dependencies
            self.dependencies = {Dependency(**dep) for dep in state.get("dependencies", [])}
            self.file_dependencies = {k: set(v) for k, v in state.get("file_dependencies", {}).items()}
            self.modules_to_files = {k: set(v) for k, v in state.get("modules_to_files", {}).items()}
            self.unresolved_dependencies = {Dependency(**dep) for dep in state.get("unresolved_dependencies", [])}
        except Exception as e:
            print(f"Error loading dependency state: {str(e)}")
    
    def generate_dependency_report(self, output_file: str = None) -> str:
        """
        Generate a report of dependencies.
        
        Args:
            output_file: If provided, write the report to this file
            
        Returns:
            The report as a string
        """
        issues = self.get_dependency_issues()
        
        report = "# Dependency Analysis Report\n\n"
        
        # Project overview
        report += "## Project Overview\n\n"
        report += f"- Total files: {len(self.file_dependencies)}\n"
        report += f"- Total dependencies: {len(self.dependencies)}\n"
        report += f"- Unresolved dependencies: {len(self.unresolved_dependencies)}\n\n"
        
        # Unresolved dependencies
        if issues["unresolved_modules"]:
            report += "## Unresolved Dependencies\n\n"
            for module_info in issues["unresolved_modules"]:
                report += f"### {module_info['module']}\n"
                report += "Imported by:\n"
                for file in module_info['imported_by']:
                    report += f"- `{file}`\n"
                report += "\n"
        else:
            report += "## Unresolved Dependencies\n\n"
            report += "No unresolved dependencies found.\n\n"
        
        # Files with issues
        if issues["files_with_issues"]:
            report += "## Files With Dependency Issues\n\n"
            for file, issues_list in issues["files_with_issues"].items():
                report += f"### {file}\n"
                for issue in issues_list:
                    report += f"- {issue}\n"
                report += "\n"
        
        # Write to file if requested
        if output_file:
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(report)
            except Exception as e:
                print(f"Error writing dependency report to {output_file}: {str(e)}")
        
        return report


class DependencyResolver:
    """Helper class to resolve dependencies."""
    
    def __init__(self, project_dir: str):
        """Initialize the resolver with a project directory."""
        self.project_dir = project_dir
        self.dependency_graph = DependencyGraph(project_dir)
    
    def initialize(self, file_map: Dict[str, Any]):
        """Initialize the dependency graph from a map of files."""
        # Add each file to the dependency graph
        for file_path, file_content in file_map.items():
            if isinstance(file_content, dict) and "content" in file_content:
                content = file_content["content"]
            else:
                content = file_content
                
            self.dependency_graph.add_file(file_path, content)
        
        # Create missing __init__.py files
        self._create_missing_init_files()
    
    def _create_missing_init_files(self):
        """Create missing __init__.py files in directories that contain Python files."""
        # Find all directories with Python files
        dirs_with_py = set()
        for file_path in self.dependency_graph.file_dependencies:
            if file_path.endswith('.py'):
                dir_path = os.path.dirname(file_path)
                if dir_path:
                    dirs_with_py.add(dir_path)
        
        # Check and create __init__.py files
        for dir_path in dirs_with_py:
            init_path = os.path.join(dir_path, "__init__.py")
            full_init_path = os.path.join(self.project_dir, init_path)
            
            # Create the directory if it doesn't exist
            full_dir_path = os.path.dirname(full_init_path)
            if not os.path.exists(full_dir_path):
                os.makedirs(full_dir_path, exist_ok=True)
                
            # Create __init__.py if it doesn't exist
            if not os.path.exists(full_init_path):
                with open(full_init_path, 'w', encoding='utf-8') as f:
                    f.write('"""Auto-generated __init__.py file."""\n')
                
                # Add to dependency graph
                self.dependency_graph.add_file(init_path, '"""Auto-generated __init__.py file."""\n')
    
    def check_file(self, file_path: str, file_content: str) -> List[Dependency]:
        """Check a file for dependencies and return any unresolved ones."""
        return self.dependency_graph.add_file(file_path, file_content)
    
    def enhance_prompt(self, file_path: str, original_prompt: str) -> str:
        """Enhance an implementation prompt with dependency information."""
        dependency_info = self.dependency_graph.generate_dependency_info_for_llm(file_path)
        
        # Add to the prompt
        if dependency_info and not dependency_info.startswith("No unresolved dependencies"):
            updated_prompt = original_prompt + "\n\n" + dependency_info
            return updated_prompt
        
        return original_prompt
    
    def perform_final_check(self, file_map: Dict[str, Any]) -> bool:
        """
        Perform a final check for all dependencies and try to resolve any issues.
        
        Args:
            file_map: Map of file paths to content
            
        Returns:
            True if all dependencies are resolved, False otherwise
        """
        # Re-analyze all files
        self.initialize(file_map)
        
        # Check if there are any unresolved dependencies
        unresolved = self.dependency_graph.get_unresolved_dependencies()
        
        return len(unresolved) == 0
    
    def get_files_needing_fixes(self) -> Dict[str, List[Dependency]]:
        """Get a map of files to their unresolved dependencies."""
        # Group by file
        files_to_deps = {}
        for dep in self.dependency_graph.unresolved_dependencies:
            if dep.source_file not in files_to_deps:
                files_to_deps[dep.source_file] = []
            files_to_deps[dep.source_file].append(dep)
        
        return files_to_deps
    
    def generate_fix_prompt(self, file_path: str, file_content: str) -> str:
        """
        Generate a prompt to fix dependency issues in a file.
        
        Args:
            file_path: The file with dependency issues
            file_content: The content of the file
            
        Returns:
            A prompt for the LLM to fix the issues
        """
        unresolved = self.dependency_graph.get_unresolved_for_file(file_path)
        
        if not unresolved:
            return ""
        
        # Group by module for clarity
        by_module = {}
        for dep in unresolved:
            if dep.module_name not in by_module:
                by_module[dep.module_name] = []
            by_module[dep.module_name].append(dep)
        
        # Build the prompt
        prompt = f"# Fix Dependency Issues in {file_path}\n\n"
        prompt += "This file has the following unresolved import dependencies:\n\n"
        
        for module, deps in by_module.items():
            prompt += f"- `{module}` (used in import type: {deps[0].import_type})\n"
        
        prompt += "\nPlease fix these issues by either:\n"
        prompt += "1. Creating the missing module(s) in the project\n"
        prompt += "2. Fixing the import statements to use existing modules\n"
        prompt += "3. Adding external dependencies to requirements.txt\n\n"
        
        prompt += "Current file content:\n\n```python\n"
        prompt += file_content
        prompt += "\n```\n\n"
        
        prompt += "Please provide a corrected version of this file that resolves the dependency issues."
        
        return prompt
    
    def iterate_fixes(self, file_map: Dict[str, Any], fix_function) -> bool:
        """
        Iteratively fix dependency issues until all are resolved or no progress is made.
        
        Args:
            file_map: Map of file paths to content
            fix_function: Function to fix a file (takes file_path, fix_prompt, file_content as args)
            
        Returns:
            True if all dependencies are resolved, False otherwise
        """
        # Initialize with current file map
        self.initialize(file_map)
        
        # Maximum number of iterations to prevent infinite loops
        max_iterations = 3
        iterations = 0
        
        while iterations < max_iterations:
            iterations += 1
            
            # Get files needing fixes
            files_needing_fixes = self.get_files_needing_fixes()
            
            if not files_needing_fixes:
                # All dependencies resolved
                return True
            
            # Try to fix each file
            progress_made = False
            
            for file_path, deps in files_needing_fixes.items():
                # Get file content
                if file_path in file_map:
                    if isinstance(file_map[file_path], dict) and "content" in file_map[file_path]:
                        file_content = file_map[file_path]["content"]
                    else:
                        file_content = file_map[file_path]
                else:
                    continue
                
                # Generate fix prompt
                fix_prompt = self.generate_fix_prompt(file_path, file_content)
                
                # Apply fix
                fixed = fix_function(file_path, fix_prompt, file_content)
                
                if fixed:
                    progress_made = True
            
            # If no progress was made, break the loop
            if not progress_made:
                break
            
            # Re-analyze dependencies
            self.initialize(file_map)
        
        # Final check
        return len(self.dependency_graph.unresolved_dependencies) == 0


# Utility functions

def get_dependency_tracker(project_root: str = None) -> DependencyGraph:
    """
    Get the dependency tracker instance.
    
    Args:
        project_root: Root directory of the project
        
    Returns:
        A DependencyGraph instance
    """
    if project_root is None:
        project_root = os.getcwd()
    
    return DependencyGraph(project_root)


def analyze_project_dependencies(project_dir: str, file_map: Dict[str, Any] = None) -> DependencyGraph:
    """
    Analyze dependencies for an entire project.
    
    Args:
        project_dir: The project directory
        file_map: A map of file paths to content. If None, reads from the project dir.
        
    Returns:
        A DependencyGraph instance
    """
    dependency_graph = DependencyGraph(project_dir)
    
    # If no file map is provided, build one from the project dir
    if file_map is None:
        file_map = {}
        for root, _, files in os.walk(project_dir):
            for file in files:
                if file.endswith(('.py', '.js', '.jsx', '.ts', '.tsx')):
                    rel_path = os.path.relpath(os.path.join(root, file), project_dir)
                    
                    # Skip various directories
                    if any(part.startswith('.') for part in rel_path.split(os.sep)):
                        continue
                    if any(part == "node_modules" for part in rel_path.split(os.sep)):
                        continue
                    if any(part == "venv" for part in rel_path.split(os.sep)):
                        continue
                    if any(part == "__pycache__" for part in rel_path.split(os.sep)):
                        continue
                    
                    try:
                        with open(os.path.join(root, file), 'r', encoding='utf-8', errors='ignore') as f:
                            file_map[rel_path] = f.read()
                    except Exception as e:
                        print(f"Error reading {rel_path}: {str(e)}")
    
    # Add each file to the dependency graph
    for file_path, file_content in file_map.items():
        if isinstance(file_content, dict) and "content" in file_content:
            content = file_content["content"]
        else:
            content = file_content
            
        dependency_graph.add_file(file_path, content)
    
    return dependency_graph


def check_file_dependencies(project_dir: str, file_path: str, file_content: str = None) -> List[Dependency]:
    """
    Check dependencies for a single file.
    
    Args:
        project_dir: The project directory
        file_path: The path of the file to check
        file_content: The content of the file. If None, reads from the file_path.
        
    Returns:
        List of unresolved dependencies
    """
    # If no content provided, read from file
    if file_content is None:
        full_path = os.path.join(project_dir, file_path)
        if os.path.exists(full_path):
            try:
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    file_content = f.read()
            except Exception as e:
                print(f"Error reading {file_path}: {str(e)}")
                return []
        else:
            print(f"File not found: {file_path}")
            return []
    
    dependency_graph = DependencyGraph(project_dir)
    return dependency_graph.add_file(file_path, file_content)


def create_missing_init_files(project_dir: str) -> List[str]:
    """
    Create missing __init__.py files in directories that contain Python files.
    
    Args:
        project_dir: The project directory
        
    Returns:
        List of created __init__.py files
    """
    # Find all Python files in the project
    py_files = []
    for root, _, files in os.walk(project_dir):
        for file in files:
            if file.endswith('.py'):
                rel_path = os.path.relpath(os.path.join(root, file), project_dir)
                py_files.append(rel_path)
    
    # Find all directories with Python files
    dirs_with_py = set()
    for file_path in py_files:
        dir_path = os.path.dirname(file_path)
        if dir_path:
            dirs_with_py.add(dir_path)
    
    # Create __init__.py files
    created_files = []
    for dir_path in dirs_with_py:
        init_path = os.path.join(dir_path, "__init__.py")
        full_init_path = os.path.join(project_dir, init_path)
        
        # Create the directory if it doesn't exist
        full_dir_path = os.path.dirname(full_init_path)
        if not os.path.exists(full_dir_path):
            os.makedirs(full_dir_path, exist_ok=True)
            
        # Create __init__.py if it doesn't exist
        if not os.path.exists(full_init_path):
            with open(full_init_path, 'w', encoding='utf-8') as f:
                f.write('"""Auto-generated __init__.py file."""\n')
            created_files.append(init_path)
    
    return created_files


def prioritize_files_by_dependencies(files_to_implement: List[str]) -> List[str]:
    """
    Prioritize files based on their dependencies so that files are implemented 
    in an order that maximizes successful dependency resolution.
    
    Args:
        files_to_implement: List of files to prioritize
        
    Returns:
        Re-ordered list of files
    """
    # We don't have dependency info yet, so use heuristics:
    # 1. __init__.py files first
    # 2. Base/utility files before modules that might depend on them
    # 3. Core logic before views/UI
    
    # Define priority categories (higher number = higher priority)
    priority_map = {
        "__init__.py": 5,
        "requirements.txt": 5,
        "package.json": 5,
        "setup.py": 5,
        "utils.py": 4,
        "helpers.py": 4,
        "common.py": 4,
        "config.py": 4,
        "constants.py": 4,
        "base.py": 4,
        "core.py": 4,
        "models.py": 3,
        "database.py": 3,
        "db.py": 3,
        "api.py": 2,
        "views.py": 1,
        "routes.py": 1,
        "controllers.py": 1,
        "app.py": 0,
        "main.py": 0,
        "server.py": 0,
    }
    
    # Assign priorities to files
    files_with_priority = []
    for file in files_to_implement:
        priority = 0
        
        # Check for exact filename matches
        file_name = os.path.basename(file)
        if file_name in priority_map:
            priority = priority_map[file_name]
        
        # __init__.py files get high priority
        if file_name == "__init__.py":
            # For deeper directories, reduce priority slightly
            depth = len(file.split(os.sep)) - 1
            priority = 5 - min(depth, 3)  # 5 for root, 4 for depth 1, etc.
        
        files_with_priority.append((file, priority))
    
    # Sort by priority (descending)
    files_with_priority.sort(key=lambda x: x[1], reverse=True)
    
    return [file for file, _ in files_with_priority]


def generate_dependency_report(project_dir: str = None, output_file: str = None) -> str:
    """
    Generate a report of dependencies for the project.
    
    Args:
        project_dir: The project directory (defaults to current directory)
        output_file: If provided, write the report to this file
        
    Returns:
        The report as a string
    """
    if project_dir is None:
        project_dir = os.getcwd()
    
    # Analyze dependencies
    dependency_graph = analyze_project_dependencies(project_dir)
    
    # Generate report
    report = dependency_graph.generate_dependency_report(output_file)
    
    return report


def enhance_implementation_prompt(file_path: str, original_prompt: str, project_dir: str = None) -> str:
    """
    Enhance an implementation prompt with dependency information.
    
    Args:
        file_path: The file being implemented
        original_prompt: The original implementation prompt
        project_dir: The project directory (defaults to current directory)
        
    Returns:
        Enhanced prompt with dependency information
    """
    if project_dir is None:
        project_dir = os.getcwd()
    
    # Build a file map of existing files
    file_map = {}
    for root, _, files in os.walk(project_dir):
        for file in files:
            if file.endswith(('.py', '.js', '.jsx', '.ts', '.tsx')):
                rel_path = os.path.relpath(os.path.join(root, file), project_dir)
                
                # Skip various directories
                if any(part.startswith('.') for part in rel_path.split(os.sep)):
                    continue
                if any(part == "node_modules" for part in rel_path.split(os.sep)):
                    continue
                if any(part == "venv" for part in rel_path.split(os.sep)):
                    continue
                if any(part == "__pycache__" for part in rel_path.split(os.sep)):
                    continue
                
                # Skip the file being implemented
                if rel_path == file_path:
                    continue
                
                # Read the file
                try:
                    with open(os.path.join(root, file), 'r', encoding='utf-8', errors='ignore') as f:
                        file_map[rel_path] = f.read()
                except Exception as e:
                    print(f"Error reading {rel_path}: {str(e)}")
    
    # Analyze dependencies
    dependency_resolver = DependencyResolver(project_dir)
    dependency_resolver.initialize(file_map)
    
    # Enhance prompt
    return dependency_resolver.enhance_prompt(file_path, original_prompt)


if __name__ == "__main__":
    print("Standalone Dependency Tracker - Run dependency_checker.py for CLI usage") 