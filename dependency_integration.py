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

# Import utility classes
from utils import ProjectFile

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
    # Import here to avoid circular imports
    from utils import ProjectFile, parse_ai_response_and_apply, write_project_file
    
    global _original_implement_single_file
    
    if not _original_implement_single_file:
        print("⚠️ Original implement_single_file function not stored. Cannot proceed with dependency tracking.")
        return False
    
    # Check if the file path is valid to avoid deep recursion on incorrect paths
    if not file_path or len(file_path) < 3:
        print(f"⚠️ Invalid file path provided: '{file_path}'")
        return False
    
    try:
        # Get the resolver - use a simple path extraction to avoid recursion in os.path.dirname
        parts = file_path.replace('\\', '/').split('/')
        if len(parts) > 1:
            # Get path components without using os.path to avoid recursion
            project_dir = '/'.join(parts[:-1])
        else:
            project_dir = "."  # Current directory as fallback
        
        # Initialize resolver with the project directory
        resolver = None
        try:
            resolver = DependencyResolver(project_dir)
        except Exception as e:
            print(f"Error initializing dependency resolver: {e}")
        
        # Create a wrapper for the call_llm function
        original_call_llm = orchestrator.call_llm
        
        def enhanced_call_llm(system_prompt, file_prompt, **kwargs):
            """Enhanced version of call_llm that adds dependency information to prompts"""
            # Only enhance if it's a file implementation prompt and resolver exists
            if resolver and "File Implementation:" in file_prompt:
                try:
                    enhanced_prompt = enhance_implementation_prompt(file_path, file_prompt)
                    return original_call_llm(system_prompt, enhanced_prompt, **kwargs)
                except Exception as e:
                    print(f"Error enhancing prompt with dependencies: {e}")
                    return original_call_llm(system_prompt, file_prompt, **kwargs)
            return original_call_llm(system_prompt, file_prompt, **kwargs)
        
        # Replace call_llm temporarily
        orchestrator.call_llm = enhanced_call_llm
        
        # Skip the recursive call and delegate to the original function in project_builder
        # Get the original module reference to avoid the monkeypatched function
        import project_builder
        
        # Use the function definition from project_builder, bypassing the monkeypatch
        from inspect import getsource, getmodule
        
        # Direct implementation based on the original code
        print(f"\nImplementing file: {file_path}")
        
        # Build focused context for this file - simplified implementation
        file_prompt = f"""# File Implementation: {file_path}

IMPORTANT: You are implementing a production-ready source file that must be complete,
robust, and maintainable. 

## Project Context
{step_outputs.get(0, '(No vision provided)')}

## Project Structure
The file is part of the following project structure:
```
{structure_content[:2000] if structure_content else '(No structure provided)'}
```

## Implementation Requirements
1. Code Quality: 
   - Production-ready, professional code with MEANINGFUL and COMPREHENSIVE functionality
   - Not just empty placeholders or minimal implementations
   - Include substantive functionality appropriate for the file's purpose
   - For __init__ files, include proper imports and exports

2. Technical Requirements:
   - Follow architectural decisions in the structure document
   - Implement COMPLETE functionality with proper error handling
   - Write thorough implementation with actual business logic
   - Code should be ready to run with minimal additional work

3. Include:
   - ALL necessary imports
   - Proper error handling
   - Meaningful comments (not just placeholders)
   - Actual business logic implementations (not just function stubs)
   - Proper function parameters and return values
   - Integration with related components

Output your implementation in `=== File: {file_path} ===`"""

        try:
            # Call the LLM to implement this file
            system_prompt = """You are an expert software engineer implementing a critical file in a complex project.
CRITICAL INSTRUCTIONS:
1. Write COMPLETE, FUNCTIONAL code with all necessary imports and error handling
2. DO NOT create minimal or placeholder implementations - write FULL-FEATURED code
3. Your implementation should be SUBSTANTIVE with real business logic
4. DO NOT use markdown formatting in your response - provide raw code only
5. DO NOT wrap your code in triple backticks (```) - your response should be the actual code file
6. When implementing __init__.py files, include proper docstrings and necessary imports
7. For empty __init__.py files, still include a package docstring at minimum
8. Write code that would satisfy a demanding senior engineer reviewing your work
9. JUST WRITE YOUR CODE AND NOTHING ELSE. YOU ARE WRITING CODE DIRECTLY TO A FILE AND DO NOT NEED FORMATTING.

Your output will be directly saved to a file without any processing."""
            
            max_output_tokens = 64000
            temperature = 0.0
            
            ai_response = orchestrator.call_llm(system_prompt, file_prompt, max_tokens=max_output_tokens, temperature=temperature)
            
            if not ai_response or ai_response.startswith("ERROR"):
                print(f"Error implementing {file_path}: {ai_response}")
                return False
            
            # Pre-process the response to handle possible markdown wrapping
            if ai_response and "```" in ai_response:
                print(f"DEBUG: AI response contains markdown code blocks, attempting to pre-process")
                
                # Add file marker if missing - helps parser identify the file
                if not "=== File:" in ai_response and not file_path in file_map:
                    # Create a new entry in the file map for the current file
                    file_map[file_path] = ProjectFile(file_path, "")
            
            # Apply the response to the file map
            parse_ai_response_and_apply(ai_response, file_map)
            
            # Check if the file was actually updated
            if file_path not in file_map or not file_map[file_path].content.strip():
                print(f"WARNING: File {file_path} is empty or wasn't properly updated")
                
                # Try to extract content from the raw response if it contains code
                if ai_response and "```" in ai_response:
                    # Simple extraction of code between triple backticks
                    start_idx = ai_response.find("```")
                    if start_idx != -1:
                        # Find the end of the first line
                        first_newline = ai_response.find("\n", start_idx)
                        if first_newline != -1:
                            # Find the closing backticks
                            end_idx = ai_response.rfind("```")
                            if end_idx > first_newline:
                                # Extract content between backticks, excluding the backticks themselves
                                code_content = ai_response[first_newline+1:end_idx].strip()
                                # Make sure ProjectFile is imported
                                try:
                                    file_map[file_path] = ProjectFile(file_path, code_content)
                                    print(f"Extracted {len(code_content.splitlines())} lines from markdown code block")
                                except Exception as e:
                                    print(f"Error creating ProjectFile: {e}")
            
            # Special handling for __init__.py files that might be empty or have markdown issues
            if file_path.endswith('__init__.py') and (file_path not in file_map or not file_map[file_path].content.strip()):
                # Add proper standard content for __init__.py
                package_path = file_path.replace('\\', '/').rsplit('/', 1)[0] if '/' in file_path else ""
                package_name = package_path.split("/")[-1] if package_path else "root"
                
                # More substantial template with actual imports and exports
                standard_init_content = f'''"""
{package_path} package

This module serves as an entry point to the {package_name} package.
It provides centralized access to the package's functionality through
convenient imports and exports, allowing users to access components through
a clean, organized API.
"""

import os
import sys
from typing import Dict, List, Optional, Any

# Import all submodules to make them available for import from this package
# The specific imports will depend on the actual modules available in the package

# Define __all__ to explicitly declare public exports
__all__ = []

# Module metadata
__version__ = '0.1.0'
__author__ = 'Your Organization'

# Package initialization
def initialize():
    """Initialize the {package_name} package, performing any necessary setup."""
    # Setup code would go here
    pass
'''
                try:
                    file_map[file_path] = ProjectFile(file_path, standard_init_content)
                    print(f"DEBUG: Added robust boilerplate to {file_path}")
                except Exception as e:
                    print(f"Error adding boilerplate to {file_path}: {e}")
            
            # For JS __init__ files that might have markdown issues
            if file_path.endswith('__init__.js') and (file_path not in file_map or not file_map[file_path].content.strip()):
                package_path = file_path.replace('\\', '/').rsplit('/', 1)[0] if '/' in file_path else ""
                component_name = package_path.split("/")[-1] if package_path else "root"
                
                # Use a simpler JS module template to avoid f-string issues
                standard_init_content = '''/**
 * Component package
 * 
 * This module serves as the main entry point to the components in this directory.
 * It provides a centralized location for exporting all components,
 * making them easily importable from other parts of the application.
 */

// Import components from this directory
// Example:
// import SomeComponent from './SomeComponent';
// import AnotherComponent from './AnotherComponent';

// Export components 
const components = {
  // Add component exports here
  getComponentInfo: function(name) {
    return {
      name: name,
      version: '1.0.0'
    };
  }
};

// Default export
export default components;

// Named exports for specific components
// export { SomeComponent, AnotherComponent };
'''
                try:
                    file_map[file_path] = ProjectFile(file_path, standard_init_content)
                    print(f"DEBUG: Added robust JS boilerplate to {file_path}")
                except Exception as e:
                    print(f"Error adding boilerplate to {file_path}: {e}")
            
            # Write all files after each implementation
            for rel_path, pf in file_map.items():
                write_project_file(project_builder.PROJECT_DIR, pf)
            
            print(f"✅ Successfully implemented {file_path}")
            result = True
        except Exception as e:
            print(f"❌ Failed to implement {file_path}: {str(e)}")
            result = False
        
        # Check dependencies after implementation
        if result and resolver and file_path in file_map:
            try:
                deps = resolver.check_file(file_path, file_map[file_path].content)
                if deps:
                    print(f"⚠️ Found {len(deps)} unresolved dependencies in {file_path}:")
                    for dep in deps:
                        print(f"  - {dep.module_name} ({dep.import_type})")
                else:
                    print(f"✅ No dependency issues found in {file_path}")
            except Exception as e:
                print(f"Error checking dependencies: {e}")
        elif file_path in file_map and not result:
            # Still try to check dependencies even if implementation "failed"
            try:
                if resolver:
                    deps = resolver.check_file(file_path, file_map[file_path].content)
                    if deps:
                        print(f"⚠️ Found {len(deps)} unresolved dependencies in partially-implemented {file_path}")
                    else:
                        print(f"✅ No dependency issues in partially-implemented {file_path}")
            except Exception as e:
                print(f"Error checking dependencies in failed implementation: {e}")
        
        return result
    except Exception as e:
        print(f"Error in dependency-aware implementation: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Always restore original function to prevent issues
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
    
    # Get original prioritization - Call directly from module, not through the same function name
    # Define a simple prioritization to avoid recursion
    def basic_prioritize(file_list, plan):
        core_files = []
        config_files = []
        other_files = []
        
        for file in file_list:
            if "config" in file or "settings" in file:
                config_files.append(file)
            elif "core" in file or "main" in file or "__init__" in file:
                core_files.append(file)
            else:
                other_files.append(file)
        
        return core_files + config_files + other_files
    
    # Use the basic prioritization instead of recursive call
    initial_priority = basic_prioritize(files, implementation_plan)
    
    # Then enhance with dependency-based prioritization
    graph = get_dependency_tracker()
    if graph is None:
        return initial_priority
    
    try:
        # Prioritize based on dependencies if the module is available
        from dependency_tracker import prioritize_files_by_dependencies
        final_priority = prioritize_files_by_dependencies(initial_priority)
        
        # If the order changed, log it
        if final_priority != initial_priority:
            print("📋 Reprioritized implementation order based on dependencies")
            
        return final_priority
    except Exception as e:
        print(f"Error during dependency prioritization: {e}")
        return initial_priority

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