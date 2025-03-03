#!/usr/bin/env python3

"""
deep_research.py

An AI-powered deep research system that:
1) Conducts thorough, systematic research on a given topic
2) Walks through a structured 8-step research process
3) Breaks each step into detailed substeps for comprehensive analysis
4) Compiles all findings into a final research report
5) Generates auxiliary materials like bibliographies and visuals

This system walks an LLM through a rigorous academic research process
to produce in-depth findings on any topic.
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import time
import subprocess
import datetime

# Try to load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("python-dotenv not installed. Environment variables must be set manually.")

from ai_clients import AIOrchestrator
from utils import ProjectFile, SubStep, read_project_files, write_project_file, parse_ai_response_and_apply

# Project directory where all files will be created
PROJECT_DIR = "research_output"

# Define the research steps with substeps
RESEARCH_STEPS = [
    {
        "phase_name": "Research Question Definition",
        "system_prompt": """You are an expert research scientist and methodologist with extensive experience in formulating precise, impactful research questions.
Your task is to help define a clear, focused, and significant research question based on the user's topic of interest.""",
        "user_prompt_template": """# Research Question Definition Phase

## Research Topic:
{vision}

## Your Task:
Develop a comprehensive research question framework for this topic.

Output your work in the following files:
""",
        "sub_steps": [
            SubStep(
                "1A", 
                "Topic Analysis & Background", 
                """Analyze the given research topic and provide a thorough background:
1. Define the broader field and domain
2. Explain the historical context and development of this area
3. Identify key concepts, terminology, and frameworks
4. Discuss the significance and relevance of this topic
5. Note any recent developments or current trends

Output this analysis in `=== File: research/01A_topic_analysis.md ===`"""
            ),
            SubStep(
                "1B", 
                "Research Gap Identification", 
                """Identify and analyze research gaps in the topic area:
1. Review what is currently known about the topic
2. Identify limitations in existing knowledge or methodologies
3. Highlight contradictions or inconsistencies in current understanding
4. Discuss opportunities for meaningful contribution
5. Explain why addressing these gaps matters

Output this gap analysis in `=== File: research/01B_research_gaps.md ===`"""
            ),
            SubStep(
                "1C", 
                "Research Question Formulation", 
                """Formulate precise research questions:
1. Develop 1 primary research question that addresses a significant gap
2. Develop 3-5 secondary questions that support the main question
3. Ensure questions are clear, focused, and answerable
4. Explain the relationship between questions
5. Discuss how these questions advance knowledge in the field

Output the research questions in `=== File: research/01C_research_questions.md ===`"""
            )
        ]
    },
    {
        "phase_name": "Literature Review",
        "system_prompt": """You are an expert academic researcher with extensive experience conducting comprehensive literature reviews.
Your task is to simulate a thorough literature review on the research topic and questions.""",
        "user_prompt_template": """# Literature Review Phase

## Research Topic:
{vision}

## Primary Research Question:
{step1}

## Your Task:
Conduct a comprehensive literature review relevant to the research questions.

Output your work in the following files:
""",
        "sub_steps": [
            SubStep(
                "2A", 
                "Core Literature Identification", 
                """Identify and analyze key literature in the field:
1. List at least 15-20 seminal works (books, papers, studies) most relevant to the research questions
2. For each work, provide full citation, brief summary, and relevance to the research
3. Group works by themes or approaches
4. Identify the most influential authors and institutions in this area
5. Note any landmark studies that changed understanding in the field

Output this core literature review in `=== File: research/02A_core_literature.md ===`"""
            ),
            SubStep(
                "2B", 
                "Theoretical Frameworks Analysis", 
                """Analyze theoretical frameworks relevant to the research:
1. Identify major theoretical perspectives used to examine this topic
2. Compare and contrast competing theoretical approaches
3. Discuss strengths and limitations of each theoretical framework
4. Analyze how different theories explain key phenomena in the research area
5. Recommend which theoretical framework(s) might be most appropriate for the research questions

Output this theoretical analysis in `=== File: research/02B_theoretical_frameworks.md ===`"""
            ),
            SubStep(
                "2C", 
                "Methodological Approaches Review", 
                """Review methodological approaches used in the field:
1. Identify major research methodologies employed in studying this topic
2. Analyze strengths and weaknesses of different methodological approaches
3. Discuss key research designs, data collection methods, and analytical techniques
4. Note any innovative or emerging methodologies being applied
5. Recommend methodological approaches that would best address the research questions

Output this methodological review in `=== File: research/02C_methodological_approaches.md ===`"""
            )
        ]
    },
    {
        "phase_name": "Research Design & Methodology",
        "system_prompt": """You are an expert research methodologist with extensive experience designing rigorous research studies.
Your task is to develop a comprehensive research design and methodology that will effectively address the research questions.""",
        "user_prompt_template": """# Research Design & Methodology Phase

## Research Questions:
{step1}

## Literature Review:
{step2}

## Your Task:
Design a comprehensive research methodology to address the research questions.

Output your work in the following files:
""",
        "sub_steps": [
            SubStep(
                "3A", 
                "Research Approach & Design", 
                """Develop the overall research approach and design:
1. Justify the chosen research paradigm (qualitative, quantitative, mixed methods)
2. Explain the specific research design (e.g., experimental, case study, ethnography)
3. Discuss ontological and epistemological assumptions underlying the approach
4. Address how the design aligns with research questions and theoretical framework
5. Outline the scope and boundaries of the research

Output this research design in `=== File: research/03A_research_design.md ===`"""
            ),
            SubStep(
                "3B", 
                "Data Collection Methods", 
                """Detail the data collection methods:
1. Specify data sources and types of data needed
2. Describe specific data collection techniques (e.g., surveys, interviews, observations)
3. Explain sampling strategy and sample size considerations
4. Address data quality, reliability, and validity concerns
5. Discuss ethical considerations in data collection

Output these data collection methods in `=== File: research/03B_data_collection.md ===`"""
            ),
            SubStep(
                "3C", 
                "Analytical Framework", 
                """Develop the analytical framework:
1. Describe data processing and preparation procedures
2. Explain analytical methods and techniques to be used
3. Justify statistical tests or qualitative analysis approaches
4. Address how analysis connects to research questions
5. Discuss how findings will be interpreted and evaluated

Output this analytical framework in `=== File: research/03C_analytical_framework.md ===`"""
            )
        ]
    },
    {
        "phase_name": "Data Analysis & Results",
        "system_prompt": """You are an expert data analyst and research scientist with extensive experience analyzing complex research data.
Your task is to simulate the data analysis process and present well-organized, insightful results from the research.""",
        "user_prompt_template": """# Data Analysis & Results Phase

## Research Questions:
{step1}

## Research Methodology:
{step3}

## Your Task:
Simulate the data analysis process and present comprehensive results.

Output your work in the following files:
""",
        "sub_steps": [
            SubStep(
                "4A", 
                "Simulated Data Description", 
                """Describe the simulated data for this research:
1. Outline the structure and characteristics of the dataset
2. Provide descriptive statistics or qualitative data overview
3. Discuss data quality, completeness, and any preprocessing steps
4. Include sample data visualizations where appropriate
5. Address any limitations or biases in the simulated data

Output this data description in `=== File: research/04A_data_description.md ===`"""
            ),
            SubStep(
                "4B", 
                "Analysis Process & Initial Findings", 
                """Document the analysis process and initial findings:
1. Walk through the step-by-step analytical process
2. Present initial findings organized by research question or theme
3. Include appropriate statistical results or thematic analysis outcomes
4. Display key results using tables, charts, or excerpts
5. Note unexpected patterns or results that emerged during analysis

Output this analysis process in `=== File: research/04B_analysis_process.md ===`"""
            ),
            SubStep(
                "4C", 
                "Synthesized Results", 
                """Synthesize and interpret the comprehensive results:
1. Present fully integrated results addressing each research question
2. Connect findings to theoretical frameworks identified earlier
3. Highlight patterns, trends, and relationships in the data
4. Discuss how results confirm or challenge existing knowledge
5. Address the strength of evidence for each major finding

Output these synthesized results in `=== File: research/04C_synthesized_results.md ===`"""
            )
        ]
    },
    {
        "phase_name": "Discussion & Interpretation",
        "system_prompt": """You are an expert research scientist with extensive experience interpreting complex research findings.
Your task is to provide insightful discussion and interpretation of the research results.""",
        "user_prompt_template": """# Discussion & Interpretation Phase

## Research Questions:
{step1}

## Key Results:
{step4}

## Your Task:
Provide comprehensive discussion and interpretation of the research findings.

Output your work in the following files:
""",
        "sub_steps": [
            SubStep(
                "5A", 
                "Findings Interpretation", 
                """Provide detailed interpretation of findings:
1. Interpret each major finding in context of existing literature
2. Explain unexpected or contradictory results
3. Discuss how findings relate to theoretical frameworks
4. Analyze patterns or themes that emerged across multiple findings
5. Address alternative explanations for key results

Output this interpretation in `=== File: research/05A_findings_interpretation.md ===`"""
            ),
            SubStep(
                "5B", 
                "Research Questions Addressed", 
                """Explicitly address how findings answer research questions:
1. Revisit each research question individually
2. Summarize evidence that addresses each question
3. Discuss the extent to which questions have been answered
4. Address any aspects of questions that remain unresolved
5. Highlight any new questions that emerged from the findings

Output this research question analysis in `=== File: research/05B_questions_addressed.md ===`"""
            ),
            SubStep(
                "5C", 
                "Theoretical & Practical Implications", 
                """Discuss theoretical and practical implications:
1. Explain how findings contribute to theoretical understanding
2. Discuss any challenges to existing theories
3. Address practical applications of the research
4. Identify stakeholders who might benefit from the findings
5. Suggest specific ways findings could influence practice or policy

Output these implications in `=== File: research/05C_implications.md ===`"""
            )
        ]
    },
    {
        "phase_name": "Limitations & Future Research",
        "system_prompt": """You are an expert research methodologist with extensive experience evaluating research limitations and identifying productive directions for future inquiry.
Your task is to critically assess limitations of the current research and outline promising directions for future studies.""",
        "user_prompt_template": """# Limitations & Future Research Phase

## Research Design:
{step3}

## Research Results:
{step4}

## Discussion:
{step5}

## Your Task:
Critically assess limitations and identify promising directions for future research.

Output your work in the following files:
""",
        "sub_steps": [
            SubStep(
                "6A", 
                "Methodological Limitations", 
                """Analyze methodological limitations:
1. Identify limitations in research design and methodology
2. Discuss constraints in data collection and analysis
3. Address issues related to sample size, selection, or representativeness
4. Consider limitations in measurement tools or approaches
5. Explain how these limitations might impact the findings

Output this limitations analysis in `=== File: research/06A_methodological_limitations.md ===`"""
            ),
            SubStep(
                "6B", 
                "Conceptual & Contextual Limitations", 
                """Assess conceptual and contextual limitations:
1. Discuss limitations in the theoretical framework applied
2. Address boundary conditions and scope restrictions
3. Consider contextual factors that might limit generalizability
4. Identify assumptions that might affect interpretation
5. Discuss any ethical considerations or constraints

Output this conceptual limitations analysis in `=== File: research/06B_conceptual_limitations.md ===`"""
            ),
            SubStep(
                "6C", 
                "Future Research Directions", 
                """Outline promising future research directions:
1. Suggest specific follow-up studies to address limitations
2. Identify new research questions that emerged
3. Recommend methodological innovations for future research
4. Suggest theoretical directions for extending the work
5. Outline a comprehensive research agenda building on current findings

Output these future directions in `=== File: research/06C_future_directions.md ===`"""
            )
        ]
    },
    {
        "phase_name": "Conclusions & Recommendations",
        "system_prompt": """You are an expert research scientist with extensive experience synthesizing research findings into concise, impactful conclusions.
Your task is to provide clear, substantive conclusions and actionable recommendations based on the research.""",
        "user_prompt_template": """# Conclusions & Recommendations Phase

## Research Questions:
{step1}

## Key Findings:
{step4}

## Discussion:
{step5}

## Limitations:
{step6}

## Your Task:
Develop comprehensive conclusions and recommendations based on the research.

Output your work in the following files:
""",
        "sub_steps": [
            SubStep(
                "7A", 
                "Key Conclusions", 
                """Synthesize key research conclusions:
1. Present major conclusions organized by research questions or themes
2. Summarize the most significant findings and their meaning
3. Connect conclusions to the broader field and existing knowledge
4. Highlight unexpected or novel conclusions
5. Discuss the strength and reliability of each conclusion

Output these conclusions in `=== File: research/07A_key_conclusions.md ===`"""
            ),
            SubStep(
                "7B", 
                "Practical Recommendations", 
                """Provide practical recommendations:
1. Offer specific, actionable recommendations for practitioners
2. Address how different stakeholders might apply findings
3. Develop recommendations for policy or decision-makers
4. Suggest frameworks for implementing recommendations
5. Discuss potential challenges in adopting recommendations

Output these recommendations in `=== File: research/07B_practical_recommendations.md ===`"""
            ),
            SubStep(
                "7C", 
                "Research Contribution Summary", 
                """Summarize research contributions:
1. Articulate the primary contributions to knowledge
2. Explain how the research advances theoretical understanding
3. Describe methodological innovations or applications
4. Discuss the significance of the research in the broader field
5. Address potential for long-term impact of the research

Output this contribution summary in `=== File: research/07C_research_contributions.md ===`"""
            )
        ]
    },
    {
        "phase_name": "Research Compilation & Presentation",
        "system_prompt": """You are an expert research communicator with extensive experience compiling complex research into accessible, compelling formats.
Your task is to create polished research deliverables that effectively communicate the entire research process and findings.""",
        "user_prompt_template": """# Research Compilation & Presentation Phase

## All Previous Research Phases:
{step1}
{step2}
{step3}
{step4}
{step5}
{step6}
{step7}

## Your Task:
Create comprehensive research deliverables that synthesize and present the entire research process and findings.

Output your work in the following files:
""",
        "sub_steps": [
            SubStep(
                "8A", 
                "Executive Summary", 
                """Create a concise executive summary:
1. Summarize the entire research in 2-3 pages
2. Cover problem statement, methodology, key findings, and implications
3. Highlight most significant conclusions and recommendations
4. Make the summary accessible to non-specialist audiences
5. Emphasize practical applications and value of the research

Output this executive summary in `=== File: research/08A_executive_summary.md ===`"""
            ),
            SubStep(
                "8B", 
                "Comprehensive Research Report", 
                """Compile a comprehensive research report:
1. Create a complete academic research report with proper structure
2. Include abstract, introduction, literature review, methodology, results, discussion, and conclusion
3. Incorporate visual elements (tables, charts, diagrams)
4. Use appropriate academic formatting and citation style
5. Ensure logical flow and coherence throughout the document

Output this comprehensive report in `=== File: research/08B_comprehensive_report.md ===`"""
            ),
            SubStep(
                "8C", 
                "Research Artifacts", 
                """Develop supporting research artifacts:
1. Create a bibliography of all sources referenced
2. Develop a glossary of key terms and concepts
3. Generate sample visualizations to illustrate key findings
4. Outline any research instruments or protocols developed
5. Create a timeline or roadmap for implementation of recommendations

Output these research artifacts in `=== File: research/08C_research_artifacts.md ===`"""
            ),
            SubStep(
                "8D", 
                "Final Research Findings", 
                """Synthesize a final research findings document:
1. Compile the most important insights from all research phases
2. Organize findings in a logical, coherent structure
3. Include primary evidence supporting each major finding
4. Connect findings to their practical applications
5. Make the document accessible while maintaining academic rigor

Output this final research findings document in `=== File: research/08D_final_research_findings.md ===`"""
            )
        ]
    }
]

