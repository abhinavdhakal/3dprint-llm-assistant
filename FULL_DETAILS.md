# CONCRETE 3D PRINTING ASSISTANT - COMPLETE TECHNICAL DOCUMENTATION

## PROJECT OVERVIEW

**Project Name:** Concrete 3D Printing Design Assistant  
**Purpose:** LLM-powered conversational interface for modifying OpenSCAD architectural designs using natural language  
**Target Use Case:** Concrete 3D printing workflows, architectural design modification  
**Development Period:** October 18-21, 2025 (~15-18 hours)  
**Tech Stack:** Python Flask + Vanilla JavaScript + Three.js + Groq LLM API

---

## WHAT THIS SYSTEM CAN DO

### Core Capabilities

1. **Natural Language Design Modification**

   - User types plain English requests: "add a window", "make the door wider", "remove the wall"
   - LLM interprets intent and generates OpenSCAD code modifications
   - Two modes available:
     - **Unrestricted Mode** (default): Full freedom to add/remove/modify any feature
     - **Restricted Mode**: Only allows ±20% parameter changes (safer, more predictable)

2. **Real-Time 3D Visualization**

   - Interactive Three.js-based 3D viewer with professional OrbitControls
   - Side-by-side comparison of current vs modified designs
   - Real-time STL generation and rendering (via OpenSCAD)
   - Automatic camera positioning to fit model in view
   - Edge detection visualization (subtle black lines showing geometry edges)

3. **CAD-Like Measurement Tools**

   - **Dimension Overlay**: Shows overall Length/Height/Width/Volume
   - **Interactive Measurement Tool**: Click two points to measure distance
   - **Edge Snapping**: Automatically snaps to nearest vertex or edge (200mm threshold)
   - **Precise Measurements**: Point-to-point distance displayed in millimeters
   - **Visual Feedback**: Red spheres at clicked points, red line connecting them, distance label

4. **Version Control System**

   - Complete version history with timestamps
   - Both STL and SCAD files backed up for each version
   - Undo/Redo functionality restores complete SCAD code (not just parameters)
   - Version descriptions auto-cleaned from verbose LLM output
   - Restore any previous version from history panel
   - Maximum 50 versions kept (older versions auto-pruned)

5. **Pending State System**

   - Modifications previewed before being committed
   - Rejected changes never touch the source SCAD file
   - Only approved changes written to disk and added to history
   - Prevents accidental design corruption

6. **Project Management**

   - Import/Export SCAD files
   - Save/Load complete project state
   - Export current design as STL
   - Project renaming with persistent state

7. **Design Analysis**
   - Automatic geometry analysis (volume, dimensions)
   - Parameter extraction from SCAD code
   - Bounding box calculations
   - Volume in both mm³ and liters

---

## WHAT THIS SYSTEM CANNOT DO

### Current Limitations

1. **LLM Unpredictability**

   - Sometimes simplifies designs instead of preserving all features
   - May misinterpret complex multi-step requests
   - Cannot guarantee preservation of all existing features
   - No formal verification of generated OpenSCAD code validity

2. **OpenSCAD Constraints**

   - Requires OpenSCAD CLI installed on system
   - STL generation can take 2-10 seconds depending on complexity
   - Cannot render invalid OpenSCAD syntax (will fail silently)
   - No syntax validation before attempting render

3. **3D Viewer Limitations**

   - Measurement text labels always face camera (not always readable at all angles)
   - Edge detection threshold fixed at 200mm (not user-adjustable)
   - No angle measurement tool
   - Cannot measure curved surfaces accurately
   - No measurement persistence across sessions
   - No measurement export functionality

4. **File Format Restrictions**

   - Only works with OpenSCAD (.scad) files
   - Cannot import STL, OBJ, or other 3D formats
   - Cannot export to formats other than STL/SCAD
   - No direct G-code generation for 3D printers

5. **Collaboration Limitations**

   - Single-user only (no multi-user collaboration)
   - No cloud storage or sync
   - No design comments or annotations
   - No design sharing/publishing features

6. **Performance Constraints**

   - Large/complex models can slow down viewer
   - No model simplification or LOD system
   - Browser-based rendering limited by GPU
   - No background STL generation (blocks UI)

7. **Missing Features**
   - No parametric constraints or design rules
   - No material/cost estimation
   - No structural analysis or validation
   - No print path planning
   - No slicing integration
   - No camera views (top/front/side shortcuts)
   - No screenshot/export of viewport
   - No dimension annotations that persist

