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
            PYTEST_FLAGS="$PYTEST_FLAGS -m \"$1\""  # Add double quotes around the marker expression
            shift
            ;;
        *)
            PYTEST_FLAGS="$PYTEST_FLAGS $1"
            shift
            ;;
    esac
done

# Setup Google credentials
if [ -f "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
    # It's a file path, copy the contents
    echo "[DEBUG] GAC is a file at $GOOGLE_APPLICATION_CREDENTIALS"
    echo "[DEBUG] Original file contents:"
    cat "$GOOGLE_APPLICATION_CREDENTIALS"
    cat "$GOOGLE_APPLICATION_CREDENTIALS" > /tmp/gcp-credentials.json
    echo "[DEBUG] Copied to /tmp/gcp-credentials.json. New file contents:"
    cat /tmp/gcp-credentials.json
else
    # Not a file, assume it's the JSON content
    echo "[DEBUG] GAC is not a file, treating as JSON content"
    echo "$GOOGLE_APPLICATION_CREDENTIALS" > /tmp/gcp-credentials.json
    echo "[DEBUG] Written to /tmp/gcp-credentials.json. File contents:"
    cat /tmp/gcp-credentials.json
fi

case $MODE in
    "local")
        echo "Executing: python -m pytest $TEST_TARGET $PYTEST_FLAGS"
        eval "python -m pytest $TEST_TARGET $PYTEST_FLAGS"
        exit $?  # Exit with pytest's exit code
        ;;
    "docker")
        # Build the Docker image
        echo "[DEBUG] Building Docker image..."
        docker build -t ganglia:latest . || exit 1
        
        echo "[DEBUG] Before Docker run:"
        echo "GAC location: $GOOGLE_APPLICATION_CREDENTIALS"
        echo "GAC contents:"
        cat $GOOGLE_APPLICATION_CREDENTIALS
        echo "/tmp contents:"
        cat /tmp/gcp-credentials.json
        
        echo "[DEBUG] Running Docker container..."
        # Run Docker with credentials mount and pass through environment variables
        docker run --rm \
            -v /tmp/gcp-credentials.json:/tmp/gcp-credentials.json \
            -e OPENAI_API_KEY \
            -e GCP_BUCKET_NAME \
            -e GCP_PROJECT_NAME \
            -e SUNO_API_KEY \
            -e GOOGLE_APPLICATION_CREDENTIALS=/tmp/gcp-credentials.json \
            ganglia:latest \
            /bin/sh -c "echo '[DEBUG] Inside Docker container:' && \
                       echo 'GAC location:' && \
                       echo \$GOOGLE_APPLICATION_CREDENTIALS && \
                       echo 'GAC contents:' && \
                       cat \$GOOGLE_APPLICATION_CREDENTIALS && \
                       pytest \"$TEST_TARGET\" $PYTEST_FLAGS"
        exit_code=$?
        rm -f /tmp/gcp-credentials.json
        exit $exit_code
        ;;
    *)
        echo "Invalid mode. Use 'local' or 'docker'"
        exit 1
        ;;
esac 