def execute_substep(orchestrator: AIOrchestrator, step_info: dict, step_index: int, 
                   sub_step_index: int, sub_step: SubStep, file_map: Dict[str, ProjectFile], 
                   step_outputs: Dict[int, str], sub_step_outputs: Dict[str, str]) -> bool:
    """
    Execute a single substep in the research process.
    
    Args:
        orchestrator: The AI client to use
        step_info: Information about the current step
        step_index: The 1-indexed step number
        sub_step_index: The 0-indexed substep number
        sub_step: The SubStep object containing the prompt
        file_map: Dictionary mapping file paths to their contents
        step_outputs: Dictionary storing outputs from previous main steps
        sub_step_outputs: Dictionary storing outputs from previous substeps
        
    Returns:
        bool: True if successful, False otherwise
    """
    phase_name = step_info["phase_name"]
    system_prompt = step_info["system_prompt"]
    sub_step_name = sub_step.name
    sub_step_id = sub_step.id
    
    # Build the user prompt
    user_prompt = f"# {phase_name}: {sub_step_name}\n\n"
    
    # Add vision if it's the first step
    if step_index == 1 and sub_step_index == 0:
        user_prompt += f"## Research Topic:\n{step_outputs.get('vision', '(No vision provided)')}\n\n"
    
    # Add previous step outputs for context
    for i in range(1, step_index):
        if i in step_outputs:
            user_prompt += f"## Previous Step {i} Output:\n{step_outputs[i][:1000]}...\n\n"
    
    # If we're beyond first substep of current step, include previous substep outputs
    if sub_step_index > 0:
        user_prompt += "## Previous Substeps in Current Phase:\n"
        for i in range(sub_step_index):
            prev_sub_step = step_info["sub_steps"][i]
            sub_step_key = f"step{step_index}_sub{i+1}"
            prev_output = sub_step_outputs.get(sub_step_key, "(No output)")
            user_prompt += f"### Substep {prev_sub_step.id} ({prev_sub_step.name}):\n{prev_output[:500]}...\n\n"
    
    # Add specific instructions for this substep
    user_prompt += f"## Your Task for Substep {sub_step_id}:\n{sub_step.prompt}\n\n"
    
    # Show step information
    print(f"\n=== {phase_name}: {sub_step_name} (Step {step_index}, Substep {sub_step_id}) ===")
    
    # Confirm with user
    proceed = input(f"Proceed with this substep? (y/n/q): ").strip().lower()
    if proceed == 'q':
        print("Exiting.")
        sys.exit(0)
    elif proceed != 'y':
        print(f"Skipping {sub_step_name}.")
        return False
    
    # Call the LLM
    ai_response = orchestrator.call_llm(system_prompt, user_prompt, max_tokens=64000, temperature=0.3)
    
    # Process the AI response
    print("\nAI Response generated. Processing output...")
    parse_ai_response_and_apply(ai_response, file_map)
    
    # Store the raw AI response in the substep outputs
    sub_step_key = f"step{step_index}_sub{sub_step_index+1}"
    sub_step_outputs[sub_step_key] = ai_response
    
    # Write files to disk
    for rel_path, pf in file_map.items():
        write_project_file(PROJECT_DIR, pf)
    
    return True