---

## SYSTEM ARCHITECTURE

### Backend (Python Flask)

**File:** `backend/app.py` (1026 lines)

**Core Routes:**

- `GET /api/current-design` - Get current design parameters and STL path
- `POST /api/modify` - Process modification request via LLM
- `POST /api/approve` - Commit pending changes to file and create version backup
- `POST /api/reject` - Discard pending changes
- `GET /api/history` - Get version history list
- `POST /api/restore-version` - Restore specific version from SCAD backup
- `POST /api/update-version-description` - Edit version description
- `POST /api/import-scad` - Import new SCAD file as project
- `GET /api/export-scad` - Export current SCAD source
- `GET /api/export-stl` - Export current STL model
- `GET /api/models/<filename>` - Serve STL files

**State Management:**

- `modifier` - DesignModifier instance (None if no project loaded)
- `version_counter` - Increments with each approved change
- `STATE_FILE` - Persists current version number and parameters
- `HISTORY_FILE` - JSON array of all versions with metadata

**Pending State System:**

```python
# In DesignModifier class:
self.pending_scad_content = None  # Modified SCAD (not saved yet)
self.pending_params = None         # Extracted parameters from pending
```

When modification requested:

1. LLM generates new SCAD code
2. Stored in `pending_scad_content` (NOT written to file)
3. STL generated from pending content using temp file
4. User approves → written to file, version created
5. User rejects → pending content discarded

---

### LLM Handlers (Multiple Implementations)

**Active Handler:** `backend/llm_handler_groq_unrestricted.py`

**Available Handlers:**

1. **llm_handler_groq_unrestricted.py** (ACTIVE)

   - Uses Groq API with llama-3.3-70b-versatile model
   - Response time: 1-3 seconds
   - Full freedom to add/remove/modify features
   - Always uses full SCAD code modification mode

2. **llm_handler_groq_restricted.py**

   - Uses Groq API (fast)
   - Only allows ±20% parameter adjustments
   - Safer, more predictable changes
   - Cannot add/remove features

3. **llm_handler.py** (Ollama - SLOW)

   - Uses local Ollama with llama3.2 model
   - Response time: 30-76 seconds
   - Moderate modification freedom

4. **llm_handler_advanced.py** (Ollama - SLOW)

   - Auto-chooses between parameter-only or full SCAD mode
   - Attempts to preserve existing design features
   - Response time: 30-76 seconds

5. **llm_handler_restricted.py** (Ollama - SLOW)
   - Parameter-only mode, ±20% limit
   - Response time: 30-76 seconds

**Switching Handlers:**

Edit `backend/app.py` line 8-13, uncomment desired handler:

```python
from llm_handler_groq_unrestricted import LLMHandler  # Current
# from llm_handler_groq_restricted import LLMHandler
# from llm_handler import LLMHandler
```

**LLM Prompt Engineering:**

The unrestricted handler includes comprehensive OpenSCAD guidelines:

- Primitive shapes (cube, sphere, cylinder, polyhedron)
- Transformations (translate, rotate, scale, mirror)
- Boolean operations (union, difference, intersection)
- Concrete 3D printing design principles (wall thickness, door heights, etc.)
- Common pitfalls and corrections
- Polyhedron syntax (corrects triangles → faces parameter)
- Building structure rules (how to add walls vs remove openings)

**LLM Response Format:**

```json
{
  "status": "ready",
  "understood": "User wants to add a window...",
  "reasoning": "I will create a window opening...",
  "changes_summary": ["Added window_width parameter", "Created window opening"],
  "new_scad_code": "// Complete OpenSCAD code here..."
}
```

---

### Design Modifier (backend/design_modifier.py)

**Class:** `DesignModifier`

**Key Methods:**

- `__init__(scad_file_path)` - Load SCAD file, extract parameters
- `read_scad_file()` - Read full SCAD content into memory
- `extract_parameters()` - Regex extraction of parameters for display
- `apply_scad_modification(new_scad)` - Store modified SCAD in pending state
- `apply_modifications(params_dict)` - Apply parameter-only changes
- `generate_stl(output_path)` - Call OpenSCAD CLI to render STL
- `analyze_stl(stl_path)` - Use trimesh to calculate volume/dimensions

**Parameter Extraction Regex:**

