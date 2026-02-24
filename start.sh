#!/bin/bash
set -e

echo "🚀 Starting NEXUS IMS Backend..."

# Change to backend directory
cd backend

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install --no-cache-dir -r requirements.txt

# Run database migrations
echo "🗄️ Running database migrations..."
alembic upgrade head

# Start the FastAPI application
echo "⚡ Starting FastAPI server..."
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
