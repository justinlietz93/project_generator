"""
utils.py

Shared utility functions and classes used across the project.
"""

import os
from pathlib import Path
from typing import Dict, List

class ProjectFile:
    def __init__(self, path: str, content: str):
        self.path = path
        self.content = content

class SubStep:
    def __init__(self, id: str, name: str, prompt: str):
        """Represents a sub-step within a main step of the framework"""
        self.id = id           # Identifier, e.g. "1A"
        self.name = name       # Name of the sub-step
        self.prompt = prompt   # Specific prompt template for this sub-step

def read_project_files(project_root: str) -> Dict[str, "ProjectFile"]:
    """
    Reads text files from project_root, ignoring .git or obvious binaries.
    Returns a dict: { "relative/path": ProjectFile(...) }
    """
    file_map = {}
    root = Path(project_root)
    if not root.is_dir():
        print(f"Warning: {project_root} is not a directory.")
        return file_map

    for p in root.rglob("*"):
        if p.is_file():
            # Use Path's methods to get platform-independent relative path
            rel_path = str(p.relative_to(root))
            # skip .git or some binaries
            if ".git" in rel_path:
                continue
            if p.suffix in [".png", ".jpg", ".exe", ".dll"]:
                continue
            try:
                content = p.read_text(encoding="utf-8")
                file_map[rel_path] = ProjectFile(rel_path, content)
            except Exception as e:
                print(f"Skipping {rel_path}: {e}")
    return file_map

def write_project_file(project_root: str, pf: ProjectFile):
    """
    Ensures the parent directory exists and writes updated content.
    Added robust error handling and extra debugging.
    """
    # Use pathlib for cross-platform path handling
    target = Path(project_root) / pf.path
    print(f"DEBUG: Attempting to write to {target}")
    
    try:
        # Create all parent directories
        target.parent.mkdir(parents=True, exist_ok=True)
        print(f"DEBUG: Ensured parent directory exists: {target.parent}")
        
        # Write the file
        target.write_text(pf.content, encoding="utf-8")
        print(f"DEBUG: Successfully wrote {len(pf.content)} characters to {target}")
        
        # Verify file exists
        if target.exists():
            print(f"DEBUG: File exists verification passed for {target}")
            print(f"DEBUG: File size: {target.stat().st_size} bytes")
        else:
            print(f"ERROR: File should exist but doesn't: {target}")
            
    except Exception as e:
        print(f"ERROR writing to {target}: {str(e)}")
        import traceback
        traceback.print_exc()

def parse_ai_response_and_apply(ai_text: str, file_map: Dict[str, ProjectFile]):
    """
    Looks for lines of the form:
      === File: path/to/file ===
      (some content)

    Then we store that content in file_map[path].
    If path not in file_map, we create a new entry (new file).
    Makes sure to normalize paths for cross-platform compatibility.
    """
    if not ai_text or ai_text.startswith("ERROR from"):
        print("Warning: AI response contains an error or is empty. Cannot parse file markers.")
        return
        
    lines = ai_text.splitlines()
    if not lines:
        print("Warning: AI response has no content lines to parse.")
        return
        
    current_file = None
    content_buffer: List[str] = []
    files_found = 0

    def commit_file():
        nonlocal current_file, content_buffer, files_found
        if current_file:
            # Normalize path separators for cross-platform compatibility
            normalized_path = current_file.replace('/', os.path.sep)
            if normalized_path not in file_map:
                # Create a new entry if it doesn't exist
                file_map[normalized_path] = ProjectFile(normalized_path, "")
            file_map[normalized_path].content = "\n".join(content_buffer)
            print(f"DEBUG: Processed file {normalized_path} with {len(content_buffer)} lines")
            files_found += 1

    for line in lines:
        if line.startswith("=== File: "):
            # commit previous file
            commit_file()
            # Extract the file path, properly trimming any trailing === markers
            file_marker = line.replace("=== File: ", "", 1).strip()
            if file_marker.endswith(" ==="):
                file_marker = file_marker[:-4].strip()
            current_file = file_marker
            content_buffer = []
        else:
            # accumulate lines for this file
            content_buffer.append(line)

    # commit last file
    commit_file()
    
    if files_found == 0:
        print("Warning: No file markers found in AI response. This may indicate formatting issues.")
        print("AI response excerpt (first 200 chars):", ai_text[:200] + "..." if len(ai_text) > 200 else ai_text) 