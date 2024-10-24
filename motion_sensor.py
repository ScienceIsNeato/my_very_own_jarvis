import cv2
import numpy as np
import time
from threading import Thread
from pubsub import PubSub
from camera import Camera

class MotionDetectionSensor:
    """Motion Detection Sensor using camera."""

    def __init__(self, pubsub: PubSub, debug=False):
        self.pubsub = pubsub
        self.camera = Camera()
        self.debug = debug
        self.thread = Thread(target=self.detect_motion)
        self.thread.daemon = True  # Daemon thread to run in the background
        self.thread.start()

    def detect_motion(self):
        """Continuously detect motion and publish events to PubSub."""
        ret, prev_frame = self.camera.cam.read()
        if not ret:
            raise RuntimeError("Failed to capture initial frame for motion detection.")

        prev_frame_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
        prev_frame_gray = cv2.GaussianBlur(prev_frame_gray, (21, 21), 0)

        while True:
            time.sleep(0.1)  # Adjust detection frequency
            ret, curr_frame = self.camera.cam.read()
            if not ret:
                continue

            curr_frame_gray = cv2.cvtColor(curr_frame, cv2.COLOR_BGR2GRAY)
            curr_frame_gray = cv2.GaussianBlur(curr_frame_gray, (21, 21), 0)

            # Compute difference between frames
            frame_delta = cv2.absdiff(prev_frame_gray, curr_frame_gray)
            thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
            thresh = cv2.dilate(thresh, None, iterations=2)

            # Find contours to detect movement
            contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            motion_detected = any(cv2.contourArea(c) > 500 for c in contours)

            if motion_detected:
                image_path = self.camera.capture_image()
                self.pubsub.publish('motion_sensor', f"Motion detected! Image saved at: {image_path}")

            prev_frame_gray = curr_frame_gray

    def release_resources(self):
        """Release all resources."""
        self.camera.release_resources()
