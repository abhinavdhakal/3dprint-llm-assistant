import os
import subprocess
import re
import trimesh

class DesignModifier:
    def __init__(self, scad_file_path):
        self.scad_file = scad_file_path
        self.current_params = self.extract_parameters()
    
    def extract_parameters(self):
        """Extract current parameter values from .scad file"""
        params = {}
        with open(self.scad_file, 'r') as f:
            content = f.read()
            # Find lines like: parameter_name = value;
            pattern = r'(\w+)\s*=\s*(\d+)\s*;'
            matches = re.findall(pattern, content)
            for name, value in matches:
                params[name] = int(value)
        return params
    
    def apply_modifications(self, modifications):
        """Update parameters in the .scad file"""
        print(f"   📝 Reading SCAD file: {self.scad_file}")
        with open(self.scad_file, 'r') as f:
            content = f.read()
        
        original_content = content
        modified_count = 0
        
        for param, new_value in modifications.items():
            if param in self.current_params:
                # Replace old value with new value
                old_pattern = f'{param}\s*=\s*\d+\s*;'
                new_line = f'{param} = {new_value};'
                old_content = content
                content = re.sub(old_pattern, new_line, content)
                
                if old_content != content:
                    modified_count += 1
                    print(f"      ✏️  {param}: {self.current_params[param]} → {new_value}")
                
                self.current_params[param] = new_value
            else:
                print(f"      ⚠️  Parameter '{param}' not found in SCAD file")
        
        # Write back to file
        with open(self.scad_file, 'w') as f:
            f.write(content)
        
        if modified_count > 0:
            print(f"   ✅ Modified {modified_count} parameters in SCAD file")
        else:
            print(f"   ⚠️  No parameters were modified (file unchanged)")
        
        return True
    
    def generate_stl(self, output_path):
        """Generate STL file from .scad using OpenSCAD"""
        try:
            cmd = [
                'openscad',
                '-o', output_path,
                self.scad_file
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
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