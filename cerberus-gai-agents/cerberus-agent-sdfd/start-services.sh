#!/bin/bash

# Cerberus GAI Agents with LangGraph Studio Startup Script

echo "🚀 Starting Cerberus GAI Agents with LangGraph Studio..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from .env.example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "📝 Please edit .env file with your API keys and configuration."
    else
        echo "❌ .env.example file not found. Please create .env file manually."
        exit 1
    fi
fi

# Build and start services
echo "🔨 Building and starting services..."
docker-compose up --build -d

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check service health
echo "🏥 Checking service health..."

# Check GAI Agents service
if curl -f http://localhost:8001/health/ > /dev/null 2>&1; then
    echo "✅ GAI Agents service is running on http://localhost:8001"
else
    echo "❌ GAI Agents service is not responding"
fi

# Check LangGraph Studio
if curl -f http://localhost:8123/ > /dev/null 2>&1; then
    echo "✅ LangGraph Studio is running on http://localhost:8123"
else
    echo "⏳ LangGraph Studio is starting up (may take a moment)..."
fi

# Check Nginx
if curl -f http://localhost/health/ > /dev/null 2>&1; then
    echo "✅ Nginx proxy is running on http://localhost"
    echo "🌐 LangGraph Studio available at: http://localhost/studio/"
else
    echo "❌ Nginx proxy is not responding"
fi

echo ""
echo "🎯 Services Summary:"
echo "   • GAI Agents API: http://localhost:8001"
echo "   • LangGraph Studio: http://localhost:8123"
echo "   • Nginx Proxy: http://localhost"
echo "   • LangGraph Studio (via proxy): http://localhost/studio/"
echo ""
echo "📊 To view logs: docker-compose logs -f"
echo "🛑 To stop services: docker-compose down"
echo ""
echo "🎉 Setup complete! Happy coding!"