def compile_step_outputs(step_index: int, step_info: dict, sub_step_outputs: Dict[str, str]) -> str:
    """
    Compile outputs from all substeps for a given step.
    
    Args:
        step_index: The 1-indexed step number
        step_info: Information about the step
        sub_step_outputs: Dictionary storing outputs from substeps
        
    Returns:
        str: Compiled output for the step
    """
    phase_name = step_info["phase_name"]
    compiled_content = f"# {phase_name}\n\n"
    
    # Add each substep's output
    for i, sub_step in enumerate(step_info["sub_steps"], start=1):
        sub_step_key = f"step{step_index}_sub{i}"
        sub_step_output = sub_step_outputs.get(sub_step_key, "")
        
        # Extract just the content part (not the file markers)
        content_lines = []
        capture = False
        for line in sub_step_output.splitlines():
            if line.startswith("=== File:"):
                capture = True
                continue
            if capture:
                content_lines.append(line)
        
        substep_content = "\n".join(content_lines)
        compiled_content += f"## {sub_step.id}. {sub_step.name}\n\n{substep_content}\n\n"
    
    return compiled_content

def generate_final_research_findings(file_map: Dict[str, ProjectFile], step_outputs: Dict[int, str]):
    """
    Generate a final research findings document that synthesizes all research steps.
    
    Args:
        file_map: Dictionary mapping file paths to their contents
        step_outputs: Dictionary storing outputs from each step
    """
    print("\n=== Generating Final Research Findings ===")
    
    # Create the final document
    now = datetime.datetime.now().strftime("%Y-%m-%d")
    final_doc = f"""# Comprehensive Research Findings
# Date: {now}

## Research Overview

"""
    
    # Add executive summary if it exists
    if "research/08A_executive_summary.md" in file_map:
        final_doc += "## Executive Summary\n\n"
        final_doc += file_map["research/08A_executive_summary.md"].content + "\n\n"
    
    # Add final research findings if they exist
    if "research/08D_final_research_findings.md" in file_map:
        final_doc += "## Final Research Findings\n\n"
        final_doc += file_map["research/08D_final_research_findings.md"].content + "\n\n"
    
    # Add key conclusions if they exist
    if "research/07A_key_conclusions.md" in file_map:
        final_doc += "## Key Conclusions\n\n"
        final_doc += file_map["research/07A_key_conclusions.md"].content + "\n\n"
    
    # Add practical recommendations if they exist
    if "research/07B_practical_recommendations.md" in file_map:
        final_doc += "## Practical Recommendations\n\n"
        final_doc += file_map["research/07B_practical_recommendations.md"].content + "\n\n"
    
    # Create navigation section with links to all research files
    final_doc += "## Research Navigation\n\n"
    final_doc += "This section provides links to all detailed research components.\n\n"
    
    for i, step in enumerate(RESEARCH_STEPS, start=1):
        final_doc += f"### {i}. {step['phase_name']}\n\n"
        for sub_step in step["sub_steps"]:
            file_key = f"research/{i:02d}{sub_step.id}_{sub_step.name.lower().replace(' ', '_')}.md"
            final_doc += f"- [{sub_step.id}. {sub_step.name}](/{file_key})\n"
        final_doc += "\n"
    
    # Save the final document
    file_map["RESEARCH_FINDINGS.md"] = ProjectFile("RESEARCH_FINDINGS.md", final_doc)
    write_project_file(PROJECT_DIR, file_map["RESEARCH_FINDINGS.md"])
    
    print("Final research findings document generated: RESEARCH_FINDINGS.md")