```python
pattern = r'(\w+)\s*=\s*(\d+(?:\.\d+)?)\s*;'
# Matches: variable_name = 1234.5;
```

**STL Generation:**

```bash
openscad -o output.stl input.scad
```

- Timeout: 30 seconds
- Uses temp file if pending modifications exist
- Returns success boolean

**Pending State Flow:**

```
User Request
    ↓
LLM Generates SCAD
    ↓
apply_scad_modification() → stores in pending_scad_content
    ↓
generate_stl() → uses temp file with pending content
    ↓
User Approves → /api/approve
    ↓
Write pending_scad_content to actual file
    ↓
Create version backup (STL + SCAD)
    ↓
Clear pending state
```

---

### Frontend Architecture

**Structure:** Vanilla JavaScript with modular design (no frameworks)

**Core Modules:**

1. **config.js** - All constants and configuration

   ```javascript
   CONFIG = {
     API_BASE_URL: 'http://127.0.0.1:5000',
     COLORS: { ... },
     VIEWER: { camera, grid, axes settings },
     LIGHTS: { ambient, directional intensities }
   }
   ```

2. **state.js** - Global application state

   ```javascript
   AppState = {
     scene,
     camera,
     renderer,
     controls,
     currentMesh,
     modifiedMesh,
     currentSTL,
     modifiedSTL,
     measurementMode,
     measurementPoints,
     viewerMode: "current" | "modified" | "both",
   };
   ```

3. **viewer.js** (724 lines) - Three.js 3D visualization

   - Scene setup with lights, grid, axes
   - OrbitControls integration
   - STL loading and rendering
   - Edge detection visualization
   - Measurement overlay system
   - Interactive point-to-point measurement tool
   - Edge/vertex snapping algorithm

4. **ui.js** - DOM manipulation and message display

   - `addMessage(text, type)` - Add chat messages
   - `displayParameters(params, changes)` - Show parameter table
   - `displayAnalysis(analysis, containerId)` - Show geometry info
   - `updateVersionDisplay(current, total)` - Update version counter

5. **api.js** - Backend communication

   - All fetch() calls wrapped in functions
   - Error handling and response parsing
   - File upload/download utilities

6. **history.js** - Version control UI

   - Load and display version history
   - Version restoration
   - Description editing (inline edit on click)

7. **importexport.js** - File operations

   - SCAD file import
   - STL/SCAD export
   - Project save/load (ZIP with all files)

8. **main.js** - Event handlers and application flow
   - Submit button → modify request
   - Approve/Reject buttons
   - Undo/Redo
   - Measurement toggle
   - View mode switching

---

### 3D Viewer Deep Dive

**Technology:** Three.js r128 with OrbitControls

**Scene Setup:**

```javascript
// Scene
scene = new THREE.Scene()
scene.background = 0x1a1a1a (dark gray)

// Camera
PerspectiveCamera(FOV=45, aspect, near=1, far=100000)
Initial position: (5000, 5000, 5000)

// Lights
AmbientLight(0xffffff, intensity=0.6)
DirectionalLight(0xffffff, intensity=0.8) at (1,1,1)

// Grid
GridHelper(size=10000, divisions=20)

// Axes
AxesHelper(size=5000)
+ Custom axis labels (X=red, Y=green, Z=blue)
```

**OrbitControls Configuration:**

```javascript
controls.enableDamping = true; // Smooth inertia
controls.dampingFactor = 0.05;
controls.minDistance = 500;
controls.maxDistance = 50000;
controls.mouseButtons = {
  LEFT: ROTATE,
  RIGHT: PAN,
  MIDDLE: DOLLY(zoom),
};
```

**Edge Detection Algorithm:**

1. Load STL geometry
2. Create `EdgesGeometry` with 15° threshold angle
3. Render edges as `LineSegments` (black, 30% opacity)
4. Store edges in `mesh.userData.edgesGeometry`

**Edge Snapping Algorithm:**

```javascript
findNearestEdgePoint(clickPoint, mesh) {
  For each edge vertex pair (v1, v2):
    - Transform to world space
    - Calculate distance from click to v1
    - Calculate distance from click to v2
    - Calculate closest point on edge line segment
    - Track minimum distance

  If minDistance < 200mm:
    Return snapped point
  Else:
    Return original click point
}
```

**Measurement Tool Workflow:**

