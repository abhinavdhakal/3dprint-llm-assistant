"""
Flask route handlers for the Concrete Design Assistant
"""
from flask import request, jsonify, send_file
import os
import json
import shutil
import zipfile
import io
import tempfile
from datetime import datetime

from config import (
    DESIGNS_DIR, MODELS_DIR, VERSIONS_DIR, 
    SCAD_VERSIONS_DIR, HISTORY_FILE
)
from state_manager import (
    backup_version, load_history, save_design_state,
    clean_description
)


def register_routes(app, modifier_ref, llm, version_counter_ref):
    """Register all Flask routes with the app
    
    Args:
        app: Flask app instance
        modifier_ref: Dict with 'current' key holding DesignModifier instance
        llm: LLMHandler instance
        version_counter_ref: Dict with 'current' key holding version counter
    """
    
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
            modifier = modifier_ref['current']
            initial_stl = os.path.join(MODELS_DIR, 'current.stl')
            
            # Check if modifier exists (project loaded)
            if modifier is None:
                return jsonify({
                    'status': 'no_project',
                    'message': 'No project loaded. Please import a SCAD file.',
                    'parameters': {},
                    'analysis': {}
                }), 200
            
            analysis = modifier.analyze_stl(initial_stl) if os.path.exists(initial_stl) else {}
            
            return jsonify({
                'parameters': modifier.current_params,
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
            version_id = data.get('version_id')
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
            modifier = modifier_ref['current']
            
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
                'modifications': modifications,
                'new_parameters': new_params,
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
            modifier = modifier_ref['current']
            data = request.json or {}
            description = data.get('description', 'design_approved')
            
            modified_stl = os.path.join(MODELS_DIR, 'modified.stl')
            current_stl = os.path.join(MODELS_DIR, 'current.stl')
            
            if os.path.exists(modified_stl):
                # Save pending SCAD changes to actual file
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
                backup_path = backup_version(modified_stl, description, modifier)
                
                # Make it current
                shutil.copy(modified_stl, current_stl)
                
                print(f"✅ Design approved: {description}")
                
                # Update version counter reference
                from state_manager import version_counter
                version_counter_ref['current'] = version_counter
                
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
            modifier = modifier_ref['current']
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
            modifier = modifier_ref['current']
            data = request.json
            version_num = data.get('version')
            
            if not version_num:
                return jsonify({
                    'status': 'error',
                    'message': 'No version number provided'
                }), 400
            
            # Find the SCAD backup file for this version
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
            modifier = modifier_ref['current']
            data = request.json
            parameters = data.get('parameters', {})
            description = data.get('description', 'parameters_updated')
            create_backup = data.get('create_backup', False)
            
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
            
            # Create backup only if requested
            backup_path = None
            if create_backup:
                backup_path = backup_version(current_stl, description, modifier)
                from state_manager import version_counter
                version_counter_ref['current'] = version_counter
            
            # Analyze new design
            analysis = modifier.analyze_stl(current_stl)
            
            return jsonify({
                'status': 'success',
                'message': 'Parameters updated successfully',
                'parameters': modifier.current_params,
                'analysis': analysis,
                'version': version_counter_ref['current'] if create_backup else None,
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
            from design_modifier import DesignModifier
            
            # Check if file was uploaded
            if 'file' not in request.files:
                return jsonify({
                    'status': 'error',
                    'message': 'No file uploaded'
                }), 400
            
            file = request.files['file']
            
            if file.filename == '' or not file.filename.endswith('.scad'):
                return jsonify({
                    'status': 'error',
                    'message': 'File must be a .scad file'
                }), 400
            
            # Save uploaded file
            original_filename = file.filename
            uploaded_scad = os.path.join(DESIGNS_DIR, original_filename)
            file.save(uploaded_scad)
            
            print(f"SCAD file uploaded: {uploaded_scad}")
            
            # Reset version counter for new file
            import state_manager
            state_manager.version_counter = 0
            version_counter_ref['current'] = 0
            
            # Clear history for new file
            if os.path.exists(HISTORY_FILE):
                with open(HISTORY_FILE, 'w') as f:
                    json.dump([], f)
            
            # Clear all version files
            if os.path.exists(VERSIONS_DIR):
                for version_file in os.listdir(VERSIONS_DIR):
                    if version_file.endswith('.stl'):
                        os.remove(os.path.join(VERSIONS_DIR, version_file))
                print(f"✨ Cleared version history for new file")
            
            # Create a new DesignModifier
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
            
            # Update the global modifier
            modifier_ref['current'] = uploaded_modifier
            
            # Create initial version
            base_name = os.path.splitext(original_filename)[0]
            initial_description = f"Original design: {base_name}"
            backup_path = backup_version(uploaded_stl, initial_description, uploaded_modifier)
            
            from state_manager import version_counter
            version_counter_ref['current'] = version_counter
            
            print(f"✅ Created initial version: v{version_counter:04d} - {initial_description}")
            
            return jsonify({
                'status': 'success',
                'message': f'SCAD file "{original_filename}" imported successfully. Version history reset.',
                'parameters': uploaded_modifier.current_params,
                'analysis': analysis,
                'stl_path': '/models/current.stl',
                'filename': original_filename,
                'version_reset': True,
                'initial_version': version_counter,
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
            import state_manager
            
            # Reset version counter
            state_manager.version_counter = 0
            version_counter_ref['current'] = 0
            
            # Clear history and state files
            for file_path in [HISTORY_FILE, os.path.join(MODELS_DIR, 'design_state.json')]:
                if os.path.exists(file_path):
                    os.remove(file_path)
            
            # Clear all version files
            for dir_path in [VERSIONS_DIR, SCAD_VERSIONS_DIR]:
                if os.path.exists(dir_path):
                    for version_file in os.listdir(dir_path):
                        os.remove(os.path.join(dir_path, version_file))
            
            # Clear current and modified STL files
            for stl_file in ['current.stl', 'modified.stl']:
                stl_path = os.path.join(MODELS_DIR, stl_file)
                if os.path.exists(stl_path):
                    os.remove(stl_path)
            
            # Clear all SCAD files in designs folder
            if os.path.exists(DESIGNS_DIR):
                for scad_file in os.listdir(DESIGNS_DIR):
                    if scad_file.endswith('.scad'):
                        os.remove(os.path.join(DESIGNS_DIR, scad_file))
                        print(f"🗑️ Removed SCAD file: {scad_file}")
            
            # Reset modifier to None
            modifier_ref['current'] = None
            
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
            if not os.path.exists(SCAD_VERSIONS_DIR):
                return "SCAD versions directory not found", 404
            
            version_prefix = f"v{int(version_num):04d}_"
            matching_files = [f for f in os.listdir(SCAD_VERSIONS_DIR) 
                             if f.startswith(version_prefix) and f.endswith('.scad')]
            
            if not matching_files:
                return f"SCAD version {version_num} not found", 404
            
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
            modifier = modifier_ref['current']
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
            modifier = modifier_ref['current']
            data = request.json or {}
            project_name = data.get('name', 'project')
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            zip_filename = f"{project_name}_{timestamp}.zip"
            
            memory_file = io.BytesIO()
            
            with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
                # Add manifest
                manifest = {
                    'name': project_name,
                    'created': timestamp,
                    'version_count': version_counter_ref['current'],
                    'scad_file': os.path.basename(modifier.scad_file) if modifier else 'unknown.scad'
                }
                zf.writestr('manifest.json', json.dumps(manifest, indent=2))
                
                # Add current SCAD file
                if modifier and os.path.exists(modifier.scad_file):
                    scad_name = os.path.basename(modifier.scad_file)
                    zf.write(modifier.scad_file, f'design/{scad_name}')
                
                # Add STL files
                for stl_name in ['current.stl', 'modified.stl']:
                    stl_path = os.path.join(MODELS_DIR, stl_name)
                    if os.path.exists(stl_path):
                        zf.write(stl_path, f'models/{stl_name}')
                
                # Add history
                if os.path.exists(HISTORY_FILE):
                    zf.write(HISTORY_FILE, 'history.json')
                
                # Add version STL files
                if os.path.exists(VERSIONS_DIR):
                    for version_file in os.listdir(VERSIONS_DIR):
                        if version_file.endswith('.stl'):
                            version_path = os.path.join(VERSIONS_DIR, version_file)
                            zf.write(version_path, f'versions/{version_file}')
                
                # Add SCAD version files
                if os.path.exists(SCAD_VERSIONS_DIR):
                    for scad_version_file in os.listdir(SCAD_VERSIONS_DIR):
                        if scad_version_file.endswith('.scad'):
                            scad_version_path = os.path.join(SCAD_VERSIONS_DIR, scad_version_file)
                            zf.write(scad_version_path, f'versions/scad/{scad_version_file}')
            
            memory_file.seek(0)
            
            print(f"✅ Project saved: {zip_filename} (v{version_counter_ref['current']})")
            
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
            from design_modifier import DesignModifier
            import state_manager
            
            if 'file' not in request.files:
                return jsonify({'status': 'error', 'message': 'No file uploaded'}), 400
            
            file = request.files['file']
            
            if file.filename == '' or not file.filename.endswith('.zip'):
                return jsonify({'status': 'error', 'message': 'File must be a .zip file'}), 400
            
            # Create temporary file
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
                            scad_name = os.path.basename(item)
                            target = os.path.join(DESIGNS_DIR, scad_name)
                            with open(target, 'wb') as f:
                                f.write(zf.read(item))
                            modifier_ref['current'] = DesignModifier(target)
                            
                        elif item.startswith('models/'):
                            stl_name = os.path.basename(item)
                            target = os.path.join(MODELS_DIR, stl_name)
                            with open(target, 'wb') as f:
                                f.write(zf.read(item))
                        
                        elif item.startswith('versions/scad/'):
                            scad_version_name = os.path.basename(item)
                            target = os.path.join(SCAD_VERSIONS_DIR, scad_version_name)
                            with open(target, 'wb') as f:
                                f.write(zf.read(item))
                        
                        elif item.startswith('versions/') and not item.startswith('versions/scad/'):
                            version_name = os.path.basename(item)
                            if version_name:
                                target = os.path.join(VERSIONS_DIR, version_name)
                                with open(target, 'wb') as f:
                                    f.write(zf.read(item))
                        
                        elif item == 'history.json':
                            with open(HISTORY_FILE, 'wb') as f:
                                f.write(zf.read(item))
                    
                    # Update version counter
                    if manifest and 'version_count' in manifest:
                        state_manager.version_counter = manifest['version_count']
                        version_counter_ref['current'] = manifest['version_count']
                    
                    # Analyze current STL
                    modifier = modifier_ref['current']
                    current_stl = os.path.join(MODELS_DIR, 'current.stl')
                    analysis = None
                    if os.path.exists(current_stl):
                        analysis = modifier.analyze_stl(current_stl)
                    
                    print(f"✅ Project loaded: {manifest.get('name', 'unknown')} (v{version_counter_ref['current']})")
                    
                    return jsonify({
                        'status': 'success',
                        'message': 'Project loaded successfully',
                        'manifest': manifest,
                        'parameters': modifier.current_params if modifier else {},
                        'analysis': analysis,
                        'version_count': version_counter_ref['current'],
                        'stl_path': '/models/current.stl'
                    })
            
            finally:
                os.unlink(tmp_path)
        
        except Exception as e:
            print(f"Error loading project: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': str(e)}), 500
