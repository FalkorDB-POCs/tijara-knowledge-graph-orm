#!/bin/bash
# Restart the Tijara Knowledge Graph API Server

echo "🛑 Stopping API server..."
pkill -f "uvicorn api.main"
sleep 2

echo "🚀 Starting API server with ORM..."
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8080 &

sleep 3

echo "✅ API server restarted"
echo "📊 Access UI at: http://localhost:8080"
echo "🔍 Health check: curl http://localhost:8080/health"
