"""
ai_clients.py

Minimal approach to calling:
1) Claude 3.7 Sonnet (Anthropic-based)
2) DeepSeek R1 (OpenAI-based approach)
3) Gemini 2.0 Pro Experimental (Google AI)
4) Ollama models (locally or remotely hosted)

"""

import os
from pathlib import Path
import requests
import json

# Ensure clean environment loading
try:
    from dotenv import load_dotenv, find_dotenv
    
    # Clear any existing API keys
    for key in ['ANTHROPIC_API_KEY', 'DEEPSEEK_API_KEY', 'GEMINI_API_KEY', 'OLLAMA_HOST']:
        if key in os.environ:
            del os.environ[key]
    
    # Find and load .env file
    env_path = find_dotenv()
    if env_path:
        print(f"Loading environment from: {env_path}")
        load_dotenv(env_path, override=True)
        
        # Verify keys are loaded
        if 'ANTHROPIC_API_KEY' in os.environ:
            key = os.environ['ANTHROPIC_API_KEY']
            print(f"Loaded Anthropic key: {key[:10]}...{key[-4:]}")
        if 'DEEPSEEK_API_KEY' in os.environ:
            key = os.environ['DEEPSEEK_API_KEY']
            print(f"Loaded DeepSeek key: {key[:10]}...{key[-4:]}")
        if 'GEMINI_API_KEY' in os.environ:
            key = os.environ['GEMINI_API_KEY']
            print(f"Loaded Gemini key: {key[:10]}...{key[-4:]}")
        if 'OLLAMA_HOST' in os.environ:
            host = os.environ['OLLAMA_HOST']
            print(f"Using Ollama host: {host}")
    else:
        print("No .env file found")
except ImportError:
    raise ImportError("python-dotenv is required. Please install it with: pip install python-dotenv")

import anthropic
import openai
try:
    import google.generativeai as genai
    HAS_GEMINI = True
except ImportError:
    print("Warning: google-generativeai not installed. To use Gemini models, install with: pip install google-generativeai")
    HAS_GEMINI = False

class Claude37SonnetClient:
    """
    Minimal client for Claude 3.7 Sonnet. 
    Uses environment variables:
      - ANTHROPIC_API_KEY: The key for Anthropic
      - CLAUDE_MODEL (optional, default "claude-3-7-sonnet-20250219")
    """

    def __init__(self):
        self.api_key = os.environ.get("ANTHROPIC_API_KEY", "missing-api-key")
        self.model_name = os.environ.get("CLAUDE_MODEL", "claude-3-7-sonnet-20250219")
        self.client = anthropic.Anthropic(api_key=self.api_key)

    def run(self, messages, max_tokens=64000, temperature=0.2, enable_thinking=False, thinking_budget=None):
        """
        Call to the Claude 3.7 Sonnet model with automatic streaming for large token counts.
        :param messages: list of { "role": "user"/"assistant"/"system", "content": "..."}
        :param max_tokens: limit for the generated text
        :param temperature: Controls randomness (0.0 to 1.0)
        :param enable_thinking: Whether to enable Claude's extended thinking capability
        :param thinking_budget: Number of tokens for thinking (min 1024, default to max_tokens - 1000)
        :return: final string
        """
        try:
            # Extract system message if present
            system_prompt = None
            filtered_messages = []
            
            for msg in messages:
                if msg["role"] == "system":
                    system_prompt = msg["content"]
                else:
                    filtered_messages.append(msg)
            
            # Create the request parameters
            params = {
                "model": self.model_name,
                "messages": filtered_messages,
                "max_tokens": max_tokens,
                "temperature": temperature
            }
            
            # Add system prompt if present
            if system_prompt:
                params["system"] = system_prompt
                
            # Add thinking if enabled
            if enable_thinking:
                # Default thinking budget is max_tokens minus a buffer, or 1024 if that would be too small
                if thinking_budget is None:
                    thinking_budget = max(1024, max_tokens - 1000)
                
                # Ensure minimum of 1024 tokens and less than max_tokens
                thinking_budget = max(1024, min(thinking_budget, max_tokens - 100))
                
                params["thinking"] = {
                    "type": "enabled",
                    "budget_tokens": thinking_budget
                }
            
            # Use streaming for large token counts to avoid timeouts
            STREAMING_THRESHOLD = 6000  # Lower threshold to be safer
            if max_tokens > STREAMING_THRESHOLD:
                # Using the anthropic-recommended streaming approach
                params["stream"] = True
                
                # Start the streaming response
                with_stream = self.client.messages.create(**params)
                
                # Collect the content properly using the stream events
                content_chunks = []
                thinking_chunks = []
                
                for event in with_stream:
                    if event.type == "content_block_delta":
                        if hasattr(event.delta, "text") and event.delta.text:
                            content_chunks.append(event.delta.text)
                        elif hasattr(event.delta, "thinking") and event.delta.thinking:
                            thinking_chunks.append(event.delta.thinking)
                
                # Join the chunks to form the complete response
                content_text = "".join(content_chunks)
                thinking_text = "".join(thinking_chunks)
                
                # Format the final response
                if thinking_text:
                    return f"Thinking:\n{thinking_text}\n\nAnswer:\n{content_text}"
                else:
                    return content_text
            else:
                # Use non-streaming for smaller token counts
                resp = self.client.messages.create(**params)
                
                # Extract content from response
                result = ""
                if resp.content and len(resp.content) > 0:
                    # Look for thinking content blocks first
                    has_thinking = False
                    thinking_text = ""
                    answer_text = ""
                    
                    for block in resp.content:
                        if hasattr(block, 'type'):
                            if block.type == "thinking":
                                has_thinking = True
                                thinking_text = block.thinking
                            elif block.type == "text":
                                answer_text += block.text
                    
                    # Format the response with thinking if available
                    if has_thinking:
                        result = f"Thinking:\n{thinking_text}\n\nAnswer:\n{answer_text}"
                    else:
                        result = answer_text or resp.content[0].text
                    
                    return result
                return ""
        except Exception as e:
            print(f"Claude API Error: {e}")  # Print the error for debugging
            return f"ERROR from Claude: {str(e)}"


