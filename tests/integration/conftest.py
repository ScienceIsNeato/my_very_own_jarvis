import os
import json
import pytest
from pathlib import Path

@pytest.fixture
def test_data_dir():
    """Return the path to the test data directory."""
    return Path(__file__).parent / "test_data"

@pytest.fixture
def base_ttv_config(test_data_dir):
    """Return a basic TTV config for testing."""
    return {
        "style": "digital art",
        "story": [
            "A mysterious figure emerges from the shadows",
            "They walk through a glowing portal of swirling energy",
            "Strange symbols float in the air around them",
            "The portal closes with a thunderous boom",
            "Everything returns to darkness"
        ],
        "title": "Integration Test Video",
        "background_music": {
            "sources": [
                {
                    "type": "file",
                    "path": str(test_data_dir / "background_music.mp3"),
                    "enabled": True
                }
            ]
        },
        "closing_credits": {
            "sources": [
                {
                    "type": "file",
                    "path": str(test_data_dir / "short_closing_credits.mp3"),
                    "enabled": True
                }
            ]
        }
    }

@pytest.fixture
def ttv_config_file(test_data_dir, base_ttv_config):
    """Create and return path to a TTV config file."""
    os.makedirs(test_data_dir, exist_ok=True)
    config_path = test_data_dir / "ttv_config.json"
    
    with open(config_path, "w") as f:
        json.dump(base_ttv_config, f, indent=2)
    
    return config_path

@pytest.fixture
def ganglia_cli():
    """Return the path to the GANGLIA CLI script."""
    return Path(os.environ["GANGLIA_HOME"]) / "ganglia.py" 