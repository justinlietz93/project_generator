#!/usr/bin/env python3
"""
Dependency Checker

A command-line tool to check and fix dependency issues in Python projects.
This is a standalone script that works with the dependency_tracker module.

Usage:
    python dependency_checker.py --check /path/to/project
    python dependency_checker.py --fix /path/to/project

This script can be used independently of the project_maker system to analyze
and fix dependency issues in any Python project.
"""

import os
import sys
import argparse
import json
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional

# Import the dependency tracker
try:
    from standalone_dependency_tracker import (
        analyze_project_dependencies,
        generate_dependency_report,
        DependencyResolver,
        Dependency
    )
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from standalone_dependency_tracker import (
        analyze_project_dependencies,
        generate_dependency_report,
        DependencyResolver,
        Dependency
    )


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Check and fix dependencies in Python projects'
    )
    
    # Project directory
    parser.add_argument(
        '--project-dir', '-p',
        help='Path to the project directory',
        default=os.getcwd()
    )
    
    # Mode selection
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '--check', '-c',
        action='store_true',
        help='Check for dependency issues'
    )
    group.add_argument(
        '--fix', '-f',
        action='store_true',
        help='Fix dependency issues'
    )
    group.add_argument(
        '--report', '-r',
        action='store_true',
        help='Generate a dependency report'
    )
    group.add_argument(
        '--create-inits', '-i',
        action='store_true',
        help='Create missing __init__.py files'
    )
    
    # LLM options for fixing
    parser.add_argument(
        '--use-llm', '-l',
        action='store_true',
        help='Use an LLM to fix dependencies (requires OpenAI API key)'
    )
    
    parser.add_argument(
        '--api-key', '-k',
        help='API key for the LLM service (defaults to OPENAI_API_KEY environment variable)'
    )
    
    parser.add_argument(
        '--model', '-m',
        help='LLM model to use',
        default='gpt-4-turbo'
    )
    
    # Output options
    parser.add_argument(
        '--output', '-o',
        help='Output file for the report',
        default=None
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    return parser.parse_args()


def build_file_map(project_dir: str) -> Dict[str, str]:
    """
    Build a map of file paths to file content for the project.
    
    Args:
        project_dir: The directory to scan
        
    Returns:
        Dict mapping file paths to content
    """
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
                
                # Read the file
                try:
                    with open(os.path.join(root, file), 'r', encoding='utf-8', errors='ignore') as f:
                        file_map[rel_path] = f.read()
                except Exception as e:
                    print(f"Error reading {rel_path}: {str(e)}")
    
    return file_map


def check_dependencies(project_dir: str, verbose: bool = False) -> bool:
    """
    Check for dependency issues in the project.
    
    Args:
        project_dir: The project directory
        verbose: Whether to print verbose output
        
    Returns:
        True if no issues were found, False otherwise
    """
    print(f"Checking dependencies in {project_dir}...")
    
    # Build file map
    file_map = build_file_map(project_dir)
    print(f"Found {len(file_map)} files to analyze")
    
    # Analyze dependencies
    dependency_graph = analyze_project_dependencies(project_dir, file_map)
    
    # Check for unresolved dependencies
    unresolved = dependency_graph.get_unresolved_dependencies()
    
    if not unresolved:
        print("No dependency issues found!")
        return True
    
    # Get dependency issues
    issues = dependency_graph.get_dependency_issues()
    
    # Print issues
    print(f"\nFound {len(unresolved)} unresolved dependencies:")
    
    # Group by module
    for module_info in issues["unresolved_modules"]:
        module = module_info["module"]
        files = module_info["imported_by"]
        
        print(f"\n- Module '{module}' is imported by:")
        for file in files:
            print(f"  - {file}")
    
    # Print per-file issues if verbose
    if verbose:
        print("\nFiles with issues:")
        for file, issues_list in issues["files_with_issues"].items():
            print(f"\n{file}:")
            for issue in issues_list:
                print(f"  - {issue}")
    
    return False


def create_missing_init_files(project_dir: str) -> List[str]:
    """
    Create missing __init__.py files in the project.
    
    Args:
        project_dir: The project directory
        
    Returns:
        List of created files
    """
    print(f"Creating missing __init__.py files in {project_dir}...")
    
    # Find all Python files in the project
    py_files = []
    for root, _, files in os.walk(project_dir):
        for file in files:
            if file.endswith('.py'):
                rel_path = os.path.relpath(os.path.join(root, file), project_dir)
                # Skip various directories
                if any(part.startswith('.') for part in rel_path.split(os.sep)):
                    continue
                if any(part == "venv" for part in rel_path.split(os.sep)):
                    continue
                if any(part == "__pycache__" for part in rel_path.split(os.sep)):
                    continue
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
            print(f"Created {init_path}")
    
    if not created_files:
        print("No missing __init__.py files found.")
    else:
        print(f"Created {len(created_files)} __init__.py files.")
    
    return created_files


def fix_with_llm(file_path: str, fix_prompt: str, file_content: str, api_key: str, model: str) -> Optional[str]:
    """
    Use an LLM to fix dependency issues in a file.
    
    Args:
        file_path: The path to the file
        fix_prompt: The prompt for the LLM
        file_content: The current content of the file
        api_key: The API key for the LLM service
        model: The model to use
        
    Returns:
        The fixed content, or None if it couldn't be fixed
    """
    try:
        # Check if OpenAI is installed
        import openai
    except ImportError:
        print("Error: OpenAI package is not installed. Install it with 'pip install openai'")
        return None
    
    # Set up the OpenAI client
    import openai
    client = openai.OpenAI(api_key=api_key)
    
    print(f"Using LLM to fix dependencies in {file_path}...")
    
    try:
        # Call the API
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that fixes dependency issues in Python code."},
                {"role": "user", "content": fix_prompt}
            ],
            temperature=0.2,
            max_tokens=4000
        )
        
        # Extract the response
        fixed_content = response.choices[0].message.content
        
        # Look for code blocks in the response
        import re
        code_blocks = re.findall(r'```(?:python)?\n(.*?)```', fixed_content, re.DOTALL)
        
        if code_blocks:
            # Use the largest code block (most likely the complete file)
            fixed_content = max(code_blocks, key=len)
        else:
            # No code blocks found, use the entire response
            # But check if it starts with explanation text and trim it
            if not fixed_content.lstrip().startswith('import ') and not fixed_content.lstrip().startswith('from '):
                # Try to find the start of Python code
                lines = fixed_content.split('\n')
                for i, line in enumerate(lines):
                    if line.startswith('import ') or line.startswith('from '):
                        fixed_content = '\n'.join(lines[i:])
                        break
        
        return fixed_content
    except Exception as e:
        print(f"Error calling LLM API: {str(e)}")
        return None