class DeepseekR1Client:
    """
    Minimal client for DeepSeek R1 using openai library with a custom base URL.
    Env variables:
      - DEEPSEEK_API_KEY
    """

    def __init__(self):
        self.api_key = os.environ.get("DEEPSEEK_API_KEY", "missing-deepseek-key")
        
        # DeepSeek API configuration
        # Base URL updated per DeepSeek API documentation
        base_url = "https://api.deepseek.com/v1"
        
        # Use OpenAI client with DeepSeek base URL
        try:
            import httpx
            # Custom headers needed for DeepSeek authentication
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            http_client = httpx.Client(
                base_url=base_url,
                headers=headers,
                timeout=60.0
            )
            self.client = openai.OpenAI(
                api_key=self.api_key, 
                http_client=http_client,
                base_url=base_url
            )
        except Exception as e:
            print(f"Warning: OpenAI client creation failed: {e}")
            # Fall back to direct HTTP requests if all else fails
            self.client = None
        
        self.model_name = "deepseek-reasoner"

    def run(self, messages, max_tokens=8192, temperature=0.2):
        """
        Call to DeepSeek R1 with automatic streaming for large token counts
        
        :param messages: list of { "role": "user"/"assistant"/"system", "content": "..."}
        :param max_tokens: limit for the generated text
        :param temperature: Controls randomness (0.0 to 2.0, lower is better for coding)
        :return: final string including reasoning if available
        """
        try:
            # If client initialization failed, make direct API call
            if self.client is None:
                print("Falling back to direct API call for DeepSeek")
                import requests
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": self.model_name,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature
                }
                response = requests.post(
                    "https://api.deepseek.com/v1/chat/completions",
                    json=payload,
                    headers=headers
                )
                if response.status_code == 200:
                    data = response.json()
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    return content
                else:
                    raise Exception(f"Error code: {response.status_code} - {response.text}")
            
            # Use streaming for large token counts to avoid timeouts
            STREAMING_THRESHOLD = 6000  # Lower threshold to be safer
            use_streaming = max_tokens > STREAMING_THRESHOLD
            
            if use_streaming:
                # Process with streaming
                stream_resp = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stream=True
                )
                
                # Collect streamed content
                content_chunks = []
                reasoning_chunks = []
                
                try:
                    for chunk in stream_resp:
                        if hasattr(chunk, 'choices') and chunk.choices and len(chunk.choices) > 0:
                            choice = chunk.choices[0]
                            # Handle deltas for content
                            if hasattr(choice, 'delta'):
                                # Extract content if present
                                if hasattr(choice.delta, 'content') and choice.delta.content is not None:
                                    content_chunks.append(choice.delta.content)
                                # Extract reasoning content if present
                                if hasattr(choice.delta, 'reasoning_content') and choice.delta.reasoning_content is not None:
                                    reasoning_chunks.append(choice.delta.reasoning_content)
                except Exception as stream_err:
                    print(f"Error during DeepSeek streaming: {stream_err}")
                    # If streaming fails partway, return what we have so far
                    if not content_chunks:
                        raise  # Re-raise if we didn't get any content
                
                # Combine chunks
                content = "".join(content_chunks)
                reasoning = "".join(reasoning_chunks)
                
                # Format response
                if reasoning:
                    return f"Reasoning:\n{reasoning}\n\nAnswer:\n{content}"
                return content
            else:
                # Use non-streaming for smaller token counts
                resp = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stream=False
                )
                
                if resp.choices and len(resp.choices) > 0:
                    # Check if reasoning content is available (deepseek-reasoner specific)
                    reasoning = getattr(resp.choices[0].message, 'reasoning_content', None)
                    content = resp.choices[0].message.content
                    
                    # If reasoning is available, prepend it to the content
                    if reasoning:
                        return f"Reasoning:\n{reasoning}\n\nAnswer:\n{content}"
                    return content
                return ""
        except Exception as e:
            print(f"DeepSeek API Error: {e}")  # Print the error for debugging
            return f"ERROR from DeepSeek: {str(e)}"