1. User clicks "📐 Measure" button
2. `measurementMode = true`
3. Click handler uses Raycaster to detect 3D point on mesh
4. Snap to nearest edge/vertex
5. Place red sphere marker (30mm radius)
6. First click: prompt "Click second point"
7. Second click: draw red line, show distance label
8. Distance label: canvas-based sprite with `depthTest: false` (always visible)
9. Continuous measurements until mode toggled off

**Measurement Label Rendering:**

```javascript
createMeasurementLabel(text) {
  - Create 512x128 canvas
  - Draw black background (80% opacity)
  - Render text "XXX.X mm" in white, bold 60px
  - Convert to texture
  - Create Sprite with depthTest=false, renderOrder=999
  - Scale 800x200 units
  - Position at midpoint between measured points
}
```

---

## FILE STRUCTURE

```
concrete-assistant/
├── backend/
│   ├── app.py                              # Main Flask server (1026 lines)
│   ├── design_modifier.py                  # SCAD manipulation (175 lines)
│   ├── llm_handler_groq_unrestricted.py    # ACTIVE LLM handler (341 lines)
│   ├── llm_handler_groq_restricted.py      # Restricted Groq handler
│   ├── llm_handler.py                      # Ollama moderate mode
│   ├── llm_handler_advanced.py             # Ollama auto-mode
│   ├── llm_handler_restricted.py           # Ollama restricted
│   ├── requirements.txt                    # Python dependencies
│   └── .env                                # GROQ_API_KEY (git-ignored)
│
├── frontend/
│   ├── index.html                          # Main UI (240 lines)
│   ├── style.css                           # All styling
│   ├── favicon.svg                         # 3D printer nozzle icon
│   ├── favicon.ico                         # PNG fallback
│   └── js/
│       ├── config.js                       # Constants and settings
│       ├── state.js                        # Global state management
│       ├── viewer.js                       # Three.js 3D viewer (724 lines)
│       ├── ui.js                           # DOM manipulation
│       ├── api.js                          # Backend API calls
│       ├── history.js                      # Version history panel
│       ├── importexport.js                 # File I/O operations
│       └── main.js                         # Event handlers & app flow
│
├── designs/
│   └── design.scad                         # Current/active SCAD file
│
├── models/
│   ├── current.stl                         # Approved design STL (git-ignored)
│   ├── modified.stl                        # Preview STL (git-ignored)
│   ├── design_state.json                   # Current version metadata
│   ├── history.json                        # Complete version history
│   └── versions/
│       ├── v0001_timestamp_desc.stl        # STL backups
│       ├── v0002_timestamp_desc.stl
│       └── scad/
│           ├── v0001_timestamp_desc.scad   # SCAD backups (for restoration)
│           └── v0002_timestamp_desc.scad
│
├── backups/                                # Manual backup copies
│   ├── backend copy/
│   └── frontend copy/
│
├── .gitignore                              # Excludes node_modules, __pycache__, .env, etc.
├── README.md                               # Setup and usage guide
├── FULL_DETAILS.md                         # This file
├── start_backend.sh                        # Backend startup script
└── start_frontend.sh                       # Frontend startup script (opens browser)
```

---

## DEPENDENCIES

### Backend (Python 3.8+)

```
flask==3.0.0           # Web server framework
flask-cors==4.0.0      # Cross-origin resource sharing
requests==2.31.0       # HTTP client library
python-dotenv==1.0.0   # Environment variable management
trimesh==4.1.0         # STL analysis (volume, dimensions)
numpy==1.26.3          # Math operations (trimesh dependency)
openai==1.12.0         # Groq API client (OpenAI-compatible)
```

### Frontend (No Build Required)

**CDN-loaded libraries:**

```html
<!-- Three.js r128 -->
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>

<!-- STL Loader -->
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/STLLoader.js"></script>

<!-- OrbitControls -->
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>

<!-- Stats.js (FPS monitor - imported but not actively used) -->
<script src="https://cdnjs.cloudflare.com/ajax/libs/stats.js/r17/Stats.min.js"></script>
```

### System Requirements

- **OpenSCAD CLI** - Must be installed and in PATH

  - macOS: `brew install openscad`
  - Linux: `apt-get install openscad`
  - Windows: Download from openscad.org

- **Python 3.8+**
- **Modern web browser** (Chrome, Firefox, Edge, Safari)

---

## CONFIGURATION

### Backend Configuration

**File:** `backend/.env`

```bash
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxx
```

Get API key from: https://console.groq.com/

