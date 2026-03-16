#!/bin/bash
# Give Me a DAY v1 — Setup script
set -e

echo "=== Give Me a DAY v1 Setup ==="

# Backend setup
echo "--- Installing backend dependencies ---"
cd backend
pip install -e ".[dev]"
cd ..

# Frontend setup
echo "--- Installing frontend dependencies ---"
cd frontend
npm install
cd ..

# Create .env if not exists
if [ ! -f .env ]; then
    cp .env.example .env
    echo "--- Created .env from .env.example ---"
fi

# Create data directories
mkdir -p backend/data/{runs,paper_runs,evidence/{price,macro,metadata},audit_log}
echo "--- Created data directories ---"

echo "=== Setup complete ==="
