import os
import subprocess
import trimesh
import re

class DesignModifier:
    def __init__(self, scad_file_path):
        self.scad_file = scad_file_path
        self.full_scad_content = self.read_scad_file()
        self.current_params = self.extract_parameters()  # Extract for display purposes
        
        # Pending modifications (not saved until approved)
        self.pending_scad_content = None
        self.pending_params = None
    
    def read_scad_file(self):
        """Read the full SCAD file content"""
        with open(self.scad_file, 'r') as f:
            return f.read()
    
    def extract_parameters(self):
        """Extract parameters from SCAD file for display purposes only"""
        params = {}
        try:
            # Match pattern: variable_name = value;
            pattern = r'(\w+)\s*=\s*(\d+(?:\.\d+)?)\s*;'
            matches = re.findall(pattern, self.full_scad_content)
            
            for key, value in matches:
                try:
                    params[key] = float(value) if '.' in value else int(value)
                except ValueError:
                    pass
        except Exception as e:
            print(f"Warning: Could not extract parameters: {e}")
        
        return params
    
    def _extract_parameters_from_content(self, content):
        """Extract parameters from given SCAD content string"""
        params = {}
        try:
            pattern = r'(\w+)\s*=\s*(\d+(?:\.\d+)?)\s*;'
            matches = re.findall(pattern, content)
            
            for key, value in matches:
                try:
                    params[key] = float(value) if '.' in value else int(value)
                except ValueError:
                    pass
        except Exception as e:
            print(f"Warning: Could not extract parameters: {e}")
        
        return params
    
    def apply_scad_modification(self, new_scad_content):
        """Store modified SCAD content in memory (don't write to file yet)"""
        print(f"   📝 Preparing SCAD code modification (not saved yet)")
        
        try:
            # Store new content in memory only
            # Do NOT write to file until user approves
            self.pending_scad_content = new_scad_content
            
            # Extract parameters from pending content for display
            self.pending_params = self._extract_parameters_from_content(new_scad_content)
            
            print(f"   ✅ SCAD modification prepared (pending approval)")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Error preparing SCAD modification: {e}")
            return False
    
    def apply_modifications(self, modifications):
        """Apply parameter modifications to SCAD file (for parameter-based mode)"""
        print(f"   📝 Applying parameter modifications: {modifications}")
        
        try:
            new_content = self.full_scad_content
            
            # Apply each modification
            for param, new_value in modifications.items():
                # Find and replace the parameter value
                pattern = rf'({param}\s*=\s*)(\d+(?:\.\d+)?)\s*;'
                replacement = rf'\g<1>{new_value};'
                new_content = re.sub(pattern, replacement, new_content)
                print(f"   ✓ Modified {param} to {new_value}")
            
            # Write the modified content
            with open(self.scad_file, 'w') as f:
                f.write(new_content)
            
            # Update cached content and parameters
            self.full_scad_content = new_content
            self.current_params = self.extract_parameters()
            
            print(f"   ✅ Parameters updated successfully")
            return True
            
        except Exception as e:
            print(f"   ❌ Error applying modifications: {e}")
            return False
    
    def generate_stl(self, output_path):
        """Generate STL file from .scad using OpenSCAD"""
        try:
            # If we have pending modifications, write to temp file
            scad_to_render = self.scad_file
            
            if self.pending_scad_content is not None:
                # Create temporary SCAD file with pending content
                import tempfile
                temp_fd, temp_scad = tempfile.mkstemp(suffix='.scad')
                try:
                    with os.fdopen(temp_fd, 'w') as f:
                        f.write(self.pending_scad_content)
                    scad_to_render = temp_scad
                except:
                    os.close(temp_fd)
                    raise
            
            cmd = [
                'openscad',
                '-o', output_path,
                scad_to_render
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Clean up temp file if used
            if scad_to_render != self.scad_file:
                try:
                    os.remove(scad_to_render)
                except:
                    pass
            
            if result.returncode != 0:
                print(f"OpenSCAD error: {result.stderr}")
                return False
            
            return os.path.exists(output_path)
        except Exception as e:
            print(f"Error generating STL: {e}")
            return False
    
    def analyze_stl(self, stl_path):
        """Analyze STL file to get geometry info"""
        try:
            mesh = trimesh.load(stl_path)
            bounds = mesh.bounds
            
            return {
                'volume_mm3': float(mesh.volume),
                'volume_liters': float(mesh.volume / 1000000),
                'height_mm': float(bounds[1][2] - bounds[0][2]),
                'length_mm': float(bounds[1][0] - bounds[0][0]),
                'width_mm': float(bounds[1][1] - bounds[0][1])
            }
        except Exception as e:
            print(f"Error analyzing STL: {e}")
            return {}