**LLM Model:** `llama-3.3-70b-versatile` (defined in llm_handler_groq_unrestricted.py)

**Server Settings:**

```python
# In app.py
if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
```

### Frontend Configuration

**File:** `frontend/js/config.js`

```javascript
const CONFIG = {
  API_BASE_URL: "http://127.0.0.1:5000",

  COLORS: {
    BACKGROUND: 0x1a1a1a,
    CURRENT_MODEL: 0x00aaff, // Cyan
    MODIFIED_MODEL: 0xff6600, // Orange
    GRID_CENTER: 0x444444,
    GRID_LINES: 0x222222,
  },

  VIEWER: {
    CAMERA_FOV: 45,
    CAMERA_NEAR: 1,
    CAMERA_FAR: 100000,
    CAMERA_INITIAL_POSITION: { x: 5000, y: 5000, z: 5000 },
    GRID_SIZE: 10000,
    GRID_DIVISIONS: 20,
    AXES_SIZE: 5000,
    ZOOM_MIN_DISTANCE: 500,
    ZOOM_MAX_DISTANCE: 50000,
  },

  LIGHTS: {
    AMBIENT_INTENSITY: 0.6,
    DIRECTIONAL_INTENSITY: 0.8,
  },
};
```

---

## USAGE WORKFLOWS

### Starting the Application

**Backend:**

```bash
cd backend
python app.py
```

Server starts at http://127.0.0.1:5000

**Frontend:**

```bash
# Option 1: Direct open
open frontend/index.html

# Option 2: Use script
./start_frontend.sh
```

### Basic Workflow

1. **Import SCAD File**

   - Click "📁 Import / Export"
   - Click "📐 Import OpenSCAD File"
   - Select .scad file
   - System loads file, generates initial STL, creates first version

2. **Make Modification**

   - Type request in text area: "add a window on the left wall"
   - Click "Submit Request"
   - LLM processes (1-3 seconds)
   - Modified preview appears in 3D viewer
   - Parameters and changes shown in chat

3. **Review Changes**

   - Switch between "Current Design" / "Modified Design" / "Compare" views
   - Use measurement tool to verify dimensions
   - Check geometry analysis (volume, dimensions)

4. **Approve or Reject**

   - Click "✓ Approve Changes" to commit
     - SCAD file updated
     - Version backup created (STL + SCAD)
     - Added to history
   - Click "✗ Request More Changes" to discard
     - Pending changes cleared
     - Source file unchanged

5. **Use Measurement Tool**
   - Click "📐 Measure" button
   - Click on first point on model (snaps to nearest edge/vertex)
   - Click on second point
   - Distance shown with visual line and label
   - Click more pairs to measure continuously
   - Click "📐 Measure" again to disable

### Version Control Workflow

**Undo:**

- Click "↶ Undo" button
- System restores previous version SCAD from backup
- Regenerates STL
- Updates display

**Redo:**

- Click "↷ Redo" button
- Moves forward in history
- Restores next version

**History Panel:**

- Click "📜 History" button
- See all versions with timestamps and descriptions
- Click version description to edit inline
- Click version entry to restore that specific version

**Version Naming:**

- Auto-generated from LLM description
- Verbose prefixes removed ("The user wants to..." → "Add a window...")
- Limited to 60 characters
- Can be edited after creation

### Import/Export Workflow

**Export Current Design:**

```
📁 Import/Export → 🗿 Export STL
Downloads: design_YYYYMMDD_HHMMSS.stl
```

```
📁 Import/Export → 📐 Export SCAD
Downloads: design_YYYYMMDD_HHMMSS.scad
```

**Save Complete Project:**

```
📁 Import/Export → 💾 Save Project
Downloads: project_name_YYYYMMDD_HHMMSS.zip
Contains:
  - designs/design.scad
  - models/current.stl
  - models/history.json
  - models/design_state.json
  - models/versions/ (all STL backups)
  - models/versions/scad/ (all SCAD backups)
```

**Load Project:**

```
📁 Import/Export → 📂 Open Project
Select: .zip file
System extracts and restores complete project state
```

---

## DESIGN PATTERNS

### Pending State Pattern

**Problem:** Rejected changes were modifying source files

**Solution:** Two-phase commit

```python
# Phase 1: Preview (in-memory only)
modifier.apply_scad_modification(new_code)
  → stores in pending_scad_content
  → generates STL from temp file
  → user sees preview

# Phase 2: Commit (if approved)
/api/approve
  → writes pending_scad_content to file
  → creates version backup
  → clears pending state
```

