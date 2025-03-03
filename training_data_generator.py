#!/usr/bin/env python3

"""
synthetic_data_generator.py

Generates "thought-action" (or chain-of-thought style) training data from
existing text pairs (like question->answer) using a smaller local LLM.

We define:
1. A local inference call (to an ollama or Hugging Face pipeline)
2. A multi-step approach that transforms each (question, answer) into
   'thought' (internal reasoning) + 'action' (final steps) records
3. Output is a JSON lines or JSON file with the new training data
4. Minimal disclaimers. The model is instructed to produce a full chain-of-thought
   with minimal self-limitations.

Usage:
  python synthetic_data_generator.py --input data.json --output out.json \
     --model-or-engine "path_or_alias_of_llm" [--use-ollama or --huggingface]

Example:
  python synthetic_data_generator.py --input existing_QA.json --output thought_action.json \
     --model-or-engine "llama2-13b" --use-ollama

Note:
 - This script can be adapted to any local inference method you prefer.
 - Ensure your local model can handle the multi-step chain-of-thought prompts effectively.
"""

import argparse
import json
import sys
import os
from typing import Dict, Any
import subprocess
import shlex

def call_ollama_local_model(model_name: str, prompt: str) -> str:
    """
    Calls a local Ollama instance to generate a response from a given model.

    model_name: e.g., "llama2-13b-q4_0"
    prompt: The text prompt to send to Ollama.

    Requirements:
      - Ollama installed on macOS.
      - The 'ollama' CLI is in PATH.
      - The model is either a local file or a known reference by name.

    Example usage:
      response = call_ollama_local_model("llama2-13b-q4_0", "Hello, how are you?")
    """

    # Escape the prompt for shell usage:
    # A safe approach is to rely on Python's ability to handle arguments by using a list
    # with no additional shell expansions.
    # We'll do:
    #   ollama -m {model_name} -p {prompt}
    # with no shell = True to avoid injection.
    # If your prompt is large, consider writing prompt to a temp file instead.

    command = ["ollama", "-m", model_name, "-p", prompt]

    try:
        # Run ollama, capturing stdout
        result = subprocess.run(
            command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        output_text = result.stdout
        # The output might contain some extra formatting or JSON, depending on your Ollama version/config.
        # For a typical usage, we assume the raw text is the answer we need.
        return output_text.strip()

    except subprocess.CalledProcessError as e:
        # If Ollama returns non-zero exit code or there's an error
        print(f"Error calling Ollama model '{model_name}': {e}\nstderr:\n{e.stderr}")
        return f"[Error from ollama: {e.stderr}]"

    except FileNotFoundError:
        # If 'ollama' is not found
        print("Error: 'ollama' CLI not found. Ensure Ollama is installed and in your PATH.")
        return "[Error: ollama CLI not found]"


def call_huggingface_model(model_name: str, prompt: str) -> str:
    """
    Example function that calls a local HF pipeline (transformers).
    You need to load the pipeline once. We'll do a simple approach: 
    pipeline(prompt, max_new_tokens=some_value).
    """
    from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
    # (In production, you'd load model once outside this function for efficiency)
    try:
        hg_tokenizer = AutoTokenizer.from_pretrained(model_name)
        hg_model = AutoModelForCausalLM.from_pretrained(model_name, device_map="auto")
        generator = pipeline("text-generation", model=hg_model, tokenizer=hg_tokenizer)
        response = generator(prompt, max_new_tokens=256, do_sample=True, temperature=0.7)
        # We'll assume the pipeline returns a list of dicts with 'generated_text'
        text_out = response[0]['generated_text']
        return text_out
    except Exception as e:
        print(f"Error calling HF model: {e}")
        return "Mock fallback response"

def multi_step_thought_action_transform(text: str, local_inference_func) -> Dict[str, str]:
    """
    Given a single chunk of text (e.g. question+answer),
    do a multi-step approach to yield:
      - 'thought': chain-of-thought or internal reasoning
      - 'action': final steps or succinct final answer
    We'll produce a dictionary with { 'thought': ..., 'action': ... }.

    We can do multiple small prompts, or a single prompt with "step by step".
    Here, we do multiple small prompts for clarity.
    """

    # 1) Summarize context
    prompt_a = f"""You have this text:
\"\"\"{text}\"\"\"

First, step A: Summarize the question & answer into a short context. 
No disclaimers. Just a short 2-3 line summary.
"""
    summary = local_inference_func(prompt_a)

    # 2) Generate hidden reasoning
    prompt_b = f"""Given the short summary:
\"\"\"{summary}\"\"\"

Step B: produce a hidden 'Thought' that explains the logical chain-of-thought 
leading from question to answer. 
Use short bullet points or a short paragraph. 
No disclaimers.
"""
    thought = local_inference_func(prompt_b)

    # 3) Generate final action or official answer
    prompt_c = f"""We have the summary:
\"\"\"{summary}\"\"\"

And the hidden 'Thought':
\"\"\"{thought}\"\"\"

Step C: now produce an 'Action' section: 
the final official answer or solution steps, 
in a concise, direct style. 
No disclaimers.
"""
    action = local_inference_func(prompt_c)

    return {
        "original_text": text,
        "summary": summary.strip(),
        "thought": thought.strip(),
        "action": action.strip()
    }

def main():
    parser = argparse.ArgumentParser(description="Generate 'thought-action' training data using a local LLM.")
    parser.add_argument("--input", type=str, required=True, help="Path to input JSON file (with Q/A or similar).")
    parser.add_argument("--output", type=str, required=True, help="Output JSON file to store synthetic data.")
    parser.add_argument("--model-or-engine", type=str, required=True,
                        help="Name of local model or engine reference. E.g., 'llama2-13b'.")
    parser.add_argument("--use-ollama", action="store_true", help="Use local ollama approach.")
    parser.add_argument("--huggingface", action="store_true", help="Use local huggingface pipeline.")
    
    args = parser.parse_args()

    # Validate
    if not os.path.exists(args.input):
        print(f"Error: input file {args.input} not found.")
        sys.exit(1)
    
    # Choose which local inference function to use
    if args.use_ollama:
        def local_inference_func(prompt: str):
            return call_ollama_local_model(args.model_or_engine, prompt)
    elif args.huggingface:
        def local_inference_func(prompt: str):
            return call_huggingface_model(args.model_or_engine, prompt)
    else:
        print("No local method specified (--use-ollama or --huggingface). Using a mock fallback.")
        def local_inference_func(prompt: str):
            return "This is a mock fallback response."
    
    # Load input data
    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)  # assume list of objects: e.g. [{"question": "x", "answer":"y"}, ...]

    # Transform
    output_list = []
    for i, item in enumerate(data):
        # Build the text
        # You can adapt based on your data schema. E.g. question+answer or problem+solution
        text_to_transform = ""
        if "question" in item and "answer" in item:
            text_to_transform = f"Q: {item['question']}\nA: {item['answer']}"
        else:
            # fallback
            text_to_transform = json.dumps(item)

        record = multi_step_thought_action_transform(text_to_transform, local_inference_func)
        output_list.append(record)
        print(f"[{i+1}/{len(data)}] Processed. 'thought' length ~ {len(record['thought'])} chars, 'action' length ~ {len(record['action'])} chars.")

    # Save
    with open(args.output, "w", encoding="utf-8") as out_f:
        json.dump(output_list, out_f, indent=2)

    print(f"\nDone. Generated {len(output_list)} records with thought+action in {args.output}")

if __name__ == "__main__":
    main()
