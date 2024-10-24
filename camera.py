import cv2
import os
import time
import tempfile

class Camera:
    """Camera class to handle image capture and processing."""

    def __init__(self, video_src=0):
        self.video_src = video_src
        self.cam = None
        self.initialize_camera()

    def initialize_camera(self):
        """Initialize the camera."""
        self.cam = cv2.VideoCapture(self.video_src)
        if not self.cam.isOpened():
            raise RuntimeError("Failed to open camera.")
        print("Camera initialized successfully.")

    def capture_image(self):
        """Capture an image and return the file path."""
        ret, frame = self.cam.read()
        if not ret:
            raise RuntimeError("Failed to capture image.")

        # Save the image to a temporary directory
        temp_dir = tempfile.gettempdir()
        timestamp = int(time.time())
        image_path = os.path.join(temp_dir, f"ganglia_image_{timestamp}.png")
        cv2.imwrite(image_path, frame)
        return image_path

    def release_resources(self):
        """Release camera resources."""
        self.cam.release()
        cv2.destroyAllWindows()
