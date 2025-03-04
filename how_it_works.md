# LLM Project Maker: How It Works

This document provides a detailed explanation of how the project generation system works, following the chronological flow from initial idea to complete project.

## 1. System Architecture Overview

The LLM Project Maker consists of several integrated components that work in sequence:

1. **Prompt Generator** - Creates structured, detailed prompts from simple user input
2. **Project Builder** - Walks an LLM through multi-phase project creation
3. **AI Orchestrator** - Manages interactions with different LLM providers 
4. **Deep Research** - Optional in-depth research capability (separate workflow)

The primary workflow follows this sequence:
```
User Input → Prompt Generator → user_prompt.txt → Orchestrator → Project Builder → Complete Project
```

## 2. Starting Your Project: Input Methods

Projects begin in one of three ways:

1. **Brief Idea + Prompt Generator**: 
   - Provide a basic idea ("Create a task management app")
   - The prompt generator expands this into a detailed specification

2. **Manual Prompt Creation**:
   - Write a detailed `user_prompt.txt` file directly
   - Skip the prompt generation step

3. **Command Line Vision**:
   - Pass a project description directly via command line arguments
   - Use this for automation or CI/CD pipelines

## 3. The Prompt Generator Process

The prompt generator (`prompt_generator.py`) transforms simple user ideas into comprehensive project specifications:

### How the Prompt Generator Works

1. **Input Collection**: 
   - Accepts a brief description of what you want to build
   - Optionally collects preference details

2. **LLM Enhancement**: 
   - Uses an LLM (Claude, DeepSeek, or Gemini) to transform your basic idea into a richly detailed prompt with:
     - Project overview
     - Core functionality requirements
     - Technical specifications
     - Deliverables
     - Success metrics

3. **Structured Output**: 
   - The enhanced prompt follows a consistent format with clear sections
   - Makes it ideal for the project builder to process

4. **Storage**: 
   - The resulting prompt is saved to `user_prompt.txt` in the project root
   - This file becomes available to other components

### Example Flow

If a user enters a simple idea like "Create a task management app", the prompt generator might produce a detailed prompt with sections on user authentication, task CRUD operations, data persistence, UI/UX requirements, and more.

## 4. The Orchestrator's Role

The `orchestrator.py` script serves as the central control point for the entire system:

1. **Entry Point Management**: 
   - Handles different execution modes:
     - Project building (`--build`)
     - Deep research (`--research`)
     - Custom workflows (`--workflow`)
     - The default Breakthrough-Idea Framework

2. **Vision/Prompt Handling**: 
   - For each mode, it:
     - Checks command-line arguments for a vision/domain
     - Looks for `user_prompt.txt` when no argument is provided
     - Passes the vision to the appropriate module

3. **Configuration**: 
   - Manages:
     - Model selection (Claude, DeepSeek, Gemini)
     - Starting points (for resuming interrupted processes)
     - Auto-approval options

## 5. AI Client Architecture

The `ai_clients.py` module provides the interface to different LLM providers:

1. **Model Support**:
   - Claude 3.7 Sonnet (Anthropic)
   - DeepSeek R1 (compatibility with OpenAI API)
   - Gemini 2.0 Pro (Google AI)

2. **The AIOrchestrator Class**:
   - Provides a consistent `call_llm()` method
   - Handles different parameter formats
   - Manages API-specific details

3. **API Integration**:
   - Loads API keys from environment variables
   - Sets appropriate model parameters
   - Handles streaming for large responses

## 6. Project Builder Overview

The project builder (`project_builder.py`) is the heart of the system, converting the detailed prompt into a complete, functional project through a methodical, phase-based approach.

### Project Vision Flow

1. **Vision Acquisition**:
   - When you run `orchestrator.py --build <model>`, the system:
     - Checks if a domain/vision was provided as a command-line argument
     - If not, it checks for and offers to use `user_prompt.txt`
     - This vision is passed to `run_project_builder()`

2. **Vision Storage and Use**:
   - The vision is stored in `step_outputs['vision']`
   - Each phase's prompt template includes a `{vision}` placeholder
   - The vision provides consistent context throughout all phases

## 7. Token Management System

The project builder includes a sophisticated token management system to handle large projects within LLM context limits:

1. **Token Budget**: 
   - Each phase has a fixed token budget (defined by `TOKEN_SAFETY_THRESHOLD`)

2. **Content Prioritization**: 
   - Content is prioritized based on importance weights:
     - Vision gets high priority as the foundational project description
     - Most recent prior phase outputs get highest priority
     - Previous substep outputs get medium priority

3. **Smart Trimming**: 
   - When content exceeds token limits, the system:
     - Preserves section headers and structure
     - Trims content proportionally based on importance weights
     - Applies consistent reduction percentages

