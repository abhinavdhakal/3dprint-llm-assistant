"""
Design modification routes - modify, approve, reject
"""
from flask import request, jsonify
import os
from config import MODELS_DIR


def register_design_routes(app, modifier_ref, llm):
    """Register design modification routes"""
    
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
            from state_manager import backup_version
            import shutil
            
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
                    
                    # ALWAYS re-extract parameters from the new content to ensure accuracy
                    modifier.current_params = modifier.extract_parameters()
                    
                    # Clear pending state
                    modifier.pending_scad_content = None
                    modifier.pending_params = None
                    
                    print(f"✅ SCAD file updated with approved changes")
                    print(f"📊 Updated parameters: {modifier.current_params}")
                
                # Backup the approved version
                backup_path = backup_version(modified_stl, description, modifier)
                
                # Make it current
                shutil.copy(modified_stl, current_stl)
                
                print(f"✅ Design approved: {description}")
                
                # Update version counter reference
                from state_manager import version_counter
                
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

    @app.route('/api/current-design', methods=['GET'])
    def get_current_design():
        """Get current design parameters and STL"""
        try:
            from state_manager import active_version, project_name
            
            modifier = modifier_ref['current']
            initial_stl = os.path.join(MODELS_DIR, 'current.stl')
            
            # Check if modifier exists (project loaded)
            if modifier is None:
                return jsonify({
                    'status': 'no_project',
                    'message': 'No project loaded. Please import a SCAD file.',
                    'parameters': {},
                    'analysis': {},
                    'current_version': 0,
                    'project_name': None
                }), 200
            
            analysis = modifier.analyze_stl(initial_stl) if os.path.exists(initial_stl) else {}
            
            return jsonify({
                'parameters': modifier.current_params,
                'analysis': analysis,
                'stl_path': '/api/models/current.stl',
                'current_version': active_version,
                'project_name': project_name  # Include project name in response
            })
        except Exception as e:
            print(f"Error in get_current_design: {e}")
            return jsonify({'error': str(e)}), 500
