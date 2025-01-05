import os
import openai
from datetime import datetime

openai.api_key = os.environ.get("OPENAI_API_KEY")

def get_tempdir():
    """
    Get the temporary directory in a platform-agnostic way.
    Creates and returns /tmp/GANGLIA for POSIX systems or %TEMP%/GANGLIA for Windows.
    """
    if os.name == 'posix':
        base_dir = '/tmp/GANGLIA'
    else:
        import tempfile
        base_dir = os.path.join(tempfile.gettempdir(), "GANGLIA")
    
    os.makedirs(base_dir, exist_ok=True)
    return base_dir

# Alias for backward compatibility
get_tmp_dir = get_tempdir
setup_tmp_dir = get_tempdir  # This will create the directory as a side effect