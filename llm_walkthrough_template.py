#!/usr/bin/env python3

"""
llm_walkthrough_template.py

A modular template for creating LLM-guided workflows that:
1) Takes a user's high-level description/requirements
2) Walks an LLM through a multi-step, multi-substep process
3) Produces structured outputs at each step
4) Creates files and directories as needed
5) Maintains context between steps

This template can be adapted for specialized workflows such as:
- Project building (like the current project_builder.py)
- Book writing (chapters, outlines, character development)
- Game design (game mechanics, levels, storylines)
- Research papers (literature review, methodology, discussion)
- Business plans (market analysis, financial projections)
- And many other structured creative or analytical processes

IMPORTANT: This template is meant to be loaded with a specific workflow configuration.
Use the load_workflow_config() function to load a template_config file for your desired workflow.
"""

import os
import sys
import importlib.util
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json
import time
import subprocess
import re

from ai_clients import AIOrchestrator
from utils import ProjectFile, SubStep, read_project_files, write_project_file, parse_ai_response_and_apply

# Configuration - Default values
DEFAULT_CONFIG = {
    "workflow_name": "Custom Workflow",
    "output_dir": "output",
    "docs_subdir": "docs",
    "workflow_steps": []  # Empty by default, must be loaded from a config
}

def build_user_prompt(step_index: int, step_info: dict, sub_step_index: int, sub_step: SubStep, 
                      step_outputs: Dict[int, str], sub_step_outputs: Dict[str, str], 
                      vision: str, docs_dir: str, workflow_steps: list) -> str:
    """
    Build the user prompt for the current substep, including relevant context.
    
    Args:
        step_index: Current step number (1-based)
        step_info: Current step information
        sub_step_index: Current substep index
        sub_step: SubStep object
        step_outputs: Dictionary of outputs from previous steps
        sub_step_outputs: Dictionary of outputs from previous substeps
        vision: The project vision
        docs_dir: Directory for documentation
        workflow_steps: List of all workflow steps
    
    Returns:
        String prompt for the current substep
    """
    # Format the substep prompt
    formatted_substep_prompt = sub_step.prompt.format(vision=vision)
    
    # Build the base prompt
    prompt = f"# {step_info['phase_name']} - Substep {sub_step.id}: {sub_step.name}\n\n"
    prompt += f"## Project Vision:\n{vision[:300]}...\n\n"  # Limit vision size
    
    # Start with minimal context
    previous_outputs = ""
    
    # For steps beyond the first, include only the MOST relevant previous step
    # Only include the step that is most relevant to the current task
    if step_index > 1:
        # For architecture step, include project planning
        # For structure step, include architecture
        # And so on - only include the immediately preceding step
        relevant_step = step_index - 1
        if relevant_step in step_outputs:
            step_output = step_outputs[relevant_step]
            # Severely limit context size
            max_chars = 300
            if len(step_output) > max_chars:
                step_output = step_output[:max_chars] + "...[content truncated]"
            prev_step_info = f"Step {relevant_step}: {workflow_steps[relevant_step-1]['phase_name']}"
            previous_outputs += f"### Previous Step ({prev_step_info}):\n{step_output}\n\n"
    
    # For substeps beyond the first in current step, include ONLY the immediately previous substep
    if sub_step_index > 0:
        prev_sub_step = step_info["sub_steps"][sub_step_index - 1]
        sub_step_key = f"step{step_index}_{prev_sub_step.id}"
        if sub_step_key in sub_step_outputs:
            prev_output = sub_step_outputs[sub_step_key]
            # More aggressive truncation
            max_chars = 300
            if len(prev_output) > max_chars:
                prev_output = prev_output[:max_chars] + "...[content truncated]"
            previous_outputs += f"### Previous Substep ({prev_sub_step.id}: {prev_sub_step.name}):\n{prev_output}\n\n"
    
    # Add previous outputs if there are any
    if previous_outputs:
        prompt += f"## Minimal Context from Previous Work:\n{previous_outputs}\n"
    
    # Add task instructions
    prompt += f"## Your Task for {sub_step.id}: {sub_step.name}\n\n{formatted_substep_prompt}\n\n"
    
    # Add final guidance - simplified to reduce tokens
    prompt += """
Please focus on this specific substep thoroughly and professionally.
"""
    
    return prompt