def fix_dependencies(project_dir: str, use_llm: bool = False, api_key: str = None, model: str = 'gpt-4-turbo', verbose: bool = False) -> bool:
    """
    Fix dependency issues in the project.
    
    Args:
        project_dir: The project directory
        use_llm: Whether to use an LLM for fixing
        api_key: API key for the LLM service
        model: The model to use
        verbose: Whether to print verbose output
        
    Returns:
        True if all issues were fixed, False otherwise
    """
    print(f"Fixing dependencies in {project_dir}...")
    
    # First, create missing __init__.py files
    create_missing_init_files(project_dir)
    
    # Build file map
    file_map = build_file_map(project_dir)
    
    # Initialize the resolver
    resolver = DependencyResolver(project_dir)
    resolver.initialize(file_map)
    
    # Get files with issues
    files_with_issues = resolver.get_files_needing_fixes()
    
    if not files_with_issues:
        print("No dependency issues found!")
        return True
    
    print(f"Found {len(files_with_issues)} files with dependency issues")
    
    if use_llm:
        # Check for API key
        if not api_key:
            api_key = os.environ.get('OPENAI_API_KEY')
            if not api_key:
                print("Error: No API key provided. Set it with --api-key or the OPENAI_API_KEY environment variable.")
                return False
        
        # Define the fix function using the LLM
        def fix_function(file_path, fix_prompt, file_content):
            fixed_content = fix_with_llm(file_path, fix_prompt, file_content, api_key, model)
            
            if fixed_content and fixed_content != file_content:
                # Write the fixed content to the file
                full_path = os.path.join(project_dir, file_path)
                try:
                    with open(full_path, 'w', encoding='utf-8') as f:
                        f.write(fixed_content)
                    
                    # Update our file map
                    file_map[file_path] = fixed_content
                    print(f"Fixed {file_path}")
                    return True
                except Exception as e:
                    print(f"Error writing to {file_path}: {str(e)}")
                    return False
            
            return False
        
        # Apply fixes
        success = resolver.iterate_fixes(file_map, fix_function)
    else:
        # Manual fixing mode - prompt the user
        print("\nTo fix dependency issues manually, you need to:")
        print("1. Create missing modules")
        print("2. Fix import statements")
        print("3. Add external dependencies to requirements.txt")
        
        # Provide a report of what to fix
        issues = resolver.dependency_graph.get_dependency_issues()
        
        print("\nUnresolved dependencies:")
        for module_info in issues["unresolved_modules"]:
            module = module_info["module"]
            files = module_info["imported_by"]
            
            print(f"\n- Module '{module}' is imported by:")
            for file in files:
                print(f"  - {file}")
        
        # Create a manual fix report
        report_path = os.path.join(project_dir, "dependency_fix_report.md")
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# Dependency Fix Report\n\n")
            f.write("This report identifies dependency issues in your project and suggests how to fix them.\n\n")
            
            f.write("## Unresolved Dependencies\n\n")
            for module_info in issues["unresolved_modules"]:
                module = module_info["module"]
                files = module_info["imported_by"]
                
                f.write(f"### Module: `{module}`\n\n")
                f.write("Imported by:\n")
                for file in files:
                    f.write(f"- `{file}`\n")
                f.write("\n")
                
                f.write("Possible fixes:\n")
                f.write("1. Create this module in your project\n")
                f.write("2. Fix the import statements to use existing modules\n")
                f.write("3. Add this as an external dependency in requirements.txt\n\n")
        
        print(f"\nA detailed fix report has been written to: {report_path}")
        success = False
    
    # Final check
    if success:
        print("\nAll dependency issues have been resolved!")
    else:
        print("\nSome dependency issues could not be automatically resolved.")
        print("You may need to manually fix the remaining issues.")
    
    return success


