#!/usr/bin/env python3

"""
orchestrator.py

Refined orchestrator that:
1) Asks for an initial user vision
2) Optionally does a Q&A for clarifications
3) Proceeds through the Breakthrough-Idea Walkthrough Framework:
   - Each step guides the LLM through a process for developing breakthrough ideas
   - Feeds back prior steps' outputs for context
   - Prompts the user to proceed, skip, or repeat
   - Can read/write files in the "some_project/" directory
4) Stores each step's output and passes it forward to keep context.

This system walks an LLM through creating a set of blueprints for a breakthrough idea
by following a carefully structured 8-stage framework designed to maximize novelty
while still producing actionable or implementable ideas.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional
import datetime
import argparse
import subprocess
import time

# Define PROJECT_DIR constant at the top of the file
PROJECT_DIR = "some_project"

# # Try to load environment variables from .env file if it exists
# try:
#     from dotenv import load_dotenv
#     load_dotenv()
# except ImportError:
#     print("python-dotenv not installed. Environment variables must be set manually.")

from ai_clients import AIOrchestrator
from utils import ProjectFile, SubStep, read_project_files, write_project_file, parse_ai_response_and_apply

class ProjectFile:
    def __init__(self, path: str, content: str):
        self.path = path
        self.content = content

class SubStep:
    def __init__(self, id: str, name: str, prompt: str):
        """Represents a sub-step within a main step of the framework"""
        self.id = id           # Identifier, e.g. "1A"
        self.name = name       # Name of the sub-step
        self.prompt = prompt   # Specific prompt template for this sub-step

def read_project_files(project_root: str) -> Dict[str, "ProjectFile"]:
    """
    Reads text files from project_root, ignoring .git or obvious binaries.
    Returns a dict: { "relative/path": ProjectFile(...) }
    """
    file_map = {}
    root = Path(project_root)
    if not root.is_dir():
        print(f"Warning: {project_root} is not a directory.")
        return file_map

    for p in root.rglob("*"):
        if p.is_file():
            # Use Path's methods to get platform-independent relative path
            rel_path = str(p.relative_to(root))
            # skip .git or some binaries
            if ".git" in rel_path:
                continue
            if p.suffix in [".png", ".jpg", ".exe", ".dll"]:
                continue
            try:
                content = p.read_text(encoding="utf-8")
                file_map[rel_path] = ProjectFile(rel_path, content)
            except Exception as e:
                print(f"Skipping {rel_path}: {e}")
    return file_map

def write_project_file(project_root: str, pf: ProjectFile):
    """
    Ensures the parent directory exists and writes updated content.
    Added robust error handling and extra debugging.
    """
    # Use pathlib for cross-platform path handling
    target = Path(project_root) / pf.path
    print(f"DEBUG: Attempting to write to {target}")
    
    try:
        # Create all parent directories
        target.parent.mkdir(parents=True, exist_ok=True)
        print(f"DEBUG: Ensured parent directory exists: {target.parent}")
        
        # Write the file
        target.write_text(pf.content, encoding="utf-8")
        print(f"DEBUG: Successfully wrote {len(pf.content)} characters to {target}")
        
        # Verify file exists
        if target.exists():
            print(f"DEBUG: File exists verification passed for {target}")
            print(f"DEBUG: File size: {target.stat().st_size} bytes")
        else:
            print(f"ERROR: File should exist but doesn't: {target}")
            
    except Exception as e:
        print(f"ERROR writing to {target}: {str(e)}")
        import traceback
        traceback.print_exc()

def parse_ai_response_and_apply(ai_text: str, file_map: Dict[str, ProjectFile]):
    """
    Looks for lines of the form:
      === File: path/to/file ===
      (some content)

    Then we store that content in file_map[path].
    If path not in file_map, we create a new entry (new file).
    Makes sure to normalize paths for cross-platform compatibility.
    """
    if not ai_text or ai_text.startswith("ERROR from"):
        print("Warning: AI response contains an error or is empty. Cannot parse file markers.")
        return
        
    lines = ai_text.splitlines()
    if not lines:
        print("Warning: AI response has no content lines to parse.")
        return
        
    current_file = None
    content_buffer: List[str] = []
    files_found = 0

    def commit_file():
        nonlocal current_file, content_buffer, files_found
        if current_file:
            # Normalize path separators for cross-platform compatibility
            normalized_path = current_file.replace('/', os.path.sep)
            if normalized_path not in file_map:
                # Create a new entry if it doesn't exist
                file_map[normalized_path] = ProjectFile(normalized_path, "")
            file_map[normalized_path].content = "\n".join(content_buffer)
            print(f"DEBUG: Processed file {normalized_path} with {len(content_buffer)} lines")
            files_found += 1

    for line in lines:
        if line.startswith("=== File: "):
            # commit previous file
            commit_file()
            # Extract the file path, properly trimming any trailing === markers
            file_marker = line.replace("=== File: ", "", 1).strip()
            if file_marker.endswith(" ==="):
                file_marker = file_marker[:-4].strip()
            current_file = file_marker
            content_buffer = []
        else:
            # accumulate lines for this file
            content_buffer.append(line)

    # commit last file
    commit_file()
    
    if files_found == 0:
        print("Warning: No file markers found in AI response. This may indicate formatting issues.")
        print("AI response excerpt (first 200 chars):", ai_text[:200] + "..." if len(ai_text) > 200 else ai_text)

def run_project_builder(model_name: str, vision: str = None, auto_yes: bool = False, start_step: int = 1, start_substep: str = None):
    """
    Run the project builder script with the specified model and vision.
    
    Args:
        model_name (str): The model to use, either "claude37sonnet" or "deepseekr1"
        vision (str, optional): The project description
        auto_yes (bool): Whether to automatically answer yes to all prompts
        start_step (int): Step number to start from (1-based)
        start_substep (str): Optional substep ID to start from (e.g. "2B")
    """
    print("\n=== Running Project Builder ===")
    try:
        # Import project_builder after imports to avoid circular dependencies
        from project_builder import run_project_builder as run_builder
        
        # If no vision provided, try to read from user_prompt.txt
        if not vision and os.path.exists("user_prompt.txt"):
            with open("user_prompt.txt", 'r', encoding='utf-8') as f:
                vision = f.read().strip()
        
        if not vision:
            print("Error: No project description provided.")
            return
            
        # Run the builder directly with all arguments
        run_builder(vision, model_name, start_step, start_substep)
        
    except Exception as e:
        print(f"Error running Project Builder: {e}")
        print("You can manually run it using: python orchestrator.py --build <model> [vision] [--start-step N] [--start-substep ID]")

def run_deep_research(model_name: str, topic: str = None):
    """
    Run the deep research script with the specified model and topic.
    
    Args:
        model_name (str): The model to use, either "claude37sonnet" or "deepseekr1"
        topic (str, optional): The research topic to investigate
    """
    print("\n=== Running Deep Research ===")
    try:
        # Import deep_research after imports to avoid circular dependencies
        from deep_research import run_deep_research as run_research
        
        # If no topic provided, try to read from user_prompt.txt
        if not topic and os.path.exists("user_prompt.txt"):
            with open("user_prompt.txt", 'r', encoding='utf-8') as f:
                topic = f.read().strip()
        
        if not topic:
            print("Error: No research topic provided.")
            return
            
        # Run the research directly
        run_research(topic, model_name)
        
    except Exception as e:
        print(f"Error running Deep Research: {e}")
        print("You can manually run it using: python orchestrator.py --research <model> [topic]")

def run_ai_proposal_generator(model: str = "claude37sonnet"):
    """
    Run the AI Proposal Generator with the specified model.
    
    Args:
        model (str): The model to use, either "claude37sonnet" or "deepseekr1"
    """
    print("\n=== Running AI Proposal Generator ===")
    try:
        # Map the internal model names to the ones expected by ai_proposal_generator.py
        proposal_model = "claude"  # Default
        if model.lower() == "claude37sonnet":
            proposal_model = "claude"
        elif model.lower() == "deepseekr1":
            proposal_model = "deepseek"
        
        # Construct the command to run the ai_proposal_generator.py script
        cmd = [sys.executable, "ai_proposal_generator.py", "--model", proposal_model]
        
        # Run the command and capture output
        print(f"Executing: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Print the output
        if result.stdout:
            print("Output:")
            print(result.stdout)
        
        # Print any errors
        if result.stderr:
            print("Errors:")
            print(result.stderr)
            
        # Check if successful
        if result.returncode == 0:
            print("\nAI Proposal Generator completed successfully!")
            print("You can find the generated proposal in some_project/doc/ai_research_proposal.md")
        else:
            print(f"\nAI Proposal Generator failed with exit code {result.returncode}")
            
    except Exception as e:
        print(f"Error running AI Proposal Generator: {e}")
        print("You can manually run it using: python ai_proposal_generator.py --model [claude|deepseek]")

def cleanup_malformed_files():
    """Clean up any existing files with malformed names (containing '===')"""
    try:
        print("Checking for malformed filenames...")
        # Check in doc directory for files with '===' in the name
        doc_dir = os.path.join(PROJECT_DIR, "doc")
        if not os.path.exists(doc_dir):
            return
            
        for filename in os.listdir(doc_dir):
            if "===" in filename:
                # Get the clean name
                clean_name = filename.replace(" ===", "").strip()
                old_path = os.path.join(doc_dir, filename)
                new_path = os.path.join(doc_dir, clean_name)
                
                print(f"Fixing malformed filename: {filename} -> {clean_name}")
                
                # If clean file already exists, merge content
                if os.path.exists(new_path):
                    with open(old_path, 'r', encoding='utf-8') as old_file:
                        old_content = old_file.read()
                    
                    with open(new_path, 'r', encoding='utf-8') as existing_file:
                        existing_content = existing_file.read()
                    
                    # Only append if content is different
                    if old_content not in existing_content:
                        with open(new_path, 'a', encoding='utf-8') as merged_file:
                            merged_file.write("\n\n" + old_content)
                    
                    # Remove the malformed file
                    os.remove(old_path)
                else:
                    # Rename the file
                    os.rename(old_path, new_path)
                    
        print("Filename cleanup complete.")
    except Exception as e:
        print(f"Error during filename cleanup: {e}")
        # Continue with the program even if cleanup fails

def run_llm_workflow(workflow_type: str, vision: str, model_name: str, start_step: int = 1, start_substep: str = None):
    """
    Run an LLM workflow of the specified type using the template-based system.
    
    Args:
        workflow_type (str): Type of workflow to run (e.g., "book_writer", "game_design")
        vision (str): The vision/description for the workflow
        model_name (str): The model to use ("claude37sonnet" or "deepseekr1")
        start_step (int): Step number to start from (1-based)
        start_substep (str): Optional substep ID to start from (e.g. "B")
    """
    print(f"\n=== Running {workflow_type} Workflow ===")
    
    try:
        # Import necessary functions from the template module
        from llm_walkthrough_template import load_workflow_config, run_workflow, list_available_workflows
        
        # Construct the path to the workflow config file
        config_path = f"configs/{workflow_type}_config.py"
        
        # Check if the configuration exists
        if not os.path.exists(config_path):
            print(f"Error: Workflow type '{workflow_type}' not found.")
            print("Available workflow types:")
            available_workflows = list_available_workflows()
            for workflow in available_workflows:
                print(f"  - {workflow.replace('_config.py', '')}")
            return
            
        # Load the workflow configuration
        config = load_workflow_config(config_path)
        
        # Run the workflow with the loaded configuration
        run_workflow(vision, model_name, config, start_step, start_substep)
        
    except Exception as e:
        print(f"Error running workflow: {e}")
        import traceback
        traceback.print_exc()

def main():
    # Platform check
    if sys.platform == 'win32':
        # On Windows, warn about paths
        print("""Note: On Windows, if the AI outputs file paths with forward slashes (/),
