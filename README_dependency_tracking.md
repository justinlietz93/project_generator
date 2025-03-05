# Dependency Tracking System for Project Builder

This extension adds dependency tracking to the project_builder.py workflow, ensuring that all dependencies between files are properly managed during the AI-driven file generation process.

## Overview

The dependency tracking system addresses several challenges in AI-generated code:

1. **Misaligned Dependencies**: When the AI generates one file at a time, it might create imports that don't match actual module/file names in other parts of the project.

2. **Implicit Dependencies**: The AI might assume dependencies exist without explicitly creating them.

3. **Dependency Ordering**: Some files need to be created before others that depend on them.

4. **Consistency**: Ensuring consistent naming across a large codebase.

## How It Works

The system consists of three main components:

1. **dependency_tracker.py**: Core module for tracking and analyzing dependencies between files
2. **dependency_integration.py**: Hooks that integrate with project_builder.py without modifying it
3. **dependency_enhanced_builder.py**: Wrapper script that enhances project_builder.py with dependency tracking

### Key Features

- **Automatic Dependency Detection**: Parses imports and tracks which files depend on which modules
- **Project-Specific Module Detection**: Distinguishes between built-in, external, and project-specific modules
- **Real-time Dependency Tracking**: Updates the dependency graph after each file is implemented
- **Intelligent File Ordering**: Prioritizes files based on dependency relationships
- **Enhanced LLM Prompts**: Provides the AI with dependency context when implementing files
- **Missing __init__.py Generation**: Automatically creates missing __init__.py files for Python packages
- **Comprehensive Reporting**: Generates detailed dependency reports for review

## Usage

Instead of running `project_builder.py` directly, run `dependency_enhanced_builder.py` with the same arguments:

```bash
python dependency_enhanced_builder.py "Your project vision" --model gpt-4-turbo
```

The enhanced builder will:

1. Run the original project_builder.py with dependencies in mind
2. Track dependencies between files as they're being implemented
3. Enhance LLM prompts with dependency information
4. Report any dependency issues
5. Generate a comprehensive dependency report

## How Dependencies are Tracked

1. **Import Analysis**: Python (using AST) and JavaScript (using regex) imports are detected
2. **Module Classification**: 
   - Built-in modules (Python standard library)
   - External modules (installed packages)
   - Project modules (modules implemented in the project)

3. **Dependency Graph Construction**:
   - Maps files to their dependencies
   - Maps modules to their implementing files
   - Tracks unresolved dependencies

4. **Dependency Resolution**:
   - When a new file is implemented, we check if it resolves any pending dependencies
   - Dependencies are "resolved" when the module they refer to is implemented

## Directory Structure

```
.
├── project_builder.py          # Original project builder (unchanged)
├── dependency_enhanced_builder.py  # Main wrapper script for project_builder
├── dependency_tracker.py       # Core dependency tracking functionality
├── dependency_integration.py   # Integration hooks for project_builder
└── .project_builder/           # Generated during execution
    ├── dependency_state.json   # Saved state of dependencies
    └── dependency_report.md    # Generated dependency report
```

## Example Dependency Report

A typical dependency report looks like:

```markdown
# Project Dependency Report
Generated on: my_project

## All Dependencies Resolved!

## Modules and Implementing Files
### api
- api/__init__.py
- api/routes.py

### database
- database/__init__.py
- database/models.py

### utils
- utils/__init__.py
- utils/helpers.py

## File Dependencies
### api/routes.py depends on:
- database/models.py
- utils/helpers.py

### app.py depends on:
- api/routes.py
- database/models.py
```

## Benefits

1. **Reduced Errors**: Catches dependency misalignments early
2. **Better Structure**: Encourages proper module organization
3. **Enhanced Context**: The AI has better visibility into project dependencies
4. **Optimized Order**: Files get implemented in a sensible order based on dependencies
5. **Complete Validation**: Ensures all dependencies are addressed before moving on

## Limitations

1. It can't fix all dependency issues automatically - some may require human intervention
2. Regex-based JS import detection is not as robust as Python's AST parsing
3. The system focuses on top-level module names, not deeper import paths

## Future Improvements

1. Deeper path analysis for imports
2. Language-specific dependency resolution strategies
3. Automated dependency suggestion for the AI
4. Integration with package managers for external dependencies 