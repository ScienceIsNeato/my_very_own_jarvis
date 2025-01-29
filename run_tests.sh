#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Load direnv if available
if command -v direnv >/dev/null 2>&1; then
    eval "$(direnv export bash)"
fi

# Check if we have exactly two arguments
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <mode> <test_type>"
    echo "  mode: 'local' or 'docker'"
    echo "  test_type: 'unit', 'smoke', or 'integration'"
    exit 1
fi

MODE=$1
TEST_TYPE=$2

# Create logs directory if it doesn't exist
mkdir -p "${SCRIPT_DIR}/logs"

# Generate timestamp for log file
TIMESTAMP=$(date +"%Y-%m-%d-%H-%M-%S")
LOG_FILE="${SCRIPT_DIR}/logs/test_run_${MODE}_${TEST_TYPE}_${TIMESTAMP}.log"

# Validate mode argument
if [[ "$MODE" != "local" && "$MODE" != "docker" ]]; then
    echo "Error: First argument must be either 'local' or 'docker'" | tee -a "$LOG_FILE"
    exit 1
fi

# Validate test type argument and set the appropriate test directory
if [[ "$TEST_TYPE" == "unit" ]]; then
    TEST_DIR="tests/unit/"
elif [[ "$TEST_TYPE" == "smoke" ]]; then
    TEST_DIR="tests/smoke/"
elif [[ "$TEST_TYPE" == "integration" ]]; then
    TEST_DIR="tests/integration/"
else
    echo "Error: Second argument must be either 'unit', 'smoke', or 'integration'" | tee -a "$LOG_FILE"
    exit 1
fi

# Setup Google credentials
if [ -f "/tmp/gcp-credentials.json" ]; then
    echo "[DEBUG] GAC file already exists at /tmp/gcp-credentials.json" | tee -a "$LOG_FILE"
else
    if [ -f "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
        # It's a file path, copy the contents
        echo "[DEBUG] GAC is a file at $GOOGLE_APPLICATION_CREDENTIALS" | tee -a "$LOG_FILE"
        cat "$GOOGLE_APPLICATION_CREDENTIALS" > /tmp/gcp-credentials.json
    else
        # Not a file, assume it's the JSON content
        echo "[DEBUG] GAC is not a file, treating as JSON content" | tee -a "$LOG_FILE"
        echo "$GOOGLE_APPLICATION_CREDENTIALS" > /tmp/gcp-credentials.json
    fi
fi

case $MODE in
    "local")
        echo "Executing: python -m pytest ${TEST_DIR} -v -s" | tee -a "$LOG_FILE"
        eval "python -m pytest ${TEST_DIR} -v -s" 2>&1 | tee -a "$LOG_FILE"
        exit ${PIPESTATUS[0]}
        ;;
    "docker")
        # Build the Docker image
        docker build -t ganglia:latest . 2>&1 | tee -a "$LOG_FILE" || exit 1
        
        # Show the command that will be run
        echo "Command to be run inside Docker: pytest ${TEST_DIR} -v -s" | tee -a "$LOG_FILE"
        
        # Run Docker with credentials mount and pass through environment variables
        docker run --rm \
            -v /tmp/gcp-credentials.json:/tmp/gcp-credentials.json \
            -e OPENAI_API_KEY \
            -e GCP_BUCKET_NAME \
            -e GCP_PROJECT_NAME \
            -e SUNO_API_KEY \
            -e GOOGLE_APPLICATION_CREDENTIALS=/tmp/gcp-credentials.json \
            ganglia:latest \
            /bin/sh -c "pytest ${TEST_DIR} -v -s" 2>&1 | tee -a "$LOG_FILE"
        exit_code=${PIPESTATUS[0]}
        rm -f /tmp/gcp-credentials.json
        exit $exit_code
        ;;
esac 