def generate_report(project_dir: str, output_file: str = None, verbose: bool = False) -> bool:
    """
    Generate a dependency report for the project.
    
    Args:
        project_dir: The project directory
        output_file: The output file for the report
        verbose: Whether to print verbose output
        
    Returns:
        True if the report was generated successfully, False otherwise
    """
    print(f"Generating dependency report for {project_dir}...")
    
    # Default output file
    if not output_file:
        output_file = os.path.join(project_dir, "dependency_report.md")
    
    # Generate report
    report = generate_dependency_report(project_dir, output_file)
    
    print(f"Dependency report written to: {output_file}")
    
    # Print summary
    if verbose:
        print("\nReport summary:")
        print(report[:500] + "..." if len(report) > 500 else report)
    
    return True


def main():
    """Main entry point."""
    # Parse arguments
    args = parse_args()
    
    # Validate project directory
    if not os.path.isdir(args.project_dir):
        print(f"Error: Directory not found: {args.project_dir}")
        return 1
    
    try:
        # Execute the selected mode
        if args.check:
            success = check_dependencies(args.project_dir, args.verbose)
        elif args.fix:
            success = fix_dependencies(
                args.project_dir,
                args.use_llm,
                args.api_key,
                args.model,
                args.verbose
            )
        elif args.report:
            success = generate_report(args.project_dir, args.output, args.verbose)
        elif args.create_inits:
            created = create_missing_init_files(args.project_dir)
            success = True
        
        return 0 if success else 1
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 