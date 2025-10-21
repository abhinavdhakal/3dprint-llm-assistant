from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from design_modifier import DesignModifier

# === LLM HANDLER CONFIGURATION ===
# Choose which LLM handler to use by uncommenting ONE of the following:

# GROQ HANDLERS (FAST - 1-3 seconds):
from llm_handler_groq_unrestricted import LLMHandler  # 🔓 GROQ UNRESTRICTED: Full freedom, can add/remove features
# from llm_handler_groq_restricted import LLMHandler    # 🔒 GROQ RESTRICTED: Only ±20% parameter changes, safe mode

# OLLAMA HANDLERS (SLOW - 30-76 seconds):
# from llm_handler import LLMHandler                    # MODERATE: Balanced modifications
# from llm_handler_advanced import LLMHandler           # ADVANCED: Auto-chooses between parameter/full SCAD mode
# from llm_handler_restricted import LLMHandler         # RESTRICTED: Only ±20% adjustments
# ===================================

import os
import shutil
import json
from datetime import datetime
import zipfile
import io
import tempfile

app = Flask(__name__)
CORS(app)

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DESIGNS_DIR = os.path.join(BASE_DIR, '..', 'designs')
MODELS_DIR = os.path.join(BASE_DIR, '..', 'models')
VERSIONS_DIR = os.path.join(MODELS_DIR, 'versions')  # Store version backups
SCAD_VERSIONS_DIR = os.path.join(MODELS_DIR, 'versions', 'scad')  # Store SCAD version backups
STATE_FILE = os.path.join(MODELS_DIR, 'design_state.json')  # Track current state
HISTORY_FILE = os.path.join(MODELS_DIR, 'history.json')  # Track version history

# Ensure directories exist
os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(VERSIONS_DIR, exist_ok=True)
os.makedirs(SCAD_VERSIONS_DIR, exist_ok=True)
os.makedirs(DESIGNS_DIR, exist_ok=True)

print("Starting Concrete Design Assistant...")
print(f"Models directory: {MODELS_DIR}")
print(f"Versions directory: {VERSIONS_DIR}")
print(f"SCAD Versions directory: {SCAD_VERSIONS_DIR}")
print(f"Versions directory: {VERSIONS_DIR}")
print(f"Designs directory: {DESIGNS_DIR}")

# Initialize modifier as None (will be set when SCAD is imported)
modifier = None

# Check if there's an existing SCAD file
existing_scad_files = [f for f in os.listdir(DESIGNS_DIR) if f.endswith('.scad')] if os.path.exists(DESIGNS_DIR) else []
if existing_scad_files:
    # Load the first SCAD file found
    scad_file = os.path.join(DESIGNS_DIR, existing_scad_files[0])
    try:
        modifier = DesignModifier(scad_file)
        print(f"✅ Loaded existing design: {existing_scad_files[0]}")
    except Exception as e:
        print(f"⚠️ Could not load existing SCAD file: {e}")
        modifier = None
else:
    print("📭 No project loaded - waiting for SCAD import")

llm = LLMHandler()

# Version counter for backend tracking
version_counter = 0

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

def save_design_state():
    """Save current design state to file"""
    if modifier is None:
        return  # Nothing to save if no project loaded
    
    state = {
        'version': version_counter,
        'timestamp': datetime.now().isoformat(),
        'parameters': modifier.current_params,  # Parameters for display
        'scad_file': os.path.basename(modifier.scad_file)
    }
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)
    print(f"💾 Design state saved (version {version_counter})")

def load_design_state():
    """Load design state from file"""
    global version_counter
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                state = json.load(f)
                version_counter = state.get('version', 0)
                print(f"📂 Loaded design state (version {version_counter})")
                return state
        except Exception as e:
            print(f"Warning: Could not load design state: {e}")
    return None

def backup_version(stl_path, description="backup"):
    """Create a backup of the current STL and SCAD with version number and save to history"""
    global version_counter
    version_counter += 1
    
    # Clean up the description
    clean_desc = clean_description(description)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    desc_safe = clean_desc.replace(' ', '_').replace('/', '_')[:30]
    
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
    
    save_design_state()
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
    
    print(f"📚 Added to history: v{version_num} - {description}")

