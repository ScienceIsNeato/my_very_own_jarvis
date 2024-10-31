import cv2
import os
import time
import tempfile

class Camera:
    """Camera class to handle image capture and processing."""

    def __init__(self, video_src=0):
        self.video_src = video_src
        self.cam = None
        self.path_printed = False
        self.initialize_camera()

    def initialize_camera(self):
        self.cam = cv2.VideoCapture(self.video_src)
        if not self.cam.isOpened():
            raise RuntimeError("Failed to open camera on video source:", self.video_src)
        print(f"Camera initialized successfully on video source {self.video_src}.")

    def capture_image(self):
        """Capture an image and return it as an in-memory array."""
        ret, frame = self.cam.read()
        if not ret:
            raise RuntimeError("Failed to capture image.")
        
        # Return the image frame in memory
        return frame

    def save_image(self, frame):
        """Save the given frame to a temporary directory and return the file path."""
        temp_dir = tempfile.gettempdir()
        timestamp = int(time.time())
        image_path = os.path.join(temp_dir, f"ganglia_image_{timestamp}.png")
        
        cv2.imwrite(image_path, frame)
        print(f"Image saved to: {image_path}")
        
        return image_path

    def release_resources(self):
        self.cam.release()
        cv2.destroyAllWindows()
