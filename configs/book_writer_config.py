#!/usr/bin/env python3

"""
book_writer_config.py

Configuration for the Book Writer workflow.
This file defines the steps, substeps, and prompts for guiding an LLM through
the process of creating a book or narrative.
"""

from utils import SubStep

# Workflow configuration
WORKFLOW_NAME = "Book Writer"
OUTPUT_DIR = "book_project"
DOCS_SUBDIR = "manuscript"

# Define the workflow steps and substeps
WORKFLOW_STEPS = [
    {
        "phase_name": "Story Development",
        "system_prompt": """You are an expert storyteller and novelist with extensive experience in narrative design.
Your task is to help develop a compelling story based on the concept provided.""",
        "user_prompt_template": """# Story Development Phase

## Concept:
{vision}

## Your Task:
Develop the fundamental elements of this story.

Output your work in the following files:
""",
        "sub_steps": [
            SubStep("1A", "Premise & Theme", """Develop the core premise and themes:
1. Create a compelling premise (1-2 sentences that capture the essence)
2. Identify 3-5 major themes to explore
3. Define the genre and narrative style
4. Establish the overall tone and mood
5. Identify the central conflict or question

Output in `=== File: {docs_dir}/01A_premise_theme.md ===`"""),
            
            SubStep("1B", "Setting Development", """Create a rich, detailed setting:
1. Define the time period and location(s)
2. Describe the world's unique aspects and rules
3. Explain cultural, social, and/or political elements
4. Identify important locations and their significance
5. Establish atmosphere and environmental details

Output in `=== File: {docs_dir}/01B_setting.md ===`"""),
            
            SubStep("1C", "Character Profiles", """Develop the main characters:
1. Create 3-7 primary character profiles with:
   - Name, age, and physical description
   - Personality traits, strengths, and flaws
   - Background and personal history
   - Goals, motivations, and fears
   - Character arc outline
2. Describe relationships between characters
3. Include any important secondary characters

Output in `=== File: {docs_dir}/01C_characters.md ===`""")
        ]
    },
    
    {
        "phase_name": "Narrative Structure",
        "system_prompt": """You are an expert novelist and story structure specialist with deep understanding of narrative architecture.
Your task is to plan the structure and plot of the story based on the established elements.""",
        "user_prompt_template": """# Narrative Structure Phase

## Concept:
{vision}

## Previous Development:
{previous_outputs}

## Your Task:
Create a detailed narrative structure and plot for this story.

Output your work in the following files:
""",
        "sub_steps": [
            SubStep("2A", "Plot Outline", """Develop the main plot structure:
1. Create a detailed synopsis (1-2 pages)
2. Structure the plot using a narrative framework (3-act, Hero's Journey, etc.)
3. Identify major plot points and turning points
4. Define the inciting incident, midpoint, climax, and resolution
5. Establish subplots and how they integrate with the main plot

Output in `=== File: {docs_dir}/02A_plot_outline.md ===`"""),
            
            SubStep("2B", "Chapter Breakdown", """Create a chapter-by-chapter outline:
1. Divide the story into 10-30 chapters
2. Write a brief summary for each chapter (2-4 sentences each)
3. Identify the purpose of each chapter (character development, plot advancement, etc.)
4. Note POV character for each chapter if multiple
5. Ensure proper pacing and flow between chapters

Output in `=== File: {docs_dir}/02B_chapter_breakdown.md ===`"""),
            
            SubStep("2C", "Key Scenes", """Develop the most important scenes:
1. Identify 5-10 key scenes that are crucial to the story
2. For each key scene, describe:
   - Setting and atmosphere
   - Characters involved
   - Main action or conflict
   - Purpose in the overall narrative
   - Emotional impact
3. Ensure these scenes effectively build toward the climax

Output in `=== File: {docs_dir}/02C_key_scenes.md ===`""")
        ]
    },
    
    {
        "phase_name": "Writing & Style",
        "system_prompt": """You are an accomplished author with a distinctive voice and style.
Your task is to establish the narrative voice and write sample content for the story.""",
        "user_prompt_template": """# Writing & Style Phase

## Concept:
{vision}

## Previous Development:
{previous_outputs}

## Your Task:
Develop the narrative voice and write key passages of the story.

Output your work in the following files:
""",
        "sub_steps": [
            SubStep("3A", "Narrative Voice", """Establish the narrative voice and style:
1. Define the narrative perspective (1st person, 3rd person limited, etc.)
2. Create a style guide with:
   - Tone and mood guidelines
   - Dialogue style and patterns
   - Description style and focus
   - Pacing guidelines
   - Language choices (formal/informal, complex/simple, etc.)
3. Provide examples of the style in short passages

Output in `=== File: {docs_dir}/03A_narrative_voice.md ===`"""),
            
            SubStep("3B", "Opening Chapter", """Write the opening chapter:
1. Create a compelling first chapter (1,500-2,500 words)
2. Introduce key elements (protagonist, setting, tone)
3. Establish an effective hook
4. Set up initial conflict or question
5. End with a reason for readers to continue

Output in `=== File: {docs_dir}/03B_opening_chapter.md ===`"""),
            
            SubStep("3C", "Pivotal Scene", """Write a pivotal scene from the story:
1. Create a full scene (1,000-2,000 words) for one of the key moments
2. Choose a scene that showcases character development and/or plot advancement
3. Include effective dialogue, description, and action
4. Demonstrate the established narrative voice
5. Create emotional impact through the writing

Output in `=== File: {docs_dir}/03C_pivotal_scene.md ===`""")
        ]
    },
    
    {
        "phase_name": "Refinement & Completion",
        "system_prompt": """You are a literary editor with an eye for quality and consistency.
Your task is to review, refine, and complete the story development process.""",
        "user_prompt_template": """# Refinement & Completion Phase

## Concept:
{vision}

## Previous Development:
{previous_outputs}

## Your Task:
Refine the story elements and provide guidance for completing the novel.

Output your work in the following files:
""",
        "sub_steps": [
            SubStep("4A", "Story Analysis", """Analyze the story developed so far:
1. Evaluate strengths and potential weaknesses
2. Identify themes that could be further developed
3. Assess character arcs for completeness and impact
4. Review plot structure for pacing and logical progression
5. Suggest refinements to improve overall quality

Output in `=== File: {docs_dir}/04A_story_analysis.md ===`"""),
            
            SubStep("4B", "Writing Plan", """Create a detailed writing plan:
1. Develop a chapter-by-chapter writing schedule
2. Identify research needs for specific sections
3. Provide guidance for maintaining consistency
4. Suggest approaches for difficult sections
5. Create a revision strategy for after the first draft

Output in `=== File: {docs_dir}/04B_writing_plan.md ===`"""),
            
            SubStep("4C", "Executive Summary", """Create a comprehensive summary of the book project:
1. Write a complete synopsis (2-3 pages)
2. Summarize main characters and their arcs
3. Outline the central themes and how they're explored
4. Create a potential back-cover blurb
5. Develop a pitch for the book that could be presented to publishers

Output in `=== File: {docs_dir}/04C_executive_summary.md ===`""")
        ]
    }
] 