def load_history():
    """Load version history from file"""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load history: {e}")
    return []

# Load existing state on startup
load_design_state()

# Generate initial STL if needed (only if modifier is loaded)
initial_stl = os.path.join(MODELS_DIR, 'current.stl')
if modifier is not None and not os.path.exists(initial_stl):
    print("Generating initial STL...")
    success = modifier.generate_stl(initial_stl)
    if success:
        print("Initial STL generated successfully")
        backup_version(initial_stl, "initial_design")
    else:
        print("Warning: Could not generate initial STL")

@app.route('/test')
def test():
    return "Backend is working!"

@app.route('/api/history', methods=['GET'])
def get_history():
    """Get version history"""
    try:
        history = load_history()
        return jsonify({
            'success': True,
            'history': history,
            'count': len(history)
        })
    except Exception as e:
        print(f"Error getting history: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/current-design', methods=['GET'])
def get_current_design():
    """Get current design parameters and STL"""
    try:
        # Check if modifier exists (project loaded)
        if modifier is None:
            return jsonify({
                'status': 'no_project',
                'message': 'No project loaded. Please import a SCAD file.',
                'parameters': {},
                'analysis': {}
            }), 200
        
        # No longer extracting parameters - working with full SCAD
        analysis = modifier.analyze_stl(initial_stl) if os.path.exists(initial_stl) else {}
        
        return jsonify({
            'parameters': modifier.current_params,  # Parameters for display
            'analysis': analysis,
            'stl_path': '/api/models/current.stl'
        })
    except Exception as e:
        print(f"Error in get_current_design: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/update-version-description', methods=['POST'])
def update_version_description():
    """Update the description of a specific version in history"""
    try:
        data = request.json
        version_id = data.get('version_id')  # e.g., "v0001_1234567890"
        new_description = data.get('description')
        
        if not version_id or not new_description:
            return jsonify({
                'status': 'error',
                'message': 'version_id and description are required'
            }), 400
        
        history = load_history()
        updated = False
        
        for entry in history:
            if entry.get('id') == version_id:
                entry['description'] = new_description
                updated = True
                break
        
        if updated:
            with open(HISTORY_FILE, 'w') as f:
                json.dump(history, f, indent=2)
            print(f"📝 Updated version {version_id} description to: {new_description}")
            return jsonify({
                'status': 'success',
                'message': 'Version description updated'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': f'Version {version_id} not found'
            }), 404
            
    except Exception as e:
        print(f"Error updating version description: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/modify', methods=['POST'])
def modify_design():
    """Process operator's modification request"""
    try:
        # Check if modifier exists (project loaded)
        if modifier is None:
            return jsonify({
                'status': 'error',
                'message': 'No project loaded. Please import a SCAD file first.'
            }), 400
        
        data = request.json
        user_input = data.get('input', '')
        
        print(f"Received modification request: {user_input}")
        
        # Store old parameters before modification
        old_params = modifier.current_params.copy()
        
        # Step 1: LLM interprets the request
        interpretation = llm.interpret_modification(
            user_input, 
            full_scad_content=modifier.full_scad_content,
            current_params=modifier.current_params
        )
        
        print(f"LLM interpretation: {interpretation}")
        
        # Step 2: Check if clarification needed
        if interpretation.get('needs_clarification'):
            return jsonify({
                'status': 'clarification_needed',
                'question': interpretation.get('clarification_question'),
                'understood': interpretation.get('understood')
            })
        
        # Step 3: Apply modifications (detect mode based on response)
        modifications_dict = interpretation.get('modifications')
        new_scad_code = interpretation.get('new_scad_code')
        
        if modifications_dict and not new_scad_code:
            # PARAMETER MODE (restricted handler)
            print(f"📝 Applying parameter modifications: {modifications_dict}")
            success = modifier.apply_modifications(modifications_dict)
            
            if not success:
                return jsonify({
                    'status': 'error',
                    'message': 'Failed to apply parameter modifications'
                }), 500
            
            print(f"✅ Parameters modified successfully")
            
        elif new_scad_code:
            # FULL SCAD MODE (advanced handler)
            print(f"📝 Applying SCAD code modification...")
            success = modifier.apply_scad_modification(new_scad_code)
            
            if not success:
                return jsonify({
                    'status': 'error',
                    'message': 'Failed to apply SCAD code modifications'
                }), 500
            
            print(f"✅ SCAD code modified successfully")
        else:
            return jsonify({
                'status': 'error',
                'message': 'LLM did not provide modifications or SCAD code'
            }), 500
        
        # Step 4: Generate new STL
        modified_stl = os.path.join(MODELS_DIR, 'modified.stl')
        success = modifier.generate_stl(modified_stl)
        
        if not success:
            return jsonify({
                'status': 'error',
                'message': 'Failed to generate modified design'
            }), 500
        
        # Step 5: Analyze new design
        analysis = modifier.analyze_stl(modified_stl)
        
        # Step 6: Detect parameter changes for display
        # Use pending_params if available (shows modified design parameters)
        new_params = modifier.pending_params if modifier.pending_params else modifier.current_params
        modifications = modifications_dict if modifications_dict else {}
        
        # If full SCAD mode, detect changes
        if not modifications_dict:
            for key, new_value in new_params.items():
                old_value = old_params.get(key)
                if old_value != new_value:
                    modifications[key] = new_value
        
        return jsonify({
            'status': 'success',
            'understood': interpretation.get('understood'),
            'reasoning': interpretation.get('reasoning'),
            'changes_summary': interpretation.get('changes_summary', []) if new_scad_code else [f"Modified {len(modifications)} parameters"],
            'modifications': modifications,  # What parameters changed
            'new_parameters': new_params,  # All parameters after modification
            'analysis': analysis,
            'stl_path': '/api/models/modified.stl'
        })
    
    except Exception as e:
        print(f"Error in modify_design: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/approve', methods=['POST'])
def approve_design():
    """Operator approves the modified design"""
    try:
        data = request.json or {}
        description = data.get('description', 'design_approved')
        
        modified_stl = os.path.join(MODELS_DIR, 'modified.stl')
        current_stl = os.path.join(MODELS_DIR, 'current.stl')
        
        if os.path.exists(modified_stl):
            # IMPORTANT: Save pending SCAD changes to actual file
            if modifier.pending_scad_content is not None:
                print(f"💾 Saving approved SCAD modifications to {modifier.scad_file}")
                with open(modifier.scad_file, 'w') as f:
                    f.write(modifier.pending_scad_content)
                
                # Update current state
                modifier.full_scad_content = modifier.pending_scad_content
                modifier.current_params = modifier.pending_params or modifier.extract_parameters()
                
                # Clear pending state
                modifier.pending_scad_content = None
                modifier.pending_params = None
                
                print(f"✅ SCAD file updated with approved changes")
            
            # Backup the approved version
            backup_path = backup_version(modified_stl, description)
            
            # Make it current
            shutil.copy(modified_stl, current_stl)
            
            print(f"✅ Design approved: {description}")
            
            return jsonify({
                'status': 'approved',
                'message': 'Design approved and set as current',
                'version': version_counter,
                'backup': os.path.basename(backup_path)
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'No modified design to approve'
            }), 400
    except Exception as e:
        print(f"Error in approve_design: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/reject', methods=['POST'])
def reject_design():
    """Operator rejects the modified design"""
    try:
        # Clear pending modifications
        if modifier.pending_scad_content is not None:
            print(f"🚫 Rejecting modifications - clearing pending state")
            modifier.pending_scad_content = None
            modifier.pending_params = None
            print(f"✅ Pending modifications discarded")
        
        return jsonify({
            'status': 'rejected',
            'message': 'Design modifications rejected and discarded'
        })
    except Exception as e:
        print(f"Error in reject_design: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/restore-version', methods=['POST'])
def restore_version():
    """Restore design from backed-up SCAD file (for undo/redo)"""
    try:
        data = request.json
        version_num = data.get('version')
        
        if not version_num:
            return jsonify({
                'status': 'error',
                'message': 'No version number provided'
            }), 400
        
        # Find the SCAD backup file for this version
        scad_pattern = f"v{version_num:04d}_*.scad"
        scad_files = [f for f in os.listdir(SCAD_VERSIONS_DIR) if f.startswith(f"v{version_num:04d}_")]
        
        if not scad_files:
            return jsonify({
                'status': 'error',
                'message': f'No SCAD backup found for version {version_num}'
            }), 404
        
        # Get the backed-up SCAD file
        scad_backup_path = os.path.join(SCAD_VERSIONS_DIR, scad_files[0])
        
        print(f"↩️  Restoring version {version_num} from {scad_files[0]}")
        
        # Read the backed-up SCAD content
        with open(scad_backup_path, 'r') as f:
            restored_scad = f.read()
        
        # Write to current SCAD file
        with open(modifier.scad_file, 'w') as f:
            f.write(restored_scad)
        
        # Update modifier state
        modifier.full_scad_content = restored_scad
        modifier.current_params = modifier.extract_parameters()
        modifier.pending_scad_content = None
        modifier.pending_params = None
        
        print(f"   ✅ SCAD file restored")
        
        # Regenerate current STL from restored SCAD
        current_stl = os.path.join(MODELS_DIR, 'current.stl')
        success = modifier.generate_stl(current_stl)
        
        if not success:
            return jsonify({
                'status': 'error',
                'message': 'Failed to generate STL from restored SCAD'
            }), 500
        
        # Analyze restored design
        analysis = modifier.analyze_stl(current_stl)
        
        print(f"   ✅ Version {version_num} restored successfully")
        
        return jsonify({
            'status': 'success',
            'message': f'Version {version_num} restored successfully',
            'parameters': modifier.current_params,
            'analysis': analysis,
            'version': version_num
        })
        
    except Exception as e:
        print(f"Error in restore_version: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/update-parameters', methods=['POST'])
def update_parameters():
    """Update design parameters and regenerate STL (for undo/redo)"""
    try:
        data = request.json
        parameters = data.get('parameters', {})
        description = data.get('description', 'parameters_updated')
        create_backup = data.get('create_backup', False)  # Only create backup if explicitly requested
        
        if not parameters:
            return jsonify({
                'status': 'error',
                'message': 'No parameters provided'
            }), 400
        
        print(f"🔄 Updating parameters: {description} (backup: {create_backup})")
        print(f"   New parameters: {parameters}")
        
        # Apply modifications to SCAD file
        modifier.apply_modifications(parameters)
        print(f"   ✅ Parameters applied to SCAD file")
        
        # Regenerate current STL with updated parameters
        current_stl = os.path.join(MODELS_DIR, 'current.stl')
        success = modifier.generate_stl(current_stl)
        
        if not success:
            return jsonify({
                'status': 'error',
                'message': 'Failed to generate STL with updated parameters'
            }), 500
        
        # Create backup only if requested (for undo/redo we want to track versions)
        backup_path = None
        if create_backup:
            backup_path = backup_version(current_stl, description)
        
        # Analyze new design
        analysis = modifier.analyze_stl(current_stl)
        
        return jsonify({
            'status': 'success',
            'message': 'Parameters updated successfully',
            'parameters': modifier.current_params,  # Parameters for display
            'analysis': analysis,
            'version': version_counter if create_backup else None,
            'backup': os.path.basename(backup_path) if backup_path else None,
            'stl_path': '/models/current.stl'
        })
    
    except Exception as e:
        print(f"Error in update_parameters: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/upload-scad', methods=['POST'])
def upload_scad():
    """Upload and parse a SCAD file"""
    try:
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({
                'status': 'error',
                'message': 'No file uploaded'
            }), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({
                'status': 'error',
                'message': 'No file selected'
            }), 400
        
        if not file.filename.endswith('.scad'):
            return jsonify({
                'status': 'error',
                'message': 'File must be a .scad file'
            }), 400
        
        # Save uploaded file with original filename
        # This tracks which model we're working on
        original_filename = file.filename
        uploaded_scad = os.path.join(DESIGNS_DIR, original_filename)
        file.save(uploaded_scad)
        
        print(f"SCAD file uploaded: {uploaded_scad}")
        
        # Reset version counter for new file (like "New File" in CAD software)
        global version_counter
        version_counter = 0
        
        # Clear history for new file
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'w') as f:
                json.dump([], f)
        
        # Clear all version files for new file
        if os.path.exists(VERSIONS_DIR):
            for version_file in os.listdir(VERSIONS_DIR):
                if version_file.endswith('.stl'):
                    os.remove(os.path.join(VERSIONS_DIR, version_file))
            print(f"✨ Cleared version history for new file")
        
        # Create a new DesignModifier with the uploaded file
        uploaded_modifier = DesignModifier(uploaded_scad)
        
        # Generate STL from the uploaded SCAD
        uploaded_stl = os.path.join(MODELS_DIR, 'current.stl')
        success = uploaded_modifier.generate_stl(uploaded_stl)
        
        if not success:
            return jsonify({
                'status': 'error',
                'message': 'Failed to generate STL from uploaded SCAD file'
            }), 500
        
        # Analyze the generated STL
        analysis = uploaded_modifier.analyze_stl(uploaded_stl)
        
        # Update the global modifier to use the uploaded design
        global modifier
        modifier = uploaded_modifier
        
        # Create initial version (v0001) for the imported design
        # This allows immediate use of version history/undo/redo
        base_name = os.path.splitext(original_filename)[0]
        initial_description = f"Original design: {base_name}"
        backup_path = backup_version(uploaded_stl, initial_description)
        
        print(f"✅ Created initial version: v{version_counter:04d} - {initial_description}")
        
        return jsonify({
            'status': 'success',
            'message': f'SCAD file "{original_filename}" imported successfully. Version history reset.',
            'parameters': uploaded_modifier.current_params,  # Parameters for display
            'analysis': analysis,
            'stl_path': '/models/current.stl',
            'filename': original_filename,
            'version_reset': True,  # Signal to frontend to clear history
            'initial_version': version_counter,  # Let frontend know initial version was created
            'initial_backup': os.path.basename(backup_path)
        })
    
    except Exception as e:
        print(f"Error in upload_scad: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/clear-project', methods=['POST'])
def clear_project():
    """Clear all project data - backend equivalent of New Project"""
    try:
        global version_counter, modifier
        
        # Reset version counter
        version_counter = 0
        
        # Clear history
        if os.path.exists(HISTORY_FILE):
            os.remove(HISTORY_FILE)
        
        # Clear design state
        if os.path.exists(STATE_FILE):
            os.remove(STATE_FILE)
        
        # Clear all version files
        if os.path.exists(VERSIONS_DIR):
            for version_file in os.listdir(VERSIONS_DIR):
                if version_file.endswith('.stl'):
                    os.remove(os.path.join(VERSIONS_DIR, version_file))
        
        # Clear all SCAD version files
        if os.path.exists(SCAD_VERSIONS_DIR):
            for scad_version_file in os.listdir(SCAD_VERSIONS_DIR):
                if scad_version_file.endswith('.scad'):
                    os.remove(os.path.join(SCAD_VERSIONS_DIR, scad_version_file))
                    print(f"🗑️ Removed SCAD version: {scad_version_file}")
        
        # Clear current and modified STL files
        current_stl = os.path.join(MODELS_DIR, 'current.stl')
        modified_stl = os.path.join(MODELS_DIR, 'modified.stl')
        if os.path.exists(current_stl):
            os.remove(current_stl)
        if os.path.exists(modified_stl):
            os.remove(modified_stl)
        
        # Clear all SCAD files in designs folder
        if os.path.exists(DESIGNS_DIR):
            for scad_file in os.listdir(DESIGNS_DIR):
                if scad_file.endswith('.scad'):
                    scad_path = os.path.join(DESIGNS_DIR, scad_file)
                    os.remove(scad_path)
                    print(f"🗑️ Removed SCAD file: {scad_file}")
        
        # Reset modifier to None
        modifier = None
        
        print("🗑️ Project cleared - all backend data removed")
        
        return jsonify({
            'status': 'success',
            'message': 'Project cleared successfully'
        })
    
    except Exception as e:
        print(f"Error clearing project: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/models/<filename>')
def serve_model(filename):
    """Serve STL files"""
    try:
        file_path = os.path.join(MODELS_DIR, filename)
        if os.path.exists(file_path):
            return send_file(file_path, mimetype='model/stl')
        return "File not found", 404
    except Exception as e:
        print(f"Error serving model: {e}")
        return str(e), 500

@app.route('/api/download-scad-version/<version_num>', methods=['GET'])
def download_scad_version(version_num):
    """Download a specific SCAD version from history"""
    try:
        # Find the SCAD file matching this version number
        if not os.path.exists(SCAD_VERSIONS_DIR):
            return "SCAD versions directory not found", 404
        
        # Look for files starting with the version number
        version_prefix = f"v{int(version_num):04d}_"
        matching_files = [f for f in os.listdir(SCAD_VERSIONS_DIR) 
                         if f.startswith(version_prefix) and f.endswith('.scad')]
        
        if not matching_files:
            return f"SCAD version {version_num} not found", 404
        
        # Use the first matching file (should only be one)
        scad_file = matching_files[0]
        file_path = os.path.join(SCAD_VERSIONS_DIR, scad_file)
        
        if os.path.exists(file_path):
            return send_file(
                file_path,
                mimetype='application/octet-stream',
                as_attachment=True,
                download_name=scad_file
            )
        
        return "File not found", 404
    except Exception as e:
        print(f"Error downloading SCAD version: {e}")
        import traceback
        traceback.print_exc()
        return str(e), 500

@app.route('/api/download-current-scad', methods=['GET'])
def download_current_scad():
    """Download the current SCAD file"""
    try:
        if not modifier or not os.path.exists(modifier.scad_file):
            return "No SCAD file loaded", 404
        
        scad_filename = os.path.basename(modifier.scad_file)
        
        return send_file(
            modifier.scad_file,
            mimetype='application/octet-stream',
            as_attachment=True,
            download_name=scad_filename
        )
    except Exception as e:
        print(f"Error downloading current SCAD: {e}")
        import traceback
        traceback.print_exc()
        return str(e), 500

@app.route('/api/save-project', methods=['POST'])
def save_project():
    """Save entire project as a zip file"""
    try:
        data = request.json or {}
        project_name = data.get('name', 'project')
        
        # Create timestamp for unique filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        zip_filename = f"{project_name}_{timestamp}.zip"
        
        # Create in-memory zip file
        memory_file = io.BytesIO()
        
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add manifest with project metadata
            manifest = {
                'name': project_name,
                'created': timestamp,
                'version_count': version_counter,
                'scad_file': os.path.basename(modifier.scad_file) if modifier else 'unknown.scad'
            }
            zf.writestr('manifest.json', json.dumps(manifest, indent=2))
            
            # Add current SCAD file
            if modifier and os.path.exists(modifier.scad_file):
                scad_name = os.path.basename(modifier.scad_file)
                zf.write(modifier.scad_file, f'design/{scad_name}')
            
            # Add current STL
            current_stl = os.path.join(MODELS_DIR, 'current.stl')
            if os.path.exists(current_stl):
                zf.write(current_stl, 'models/current.stl')
            
            # Add modified STL if exists
            modified_stl = os.path.join(MODELS_DIR, 'modified.stl')
            if os.path.exists(modified_stl):
                zf.write(modified_stl, 'models/modified.stl')
            
            # Add history.json
            if os.path.exists(HISTORY_FILE):
                zf.write(HISTORY_FILE, 'history.json')
            
            # Add all version STL files
            if os.path.exists(VERSIONS_DIR):
                for version_file in os.listdir(VERSIONS_DIR):
                    if version_file.endswith('.stl'):
                        version_path = os.path.join(VERSIONS_DIR, version_file)
                        zf.write(version_path, f'versions/{version_file}')
            
            # Add all SCAD version files
            if os.path.exists(SCAD_VERSIONS_DIR):
                for scad_version_file in os.listdir(SCAD_VERSIONS_DIR):
                    if scad_version_file.endswith('.scad'):
                        scad_version_path = os.path.join(SCAD_VERSIONS_DIR, scad_version_file)
                        zf.write(scad_version_path, f'versions/scad/{scad_version_file}')
        
        # Seek to beginning of file
        memory_file.seek(0)
        
        print(f"✅ Project saved: {zip_filename} (v{version_counter})")
        
        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=zip_filename
        )
    
    except Exception as e:
        print(f"Error saving project: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/load-project', methods=['POST'])
def load_project():
    """Load project from uploaded zip file"""
    try:
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({
                'status': 'error',
                'message': 'No file uploaded'
            }), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({
                'status': 'error',
                'message': 'No file selected'
            }), 400
        
        if not file.filename.endswith('.zip'):
            return jsonify({
                'status': 'error',
                'message': 'File must be a .zip file'
            }), 400
        
        # Create temporary file to save upload
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp:
            file.save(tmp.name)
            tmp_path = tmp.name
        
        try:
            # Extract zip file
            with zipfile.ZipFile(tmp_path, 'r') as zf:
                # Read manifest
                manifest = None
                if 'manifest.json' in zf.namelist():
                    manifest = json.loads(zf.read('manifest.json'))
                    print(f"Loading project: {manifest.get('name', 'unknown')}")
                
                # Clear existing versions
                if os.path.exists(VERSIONS_DIR):
                    shutil.rmtree(VERSIONS_DIR)
                os.makedirs(VERSIONS_DIR, exist_ok=True)
                os.makedirs(SCAD_VERSIONS_DIR, exist_ok=True)
                
                # Extract all files
                for item in zf.namelist():
                    if item.startswith('design/'):
                        # Extract SCAD file
                        scad_name = os.path.basename(item)
                        target = os.path.join(DESIGNS_DIR, scad_name)
                        with open(target, 'wb') as f:
                            f.write(zf.read(item))
                        
                        # Update global modifier to use this SCAD
                        global modifier
                        modifier = DesignModifier(target)
                        
                    elif item.startswith('models/'):
                        # Extract current/modified STL
                        stl_name = os.path.basename(item)
                        target = os.path.join(MODELS_DIR, stl_name)
                        with open(target, 'wb') as f:
                            f.write(zf.read(item))
                    
                    elif item.startswith('versions/scad/'):
                        # Extract SCAD version
                        scad_version_name = os.path.basename(item)
                        target = os.path.join(SCAD_VERSIONS_DIR, scad_version_name)
                        with open(target, 'wb') as f:
                            f.write(zf.read(item))
                    
                    elif item.startswith('versions/') and not item.startswith('versions/scad/'):
                        # Extract STL version
                        version_name = os.path.basename(item)
                        if version_name:  # Skip directory entries
                            target = os.path.join(VERSIONS_DIR, version_name)
                            with open(target, 'wb') as f:
                                f.write(zf.read(item))
                    
                    elif item == 'history.json':
                        # Extract history
                        with open(HISTORY_FILE, 'wb') as f:
                            f.write(zf.read(item))
                
                # Update version counter from manifest
                global version_counter
                if manifest and 'version_count' in manifest:
                    version_counter = manifest['version_count']
                
                # Analyze current STL
                current_stl = os.path.join(MODELS_DIR, 'current.stl')
                analysis = None
                if os.path.exists(current_stl):
                    analysis = modifier.analyze_stl(current_stl)
                
                print(f"✅ Project loaded: {manifest.get('name', 'unknown')} (v{version_counter})")
                
                return jsonify({
                    'status': 'success',
                    'message': 'Project loaded successfully',
                    'manifest': manifest,
                    'parameters': modifier.current_params if modifier else {},  # Parameters for display
                    'analysis': analysis,
                    'version_count': version_counter,
                    'stl_path': '/models/current.stl'
                })
        
        finally:
            # Clean up temp file
            os.unlink(tmp_path)
    
    except Exception as e:
        print(f"Error loading project: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("Flask app starting...")
    app.run(debug=True, host='127.0.0.1', port=5000)