#!/usr/bin/env python3

"""
game_design_config.py

Configuration for the Game Design workflow.
This file defines the steps, substeps, and prompts for guiding an LLM through
the process of creating a comprehensive game design document.
"""

from utils import SubStep

# Workflow configuration
WORKFLOW_NAME = "Game Design Document Creator"
OUTPUT_DIR = "game_design"
DOCS_SUBDIR = "design_docs"

# Define the workflow steps and substeps
WORKFLOW_STEPS = [
    {
        "phase_name": "Game Concept",
        "system_prompt": """You are an expert game designer with extensive experience in concept development.
Your task is to develop a compelling game concept based on the vision provided.""",
        "user_prompt_template": """# Game Concept Phase

## Game Vision:
{vision}

## Your Task:
Develop the core concept for this game.

Output your work in the following files:
""",
        "sub_steps": [
            SubStep("1A", "High Concept & Vision", """Develop the core game concept:
1. Create a high concept statement (1-2 sentences)
2. Define the game's genre and format (e.g., RPG, FPS, platformer, etc.)
3. Identify target platforms (PC, console, mobile, etc.)
4. Determine target audience and age rating
5. Summarize the game's unique selling points (USPs)

Output in `=== File: {docs_dir}/01A_high_concept.md ===`"""),
            
            SubStep("1B", "Game Pillars", """Define the core pillars of the game:
1. Identify 3-5 core design pillars (fundamental principles)
2. For each pillar, explain:
   - What it means for gameplay
   - How it will influence design decisions
   - Examples of how it will manifest in the game
3. Describe how these pillars work together
4. Explain how these pillars support the high concept

Output in `=== File: {docs_dir}/01B_game_pillars.md ===`"""),
            
            SubStep("1C", "Competitive Analysis", """Analyze similar games and market positioning:
1. Identify 3-5 comparable games or competitors
2. For each, analyze:
   - Core gameplay and mechanics
   - Strengths and weaknesses
   - Target audience and performance
3. Explain how your game will differentiate itself
4. Identify market opportunities and potential challenges
5. Summarize the competitive advantage

Output in `=== File: {docs_dir}/01C_competitive_analysis.md ===`""")
        ]
    },
    
    {
        "phase_name": "Game Systems",
        "system_prompt": """You are an expert game systems designer with deep understanding of mechanics and dynamics.
Your task is to design the core systems and mechanics for the game.""",
        "user_prompt_template": """# Game Systems Phase

## Game Vision:
{vision}

## Previous Development:
{previous_outputs}

## Your Task:
Design the core systems and mechanics that will define the gameplay experience.

Output your work in the following files:
""",
        "sub_steps": [
            SubStep("2A", "Core Gameplay Loop", """Define the core gameplay loop:
1. Describe the minute-to-minute gameplay experience
2. Detail the primary activities players will engage in
3. Explain the core interaction loops (actions → rewards → progression)
4. Diagram the flow of gameplay (using text descriptions)
5. Connect the gameplay loop to the game pillars

Output in `=== File: {docs_dir}/02A_gameplay_loop.md ===`"""),
            
            SubStep("2B", "Game Mechanics", """Design the primary game mechanics:
1. Detail 5-10 key mechanics that drive the gameplay
2. For each mechanic, specify:
   - How it works in detail
   - Player inputs and system responses
   - Balancing considerations
   - How it interacts with other mechanics
3. Identify any novel or innovative mechanics
4. Explain how the mechanics support the core pillars

Output in `=== File: {docs_dir}/02B_game_mechanics.md ===`"""),
            
            SubStep("2C", "Progression Systems", """Design the progression systems:
1. Define how players advance through the game
2. Detail any leveling or upgrade systems
3. Explain unlock mechanisms for:
   - Skills/abilities
   - Items/equipment
   - Content/levels
4. Describe the pacing of progression
5. Connect progression to player motivation and retention

Output in `=== File: {docs_dir}/02C_progression_systems.md ===`""")
        ]
    },
    
    {
        "phase_name": "World & Content",
        "system_prompt": """You are an expert game world builder and content designer.
Your task is to develop the game world, characters, and content that players will experience.""",
        "user_prompt_template": """# World & Content Phase

## Game Vision:
{vision}

## Previous Development:
{previous_outputs}

## Your Task:
Design the game world, narrative elements, and content structure.

Output your work in the following files:
""",
        "sub_steps": [
            SubStep("3A", "World Design", """Create the game world:
1. Establish the setting and environment
2. Define the world's history and background
3. Detail the aesthetic style and visual themes
4. Describe key locations and their purpose
5. Explain how the world connects to gameplay

Output in `=== File: {docs_dir}/03A_world_design.md ===`"""),
            
            SubStep("3B", "Narrative Design", """Develop the narrative elements:
1. Create the main storyline (if applicable)
2. Develop key characters and their roles
3. Define the storytelling approach (explicit, environmental, etc.)
4. Outline key story moments and how they integrate with gameplay
5. Detail how player agency influences the narrative (if applicable)

Output in `=== File: {docs_dir}/03B_narrative_design.md ===`"""),
            
            SubStep("3C", "Level/Content Structure", """Design the content structure:
1. Outline the overall game structure (levels, missions, etc.)
2. For each major content piece, specify:
   - Objectives and challenges
   - Key mechanics utilized
   - Unique elements or set pieces
3. Detail the difficulty curve across content
4. Explain content variety and pacing
5. Describe how content connects to progression systems

Output in `=== File: {docs_dir}/03C_content_structure.md ===`""")
        ]
    },
    
    {
        "phase_name": "Implementation Planning",
        "system_prompt": """You are an expert game producer with experience in production planning and technical implementation.
Your task is to create practical plans for implementing the game design.""",
        "user_prompt_template": """# Implementation Planning Phase

## Game Vision:
{vision}

## Previous Development:
{previous_outputs}

## Your Task:
Create practical implementation plans for the game design.

Output your work in the following files:
""",
        "sub_steps": [
            SubStep("4A", "Technical Specifications", """Define technical requirements and specifications:
1. Identify target technical specifications:
   - Platform requirements
   - Performance targets
   - Engine/technology requirements
2. List key technical challenges
3. Recommend technological solutions for major features
4. Outline asset requirements (art, audio, etc.)
5. Identify any technical constraints or limitations

Output in `=== File: {docs_dir}/04A_technical_specifications.md ===`"""),
            
            SubStep("4B", "Production Roadmap", """Create a production roadmap:
1. Break down development into phases:
   - Pre-production
   - Production
   - Post-production
2. Define milestones and deliverables for each phase
3. Identify dependencies between different elements
4. Recommend team structure and resource needs
5. Outline potential risks and contingency plans

Output in `=== File: {docs_dir}/04B_production_roadmap.md ===`"""),
            
            SubStep("4C", "Prototype Plan", """Design an initial prototype plan:
1. Define the scope of a first playable prototype
2. Identify the core mechanics to be prototyped first
3. Create a prioritized feature list for early implementation
4. Outline testing objectives and success criteria
5. Recommend a plan for prototype iteration

Output in `=== File: {docs_dir}/04C_prototype_plan.md ===`""")
        ]
    },
    
    {
        "phase_name": "Final Design Document",
        "system_prompt": """You are a senior game design document specialist with extraordinary organizational skills.
Your task is to compile and refine all the design elements into a cohesive game design document (GDD).""",
        "user_prompt_template": """# Final Design Document Phase

## Game Vision:
{vision}

## Previous Development:
{previous_outputs}

## Your Task:
Compile a complete game design document that effectively communicates the entire design.

Output your work in the following files:
""",
        "sub_steps": [
            SubStep("5A", "Executive Summary", """Create a concise executive summary:
1. Write a compelling 1-2 page overview of the game
2. Summarize key features and innovations
3. Highlight market positioning and opportunities
4. Include visuals descriptions or mockups
5. Present the core value proposition

Output in `=== File: {docs_dir}/05A_executive_summary.md ===`"""),
            
            SubStep("5B", "Complete GDD", """Compile the complete game design document:
1. Create a comprehensive GDD with proper structure including:
   - Table of contents
   - All previously developed sections, properly organized
   - Clear headings and navigation
2. Ensure consistency across all sections
3. Add cross-references between related sections
4. Include placeholders for future visual assets
5. Add glossary of terms and appendices as needed

Output in `=== File: {docs_dir}/05B_complete_gdd.md ===`"""),
            
            SubStep("5C", "Future Considerations", """Document future considerations:
1. Identify potential expansions or DLC opportunities
2. Outline live service elements (if applicable)
3. Suggest community and engagement strategies
4. Describe monetization options and strategies
5. Present a vision for franchise potential

Output in `=== File: {docs_dir}/05C_future_considerations.md ===`""")
        ]
    }
] 