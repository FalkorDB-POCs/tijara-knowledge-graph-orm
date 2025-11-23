#!/bin/bash

# Tijara Knowledge Graph - Startup Script
# This script starts the Tijara API server with all required environment variables
# Usage: ./start_tijara.sh [start|stop|restart|status]

# Set the project directory
PROJECT_DIR="/Users/shaharbiron/Documents/FalkorDB/Poc/LDC/tijara-knowledge-graph-orm"

# Function to stop the service
stop_service() {
    echo "Stopping Tijara service..."
    if lsof -Pi :8080 -sTCP:LISTEN -t > /dev/null 2>&1; then
        lsof -ti:8080 | xargs kill -9 2>/dev/null
        sleep 2
        echo "✅ Service stopped"
        return 0
    else
        echo "ℹ️  No service running on port 8080"
        return 1
    fi
}

# Function to check service status
check_status() {
    if lsof -Pi :8080 -sTCP:LISTEN -t > /dev/null 2>&1; then
        PID=$(lsof -ti:8080)
        echo "✅ Tijara service is RUNNING (PID: $PID)"
        echo "   URL: http://localhost:8080"
        return 0
    else
        echo "❌ Tijara service is NOT RUNNING"
        return 1
    fi
}

# Function to start the service
start_service() {
    echo "======================================================================"
    echo "Starting Tijara Knowledge Graph Solution"
    echo "======================================================================"

# Set OpenAI API Key (must be set in environment or config file)
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  OPENAI_API_KEY not set. Please set it in your environment:"
    echo "   export OPENAI_API_KEY='your-api-key-here'"
    echo "   Or configure it in config/config.yaml"
fi

# Set Python path
export PYTHONPATH="$PROJECT_DIR"

# Check if FalkorDB/Redis is running
echo ""
echo "Checking FalkorDB/Redis status..."
if redis-cli ping > /dev/null 2>&1; then
    echo "✅ FalkorDB/Redis is running"
else
    echo "❌ FalkorDB/Redis is not running!"
    echo "Please start FalkorDB first:"
    echo "  docker run -p 6379:6379 -it --rm falkordb/falkordb"
    echo "  OR"
    echo "  redis-server --loadmodule /path/to/falkordb.so"
    exit 1
fi

    # Check if port 8080 is already in use
    if lsof -Pi :8080 -sTCP:LISTEN -t > /dev/null 2>&1; then
        echo ""
        echo "⚠️  Port 8080 is already in use. Stopping existing process..."
        lsof -ti:8080 | xargs kill -9 2>/dev/null
        sleep 2
    fi

    # Navigate to project directory
    cd "$PROJECT_DIR"

    echo ""
    echo "Starting Tijara API server with ORM..."
    echo "  - API URL: http://localhost:8080"
    echo "  - Web UI: http://localhost:8080"
    echo "  - FalkorDB: localhost:6379 (ldc_graph) with ORM Layer"
    echo "  - Graphiti: Enabled with OpenAI"
    echo ""

    # Start the server in the background
    nohup python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8080 > api.log 2>&1 &

    # Get the process ID
    PID=$!

    echo "Server starting with PID: $PID"
    echo "Logs: $PROJECT_DIR/api.log"
    echo ""

    # Wait a few seconds and check if server started successfully
    sleep 3

    if ps -p $PID > /dev/null 2>&1; then
        echo "✅ Server started successfully!"
        echo ""
        echo "Open your browser at: http://localhost:8080"
        echo ""
        echo "To stop the server, run:"
        echo "  ./start_tijara.sh stop"
        echo "  OR"
        echo "  lsof -ti:8080 | xargs kill -9"
        echo ""
        echo "To restart the server:"
        echo "  ./start_tijara.sh restart"
        echo ""
        echo "To view logs:"
        echo "  tail -f $PROJECT_DIR/api.log"
        echo ""
    else
        echo "❌ Server failed to start. Check logs:"
        echo "  tail -50 $PROJECT_DIR/api.log"
        exit 1
    fi

    echo "======================================================================"
    echo "Tijara Knowledge Graph is ready!"
    echo "======================================================================"
}

# Main script logic - handle command line arguments
COMMAND=${1:-start}

case $COMMAND in
    start)
        start_service
        ;;
    stop)
        stop_service
        ;;
    restart)
        echo "======================================================================"
        echo "Restarting Tijara Knowledge Graph Solution"
        echo "======================================================================"
        echo ""
        stop_service
        echo ""
        sleep 1
        start_service
        ;;
    status)
        check_status
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        echo ""
        echo "Commands:"
        echo "  start   - Start the Tijara service"
        echo "  stop    - Stop the Tijara service"
        echo "  restart - Restart the Tijara service"
        echo "  status  - Check service status"
        echo ""
        exit 1
        ;;
esac