### Parameter Extraction Pattern

**Problem:** Need to show parameters even from pending modifications

**Solution:** Dual parameter sets

```python
self.current_params   # From actual file
self.pending_params   # From pending modifications

# Display logic:
params_to_show = modifier.pending_params if modifier.pending_params else modifier.current_params
```

### Version Restoration Pattern

**Problem:** Undo/redo was only changing parameters, not full design

**Solution:** Store complete SCAD backups

```
/api/restore-version?version=5
  → finds models/versions/scad/v0005_*.scad
  → copies to designs/design.scad
  → regenerates STL
  → extracts parameters
  → updates display
```

### Edge Snapping Pattern

**Problem:** Clicking on mesh surfaces isn't precise for measurements

**Solution:** Multi-level snapping algorithm

```javascript
1. User clicks on mesh surface (raycaster intersection)
2. Extract all edge geometry vertices
3. For each edge segment:
   a. Check distance to both endpoints
   b. Check distance to closest point on line segment
4. Find global minimum distance
5. If < 200mm threshold: snap to that point
6. Else: use original click point
```

---

## KNOWN ISSUES

### Critical Issues

1. **LLM Design Simplification**

   - **Symptom:** LLM removes features when asked to modify
   - **Example:** "add a window" → removes existing doors
   - **Cause:** LLM generates new SCAD without preserving all features
   - **Mitigation:** Prompt includes "preserve all existing features" but not 100% reliable
   - **Workaround:** Use restricted mode for simple changes, undo if features lost

2. **No OpenSCAD Syntax Validation**
   - **Symptom:** Invalid SCAD code causes silent STL generation failure
   - **Cause:** No pre-render validation of generated code
   - **Result:** User sees "Failed to generate modified design" error
   - **Workaround:** Check terminal for OpenSCAD error output

### Minor Issues

3. **Measurement Labels Occlusion**

   - **Symptom:** Labels blocked by model at certain angles (PARTIALLY FIXED)
   - **Fix Applied:** Added `depthTest: false`, `renderOrder: 999`
   - **Remaining Issue:** Labels always face camera, hard to read when edge-on

4. **Edge Detection Threshold Fixed**

   - **Issue:** 200mm snap threshold not adjustable by user
   - **Impact:** May snap too aggressively on large models, not enough on small models

5. **No Measurement Persistence**

   - **Issue:** All measurements cleared when toggling mode off
   - **Missing:** Save measurements, export measurement data, measurement layers

6. **Version History Growth**

   - **Issue:** Large projects accumulate many backup files
   - **Mitigation:** Only keeps last 50 versions
   - **Missing:** Selective version pruning, version compression

7. **No Multi-User Support**
   - **Issue:** File-based storage means only one user per project
   - **Risk:** Concurrent edits would cause conflicts

---

## PERFORMANCE CHARACTERISTICS

### Response Times

**LLM Processing (Groq):**

- Simple request: 1-2 seconds
- Complex request: 2-4 seconds
- Network latency dependent

**LLM Processing (Ollama - Local):**

- Simple request: 30-45 seconds
- Complex request: 60-76 seconds
- CPU dependent

**STL Generation:**

- Simple design: 2-5 seconds
- Complex design: 5-10 seconds
- Depends on geometry complexity and OpenSCAD performance

**3D Rendering:**

- Load STL: < 1 second
- Initial render: < 1 second
- Rotation/zoom: 60 FPS (GPU dependent)

**Version Operations:**

- Undo/Redo: 3-6 seconds (includes SCAD restore + STL regen)
- History load: < 100ms
- Version restore: 3-6 seconds

### File Sizes

**Typical SCAD:** 2-5 KB  
**Typical STL:** 500 KB - 5 MB (depends on geometry complexity)  
**Complete Project ZIP:** 10-50 MB (includes all versions)  
**History JSON:** 5-20 KB (50 versions × ~400 bytes each)

---

## TROUBLESHOOTING

### Backend Won't Start

**Error:** `ModuleNotFoundError: No module named 'flask'`  
**Solution:** `pip install -r requirements.txt`

**Error:** `GROQ_API_KEY not found`  
**Solution:** Create `backend/.env` with `GROQ_API_KEY=your_key`

