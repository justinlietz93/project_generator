from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Optional, List
import os
import time
import jwt
from datetime import datetime, timedelta
import uuid
import asyncio
import json
import shutil
import zipfile
from fastapi.responses import FileResponse
import re
import sys
import threading

# Import the AIOrchestrator
from ai_clients import AIOrchestrator

# Initialize FastAPI app
app = FastAPI(title="AI Orchestration API", 
              description="API for accessing various AI models through a unified interface")

# Add CORS middleware to allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update this with specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# JWT Authentication configuration
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "insecure-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 day

# OAuth2 password bearer for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Rate limiting configuration
RATE_LIMIT_STANDARD = 10  # requests per minute for standard tier
RATE_LIMIT_PREMIUM = 30   # requests per minute for premium tier
user_request_counts = {}  # Track user requests

# Global dictionary to track active build processes
active_build_processes = {}

# Models for request/response
class TokenData(BaseModel):
    username: str
    tier: str

class Token(BaseModel):
    access_token: str
    token_type: str

class User(BaseModel):
    username: str
    tier: str = "standard"  # "standard" or "premium"
    disabled: bool = False

class UserInDB(User):
    hashed_password: str
    api_key: str
    
class AIPromptRequest(BaseModel):
    model: str
    system_prompt: str
    user_prompt: str
    max_tokens: Optional[int] = 1000
    temperature: Optional[float] = 0.7

class AIPromptResponse(BaseModel):
    response: str
    model: str
    tokens_used: int
    request_id: str

# Define a response model for model information
class ModelInfo(BaseModel):
    id: str
    name: str
    description: str
    max_tokens: int
    tier: str  # "standard" or "premium"

# In-memory user database - replace with a real database in production
fake_users_db = {
    "demo": {
        "username": "demo",
        "hashed_password": "password123",  # Use proper hashing in production
        "tier": "standard",
        "disabled": False,
        "api_key": "demo-api-key"
    },
    "premium_user": {
        "username": "premium_user",
        "hashed_password": "premium123",  # Use proper hashing in production
        "tier": "premium",
        "disabled": False,
        "api_key": "premium-api-key"
    }
}

# Usage tracking - replace with a database in production
usage_log = []

# Authentication functions
def verify_password(plain_password, hashed_password):
    # Replace with proper password verification in production
    return plain_password == hashed_password

def get_user(db, username: str):
    if username in db:
        user_dict = db[username]
        return UserInDB(**user_dict)
    return None

def authenticate_user(fake_db, username: str, password: str):
    user = get_user(fake_db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username, tier=payload.get("tier", "standard"))
    except jwt.PyJWTError:
        raise credentials_exception
    user = get_user(fake_users_db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

# Rate limiting middleware
async def check_rate_limit(request: Request, user: User = Depends(get_current_active_user)):
    current_minute = int(time.time() / 60)
    user_key = f"{user.username}:{current_minute}"
    
    if user_key not in user_request_counts:
        user_request_counts[user_key] = 0
    
    user_request_counts[user_key] += 1
    
    # Clean up old entries
    for key in list(user_request_counts.keys()):
        if not key.endswith(str(current_minute)):
            del user_request_counts[key]
    
    # Check if the user has exceeded their rate limit
    rate_limit = RATE_LIMIT_PREMIUM if user.tier == "premium" else RATE_LIMIT_STANDARD
    if user_request_counts[user_key] > rate_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Your tier ({user.tier}) allows {rate_limit} requests per minute."
        )

# Token endpoint for authentication
@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(fake_users_db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "tier": user.tier}, 
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# API Key authentication for programmatic access
async def get_user_by_api_key(api_key: str, db=fake_users_db):
    for username, user_data in db.items():
        if user_data.get("api_key") == api_key:
            return UserInDB(**user_data)
    return None

# API endpoint to list available models
@app.get("/models", response_model=List[str])
async def list_models(user: User = Depends(get_current_active_user)):
    # List available models based on user tier
    # For testing: make all models available to all users
    available_models = ["deepseekr1", "claude37sonnet"]
    
    # Return all models for now
    return available_models

# Add a new endpoint for detailed model information
@app.get("/model-info", response_model=List[ModelInfo])
async def get_model_info(user: User = Depends(get_current_active_user)):
    # Define model details
    model_details = [
        ModelInfo(
            id="deepseekr1",
            name="DeepSeek-1 Lite",
            description="A capable language model for general tasks",
            max_tokens=8192,
            tier="standard"
        ),
        ModelInfo(
            id="claude37sonnet",
            name="Claude 3.7 Sonnet",
            description="Anthropic's advanced model with strong reasoning capabilities",
            max_tokens=64000,
            tier="premium"
        )
    ]
    
    # Filter models based on user tier
    if user.tier != "premium":
        model_details = [m for m in model_details if m.tier == "standard"]
        
    return model_details

