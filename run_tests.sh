#!/bin/bash

# Check if we have the required arguments
if [ "$#" -lt 2 ]; then
    echo "Usage: $0 <mode> <test_target>"
    echo "  mode: 'local' or 'docker'"
    echo "  test_target: pytest target (e.g., 'tests/' or 'tests/unit/test_specific.py::test_function')"
    exit 1
fi

MODE=$1
TEST_TARGET=$2
shift 2  # Remove the first two arguments

# Always use -v and -s flags
PYTEST_FLAGS="-v -s"

# Process remaining arguments to handle -m flag specially
while [[ $# -gt 0 ]]; do
    case $1 in
        -m)
            shift  # Remove -m
            PYTEST_FLAGS="$PYTEST_FLAGS -m '$1'"  # Use single quotes
            shift
            ;;
        *)
            PYTEST_FLAGS="$PYTEST_FLAGS $1"
            shift
            ;;
    esac
done

# Setup Google credentials
if [ -f "/tmp/gcp-credentials.json" ]; then
    echo "[DEBUG] GAC file already exists at /tmp/gcp-credentials.json"
else
    if [ -f "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
        # It's a file path, copy the contents
        echo "[DEBUG] GAC is a file at $GOOGLE_APPLICATION_CREDENTIALS"
        cat "$GOOGLE_APPLICATION_CREDENTIALS" > /tmp/gcp-credentials.json
    else
        # Not a file, assume it's the JSON content
        echo "[DEBUG] GAC is not a file, treating as JSON content"
        echo "$GOOGLE_APPLICATION_CREDENTIALS" > /tmp/gcp-credentials.json
    fi
fi

case $MODE in
    "local")
        echo "Executing: python -m pytest $TEST_TARGET $PYTEST_FLAGS"
        eval "python -m pytest $TEST_TARGET $PYTEST_FLAGS"
        exit $?  # Exit with pytest's exit code
        ;;
    "docker")
        # Build the Docker image
        docker build -t ganglia:latest . || exit 1
        
        # Show the command that will be run
        final_command="pytest \"$TEST_TARGET\" -v -s $(echo $PYTEST_FLAGS | sed 's/-m '\''\([^'\'']*\)'\''/--m "\1"/g')"
        echo "Command to be run inside Docker: $final_command"
        
        # Run Docker with credentials mount and pass through environment variables
        docker run --rm \
            -v /tmp/gcp-credentials.json:/tmp/gcp-credentials.json \
            -e OPENAI_API_KEY \
            -e GCP_BUCKET_NAME \
            -e GCP_PROJECT_NAME \
            -e SUNO_API_KEY \
            -e GOOGLE_APPLICATION_CREDENTIALS=/tmp/gcp-credentials.json \
            ganglia:latest \
            /bin/sh -c "$final_command"
        exit_code=$?
        sudo rm -f /tmp/gcp-credentials.json
        exit $exit_code
        ;;
    *)
        echo "Invalid mode. Use 'local' or 'docker'"
        exit 1
        ;;
esac 