def execute_substep(orchestrator: AIOrchestrator, step_info: dict, step_index: int, 
                   sub_step_index: int, sub_step: SubStep, file_map: Dict[str, ProjectFile], 
                   step_outputs: Dict[int, str], sub_step_outputs: Dict[str, str],
                   vision: str, docs_dir: str, workflow_steps: list) -> bool:
    """Execute a single substep in the workflow process.
    
    Args:
        orchestrator: AIOrchestrator instance for LLM calls
        step_info: Current step information
        step_index: Current step number (1-based)
        sub_step_index: Current substep index
        sub_step: SubStep object
        file_map: Dictionary mapping relative file paths to ProjectFile objects
        step_outputs: Dictionary of outputs from previous steps
        sub_step_outputs: Dictionary of outputs from previous substeps
        vision: The project vision
        docs_dir: Directory for documentation
        workflow_steps: List of all workflow steps
    
    Returns:
        True if substep execution succeeded, False otherwise
    """
    print(f"Executing substep {sub_step.id}: {sub_step.name}")
    
    try:
        # Build prompt for this substep
        prompt = build_user_prompt(step_index, step_info, sub_step_index, sub_step, 
                                step_outputs, sub_step_outputs, vision, docs_dir, workflow_steps)
        
        # Create a temporary map for just this substep's files
        # This is crucial to prevent token overload 
        current_step_files = {}
        
        # Only include a very limited set of files in context
        if file_map:
            # Only include files likely to be relevant to this substep, max 2-3 files
            # Prefer files from the current step, or key architecture files
            file_count = 0
            for file_path, file_obj in file_map.items():
                # Use heuristics to determine relevance to current substep
                if (file_path.startswith(f"step{step_index}/") or 
                    "architecture" in file_path or 
                    "structure" in file_path) and file_count < 2:
                    # Further limit file content size
                    if len(file_obj.content) > 300:
                        truncated_content = file_obj.content[:300] + "...[content truncated]"
                        current_step_files[file_path] = ProjectFile(
                            path=file_path,
                            content=truncated_content,
                            description=file_obj.description
                        )
                    else:
                        current_step_files[file_path] = file_obj
                    file_count += 1
        
        # Add file context to prompt if needed
        if current_step_files:
            file_context = "\n\n## Relevant Files:\n"
            for file_path, file_obj in current_step_files.items():
                file_context += f"\n### {file_path}:\n"
                file_context += f"{file_obj.content}\n"
            
            # Only add file context if it's not too large
            if len(file_context) < 500:
                prompt += file_context
        
        # Call the LLM with the prompt
        response = orchestrator.call_llm(prompt)
        
        # Process response and update file map
        sub_step_key = f"step{step_index}_{sub_step.id}"
        sub_step_outputs[sub_step_key] = response
        
        # Write step output to markdown file
        os.makedirs(docs_dir, exist_ok=True)
        with open(os.path.join(docs_dir, f"step{step_index}_{sub_step.id}.md"), "w") as f:
            f.write(f"# {step_info['phase_name']} - {sub_step.id}: {sub_step.name}\n\n")
            f.write(response)
        
        # Process files if needed
        files_to_update = extract_files_from_response(response)
        for file_path, content in files_to_update.items():
            if file_path in file_map:
                # Update existing file
                file_map[file_path].content = content
            else:
                # Create new file
                file_map[file_path] = ProjectFile(path=file_path, content=content)
            
            # Write file to disk
            full_path = file_path
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w") as f:
                f.write(content)
        
        return True
        
    except Exception as e:
        print(f"Error in substep {sub_step.id}: {str(e)}")
        return False