# Main API endpoint for AI requests
@app.post("/generate", response_model=AIPromptResponse)
async def generate_ai_response(
    request: AIPromptRequest,
    user: User = Depends(get_current_active_user),
    _: None = Depends(check_rate_limit)
):
    # Define model-specific token limits
    model_token_limits = {
        "deepseekr1": 8192,
        "claude37sonnet": 64000
    }
    
    # Standard tier token limit
    standard_tier_limit = 2000
    
    # Validate model access based on user tier
    premium_only_models = ["claude37sonnet"]
    if user.tier != "premium" and request.model.lower() in premium_only_models:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Model {request.model} is only available to premium users"
        )
    
    # Apply token limits based on tier and model
    max_tokens = request.max_tokens
    if user.tier != "premium":
        max_tokens = min(max_tokens, standard_tier_limit)
    else:
        # For premium users, limit to the model's maximum
        model_limit = model_token_limits.get(request.model.lower(), 4000)  # Default to 4000 if model not found
        max_tokens = min(max_tokens, model_limit)
    
    # Generate a unique request ID
    request_id = str(uuid.uuid4())
    
    try:
        # Initialize the orchestrator with the requested model
        orchestrator = AIOrchestrator(request.model)
            
        # Call the LLM
        response = orchestrator.call_llm(
            system_prompt=request.system_prompt,
            user_prompt=request.user_prompt,
            max_tokens=max_tokens,
            temperature=request.temperature
        )
        
        # Estimate tokens used (rough approximation)
        tokens_used = len(response.split()) * 1.3
        
        # Log usage for billing/analytics
        usage_log.append({
            "user": user.username,
            "tier": user.tier,
            "model": request.model,
            "tokens_used": tokens_used,
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": request_id
        })
        
        return AIPromptResponse(
            response=response,
            model=request.model,
            tokens_used=int(tokens_used),
            request_id=request_id
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing request: {str(e)}"
        )

