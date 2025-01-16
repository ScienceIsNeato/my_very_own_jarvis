import os
import pytest
import subprocess
import time
from pathlib import Path

def test_basic_ttv_pipeline(ganglia_cli, ttv_config_file):
    """Test the basic text-to-video pipeline end-to-end."""
    cmd = [
        "python3",
        str(ganglia_cli),
        "--text-to-video",
        "--ttv-config", str(ttv_config_file)
    ]
    
    print(f"\nRunning command: {' '.join(cmd)}")
    
    # Run the command without capturing output
    try:
        start_time = time.time()
        result = subprocess.run(
            cmd,
            env=os.environ.copy(),  # Use current environment including PYTHONPATH
            text=True,
            check=False  # Don't raise on non-zero exit
        )
        total_time = time.time() - start_time
        
        print(f"\nProcess completed with return code: {result.returncode}")
        print(f"Total execution time: {total_time:.2f} seconds")
        
        # Verify the output video exists
        output_dir = Path("/tmp/GANGLIA/ttv")
        video_files = list(output_dir.glob("final_output*.mp4"))
        
        if len(video_files) > 0:
            video_size = video_files[0].stat().st_size
            print(f"\nGenerated video file: {video_files[0]}")
            print(f"Video size: {video_size / 1024 / 1024:.2f} MB")
            
            # Only fail if we got no video output
            assert video_size > 0, f"Output video file is empty: {video_files[0]}"
        else:
            pytest.fail("No output video file found")
        
    except subprocess.CalledProcessError as e:
        pytest.fail(f"Pipeline failed with error:\nSTDOUT:\n{e.stdout}\nSTDERR:\n{e.stderr}") 