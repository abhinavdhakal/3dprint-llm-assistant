#!/bin/bash

# Start the Flask backend server for Concrete Design Assistant

cd "$(dirname "$0")/backend"

echo "🚀 Starting Concrete Design Assistant Backend..."
echo "📍 Backend will run on: http://127.0.0.1:5000"
echo "📍 API endpoint: http://127.0.0.1:5000/api"
echo ""
echo "Press Ctrl+C to stop the server"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

python3 app.py
