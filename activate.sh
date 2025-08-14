#!/bin/bash
# PostSync Virtual Environment Activation Script

echo "🚀 Activating PostSync virtual environment..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Creating one..."
    python3 -m venv venv
    
    echo "📦 Installing dependencies..."
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements-minimal.txt
    echo "✅ Dependencies installed successfully!"
else
    echo "✅ Virtual environment found!"
fi

# Activate the virtual environment
source venv/bin/activate

echo "🎯 Virtual environment activated!"
echo "📍 Python location: $(which python)"
echo "🐍 Python version: $(python --version)"
echo "📦 FastAPI version: $(python -c 'import fastapi; print(fastapi.__version__)' 2>/dev/null || echo 'Not installed')"

echo ""
echo "💡 To deactivate the virtual environment, run: deactivate"
echo "🚀 To start the development server, run: PYTHONPATH=/Users/nio/postsync uvicorn src.main:app --reload --host 0.0.0.0 --port 8000"
echo ""