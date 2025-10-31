#!/bin/bash
# Quick benchmark runner script

echo "🏠 LLM Concrete House Benchmark Runner"
echo "======================================"

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found!"
    echo "📝 Copy .env.template to .env and add your API keys"
    echo "   cp .env.template .env"
    echo "   # Then edit .env with your keys"
    exit 1
fi

# Check if dependencies are installed
if ! python3 -c "import openai, groq" 2>/dev/null; then
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt
fi

# Run benchmark
echo "🚀 Starting benchmark..."
echo ""

if [ $# -eq 0 ]; then
    python3 benchmark.py
else
    python3 benchmark.py "$@"
fi