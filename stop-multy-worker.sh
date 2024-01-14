#!/bin/bash

# Name of the Python script without the extension
SCRIPT_NAME="worker"

# Use pkill to terminate all processes with the name that matches your Python script
pkill -f "$SCRIPT_NAME"

echo "All instances of $SCRIPT_NAME have been terminated."