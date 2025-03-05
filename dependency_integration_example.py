#!/usr/bin/env python3
"""
Dependency Integration Example for Project Builder

This script demonstrates how to use the dependency tracker with project_builder.py to:
1. Track dependencies in real-time as files are generated
2. Enhance LLM prompts with dependency information
3. Resolve remaining dependencies at the end of project generation

Usage:
    python dependency_integration_example.py "<project_vision>" --model <model_name>
"""

import os
import sys
import argparse
from typing import Dict, Any, List

# Import the original project_builder module
try:
    from project_builder import (
        run_project_builder, implement_single_file, ProjectFile, 
        extract_files_from_structure, prioritize_files
    )
except ImportError:
    print("Error: Could not import project_builder. Make sure it's in the same directory.")
    sys.exit(1)

# Import utils
try:
    from utils import parse_ai_response_and_apply, read_project_files, write_project_file
except ImportError:
    print("Error: Could not import utils. Make sure it's in the same directory.")
    sys.exit(1)

# Import our dependency tracker
from dependency_tracker import (
    DependencyResolver, get_dependency_tracker,
    analyze_project_dependencies, enhance_implementation_prompt
)


# Store the original implement_single_file function to patch it
original_implement_single_file = implement_single_file


def dependency_aware_implement(file_path: str, structure_content: str, step_outputs: Dict[int, str], 
                               orchestrator, model_name: str, file_map: Dict[str, ProjectFile]) -> bool:
    """
    Wrapper for the original implement_single_file that adds dependency tracking.
    """
    print(f"\n🔍 Checking dependencies for implementation of {file_path}")
    
    # Get project directory from the LLM
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(file_path)))
    
    # Initialize the resolver if needed
    resolver = DependencyResolver(project_dir)
    
    # Build the original file implementation prompt
    original_file_prompt = f"""# File Implementation: {file_path}

IMPORTANT: You are implementing a production-ready source file that must be complete,
robust, and maintainable. Minimal or superficial implementations are not acceptable.

CRITICAL: DO NOT WRITE DEMONSTRATION CODE. Write REAL, FUNCTIONAL code that would
actually be used in a production environment. Your code will be saved directly to a file
and is expected to work without modification.

## Project Context
{step_outputs.get('vision', '(No vision provided)')}

## Project Structure
The file is part of the following project structure:
```
{structure_content[:2000]}  # Include first 2000 chars of the structure
```

## Relevant Architecture & Design
{step_outputs.get(2, '(No architecture)')[:1000]}  # Only first 1000 chars of architecture
{step_outputs.get(3, '(No structure)')[:1000]}     # Only first 1000 chars of structure

## Implementation Task
Your task is to implement: {file_path}

## Implementation Requirements
1. Code Quality:
   - Production-ready, professional code
   - Comprehensive error handling
   - Complete input validation
   - Proper logging
   - Thorough documentation
   - Clear code organization

2. Technical Requirements:
   - Follow all architectural decisions
   - Implement complete functionality
   - Include ALL necessary imports
   - Handle ALL edge cases
   - Include proper error messages
   - Add debug logging where appropriate

3. Documentation Requirements:
   - File-level documentation
   - Function/class documentation
   - Important code block documentation
   - Usage examples in comments
   - Edge case documentation
   - Error handling documentation

4. Testing Considerations:
   - Make code testable
   - Document test scenarios
   - Handle boundary conditions
   - Consider error scenarios

5. Security & Robustness:
   - Implement security best practices
   - Handle resource cleanup
   - Prevent memory leaks
   - Secure error handling
   - Input sanitization

Remember: This code will be used in production. It must be complete, robust, and maintainable.
Avoid shortcuts or minimal implementations. Write code that you would confidently deploy to production.

Output your implementation in `=== File: {file_path} ===`"""

    # Enhance the prompt with dependency information
    enhanced_prompt = enhance_implementation_prompt(file_path, original_file_prompt)
    
    # Use the original function's scope but with our enhanced prompt
    def get_enhanced_ai_response(system_prompt, file_prompt, **kwargs):
        # Replace the file_prompt with our enhanced version
        return orchestrator.call_llm(system_prompt, enhanced_prompt, **kwargs)
    
    # Store the original call_llm function
    original_call_llm = orchestrator.call_llm
    
    try:
        # Replace the orchestrator's call_llm function temporarily
        orchestrator.call_llm = get_enhanced_ai_response
        
        # Call the original function with our modified orchestrator
        result = original_implement_single_file(file_path, structure_content, step_outputs, 
                                             orchestrator, model_name, file_map)
        
        # After implementation, check for dependencies
        if result and file_path in file_map:
            deps = resolver.check_file(file_path, file_map[file_path].content)
            if deps:
                print(f"⚠️ Found {len(deps)} unresolved dependencies in {file_path}:")
                for dep in deps:
                    print(f"  - {dep.module_name} ({dep.import_type})")
            else:
                print(f"✅ No dependency issues found in {file_path}")
        
        return result
    finally:
        # Restore the original call_llm function
        orchestrator.call_llm = original_call_llm


