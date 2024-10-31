import cv2
import numpy as np
import time
from threading import Thread
from pubsub import PubSub
from camera import Camera

class MotionDetectionSensor:
    """Motion Detection Sensor using camera."""

    def __init__(self, pubsub: PubSub, video_src=0, debug=False, max_events=None):
        """
        Initializes the MotionDetectionSensor.

        Args:
            pubsub (PubSub): The PubSub instance for publishing events.
            video_src (int): The video source for the camera.
            debug (bool): Enables debug mode if True.
            max_events (int, optional): The maximum number of motion events before self-destruction.
                                         If None, it runs indefinitely.
        """
        self.pubsub = pubsub
        self.camera = Camera(video_src=video_src)
        self.debug = debug
        self.sample_image_saved = False  # Flag to ensure only the first image is saved
        self.max_events = max_events  # Maximum number of events before self-destruct
        self.event_count = 0  # Counter for motion events

        self.thread = Thread(target=self.detect_motion)
        self.thread.daemon = True  # Daemon thread to run in the background
        self.thread.start()

    def detect_motion(self):
        """Continuously detect motion and publish events to PubSub until max_events is reached."""
        ret, prev_frame = self.camera.cam.read()
        if not ret:
            raise RuntimeError("Failed to capture initial frame for motion detection.")

        prev_frame_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
        prev_frame_gray = cv2.GaussianBlur(prev_frame_gray, (21, 21), 0)

        while True:
            # Check if max_events has been reached
            if self.max_events is not None and self.event_count >= self.max_events:
                self.release_resources()
                print("Max motion events reached. Motion sensor deactivated.")
                break

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
                self.pubsub.publish('motion_sensor', curr_frame)
                self.event_count += 1  # Increment event counter

            prev_frame_gray = curr_frame_gray

    def release_resources(self):
        """Release all resources."""
        self.camera.release_resources()
