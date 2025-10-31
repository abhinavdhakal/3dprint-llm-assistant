"""
State and history management for design versions
"""
import os
import json
import shutil
from datetime import datetime
from config import (
    STATE_FILE, HISTORY_FILE, VERSIONS_DIR, 
    SCAD_VERSIONS_DIR
)

# Global version counter (last saved version)
version_counter = 0

# Active version (which version is currently displayed/active)
# This can differ from version_counter when user undoes/redoes
active_version = 0

# Project name (stored for persistence across reloads)
project_name = None


def clean_description(desc):
    """Clean up verbose LLM descriptions for concise version history"""
    if not desc:
        return "Modified"
    
    # Remove common verbose prefixes
    prefixes_to_remove = [
        "The operator wants to ",
        "The user wants to ",
        "The request is to ",
        "Operator requested to ",
        "User requested to ",
    ]
    
    cleaned = desc
    for prefix in prefixes_to_remove:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):]
            break
    
    # Capitalize first letter
    if cleaned:
        cleaned = cleaned[0].upper() + cleaned[1:]
    
    # Limit length
    if len(cleaned) > 60:
        cleaned = cleaned[:57] + "..."
    
    return cleaned


def save_design_state(modifier):
    """Save current design state to file"""
    if modifier is None:
        return  # Nothing to save if no project loaded
    
    state = {
        'version': version_counter,
        'active_version': active_version,
        'timestamp': datetime.now().isoformat(),
        'parameters': modifier.current_params,
        'scad_file': os.path.basename(modifier.scad_file),
        'project_name': project_name  # Save project name
    }
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)
    print(f"💾 Design state saved (version {version_counter}, active: {active_version}, project: {project_name})")


def load_design_state():
    """Load design state from file"""
    global version_counter, active_version, project_name
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                state = json.load(f)
                version_counter = state.get('version', 0)
                active_version = state.get('active_version', version_counter)
                project_name = state.get('project_name', None)  # Load project name
                print(f"📂 Loaded design state (version {version_counter}, active: {active_version}, project: {project_name})")
                return state
        except Exception as e:
            print(f"Warning: Could not load design state: {e}")
    return None


def backup_version(stl_path, description, modifier):
    """Create a backup of the current STL and SCAD with version number"""
    global version_counter, active_version
    version_counter += 1
    active_version = version_counter  # When we save a new version, it becomes active
    
    # Clean up the description
    clean_desc = clean_description(description)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    desc_safe = clean_desc.replace(' ', '_').replace('/', '_')[:30]
    
    # Ensure directories exist
    os.makedirs(VERSIONS_DIR, exist_ok=True)
    os.makedirs(SCAD_VERSIONS_DIR, exist_ok=True)
    
    # Backup STL file
    backup_name = f"v{version_counter:04d}_{timestamp}_{desc_safe}.stl"
    backup_path = os.path.join(VERSIONS_DIR, backup_name)
    
    if os.path.exists(stl_path):
        shutil.copy(stl_path, backup_path)
        print(f"📦 Backed up STL version {version_counter}: {backup_name}")
    
    # Backup SCAD file (if modifier exists)
    if modifier and os.path.exists(modifier.scad_file):
        scad_backup_name = f"v{version_counter:04d}_{timestamp}_{desc_safe}.scad"
        scad_backup_path = os.path.join(SCAD_VERSIONS_DIR, scad_backup_name)
        shutil.copy(modifier.scad_file, scad_backup_path)
        print(f"📦 Backed up SCAD version {version_counter}: {scad_backup_name}")
        
        # Add to history with cleaned description
        add_to_history(version_counter, clean_desc, modifier.current_params)
    
    save_design_state(modifier)
    return backup_path


def add_to_history(version_num, description, parameters):
    """Add a version to the history file"""
    history = load_history()
    
    version_entry = {
        'id': f"v{version_num}_{int(datetime.now().timestamp() * 1000)}",
        'version': version_num,
        'timestamp': datetime.now().isoformat(),
        'description': description,
        'parameters': parameters
    }
    
    history.append(version_entry)
    
    # Keep last 50 versions
    if len(history) > 50:
        history = history[-50:]
    
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)
    
    print(f"[HISTORY] Added to history: v{version_num} - {description}")


def load_history():
    """Load version history from file"""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r') as f:
                history = json.load(f)
                print(f"[HISTORY] Loaded {len(history)} saved versions from history")
                return history
        except Exception as e:
            print(f"Warning: Could not load history: {e}")
    return []
