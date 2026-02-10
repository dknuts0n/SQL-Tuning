#!/bin/bash

# MySQL Index Analysis Tool Runner Script
# Automatically activates venv, loads environment, and runs the tool

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    print_error "Virtual environment not found!"
    print_info "Creating virtual environment..."
    python3 -m venv venv
    print_info "Installing dependencies..."
    source venv/bin/activate
    pip install -r requirements.txt
else
    # Activate virtual environment
    source venv/bin/activate
fi

# Load environment variables from .env if it exists
if [ -f ".env" ]; then
    print_info "Loading environment variables from .env"
    set -a
    source .env
    set +a
elif [ ! -f ".env" ] && [ -z "$MYSQL_HOST" ]; then
    print_warn "No .env file found and MYSQL_HOST not set"
    print_info "Copy .env.example to .env and configure your database credentials"
    echo ""
    echo "Example:"
    echo "  cp .env.example .env"
    echo "  # Edit .env with your database credentials"
    echo ""
fi

# Check if MySQL credentials are set
if [ -z "$MYSQL_HOST" ] || [ -z "$MYSQL_USER" ] || [ -z "$MYSQL_PASSWORD" ]; then
    print_error "Missing required MySQL credentials!"
    echo ""
    echo "Required environment variables:"
    echo "  MYSQL_HOST     - Database host (e.g., localhost)"
    echo "  MYSQL_USER     - Database username"
    echo "  MYSQL_PASSWORD - Database password"
    echo "  MYSQL_DATABASE - Target database (optional, scans all if not set)"
    echo ""
    echo "Set them in .env file or export them before running this script"
    exit 1
fi

# Show what we're connecting to (without showing password)
print_info "Connecting to MySQL: ${MYSQL_USER}@${MYSQL_HOST}:${MYSQL_PORT:-3306}"
if [ -n "$MYSQL_DATABASE" ]; then
    print_info "Target database: $MYSQL_DATABASE"
else
    print_info "Target: All databases"
fi

echo ""

# Run the index analyzer with all passed arguments
print_info "Running index analysis..."
python find_unused_indexes.py "$@"

# Deactivate virtual environment
deactivate
