import os
import openai
from datetime import datetime
import tempfile

openai.api_key = os.environ.get("OPENAI_API_KEY")

def get_tempdir():
    """
    Get the temporary directory in a platform-agnostic way.
    Creates and returns /tmp/GANGLIA for POSIX systems or %TEMP%/GANGLIA for Windows.
    """
    temp_dir = os.path.join(tempfile.gettempdir(), 'GANGLIA')
    os.makedirs(temp_dir, exist_ok=True)
    return temp_dir

# Alias for backward compatibility
get_tmp_dir = get_tempdir
setup_tmp_dir = get_tempdir  # This will create the directory as a side effect

def get_config_path():
    """Get the path to the config directory relative to the project root."""
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'ganglia_config.json')