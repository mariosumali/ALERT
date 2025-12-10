#!/bin/bash

# Quick start script for local development

echo "🚀 Starting ALERT — Audio-Visual Log Event Recognition Toolkit..."
source .env
if [ -z "$OPENAI_API_KEY" ]; then
  echo "❌ OPENAI_API_KEY not set in .env. Please set it."
  exit 1
fi
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Start services
echo "📦 Starting Docker services..."
docker-compose up -d

# Wait for database to be ready
echo "⏳ Waiting for database to be ready..."
sleep 5

# Initialize database
echo "🗄️  Initializing database..."
docker-compose exec -T backend python init_db.py

echo "✅ Setup complete!"
echo ""
echo "🌐 Frontend: http://localhost:5001"
echo "🔧 Backend API: http://localhost:8000"
echo "📚 API Docs: http://localhost:8000/docs"
echo ""
echo "To view logs: docker-compose logs -f"
echo "To stop: docker-compose down"

