#!/usr/bin/env bash

# Healthcare RAG Startup Script (improved)
# - Interactive menu for Docker vs local
# - Local options: backend-only, backend+frontend, backend+streamlit
# - Respects existing .venv and allows skipping installs via flags

set -euo pipefail

ROOT_DIR=$(cd "$(dirname "$0")" && pwd)
cd "$ROOT_DIR"

echo "🏥 Healthcare RAG - Quick Start"
echo "========================================"

print_menu() {
    echo "Choose how to run the app:"
    echo "  1) Docker (recommended)"
    echo "  2) Local (backend + React frontend)"
    echo "  3) Local (backend + Streamlit UI)"
    echo "  4) Local (backend only)"
    echo "  5) Stop / Exit"
}

if [[ ${1:-} == "--help" || ${1:-} == "-h" ]]; then
    print_menu
    echo
    echo "You can pass one of the menu numbers as the first argument to skip the prompt."
    exit 0
fi

CHOSEN=""
if [[ -n "${1:-}" && "$1" =~ ^[1-5]$ ]]; then
    CHOSEN="$1"
else
    # If docker-compose is installed, default to Docker
    if command -v docker >/dev/null 2>&1 && command -v docker-compose >/dev/null 2>&1; then
        echo "Docker detected. Press Enter to run with Docker (recommended) or choose another option."
        print_menu
        read -rp "Select an option [1-5] (default 1): " CHOSEN
        CHOSEN=${CHOSEN:-1}
    else
        print_menu
        read -rp "Select an option [2-5] (default 2): " CHOSEN
        CHOSEN=${CHOSEN:-2}
    fi
fi

run_docker() {
    echo "� Starting Healthcare RAG with Docker Compose..."
    docker-compose up --build -d
    echo "✅ Application started via Docker"
    echo "Backend: http://localhost:8000  Frontend: http://localhost:3000"
}

ensure_venv() {
    if [ ! -d ".venv" ]; then
        echo "Creating project virtual environment at ./.venv..."
        python3 -m venv ./.venv
    fi
    # shellcheck source=/dev/null
    source ./.venv/bin/activate
}

install_python_deps() {
    if [ -f "requirements.txt" ]; then
        echo "Installing Python dependencies (requirements.txt)..."
        pip install --upgrade pip
        pip install -r requirements.txt
    else
        echo "requirements.txt not found; skipping Python dependency install"
    fi
}

start_backend() {
    echo "🚀 Starting backend server (uvicorn)..."
    # use python -m uvicorn to ensure venv's python is used
    python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 &
    BACKEND_PID=$!
    echo "Backend PID: $BACKEND_PID"
}

start_frontend() {
    echo "🔧 Starting React frontend (Vite)..."
    cd frontend
    if ! command -v npm >/dev/null 2>&1; then
        echo "npm not found. Please install Node.js/npm or run Docker option."
        cd "$ROOT_DIR"
        return 1
    fi
    if [ ! -d "node_modules" ]; then
        npm install
    fi
    npm run dev &
    FRONTEND_PID=$!
    echo "Frontend PID: $FRONTEND_PID"
    cd "$ROOT_DIR"
}

start_streamlit() {
    echo "🔧 Starting Streamlit UI..."
    cd frontend
    if ! command -v streamlit >/dev/null 2>&1; then
        echo "streamlit not found in PATH. Installing into venv..."
        pip install streamlit
    fi
    streamlit run frontend/app_streamlit.py &
    STREAMLIT_PID=$!
    echo "Streamlit PID: $STREAMLIT_PID"
    cd "$ROOT_DIR"
}

case "$CHOSEN" in
    1)
        run_docker
        exit 0
        ;;
    2)
        ensure_venv
        install_python_deps
        start_backend
        start_frontend || true
        ;;
    3)
        ensure_venv
        install_python_deps
        start_backend
        start_streamlit
        ;;
    4)
        ensure_venv
        install_python_deps
        start_backend
        ;;
    *)
        echo "Exiting. No services started."; exit 0
        ;;
esac

echo ""
echo "Services started. URLs:"
echo "  Backend: http://localhost:8000"
echo "  API docs: http://localhost:8000/docs"
echo "  Frontend (Vite): http://localhost:3000  (if running)"
echo "  Streamlit: http://localhost:8501  (if running)"

trap 'echo "Stopping services..."; kill ${BACKEND_PID:-} ${FRONTEND_PID:-} ${STREAMLIT_PID:-} 2>/dev/null || true; exit' INT TERM

# Wait for background processes (simple sleep loop)
while true; do
    sleep 2
done