they will be automatically converted to backslashes (\\) when saving files.
This ensures cross-platform compatibility.""")
    else:
        print("Running on Unix-like platform. File paths will use forward slashes (/).")
    
    # Clean up any malformed filenames
    cleanup_malformed_files()
    
    # Set up argument parser for command-line options
    parser = argparse.ArgumentParser(description='Orchestrate an LLM to walk through the Breakthrough-Idea Framework')
    parser.add_argument('--auto-yes', '-y', action='store_true', help='Automatically answer "y" to all prompts')
    parser.add_argument('--generate-proposal', action='store_true', help='Automatically run the AI Proposal Generator after all steps complete')
    parser.add_argument('--build', action='store_true', help='Run the Project Builder instead of the Breakthrough-Idea Framework')
    parser.add_argument('--research', action='store_true', help='Run the Deep Research process instead of the Breakthrough-Idea Framework')
    parser.add_argument('--workflow', type=str, help='Run a custom LLM workflow (e.g., book_writer, game_design)')
    parser.add_argument('--start-step', type=int, default=1, help='Step number to start from (1-based)')
    parser.add_argument('--start-substep', type=str, help='Substep ID to start from (e.g. "B")')
    parser.add_argument('--syntax-check', action='store_true', help='Run syntax checking on the generated project files')
    parser.add_argument('--disable-syntax-check', action='store_true', help='Disable automatic syntax checking during build')
    parser.add_argument('model', choices=['claude37sonnet', 'deepseekr1'], 
                      help='Which LLM to use (claude37sonnet or deepseekr1)')
    parser.add_argument('domain', nargs='?', default=None, 
                      help='Domain/challenge to explore')
    
    args = parser.parse_args()
    auto_yes = args.auto_yes
    generate_proposal = args.generate_proposal
    build_mode = args.build
    research_mode = args.research
    workflow_type = args.workflow
    start_step = args.start_step
    start_substep = args.start_substep
    
    model_name = args.model.lower()
    orchestrator = AIOrchestrator(model_name)
    
    # Check if domain/challenge was provided as a command line argument
    user_vision = args.domain

    # Run the appropriate mode based on flags
    if workflow_type:
        # Run a custom workflow from the template system
        run_llm_workflow(workflow_type, user_vision, model_name, start_step, start_substep)
        return
    elif build_mode:
        # Run the Project Builder
        print("Running Project Builder...")
        from project_builder import run_project_builder
        
        # Set the global syntax checking flag based on command line args
        if args.disable_syntax_check:
            print("Automatic syntax checking disabled")
            from project_builder import ENABLE_SYNTAX_CHECKING
            ENABLE_SYNTAX_CHECKING = False
            
        # Run just the syntax checker if requested
        if args.syntax_check:
            print("Running syntax check on generated project...")
            run_project_builder(vision=None, model_name=args.model, run_syntax_check_only=True)
        else:
            run_project_builder(vision=args.domain, model_name=args.model, 
                           start_step=args.start_step, start_substep=args.start_substep)
        return
    elif research_mode:
        # Run the Deep Research process
        run_deep_research(model_name, user_vision)
        return
    
    # Step 0) Check for user_prompt.txt and offer to use it
    prompt_file_path = "user_prompt.txt"
    if not user_vision and os.path.exists(prompt_file_path):
        try:
            with open(prompt_file_path, 'r', encoding='utf-8') as f:
                file_content = f.read().strip()
            
            if file_content:
                print("\n=== FOUND USER_PROMPT.TXT ===")
                print("Preview of user_prompt.txt:")
                print("---")
                # Show first 200 chars with ellipsis if longer
                preview = file_content[:200] + ("..." if len(file_content) > 200 else "")
                print(preview)
                print("---")
                
                if auto_yes:
                    print("Auto-yes enabled: Using user_prompt.txt as domain/challenge.")
                    user_vision = file_content
                else:
                    use_file = input("Use this content as your domain/challenge? (y/n): ").strip().lower()
                    if use_file == 'y':
                        user_vision = file_content
                        print("Using user_prompt.txt as domain/challenge.")
        except Exception as e:
            print(f"Error reading user_prompt.txt: {e}")
    
    # Step 0) Ask user for project vision if not already set
    if not user_vision:
        print("=== INITIAL DOMAIN OR CHALLENGE ===")
        user_vision = input("Describe the domain or challenge you want breakthrough ideas for (a line or paragraph): ")

    # Step 0.5) Offer to ask follow-up questions
    if auto_yes:
        print("Auto-yes enabled: Skipping follow-up questions.")
        ask_q = 'n'
    else:
        ask_q = input("Should the AI ask follow-up questions about your domain/challenge? (y/n): ").strip().lower()
    
    if ask_q == 'y':
        conversation = [
            {
                "role": "system",
                "content": (
                    "You are a helpful AI that clarifies the user's domain or challenge. "
                    "Ask short follow-up questions to fully understand the user's needs."
                )
            },
            {"role": "user", "content": user_vision},
        ]
        while True:
            # let AI ask a question
            question = orchestrator.client.run(conversation, max_tokens=1024)
            print("\nAI asks:\n", question)
            user_ans = input("Your answer (type 'done' to finish Q&A): ")
            if user_ans.strip().lower() == 'done':
                break
            conversation.append({"role": "assistant", "content": question})
            conversation.append({"role": "user", "content": user_ans})

        # Combine the conversation into user_vision
        user_vision += "\n\nAdditional Clarifications:\n" + "\n".join(
            [f"{msg['role']}: {msg['content']}" for msg in conversation if msg['role'] == 'user']
        )

    # Prepare "some_project" folder - use pathlib for cross-platform compatibility
    
    # Pre-check to ensure we can create and write to the directories
    try:
        print("PRE-CHECK: Verifying we can create and write to directories...")
        Path(PROJECT_DIR).mkdir(exist_ok=True)
        doc_dir = Path(PROJECT_DIR) / "doc"
        doc_dir.mkdir(exist_ok=True)
        
        # Try writing a test file
        test_file = doc_dir / "test_write.txt"
        test_file.write_text("Test write permission - " + str(datetime.datetime.now()), encoding="utf-8")
        if test_file.exists():
            print(f"PRE-CHECK: Successfully created test file at {test_file}")
            print(f"PRE-CHECK: Directory permissions OK for writing files")
        
        # Try reading the test file
        test_content = test_file.read_text(encoding="utf-8")
        print(f"PRE-CHECK: Successfully read test file content: '{test_content[:20]}...'")
        
    except Exception as e:
        print(f"ERROR in pre-check: {str(e)}")
        print("The program may not be able to write files. Please check permissions.")
        print("Continuing anyway, but be aware files might not be created properly.")
        import traceback
        traceback.print_exc()
    
    # Continue with normal initialization
    Path(PROJECT_DIR).mkdir(exist_ok=True)
    Path(PROJECT_DIR).joinpath("doc").mkdir(exist_ok=True)
    file_map = read_project_files(PROJECT_DIR)

    # We'll store step outputs to feed them as context into subsequent steps
    step_outputs = {}

    # Dictionary to store step outputs
    step_outputs = {}
    
    # Define the steps with sub-steps
    STEPS = [
        {
            "phase_name": "Context & Constraints",
            "system_prompt": "You are a specialized consultant for breakthrough innovation. Your task is to thoroughly analyze the context, constraints, and potential for innovation in the stated domain. You must produce specific outputs for each sub-step, avoiding disclaimers about feasibility.",
            "user_prompt_template": (
                "Step 1: Context & Constraints - Please analyze the following domain or challenge:\n\n"
                "{vision}\n\n"
                "For this step, please complete the following sub-steps:\n\n"
                "Sub-Step A: Summarize the domain context, including key technologies, current limitations, and context.\n"
                "Sub-Step B: Identify unusual references or cross-domain knowledge that could be relevant.\n"
                "Sub-Step C: Provide an initial short list of 3-5 potential synergy angles that might lead to breakthroughs.\n\n"
                "Place your complete response in `=== File: doc/CONTEXT_CONSTRAINTS.md ===`\n"
                "Format your response with clear headings for each sub-step."
            ),
            "sub_steps": [
                SubStep("1A", "Domain Context Summary", 
                         "Summarize the domain context, including key technologies, current limitations, and context."),
                SubStep("1B", "Unusual References", 
                         "Identify unusual references or cross-domain knowledge that could be relevant."),
                SubStep("1C", "Potential Synergy Angles", 
                         "Provide an initial short list of 3-5 potential synergy angles that might lead to breakthroughs.")
            ]
        },
        {
            "phase_name": "Divergent Brainstorm of Solutions",
            "system_prompt": "You are an innovation consultant specialized in generating diverse, novel solutions. Generate multiple creative solution approaches based on the synergy angles identified in the previous step. Avoid disclaimers about feasibility - focus on innovation potential.",
            "user_prompt_template": (
                "Step 2: Divergent Brainstorm of Solutions\n\n"
                "Domain/Challenge:\n{vision}\n\n"
                "Context & Constraints (Step 1 Output):\n{step1}\n\n"
                "For this step, please complete the following sub-steps:\n\n"
                "Sub-Step A: For each synergy angle from Step 1C, produce at least 2 distinct solution sketches (total 6-10 solutions).\n"
                "Sub-Step B: Rate each solution on originality, feasibility, and potential impact (avoid disclaimers).\n"
                "Sub-Step C: Convert the top 3 solutions into a more detailed outline.\n\n"
                "Place your complete response in `=== File: doc/DIVERGENT_SOLUTIONS.md ===`\n"
                "Format your response with clear headings for each sub-step."
            ),
            "sub_steps": [
                SubStep("2A", "Solution Sketches", 
                         "For each synergy angle from Step 1C, produce at least 2 distinct solution sketches (total 6-10 solutions)."),
                SubStep("2B", "Solution Ratings", 
                         "Rate each solution on originality, feasibility, and potential impact (avoid disclaimers)."),
                SubStep("2C", "Detailed Outlines", 
                         "Convert the top 3 solutions into a more detailed outline.")
            ]
        },
        {
            "phase_name": "Deep-Dive on Chosen Solutions",
            "system_prompt": "You are a technical specialist providing deep analysis on innovative solutions. Thoroughly analyze the top solutions identified in the previous step, explaining underlying mechanisms, domain synergies, and providing actionable implementation steps.",
            "user_prompt_template": (
                "Step 3: Deep-Dive on Chosen Solutions\n\n"
                "Domain/Challenge:\n{vision}\n\n"
                "Context & Constraints (Step 1 Output):\n{step1}\n\n"
                "Divergent Solutions (Step 2 Output):\n{step2}\n\n"
                "For this step, please complete the following sub-steps:\n\n"
                "Sub-Step A: For each chosen solution, do a 1-2 page deep-dive (theory, domain synergy, example scenario).\n"
                "Sub-Step B: Propose key resources or advanced references needed.\n"
                "Sub-Step C: List 3-5 action items for each solution if one wanted to prototype it.\n\n"
                "Place your complete response in `=== File: doc/DEEP_DIVE_MECHANISMS.md ===`\n"
                "Format your response with clear headings for each sub-step."
            ),
            "sub_steps": [
                SubStep("3A", "Deep Analysis", 
                         "For each chosen solution, do a 1-2 page deep-dive (theory, domain synergy, example scenario)."),
                SubStep("3B", "Key Resources", 
                         "Propose key resources or advanced references needed."),
                SubStep("3C", "Action Items", 
                         "List 3-5 action items for each solution if one wanted to prototype it.")
            ]
        },
        {
            "phase_name": "Self-Critique & Merge",
            "system_prompt": "You are a critical analyst and synthesizer of breakthrough ideas. Critically evaluate the previously developed solutions, identify limitations, and merge the best aspects into stronger unified approaches.",
            "user_prompt_template": (
                "Step 4: Self-Critique & Merge\n\n"
                "Domain/Challenge:\n{vision}\n\n"
                "Context & Constraints (Step 1 Output):\n{step1}\n\n"
                "Deep-Dive Analysis (Step 3 Output):\n{step3}\n\n"
                "For this step, please complete the following sub-steps:\n\n"
                "Sub-Step A: Evaluate each solution's limitations or synergy potential.\n"
                "Sub-Step B: Propose 2 merged approaches that combine the best aspects.\n"
                "Sub-Step C: For each merged approach, produce a short \"Implementation Rationale\" explaining the synergy.\n\n"
                "Place your complete response in `=== File: doc/SELF_CRITIQUE_SYNERGY.md ===`\n"
                "Format your response with clear headings for each sub-step."
            ),
            "sub_steps": [
                SubStep("4A", "Solution Evaluation", 
                         "Evaluate each solution's limitations or synergy potential."),
                SubStep("4B", "Merged Approaches", 
                         "Propose 2 merged approaches that combine the best aspects."),
                SubStep("4C", "Implementation Rationale", 
                         "For each merged approach, produce a short \"Implementation Rationale\" explaining the synergy.")
            ]
        },
        {
            "phase_name": "Final Breakthrough Blueprint",
            "system_prompt": "You are an innovation architect finalizing a breakthrough approach. Create a comprehensive blueprint that synthesizes all previous analysis into a unified, actionable solution with clear implementation steps.",
            "user_prompt_template": (
                "Step 5: Final Breakthrough Blueprint\n\n"
                "Domain/Challenge:\n{vision}\n\n"
                "Context & Constraints (Step 1 Output):\n{step1}\n\n"
                "Self-Critique & Merged Approaches (Step 4 Output):\n{step4}\n\n"
                "For this step, please complete the following sub-steps:\n\n"
                "Sub-Step A: Summarize the final breakthrough approach in 3-5 paragraphs.\n"
                "Sub-Step B: Provide a bullet list of 10 actionable steps to realize it.\n"
                "Sub-Step C: (Optional) Provide an ASCII or block diagram illustrating the approach.\n\n"
                "Place your complete response in `=== File: doc/BREAKTHROUGH_BLUEPRINT.md ===`\n"
                "Format your response with clear headings for each sub-step."
            ),
            "sub_steps": [
                SubStep("5A", "Blueprint Summary", 
                         "Summarize the final breakthrough approach in 3-5 paragraphs."),
                SubStep("5B", "Actionable Steps", 
                         "Provide a bullet list of 10 actionable steps to realize it."),
                SubStep("5C", "Visual Diagram", 
                         "(Optional) Provide an ASCII or block diagram illustrating the approach.")
            ]
        },
        {
            "phase_name": "Implementation & Risk Minimization Plan",
            "system_prompt": "You are a project manager specialized in bringing innovative ideas to implementation. Create a detailed implementation plan with timeline, risk management, and success metrics for the breakthrough blueprint.",
            "user_prompt_template": (
                "Step 6: Implementation & Risk Minimization Plan\n\n"
                "Domain/Challenge:\n{vision}\n\n"
                "Breakthrough Blueprint (Step 5 Output):\n{step5}\n\n"
                "For this step, please complete the following sub-steps:\n\n"
                "Sub-Step A: Provide a timeline (like 3-6 months) with milestones.\n"
                "Sub-Step B: Outline potential roadblocks with specific solutions for each.\n"
                "Sub-Step C: Summarize each milestone's success criteria and metrics.\n\n"
                "Place your complete response in `=== File: doc/IMPLEMENTATION_PATH.md ===`\n"
                "Format your response with clear headings for each sub-step."
            ),
            "sub_steps": [
                SubStep("6A", "Implementation Timeline", 
                         "Provide a timeline (like 3-6 months) with milestones."),
                SubStep("6B", "Risk Management", 
                         "Outline potential roadblocks with specific solutions for each."),
                SubStep("6C", "Success Metrics", 
                         "Summarize each milestone's success criteria and metrics.")
            ]
        },
        {
            "phase_name": "Cross-Check with Known Projects",
            "system_prompt": "You are a research analyst with knowledge of existing state-of-the-art projects. Compare the developed blueprint against known projects or research, identifying unique elements and validating its novelty.",
            "user_prompt_template": (
                "Step 7: Cross-Check with Known Projects\n\n"
                "Domain/Challenge:\n{vision}\n\n"
                "Breakthrough Blueprint (Step 5 Output):\n{step5}\n\n"
                "For this step, please complete the following sub-steps:\n\n"
                "Sub-Step A: List existing open-source or research efforts that share partial elements.\n"
                "Sub-Step B: Distill the unique points that go beyond those references.\n"
                "Sub-Step C: Summarize why this blueprint remains fresh or unique.\n\n"
                "Place your complete response in `=== File: doc/NOVELTY_CHECK.md ===`\n"
                "Format your response with clear headings for each sub-step."
            ),
            "sub_steps": [
                SubStep("7A", "Existing Projects", 
                         "List existing open-source or research efforts that share partial elements."),
                SubStep("7B", "Unique Elements", 
                         "Distill the unique points that go beyond those references."),
                SubStep("7C", "Novelty Summary", 
                         "Summarize why this blueprint remains fresh or unique.")
            ]
        },
        {
            "phase_name": "Additional Q&A or Clarifications",
            "system_prompt": "You are a technical consultant providing clarity and final details on the breakthrough idea. Address any questions or areas needing elaboration, and optionally provide code stubs or technical specifications if relevant.",
            "user_prompt_template": (
                "Step 8: Additional Q&A or Clarifications\n\n"
                "Domain/Challenge:\n{vision}\n\n"
                "Breakthrough Blueprint (Step 5 Output):\n{step5}\n\n"
                "Implementation Path (Step 6 Output):\n{step6}\n\n"
                "Novelty Check (Step 7 Output):\n{step7}\n\n"
                "For this step, please complete the following sub-steps:\n\n"
                "Sub-Step A: Address any final questions or areas needing clarification.\n"
                "Sub-Step B: Elaborate on any technical details that require further explanation.\n"
                "Sub-Step C: (Optional) Provide any code stubs or technical specifications if relevant.\n\n"
                "Place your complete response in `=== File: doc/ELABORATIONS.md ===`\n"
                "Format your response with clear headings for each sub-step."
            ),
            "sub_steps": [
                SubStep("8A", "Clarifications", 
                         "Address any final questions or areas needing clarification."),
                SubStep("8B", "Technical Details", 
                         "Elaborate on any technical details that require further explanation."),
                SubStep("8C", "Code Stubs", 
                         "(Optional) Provide any code stubs or technical specifications if relevant.")
            ]
        },
    ]

    def build_user_prompt(step_index: int, step_info: dict, sub_step_index: int = None) -> str:
        """
        Takes the step index, step definition, and optional sub-step index,
        returns the user prompt with prior step outputs inserted for context.
        
        If sub_step_index is provided, generates a prompt for just that sub-step.
        Otherwise, generates the full step prompt with all sub-steps.
        """
        prompt = step_info["user_prompt_template"]
        
        # Replace vision and prior step outputs
        prompt = prompt.replace("{vision}", user_vision)
        for i in range(1, step_index):
            placeholder = f"{{step{i}}}"
            prompt = prompt.replace(placeholder, step_outputs.get(i, "(No output)"))
        
        # If we're processing a specific sub-step, modify the prompt
        if sub_step_index is not None:
            sub_step = step_info["sub_steps"][sub_step_index]
            sub_step_id = sub_step.id
            sub_step_name = sub_step.name
            sub_step_prompt = sub_step.prompt
            
            # Build a more focused prompt for just this sub-step
            prompt = (
                f"Step {step_index}, Sub-Step {sub_step_id}: {sub_step_name}\n\n"
                f"Domain/Challenge:\n{user_vision}\n\n"
            )
            
            # Add relevant prior outputs for context
            if step_index > 1:
                prompt += f"Context & Constraints (Step 1 Output):\n{step_outputs.get(1, '(No output)')}\n\n"
            
            # If we're beyond step 2 and processing a later sub-step, include previous sub-step outputs
            if sub_step_index > 0:
                # Include previous sub-step outputs from the same step
                prompt += "Previous Sub-Step Outputs for this Step:\n"
                for i in range(sub_step_index):
                    prev_sub_step = step_info["sub_steps"][i]
                    sub_step_output_key = f"step{step_index}_sub{i+1}"
                    prev_output = sub_step_outputs.get(sub_step_output_key, "(No output)")
                    prompt += f"Sub-Step {prev_sub_step.id} ({prev_sub_step.name}):\n{prev_output}\n\n"
            
            # Add specific instructions for this sub-step
            prompt += f"Your task for this sub-step:\n{sub_step_prompt}\n\n"
            
            # Output instructions
            prompt += (
                f"Place your response for Sub-Step {sub_step_id} in "
                f"`=== File: doc/STEP{step_index}_SUBSTEP_{sub_step_id}.md ===`\n"
                f"Focus only on completing this specific sub-step."
            )
        
        return prompt

    # Dictionary to store sub-step outputs
    sub_step_outputs = {}
    
    # Process mode selection
    process_mode = input("Process mode: (1) Entire steps at once, or (2) Individual sub-steps? (1/2): ").strip()
    process_by_substeps = process_mode == "2"
    
    # Run the steps
    for i, step in enumerate(STEPS, start=1):
        phase_name = step["phase_name"]
        system_prompt = step["system_prompt"]
        
        # Process by individual sub-steps or entire step at once
        if process_by_substeps and "sub_steps" in step:
            # Process each sub-step individually
            for j, sub_step in enumerate(step["sub_steps"], start=1):
                sub_step_name = f"{phase_name}: {sub_step.name}"
                retry_substep = True
                
                # Loop until we successfully complete or skip this sub-step
                while retry_substep:
                    print(f"\n=== {sub_step_name} ===")
                    
                    if auto_yes:
                        print("Auto-yes enabled: Proceeding with this sub-step.")
                        do_it = 'y'
                    else:
                        do_it = input(f"Proceed with sub-step {sub_step.id}? (y = proceed, s = skip, q = quit): ").strip().lower()
                    
                    if do_it == 'q':
                        # Quit entirely
                        print("Exiting.")
                        sys.exit(0)
                    elif do_it == 's':
                        # Skip sub-step
                        print(f"Skipping {sub_step_name}.")
                        retry_substep = False  # Exit retry loop and move to next sub-step
                        continue
                    elif do_it == 'y':
                        # Generate sub-step specific prompt
                        user_prompt = build_user_prompt(i, step, j-1)
                        
                        # Call the LLM with increased max_tokens to avoid truncation
                        ai_response = orchestrator.call_llm(system_prompt, user_prompt, max_tokens=64000, temperature=0.2)
                        print("\nAI Response:\n", ai_response)
                        
                        # Let user decide to apply, retry, or skip
                        if auto_yes:
                            print("Auto-yes enabled: Applying changes.")
                            apply_yn = 'y'
                        else:
                            apply_yn = input(
                                "Apply changes (create/update files in some_project)? "
                                "(y = apply, r = retry sub-step, n = skip sub-step): "
                            ).strip().lower()
                        
                        if apply_yn == 'y':
                            # Parse file markers from response
                            print("Attempting to parse file markers from response...")
                            parse_ai_response_and_apply(ai_response, file_map)
                            
                            # Store sub-step output for later reference
                            sub_step_key = f"step{i}_sub{j}"
                            sub_step_outputs[sub_step_key] = ai_response
                            
                            # ALWAYS write a specific file for this substep regardless of parsing result
                            output_file = f"doc/STEP{i}_SUBSTEP_{sub_step.id}.md"
                            # Ensure the filename is clean (no trailing === or other artifacts)
                            output_file = output_file.replace(" ===", "").strip()
                            
                            print(f"Creating {output_file}...")
                            content = f"# {phase_name}: {sub_step.name}\n\n{ai_response}"
                            file_map[output_file] = ProjectFile(output_file, content)
                            
                            # Write all files now
                            for rel_path, pf in file_map.items():
                                # Normalize the path before writing
                                clean_path = rel_path.replace(" ===", "").strip()
                                if clean_path != rel_path:
                                    file_map[clean_path] = file_map.pop(rel_path)
                                write_project_file(PROJECT_DIR, file_map[clean_path])
                            
                            print(f"Successfully wrote {output_file} to some_project/{output_file}")
                            retry_substep = False  # Sub-step completed successfully, move to next one
                        elif apply_yn == 'r':
                            # Retry sub-step
                            print(f"Retrying {sub_step_name}.")
                            # Continue retry loop for this sub-step
                            continue
                        else:
                            # Skip applying changes for this sub-step
                            print(f"Skipping applying changes for {sub_step_name}.")
                            retry_substep = False  # Exit retry loop and move to next sub-step
            
            # After all sub-steps are done, compile them into a single document
            print(f"\n=== Compiling all sub-steps for {phase_name} ===")
            
            # Build combined content from all sub-steps
            combined_content = f"# {phase_name}\n\n"
            for j, sub_step in enumerate(step["sub_steps"], start=1):
                sub_step_key = f"step{i}_sub{j}"
                sub_step_output = sub_step_outputs.get(sub_step_key, "")
                if sub_step_output:
                    combined_content += f"## Sub-Step {sub_step.id}: {sub_step.name}\n\n{sub_step_output}\n\n"
            
            # Define output file for the combined content
            output_file = None
            if i == 1:
                output_file = "doc/01_CONTEXT_CONSTRAINTS.md"
            elif i == 2:
                output_file = "doc/02_DIVERGENT_SOLUTIONS.md"
            elif i == 3:
                output_file = "doc/03_DEEP_DIVE_MECHANISMS.md"
            elif i == 4:
                output_file = "doc/04_SELF_CRITIQUE_SYNERGY.md"
            elif i == 5:
                output_file = "doc/05_BREAKTHROUGH_BLUEPRINT.md"
            elif i == 6:
                output_file = "doc/06_IMPLEMENTATION_PATH.md"
            elif i == 7:
                output_file = "doc/07_NOVELTY_CHECK.md"
            elif i == 8:
                output_file = "doc/08_ELABORATIONS.md"
            
            if output_file:
                print(f"Creating combined file {output_file}...")
                file_map[output_file] = ProjectFile(output_file, combined_content)
                write_project_file(PROJECT_DIR, file_map[output_file])
                print(f"Successfully wrote combined file to some_project/{output_file}")
            
            # Store this step's output for use in future steps
            step_outputs[i] = combined_content
            print(f"Stored combined output for Step {i} for reference in future steps")
        else:
            # Process the entire step at once (original behavior)
            user_prompt = build_user_prompt(i, step)
            
            while True:
                print(f"\n=== {phase_name} ===")
                
                if auto_yes:
                    print("Auto-yes enabled: Proceeding with this step.")
                    do_it = 'y'
                else:
                    do_it = input("Proceed with this step? (y = proceed, s = skip, q = quit): ").strip().lower()

                if do_it == 'q':
                    # Quit entirely
                    print("Exiting.")
                    sys.exit(0)
                elif do_it == 's':
                    # Skip step
                    print(f"Skipping {phase_name}.")
                    break
                elif do_it == 'y':
                    # Call the LLM with increased max_tokens to avoid truncation
                    ai_response = orchestrator.call_llm(system_prompt, user_prompt, max_tokens=64000, temperature=0.2)
                    print("\nAI Response:\n", ai_response)
                    
                    # Let user decide to apply, retry, or skip
                    if auto_yes:
                        print("Auto-yes enabled: Applying changes.")
                        apply_yn = 'y'
                    else:
                        apply_yn = input(
                            "Apply changes (create/update files in some_project)? "
                            "(y = apply, r = retry step, n = skip step): "
                        ).strip().lower()
                    
                    if apply_yn == 'y':
                        # First attempt normal parsing (for backward compatibility)
                        print("Attempting to parse file markers from response...")
                        parse_ai_response_and_apply(ai_response, file_map)
                        
                        # FORCE DIRECT WRITING: Always write a file for each step regardless of parsing result
                        output_file = None
                        file_written = False
                        
                        # Define direct mapping from step index to output file
                        if i == 1:
                            output_file = "doc/01_CONTEXT_CONSTRAINTS.md"
                        elif i == 2:
                            output_file = "doc/02_DIVERGENT_SOLUTIONS.md"
                        elif i == 3:
                            output_file = "doc/03_DEEP_DIVE_MECHANISMS.md"
                        elif i == 4:
                            output_file = "doc/04_SELF_CRITIQUE_SYNERGY.md"
                        elif i == 5:
                            output_file = "doc/05_BREAKTHROUGH_BLUEPRINT.md"
                        elif i == 6:
                            output_file = "doc/06_IMPLEMENTATION_PATH.md"
                        elif i == 7:
                            output_file = "doc/07_NOVELTY_CHECK.md"
                        elif i == 8:
                            output_file = "doc/08_ELABORATIONS.md"
                        
                        if output_file:
                            print(f"DIRECT WRITE: Creating {output_file} regardless of file markers...")
                            # Create file contents with step name header and AI response
                            content = f"# {phase_name}\n\n{ai_response}"
                            file_map[output_file] = ProjectFile(output_file, content)
                            file_written = True
                        
                        # Write all files
                        for rel_path, pf in file_map.items():
                            write_project_file(PROJECT_DIR, pf)
                        
                        if file_written:
                            print(f"DIRECT WRITE: Successfully wrote {output_file} to some_project/{output_file}")
                        
                        print("Changes saved to some_project/.")
                        # Store step output in step_outputs
                        step_outputs[i] = ai_response
                        # Done with this step
                        break
                    elif apply_yn == 'r':
                        print("Repeating this step...\n")
                    else:  # 'n' or anything else
                        print("Skipping file changes.")
                        # Optionally still store the AI text as the step output
                        step_outputs[i] = ai_response
                        break
                else:
                    print("Invalid choice. Please enter 'y', 's', or 'q'.")

    print("\n=== Breakthrough Idea Process Completed ===")
    print("You can check 'some_project/doc/' for your breakthrough blueprint files.")
    
    # Automatically run the AI Proposal Generator if requested
    if generate_proposal:
        run_ai_proposal_generator(model_name)

def extract_file_paths_from_structure(structure_file):
    """Extract file paths from the project structure file"""
    if not structure_file:
        return []
    
    file_paths = []
    lines = structure_file.content.splitlines()
    
    for line in lines:
        # Look for lines that appear to be file paths (containing a dot or ending with common extensions)
        if ('.' in line and not line.startswith('#') and not line.startswith('-')) or \
           any(line.strip().endswith(ext) for ext in ['.py', '.js', '.html', '.css', '.md', '.txt', '.json']):
            # Extract the file path - this is a simplified approach
            path = line.strip()
            # Clean up the path (remove bullets, etc.)
            path = path.lstrip('- */').split()[0] if path.split() else ""
            if path and '.' in path:  # Ensure it's likely a file
                file_paths.append(path)
    
    return file_paths

def parse_todo_list(todo_content):
    """Parse the TODO list to extract files in implementation order"""
    files_to_implement = []
    lines = todo_content.splitlines()
    
    for line in lines:
        # Look for lines that appear to be file tasks
        if ('- [ ]' in line or '* [ ]' in line) and '.' in line:
            # Extract file path using a simple heuristic
            parts = line.split()
            for part in parts:
                if '.' in part and not part.endswith('.') and not part.startswith('.'):
                    # Clean up the path
                    path = part.strip('(),;:"\'-')
                    files_to_implement.append({'path': path, 'completed': False})
                    break
    
    return files_to_implement

def mark_file_complete(todo_content, file_path):
    """Mark a file as complete in the TODO list"""
    lines = todo_content.splitlines()
    updated_lines = []
    
    for line in lines:
        if file_path in line and ('- [ ]' in line or '* [ ]' in line):
            # Replace the unchecked box with a checked one
            updated_line = line.replace('- [ ]', '- [x]').replace('* [ ]', '* [x]')
            updated_lines.append(updated_line)
        else:
            updated_lines.append(line)
    
    return '\n'.join(updated_lines)

if __name__ == "__main__":
    main()