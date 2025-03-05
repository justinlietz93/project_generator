"""
Dependency Integration Module

This module integrates the dependency tracking system with the existing project_builder workflow
without modifying its core functionality.
"""

import os
import sys
from typing import Dict, List, Any, Callable, Optional

# Import the dependency tracker
from dependency_tracker import (
    DependencyResolver, get_dependency_tracker,
    enhance_implementation_prompt, analyze_project_dependencies,
    generate_dependency_report
)

# Store original function references
_original_implement_single_file = None
_original_prioritize_files = None

def initialize_dependency_tracking(project_builder_module, project_dir: str):
    """
    Initialize dependency tracking by storing original functions and patching them.
    
    Args:
        project_builder_module: The project_builder module
        project_dir: The directory where the project is being built
    """
    global _original_implement_single_file, _original_prioritize_files
    
    # Store original functions
    _original_implement_single_file = project_builder_module.implement_single_file
    _original_prioritize_files = project_builder_module.prioritize_files
    
    # Initialize the resolver
    resolver = DependencyResolver(project_dir)
    
    # Apply monkey patches
    project_builder_module.implement_single_file = dependency_aware_implement
    project_builder_module.prioritize_files = dependency_aware_prioritize
    
    print("🔍 Dependency tracking enabled. Dependencies will be tracked during file generation.")
    
    return resolver

def restore_original_functions(project_builder_module):
    """
    Restore the original functions after dependency tracking is done.
    
    Args:
        project_builder_module: The project_builder module
    """
    global _original_implement_single_file, _original_prioritize_files
    
    if _original_implement_single_file:
        project_builder_module.implement_single_file = _original_implement_single_file
    
    if _original_prioritize_files:
        project_builder_module.prioritize_files = _original_prioritize_files

def dependency_aware_implement(file_path, structure_content, step_outputs, orchestrator, model_name, file_map):
    """
    Dependency-aware implementation of the implement_single_file function.
    This is used to replace the original function during monkey patching.
    """
    global _original_implement_single_file
    
    if not _original_implement_single_file:
        print("⚠️ Original implement_single_file function not stored. Cannot proceed with dependency tracking.")
        return False
    
    # Get project directory from the file path
    project_dir = os.path.dirname(os.path.abspath(file_path))
    
    # Get or create resolver
    resolver = DependencyResolver(project_dir)
    
    # Create a wrapper for the call_llm function
    original_call_llm = orchestrator.call_llm
    
    def enhanced_call_llm(system_prompt, file_prompt, **kwargs):
        """Enhanced version of call_llm that adds dependency information to prompts"""
        # Only enhance if it's a file implementation prompt
        if "File Implementation:" in file_prompt:
            enhanced_prompt = enhance_implementation_prompt(file_path, file_prompt)
            return original_call_llm(system_prompt, enhanced_prompt, **kwargs)
        return original_call_llm(system_prompt, file_prompt, **kwargs)
    
    try:
        # Replace call_llm temporarily
        orchestrator.call_llm = enhanced_call_llm
        
        # Call original implementation
        result = _original_implement_single_file(file_path, structure_content, step_outputs, 
                                               orchestrator, model_name, file_map)
        
        # Check dependencies after implementation
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
        # Restore original function
        orchestrator.call_llm = original_call_llm

def dependency_aware_prioritize(files, implementation_plan):
    """
    Dependency-aware implementation of the prioritize_files function.
    This is used to replace the original function during monkey patching.
    """
    global _original_prioritize_files
    
    if not _original_prioritize_files:
        print("⚠️ Original prioritize_files function not stored. Using basic prioritization.")
        return files
    
    # Get original prioritization
    initial_priority = _original_prioritize_files(files, implementation_plan)
    
    # Then enhance with dependency-based prioritization
    graph = get_dependency_tracker()
    if graph is None:
        return initial_priority
    
    # Prioritize based on dependencies
    from dependency_tracker import prioritize_files_by_dependencies
    final_priority = prioritize_files_by_dependencies(initial_priority)
    
    # If the order changed, log it
    if final_priority != initial_priority:
        print("📋 Reprioritized implementation order based on dependencies")
    
    return final_priority

def perform_final_dependency_check(project_dir: str, orchestrator, model_name: str) -> bool:
    """
    Perform a final dependency check on the generated project and fix issues.
    
    Args:
        project_dir: The project directory
        orchestrator: The AI orchestrator to use for fixing issues
        model_name: The model name to use
        
    Returns:
        True if all dependencies are resolved, False otherwise
    """
    print("\n=== Performing Final Dependency Check ===")
    
    # Import these without modifying existing code
    from utils import read_project_files, write_project_file, parse_ai_response_and_apply
    
    # Get the file map
    file_map = read_project_files(project_dir)
    
    # Initialize or get resolver
    resolver = DependencyResolver(project_dir)
    resolver.initialize(file_map)
    
    # Check for unresolved dependencies
    if not resolver.perform_final_check(file_map):
        print("\n⚠️ Found dependency issues. Starting iterative fix process.")
        
        # Define fix function 
        def fix_with_ai(file_path, fix_prompt, file_content):
            """Use the AI to fix dependency issues"""
            system_prompt = """You are an expert software engineer fixing dependency issues.
Your task is to update the file to resolve any dependency issues while maintaining its functionality.
Focus specifically on fixing import statements and module references.

IMPORTANT GUIDELINES:
1. Provide the COMPLETE updated file content, not just the changes
2. Make minimal changes needed to fix the dependency issues
3. Output the entire fixed file content inside === File: path/to/file === markers
4. Be consistent with the project's module structure and naming conventions"""
            
            response = orchestrator.call_llm(system_prompt, fix_prompt, temperature=0.0)
            
            # Process the response
            fixed_files = {}
            parse_ai_response_and_apply(response, fixed_files)
            
            # Return the fixed content
            if file_path in fixed_files and hasattr(fixed_files[file_path], 'content'):
                return fixed_files[file_path].content
            print(f"⚠️ Failed to parse AI response for {file_path}. Keeping original content.")
            return file_content
        
        # Perform iterative dependency resolution
        success = resolver.iterate_fixes(file_map, fix_with_ai)
        
        # Write the updated files
        for file_path, file_obj in file_map.items():
            write_project_file(project_dir, file_obj)
        
        if success:
            print("\n✅ All dependencies have been resolved successfully!")
        else:
            print("\n⚠️ Some dependencies could not be resolved. Check the dependency report.")
        
        # Generate a final report
        report_path = os.path.join(project_dir, "dependency_report.md")
        generate_dependency_report(report_path)
        print(f"📊 Dependency report saved to: {report_path}")
        
        return success
    else:
        print("\n✅ All dependencies are already resolved! Your project is ready to run.")
        return True

def fix_existing_project_dependencies(project_dir: str, model_name: str) -> bool:
    """
    Fix dependencies in an existing project.
    
    Args:
        project_dir: Path to the project directory
        model_name: Model to use for AI-based fixing
        
    Returns:
        True if successful, False otherwise
    """
    if not os.path.exists(project_dir):
        print(f"Error: Project directory {project_dir} does not exist.")
        return False
    
    print(f"Fixing dependencies in project: {project_dir}")
    
    # Import AI orchestrator without modifying existing code
    from ai_clients import AIOrchestrator
    orchestrator = AIOrchestrator(model_name)
    
    # Perform the dependency check and fixing
    return perform_final_dependency_check(project_dir, orchestrator, model_name) 