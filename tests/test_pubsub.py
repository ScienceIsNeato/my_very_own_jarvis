import time
from pubsub import PubSub


def video_job_processor(message):
    """Simulate processing a text-to-video job."""
    print(f"Processing video job: {message}")
    time.sleep(3)  # Simulate some processing delay
    print(f"Completed video job: {message}")

def notify_main_thread(message):
    """Simulate notifying the main thread when a job is done."""
    print(f"Notification received: {message}")

# Test PubSub system
def test_pubsub():
    pubsub = PubSub()

    # Subscribe the video processor and the main thread notifier to different topics
    pubsub.subscribe('video_jobs', video_job_processor)
    pubsub.subscribe('job_completion', notify_main_thread)

    # Publisher adds a job to the queue
    pubsub.publish('video_jobs', 'Create TTV for Halloween intro.')
    
    # Simulate job completion after processing (done in video_job_processor)
    time.sleep(4)  # Wait for job processing to complete
    pubsub.publish('job_completion', 'TTV job for Halloween intro is complete.')

if __name__ == "__main__":
    test_pubsub()
