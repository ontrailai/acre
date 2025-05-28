#!/bin/bash

# Script to restart the Lease Logik backend server

echo "🚀 Starting Lease Logik Backend Server..."

# Navigate to backend directory
cd /Users/ryanwatson/Desktop/acre/backend

# Activate virtual environment
source venv/bin/activate

# Export environment variables from .env file
set -a
source .env
set +a

# Run the server
echo "📡 Starting server on http://127.0.0.1:8000"
echo "📝 Logs will appear below..."
echo "🛑 Press Ctrl+C to stop the server"
echo ""

uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
