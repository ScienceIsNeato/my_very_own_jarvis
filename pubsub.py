import queue
import threading
import time
from typing import Callable, Dict, List

class PubSub:
    def __init__(self):
        self.topics: Dict[str, List[Callable]] = {}  # Topic to subscriber mapping
        self.queues: Dict[str, queue.Queue] = {}  # Queues for each topic

    def subscribe(self, topic: str, subscriber: Callable):
        """Subscribe a subscriber (callback function) to a topic."""
        if topic not in self.topics:
            self.topics[topic] = []
            self.queues[topic] = queue.Queue()
            threading.Thread(target=self._worker, args=(topic,)).start()

        self.topics[topic].append(subscriber)

    def publish(self, topic: str, message):
        """Publish a message to a topic."""
        if topic not in self.topics:
            print(f"No subscribers for topic: {topic}")
            return

        # Place the message in the topic's queue for subscribers to process
        self.queues[topic].put(message)

    def _worker(self, topic: str):
        """A background worker that listens to a topic and dispatches messages to subscribers."""
        while True:
            message = self.queues[topic].get()  # Blocking call
            for subscriber in self.topics[topic]:
                subscriber(message)  # Dispatch message to subscriber

    def unsubscribe(self, topic: str, subscriber: Callable):
        """Unsubscribe a subscriber from a topic."""
        if topic in self.topics and subscriber in self.topics[topic]:
            self.topics[topic].remove(subscriber)
            if not self.topics[topic]:  # If no subscribers left, remove topic
                del self.topics[topic]
                del self.queues[topic]
