"""
Configuration and constants for the Concrete Design Assistant
"""
import os

# Base directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DESIGNS_DIR = os.path.join(BASE_DIR, 'designs')
MODELS_DIR = os.path.join(BASE_DIR, 'models')
VERSIONS_DIR = os.path.join(MODELS_DIR, 'versions')
SCAD_VERSIONS_DIR = os.path.join(MODELS_DIR, 'versions', 'scad')
STATE_FILE = os.path.join(MODELS_DIR, 'design_state.json')
HISTORY_FILE = os.path.join(MODELS_DIR, 'history.json')

# Ensure directories exist
def setup_directories():
    """Create required directories if they don't exist"""
    os.makedirs(MODELS_DIR, exist_ok=True)
    os.makedirs(VERSIONS_DIR, exist_ok=True)
    os.makedirs(SCAD_VERSIONS_DIR, exist_ok=True)
    os.makedirs(DESIGNS_DIR, exist_ok=True)
    
    print("Starting Concrete Design Assistant...")
    print(f"Models directory: {MODELS_DIR}")
    print(f"Versions directory: {VERSIONS_DIR}")
    print(f"SCAD Versions directory: {SCAD_VERSIONS_DIR}")
    print(f"Designs directory: {DESIGNS_DIR}")