class GeminiProClient:
    """
    Minimal client for Google's Gemini models.
    Uses environment variables:
      - GEMINI_API_KEY: The API key for Google AI
      - GEMINI_MODEL (optional, default "gemini-2.0-flash")
    """

    def __init__(self):
        if not HAS_GEMINI:
            raise ImportError("google-generativeai package is required to use Gemini models. Install with: pip install google-generativeai")
        
        self.api_key = os.environ.get("GEMINI_API_KEY", "missing-api-key")
        self.model_name = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
        # Configure the API key
        genai.configure(api_key=self.api_key)
        # Default output token limits per model
        self.output_token_limits = {
            "gemini-2.0-flash": 8192,
            "gemini-2.0-pro-exp-0205": 64000
        }
        # Default input token limits per model
        self.input_token_limits = {
            "gemini-2.0-flash": 1000000,
            "gemini-2.0-pro-exp-0205": 1000000
        }

    def run(self, messages, max_tokens=None, temperature=0.2, enable_thinking=False, thinking_budget=None):
        """
        Call to the Gemini model.
        
        :param messages: list of { "role": "user"/"assistant"/"system", "content": "..."}
        :param max_tokens: Maximum tokens in the response (defaults to model's output limit)
        :param temperature: Controls randomness (0.0-1.0, higher = more creative)
        :param enable_thinking: Not used for Gemini
        :param thinking_budget: Not used for Gemini
        :return: The model's response text
        """
        try:
            # Set default max tokens based on the model
            if max_tokens is None:
                max_tokens = self.output_token_limits.get(self.model_name, 8192)
            
            # Create a generation config
            generation_config = {
                "max_output_tokens": max_tokens,
                "temperature": temperature
            }
            
            # Convert messages to Gemini-friendly format
            gemini_messages = []
            system_content = None
            
            # Extract system message if present
            for msg in messages:
                if msg["role"] == "system":
                    system_content = msg["content"]
                elif msg["role"] == "user":
                    if system_content:
                        # If we have a system message, prepend it to user message
                        role_content = f"System Instructions: {system_content}\n\nUser Message: {msg['content']}"
                        gemini_messages.append({"role": "user", "parts": [role_content]})
                        system_content = None  # Clear after use
                    else:
                        gemini_messages.append({"role": "user", "parts": [msg["content"]]})
                elif msg["role"] == "assistant":
                    gemini_messages.append({"role": "model", "parts": [msg["content"]]})
            
            # Get the model
            model = genai.GenerativeModel(model_name=self.model_name, generation_config=generation_config)
            
            # If we only have one message, use the generate_content method
            if len(gemini_messages) <= 1:
                content = system_content or ""
                if gemini_messages:
                    content = gemini_messages[0]["parts"][0]
                response = model.generate_content(content)
                return response.text
            
            # Otherwise use the chat method
            chat = model.start_chat()
            for msg in gemini_messages:
                if msg["role"] == "user":
                    response = chat.send_message(msg["parts"][0])
            
            return response.text
            
        except Exception as e:
            error_msg = f"ERROR from Gemini: {str(e)}"
            print(error_msg)
            return error_msg


