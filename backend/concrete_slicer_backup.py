"""
Concrete 3D Printer Slicer
Converts STL models to G-code for concrete 3D printing
Based on WASP/COBOD printer specifications
"""

import trimesh
import numpy as np
from datetime import datetime

# Import shapely for robust polygon handling
try:
    from shapely.geometry import Polygon, MultiPolygon
    from shapely.ops import unary_union
    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False
    print("⚠️  Warning: Shapely not installed. Install with: pip install shapely")


class ConcreteSlicer:
    """Simple slicer for concrete 3D printing"""
    
    def __init__(self, stl_path, custom_settings=None):
        self.mesh = trimesh.load(stl_path)
        
        # Don't center - keep original coordinates to match STL
        # The frontend will handle centering for display
        self.bounds = self.mesh.bounds
        
        # Default concrete printer settings (WASP/COBOD compatible)
        self.layer_height = 15.0  # mm (typical for concrete: 10-30mm)
        self.nozzle_diameter = 30.0  # mm (typical: 20-50mm)
        self.print_speed = 100.0  # mm/s (slower than plastic)
        self.travel_speed = 200.0  # mm/s
        self.extrusion_width = 35.0  # mm (slightly wider than nozzle)
        self.flow_rate = 100.0  # percentage
        self.concrete_density = 2400.0  # kg/m³
        self.waste_factor = 10.0  # percentage
        self.num_perimeters = 2  # Number of perimeter walls (for strength)
        self.infill_density = 0  # 0-100% (0 = hollow, concrete usually hollow)
        
        # Apply custom settings if provided
        if custom_settings:
            if 'layer_height' in custom_settings:
                self.layer_height = float(custom_settings['layer_height'])
            if 'nozzle_diameter' in custom_settings:
                self.nozzle_diameter = float(custom_settings['nozzle_diameter'])
                self.extrusion_width = self.nozzle_diameter * 1.15  # 15% wider than nozzle
            if 'print_speed' in custom_settings:
                self.print_speed = float(custom_settings['print_speed'])
            if 'travel_speed' in custom_settings:
                self.travel_speed = float(custom_settings['travel_speed'])
            if 'concrete_density' in custom_settings:
                self.concrete_density = float(custom_settings['concrete_density'])
            if 'waste_factor' in custom_settings:
                self.waste_factor = float(custom_settings['waste_factor'])
        
    def slice_to_layers(self):
        """Slice the mesh into horizontal layers using trimesh + shapely for robust handling"""
        z_min = self.bounds[0][2]
        z_max = self.bounds[1][2]
        
        # Generate layer heights
        num_layers = int((z_max - z_min) / self.layer_height) + 1
        z_heights = z_min + np.arange(num_layers) * self.layer_height
        
        print(f"   📊 Model bounds: Z={z_min:.2f} to {z_max:.2f}mm")
        print(f"   📏 Layer height: {self.layer_height}mm")
        print(f"   🔢 Expected layers: {num_layers}")
        
        try:
            layers = []
            
            for i, z in enumerate(z_heights):
                # Slice the mesh at this Z height
                slice_2d = self.mesh.section(
                    plane_origin=[0, 0, z],
                    plane_normal=[0, 0, 1]
                )
                
                if slice_2d is None:
                    continue
                
                try:
                    # Convert to 2D path
                    path_2d, to_3D = slice_2d.to_planar()
                    
                    path_list = []
                    
                    # Use shapely for robust polygon handling
                    if SHAPELY_AVAILABLE:
                        # Get all polygons from the path
                        try:
                            # Use path_2d.polygons_closed for proper closed polygons
                            if hasattr(path_2d, 'polygons_closed'):
                                polygons = path_2d.polygons_closed
                            elif hasattr(path_2d, 'discrete'):
                                polygons = path_2d.discrete
                            else:
                                polygons = []
                            
                            if polygons is not None and len(polygons) > 0:
                                for poly_points in polygons:
                                    if len(poly_points) < 3:
                                        continue
                                    
                                    try:
                                        # Create shapely polygon and validate
                                        poly = Polygon(poly_points)
                                        
                                        # Fix invalid polygons
                                        if not poly.is_valid:
                                            poly = poly.buffer(0)  # Fix self-intersections
                                        
                                        # Skip empty or invalid polygons
                                        if poly.is_empty or not poly.is_valid:
                                            continue
                                        
                                        # Simplify to remove tiny segments and noise
                                        poly = poly.simplify(tolerance=0.1, preserve_topology=True)
                                        
                                        # Skip if too small after simplification
                                        if poly.is_empty or poly.area < 1.0:
                                            continue
                                        
                                        # Handle MultiPolygon (result of buffer operation)
                                        if isinstance(poly, MultiPolygon):
                                            for p in poly.geoms:
                                                if p.area >= 1.0:
                                                    coords = list(p.exterior.coords)
                                                    if len(coords) >= 3:
                                                        path_list.append(np.array(coords))
                                                    # Add holes
                                                    for interior in p.interiors:
                                                        hole_coords = list(interior.coords)
                                                        if len(hole_coords) >= 3:
                                                            path_list.append(np.array(hole_coords))
                                        else:
                                            # Single polygon - get exterior
                                            coords = list(poly.exterior.coords)
                                            if len(coords) >= 3:
                                                path_list.append(np.array(coords))
                                            # Add holes (windows, doors)
                                            for interior in poly.interiors:
                                                hole_coords = list(interior.coords)
                                                if len(hole_coords) >= 3:
                                                    path_list.append(np.array(hole_coords))
                                    except Exception as e:
                                        # If shapely fails, use raw points
                                        if len(poly_points) >= 3:
                                            path_list.append(np.asarray(poly_points))
                        except Exception as e:
                            # Fall back to discrete if polygons_closed fails
                            if hasattr(path_2d, 'discrete'):
                                discrete_paths = path_2d.discrete
                                if discrete_paths is not None:
                                    if isinstance(discrete_paths, list):
                                        path_list = [np.asarray(p) for p in discrete_paths if len(p) >= 3]
                                    elif len(discrete_paths) >= 3:
                                        path_list = [np.asarray(discrete_paths)]
                    
                    else:
                        # Fallback without shapely (basic slicing)
                        if hasattr(path_2d, 'discrete'):
                            paths = path_2d.discrete
                            if paths is not None and len(paths) > 0:
                                if isinstance(paths, list):
                                    path_list = [np.asarray(p) for p in paths if len(p) >= 3]
                                elif len(paths) >= 3:
                                    path_list = [np.asarray(paths)]
                    
                    if len(path_list) > 0:
                        layers.append({
                            'z': float(z),
                            'paths': path_list
                        })
                    
                    if i % 10 == 0 and i > 0:
                        print(f"   ⏳ Processing layer {i+1}/{num_layers}...")
                        
                except Exception as e:
                    if i < 5:  # Only show first few errors
                        print(f"   ⚠️  Layer {i+1} error: {e}")
                    continue
            
            print(f"🔪 Sliced model into {len(layers)} valid layers")
            
            if len(layers) == 0:
                print(f"   ❌ ERROR: No valid layers found!")
                print(f"   💡 Try: Reduce layer height or check model validity")
            
            return layers
            
        except Exception as e:
            print(f"   ❌ Slicing failed: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def generate_gcode(self, output_path, layers):
        """Generate G-code for concrete printer"""
        
        with open(output_path, 'w') as f:
            # Write header
            f.write(self._generate_header())
            
            # Write layer-by-layer G-code
            for i, layer in enumerate(layers):
                f.write(f"\n; Layer {i + 1}/{len(layers)} at Z={layer['z']:.2f}mm\n")
                f.write(f"G0 Z{layer['z']:.3f} F{self.travel_speed}\n")
                
                for path in layer['paths']:
                    if len(path) < 2:
                        continue
                    
                    # Move to start of path (travel move, no extrusion)
                    start = path[0]
                    f.write(f"G0 X{start[0]:.3f} Y{start[1]:.3f} F{self.travel_speed}\n")
                    f.write(f"M106 S0 ; Pump OFF\n")
                    
                    # Print the path
                    f.write(f"M106 S255 ; Pump ON\n")
                    for point in path[1:]:
                        f.write(f"G1 X{point[0]:.3f} Y{point[1]:.3f} F{self.print_speed}\n")
                    
                    # Stop extrusion
                    f.write(f"M106 S0 ; Pump OFF\n")
            
            # Write footer
            f.write(self._generate_footer())
        
        print(f"📝 G-code written to {output_path}")
        return output_path
    
    def _generate_header(self):
        """Generate G-code header with printer setup"""
        header = f"""; Concrete 3D Printer G-code
; Generated by Concrete Assistant
; Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
; 
; Printer: WASP/COBOD Compatible
; Layer Height: {self.layer_height}mm
; Nozzle Diameter: {self.nozzle_diameter}mm
; Print Speed: {self.print_speed}mm/s
; Extrusion Width: {self.extrusion_width}mm
;
; Model Dimensions:
; X: {self.bounds[1][0] - self.bounds[0][0]:.1f}mm
; Y: {self.bounds[1][1] - self.bounds[0][1]:.1f}mm
; Z: {self.bounds[1][2] - self.bounds[0][2]:.1f}mm

G21 ; Set units to millimeters
G90 ; Absolute positioning
M82 ; Absolute extrusion mode
G28 ; Home all axes
G92 E0 ; Reset extruder position
M106 S0 ; Pump OFF (M106 controls concrete pump)

; Move to start position
G0 Z10 F{self.travel_speed}
G0 X0 Y0 F{self.travel_speed}

"""
        return header
    
    def _generate_footer(self):
        """Generate G-code footer"""
        footer = """
; End of print
M106 S0 ; Pump OFF
G91 ; Relative positioning
G0 Z20 F150 ; Raise nozzle
G90 ; Absolute positioning
G28 X Y ; Home X and Y
M84 ; Disable motors

; Print complete!
"""
        return footer
    
    def generate_visualization_data(self, layers):
        """Generate data for 3D visualization of toolpaths"""
        viz_data = {
            'layers': [],
            'bounds': {
                'x_min': float(self.bounds[0][0]),
                'y_min': float(self.bounds[0][1]),
                'z_min': float(self.bounds[0][2]),
                'x_max': float(self.bounds[1][0]),
                'y_max': float(self.bounds[1][1]),
                'z_max': float(self.bounds[1][2])
            },
            'settings': {
                'layer_height': self.layer_height,
                'nozzle_diameter': self.nozzle_diameter,
                'print_speed': self.print_speed,
                'extrusion_width': self.extrusion_width
            }
        }
        
        for i, layer in enumerate(layers):
            layer_data = {
                'layer_number': i + 1,
                'z': float(layer['z']),
                'paths': []
            }
            
            for path in layer['paths']:
                if len(path) > 1:
                    # Convert numpy arrays to lists for JSON serialization
                    points = [[float(p[0]), float(p[1])] for p in path]
                    layer_data['paths'].append(points)
            
            viz_data['layers'].append(layer_data)
        
        return viz_data
    
    def estimate_print_time(self, layers):
        """Estimate total print time in minutes"""
        total_distance = 0.0
        
        for layer in layers:
            for path in layer['paths']:
                if len(path) < 2:
                    continue
                    
                # Calculate path length
                for i in range(len(path) - 1):
                    dx = path[i+1][0] - path[i][0]
                    dy = path[i+1][1] - path[i][1]
                    total_distance += np.sqrt(dx*dx + dy*dy)
        
        # Time = distance / speed (convert to minutes)
        print_time_minutes = (total_distance / self.print_speed) / 60.0
        
        # Add ~20% for travel moves and layer changes
        total_time = print_time_minutes * 1.2
        
        return {
            'print_distance_m': total_distance / 1000.0,
            'estimated_time_minutes': round(total_time, 1),
            'estimated_time_hours': round(total_time / 60.0, 2)
        }
    
    def estimate_material(self):
        """Estimate concrete material needed"""
        # Volume from mesh (in mm³)
        volume_mm3 = float(self.mesh.volume)
        volume_m3 = volume_mm3 / 1e9
        
        # Use configured concrete density and waste factor
        weight_kg = volume_m3 * self.concrete_density
        
        # Add configured waste factor
        waste_multiplier = 1.0 + (self.waste_factor / 100.0)
        weight_with_waste = weight_kg * waste_multiplier
        
        return {
            'volume_m3': round(volume_m3, 4),
            'volume_liters': round(volume_m3 * 1000, 2),
            'weight_kg': round(weight_kg, 2),
            'weight_with_waste_kg': round(weight_with_waste, 2)
        }


def slice_for_concrete_printing(stl_path, output_gcode_path, custom_settings=None):
    """
    Main function to slice STL and generate G-code for concrete printing
    
    Args:
        stl_path: Path to input STL file
        output_gcode_path: Path for output G-code file
        custom_settings: Optional dict of printer settings to override defaults
        
    Returns:
        dict: Summary of slicing results including visualization data
        
    Note:
        Concrete printing typically uses hollow walls (perimeters only) because:
        - Concrete is heavy (solid infill would be too heavy)
        - Saves material costs significantly
        - Hollow spaces can be filled with insulation later
        - Multiple perimeter walls provide sufficient strength
    """
    print(f"\n[SLICER] Starting concrete printer slicing...")
    print(f"[SLICER] Input: {stl_path}")
    print(f"[SLICER] Note: Generating hollow walls (standard for concrete printing)")
    
    slicer = ConcreteSlicer(stl_path, custom_settings)
    
    # Slice the model
    layers = slicer.slice_to_layers()
    
    if not layers:
        return {
            'success': False,
            'error': 'Failed to slice model - no valid layers generated'
        }
    
    # Generate G-code
    gcode_path = slicer.generate_gcode(output_gcode_path, layers)
    
    # Generate visualization data
    viz_data = slicer.generate_visualization_data(layers)
    
    # Estimate print metrics
    time_estimate = slicer.estimate_print_time(layers)
    material_estimate = slicer.estimate_material()
    
    print(f"\n[SLICER] Slicing complete!")
    print(f"[SLICER] Layers: {len(layers)}")
    print(f"[SLICER] Layer height: {slicer.layer_height}mm")
    print(f"[SLICER] Print time: ~{time_estimate['estimated_time_hours']} hours")
    print(f"[SLICER] Material: ~{material_estimate['weight_with_waste_kg']} kg concrete")
    
    return {
        'success': True,
        'gcode_path': gcode_path,
        'layer_count': len(layers),
        'visualization': viz_data,
        'estimates': {
            'time': time_estimate,
            'material': material_estimate
        },
        'settings': {
            'layer_height': slicer.layer_height,
            'nozzle_diameter': slicer.nozzle_diameter,
            'print_speed': slicer.print_speed,
            'travel_speed': slicer.travel_speed,
            'extrusion_width': slicer.extrusion_width,
            'concrete_density': slicer.concrete_density,
            'waste_factor': slicer.waste_factor
        }
    }
