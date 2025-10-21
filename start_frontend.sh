#!/bin/bash

# Start the frontend server for Concrete Design Assistant

cd "$(dirname "$0")/frontend"

echo "🌐 Starting Concrete Design Assistant Frontend..."
echo "📍 Frontend will run on: http://127.0.0.1:8000"
echo ""
echo "Open your browser to: http://127.0.0.1:8000"
echo "Press Ctrl+C to stop the server"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

python3 -m http.server 8000
