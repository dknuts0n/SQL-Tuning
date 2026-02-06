#!/bin/bash
# Helper script to activate the virtual environment
# Usage: source activate_venv.sh

if [ -d "venv" ]; then
    source venv/bin/activate
    echo "✓ Virtual environment activated"
    echo "Python: $(which python)"
    echo "Pip packages installed:"
    pip list
else
    echo "Error: venv directory not found"
    echo "Run: python3 -m venv venv"
fi