class OllamaClient:
    """
    Client for Ollama models running locally or remotely.
    Uses environment variables:
      - OLLAMA_HOST: The host where Ollama is running (default: http://localhost:11434)
    """

    def __init__(self, model_name):
        self.host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        self.model_name = model_name
        # Remove the 'ollama:' prefix if present
        if self.model_name.startswith("ollama:"):
            self.model_name = self.model_name[7:]
        
        # Check if the model exists
        try:
            response = requests.get(f"{self.host}/api/tags")
            if response.status_code == 200:
                models = [model["name"] for model in response.json().get("models", [])]
                if self.model_name not in models:
                    print(f"Warning: Model '{self.model_name}' not found in Ollama. Available models: {models}")
        except Exception as e:
            print(f"Warning: Could not connect to Ollama at {self.host}: {e}")

    def run(self, messages, max_tokens=4096, temperature=0.2):
        """
        Call to Ollama model
        
        :param messages: list of { "role": "user"/"assistant"/"system", "content": "..."}
        :param max_tokens: limit for the generated text (note: not all Ollama models respect this)
        :param temperature: Controls randomness (0.0 to 1.0)
        :return: final string
        """
        try:
            # Convert client format to Ollama format
            ollama_messages = []
            for msg in messages:
                role = msg["role"]
                # Ollama uses "assistant" instead of "model"
                if role == "model":
                    role = "assistant"
                ollama_messages.append({
                    "role": role,
                    "content": msg["content"]
                })
            
            # Prepare request data
            data = {
                "model": self.model_name,
                "messages": ollama_messages,
                "options": {
                    "temperature": temperature
                }
            }
            
            # Add max_tokens if supported
            if max_tokens:
                data["options"]["num_predict"] = max_tokens
            
            # Make API call
            response = requests.post(f"{self.host}/api/chat", json=data)
            
            if response.status_code == 200:
                return response.json().get("message", {}).get("content", "")
            else:
                error_message = f"Ollama API Error: HTTP {response.status_code} - {response.text}"
                print(error_message)
                return f"ERROR from Ollama: {error_message}"
        
        except Exception as e:
            error_message = f"Ollama API Error: {str(e)}"
            print(error_message)
            return f"ERROR from Ollama: {error_message}"


class AIOrchestrator:
    """
    A minimal orchestrator that picks either Claude3.7Sonnet, DeepseekR1, Gemini, or Ollama models
    and calls .run(...) with system+user messages.
    """

    def __init__(self, model_name: str):
        """
        model_name can be:
        - "claude37sonnet" 
        - "deepseekr1"
        - "gemini2pro"
        - "gemini2flash"
        - "ollama:modelname" or just a model name for Ollama
        """
        self.model_name = model_name.lower()
        
        # Standard models
        if self.model_name == "claude37sonnet":
            self.client = Claude37SonnetClient()
            self.max_tokens_limit = 64000
            self.max_input_tokens = 200000  # Claude's input limit
        elif self.model_name == "deepseekr1":
            self.client = DeepseekR1Client()
            self.max_tokens_limit = 8192  # DeepSeek's output limit
            self.max_input_tokens = 32000  # DeepSeek's input limit
        elif self.model_name == "gemini2pro":
            self.client = GeminiProClient()
            self.max_tokens_limit = 64000
            self.max_input_tokens = 1000000  # Gemini Pro's input limit
            self.client.model_name = "gemini-2.0-pro-exp-0205"  # Override to use Pro model
        elif self.model_name == "gemini2flash":
            self.client = GeminiProClient()
            self.max_tokens_limit = 8192  # Gemini 2.0 Flash output limit
            self.max_input_tokens = 1000000  # Gemini 2.0 Flash input limit (1,048,576)
            self.client.model_name = "gemini-2.0-flash"  # Ensure using Flash model
        # Ollama models
        elif self.model_name.startswith("ollama:") or self._is_ollama_model(self.model_name):
            self.client = OllamaClient(self.model_name)
            self.max_tokens_limit = 4096  # Default for most Ollama models
            self.max_input_tokens = 8192  # Default input limit for Ollama models
        else:
            raise ValueError(f"Unknown model: {model_name}")

    def _is_ollama_model(self, model_name):
        """Check if a model name might be an Ollama model"""
        # Try to check available Ollama models
        try:
            ollama_host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
            response = requests.get(f"{ollama_host}/api/tags")
            if response.status_code == 200:
                models = [model["name"] for model in response.json().get("models", [])]
                return model_name in models
        except:
            # If we can't connect or validate, just return False
            return False
        return False

    def call_llm(self, system_prompt: str, user_prompt: str, max_tokens: int = None, temperature: float = 0.2) -> str:
        """
        Minimal synergy: just pass system+user messages, get final text.
        
        :param system_prompt: The system instruction
        :param user_prompt: The user query or instruction
        :param max_tokens: Maximum tokens in the response (defaults to model's limit)
        :param temperature: Controls randomness (0.0-1.0, higher = more creative)
        :return: The model's response text
        """
        # If max_tokens is not specified, use the model's default limit
        if max_tokens is None:
            max_tokens = self.max_tokens_limit
        else:
            # Otherwise ensure max_tokens is within the model's limit
            max_tokens = min(max_tokens, self.max_tokens_limit)
        
        # Create the messages list for the model
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # Call the model
        return self.client.run(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature
        )
