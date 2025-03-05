# LLM Project Maker

A versatile AI orchestration framework for building complete projects, conducting deep research, generating proposals, and more using Large Language Models.

```
 _     _     __  __   ____            _           _     __  __       _
| |   | |   |  \/  | |  _ \ _ __ ___ (_) ___  ___| |_  |  \/  | __ _| | _____ _ __
| |   | |   | |\/| | | |_) | '__/ _ \| |/ _ \/ __| __| | |\/| |/ _` | |/ / _ \ '__|
| |___| |___| |  | | |  __/| | | (_) | |  __/ (__| |_  | |  | | (_| |   <  __/ |
|_____|_____|_|  |_| |_|   |_|  \___// |\___|\___|\__| |_|  |_|\__,_|_|\_\___|_|
                                   |__/
```

## ![Highlights](https://img.shields.io/badge/HIGHLIGHTS-Features-blue)

- **Generate Entire Projects With One Prompt**: Create complete project codebases from a single description. No need to write code file by file - get an entire working project structure with implementation.
- **Deep Research Capabilities**: Conduct structured, citation-backed research that exceeds OpenAI's depth with detailed reasoning and analysis.
- **Custom LLM Workflows**: Design your own multi-step LLM workflows with configurable templates for any domain.
- **AI Proposal Generator**: Generate professional proposals based on project requirements and documentation.

### ![Functions](https://img.shields.io/badge/KEY-Functions-green)

- **Project Builder**: `python -m project_maker.orchestrator --build` - Generate complete, working projects from a single prompt
- **Deep Research**: `python -m project_maker.orchestrator --research` - Superior research capabilities with structured methodology beyond what OpenAI provides
- **AI Proposal Generator**: `python -m project_maker.ai_proposal_generator` - Create professional, publication-ready proposals
- **Custom Workflows**: `python -m project_maker.orchestrator --walkthrough [template]` - Run specialized LLM workflows
- **Training Data Generator**: `python -m project_maker.training_data_generator` - Create datasets for model fine-tuning

### ![Research](https://img.shields.io/badge/ADVANCED-Research-red)

- **Structured multi-step methodology** versus single-prompt responses
- **Citation tracking** with proper academic referencing
- **Counter-argument analysis** for balanced perspective
- **Self-critique** and validation steps built into the process
- **Deeper domain expertise** through focused context retrieval

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Components](#components)
  - [Project Builder](#project-builder)
  - [Deep Research](#deep-research)
  - [AI Proposal Generator](#ai-proposal-generator)
  - [LLM Walkthrough Template](#llm-walkthrough-template)
  - [Training Data Generator](#training-data-generator)
- [Configuration](#configuration)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

## Overview

This framework provides a comprehensive set of tools for working with Large Language Models (LLMs) to accomplish complex tasks through structured workflows. The system orchestrates multi-step processes, manages context and token limits, and provides specialized templates for different use cases.

Key features:
- **Project Builder**: Generate complete, working project codebases from a simple description
- **Deep Research**: Conduct in-depth research on topics with structured documentation
- **AI Proposal Generator**: Create professional proposals based on project requirements
- **Customizable Workflows**: Define your own LLM-powered workflows with templates
- **Training Data Generation**: Generate training data for fine-tuning language models

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/project_maker.git
   cd project_maker
   ```

2. Set up a virtual environment:
   ```bash
   python -m venv .venv
   # On Windows
   .\.venv\Scripts\activate
   # On Linux/Mac
   source .venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up API keys (create a `.env` file in the project root):
   ```
   OPENAI_API_KEY=your_openai_key_here
   ANTHROPIC_API_KEY=your_anthropic_key_here
   ```

## Components

### Project Builder

The Project Builder is the core component, designed to create complete, working projects from a simple description. It follows a structured, multi-step approach:

1. Project Planning
2. System Architecture
3. Project Structure
4. Implementation Plan
5. File Implementation
6. Assembly and Usage Guide

#### How to Use Project Builder

Run the Project Builder with a description of the project you want to create:

```bash
python -m project_maker.orchestrator --build --model claude-3-opus-20240229 "Create a Python web application for a task management system with user authentication, task prioritization, and reminder features."
```

**Command-line Arguments:**

- `--build`: Activates the project builder mode
- `--model`: Specifies which LLM to use (options: openai, claude37sonnet, claude-3-opus-20240229, etc.)
- `--start_step`: Optionally specify which step to start from (1-6)
- `--start_substep`: Optionally specify which substep to start from (A, B, C, etc.)

**Resuming a Build:**

If your build is interrupted, you can resume from a specific step:

```bash
python -m project_maker.orchestrator --build --model claude-3-opus-20240229 --start_step 4
```

**Output:**

The Project Builder creates a complete project in the `generated_project` directory, including:
- Documentation in `generated_project/doc/`
- Source code files organized according to the planned structure
- Configuration files, README, and other project files

**Advanced Usage:**

For more control over the project generation process, you can:
1. Run individual steps manually and review outputs
2. Edit the STEP1_SUBSTEP_1C.md file before step 4 to customize the project structure
3. Modify configuration settings in the code for different token limits or behavior

### Deep Research

The Deep Research tool conducts comprehensive research on a topic using LLMs, producing structured documentation.

```bash
python -m project_maker.orchestrator --research --model claude-3-opus-20240229 "Explain quantum computing fundamentals and recent advancements"
```

**Command-line Arguments:**

- `--research`: Activates the deep research mode
- `--model`: Specifies which LLM to use
- Research topic as the final argument

**Output:**

Creates a structured research document with:
- Executive summary
- Key findings
- Detailed analysis
- References and sources
- Recommendations and next steps

### AI Proposal Generator

The AI Proposal Generator creates professional project proposals based on existing documentation.

```bash
python -m project_maker.ai_proposal_generator --model claude37sonnet
```

This tool:
1. Reads documentation from the `generated_project/doc/` directory
2. Synthesizes a comprehensive project proposal
3. Outputs a professional proposal document

### LLM Walkthrough Template

The LLM Walkthrough Template system allows you to create custom LLM-powered workflows.

```bash
python -m project_maker.orchestrator --walkthrough book_writer --model claude37sonnet "Write a sci-fi novel about time travel"
```

**Available Templates:**

- `book_writer`: Template for writing books or long-form content
- `game_design`: Template for designing games with rules, mechanics, etc.

To create your own template, define a configuration file in the `configs/` directory.

### Training Data Generator

The Training Data Generator creates synthetic training data for fine-tuning language models.

```bash
python -m project_maker.training_data_generator --model mistral-7b --output training_data/ --examples 100
```

This component can generate:
- Question-answer pairs
- Instruction-following examples
- Dialogue interactions
- Custom formats based on templates

## Configuration

The `configs/` directory contains configuration files for different workflows:

- `book_writer_config.py`: Configuration for book writing workflow
- `game_design_config.py`: Configuration for game design workflow

Each configuration file defines:
- Workflow steps and substeps
- Prompts and instructions for each step
- System prompts for different stages
- Token management parameters

To create a custom configuration:
1. Copy an existing config file
2. Modify the steps, substeps, and prompts
3. Add your new config file to the `configs/` directory
4. Use it with `--walkthrough your_config_name`

## Examples

### Building a Web Application

```bash
python -m project_maker.orchestrator --build --model claude-3-opus-20240229 "Create a Django web application for a blog with user authentication, comment system, and tag-based categorization."
```

### Conducting Research

```bash
python -m project_maker.orchestrator --research --model claude-3-opus-20240229 "Research the environmental impact of different types of renewable energy sources"
```

### Creating a Custom Workflow

```bash
python -m project_maker.orchestrator --walkthrough game_design --model claude37sonnet "Design a cooperative board game about space exploration"
```

## Troubleshooting

**API Rate Limits**:
- If you encounter rate limit errors, the system will automatically pause and retry
- You can adjust TOKEN_SAFETY_THRESHOLD in project_builder.py for more conservative token usage

**File Generation Issues**:
- If files are created in the wrong location, check the paths in the script generation
- Try rerunning with `--start_step 4` to regenerate the project structure

**Model Selection**:
- Different models have different capabilities and token limits
- Claude-3.7-sonnet-thinking and Deepseek R1 or other reasoning models generally provide the best results for complex projects

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

# Dependency Tracking System for Project Builder

This system enhances your AI-driven project generation by tracking and validating dependencies between files in real-time, ensuring all imports and module references are properly aligned.

## Problem

When the AI generates one file at a time, it might create imports that don't match actual module/file names in other parts of the project. This leads to broken dependencies and errors when running the generated code.

The iterative dependency tracking system solves this by:
1. Tracking dependencies as files are created
2. Providing dependency context to the LLM when implementing files
3. Checking for unresolved dependencies after each file is implemented
4. Fixing any remaining dependency issues at the end of project generation

## How to Use

### Option 1: Use the Integration Example Script

The simplest way to use the dependency tracking system is with the integration example script:

```bash
python dependency_integration_example.py "Your project vision" --model "your-model"
```

This script:
1. Runs the original project_builder.py with dependency awareness
2. Enhances LLM prompts with dependency information
3. Checks for dependencies after each file is generated
4. Fixes any remaining dependencies at the end of the process

### Option 2: Use the DependencyResolver Directly

If you want to integrate the dependency tracking more deeply into your own workflow:

```python
from dependency_tracker import DependencyResolver

# Initialize the resolver
resolver = DependencyResolver(project_dir)
resolver.initialize(file_map)

# When implementing a file, enhance the prompt with dependency context
enhanced_prompt = resolver.enhance_prompt(file_path, original_prompt)

# After implementing a file, check for dependencies
unresolved_deps = resolver.check_file(file_path, file_content)

# At the end, perform a final check and fix remaining issues
if not resolver.perform_final_check(file_map):
    # Use the iterate_fixes method with your own fix function
    resolver.iterate_fixes(file_map, your_fix_function)
```

## How It Works

1. **Dependency Detection**: The system parses imports in files and tracks which files depend on which modules.

2. **Real-time Tracking**: As each file is implemented, its dependencies are recorded and checked.

3. **Enhanced Prompting**: When implementing a file, the LLM is provided with information about:
   - Unresolved dependencies specific to this file
   - Available project modules that can be imported
   - Suggestions for handling missing dependencies

4. **Iterative Resolution**: After all files are generated, the system iteratively fixes remaining dependency issues by:
   - Identifying files with unresolved dependencies
   - Generating specialized prompts for the LLM to fix each file
   - Updating the files with the fixes
   - Re-checking dependencies until everything is resolved

5. **Missing __init__.py Generation**: The system automatically creates missing __init__.py files in Python packages.

## Files in this System

- **dependency_tracker.py**: Core module for tracking and analyzing dependencies
- **dependency_integration_example.py**: Example script showing how to use the dependency tracking system

## Benefits

1. **Reduced Errors**: Catches dependency misalignments early in the generation process
2. **Improved Coherence**: Ensures consistent naming across modules and imports 
3. **Better Context**: Provides the AI with information about existing modules
4. **Automatic Fixes**: Iteratively resolves dependency issues until the project is clean
5. **Non-Invasive**: Works without modifying the core project_builder.py functionality

This system significantly improves the reliability of AI-generated code by ensuring that all dependencies are properly aligned and resolved.

