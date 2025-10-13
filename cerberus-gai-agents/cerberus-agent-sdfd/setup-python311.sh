#!/bin/bash

# Cerberus Agent - Python 3.11 Virtual Environment Setup Script
# This script sets up a Python 3.11 virtual environment for the project

set -e  # Exit on any error

echo "🐍 Cerberus Agent - Python 3.11 Setup"
echo "======================================"

# Check if Python 3.11 is available
if ! command -v python3.11 &> /dev/null; then
    echo "❌ Python 3.11 is not installed on your system."
    echo ""
    echo "Please install Python 3.11 first:"
    echo "1. Go to https://www.python.org/downloads/release/python-3119/"
    echo "2. Download the macOS installer (.pkg file)"
    echo "3. Run the installer and follow the installation wizard"
    echo "4. Then run this script again"
    echo ""
    exit 1
fi

echo "✅ Python 3.11 found: $(python3.11 --version)"

# Navigate to project directory
cd "$(dirname "$0")"

# Remove existing virtual environment if it exists
if [ -d "venv" ]; then
    echo "🗑️  Removing existing virtual environment..."
    rm -rf venv
fi

# Create new virtual environment with Python 3.11
echo "🔨 Creating virtual environment with Python 3.11..."
python3.11 -m venv venv

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
python -m pip install --upgrade pip

# Install project dependencies
echo "📦 Installing project dependencies..."
pip install -e .

# Install development dependencies
echo "🛠️  Installing development dependencies..."
pip install "langgraph-cli[inmem]>=0.1.71"

echo ""
echo "🎉 Setup complete!"
echo ""
echo "To activate the virtual environment manually:"
echo "  source venv/bin/activate"
echo ""
echo "To start the development server:"
echo "  make dev"
echo "  # or"
echo "  ./start-langgraph.sh"
echo ""
echo "To deactivate the virtual environment:"
echo "  deactivate"
