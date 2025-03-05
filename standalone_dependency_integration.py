"""
Standalone Dependency Integration Module

This module integrates the dependency tracking system with the existing project_builder workflow
without modifying its core functionality. It works by hooking into the project builder's API
using monkey patching to track and resolve dependencies during file generation.
"""

import os
import sys
import importlib
import types
from typing import Dict, List, Any, Callable, Optional, Union

# Import the dependency tracker
from standalone_dependency_tracker import (
    DependencyResolver, get_dependency_tracker,
    enhance_implementation_prompt, analyze_project_dependencies,
    generate_dependency_report, prioritize_files_by_dependencies
)

# Storage for original function references
_original_functions = {}

def initialize_dependency_tracking(project_dir: str):
    """
    Initialize dependency tracking for a project.
    
    Args:
        project_dir: The directory where the project is being built
    """
    # Create a resolver instance
    resolver = DependencyResolver(project_dir)
    
    # Store it in global state for access by patched functions
    _set_global_state('resolver', resolver)
    _set_global_state('project_dir', project_dir)
    
    # Initialize file map
    _set_global_state('file_map', {})
    
    # Track which files have been implemented
    _set_global_state('implemented_files', set())
    
    return resolver


def integrate_with_project_builder():
    """
    Integrate dependency tracking with the project_builder module.
    This patches relevant functions but does not modify any code.
    
    Returns:
        True if integration was successful, False otherwise
    """
    try:
        # First, try to import the project_builder module
        try:
            project_builder = importlib.import_module('project_builder')
        except ImportError:
            print("Warning: project_builder module not found in path. Integration will only activate when it's imported.")
            project_builder = None
        
        # Also look for orchestrator
        try:
            orchestrator = importlib.import_module('orchestrator')
        except ImportError:
            orchestrator = None
        
        # If we have a project_builder, patch its functions directly
        if project_builder:
            # Find the implementation function - look for common patterns
            implementation_functions = [
                getattr(project_builder, 'implement_file', None),
                getattr(project_builder, 'implement_single_file', None),
                getattr(project_builder, 'generate_file', None),
                getattr(project_builder, 'generate_file_content', None),
                getattr(project_builder, 'implement_file_with_llm', None)
            ]
            
            # Find the first non-None function
            impl_func = next((f for f in implementation_functions if f is not None), None)
            
            if impl_func:
                # Store the original function
                _original_functions['implement_file'] = impl_func
                
                # Create a patched version
                patched_impl = _create_implementation_patch(impl_func)
                
                # Replace the function
                for name, func in [(n, f) for n, f in project_builder.__dict__.items() if f is impl_func]:
                    setattr(project_builder, name, patched_impl)
                
                print(f"Successfully patched implementation function: {impl_func.__name__}")
            
            # Also look for functions that prioritize file order
            prioritize_functions = [
                getattr(project_builder, 'prioritize_files', None),
                getattr(project_builder, 'order_files', None),
                getattr(project_builder, 'determine_file_order', None)
            ]
            
            # Find the first non-None function
            prio_func = next((f for f in prioritize_functions if f is not None), None)
            
            if prio_func:
                # Store the original function
                _original_functions['prioritize_files'] = prio_func
                
                # Create a patched version
                patched_prio = _create_prioritize_patch(prio_func)
                
                # Replace the function
                for name, func in [(n, f) for n, f in project_builder.__dict__.items() if f is prio_func]:
                    setattr(project_builder, name, patched_prio)
                
                print(f"Successfully patched prioritization function: {prio_func.__name__}")
        
        # If we have an orchestrator, also install hooks there if it has specific functions
        if orchestrator:
            # Look for the function that calls the LLM to implement files
            llm_call_functions = [
                getattr(orchestrator, 'call_llm', None),
                getattr(orchestrator, 'call_llm_for_implementation', None),
                getattr(orchestrator, 'generate_with_llm', None)
            ]
            
            # Find the first non-None function
            llm_func = next((f for f in llm_call_functions if f is not None), None)
            
            if llm_func:
                # Store the original function
                _original_functions['call_llm'] = llm_func
                
                # Create a patched version
                patched_llm = _create_llm_call_patch(llm_func)
                
                # Replace the function
                for name, func in [(n, f) for n, f in orchestrator.__dict__.items() if f is llm_func]:
                    setattr(orchestrator, name, patched_llm)
                
                print(f"Successfully patched LLM call function: {llm_func.__name__}")
        
        return True
    except Exception as e:
        print(f"Error integrating with project_builder: {str(e)}")
        return False


