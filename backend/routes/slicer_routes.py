"""
Concrete printer slicing routes
"""
from flask import request, jsonify
import os
import json
from config import MODELS_DIR


def register_slicer_routes(app, modifier_ref):
    """Register concrete printer slicing routes"""
    
    @app.route('/api/slice-for-printing', methods=['POST'])
    def slice_for_printing():
        """Generate G-code and visualization for concrete 3D printing"""
        try:
            from concrete_slicer import slice_for_concrete_printing
            
            data = request.json
            stl_file = data.get('stl_file', 'current.stl')
            custom_settings = data.get('settings', {})
            
            stl_path = os.path.join(MODELS_DIR, stl_file)
            
            if not os.path.exists(stl_path):
                return jsonify({
                    'success': False,
                    'error': f'STL file not found: {stl_file}'
                }), 404
            
            # Generate output paths
            gcode_path = os.path.join(MODELS_DIR, 'print.gcode')
            viz_path = os.path.join(MODELS_DIR, 'toolpath_viz.json')
            
            print(f"\n[SLICER] Slicing {stl_file} for concrete printing...")
            if custom_settings:
                print(f"[SLICER] Using custom settings: {custom_settings}")
            
            # Slice and generate G-code with custom settings
            result = slice_for_concrete_printing(stl_path, gcode_path, custom_settings)
            
            if not result['success']:
                return jsonify(result), 500
            
            # Save visualization data
            with open(viz_path, 'w') as f:
                json.dump(result['visualization'], f, indent=2)
            
            print(f"[SLICER] Visualization data saved to {viz_path}")
            
            # Read first 50 lines of G-code for preview
            with open(gcode_path, 'r') as f:
                gcode_preview = ''.join(f.readlines()[:50])
            
            return jsonify({
                'success': True,
                'message': 'G-code generated successfully',
                'gcode_path': '/models/print.gcode',
                'gcode_preview': gcode_preview,
                'visualization_path': '/models/toolpath_viz.json',
                'layer_count': result['layer_count'],
                'estimates': result['estimates'],
                'settings': result['settings']
            })
            
        except Exception as e:
            print(f"Error in slice_for_printing: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/download-gcode', methods=['GET'])
    def download_gcode():
        """Download generated G-code file"""
        try:
            from flask import send_file
            
            gcode_path = os.path.join(MODELS_DIR, 'print.gcode')
            
            if not os.path.exists(gcode_path):
                return jsonify({
                    'error': 'G-code file not found. Please generate G-code first.'
                }), 404
            
            return send_file(
                gcode_path,
                mimetype='text/plain',
                as_attachment=True,
                download_name='concrete_print.gcode'
            )
            
        except Exception as e:
            print(f"Error downloading G-code: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/toolpath-visualization', methods=['GET'])
    def get_toolpath_visualization():
        """Get toolpath visualization data"""
        try:
            viz_path = os.path.join(MODELS_DIR, 'toolpath_viz.json')
            
            if not os.path.exists(viz_path):
                return jsonify({
                    'success': False,
                    'error': 'No visualization data found. Please generate G-code first.'
                }), 404
            
            with open(viz_path, 'r') as f:
                viz_data = json.load(f)
            
            return jsonify({
                'success': True,
                'data': viz_data
            })
            
        except Exception as e:
            print(f"Error getting visualization: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
