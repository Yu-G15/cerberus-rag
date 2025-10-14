#!/bin/bash

# Cerberus Agent - LangGraph Development Server Startup Script
# This script ensures the correct PATH is set and starts the LangGraph dev server

# Navigate to the project directory
cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "🐍 Activating Python virtual environment..."
    source venv/bin/activate
elif [ -d ".venv" ]; then
    echo "🐍 Activating Python virtual environment..."
    source .venv/bin/activate
else
    echo "⚠️  No virtual environment found. Using system Python."
    # Set the correct PATH for langgraph command (fallback)
    export PATH="/Users/bassimananuar/Library/Python/3.9/bin:$PATH"
fi

# Check if langgraph command is available
if ! command -v langgraph &> /dev/null; then
    echo "❌ Error: langgraph command not found in PATH"
    echo "Please ensure langgraph-cli[inmem] is installed:"
    echo "pip install -U 'langgraph-cli[inmem]'"
    exit 1
fi

# Check if we're in the correct directory
if [ ! -f "langgraph.json" ]; then
    echo "❌ Error: langgraph.json not found. Please run this script from the project root."
    exit 1
fi

echo "🚀 Starting LangGraph development server..."
echo "📁 Project directory: $(pwd)"
echo "🔧 LangGraph version: $(langgraph --version 2>/dev/null || echo 'unknown')"
echo ""

# Start the development server
langgraph dev "$@"