def run_workflow(vision: str, model_name: str, config: dict, start_step: int = 1, start_substep: str = None):
    """
    Run the workflow defined in the configuration.
    
    Args:
        vision: The project vision or description
        model_name: Name of the model to use
        config: The workflow configuration dictionary
        start_step: The step to start from (default is 1)
        start_substep: Optional substep ID to start from (e.g., "2B")
    """
    print(f"\n{'='*50}")
    print(f"Starting {config['WORKFLOW_NAME']} Workflow")
    print(f"{'='*50}\n")
    
    # Extract configuration variables
    workflow_name = config.get('WORKFLOW_NAME', 'Custom Workflow')
    output_dir = config.get('OUTPUT_DIR', 'output')
    docs_subdir = config.get('DOCS_SUBDIR', 'docs')
    workflow_steps = config.get('WORKFLOW_STEPS', [])
    
    # Create directories
    os.makedirs(output_dir, exist_ok=True)
    docs_dir = os.path.join(output_dir, docs_subdir)
    os.makedirs(docs_dir, exist_ok=True)
    
    # Initialize AI orchestrator
    orchestrator = AIOrchestrator(model_name)
    
    # Prepare data structures
    file_map = {}
    step_outputs = {}
    sub_step_outputs = {}
    
    # Load existing outputs if starting from a step greater than 1
    if start_step > 1:
        print(f"Resuming from step {start_step}{f', substep {start_substep}' if start_substep else ''}")
        for prev_step in range(1, start_step):
            # Try to load previous step outputs from markdown files
            step_md_path = os.path.join(docs_dir, f"step{prev_step}_output.md")
            if os.path.exists(step_md_path):
                with open(step_md_path, "r") as f:
                    step_outputs[prev_step] = f.read()
                print(f"Loaded previous output for step {prev_step}")
    
    # Process each step
    for step_index, step_info in enumerate(workflow_steps, start=1):
        if step_index < start_step:
            continue
        
        print(f"\n{'-'*50}")
        print(f"Step {step_index}: {step_info['phase_name']}")
        print(f"{'-'*50}")
        
        # Process substeps
        start_substep_index = 0
        if start_step == step_index and start_substep:
            # Find the index of the starting substep
            for i, sub_step in enumerate(step_info["sub_steps"]):
                if sub_step.id == start_substep:
                    start_substep_index = i
                    break
        
        sub_step_outputs_for_step = []
        
        for sub_step_index, sub_step in enumerate(step_info["sub_steps"]):
            if step_index == start_step and sub_step_index < start_substep_index:
                continue
            
            success = execute_substep(
                orchestrator,
                step_info,
                step_index,
                sub_step_index,
                sub_step,
                file_map,
                step_outputs,
                sub_step_outputs,
                vision,
                docs_dir,
                workflow_steps
            )
            
            if not success:
                print(f"Failed during substep {sub_step.id}: {sub_step.name}")
                print(f"Use --start-step {step_index} --start-substep {sub_step.id} to resume from this point")
                return False
            
            # Store substep output
            sub_step_outputs_for_step.append(sub_step_outputs[f"step{step_index}_{sub_step.id}"])
        
        # Combine all substep outputs for this step
        combined_output = "\n\n".join(sub_step_outputs_for_step)
        step_outputs[step_index] = combined_output
        
        # Write combined step output to markdown file
        with open(os.path.join(docs_dir, f"step{step_index}_output.md"), "w") as f:
            f.write(f"# Step {step_index}: {step_info['phase_name']}\n\n")
            f.write(combined_output)
    
    print(f"\n{'='*50}")
    print(f"Workflow completed successfully!")
    print(f"{'='*50}")
    print(f"Output directory: {os.path.abspath(output_dir)}")
    print(f"Documentation: {os.path.abspath(docs_dir)}")
    
    return True

