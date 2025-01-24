# GANGLIA Test Suite

This directory contains the test suite for the GANGLIA project. The tests are organized into three main categories:

## Test Categories

### Unit Tests (`tests/unit/`)
Fast tests that verify individual components in isolation. These tests:
- Have no external dependencies
- Run quickly (milliseconds)
- Test a single unit of functionality
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

## Running Tests

### Development
```bash
# Run unit tests (fast, no external dependencies)
pytest -m unit

# Run specific test directory
pytest tests/unit/ttv/

# Run all tests except costly ones
pytest -m "not costly"
```

### CI Pipeline
```bash
# On commit (unit tests only)
pytest -m unit

# On PR (unit tests + cheap integration tests)
pytest -m "unit or (integration and not costly)"

# Full test suite
pytest
```

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