def run_deep_research(vision: str, model_name: str):
    """
    Run the main deep research workflow.
    
    Args:
        vision: The user's research topic
        model_name: The model to use (claude37sonnet or deepseekr1)
    """
    print(f"\n=== Starting Deep Research with {model_name} ===")
    print(f"Research topic: {vision[:100]}...")
    
    # Initialize the orchestrator
    orchestrator = AIOrchestrator(model_name)
    
    # Create storage
    file_map = {}  # Stores file contents
    step_outputs = {'vision': vision}  # Stores raw outputs from each step
    sub_step_outputs = {}  # Stores raw outputs from each substep
    
    # Create project directory
    project_dir = Path(PROJECT_DIR)
    if not project_dir.exists():
        project_dir.mkdir(parents=True)
        print(f"Created project directory: {project_dir}")
    
    # Create research directory
    research_dir = project_dir / "research"
    if not research_dir.exists():
        research_dir.mkdir(parents=True)
        print(f"Created research directory: {research_dir}")
    
    # Execute each step with its substeps
    for i, step in enumerate(RESEARCH_STEPS, start=1):
        phase_name = step["phase_name"]
        print(f"\n=== Step {i}: {phase_name} ===")
        
        # Execute each substep
        if "sub_steps" not in step:
            print(f"Warning: Step {i} ({phase_name}) does not have sub_steps defined. Skipping.")
            continue
            
        for j, sub_step in enumerate(step["sub_steps"]):
            success = execute_substep(
                orchestrator, 
                step, 
                i, 
                j, 
                sub_step, 
                file_map, 
                step_outputs, 
                sub_step_outputs
            )
            
            if not success:
                print(f"Skipped substep {sub_step.id}: {sub_step.name}")
                continue
        
        # Compile substep outputs for this step
        step_output = compile_step_outputs(i, step, sub_step_outputs)
        step_outputs[i] = step_output
        
        # Create a combined file for this step
        step_file = f"research/STEP{i:02d}_{phase_name.replace(' ', '_').upper()}.md"
        file_map[step_file] = ProjectFile(step_file, step_output)
        write_project_file(PROJECT_DIR, file_map[step_file])
        print(f"Created combined file for Step {i}: {step_file}")
    
    # Generate final research findings document
    generate_final_research_findings(file_map, step_outputs)
    
    print("\n=== Deep Research Complete ===")
    print(f"Your research output has been generated in the '{PROJECT_DIR}' directory.")
    print("You can find the comprehensive research findings in RESEARCH_FINDINGS.md")
    print("Detailed research files are available in the 'research' subdirectory.")

