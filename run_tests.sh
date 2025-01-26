#!/bin/bash

# Check if we have exactly two arguments
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <mode> <test_type>"
    echo "  mode: 'local' or 'docker'"
    echo "  test_type: 'unit' or 'integration'"
    exit 1
fi

MODE=$1
TEST_TYPE=$2

# Validate mode argument
if [[ "$MODE" != "local" && "$MODE" != "docker" ]]; then
    echo "Error: First argument must be either 'local' or 'docker'"
    exit 1
fi

# Validate test type argument and set the appropriate pytest marker
if [[ "$TEST_TYPE" == "unit" ]]; then
    PYTEST_MARKER="'(unit or integration) and not costly'"
elif [[ "$TEST_TYPE" == "integration" ]]; then
    PYTEST_MARKER="'unit or integration'"
else
    echo "Error: Second argument must be either 'unit' or 'integration'"
    exit 1
fi

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
        echo "Executing: python -m pytest tests/ -v -s -m $PYTEST_MARKER"
        eval "python -m pytest tests/ -v -s -m $PYTEST_MARKER"
        exit $?
        ;;
    "docker")
        # Build the Docker image
        docker build -t ganglia:latest . || exit 1
        
        # Show the command that will be run
        echo "Command to be run inside Docker: pytest tests/ -v -s -m $PYTEST_MARKER"
        
        # Run Docker with credentials mount and pass through environment variables
        docker run --rm \
            -v /tmp/gcp-credentials.json:/tmp/gcp-credentials.json \
            -e OPENAI_API_KEY \
            -e GCP_BUCKET_NAME \
            -e GCP_PROJECT_NAME \
            -e SUNO_API_KEY \
            -e GOOGLE_APPLICATION_CREDENTIALS=/tmp/gcp-credentials.json \
            ganglia:latest \
            /bin/sh -c "pytest tests/ -v -s -m $PYTEST_MARKER"
        exit_code=$?
        rm -f /tmp/gcp-credentials.json
        exit $exit_code
        ;;
esac 

