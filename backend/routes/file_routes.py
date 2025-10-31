"""
File serving routes - STL models, SCAD downloads
"""
from flask import send_file
import os
from config import MODELS_DIR, SCAD_VERSIONS_DIR


def register_file_routes(app, modifier_ref):
    """Register file serving routes"""
    
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
