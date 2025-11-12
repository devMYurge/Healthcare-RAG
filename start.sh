#!/bin/bash

# Healthcare RAG Startup Script
# This script helps you set up and run the Healthcare RAG application

set -e

echo "🏥 Healthcare RAG Setup & Startup Script"
echo "========================================"
echo ""

# Check if Docker is installed
if command -v docker &> /dev/null && command -v docker-compose &> /dev/null; then
    echo "✅ Docker and Docker Compose found"
    echo ""
    echo "Would you like to run with Docker? (recommended) [Y/n]"
    read -r use_docker
    
    if [[ "$use_docker" != "n" && "$use_docker" != "N" ]]; then
        echo ""
        echo "🐳 Starting Healthcare RAG with Docker..."
        docker-compose up --build -d
        echo ""
        echo "✅ Application started successfully!"
        echo ""
        echo "📍 Backend API: http://localhost:8000"
        echo "📍 Frontend UI: http://localhost:3000"
        echo "📍 API Docs: http://localhost:8000/docs"
        echo ""
        echo "To view logs: docker-compose logs -f"
        echo "To stop: docker-compose down"
        exit 0
    fi
fi

echo ""
echo "📦 Setting up local development environment..."
echo ""

# Backend setup
echo "🔧 Setting up backend..."
cd backend

if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing Python dependencies..."
pip install -r requirements.txt

echo "✅ Backend setup complete!"
echo ""

# Start backend in background
echo "🚀 Starting backend server..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
echo "Backend running with PID: $BACKEND_PID"

cd ..

# Frontend setup
echo ""
echo "🔧 Setting up frontend..."
cd frontend

if [ ! -d "node_modules" ]; then
    echo "Installing Node.js dependencies..."
    npm install
fi

echo "✅ Frontend setup complete!"
echo ""

# Start frontend
echo "🚀 Starting frontend server..."
npm run dev &
FRONTEND_PID=$!
echo "Frontend running with PID: $FRONTEND_PID"

cd ..

echo ""
echo "✅ Application started successfully!"
echo ""
echo "📍 Backend API: http://localhost:8000"
echo "📍 Frontend UI: http://localhost:3000"
echo "📍 API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Wait for Ctrl+C
trap "echo ''; echo 'Stopping services...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT
wait
