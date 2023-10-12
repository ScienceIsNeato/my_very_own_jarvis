
# This is a quick and dirty test to check that creds are in place and session logs can be uploaded to GCP storage
# Successful output will look like:
#   ❯ python tests/test_gcp_upload.py
#       File /tmp/gcp_test_payload.txt uploaded to ganglia_session_logger.
#       Confirmed: /tmp/gcp_test_payload.txt exists in ganglia_session_logger.
#       Removed test file /tmp/gcp_test_payload.txt.

import os
from google.cloud import storage
from dotenv import load_dotenv

def create_test_file(file_path):
    with open(file_path, 'w') as f:
        f.write("Why did the developer go broke? Because he used up all his cache.")

def upload_to_gcloud(bucket_name, project_name, file_name):
    storage_client = storage.Client(project=project_name)
    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.blob(os.path.basename(file_name))
    blob.upload_from_filename(file_name)
    print(f"File {file_name} uploaded to {bucket_name}.")

def confirm_upload(bucket_name, project_name, file_name):
    storage_client = storage.Client(project=project_name)
    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.blob(os.path.basename(file_name))

    if blob.exists():
        print(f"Confirmed: {file_name} exists in {bucket_name}.")
    else:
        print(f"Error: {file_name} does not exist in {bucket_name}.")

def cleanup_test_file(file_path):
    os.remove(file_path)
    print(f"Removed test file {file_path}.")

if __name__ == "__main__":
    # Change to this directory so that we know where to load the .env from
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # Load environment variables from .env file located one directory above
    load_dotenv('../.env')

    # Fetch environment variables
    bucket_name = os.getenv('GCP_BUCKET_NAME')
    project_name = os.getenv('GCP_PROJECT_NAME')

    # Temporary file path
    file_path = '/tmp/gcp_test_payload.txt'

    # Create the test file
    create_test_file(file_path)

    # Upload the file
    upload_to_gcloud(bucket_name, project_name, file_path)

    # Confirm the upload
    confirm_upload(bucket_name, project_name, file_path)

    # Clean up the test file
    cleanup_test_file(file_path)

