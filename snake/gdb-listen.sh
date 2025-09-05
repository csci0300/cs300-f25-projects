#!/bin/bash

# Build snake and check if it succeeded
echo "Building snake..."
if ! make snake; then
    echo "ERROR: Failed to build snake"
    exit 1
fi

# Make sure there is a snake program
if [ ! -e ./snake ]; then
    echo "ERROR: Could not start gdb; snake program not found after running `make`"
    exit 1
fi

echo "Starting gdbserver on port 12345..."
gdbserver :12345 ./snake ${@: 1}


