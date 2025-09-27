#!/bin/bash

# KAG-LangGraph Pipeline Server Startup Script
# This script helps start the server with proper configuration

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default configuration
DEFAULT_HOST="0.0.0.0"
DEFAULT_PORT="8000"
DEFAULT_RELOAD="false"
DEFAULT_LOG_LEVEL="info"

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if dependencies are installed
check_dependencies() {
    print_info "Checking dependencies..."
    
    # Check if uv is available
    if ! command -v uv &> /dev/null; then
        print_error "uv is not installed or not in PATH. Please install uv first."
        exit 1
    fi

    # Check if required packages are installed
    uv run python -c "import fastapi, uvicorn" 2>/dev/null || {
        print_warning "FastAPI or uvicorn not found. Installing dependencies..."
        uv pip install fastapi uvicorn || {
            print_error "Failed to install dependencies. Please run: uv pip install fastapi uvicorn"
            exit 1
        }
    }
    
    print_success "Dependencies check passed"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --host HOST        Host to bind to (default: $DEFAULT_HOST)"
    echo "  -p, --port PORT        Port to listen on (default: $DEFAULT_PORT)"
    echo "  -r, --reload           Enable auto-reload for development"
    echo "  -l, --log-level LEVEL  Log level (default: $DEFAULT_LOG_LEVEL)"
    echo "  --help                 Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Start with defaults"
    echo "  $0 --host 127.0.0.1 --port 8080     # Custom host and port"
    echo "  $0 --reload --log-level debug        # Development mode"
}

# Parse command line arguments
HOST="$DEFAULT_HOST"
PORT="$DEFAULT_PORT"
RELOAD="$DEFAULT_RELOAD"
LOG_LEVEL="$DEFAULT_LOG_LEVEL"

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--host)
            HOST="$2"
            shift 2
            ;;
        -p|--port)
            PORT="$2"
            shift 2
            ;;
        -r|--reload)
            RELOAD="true"
            shift
            ;;
        -l|--log-level)
            LOG_LEVEL="$2"
            shift 2
            ;;
        --help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Main execution
main() {
    print_info "Starting KAG-LangGraph Pipeline Server..."
    
    # Check dependencies
    check_dependencies
    
    # Set environment variables
    export SERVER_HOST="$HOST"
    export SERVER_PORT="$PORT"
    export SERVER_RELOAD="$RELOAD"
    export LOG_LEVEL="$LOG_LEVEL"
    
    # Print configuration
    print_info "Server configuration:"
    echo "  Host: $HOST"
    echo "  Port: $PORT"
    echo "  Reload: $RELOAD"
    echo "  Log Level: $LOG_LEVEL"
    echo ""
    
    # Check if port is available
    if command -v netstat &> /dev/null; then
        if netstat -tuln | grep -q ":$PORT "; then
            print_warning "Port $PORT appears to be in use"
        fi
    fi
    
    print_info "Starting server..."
    print_info "API documentation will be available at: http://$HOST:$PORT/docs"
    print_info "Press Ctrl+C to stop the server"
    echo ""
    
    # Start the server
    if [ "$RELOAD" = "true" ]; then
        uv run uvicorn sever:app --host "$HOST" --port "$PORT" --reload --log-level "$LOG_LEVEL"
    else
        uv run python sever.py
    fi
}

# Run main function
main "$@"