def _create_implementation_patch(original_func):
    """Create a patched version of the implementation function."""
    
    def patched_implementation(*args, **kwargs):
        # Call the original function first
        result = original_func(*args, **kwargs)
        
        # Extract file path and content from the result or arguments
        file_path, file_content = _extract_file_info(result, args, kwargs)
        
        if file_path and file_content:
            # Get the resolver
            resolver = _get_global_state('resolver')
            if resolver:
                # Track the file in our dependency system
                resolver.check_file(file_path, file_content)
                
                # Update our file map
                file_map = _get_global_state('file_map')
                file_map[file_path] = file_content
                _set_global_state('file_map', file_map)
                
                # Mark as implemented
                implemented_files = _get_global_state('implemented_files')
                implemented_files.add(file_path)
                _set_global_state('implemented_files', implemented_files)
        
        return result
    
    # Preserve the function name and docstring
    patched_implementation.__name__ = original_func.__name__
    patched_implementation.__doc__ = original_func.__doc__
    
    return patched_implementation


def _create_prioritize_patch(original_func):
    """Create a patched version of the prioritize files function."""
    
    def patched_prioritize(*args, **kwargs):
        # Call the original function first
        result = original_func(*args, **kwargs)
        
        # Try to extract the list of files
        files_to_prioritize = None
        if isinstance(result, list):
            files_to_prioritize = result
        elif len(args) > 0 and isinstance(args[0], list):
            files_to_prioritize = args[0]
        
        if files_to_prioritize:
            # Apply our additional prioritization
            reprioritized = prioritize_files_by_dependencies(files_to_prioritize)
            
            # If the result is a list, replace it
            if isinstance(result, list):
                return reprioritized
            
            # If the result is something else, leave it as is
            return result
        
        return result
    
    # Preserve the function name and docstring
    patched_prioritize.__name__ = original_func.__name__
    patched_prioritize.__doc__ = original_func.__doc__
    
    return patched_prioritize


def _create_llm_call_patch(original_func):
    """Create a patched version of the LLM call function."""
    
    def patched_llm_call(*args, **kwargs):
        # Extract the prompt and file path
        prompt, file_path = _extract_prompt_info(args, kwargs)
        
        if prompt and file_path:
            # Enhance the prompt with dependency information
            resolver = _get_global_state('resolver')
            if resolver and not isinstance(resolver, dict):
                enhanced_prompt = resolver.enhance_prompt(file_path, prompt)
                
                # Replace the prompt in args or kwargs
                if len(args) > 0 and isinstance(args[0], str):
                    args = (enhanced_prompt,) + args[1:]
                elif 'prompt' in kwargs:
                    kwargs['prompt'] = enhanced_prompt
                elif 'system_prompt' in kwargs:
                    kwargs['system_prompt'] = enhanced_prompt
                elif 'user_prompt' in kwargs:
                    kwargs['user_prompt'] = enhanced_prompt
        
        # Call the original function with updated args
        return original_func(*args, **kwargs)
    
    # Preserve the function name and docstring
    patched_llm_call.__name__ = original_func.__name__
    patched_llm_call.__doc__ = original_func.__doc__
    
    return patched_llm_call


def fix_dependencies(file_map: Dict[str, Any], fix_function: Callable) -> bool:
    """
    Fix dependency issues in the project by applying fixes to files with issues.
    
    Args:
        file_map: A map of file paths to content
        fix_function: A function that takes (file_path, prompt, content) and returns fixed content
        
    Returns:
        True if all dependencies were resolved, False otherwise
    """
    resolver = _get_global_state('resolver')
    if not resolver:
        project_dir = _get_global_state('project_dir') or os.getcwd()
        resolver = DependencyResolver(project_dir)
        _set_global_state('resolver', resolver)
    
    return resolver.iterate_fixes(file_map, fix_function)


def generate_final_dependency_report(output_file: str = None) -> str:
    """
    Generate a final dependency report for the project.
    
    Args:
        output_file: If provided, write the report to this file
        
    Returns:
        The report content as a string
    """
    file_map = _get_global_state('file_map')
    project_dir = _get_global_state('project_dir') or os.getcwd()
    
    # Analyze dependencies
    dependency_graph = analyze_project_dependencies(project_dir, file_map)
    
    # Generate report
    return dependency_graph.generate_dependency_report(output_file)


def _extract_file_info(result, args, kwargs):
    """Extract file path and content from function arguments and result."""
    file_path = None
    file_content = None
    
    # Try to extract from the result
    if isinstance(result, dict):
        if 'path' in result and 'content' in result:
            file_path = result['path']
            file_content = result['content']
        elif 'file_path' in result and 'content' in result:
            file_path = result['file_path']
            file_content = result['content']
    elif isinstance(result, tuple) and len(result) >= 2:
        file_path, file_content = result[0], result[1]
    
    # If not found in result, check args
    if not file_path and len(args) >= 1:
        if isinstance(args[0], str):
            file_path = args[0]
            
            # Try to find content in other args
            if len(args) >= 2 and isinstance(args[1], str):
                file_content = args[1]
    
    # If still not found, check kwargs
    if not file_path and 'file_path' in kwargs:
        file_path = kwargs['file_path']
    
    if not file_content and 'file_content' in kwargs:
        file_content = kwargs['file_content']
    elif not file_content and 'content' in kwargs:
        file_content = kwargs['content']
    
    return file_path, file_content


