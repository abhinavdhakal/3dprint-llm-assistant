"""
Version management routes - history, restore, update parameters
"""
from flask import request, jsonify
import os
import json
import shutil
from config import MODELS_DIR, HISTORY_FILE, SCAD_VERSIONS_DIR, VERSIONS_DIR
from state_manager import load_history, backup_version


def register_version_routes(app, modifier_ref):
    """Register version management routes"""
    
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

    @app.route('/api/restore-version', methods=['POST'])
    def restore_version():
        """Restore design from backed-up SCAD file (for undo/redo)"""
        try:
            import state_manager
            
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
            
            # Update active version (but don't change version_counter)
            state_manager.active_version = version_num
            
            print(f"   ✅ SCAD file restored")
            print(f"   📍 Active version set to {version_num}")
            
            # Check if we have a backed-up STL for this version - use it instead of regenerating
            stl_backup_path = None
            stl_files = [f for f in os.listdir(VERSIONS_DIR) if f.startswith(f"v{version_num:04d}_") and f.endswith('.stl')]
            
            current_stl = os.path.join(MODELS_DIR, 'current.stl')
            
            if stl_files:
                # Found backed-up STL - use the LATEST one (sort by timestamp in filename)
                stl_files.sort(reverse=True)  # Sort descending to get newest first
                stl_backup_path = os.path.join(VERSIONS_DIR, stl_files[0])
                print(f"   📋 Copying backed-up STL: {stl_files[0]}")
                shutil.copy(stl_backup_path, current_stl)
                print(f"   ⚡ STL restored from backup (instant)")
            else:
                # No backup found - regenerate from SCAD
                print(f"   🔄 No STL backup found, regenerating from SCAD...")
                success = modifier.generate_stl(current_stl)
                
                if not success:
                    return jsonify({
                        'status': 'error',
                        'message': 'Failed to generate STL from restored SCAD'
                    }), 500
            
            # Analyze restored design
            analysis = modifier.analyze_stl(current_stl)
            
            # Save state with updated active_version
            from state_manager import save_design_state
            save_design_state(modifier)
            
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
            current_version = None
            if create_backup:
                backup_path = backup_version(current_stl, description, modifier)
                from state_manager import version_counter
                current_version = version_counter
            
            # Analyze new design
            analysis = modifier.analyze_stl(current_stl)
            
            return jsonify({
                'status': 'success',
                'message': 'Parameters updated successfully',
                'parameters': modifier.current_params,
                'analysis': analysis,
                'version': current_version,
                'backup': os.path.basename(backup_path) if backup_path else None,
                'stl_path': '/models/current.stl'
            })
        
        except Exception as e:
            print(f"Error in update_parameters: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': str(e)}), 500
