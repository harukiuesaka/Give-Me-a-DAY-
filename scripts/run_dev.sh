#!/bin/bash
# Give Me a DAY v1 — Development server launcher
set -e

echo "=== Starting Give Me a DAY v1 ==="

# Start backend
echo "--- Starting backend (FastAPI) on port 8000 ---"
cd backend
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

# Start frontend
echo "--- Starting frontend (Vite) on port 3000 ---"
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "Backend:  http://localhost:8000"
echo "Frontend: http://localhost:3000"
echo "API docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop both servers."

# Trap Ctrl+C to kill both processes
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM

wait
