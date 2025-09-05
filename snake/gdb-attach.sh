#!/bin/bash

echo "Connecting to GDB on localhost:12345..."

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

gdb  -iex="target remote localhost:12345"

