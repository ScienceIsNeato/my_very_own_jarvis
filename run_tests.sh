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
EXTRA_ARGS="$@"  # Capture any remaining arguments

# Always use -v and -s flags
PYTEST_FLAGS="-v -s $EXTRA_ARGS"

# Function to build Docker run command with optional credentials
build_docker_cmd() {
    local cmd="docker run --rm"
    
    # Add Google credentials mount if available
    if [ ! -z "$GOOGLE_APPLICATION_CREDENTIALS" ] && [ -f "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
        cmd="$cmd -v \"$GOOGLE_APPLICATION_CREDENTIALS:/tmp/gcp-credentials.json\""
        cmd="$cmd --env GOOGLE_APPLICATION_CREDENTIALS=/tmp/gcp-credentials.json"
    fi
    
    # Add environment variables from stdin
    cmd="$cmd --env-file /dev/stdin"
    
    # Add image and test command
    cmd="$cmd ganglia:latest /bin/sh -c \"pytest $TEST_TARGET $PYTEST_FLAGS\""
    
    echo "$cmd"
}

case $MODE in
    "local")
        python -m pytest $TEST_TARGET $PYTEST_FLAGS
        ;;
    "docker")
        # Build the Docker image first
        docker build -t ganglia:latest . || exit 1
        
        # Run the tests in Docker with environment variables
        printenv | grep -v ' ' > temp.env
        docker run --rm --env-file temp.env ganglia:latest pytest $TEST_TARGET $PYTEST_FLAGS
        rm temp.env
        ;;
    *)
        echo "Invalid mode. Use 'local' or 'docker'"
        exit 1
        ;;
esac 