def main():
    parser = argparse.ArgumentParser(description="Conduct deep, systematic research on any topic")
    parser.add_argument('model', choices=['claude37sonnet', 'deepseekr1'], 
                      help='Which LLM to use (claude37sonnet or deepseekr1)')
    parser.add_argument('topic', nargs='?', default=None, 
                      help='Research topic to investigate')
    
    args = parser.parse_args()
    
    model_name = args.model.lower()
    research_topic = args.topic
    
    # Check if research topic was provided as a command line argument
    if not research_topic:
        # Check for user_prompt.txt
        prompt_file_path = "user_prompt.txt"
        if os.path.exists(prompt_file_path):
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
                    
                    use_file = input("Use this content as research topic? (y/n): ").strip().lower()
                    if use_file == 'y':
                        research_topic = file_content
            except Exception as e:
                print(f"Error reading user_prompt.txt: {e}")
    
    # If still no research topic, prompt the user
    if not research_topic:
        print("\nPlease describe the research topic you want to investigate:")
        print("(Enter your complete research topic, finish with Ctrl+D on Unix or Ctrl+Z followed by Enter on Windows)")
        
        lines = []
        try:
            while True:
                line = input()
                lines.append(line)
        except EOFError:
            # End of input
            pass
        
        research_topic = "\n".join(lines)
    
    # Ensure we have a research topic
    if not research_topic or research_topic.strip() == "":
        print("Error: No research topic provided.")
        sys.exit(1)
    
    # Run the deep research
    run_deep_research(research_topic, model_name)

if __name__ == "__main__":
    main()
