#!/bin/bash
# BLE Scanner Launch Script

# Check for Ubertooth
if ! command -v ubertooth-btle &> /dev/null; then
    echo "ERROR: ubertooth-btle command not found."
    echo "Please install Ubertooth tools before running this script."
    exit 1
fi

# Check for Python packages
if ! python3 -c "import flask" &> /dev/null; then
    echo "Installing required Python packages..."
    pip3 install flask
fi

# Create templates directory if needed
mkdir -p templates

# Check Ubertooth connectivity
echo "Checking Ubertooth device..."
if ubertooth-util -v &> /dev/null; then
    echo "Ubertooth device found!"
else
    echo "WARNING: Ubertooth device not detected or not responding."
    echo "Make sure it's properly connected and powered on."
    echo "Do you want to continue anyway? (y/n)"
    read answer
    if [[ ! "$answer" =~ ^[Yy]$ ]]; then
        echo "Exiting..."
        exit 1
    fi
fi

# Start the application
echo "Starting BLE Scanner..."
python3 app.py