4. **Adaptive Token Allocation**: 
   - For very large projects, the system can:
     - Apply aggressive trimming when needed
     - Offer options to continue, trim more, or skip steps
     - Maintain key context even with severe trimming

## 8. Project Building Phases

The project builder walks through 6 sequential phases, each building on the previous:

### Phase 1: Project Planning (3 substeps)
   - **Project Overview**: Define scope, goals, and requirements
   - **Technology Stack Selection**: Choose languages, frameworks, and libraries
   - **Project Structure Planning**: Plan high-level organization

### Phase 2: System Architecture (3 substeps)
   - **Component Architecture**: Design system components and their relationships
   - **Data Architecture**: Define data models, relationships, and storage
   - **Interface Design**: Specify APIs, service boundaries, and contracts

### Phase 3: Project Structure (3 substeps)
   - **Directory Structure**: Define the file and folder organization
   - **File Templates**: Create templates for different file types
   - **Build Configuration**: Set up configuration for development and deployment

### Phase 4: Implementation Plan
   - Create a detailed roadmap for building the project
   - Specify file dependencies and implementation order
   - Generate a setup script for the project structure

### Phase 5: File Implementation
   - Actual coding of all project files
   - Prioritize core files and dependencies first
   - Integrate components according to the architecture

### Phase 6: Assembly and Usage Guide
   - Create comprehensive README
   - Generate documentation
   - Provide usage examples and deployment guides

## 9. The Phase-by-Phase Process

For each phase:

1. **Prompt Construction**:
   - The builder constructs a specific prompt using:
     - The vision (from `user_prompt.txt` or command line)
     - Outputs from previous phases
     - Phase-specific instructions

2. **Token Management**:
   - It allocates space between:
     - The project vision
     - Previous phase outputs
     - Current phase instructions

3. **AI Generation**:
   - The AI generates detailed output for the phase
   - The system provides relevant context from previous phases

4. **Output Processing**:
   - The system parses file markers from the response (`=== File: path/to/file ===`)
   - Creates actual files in the project structure

5. **Context Storage**:
   - The output is stored both as files and in memory
   - This provides context for subsequent phases

## 10. Structure Creation Process

Before implementing code, the system creates the complete project structure:

1. **Script Generation Process**:
   - The system analyzes the project structure document created in Phase 3
   - It extracts directory structures and file paths using pattern recognition
   - A bash script (`setup_project_structure.sh`) is generated with:
     ```bash
     mkdir -p "path/to/directory"
     touch "path/to/file.ext"
     ```
   - The script includes clear progress reporting for each operation
   - Path handling is normalized for cross-platform compatibility

2. **Script Execution**:
   - The system executes this script in a controlled environment
   - On Windows, it attempts to use Git Bash if available
   - Falls back to a Python-based interpretation if needed
   - Creates all directories with proper nesting
   - Initializes empty files as placeholders
   - Validates the structure creation by counting created files

## 11. File Implementation Process

### Intelligent File Discovery and Prioritization

1. **Comprehensive File Search**:
   - The `discover_all_files()` function recursively walks the project structure
   - It identifies files by extension (.py, .js, .html, etc.)
   - Filters out non-implementation files (like documentation)
   - Creates a master list of all files needing implementation
   - Debug information helps track found files

2. **Sophisticated Prioritization**:
   - The `prioritize_files()` function creates an optimal implementation order
   - It uses multiple heuristics:
     - Configuration files first (containing "config", "settings", etc.)
     - Core files second (containing "core", "main", "__init__", etc.)
     - Other files afterward, using the implementation plan for guidance
   - The function can parse the implementation plan document for dependency hints
   - It handles circular dependencies by making intelligent breaks

3. **Progress Tracking Setup**:
   - Creates a JSON-based progress tracking file
   - Loads any existing progress from previous runs
   - Identifies files that have already been implemented
   - Creates a precise implementation queue for remaining files

### Iterative File-by-File Implementation Loop

For each file in the prioritized list, the system follows a detailed process:

1. **Initial File Check**:
   - Verifies if the file already exists from a previous run
   - Checks if it has content (non-zero size)
   - If populated, reads content and adds to in-memory model
   - If empty, proceeds with implementation

2. **Context Gathering and Prompt Construction**:
   - Assembles a comprehensive file-specific prompt with sections:
     ```
     # File Implementation: path/to/file.ext
     
     ## Project Context
     [Complete vision from step_outputs['vision']]
     
     ## Project Structure
     [First 2000 chars of the structure document]
     
     ## Relevant Architecture & Design
     [First 1000 chars of architecture outputs]
     [First 1000 chars of structure outputs]
     
     ## Implementation Task
     Your task is to implement: path/to/file.ext
     
     ## Implementation Requirements
     [Detailed list of requirements for implementation]
     ```

