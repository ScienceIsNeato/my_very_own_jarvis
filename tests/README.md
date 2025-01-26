# GANGLIA Test Suite

This directory contains the test suite for the GANGLIA project. The tests are organized into three main categories:

## Test Categories

### Unit Tests (`tests/unit/`)
Fast tests that verify individual components. Note that despite the name, many of these tests do interact with external services. This is due to:
1. The inherently interconnected nature of GANGLIA's components
2. The desire to test real-world interactions rather than mocked behavior
3. Historical development patterns prioritizing end-to-end verification

TODO: Consider mocking external services where the real service doesn't materially impact the test's purpose. This would:
- Speed up test execution
- Reduce costs
- Make tests more reliable
- Allow offline testing

For now, these tests:
- Run relatively quickly (seconds rather than minutes)
- Test focused functionality
- May require external API access
- Are suitable for running during development

### Third-Party Tests (`tests/third_party/`)
Tests that validate integration with external services. These tests:
- Require external API keys or services
- May incur costs
- Are not run in standard CI pipelines
- Validate third-party service integration
- Good for debugging during development

### Integration Tests (`tests/integration/`)
Tests that verify multiple components working together. These tests:
- May be costly (time/compute)
- Test end-to-end functionality
- Validate system behavior
- Used by CI (Github) to validate:
    - Commits via `[@pytest.mark.unit, @pytest.mark.integration and not @pytest.mark.costly]`
    - Pull Requests via `[@pytest.mark.unit, @pytest.mark.integration]`

## Test Markers

Tests are marked with pytest markers to control execution:

- `@pytest.mark.unit`: Fast tests with no external dependencies
- `@pytest.mark.third_party`: Tests requiring external services
- `@pytest.mark.integration`: Tests of multiple components
- `@pytest.mark.costly`: Time or resource-intensive tests

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
# test_type: 'unit' or 'integration'
#
# unit: Runs tests marked as (unit or integration) and not costly
# integration: Runs all tests marked as unit or integration
```

### Common Test Commands

```bash
# Run unit tests (non-costly) in local mode
./run_tests.sh local unit

# Run all integration tests in Docker
./run_tests.sh docker integration
```

The script automatically:
- Handles environment variables correctly
- Builds the Docker image when needed
- Ensures consistent test execution
- Includes verbose output (-v flag)
- Shows print statements during test execution (-s flag)

### CI Pipeline
The CI pipeline uses the same `run_tests.sh` script with different test types depending on the context:

- On push to main:
  - Runs unit tests (non-costly)
  - `./run_tests.sh docker unit`

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
└── integration/       # Multi-component tests
    ├── ttv/           # TTV integration tests
    └── ...            # Other integration tests
```

## Adding New Tests

1. Place test in appropriate directory based on type
2. Add relevant pytest markers
3. Follow naming convention: `test_*.py`
4. Include docstring explaining test purpose
5. Mark costly tests appropriately