def load_workflow_config(config_path: str) -> dict:
    """Load a workflow configuration from a Python module.
    
    Args:
        config_path: Path to the configuration Python file
        
    Returns:
        A dictionary containing the workflow configuration
    """
    # Validate the file exists
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    # Get the module name from the file path
    module_name = os.path.basename(config_path).replace('.py', '')
    
    # Load the module dynamically
    spec = importlib.util.spec_from_file_location(module_name, config_path)
    config_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config_module)
    
    # Check for required configuration attributes
    required_attrs = ["WORKFLOW_NAME", "OUTPUT_DIR", "DOCS_SUBDIR", "WORKFLOW_STEPS"]
    for attr in required_attrs:
        if not hasattr(config_module, attr):
            raise ValueError(f"Config file is missing required attribute: {attr}")
    
    # Create and return the configuration dictionary
    config = {
        "workflow_name": config_module.WORKFLOW_NAME,
        "output_dir": config_module.OUTPUT_DIR,
        "docs_subdir": config_module.DOCS_SUBDIR,
        "workflow_steps": config_module.WORKFLOW_STEPS
    }
    
    return config

# Function to list available workflow configurations
def list_available_workflows():
    """List all available workflow configuration files in the configs directory."""
    config_dir = Path("configs")
    if not config_dir.exists():
        print("No configs directory found. Create a 'configs' directory with workflow configuration files.")
        return []
    
    configs = []
    for file in config_dir.glob("*_config.py"):
        configs.append(file.name)
    
    return configs

# Example usage in orchestrator.py
"""
def run_llm_workflow(workflow_type, vision, model_name, start_step=1, start_substep=None):
    '''Run an LLM workflow of the specified type.'''
    
    from llm_walkthrough_template import load_workflow_config, run_workflow
    
    # Construct the path to the workflow config file
    config_path = f"configs/{workflow_type}_config.py"
    
    try:
        # Load the workflow configuration
        config = load_workflow_config(config_path)
        
        # Run the workflow with the loaded configuration
        run_workflow(vision, model_name, config, start_step, start_substep)
        
    except FileNotFoundError:
        print(f"Error: Workflow type '{workflow_type}' not found. Available workflow types:")
        available_workflows = list_available_workflows()
        for workflow in available_workflows:
            print(f"  - {workflow.replace('_config.py', '')}")
    except Exception as e:
        print(f"Error running workflow: {e}")
"""

def extract_files_from_response(response: str) -> Dict[str, str]:
    """
    Extract file contents from an AI response.
    
    Args:
        response: The LLM response text
        
    Returns:
        Dictionary mapping file paths to file contents
    """
    files = {}
    
    # Common file markers in LLM responses
    file_start_patterns = [
        r'```\s*(?:file|filename):\s*([^\n]+)',  # ```file: filename.py
        r'```(?:python|javascript|typescript|html|css|json|yaml|md|txt)\s+(?:file|filename):\s*([^\n]+)',  # ```python file: filename.py
        r'## File: ([^\n]+)',  # ## File: filename.py
        r'### ([^#\n]+\.[a-zA-Z0-9]+)',  # ### filename.py
        r'```\s*([^`\n]+\.[a-zA-Z0-9]+)'  # ```filename.py
    ]
    
    file_end_pattern = r'```'
    
    # Look for markers indicating file content
    current_file = None
    file_content = []
    
    for line in response.split('\n'):
        if current_file is None:
            # Look for file start
            for pattern in file_start_patterns:
                match = re.search(pattern, line)
                if match:
                    current_file = match.group(1).strip()
                    # If the line contains code after the file name, add it
                    content_start = line.find(current_file) + len(current_file)
                    if content_start < len(line):
                        remaining = line[content_start:].strip()
                        if remaining and not remaining.startswith('```'):
                            file_content.append(remaining)
                    break
        else:
            # We're inside a file block
            if re.search(file_end_pattern, line) and not line.strip().startswith('```'):
                # End of file reached
                files[current_file] = '\n'.join(file_content)
                current_file = None
                file_content = []
            else:
                # Add line to current file content
                file_content.append(line)
    
    # If we have an unclosed file at the end
    if current_file and file_content:
        files[current_file] = '\n'.join(file_content)
    
    return files
