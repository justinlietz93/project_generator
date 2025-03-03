#!/usr/bin/env python3

"""
prompt_generator.py

A tool that uses an LLM to generate comprehensive, structured prompts from simple user inputs.
The generated prompts are saved to user_prompt.txt and can be used for project generation.

Usage:
  python prompt_generator.py [--model MODEL_NAME]

Where:
  --model: Optional model to use (claude37sonnet, deepseekr1, gemini2pro)
           Defaults to claude37sonnet if not specified
"""

import os
import sys
import argparse
from typing import Optional
import textwrap

# Import the AIOrchestrator from ai_clients
from ai_clients import AIOrchestrator

def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def get_multiline_input(prompt: str) -> str:
    """Get multiline input from the user with instructions on how to finish."""
    print(f"\n{prompt}")
    print("(Type your input over multiple lines. When finished, enter 'DONE' on a new line)")
    
    lines = []
    while True:
        try:
            line = input()
            if line.strip().upper() == "DONE":
                break
            lines.append(line)
        except EOFError:
            break
    
    return "\n".join(lines)

def generate_prompt(user_input: str, user_preferences: Optional[str], orchestrator: AIOrchestrator) -> str:
    """
    Use the LLM to generate a structured prompt based on user input.
    
    Args:
        user_input: The basic idea or request from the user
        user_preferences: Optional additional details about format, style, etc.
        orchestrator: The AIOrchestrator instance for LLM access
        
    Returns:
        str: The generated structured prompt
    """
    # Compose system prompt to instruct the LLM
    system_prompt = """You are an expert prompt engineer who creates comprehensive, detailed prompts 
for AI systems to generate projects or solutions. Your task is to take a user's basic idea and expand 
it into a well-structured, detailed prompt that would guide an AI to create exactly what the user needs.

Your generated prompts should:
1. Have a clear, hierarchical structure with sections and subsections
2. Include specific requirements and constraints
3. Break down complex aspects into clear bullet points
4. Provide context and background where needed
5. Set clear expectations for deliverables
6. Use precise, unambiguous language
7. Be comprehensive enough to guide project implementation

The output should ONLY contain the prompt text, with no explanations, introductions, or meta-commentary.
Create the prompt as if it were going to be directly submitted to an AI system."""

    # Compose user prompt to guide the LLM
    base_user_prompt = f"""Please create a comprehensive, detailed prompt based on this basic idea:

{user_input}

"""
    
    # Add user preferences if provided
    if user_preferences and user_preferences.strip():
        base_user_prompt += f"""
Please consider these additional preferences/requirements:

{user_preferences}
"""

    # Call the LLM
    print("\nGenerating structured prompt...\n")
    generated_prompt = orchestrator.call_llm(
        system_prompt=system_prompt,
        user_prompt=base_user_prompt,
        max_tokens=64000,  # Limiting token count for prompt generation
        temperature=0.7   # Slight creativity for prompt structure
    )
    
    return generated_prompt

def save_to_file(content: str, filename: str = "user_prompt.txt") -> None:
    """Save content to a file."""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"\n✅ Prompt successfully saved to {filename}")
    except Exception as e:
        print(f"\n❌ Error saving to {filename}: {str(e)}")

def main():
    """Main function to run the prompt generator."""
    parser = argparse.ArgumentParser(description="Generate structured prompts using an LLM")
    parser.add_argument('--model', type=str, default='claude37sonnet',
                      help="Model to use (claude37sonnet, deepseekr1, gemini2pro)")
    
    args = parser.parse_args()
    
    # Initialize the orchestrator with the specified model
    try:
        orchestrator = AIOrchestrator(args.model)
    except ValueError as e:
        print(f"Error: {str(e)}")
        print("Available models: claude37sonnet, deepseekr1, gemini2pro")
        sys.exit(1)
    except Exception as e:
        print(f"Error initializing AI client: {str(e)}")
        sys.exit(1)
    
    clear_screen()
    print("=" * 80)
    print("📝 PROMPT GENERATOR".center(80))
    print("=" * 80)
    print("\nThis tool will help you create structured, detailed prompts for AI project generation.")
    print("Your simple idea will be expanded into a comprehensive prompt saved to user_prompt.txt")
    
    # Get the basic idea from the user
    user_input = get_multiline_input("What would you like to create? (Describe your basic idea or request)")
    
    if not user_input.strip():
        print("No input provided. Exiting.")
        return
    
    # Get optional preferences
    print("\n" + "-" * 80)
    print("Optional: Provide any specific preferences for the prompt structure, style, or content.")
    print("This could include format requirements, specific sections to include, level of detail, etc.")
    user_preferences = get_multiline_input("Additional preferences (optional, press DONE to skip)")
    
    # Generate the prompt
    generated_prompt = generate_prompt(user_input, user_preferences, orchestrator)
    
    # Display the generated prompt
    clear_screen()
    print("=" * 80)
    print("GENERATED PROMPT".center(80))
    print("=" * 80)
    print("\n" + generated_prompt + "\n")
    
    # Ask if the user wants to save it
    save_choice = input("\nSave this prompt to user_prompt.txt? (y/n): ").strip().lower()
    if save_choice == 'y':
        save_to_file(generated_prompt)
    else:
        print("\nPrompt not saved.")

if __name__ == "__main__":
    main()
