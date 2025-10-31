# Concrete 3D Printing Assistant

A conversational interface for modifying OpenSCAD designs using natural language. Built for concrete 3D printing workflows but works with any parametric OpenSCAD models.

## What it does

Takes an OpenSCAD file and lets you modify it by describing what you want in plain English. The backend uses Groq's LLM to understand your request and generate new OpenSCAD code. You can preview changes in real-time, approve or reject them, and maintain a full version history.

## Setup

### Backend

```bash
cd backend
pip install -r requirements.txt
```

Create a `.env` file in the backend directory:

```
GROQ_API_KEY=your_groq_api_key_here
```

Get an API key from https://console.groq.com/

### Frontend

Just open `frontend/index.html` in a browser. No build step needed.

## Usage

1. Start the backend:

```bash
cd backend
python app.py
```

2. Open `frontend/index.html` in your browser

3. Import a SCAD file or work with the default room design

4. Type what you want to change (or use voice input):

   - "add a window to the back wall"
   - "make the door wider"
   - "remove the window"
   - etc.

5. **Voice Input**: Click the "🎤 Voice" button to speak your modification request instead of typing

6. Preview the changes in the 3D viewer

7. Approve or reject the modification

## Features

- Natural language modification of OpenSCAD designs
- **Speech-to-text input using OpenAI Whisper API** (works in all browsers including Brave!)
- Real-time 3D preview using Three.js
- Version history with undo/redo
- Two modification modes:
  - Unrestricted: Can add/remove features
  - Restricted: Only parameter changes within 20% bounds
- Pending state system (changes only saved on approval)
- SCAD and STL backups for every version
- Professional 3D viewer with OrbitControls
- CAD-like measurement tools with edge snapping

### Voice Input Setup

1. Get an OpenAI API key from https://platform.openai.com/api-keys
2. Click the "🎤 Voice" button
3. Enter your API key when prompted (stored in browser)
4. Allow microphone access
5. Speak your request, then click "🔴 Stop"
6. Speech is transcribed automatically!

## Architecture

### Backend (Flask + Python)

- `app.py` - Main Flask server, API endpoints
- `design_modifier.py` - Handles SCAD file modifications and STL generation
- `llm_handler.py` - Groq API integration for code generation

### Frontend (Vanilla JS)

- `viewer.js` - Three.js 3D visualization
- `api.js` - Backend communication
- `history.js` - Version control
- `main.js` - Application logic
- `ui.js` - Interface updates

### Data Flow

1. User enters modification request
2. Backend sends current SCAD + request to Groq LLM
3. LLM returns modified SCAD code
4. Backend generates STL preview
5. Frontend displays both designs side-by-side
6. On approval: saves to file and creates version backup
7. On rejection: discards pending changes

## API Endpoints

- `GET /api/current-design` - Current design parameters and analysis
- `POST /api/modify` - Submit modification request
- `POST /api/approve` - Approve pending modification
- `POST /api/reject` - Reject pending modification
- `POST /api/restore-version` - Restore from version backup
- `GET /api/history` - Get version history
- `GET /api/models/<filename>` - Serve STL files

## File Structure

```
backend/
  app.py
  design_modifier.py
  llm_handler.py
  requirements.txt

frontend/
  index.html
  style.css
  js/
    main.js
    viewer.js
    api.js
    history.js
    ui.js
    state.js
    config.js

designs/
  room.scad          # Source SCAD file

models/
  current.stl        # Current approved design
  modified.stl       # Preview of pending changes
  history.json       # Version metadata
  versions/          # STL backups
  versions/scad/     # SCAD backups
```

## Notes

The LLM can be unpredictable. It sometimes simplifies designs when you just want a small change. The restricted mode helps with this but limits what you can do. Working on better prompt engineering to preserve existing features.

The pending state system prevents rejected modifications from corrupting your source file. Changes only write to disk after approval.

Version backups include both SCAD and STL files so you can restore complete historical states.

## Dependencies

Backend:

- Flask
- flask-cors
- openai (for Groq API)
- python-dotenv
- trimesh (STL analysis)

Frontend:

- Three.js (r128)
- STLLoader
- OrbitControls

Requires OpenSCAD installed and in PATH for STL generation.

## License

MIT