3. **File-Specific Context Enhancement**:
   - Analyzes the file's directory location and purpose
   - Includes relevant outputs from prior steps focused on this file's role
   - For framework-specific files, includes framework-specific best practices
   - For interdependent files, includes interfaces they must implement
   - Adds information about existing models, utilities, or services

4. **Specialized System Prompt for Implementation**:
   - Uses a focused system prompt that emphasizes:
     ```
     You are an expert software engineer implementing a critical file in a complex project.
     CRITICAL INSTRUCTIONS:
     1. Write COMPLETE, FUNCTIONAL code that can be used in a production environment
     2. Do NOT write pseudo-code or example code
     3. Do NOT include comments like "This is just a demonstration"
     4. Implement FULL functionality according to requirements
     5. Include ALL necessary imports, constants, error handling, and logic
     6. Your code will be directly saved to a file and is expected to work without modifications
     ```

5. **Advanced AI Configuration for Implementation**:
   - Sets `max_tokens` to the maximum allowed (64,000)
   - Uses temperature=0.0 for deterministic code generation
   - Disables creative variations for consistency across files
   - Configures streaming for large file implementations

6. **AI Response Processing**:
   - Parses the AI response for file markers (`=== File: path/to/file.ext ===`)
   - Extracts the content between markers
   - Handles special cases like multi-file responses
   - Normalizes line endings for the target platform

7. **File Writing and Verification**:
   - Creates any necessary parent directories
   - Writes the content to the target file
   - Verifies successful file creation
   - Adds the file to the in-memory model (`file_map`)

8. **Progress Tracking and Update**:
   - Adds the implemented file to the completed list
   - Updates the progress tracking JSON file
   - Prints progress statistics (X/Y files completed)
   - Ensures partial progress is never lost due to crashes

## 12. Building Context Across Files

### Progressive Context Building

As the implementation progresses file-by-file, the system builds a progressively richer context:

1. **In-Memory File Map Growth**:
   - Each implemented file is added to `file_map`
   - This map becomes part of the context for subsequent files
   - Files late in the implementation can reference patterns from earlier files

2. **Pattern and Convention Propagation**:
   - Naming conventions established in early files are referenced
   - Function signatures, class structures, and design patterns are maintained
   - The LLM is guided to maintain consistent coding style across files

3. **Import Management Across Files**:
   - The system maintains correct relative imports between files
   - Package structure is consistent throughout the codebase
   - Dependencies declared in early files are properly imported in later files

4. **Interface Implementation Checking**:
   - When implementing classes that must adhere to interfaces:
     - The interface definition is included in the context
     - Required methods and signatures are highlighted
     - Type compatibility is maintained

### File-Specific Knowledge Enhancement

The system enhances the prompt with file-specific knowledge based on the file type:

1. **For Models/Schemas**:
   - Includes database schema details
   - Specifies field types, validations, and relationships
   - References relevant data architecture decisions

2. **For Controllers/Services**:
   - Includes API endpoint specifications
   - Details required business logic
   - References models they operate on
   - Explains authorization requirements

3. **For Utility Files**:
   - Details reuse patterns across the project
   - Specifies error handling conventions
   - Includes logging requirements

4. **For Frontend Components**:
   - Includes UI/UX requirements
   - References API endpoints to consume
   - Details state management approach
   - Explains component hierarchy

5. **For Configuration Files**:
   - Lists all required configuration parameters
   - Specifies environment variables
   - Includes deployment-specific requirements

### Implementation Order Management

The system intelligently manages implementation order to ensure proper dependencies:

1. **Dependency Resolution**:
   - The implementation plan (Phase 4) includes explicit dependency mapping
   - Files are sorted based on dependency chains (core utilities → services → controllers → UI)
   - The builder prioritizes foundational files before dependent ones

2. **Typical Implementation Sequence**:
   - **Configuration Files** (First)
   - **Core Utilities** (Second)
   - **Data Models** (Third)
   - **Services/Business Logic** (Fourth)
   - **API Endpoints** (Fifth)
   - **User Interface** (Last)

## 13. Cross-File Consistency Mechanisms

The project builder maintains coherence across large numbers of files through several mechanisms:

1. **Shared Vision Context**: 
   - Every file implementation prompt includes the complete project vision
   - This ensures every file is built with the same overall understanding

2. **Phase Persistence**:
   - Outputs from planning, architecture, and structure phases are stored in `step_outputs`
   - Each file implementation references these shared specifications
   - This creates consistency across all files regardless of when they're generated

3. **Technical Decisions Propagation**:
   - Key decisions (frameworks, patterns, naming conventions) from early phases
   - Get included in each file implementation prompt
   - Ensures architectural consistency across the codebase

