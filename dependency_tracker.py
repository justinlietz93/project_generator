"""
Dependency Tracker for Project Builder

This module helps track and validate dependencies during the AI-driven file generation process.
It ensures that:
1. All imported modules/components are tracked in real-time
2. Dependencies between files are properly recorded and validated
3. Unresolved dependencies are highlighted for resolution
4. Dependency information is provided to the LLM when implementing files
5. The process continues iteratively until all dependencies are resolved

This integrates with the project_builder.py without modifying its core functionality.
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
    
    def get_dependency_issues(self) -> Dict[str, List[str]]:
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


# Dependency Tracker Singleton
_DEPENDENCY_TRACKER: Optional[DependencyGraph] = None

def get_dependency_tracker(project_root: str = None) -> DependencyGraph:
    """Get or create the global dependency tracker instance."""
    global _DEPENDENCY_TRACKER
    if _DEPENDENCY_TRACKER is None and project_root:
        _DEPENDENCY_TRACKER = DependencyGraph(project_root=project_root)
    return _DEPENDENCY_TRACKER


def analyze_project_dependencies(project_dir: str, file_map: Dict[str, Any]) -> DependencyGraph:
    """
    Analyze all files in the project for dependencies.
    
    Args:
        project_dir: The project directory
        file_map: A map of file paths to ProjectFile objects
        
    Returns:
        DependencyGraph object with dependency information
    """
    # Use the global dependency tracker
    graph = get_dependency_tracker(project_dir)
    
    # Analyze each file
    for file_path, project_file in file_map.items():
        if hasattr(project_file, 'content'):
            graph.add_file(file_path, project_file.content)
    
    return graph


def check_file_dependencies(project_dir: str, file_path: str, file_content: str) -> List[Dependency]:
    """
    Check a single file for dependencies after it's been implemented.
    
    Args:
        project_dir: The project directory
        file_path: The relative path of the file
        file_content: The content of the file
        
    Returns:
        List of unresolved dependencies
    """
    graph = get_dependency_tracker(project_dir)
    if graph is None:
        graph = DependencyGraph(project_root=project_dir)
        global _DEPENDENCY_TRACKER
        _DEPENDENCY_TRACKER = graph
    
    return graph.add_file(file_path, file_content)


def create_missing_init_files(project_dir: str) -> List[str]:
    """
    Create missing __init__.py files for Python packages.
    
    Args:
        project_dir: The project directory
        
    Returns:
        List of created __init__.py files
    """
    graph = get_dependency_tracker()
    if graph is None:
        print("Dependency graph not initialized.")
        return []
    
    created_files = []
    python_dirs = set()
    
    # Find all directories containing Python files
    for file_path in graph.file_dependencies.keys():
        if file_path.endswith('.py'):
            dir_path = os.path.dirname(file_path)
            while dir_path:
                python_dirs.add(dir_path)
                # Move up one level
                dir_path = os.path.dirname(dir_path)
    
    # Create __init__.py in each directory
    for dir_path in python_dirs:
        full_dir_path = os.path.join(project_dir, dir_path)
        init_file = os.path.join(dir_path, '__init__.py')
        full_init_path = os.path.join(project_dir, dir_path, '__init__.py')
        
        if not os.path.exists(full_dir_path):
            os.makedirs(full_dir_path, exist_ok=True)
        
        if not os.path.exists(full_init_path):
            with open(full_init_path, 'w', encoding='utf-8') as f:
                f.write('"""Package module."""\n')
            created_files.append(init_file)
    
    return created_files


def prioritize_files_by_dependencies(files_to_implement: List[str]) -> List[str]:
    """
    Prioritize files for implementation based on dependencies.
    
    Args:
        files_to_implement: List of files to implement
        
    Returns:
        Prioritized list of files
    """
    graph = get_dependency_tracker()
    if graph is None:
        print("Dependency graph not initialized.")
        return files_to_implement
    
    # Start with files that are dependencies of other files
    dependency_count = {}
    for file in files_to_implement:
        dependency_count[file] = 0
    
    # Count how many times each file is a dependency
    for file, deps in graph.file_dependencies.items():
        for dep in deps:
            if dep in dependency_count:
                dependency_count[dep] += 1
    
    # Sort files by dependency count (descending)
    return sorted(files_to_implement, key=lambda f: dependency_count.get(f, 0), reverse=True)


def generate_dependency_report(output_file: str = None):
    """
    Generate a detailed report of project dependencies.
    
    Args:
        output_file: Optional path to save the report
    """
    graph = get_dependency_tracker()
    if graph is None:
        print("Dependency graph not initialized. Cannot generate report.")
        return "Dependency graph not initialized."
    
    report = []
    report.append("# Project Dependency Report")
    report.append(f"Generated on: {os.path.basename(graph.project_root)}")
    report.append("")
    
    # Unresolved dependencies
    unresolved = graph.get_unresolved_dependencies()
    if unresolved:
        report.append("## Unresolved Dependencies")
        for dep in unresolved:
            report.append(f"- {dep.module_name} (imported by {dep.source_file})")
        report.append("")
    else:
        report.append("## All Dependencies Resolved!")
        report.append("")
    
    # Files by module
    report.append("## Modules and Implementing Files")
    for module, files in sorted(graph.modules_to_files.items()):
        report.append(f"### {module}")
        for file in sorted(files):
            report.append(f"- {file}")
        report.append("")
    
    # File dependencies
    report.append("## File Dependencies")
    for file, deps in sorted(graph.file_dependencies.items()):
        if deps:
            report.append(f"### {file} depends on:")
            for dep in sorted(deps):
                report.append(f"- {dep}")
            report.append("")
    
    # Save or print the report
    report_text = "\n".join(report)
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report_text)
        print(f"Dependency report saved to {output_file}")
    
    return report_text


def enhance_implementation_prompt(file_path: str, original_prompt: str) -> str:
    """
    Enhance an implementation prompt with dependency information.
    
    Args:
        file_path: Path of the file being implemented
        original_prompt: Original implementation prompt
        
    Returns:
        Enhanced prompt with dependency context
    """
    graph = get_dependency_tracker()
    if graph is None:
        return original_prompt
    
    # Generate dependency information for this file
    dependency_info = graph.generate_dependency_info_for_llm(file_path)
    
    # Find a good place to insert the dependency information
    if "## Implementation Requirements" in original_prompt:
        # Insert before implementation requirements
        parts = original_prompt.split("## Implementation Requirements")
        enhanced_prompt = parts[0] + "## Dependency Information\n\n" + dependency_info + "\n\n## Implementation Requirements" + parts[1]
    else:
        # Just append to the end
        enhanced_prompt = original_prompt + "\n\n## Dependency Information\n\n" + dependency_info
    
    return enhanced_prompt


def perform_final_dependency_check(project_dir: str, file_map: Dict[str, Any]) -> bool:
    """
    Perform a final dependency check on the entire project.
    
    Args:
        project_dir: The project directory
        file_map: Map of file paths to ProjectFile objects
        
    Returns:
        True if all dependencies are resolved, False otherwise
    """
    # Analyze the entire project
    graph = analyze_project_dependencies(project_dir, file_map)
    
    # Check if there are any unresolved dependencies
    unresolved = graph.get_unresolved_dependencies()
    
    # Generate a report
    report_path = os.path.join(project_dir, "dependency_report.md")
    generate_dependency_report(report_path)
    
    return len(unresolved) == 0


def get_files_with_dependency_issues() -> Dict[str, List[Dependency]]:
    """
    Get a mapping of files to their unresolved dependencies.
    
    Returns:
        Dict mapping file paths to lists of unresolved dependencies
    """
    graph = get_dependency_tracker()
    if graph is None:
        return {}
    
    files_with_issues = {}
    for dep in graph.unresolved_dependencies:
        if dep.source_file not in files_with_issues:
            files_with_issues[dep.source_file] = []
        files_with_issues[dep.source_file].append(dep)
    
    return files_with_issues


class DependencyResolver:
    """
    A class for resolving dependencies iteratively during and after project generation.
    """
    def __init__(self, project_dir: str):
        self.project_dir = project_dir
        self.graph = get_dependency_tracker(project_dir)
        self.iteration = 0
        self.max_iterations = 5  # Maximum number of fix iterations to avoid infinite loops
    
    def initialize(self, file_map: Dict[str, Any]):
        """Initialize the dependency graph with existing files."""
        analyze_project_dependencies(self.project_dir, file_map)
        self._create_missing_init_files()
    
    def _create_missing_init_files(self):
        """Create missing __init__.py files."""
        created = create_missing_init_files(self.project_dir)
        if created:
            print(f"Created {len(created)} missing __init__.py files.")
    
    def check_file(self, file_path: str, file_content: str) -> List[Dependency]:
        """Check a file for dependencies after it's created or updated."""
        return check_file_dependencies(self.project_dir, file_path, file_content)
    
    def enhance_prompt(self, file_path: str, original_prompt: str) -> str:
        """Enhance an implementation prompt with dependency context."""
        return enhance_implementation_prompt(file_path, original_prompt)
    
    def perform_final_check(self, file_map: Dict[str, Any]) -> bool:
        """Perform a final dependency check on the entire project."""
        return perform_final_dependency_check(self.project_dir, file_map)
    
    def get_files_needing_fixes(self) -> Dict[str, List[Dependency]]:
        """Get files that need fixes for unresolved dependencies."""
        return get_files_with_dependency_issues()
    
    def generate_fix_prompt(self, file_path: str, file_content: str) -> str:
        """Generate a prompt to fix dependencies in a file."""
        # Get unresolved dependencies for this file
        graph = get_dependency_tracker()
        unresolved = [dep for dep in graph.unresolved_dependencies if dep.source_file == file_path]
        
        if not unresolved:
            return "No dependency issues to fix in this file."
        
        # Group by module name for clarity
        by_module = {}
        for dep in unresolved:
            if dep.module_name not in by_module:
                by_module[dep.module_name] = []
            by_module[dep.module_name].append(dep)
        
        prompt = f"# Dependency Fix for {file_path}\n\n"
        prompt += "This file has the following unresolved dependencies that need to be fixed:\n\n"
        
        for module, deps in by_module.items():
            prompt += f"## Module: {module}\n"
            prompt += f"Import type: {deps[0].import_type}\n\n"
        
        prompt += "Please fix these dependencies by either:\n"
        prompt += "1. Changing the import to use an existing module\n"
        prompt += "2. Creating the necessary module if it's a project module\n"
        prompt += "3. Adding the external dependency to requirements.txt if it's a third-party package\n\n"
        
        prompt += "## Current File Content\n"
        prompt += f"```python\n{file_content}\n```\n\n"
        
        # Add information about available modules
        if graph.modules_to_files:
            prompt += "## Available Project Modules\n"
            for module in sorted(graph.modules_to_files.keys()):
                prompt += f"- {module}\n"
            prompt += "\n"
        
        prompt += "Please provide the updated file content that resolves these dependency issues."
        
        return prompt
    
    def iterate_fixes(self, file_map: Dict[str, Any], fix_function) -> bool:
        """
        Iteratively fix dependency issues until resolved or max iterations reached.
        
        Args:
            file_map: Map of file paths to ProjectFile objects
            fix_function: Function to call to fix a file, should accept (file_path, fix_prompt, file_content)
                         and return the fixed content
        
        Returns:
            True if all dependencies resolved, False otherwise
        """
        self.iteration = 0
        while self.iteration < self.max_iterations:
            self.iteration += 1
            print(f"\n=== Dependency Fix Iteration {self.iteration} ===")
            
            # Update the dependency graph
            analyze_project_dependencies(self.project_dir, file_map)
            
            # Check for files with issues
            files_with_issues = self.get_files_needing_fixes()
            
            if not files_with_issues:
                print("All dependencies resolved!")
                return True
            
            print(f"Found {len(files_with_issues)} files with dependency issues.")
            
            # Fix each file with issues
            for file_path, deps in files_with_issues.items():
                if file_path not in file_map:
                    print(f"Warning: File {file_path} not in file_map, skipping.")
                    continue
                
                print(f"Fixing dependencies in {file_path}...")
                file_content = file_map[file_path].content
                fix_prompt = self.generate_fix_prompt(file_path, file_content)
                
                # Call the provided fix function
                updated_content = fix_function(file_path, fix_prompt, file_content)
                
                # Update the file in the file_map
                if hasattr(file_map[file_path], 'content'):
                    file_map[file_path].content = updated_content
            
            # Create any missing __init__.py files
            self._create_missing_init_files()
            
            # Check if all dependencies are now resolved
            if self.perform_final_check(file_map):
                print(f"All dependencies resolved after {self.iteration} iterations!")
                return True
        
        print(f"Reached maximum iteration limit ({self.max_iterations}), some dependencies remain unresolved.")
        return False 