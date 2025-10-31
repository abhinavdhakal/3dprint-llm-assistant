"""
Project management routes - upload, save, load, clear
"""
from flask import request, jsonify, send_file
import os
import json
import shutil
import zipfile
import io
import tempfile
from datetime import datetime

from config import DESIGNS_DIR, MODELS_DIR, VERSIONS_DIR, SCAD_VERSIONS_DIR, HISTORY_FILE
from state_manager import backup_version


def register_project_routes(app, modifier_ref):
    """Register project management routes"""
    
    @app.route('/test')
    def test():
        return "Backend is working!"

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
            
            # FIRST: Clear old SCAD files BEFORE saving the new one
            # This prevents race conditions with clear-project endpoint
            if os.path.exists(DESIGNS_DIR):
                for scad_file in os.listdir(DESIGNS_DIR):
                    if scad_file.endswith('.scad'):
                        old_scad_path = os.path.join(DESIGNS_DIR, scad_file)
                        os.remove(old_scad_path)
                        print(f"🗑️  Removed old SCAD file: {scad_file}")
            
            # NOW save the new file
            file.save(uploaded_scad)
            print(f"📥 SCAD file uploaded: {uploaded_scad}")
            
            # Reset version counter for new file
            import state_manager
            state_manager.version_counter = 0
            
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
            
            # Reset version counter and project name
            state_manager.version_counter = 0
            state_manager.project_name = None
            
            # Clear history and state files
            for file_path in [HISTORY_FILE, os.path.join(MODELS_DIR, 'design_state.json')]:
                if os.path.exists(file_path):
                    os.remove(file_path)
            
            # Clear all version files
            for dir_path in [VERSIONS_DIR, SCAD_VERSIONS_DIR]:
                if os.path.exists(dir_path):
                    for item in os.listdir(dir_path):
                        item_path = os.path.join(dir_path, item)
                        if os.path.isdir(item_path):
                            shutil.rmtree(item_path)  # Remove directories recursively
                        else:
                            os.remove(item_path)  # Remove files
            
            # Clear current and modified STL files, gcode, and toolpath files
            for file_name in ['current.stl', 'modified.stl', 'print.gcode']:
                file_path = os.path.join(MODELS_DIR, file_name)
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"🗑️  Removed: {file_name}")
            
            # NOTE: We DO NOT delete SCAD files here anymore
            # The upload-scad route handles clearing old SCAD files BEFORE saving new ones
            # This prevents race conditions where clear-project deletes a file being processed
            
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

    @app.route('/api/set-project-name', methods=['POST'])
    def set_project_name():
        """Set the project name and save to state"""
        try:
            import state_manager
            data = request.json or {}
            
            project_name = data.get('project_name', '').strip()
            if not project_name:
                return jsonify({
                    'status': 'error',
                    'message': 'Project name cannot be empty'
                }), 400
            
            # Update global project name
            state_manager.project_name = project_name
            
            # Save state to persist the name
            modifier = modifier_ref['current']
            if modifier:
                state_manager.save_design_state(modifier)
            
            print(f"📝 Project name set to: {project_name}")
            
            return jsonify({
                'status': 'success',
                'message': f'Project name set to: {project_name}',
                'project_name': project_name
            })
        
        except Exception as e:
            print(f"Error setting project name: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': str(e)}), 500

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
                from state_manager import version_counter
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
            
            from state_manager import version_counter
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
                    
                    # Analyze current STL
                    modifier = modifier_ref['current']
                    current_stl = os.path.join(MODELS_DIR, 'current.stl')
                    analysis = None
                    if os.path.exists(current_stl):
                        analysis = modifier.analyze_stl(current_stl)
                    
                    from state_manager import version_counter
                    print(f"✅ Project loaded: {manifest.get('name', 'unknown')} (v{version_counter})")
                    
                    return jsonify({
                        'status': 'success',
                        'message': 'Project loaded successfully',
                        'manifest': manifest,
                        'parameters': modifier.current_params if modifier else {},
                        'analysis': analysis,
                        'version_count': version_counter,
                        'stl_path': '/models/current.stl'
                    })
            
            finally:
                os.unlink(tmp_path)
        
        except Exception as e:
            print(f"Error loading project: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': str(e)}), 500
