#!/bin/bash
# Test binary module that outputs JSON

# Parse arguments (format: key=value)
for arg in "$@"; do
    if [[ $arg == *"="* ]]; then
        key="${arg%%=*}"
        value="${arg#*=}"
        eval "$key='$value'"
    fi
done

# Output JSON result
echo "{\"changed\": false, \"msg\": \"Binary module executed\", \"args\": \"$*\"}"