**Error:** `openscad: command not found`  
**Solution:** Install OpenSCAD CLI: `brew install openscad`

### Frontend Issues

**Error:** STL doesn't load / viewer blank  
**Check:**

1. Is backend running? (http://127.0.0.1:5000/test should show "Backend is working!")
2. Browser console for CORS errors
3. Network tab shows 200 OK for `/api/models/current.stl`

**Error:** Three.js not defined  
**Solution:** Check internet connection (CDN libraries must load)

### LLM Issues

**Error:** "Failed to generate modified design"  
**Check:**

1. Backend terminal for OpenSCAD error output
2. LLM response in backend terminal (look for syntax errors in generated SCAD)
3. Try simpler request

**Issue:** LLM removes features  
**Solution:**

1. Use restricted mode handler
2. Be very specific: "add a window BUT keep all existing doors and windows"
3. Undo if features lost

### Measurement Tool Issues

**Issue:** Can't see measurement labels  
**Check:**

1. Labels have `depthTest: false` (should always be visible)
2. Try rotating view
3. Check if labels positioned at midpoint of measured points

**Issue:** Clicking doesn't register points  
**Check:**

1. Measurement mode enabled? (button should have .active class)
2. Clicking on actual mesh surface?
3. Browser console for errors

---

## FUTURE ENHANCEMENTS

### High Priority

1. **LLM Reliability Improvements**

   - Structured output format (JSON schema)
   - Diff-based modifications (preserve unchanged code)
   - Formal verification of generated SCAD
   - Multi-step planning for complex requests

2. **Measurement Tool Enhancements**

   - Angle measurement between lines
   - Area measurement (select multiple points, calculate polygon area)
   - Measurement units toggle (mm/cm/m/inches)
   - Persistent measurements (save with version)
   - Measurement export (CSV, annotations on STL)

3. **Collaboration Features**
   - Cloud storage integration
   - Real-time multi-user editing
   - Design comments and annotations
   - Version branching and merging

### Medium Priority

4. **CAD Feature Parity**

   - Dimension constraints
   - Parametric relationships (wall_height = 2 × door_height)
   - Design rules validation
   - Material library and assignment

5. **3D Printing Integration**

   - G-code generation
   - Slicing integration (CuraEngine, PrusaSlicer)
   - Print path visualization
   - Support structure generation
   - Multi-material support

6. **Performance Optimization**
   - Background STL generation (Web Workers)
   - Model simplification / LOD
   - Partial re-rendering
   - Caching and preloading

### Low Priority

7. **UI/UX Improvements**

   - Dark/light theme toggle
   - Keyboard shortcuts
   - Camera presets (top, front, side, isometric)
   - Screenshot/viewport export
   - Customizable grid and axes

8. **Analysis Features**
   - Structural analysis (FEA integration)
   - Material cost estimation
   - Print time estimation
   - Weight calculation
   - Center of mass visualization

---

## API REFERENCE

### GET /api/current-design

**Description:** Get current design state

**Response:**

```json
{
  "parameters": {
    "room_length": 6500,
    "room_width": 5500,
    "wall_height": 2800
  },
  "analysis": {
    "volume_mm3": 12345678,
    "volume_liters": 12.35,
    "height_mm": 2800,
    "length_mm": 6500,
    "width_mm": 5500
  },
  "stl_path": "/api/models/current.stl"
}
```

**Status Codes:**

- 200: Success
- 500: Server error

---

### POST /api/modify

**Description:** Process modification request via LLM

**Request Body:**

```json
{
  "input": "add a window on the left wall"
}
```

**Response (Success):**

```json
{
  "status": "success",
  "understood": "User wants to add a window on the left wall",
  "reasoning": "I will create a window opening...",
  "changes_summary": ["Added window_width parameter", "Created window opening"],
  "modifications": {
    "window_width": 1600,
    "window_height": 1200
  },
  "new_parameters": {
    "room_length": 6500,
    "window_width": 1600
  },
  "analysis": {
    "volume_liters": 11.2
  },
  "stl_path": "/api/models/modified.stl"
}
```

**Response (Clarification Needed):**

```json
{
  "status": "clarification_needed",
  "question": "Which wall do you mean by 'left wall'?",
  "understood": "User wants to add a window but location unclear"
}
```

**Status Codes:**

- 200: Success or clarification needed
- 400: No project loaded
- 500: Generation error

---

### POST /api/approve

**Description:** Commit pending changes to file and create version

**Response:**

```json
{
  "status": "success",
  "message": "Design approved and saved"
}
```

---

### POST /api/reject

**Description:** Discard pending changes

**Response:**

```json
{
  "status": "success",
  "message": "Changes rejected"
}
```

---

### GET /api/history

**Description:** Get version history list

**Response:**

```json
{
  "success": true,
  "history": [
    {
      "id": "v1_1760986991288",
      "version": 1,
      "timestamp": "2025-10-20T14:03:11.288108",
      "description": "Original design: design",
      "parameters": { ... }
    }
  ],
  "count": 12
}
```

---

### POST /api/restore-version

**Description:** Restore specific version from SCAD backup

**Request Body:**

```json
{
  "version": 5
}
```

**Response:**

```json
{
  "status": "success",
  "message": "Version 5 restored successfully"
}
```

---

### POST /api/import-scad

**Description:** Import SCAD file as new project

**Request:** multipart/form-data with `file` field

**Response:**

```json
{
  "status": "success",
  "message": "SCAD file imported successfully"
}
```

---

### GET /api/export-scad

**Description:** Download current SCAD file

**Response:** File download

---

### GET /api/export-stl

**Description:** Download current STL file

**Response:** File download

---

## TESTING CHECKLIST

### Backend Tests

- [ ] `/test` endpoint returns "Backend is working!"
- [ ] Import SCAD file creates initial STL
- [ ] Modification request generates preview STL
- [ ] Approve creates version backup (STL + SCAD)
- [ ] Reject clears pending state
- [ ] Undo restores previous SCAD version
- [ ] Redo moves forward in history
- [ ] Export SCAD downloads file
- [ ] Export STL downloads file
- [ ] History API returns version list
- [ ] Version restoration works correctly

### Frontend Tests

- [ ] 3D viewer initializes with grid and axes
- [ ] STL loads and renders correctly
- [ ] OrbitControls work (rotate, pan, zoom)
- [ ] Dimension overlay shows correct values
- [ ] Measurement tool button toggles mode
- [ ] Click measurement creates markers
- [ ] Two-point measurement shows distance
- [ ] Edge snapping works on model edges
- [ ] Measurement labels visible at all angles
- [ ] View mode switching works (current/modified/compare)
- [ ] Undo/Redo buttons enable/disable correctly
- [ ] Version counter updates
- [ ] History panel loads and displays
- [ ] Version description editing works
- [ ] Import/Export menu opens/closes

### Integration Tests

- [ ] End-to-end workflow: import → modify → approve → undo
- [ ] Project save/load preserves all state
- [ ] Multiple modifications in sequence
- [ ] Complex requests with clarification
- [ ] Error handling for invalid SCAD
- [ ] Large file handling
- [ ] Version history pruning at 50 versions

---

## CREDITS AND LICENSES

**Developed by:** Student worker at Rula Lab  
**Development Time:** ~15-18 hours (Oct 18-21, 2025)  
**AI Assistance:** GitHub Copilot, Claude AI (for code generation and debugging)

**Third-Party Libraries:**

- **Flask** - BSD-3-Clause License
- **Three.js** - MIT License
- **trimesh** - MIT License
- **Groq API** - Proprietary (requires API key)
- **OpenSCAD** - GPL-3.0 License

**Fonts:** System fonts (-apple-system, BlinkMacSystemFont, Segoe UI, Roboto)

---

## CONCLUSION

This system demonstrates a working prototype of LLM-assisted CAD modification for concrete 3D printing. While it has limitations (LLM unpredictability, no formal verification), it successfully enables natural language interaction with parametric design files. The pending state system, version control, and CAD-like measurement tools make it viable for iterative design workflows.

Key achievements:

- ✅ 1-3 second LLM response times (Groq)
- ✅ Full version control with SCAD restoration
- ✅ Professional 3D viewer with measurement tools
- ✅ Pending state prevents design corruption
- ✅ Complete project save/load functionality

Key limitations:

- ❌ LLM can simplify designs unintentionally
- ❌ No formal SCAD code validation
- ❌ Single-user only (no collaboration)
- ❌ Limited to OpenSCAD format

**Total Lines of Code (excluding backups):**

- Backend: ~1,900 lines Python
- Frontend: ~2,400 lines JavaScript
- Total: ~4,300 lines

**File Count:** 27 active files (excluding backups and generated files)

---

_Last Updated: October 30, 2025_