def fix_file_dependencies(file_path: str, fix_prompt: str, file_content: str, orchestrator, model_name: str) -> str:
    """
    Fix dependencies in a file by calling the LLM.
    
    Args:
        file_path: The path of the file to fix
        fix_prompt: The prompt to send to the LLM
        file_content: The current content of the file
        orchestrator: The AI orchestrator to use
        model_name: The model to use
    
    Returns:
        The updated file content
    """
    print(f"Fixing dependencies in {file_path}...")
    
    system_prompt = """You are an expert software engineer fixing dependency issues in a file.
Your task is to update the file to resolve any dependency issues while maintaining its functionality.
Focus specifically on fixing import statements and module references.

IMPORTANT GUIDELINES:
1. Provide the COMPLETE updated file content, not just the changes
2. Make minimal changes to fix the dependency issues
3. Do not add comments about the changes you made
4. Output the entire fixed file content inside === File: path/to/file === markers
5. Be consistent with the project's module structure"""

    response = orchestrator.call_llm(system_prompt, fix_prompt, temperature=0.0)
    
    # Process the response
    files_updated = {}
    parse_ai_response_and_apply(response, files_updated)
    
    # Get the updated content
    if file_path in files_updated and hasattr(files_updated[file_path], 'content'):
        return files_updated[file_path].content
    
    # If parsing failed, return the original content
    print(f"⚠️ Failed to parse LLM response for {file_path}. Keeping original content.")
    return file_content


def run_with_dependency_tracking(vision: str, model_name: str, start_step: int = 1, 
                               start_substep: str = None, run_syntax_check_only: bool = False):
    """
    Run project_builder with dependency tracking.
    
    Args:
        Same as run_project_builder function
    """
    # Store original functions
    original_prioritize = prioritize_files
    
    # Create a dependency-aware prioritize function
    def dependency_aware_prioritize(files: List[str], implementation_plan: str) -> List[str]:
        # First get the initial prioritization
        initial_order = original_prioritize(files, implementation_plan)
        
        # Get the project directory
        project_dir = os.getcwd()
        
        # Get the resolver
        resolver = DependencyResolver(project_dir)
        
        # Add dependency prioritization
        graph = get_dependency_tracker()
        if graph is None:
            return initial_order
        
        # Start with the initial order but prioritize by dependencies
        return initial_order  # TODO: Implement actual dependency prioritization
    
    try:
        # Monkey patch the project_builder function
        import project_builder
        project_builder.implement_single_file = dependency_aware_implement
        project_builder.prioritize_files = dependency_aware_prioritize
        
        # Run the original project_builder
        result = run_project_builder(vision, model_name, start_step, start_substep, run_syntax_check_only)
        
        # After project generation, perform a final dependency check
        if hasattr(project_builder, 'PROJECT_DIR') and os.path.exists(project_builder.PROJECT_DIR):
            print("\n=== Performing Final Dependency Check ===")
            
            # Get the file map
            file_map = read_project_files(project_builder.PROJECT_DIR)
            
            # Create a resolver
            resolver = DependencyResolver(project_builder.PROJECT_DIR)
            resolver.initialize(file_map)
            
            # Check if there are any unresolved dependencies
            if not resolver.perform_final_check(file_map):
                print("\n⚠️ Found dependency issues. Starting iterative fix process.")
                
                # Define a fix function that uses our LLM to fix the issues
                def fix_with_llm(file_path, fix_prompt, file_content):
                    # Create a new orchestrator for fixing
                    from ai_orchestrator import AIOrchestrator
                    orchestrator = AIOrchestrator(model_name)
                    return fix_file_dependencies(file_path, fix_prompt, file_content, orchestrator, model_name)
                
                # Iterate through fixes until all dependencies are resolved
                resolver.iterate_fixes(file_map, fix_with_llm)
                
                # Write the updated files back to disk
                for file_path, file_obj in file_map.items():
                    write_project_file(project_builder.PROJECT_DIR, file_obj)
                
                print("\n✅ Dependency resolution complete. All files updated.")
            else:
                print("\n✅ All dependencies are resolved!")
        
        return result
    finally:
        # Restore original functions
        project_builder.implement_single_file = original_implement_single_file
        project_builder.prioritize_files = original_prioritize


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Build a project with dependency tracking")
    parser.add_argument("vision", help="Vision for the project")
    parser.add_argument("--model", default="gpt-4-turbo", help="Model to use")
    parser.add_argument("--start-step", type=int, default=1, help="Step to start from")
    parser.add_argument("--start-substep", default=None, help="Sub-step to start from")
    parser.add_argument("--syntax-check-only", action="store_true", help="Only run syntax check")
    
    args = parser.parse_args()
    
    run_with_dependency_tracking(
        args.vision,
        args.model,
        start_step=args.start_step,
        start_substep=args.start_substep,
        run_syntax_check_only=args.syntax_check_only
    )


if __name__ == "__main__":
    main() 