# GANGLIA Test Suite

This directory contains the test suite for the GANGLIA project. The tests are organized into directories based on their type:

## Test Categories

### Unit Tests (`tests/unit/`)
Fast tests that verify individual components. These tests:
- Run quickly (seconds)
- Test focused functionality
- Have minimal external dependencies
- Are suitable for running during development

### Integration Tests (`tests/integration/`)
Tests that verify multiple components working together. These tests:
- May be costly (time/compute)
- Test end-to-end functionality
- Validate system behavior with real external services
- Used by CI (Github) to validate pull requests

### Third-Party Tests (`tests/third_party/`)
Tests that validate integration with external services. These tests:
- Require external API keys or services
- May incur costs
- Are not run in standard CI pipelines
- Validate third-party service integration
- Good for debugging during development

## Test Markers

Tests can be marked with pytest markers to control execution:

- `@pytest.mark.costly`: Time or resource-intensive tests that should be run with caution

## Test Environment

### Required Environment Variables
All tests require certain environment variables to be set. These are managed through `direnv` and should be configured in your `.envrc` file. See the project root's `.envrc.template` for a complete list of required variables and their purposes.

### Media Playback in Tests
Tests that generate audio or video content can optionally play the media for verification. This is controlled by the `PLAYBACK_MEDIA_IN_TESTS` environment variable:

```bash
# Enable media playback (useful for local development)
export PLAYBACK_MEDIA_IN_TESTS="true"

# Disable media playback (default in CI and headless environments)
export PLAYBACK_MEDIA_IN_TESTS="false"
```

## Running Tests

The project includes a `run_tests.sh` script that handles both local and Docker test execution. The script ensures consistent test execution between development and CI environments.

### Usage
```bash
./run_tests.sh <mode> <test_type>

# Arguments:
# mode: 'local' or 'docker'
# test_type: 'unit', 'smoke', or 'integration'
#
# unit: Runs only unit tests
# smoke: Runs only smoke tests
# integration: Runs only integration tests
```

### Common Test Commands

```bash
# Run unit tests in local mode
./run_tests.sh local unit

# Run smoke tests in Docker
./run_tests.sh docker smoke

# Run integration tests in Docker
./run_tests.sh docker integration
```

The script automatically:
- Handles environment variables correctly
- Builds the Docker image when needed
- Ensures consistent test execution
- Includes verbose output (-v flag)
- Shows print statements during test execution (-s flag)
- Saves test output to timestamped log files

### CI Pipeline
The CI pipeline uses the same `run_tests.sh` script with different test types depending on the context:

- On push to branch:
  - Runs unit and smoke tests
  - `./run_tests.sh docker unit && ./run_tests.sh docker smoke`

- On pull request:
  - Runs all integration tests
  - `./run_tests.sh docker integration`

Note: Third-party tests are never run in CI and must be run manually during development.
      These are for things such as: checking why your mic is not working, or why the SUNO API is not working.

## Directory Structure
```
tests/
├── unit/               # Fast, isolated tests
│   ├── ttv/           # Text-to-Video unit tests
│   └── ...            # Other unit tests
├── third_party/       # External service tests
│   ├── ttv/           # TTV third-party tests
│   └── ...            # Other third-party tests
├── smoke/             # Smoke tests
│   ├── ttv/           # TTV smoke tests
│   └── ...            # Other smoke tests
├── integration/       # Multi-component tests
    ├── ttv/           # TTV integration tests
    └── ...            # Other integration tests
```

## Adding New Tests

1. Place test in appropriate directory based on type
2. Add relevant pytest markers
3. Follow naming convention: `test_*.py`
4. Include docstring explaining test purpose
5. Mark costly tests appropriately (integration or third-party only)