def _extract_prompt_info(args, kwargs):
    """Extract prompt and file path from args and kwargs."""
    prompt = None
    file_path = None
    
    # Check args for prompt
    if len(args) >= 1 and isinstance(args[0], str):
        prompt = args[0]
    
    # Check kwargs for prompt
    if not prompt:
        for key in ['prompt', 'system_prompt', 'user_prompt']:
            if key in kwargs and isinstance(kwargs[key], str):
                prompt = kwargs[key]
                break
    
    # Check kwargs for file_path
    for key in ['file_path', 'file', 'path']:
        if key in kwargs and isinstance(kwargs[key], str):
            file_path = kwargs[key]
            break
    
    # If no file path is found directly, try to extract it from the prompt
    if not file_path and prompt:
        # Look for patterns like "Implement file: path/to/file.py" in the prompt
        import re
        file_patterns = [
            r"Implement file[:\s]+([^\s]+\.[a-zA-Z]+)",
            r"Generate file[:\s]+([^\s]+\.[a-zA-Z]+)",
            r"Create file[:\s]+([^\s]+\.[a-zA-Z]+)",
            r"File: ([^\s]+\.[a-zA-Z]+)",
            r"PATH: ([^\s]+\.[a-zA-Z]+)"
        ]
        
        for pattern in file_patterns:
            match = re.search(pattern, prompt)
            if match:
                file_path = match.group(1)
                break
    
    return prompt, file_path


# Global state management for sharing objects between patched functions
_global_state = {}

def _set_global_state(key, value):
    """Set a value in the global state."""
    _global_state[key] = value

def _get_global_state(key):
    """Get a value from the global state."""
    return _global_state.get(key)


# Public API functions

def activate(project_dir: str = None):
    """
    Activate dependency tracking for the project builder.
    
    Args:
        project_dir: The directory where the project is being built (defaults to current directory)
        
    Returns:
        True if activation was successful, False otherwise
    """
    if project_dir is None:
        project_dir = os.getcwd()
    
    # Initialize tracking
    initialize_dependency_tracking(project_dir)
    
    # Integrate with the project builder
    return integrate_with_project_builder()


def deactivate():
    """
    Deactivate dependency tracking and restore original functions.
    
    Returns:
        True if deactivation was successful, False otherwise
    """
    try:
        # Restore original functions if they exist
        if 'implement_file' in _original_functions:
            # Find the project_builder module
            project_builder = sys.modules.get('project_builder')
            if project_builder:
                # Find the current patched function
                for name, func in project_builder.__dict__.items():
                    if func.__name__ == _original_functions['implement_file'].__name__:
                        # Restore the original
                        setattr(project_builder, name, _original_functions['implement_file'])
        
        if 'prioritize_files' in _original_functions:
            # Find the project_builder module
            project_builder = sys.modules.get('project_builder')
            if project_builder:
                # Find the current patched function
                for name, func in project_builder.__dict__.items():
                    if func.__name__ == _original_functions['prioritize_files'].__name__:
                        # Restore the original
                        setattr(project_builder, name, _original_functions['prioritize_files'])
        
        if 'call_llm' in _original_functions:
            # Find the orchestrator module
            orchestrator = sys.modules.get('orchestrator')
            if orchestrator:
                # Find the current patched function
                for name, func in orchestrator.__dict__.items():
                    if func.__name__ == _original_functions['call_llm'].__name__:
                        # Restore the original
                        setattr(orchestrator, name, _original_functions['call_llm'])
        
        # Clear global state
        _global_state.clear()
        _original_functions.clear()
        
        return True
    except Exception as e:
        print(f"Error deactivating dependency tracking: {str(e)}")
        return False


def get_project_dependency_graph():
    """
    Get the current dependency graph for the project.
    
    Returns:
        The DependencyGraph instance or None if not initialized
    """
    resolver = _get_global_state('resolver')
    if resolver:
        return resolver.dependency_graph
    return None


def enhance_prompt(file_path: str, prompt: str) -> str:
    """
    Enhance a prompt with dependency information.
    
    Args:
        file_path: The file being implemented
        prompt: The original prompt
        
    Returns:
        Enhanced prompt with dependency information
    """
    resolver = _get_global_state('resolver')
    if resolver:
        return resolver.enhance_prompt(file_path, prompt)
    return prompt


def get_unresolved_dependencies():
    """
    Get a list of unresolved dependencies for the project.
    
    Returns:
        List of unresolved dependencies
    """
    resolver = _get_global_state('resolver')
    if resolver:
        return resolver.dependency_graph.get_unresolved_dependencies()
    return []


def get_files_needing_fixes():
    """
    Get a map of files that need dependency fixes.
    
    Returns:
        Dict mapping file paths to lists of unresolved dependencies
    """
    resolver = _get_global_state('resolver')
    if resolver:
        return resolver.get_files_needing_fixes()
    return {}


if __name__ == "__main__":
    print("Standalone Dependency Integration - Import this module to use its functionality") 