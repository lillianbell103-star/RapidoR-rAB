#!/bin/bash
# Rapido Rör AB – Start the API Server
# 
# Starts the Node.js lead capture API server on port 3001.
# The server accepts POST /api/lead and stores leads in the Turso database.

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

echo "🚀 Starting Rapido Rör API server..."
echo ""

nohup node server.js > /tmp/rapido-api.log 2>&1 &

PID=$!
echo "✅ API server started (PID: $PID) on port 3001"
echo ""
echo "   Health check:  curl http://localhost:3001/api/health"
echo "   Submit lead:   curl -X POST http://localhost:3001/api/lead \\"
echo "                     -H 'Content-Type: application/json' \\"
echo "                     -d '{\"name\":\"Test\",\"phone\":\"070-123 45 67\",\"email\":\"test@example.com\"}'"
echo ""
echo "   To view leads: open admin.html in your browser"
echo "   To stop:       kill $PID"
echo ""
echo "📋 Logs: tail -f /tmp/rapido-api.log"