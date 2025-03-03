# AI Project Builder & Research Proposal Framework

This project implements two main functionalities:
1. An AI-powered project builder that systematically creates complete software projects from high-level descriptions
2. An AI research proposal generator that creates formal academic research proposals from project documentation

## Overview

The Project Builder is designed to:
1. Take a user's project description/requirements
2. Plan and design the project architecture
3. Create a complete project structure with folders and files
4. Implement each file with appropriate code
5. Provide comprehensive assembly instructions and usage guidance

## Core Components

The system consists of several key modules:

1. **Project Builder (`project_builder.py`)**: The main module that implements the project building workflow
2. **AI Proposal Generator (`ai_proposal_generator.py`)**: Generates formal academic research proposals
3. **AI Orchestrator (`ai_clients.py`)**: Handles interactions with the LLM models (Claude 3.7 Sonnet or DeepSeek)
4. **Utility Functions (`utils.py`)**: Provides shared functionality for file operations and response parsing

## Project Building Process

The system follows a structured 6-phase approach:

### 1. Project Planning
- **Sub-Step A**: Project Overview
  - Vision Summary
  - Project Objectives
  - Expected Outcomes

- **Sub-Step B**: Technology Stack
  - Core Technologies
  - Supporting Libraries
  - Development Tools

- **Sub-Step C**: Project Structure
  - Directory organization
  - Key files and purposes
  - Module organization
  - Naming conventions

### 2. System Architecture
- **Sub-Step A**: Component Architecture
  - Major system components
  - Component responsibilities
  - Component interactions
  - Architectural patterns

- **Sub-Step B**: Data Architecture
  - Data models and schemas
  - Data flow between components
  - Storage solutions
  - Security considerations

- **Sub-Step C**: Interface Design
  - API contracts
  - Communication protocols
  - Interface patterns
  - Error handling

### 3. Project Structure
- **Sub-Step A**: Directory Structure
  - Directory hierarchy
  - Organization patterns
  - Future expansion considerations
  - Build/deployment structure

- **Sub-Step B**: File Templates
  - Core file templates
  - Naming conventions
  - Organization rules
  - Configuration templates

- **Sub-Step C**: Build Configuration
  - Build scripts
  - Dependency management
  - Development tools
  - CI/CD templates

### 4. Implementation Plan
Creates a detailed plan for implementing the project, including:
- File implementation order
- Dependencies between components
- Complexity estimates
- Testing strategy

### 5. File Implementation
Implements each file in the project following strict requirements:
- Production-ready code quality
- Comprehensive error handling
- Complete documentation
- Security best practices
- Testing considerations

### 6. Assembly and Usage Guide
Creates comprehensive documentation including:
- Detailed README.md
- Installation instructions
- Configuration guide
- Usage examples
- API documentation
- Deployment guidelines
- Troubleshooting tips

## Output Structure

The Project Builder creates files in the `generated_project/` directory:

```
generated_project/
├── doc/
│   ├── 01_project_plan_overview.md
│   ├── 01_project_plan_tech.md
│   ├── 01_project_plan_structure.md
│   ├── 02A_component_architecture.md
│   ├── 02B_data_architecture.md
│   ├── 02C_interface_design.md
│   ├── 03A_directory_structure.md
│   ├── 03B_file_templates.md
│   ├── 03C_build_configuration.md
│   └── 04_implementation_plan.md
├── src/
│   └── [Generated source files]
└── README.md
```

## Usage

### Project Builder Usage

```bash
python project_builder.py <model_name> "Your project description"
```

Where `model_name` is either:
- `claude37sonnet` for Claude 3.7 Sonnet
- `deepseekr1` for DeepSeek R1

Example:
```bash
python project_builder.py claude37sonnet "Create a web application for tracking personal fitness with goal setting, progress visualization, and social sharing features"
```

### Research Proposal Generator Usage

```bash
python ai_proposal_generator.py --model <model_name>
```

Where `model_name` is either:
- `claude` for Claude 3.7 Sonnet
- `deepseek` for DeepSeek R1

The proposal generator reads files from the `some_project/doc` folder in this order:
1. `01_CONTEXT_CONSTRAINTS.md`
2. `02_DIVERGENT_SOLUTIONS.md`
3. `03_DEEP_DIVE_MECHANISMS.md`
4. `04_SELF_CRITIQUE_SYNERGY.md`
5. `05_BREAKTHROUGH_BLUEPRINT.md`
6. `06_IMPLEMENTATION_PATH.md`
7. `07_NOVELTY_CHECK.md`
8. `08_ELABORATIONS.md`

The generated proposal will be saved as `ai_research_proposal.md` in the project root.

## Environment Setup

The system requires API keys for the LLM service you choose:

- For Claude 3.7 Sonnet: Set the `ANTHROPIC_API_KEY` environment variable
- For DeepSeek R1: Set the `DEEPSEEK_API_KEY` environment variable

API keys can be set in a `.env` file in the project root directory.

## Key Features

1. **Structured Process**: Follows a carefully designed phase-by-phase approach
2. **Production Quality**: Enforces high standards for code and documentation
3. **Comprehensive Context**: Each phase builds on previous decisions
4. **Detailed Documentation**: Generates thorough documentation at every level
5. **Security Focus**: Emphasizes security best practices throughout
6. **Testing Consideration**: Includes testing requirements in implementation
7. **Research Proposal Generation**: Creates formal academic research proposals from project documentation

## Technical Requirements

- Python 3.6+
- Required packages: See `requirements.txt`

## Cross-Platform Compatibility

The system uses Python's `pathlib` for platform-independent path handling, ensuring compatibility across:
- Windows
- Linux
- macOS

## Example Outputs

### Project Builder Output (excerpt)
```markdown
# Project Plan: Personal Fitness Tracker

## Project Objectives
- Create a web application for tracking personal fitness
- Implement goal setting and progress visualization features
- Develop social sharing capabilities
- Ensure mobile-responsive design

## Technology Stack
- Frontend: React.js with TypeScript
- Backend: Node.js with Express
- Database: MongoDB
- Authentication: JWT with OAuth
- Visualization: D3.js
- Hosting: Docker on AWS
```

### Research Proposal Output (excerpt)
```markdown
# NeuroCognitive Architecture (NCA): A Brain-Inspired LLM Framework

## Abstract
This research proposal outlines a novel approach to large language model architectures 
inspired by neurobiological principles. The NeuroCognitive Architecture (NCA) framework 
aims to bridge the gap between artificial neural networks and biological neural 
processing by incorporating key mechanisms from human cognition.

## Research Objectives
1. Develop a brain-inspired architecture for language models
2. Implement neurobiological attention mechanisms
3. Create a modular system for cognitive task processing
4. Evaluate performance against existing LLM architectures

## Methodology
The research will follow a systematic approach:
1. Literature review of neuroscience and LLM architectures
2. Design and implementation of the NCA framework
3. Experimental validation using standard NLP benchmarks
4. Comparative analysis with existing architectures
```