# User info endpoint
@app.get("/user/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user

# Usage stats endpoint
@app.get("/user/usage")
async def get_usage_stats(current_user: User = Depends(get_current_active_user)):
    user_usage = [log for log in usage_log if log["user"] == current_user.username]
    return {
        "total_requests": len(user_usage),
        "total_tokens": sum(log["tokens_used"] for log in user_usage),
        "recent_requests": user_usage[-10:] if user_usage else []
    }

# Project Builder endpoint
@app.post("/project/build")
async def build_project(
    request: AIPromptRequest,
    user: User = Depends(get_current_active_user),
    _: None = Depends(check_rate_limit)
):
    # Define model-specific token limits
    model_token_limits = {
        "deepseekr1": 8192,
        "claude37sonnet": 64000
    }
    
    # Validate model access based on user tier
    premium_only_models = ["claude37sonnet"]
    if user.tier != "premium" and request.model.lower() in premium_only_models:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Model {request.model} is only available to premium users"
        )
    
    # Apply token limits based on tier and model
    max_tokens = request.max_tokens
    if user.tier != "premium":
        max_tokens = min(max_tokens, 2000)  # Limit to 2000 for standard tier
    else:
        # For premium users, limit to the model's maximum
        model_limit = model_token_limits.get(request.model.lower(), 4000)  # Default if model not found
        max_tokens = min(max_tokens, model_limit)
    
    # Generate a unique request ID
    request_id = str(uuid.uuid4())
    
    try:
        # Import the project_builder module
        from orchestrator import run_project_builder
        import threading
        
        # Create a mapping record for this user's project to the generated_project directory
        # Store it in user projects for tracking purposes
        user_project_dir = os.path.join("projects", user.username)
        os.makedirs(user_project_dir, exist_ok=True)
        
        # Create a metadata file that maps this project ID to the main generated_project directory
        project_mapping = {
            "project_id": request_id,
            "generated_at": datetime.utcnow().isoformat(),
            "user_prompt": request.user_prompt,
            "model": request.model,
            "max_tokens": max_tokens
        }
        
        with open(os.path.join(user_project_dir, f"{request_id}.json"), "w") as f:
            json.dump(project_mapping, f, indent=2)
        
        # Create initial status file showing "in_progress"
        status_path = os.path.join("generated_project", "status.json")
        status_data = {
            "status": "in_progress",
            "project_id": request_id,
            "user": user.username,
            "start_time": datetime.utcnow().isoformat(),
            "model": request.model,
            "estimated_duration": "This may take several hours for complex projects",
            "progress_updates": [
                {
                    "time": datetime.utcnow().isoformat(),
                    "message": "Project generation started"
                }
            ]
        }
        
        with open(status_path, "w") as f:
            json.dump(status_data, f, indent=2)
        
        # Function to periodically update status during long generation
        def update_status_periodically():
            try:
                # Update status every minute while the build is running
                counter = 0
                while True:
                    counter += 1
                    time.sleep(60)  # 1 minute
                    
                    # Check if the project has completed or errored out
                    try:
                        with open(status_path, 'r') as f:
                            current_status = json.load(f)
                            if current_status.get("status") in ["complete", "error"]:
                                break
                    except:
                        pass
                    
                    # Update the status with a new progress message
                    try:
                        with open(status_path, 'r') as f:
                            status_data = json.load(f)
                        
                        # Check for current phase by examining files
                        phase_description = "initial planning"
                        files_count = 0
                        doc_files = []
                        
                        # Count files and check for specific indicators of progress
                        for root, _, files in os.walk("generated_project"):
                            for filename in files:
                                if filename in ['status.json']:
                                    continue
                                files_count += 1
                                
                                # Check for phase indicators in doc directory
                                if root.endswith('/doc') or root.endswith('\\doc'):
                                    doc_files.append(filename)
                        
                        # Determine current phase based on files
                        if any(f.startswith("STEP1_") for f in doc_files):
                            phase_description = "requirements analysis"
                        if any(f.startswith("STEP2_") for f in doc_files):
                            phase_description = "architecture planning"
                        if any(f.startswith("STEP3_") for f in doc_files):
                            phase_description = "module design"
                        if any(f.startswith("STEP4_") for f in doc_files):
                            phase_description = "project structure setup"
                        if any(f.startswith("STEP5_") for f in doc_files):
                            phase_description = "implementing core files"
                        if any(f.startswith("STEP6_") for f in doc_files):
                            phase_description = "code optimization"
                        if "IMPLEMENTATION.md" in doc_files:
                            phase_description = "final implementation stages"
                        
                        # Update step_info if it exists
                        if "step_info" in status_data:
                            status_data["step_info"]["description"] = f"Working on {phase_description}"
                        
                        # Add new progress update
                        status_data.setdefault("progress_updates", []).append({
                            "time": datetime.utcnow().isoformat(),
                            "message": f"Working on {phase_description} ({counter} minutes elapsed)",
                            "files_found": files_count
                        })
                        
                        with open(status_path, 'w') as f:
                            json.dump(status_data, f, indent=2)
                    except Exception as e:
                        print(f"Error updating status: {e}")
            except Exception as e:
                print(f"Status update thread error: {e}")
        
        # Start project building in a separate thread
        def build_project_thread():
            try:
                # Analyze existing project files to determine where to start
                start_step = 1
                start_substep = None
                doc_dir = os.path.join("generated_project", "doc")
                
                # Detect the current progress by examining existing files
                if os.path.exists(doc_dir):
                    # Check for the most advanced step file
                    step_files = []
                    for file in os.listdir(doc_dir):
                        if file.startswith("STEP") and file.endswith(".md"):
                            step_files.append(file)
                    
                    if step_files:
                        # Sort files to find the latest step/substep
                        step_files.sort()
                        latest_file = step_files[-1]
                        print(f"Found latest step file: {latest_file}")
                        
                        # Parse step/substep from filename (e.g., STEP3_SUBSTEP_3B.md)
                        try:
                            if "_SUBSTEP_" in latest_file:
                                step_part = latest_file.split("_SUBSTEP_")[0].replace("STEP", "")
                                substep_part = latest_file.split("_SUBSTEP_")[1].split(".")[0]
                                
                                # Extract step number and substep letter
                                start_step = int(step_part)
                                if substep_part:
                                    # Get just the letter part (e.g., "3B" -> "B")
                                    letter = ''.join([c for c in substep_part if c.isalpha()])
                                    if letter:
                                        start_substep = letter
                                        # Move to next substep
                                        import string
                                        alphabet = string.ascii_uppercase
                                        next_idx = alphabet.index(letter) + 1
                                        if next_idx < len(alphabet):
                                            start_substep = alphabet[next_idx]
                            elif "STEP" in latest_file:
                                # Just has step number
                                step_num = int(''.join(filter(str.isdigit, latest_file)))
                                start_step = step_num + 1  # Move to next step
                                
                            print(f"Will resume from step {start_step}{start_substep or ''}")
                        except Exception as e:
                            print(f"Error parsing step files: {e}, starting from the beginning")
                            start_step = 1
                            start_substep = None
                    
                    # Check if implementation has started
                    if os.path.exists(os.path.join(doc_dir, "IMPLEMENTATION.md")) or os.path.exists(os.path.join(doc_dir, "project_complete.flag")):
                        print("Project appears to be complete, running syntax check only")
                        run_syntax_check_only = True
                    else:
                        run_syntax_check_only = False
                else:
                    # No doc directory, start from the beginning
                    start_step = 1
                    start_substep = None
                    run_syntax_check_only = False
                
                # Import directly from project_builder to avoid the orchestrator wrapper
                import project_builder
                
                # Call the function directly with the correct parameter signature and determined starting point
                project_builder.run_project_builder(
                    vision=request.user_prompt,
                    model_name=request.model,
                    start_step=start_step,
                    start_substep=start_substep,
                    run_syntax_check_only=run_syntax_check_only
                )
                
                # Wait a moment to ensure file operations are complete
                time.sleep(2)
                
                # Check for proper project completion by looking for critical indicators
                # rather than specific file counts
                
                # Check these signs of completion:
                # 1. The doc directory exists
                # 2. The project has some critical files indicating completion
                # 3. The flag file exists (if the orchestrator creates one)
                completion_indicators = [
                    os.path.exists(doc_dir),  # Doc directory exists
                    os.path.exists(os.path.join("generated_project", "doc", "project_complete.flag")) or  # Flag file
                    os.path.exists(os.path.join("generated_project", "doc", "SUMMARY.md")) or  # Summary file
                    len([f for f in os.listdir("generated_project") if f.endswith('.md') or f.endswith('.py') or f.endswith('.js')]) > 0  # Any content files
                ]
                
                if not all(completion_indicators[:1]) or not any(completion_indicators[1:]):
                    # If primary indicators are missing, wait a bit longer and check again
                    time.sleep(5)
                    completion_indicators = [
                        os.path.exists(doc_dir),
                        os.path.exists(os.path.join("generated_project", "doc", "project_complete.flag")) or
                        os.path.exists(os.path.join("generated_project", "doc", "SUMMARY.md")) or
                        len([f for f in os.listdir("generated_project") if f.endswith('.md') or f.endswith('.py') or f.endswith('.js')]) > 0
                    ]
                    
                    if not all(completion_indicators[:1]) or not any(completion_indicators[1:]):
                        raise Exception("Project generation incomplete - missing expected output files")
                
                # Count total files as a metric
                total_files = sum([len(files) for _, _, files in os.walk("generated_project")])
                
                # Create a status file in the generated_project directory
                status_data = {
                    "status": "complete",
                    "project_id": request_id,
                    "user": user.username,
                    "completed_at": datetime.utcnow().isoformat(),
                    "model": request.model,
                    "file_count": total_files,
                    "total_duration_minutes": round((datetime.utcnow() - datetime.fromisoformat(project_mapping["generated_at"])).total_seconds() / 60, 1)
                }
                
                # Preserve progress updates from previous status
                try:
                    with open(status_path, 'r') as f:
                        old_status = json.load(f)
                        if "progress_updates" in old_status:
                            status_data["progress_updates"] = old_status["progress_updates"]
                except:
                    pass
                
                # Add final update
                status_data.setdefault("progress_updates", []).append({
                    "time": datetime.utcnow().isoformat(),
                    "message": f"Project completed successfully with {total_files} files"
                })
                
                with open(status_path, "w") as f:
                    json.dump(status_data, f, indent=2)
                
                print(f"Project {request_id} completed successfully with {total_files} files")
                    
            except Exception as e:
                print(f"Error in project building thread: {e}")
                # Update status on error
                try:
                    # Get current status to preserve progress updates
                    try:
                        with open(status_path, 'r') as f:
                            status_data = json.load(f)
                    except:
                        status_data = {
                            "progress_updates": []
                        }
                    
                    # Update with error information
                    status_data.update({
                        "status": "error",
                        "project_id": request_id,
                        "error": str(e),
                        "user": user.username,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    
                    # Add error to progress updates
                    status_data.setdefault("progress_updates", []).append({
                        "time": datetime.utcnow().isoformat(),
                        "message": f"Error: {str(e)}"
                    })
                    
                    with open(status_path, "w") as f:
                        json.dump(status_data, f, indent=2)
                except Exception as inner_e:
                    print(f"Failed to update status with error: {inner_e}")
                    pass
        
        # Start the build thread
        thread = threading.Thread(target=build_project_thread)
        thread.daemon = True
        thread.start()
        
        # Track the thread in our active processes dictionary
        active_build_processes[request_id] = {
            "thread": thread,
            "start_time": datetime.utcnow()
        }
        
        # Start the status update thread
        status_thread = threading.Thread(target=update_status_periodically)
        status_thread.daemon = True
        status_thread.start()
        
        # Return a simple response with the project ID
        return {
            "project_id": request_id,
            "status": "processing",
            "message": "Project build started. This may take several hours for complex projects. Check status endpoint for updates.",
            "tokens_used": 0,  # Initial token usage
            "response": "Project build initiated"
        }
        
    except Exception as e:
        print(f"Error starting project build: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error starting project build: {str(e)}"
        )

@app.get("/project/status/{project_id}")
async def get_project_status(
    project_id: str,
    user: User = Depends(get_current_active_user)
):
    # Check if the project exists for this user
    project_metadata_path = os.path.join("projects", user.username, f"{project_id}.json")
    if not os.path.exists(project_metadata_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Check the status in the generated_project directory
    status_file = os.path.join("generated_project", "status.json")
    files = []
    step_info = {}
    progress_updates = []
    
    # Default status is "in_progress" unless we can confirm otherwise
    status_value = "in_progress"
    
    # If we have a status file, read it
    if os.path.exists(status_file):
        try:
            with open(status_file, 'r') as f:
                status_data = json.load(f)
            
            # Get status from the file - could be "in_progress", "complete" or "error"
            status_value = status_data.get("status", "in_progress")
            
            # Include any additional status info
            if "error" in status_data:
                step_info["error"] = status_data["error"]
                
            if "file_count" in status_data:
                step_info["file_count"] = status_data["file_count"]
                
            if "estimated_duration" in status_data:
                step_info["estimated_duration"] = status_data["estimated_duration"]
                
            if "total_duration_minutes" in status_data:
                step_info["total_duration_minutes"] = status_data["total_duration_minutes"]
                
            # Get progress updates if available
            if "progress_updates" in status_data:
                progress_updates = status_data["progress_updates"]
        except Exception as e:
            print(f"Error reading status file: {e}")
    
    # Additional verification of project completeness
    doc_dir = os.path.join("generated_project", "doc")
    flag_file = os.path.join(doc_dir, "project_complete.flag")
    summary_file = os.path.join(doc_dir, "SUMMARY.md")
    
    # Check if key indicators of completion exist
    if status_value == "complete":
        # Verify the completion with actual file presence
        if not (os.path.exists(doc_dir) and 
               (os.path.exists(flag_file) or os.path.exists(summary_file))):
            # If claimed to be complete but missing critical files, treat as in progress
            status_value = "in_progress"
    
    # Get the current number of files even while in progress
    file_count = 0
    for root, _, filenames in os.walk("generated_project"):
        for filename in filenames:
            if filename in ['status.json']:
                continue
            file_count += 1
            rel_path = os.path.relpath(os.path.join(root, filename), "generated_project")
            files.append(rel_path)
    
    # Extract step information from SUMMARY.md if it exists
    if os.path.exists(summary_file):
        try:
            with open(summary_file, "r") as f:
                steps_content = f.read()
            
            # Parse step information
            import re
            steps = re.findall(r"## (Step \d+|Vision|.*?)\n(.*?)(?=\n## |$)", steps_content, re.DOTALL)
            
            step_info.update({
                "total_steps": len(steps) - 1 if steps else 0,  # Subtract 1 for Vision
                "current_step": len(steps) - 1 if status_value == "complete" else len(steps) - 2,
                "description": f"Step {len(steps) - 1}" if steps else "Processing"
            })
        except Exception as e:
            print(f"Error parsing steps: {e}")
    
    # Basic response with everything we've gathered
    response = {
        "status": status_value,
        "project_id": project_id,
        "files": sorted(files),
        "file_count": file_count
    }
    
    # Add step info if we have it
    if step_info:
        response["step_info"] = step_info
        
    # Add progress updates if available
    if progress_updates:
        response["progress_updates"] = progress_updates
        
    # Add timestamps if available
    if os.path.exists(status_file):
        try:
            with open(status_file, 'r') as f:
                status_data = json.load(f)
                
            if "start_time" in status_data:
                response.setdefault("timestamps", {})["start_time"] = status_data["start_time"]
                
            if "completed_at" in status_data:
                response.setdefault("timestamps", {})["end_time"] = status_data["completed_at"]
        except:
            pass
    
    return response

@app.get("/project/download/{project_id}")
async def download_project(
    project_id: str,
    user: User = Depends(get_current_active_user)
):
    # Check if the project exists for this user
    project_metadata_path = os.path.join("projects", user.username, f"{project_id}.json")
    if not os.path.exists(project_metadata_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Use the existing generated_project directory
    project_dir = "generated_project"
    if not os.path.exists(project_dir):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project files not found"
        )
    
    # Create a temporary directory to prepare the downloaded files
    temp_dir = os.path.join("temp", f"project_{project_id}")
    os.makedirs(temp_dir, exist_ok=True)
    
    # Copy all project files to the temp directory, excluding metadata files
    for root, _, files in os.walk(project_dir):
        for file in files:
            # Skip metadata files
            if file in ['status.json']:
                continue
                
            src_path = os.path.join(root, file)
            rel_path = os.path.relpath(src_path, project_dir)
            dst_path = os.path.join(temp_dir, rel_path)
            
            # Create directory structure if needed
            os.makedirs(os.path.dirname(dst_path), exist_ok=True)
            
            # Copy the file
            shutil.copy2(src_path, dst_path)
    
    # Create a ZIP file of the project
    zip_path = os.path.join("temp", f"project_{project_id}.zip")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(temp_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, temp_dir)
                zipf.write(file_path, arcname)
    
    # Clean up the temp directory after creating the ZIP
    shutil.rmtree(temp_dir)
    
    # Return the ZIP file
    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename=f"project_{project_id}.zip"
    )

@app.post("/project/stop/{project_id}")
async def stop_project_build(
    project_id: str,
    user: User = Depends(get_current_active_user)
):
    """
    Stop a running project build process.
    
    Args:
        project_id: ID of the project to stop
        
    Returns:
        JSON response indicating success or failure
    """
    try:
        # Check if the project exists
        project_dir = os.path.join("projects", user.username)
        project_file = os.path.join(project_dir, f"{project_id}.json")
        
        if not os.path.exists(project_file):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with ID {project_id} not found"
            )
        
        # Check if we have a thread for this project
        if project_id not in active_build_processes:
            # Update the status file to indicate stopped even if we don't have a thread
            status_path = os.path.join("generated_project", "status.json")
            if os.path.exists(status_path):
                try:
                    with open(status_path, 'r') as f:
                        status_data = json.load(f)
                    
                    # Only update if it's still in progress
                    if status_data.get("status") == "in_progress":
                        status_data["status"] = "stopped"
                        status_data.setdefault("progress_updates", []).append({
                            "time": datetime.utcnow().isoformat(),
                            "message": "Project build stopped by user"
                        })
                        
                        with open(status_path, 'w') as f:
                            json.dump(status_data, f, indent=2)
                except Exception as e:
                    print(f"Error updating status file: {e}")
            
            return {
                "success": True,
                "message": "Project was not running or has already completed"
            }
        
        # Get the thread and set a flag to stop it
        # We'll use an environment variable to signal the build process to stop
        # This allows us to stop the build without directly terminating threads
        os.environ[f"STOP_BUILD_{project_id}"] = "true"
        
        # Update the status file
        status_path = os.path.join("generated_project", "status.json")
        if os.path.exists(status_path):
            try:
                with open(status_path, 'r') as f:
                    status_data = json.load(f)
                
                status_data["status"] = "stopped"
                status_data.setdefault("progress_updates", []).append({
                    "time": datetime.utcnow().isoformat(),
                    "message": "Project build stopped by user"
                })
                
                with open(status_path, 'w') as f:
                    json.dump(status_data, f, indent=2)
            except Exception as e:
                print(f"Error updating status file: {e}")
        
        # Remove the build process from our tracking dictionary
        thread_info = active_build_processes.pop(project_id, None)
        
        return {
            "success": True,
            "message": "Project build stopping"
        }
    
    except Exception as e:
        print(f"Error stopping project build: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error stopping project build: {str(e)}"
        )

class ResumeProjectRequest(BaseModel):
    model: Optional[str] = None

@app.post("/project/resume/{project_id}")
async def resume_project_build(
    project_id: str,
    request: Optional[ResumeProjectRequest] = None,
    user: User = Depends(get_current_active_user)
):
    """
    Resume a stopped project build process.
    
    Args:
        project_id: ID of the project to resume
        request: Optional request containing model to use when resuming
        
    Returns:
        JSON response indicating success or failure
    """
    try:
        # Check if the project exists
        project_dir = os.path.join("projects", user.username)
        project_file = os.path.join(project_dir, f"{project_id}.json")
        
        if not os.path.exists(project_file):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with ID {project_id} not found"
            )
        
        # Check if the project is actually stopped
        status_path = os.path.join("generated_project", "status.json")
        if not os.path.exists(status_path):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project status file not found"
            )
            
        try:
            with open(status_path, 'r') as f:
                status_data = json.load(f)
                
            if status_data.get("status") != "stopped":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Project is not in a stopped state (current state: {status_data.get('status')})"
                )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error reading project status: {str(e)}"
            )
        
        # Load the project data
        with open(project_file, 'r') as f:
            project_data = json.load(f)
        
        # Get the model to use - either from the request or fall back to the original
        model_name = project_data.get("model", "deepseekr1")
        
        # If a new model was specified in the request, use that instead
        if request and request.model:
            model_name = request.model
            # Update the project data with the new model
            project_data["model"] = model_name
            with open(project_file, 'w') as f:
                json.dump(project_data, f, indent=2)
        
        # Update the status to in_progress
        status_data["status"] = "in_progress"
        status_data["model"] = model_name  # Ensure status reflects the current model
        status_data.setdefault("progress_updates", []).append({
            "time": datetime.utcnow().isoformat(),
            "message": f"Project build resumed by user with model: {model_name}"
        })
        
        with open(status_path, 'w') as f:
            json.dump(status_data, f, indent=2)
        
        # Start a new build thread
        def build_project_thread():
            try:
                # Analyze existing project files to determine where to start
                start_step = 1
                start_substep = None
                doc_dir = os.path.join("generated_project", "doc")
                
                # Detect the current progress by examining existing files
                if os.path.exists(doc_dir):
                    # Check for the most advanced step file
                    step_files = []
                    for file in os.listdir(doc_dir):
                        if file.startswith("STEP") and file.endswith(".md"):
                            step_files.append(file)
                    
                    if step_files:
                        # Sort files to find the latest step/substep
                        step_files.sort()
                        latest_file = step_files[-1]
                        print(f"Found latest step file: {latest_file}")
                        
                        # Parse step/substep from filename (e.g., STEP3_SUBSTEP_3B.md)
                        try:
                            if "_SUBSTEP_" in latest_file:
                                step_part = latest_file.split("_SUBSTEP_")[0].replace("STEP", "")
                                substep_part = latest_file.split("_SUBSTEP_")[1].split(".")[0]
                                
                                # Extract step number and substep letter
                                start_step = int(step_part)
                                if substep_part:
                                    # Get just the letter part (e.g., "3B" -> "B")
                                    letter = ''.join([c for c in substep_part if c.isalpha()])
                                    if letter:
                                        start_substep = letter
                                        # Move to next substep
                                        import string
                                        alphabet = string.ascii_uppercase
                                        next_idx = alphabet.index(letter) + 1
                                        if next_idx < len(alphabet):
                                            start_substep = alphabet[next_idx]
                            elif "STEP" in latest_file:
                                # Just has step number
                                step_num = int(''.join(filter(str.isdigit, latest_file)))
                                start_step = step_num + 1  # Move to next step
                                
                            print(f"Will resume from step {start_step}{start_substep or ''}")
                        except Exception as e:
                            print(f"Error parsing step files: {e}, starting from the beginning")
                            start_step = 1
                            start_substep = None
                    
                    # Check if implementation has started
                    if os.path.exists(os.path.join(doc_dir, "IMPLEMENTATION.md")) or os.path.exists(os.path.join(doc_dir, "project_complete.flag")):
                        print("Project appears to be complete, running syntax check only")
                        run_syntax_check_only = True
                    else:
                        run_syntax_check_only = False
                else:
                    # No doc directory, start from the beginning
                    start_step = 1
                    start_substep = None
                    run_syntax_check_only = False
                
                # Clear any previous stop signal
                if f"STOP_BUILD_{project_id}" in os.environ:
                    del os.environ[f"STOP_BUILD_{project_id}"]
                
                # Load project details
                with open(project_file, 'r') as f:
                    project_data = json.load(f)
                
                # Import directly from project_builder to avoid the orchestrator wrapper
                import project_builder
                
                # Call the function directly with the correct parameter signature and determined starting point
                project_builder.run_project_builder(
                    vision=project_data.get("user_prompt", ""),
                    model_name=model_name,
                    start_step=start_step,
                    start_substep=start_substep,
                    run_syntax_check_only=run_syntax_check_only
                )
                
                # Wait a moment to ensure file operations are complete
                time.sleep(2)
                
                # Check for proper project completion
                completion_indicators = [
                    os.path.exists(doc_dir),  # Doc directory exists
                    os.path.exists(os.path.join("generated_project", "doc", "project_complete.flag")) or  # Flag file
                    os.path.exists(os.path.join("generated_project", "doc", "SUMMARY.md")) or  # Summary file
                    len([f for f in os.listdir("generated_project") if f.endswith('.md') or f.endswith('.py') or f.endswith('.js')]) > 0  # Any content files
                ]
                
                if not all(completion_indicators[:1]) or not any(completion_indicators[1:]):
                    # If primary indicators are missing, wait a bit longer and check again
                    time.sleep(5)
                    completion_indicators = [
                        os.path.exists(doc_dir),
                        os.path.exists(os.path.join("generated_project", "doc", "project_complete.flag")) or
                        os.path.exists(os.path.join("generated_project", "doc", "SUMMARY.md")) or
                        len([f for f in os.listdir("generated_project") if f.endswith('.md') or f.endswith('.py') or f.endswith('.js')]) > 0
                    ]
                    
                    if not all(completion_indicators[:1]) or not any(completion_indicators[1:]):
                        raise Exception("Project generation incomplete - missing expected output files")
                
                # Count total files as a metric
                total_files = sum([len(files) for _, _, files in os.walk("generated_project")])
                
                # Create a status file in the generated_project directory
                status_data = {
                    "status": "complete",
                    "project_id": project_id,
                    "user": user.username,
                    "completed_at": datetime.utcnow().isoformat(),
                    "model": project_data.get("model", "deepseekr1"),
                    "file_count": total_files,
                    "total_duration_minutes": round((datetime.utcnow() - datetime.fromisoformat(project_data.get("generated_at", datetime.utcnow().isoformat()))).total_seconds() / 60, 1)
                }
                
                # Preserve progress updates from previous status
                try:
                    with open(status_path, 'r') as f:
                        old_status = json.load(f)
                        if "progress_updates" in old_status:
                            status_data["progress_updates"] = old_status["progress_updates"]
                except:
                    pass
                
                # Add final update
                status_data.setdefault("progress_updates", []).append({
                    "time": datetime.utcnow().isoformat(),
                    "message": f"Project completed successfully with {total_files} files"
                })
                
                with open(status_path, "w") as f:
                    json.dump(status_data, f, indent=2)
                
                print(f"Project {project_id} completed successfully with {total_files} files")
                    
            except Exception as e:
                print(f"Error in project building thread: {e}")
                # Update status on error
                try:
                    # Get current status to preserve progress updates
                    try:
                        with open(status_path, 'r') as f:
                            status_data = json.load(f)
                    except:
                        status_data = {
                            "progress_updates": []
                        }
                    
                    # Update with error information
                    status_data.update({
                        "status": "error",
                        "project_id": project_id,
                        "error": str(e),
                        "user": user.username,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    
                    # Add error to progress updates
                    status_data.setdefault("progress_updates", []).append({
                        "time": datetime.utcnow().isoformat(),
                        "message": f"Error: {str(e)}"
                    })
                    
                    with open(status_path, "w") as f:
                        json.dump(status_data, f, indent=2)
                except Exception as inner_e:
                    print(f"Failed to update status with error: {inner_e}")
                    pass
        
        # Start the build thread
        thread = threading.Thread(target=build_project_thread)
        thread.daemon = True
        thread.start()
        
        # Track the thread in our active processes dictionary
        active_build_processes[project_id] = {
            "thread": thread,
            "start_time": datetime.utcnow()
        }
        
        # Start the status update thread
        def update_status_periodically():
            try:
                # Update status every minute while the build is running
                counter = 0
                while True:
                    counter += 1
                    time.sleep(60)  # 1 minute
                    
                    # Check if the project has completed or errored out
                    try:
                        with open(status_path, 'r') as f:
                            current_status = json.load(f)
                            if current_status.get("status") in ["complete", "error", "stopped"]:
                                break
                    except:
                        pass
                    
                    # Update the status with a new progress message
                    try:
                        with open(status_path, 'r') as f:
                            status_data = json.load(f)
                        
                        # Count files in the project directory
                        files_count = 0
                        doc_files = []
                        for root, dirs, files in os.walk("generated_project"):
                            files_count += len(files)
                            if root.endswith("doc"):
                                doc_files = files
                        
                        # Determine the current phase based on doc files
                        phase_description = "initial planning"
                        if any(f.startswith("STEP3") for f in doc_files):
                            phase_description = "module design"
                        elif any(f.startswith("STEP2") for f in doc_files):
                            phase_description = "system architecture"
                        elif any(f.startswith("STEP1") for f in doc_files):
                            phase_description = "project planning"
                        
                        if "IMPLEMENTATION.md" in doc_files:
                            phase_description = "final implementation stages"
                        
                        # Update step_info if it exists
                        if "step_info" in status_data:
                            status_data["step_info"]["description"] = f"Working on {phase_description}"
                        
                        # Add new progress update
                        status_data.setdefault("progress_updates", []).append({
                            "time": datetime.utcnow().isoformat(),
                            "message": f"Working on {phase_description} ({counter} minutes elapsed)",
                            "files_found": files_count
                        })
                        
                        with open(status_path, 'w') as f:
                            json.dump(status_data, f, indent=2)
                    except Exception as e:
                        print(f"Error updating status: {e}")
            except Exception as e:
                print(f"Status update thread error: {e}")
        
        status_thread = threading.Thread(target=update_status_periodically)
        status_thread.daemon = True
        status_thread.start()
        
        return {
            "success": True,
            "message": "Project build resumed",
            "project_id": project_id
        }
    
    except Exception as e:
        print(f"Error resuming project build: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error resuming project build: {str(e)}"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 