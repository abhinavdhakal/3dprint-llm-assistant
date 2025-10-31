"""
Concrete Design Assistant - Main Flask Application
Modularized for better maintainability
"""
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from design_modifier import DesignModifier
import os

# === LLM HANDLER CONFIGURATION ===
# Choose which LLM handler to use by uncommenting ONE of the following:

# GROQ HANDLERS (FAST - 1-3 seconds):
from llm_handlers.llm_handler_groq_unrestricted import LLMHandler  # 🔓 GROQ UNRESTRICTED: Full freedom
# from llm_handlers.llm_handler_groq_restricted import LLMHandler    # 🔒 GROQ RESTRICTED: Only ±20% parameter changes

# OLLAMA HANDLERS (SLOW - 30-76 seconds):
# from llm_handlers.llm_handler import LLMHandler                    # MODERATE: Balanced modifications
# from llm_handlers.llm_handler_advanced import LLMHandler           # ADVANCED: Auto-chooses parameter/SCAD mode
# from llm_handlers.llm_handler_restricted import LLMHandler         # RESTRICTED: Only ±20% adjustments
# ===================================

from config import setup_directories, DESIGNS_DIR, MODELS_DIR
from state_manager import load_design_state
from routes_register import register_routes
from llm_handlers.llm_handler_openai import call_openai_llm
from llm_handlers.llm_handler_groq_restricted import call_groq_llm

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Setup directories
setup_directories()

# Initialize modifier as None (will be set when SCAD is imported)
modifier = None

# Check if there's an existing SCAD file
existing_scad_files = [f for f in os.listdir(DESIGNS_DIR) if f.endswith('.scad')] if os.path.exists(DESIGNS_DIR) else []
if existing_scad_files:
    # Load the first SCAD file found
    scad_file = os.path.join(DESIGNS_DIR, existing_scad_files[0])
    try:
        modifier = DesignModifier(scad_file)
        print(f"✅ Loaded existing design: {existing_scad_files[0]}")
    except Exception as e:
        print(f"⚠️ Could not load existing SCAD file: {e}")
        modifier = None
else:
    print("📭 No project loaded - waiting for SCAD import")

# Initialize LLM handler
llm = LLMHandler()

# Load existing state on startup
load_design_state()

# Generate initial STL if needed (only if modifier is loaded)
initial_stl = os.path.join(MODELS_DIR, 'current.stl')
if modifier is not None and not os.path.exists(initial_stl):
    print("Generating initial STL...")
    from state_manager import backup_version
    success = modifier.generate_stl(initial_stl)
    if success:
        print("Initial STL generated successfully")
        backup_version(initial_stl, "initial_design", modifier)
    else:
        print("Warning: Could not generate initial STL")

# Use dictionaries to pass mutable references to routes
modifier_ref = {'current': modifier}
version_counter_ref = {'current': 0}

# Register all routes
register_routes(app, modifier_ref, llm, version_counter_ref)

print("🔍 Available routes:")
for rule in app.url_map.iter_rules():
    print(f"  {rule.rule} -> {rule.endpoint}")

@app.route('/api/llm/openai', methods=['POST'])
def api_llm_openai():
    print("📨 OpenAI API called")
    
    # Handle both form data and header formats
    prompt = request.form.get('prompt') or request.headers.get('X-Prompt')
    scad_file = request.files.get('scad')
    
    scad_content = None
    if scad_file:
        scad_content = scad_file.read().decode('utf-8')
    
    if not prompt:
        return jsonify({"error": "No prompt provided"}), 400
    
    # Call LLM with both prompt and SCAD content
    result = call_openai_llm(prompt, scad_content)
    return jsonify(result)

@app.route('/api/llm/groq', methods=['POST'])
def api_llm_groq():
    print("📨 Groq API called")
    
    # Handle both form data and header formats
    prompt = request.form.get('prompt') or request.headers.get('X-Prompt')
    scad_file = request.files.get('scad')
    
    scad_content = None
    if scad_file:
        scad_content = scad_file.read().decode('utf-8')
    
    if not prompt:
        return jsonify({"error": "No prompt provided"}), 400
    
    # Call LLM with both prompt and SCAD content
    result = call_groq_llm(prompt, scad_content)
    return jsonify(result)

@app.route('/simple_benchmark.html')
def simple_benchmark():
    return send_from_directory('../frontend', 'simple_benchmark.html')

# === Flask App Startup ===
if __name__ == "__main__":
    print("\n🚀 Starting Concrete Design Assistant Backend...")
    print("📍 Backend will run on: http://127.0.0.1:5000")
    print("📍 API endpoint: http://127.0.0.1:5000/api\n")
    print("Press Ctrl+C to stop the server\n" + "━"*60 + "\n")
    app.run(debug=True, host='127.0.0.1', port=5000)
