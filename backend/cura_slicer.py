"""
CuraEngine Python wrapper for concrete 3D printing
Requires CuraEngine CLI installed and in PATH
"""
import subprocess
import os

PROFILE_PATH = os.path.join(os.path.dirname(__file__), "concrete_printing.def.json")


def slice_with_curaengine(stl_path, output_gcode_path, layer_height=15, nozzle_diameter=30, print_speed=100, wall_count=2):
    # CuraEngine settings for concrete printing
    command = [
        "CuraEngine", "slice",
        "-j", PROFILE_PATH,
        "-l", stl_path,
        "-o", output_gcode_path,
        "-s", f"layer_height={layer_height}",
        "-s", f"wall_line_count={wall_count}",
        "-s", f"wall_thickness={wall_count * nozzle_diameter}",
        "-s", f"infill_density=0",
        "-s", f"print_speed={print_speed}",
        "-s", f"nozzle_size={nozzle_diameter}"
    ]
    print("[CURA] Running:", " ".join(command))
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        print("[CURA] Error:", result.stderr)
        return False
    print("[CURA] Slicing complete. Output:", output_gcode_path)
    return True

# Example usage:
# slice_with_curaengine("models/current.stl", "print.gcode")