4. **Cross-File Referencing**:
   - **Import Statement Consistency**: Correct relative paths and module naming
   - **Interface Adherence**: Ensuring methods are implemented as expected
   - **Project-Wide Typing**: Consistent type definitions across files

5. **Contextual Prompting**: 
   - Each file implementation includes its specific context in the project structure
   - References patterns from previously generated files
   - Includes architecture diagrams showing relationships
   - Specifies the file's role in the overall system

## 14. Crash Recovery and Resilience

The crash recovery system ensures work is never lost:

1. **Granular Progress Tracking**:
   - Maintains a JSON file with all completed files
   - Updates this file after each successful implementation
   - Stores in a reliable location (doc directory)

2. **Intelligent Resumption**:
   - On restart, loads the progress tracking file
   - Rebuilds the in-memory model from existing files
   - Creates a new implementation queue excluding completed files
   - Resumes exactly where it left off

3. **File Verification**:
   - Checks file existence before implementation
   - Verifies file contents are valid
   - Handles edge cases like partially written files

4. **Implementation Protection**:
   - Never overwrites existing non-empty files
   - Adds existing files to the in-memory model
   - Ensures consistency between files regardless of implementation order

## 15. Memory Management Strategies

Creating hundreds of files requires strategies for managing LLM context limitations:

1. **Selective Context Inclusion**:
   - The system can't include all previously generated files in each prompt
   - Instead, it prioritizes including:
     - The most relevant files for the current implementation
     - Core interface definitions
     - Direct dependencies

2. **Abstraction Level Management**:
   - Early phases create detailed architecture diagrams
   - These diagrams serve as compact representations of system relationships
   - Each file implementation refers to the diagram rather than needing every implementation detail

3. **Progressive Knowledge Transfer**:
   - Knowledge about the project builds up across steps
   - Early steps define patterns that later steps follow
   - Each implementation reinforces and builds upon established conventions

## 16. Quality Control and Validation

After implementation, the system performs quality control:

1. **Syntax Checking**:
   - Runs language-specific syntax validators
   - For Python: uses Python's built-in `compile()` function
   - For JavaScript: uses Node.js with `--check` flag
   - For JSON, HTML, CSS: runs format validation

2. **Error Reporting**:
   - Collects syntax errors by file
   - Displays line numbers and error descriptions
   - Offers options to fix or continue

3. **Integration Validation** (when possible):
   - Checks import statements for correct paths
   - Validates that referenced modules exist
   - Ensures class references are consistent

## 17. Running Your Own Projects

To create your own project, follow this workflow:

1. **Generate a Prompt** (optional but recommended):
   ```
   python prompt_generator.py --model claude37sonnet
   ```
   - Enter your basic idea
   - Review and save the detailed prompt to `user_prompt.txt`

2. **Run the Project Builder**:
   ```
   python orchestrator.py --build claude37sonnet
   ```
   - The system will detect and use `user_prompt.txt`
   - Follow the prompts to guide the process

3. **Find Your Project**:
   - The complete project will be in the `generated_project/` directory
   - Review the documentation in `generated_project/doc/`
   - Use the README for guidance on using your new project

## 18. Advanced Features

The system includes several advanced features:

1. **Resumable Builds**: Can continue from any step or substep if interrupted

2. **Model Switching**: Can use different LLMs for different capabilities

3. **Custom Workflows**: Supports domain-specific template-based workflows

4. **Deep Research**: Can perform in-depth research on topics before building

## 19. Technical Implementation Notes

For those interested in the implementation details:

1. **File Parsing**: The system uses regex patterns to extract file markers from LLM responses

2. **Cross-Platform Compatibility**: Path handling works across Windows, macOS, and Linux

3. **Token Estimation**: Uses a character-based heuristic to estimate tokens

4. **Error Handling**: Includes robust error handling and debugging output

5. **Extensibility**: The modular design allows adding new models or steps

## 20. Conclusion and Benefits

The LLM Project Maker yields several significant benefits:

1. **Coherent Large-Scale Projects**:
   - Projects with 50-300 files maintain consistency throughout
   - Dependencies remain aligned even across complex codebases
   - Features work together across architectural boundaries

2. **Extensibility**:
   - Generated projects can be extended with new files
   - Additional features naturally align with existing patterns
   - New code can be seamlessly integrated

3. **Maintenance Advantages**:
   - Consistent structure makes maintenance easier
   - Well-defined patterns simplify debugging
   - Documentation created throughout the process provides context

4. **Adaptability to Different Stacks**:
   - The same project architecture adapts to different technology stacks
   - File dependencies are managed correctly regardless of language
   - Works equally well for monoliths, microservices, or serverless architectures

By combining structured planning phases with intelligent file ordering and context management, the project builder creates remarkably coherent codebases that would otherwise require a team of developers working with shared understanding and conventions.
