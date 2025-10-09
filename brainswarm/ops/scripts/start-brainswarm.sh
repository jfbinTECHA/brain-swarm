#!/bin/bash

# Start BrainSwarm API
echo "🚀 Starting BrainSwarm API..."
/home/sysop/brainswarm/venv/bin/python -m uvicorn brainswarm.main:app --host 0.0.0.0 --port 8001 &

# Wait a bit for API to start
sleep 5

# Start ngrok tunnel
echo "🌐 Starting ngrok tunnel..."
ngrok http 8001 &

# Wait for ngrok to establish
sleep 5

echo "✅ BrainSwarm API and ngrok tunnel started."
echo "📡 Check ngrok status at http://localhost:4040"

# Keep running
wait