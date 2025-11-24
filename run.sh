#!/bin/bash
# Toyota Race Suite - Cross-platform launcher script
# Works on macOS and Linux

cd "$(dirname "$0")"

# Check if venv exists
if [ ! -f "venv/bin/python" ]; then
    echo "============================================"
    echo "  First-time setup - Creating environment"
    echo "============================================"
    echo ""

    # Create virtual environment
    echo "Creating virtual environment..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo ""
        echo "ERROR: Failed to create virtual environment"
        echo "Please install Python 3.10+ from https://python.org"
        echo ""
        read -p "Press Enter to exit..."
        exit 1
    fi

    # Activate and install dependencies
    echo "Installing dependencies (this may take a minute)..."
    source venv/bin/activate
    pip install --upgrade pip > /dev/null 2>&1
    pip install -r requirements.txt

    if [ $? -ne 0 ]; then
        echo ""
        echo "ERROR: Failed to install dependencies"
        echo ""
        read -p "Press Enter to exit..."
        exit 1
    fi

    echo ""
    echo "============================================"
    echo "  Setup complete! Starting application..."
    echo "============================================"
    echo ""
fi

# Run the application
echo "Starting Race Replay..."
venv/bin/python -m src.app.main

# If app exits with error, pause so user can see
if [ $? -ne 0 ]; then
    echo ""
    echo "Application exited with error code $?"
    read -p "Press Enter to exit..."
fi
