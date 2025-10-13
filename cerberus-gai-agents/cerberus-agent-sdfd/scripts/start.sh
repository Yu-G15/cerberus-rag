#!/bin/bash

# Cerberus Agent Startup Script

set -e

echo "Starting Cerberus Agent..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Warning: .env file not found. Copying from env.example..."
    cp env.example .env
    echo "Please update .env file with your configuration before running again."
    exit 1
fi

# Check if OpenAI API key is set
if [ -z "$OPENAI_API_KEY" ]; then
    echo "Error: OPENAI_API_KEY environment variable is not set."
    echo "Please set it in your .env file or environment."
    exit 1
fi

# Install dependencies if needed
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing dependencies..."
pip install -e .

# Run database migrations if needed
echo "Running database setup..."
# Add database migration commands here if needed

# Start the application
echo "Starting Cerberus Agent API..."
python -m cerberus_agent.api.main
