import json
import datetime
import subprocess

def parse_timestamp(timestamp_str):
    """Parse timestamp string into datetime object, handling both formats with and without milliseconds."""
    # Replace periods with colons in the time portion of the timestamp
    timestamp_str = timestamp_str.replace('.', ':')
    try:
        return datetime.datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S.%f")  # Handle milliseconds
    except ValueError:
        return datetime.datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S")  # Fallback to no milliseconds


def fetch_logs_from_gcs(hours):
    """Fetch logs from GCS based on the given time range."""
    logs = []
    current_time = datetime.datetime.now()

    for i in range(1, 5000):  # Loop to get up to 5000 files or until the range is exceeded
        # Get the file list from GCS and download one at a time
        try:
            command = f"gsutil ls -l gs://ganglia_session_logger/ | grep -v 'TOTAL:' | sort -rk 2,2 | head -n {i} | tail -n 1 | awk '{{print $NF}}' | xargs -I {{}} sh -c 'temp_file=$(mktemp); gsutil cp {{}} $temp_file; cat $temp_file; rm $temp_file'"
            log_content = subprocess.check_output(command, shell=True).decode("utf-8")

            log_json = json.loads(log_content)
            conversation_logs = log_json.get("conversation", [])

            # Get timestamp of the first event in this log file
            if not conversation_logs:
                print("No conversation logs found in this file. Skipping.")
                continue
            first_event_timestamp = parse_timestamp(conversation_logs[0]['time_logged'])
            print(f"First event timestamp: {first_event_timestamp}")

            # Calculate the time difference
            time_diff = current_time - first_event_timestamp
            hours_diff = time_diff.total_seconds() / 3600

            # Stop if we've exceeded the time range
            if hours_diff > hours:
                print("Exceeded the specified time range: hours_diff (" + str(hours_diff) + ") > hours (" + str(hours) + ")")
                break

            # Add logs from this file to the result
            logs.extend(conversation_logs)

        except subprocess.CalledProcessError as e:
            print(f"Error fetching logs: {e}")
            continue
        except (ValueError, json.JSONDecodeError):
            print("Invalid log format. Skipping this log.")
            continue

    return logs


def display_logs(hours):
    logs = fetch_logs_from_gcs(hours)

    # Combine and sort the logs based on timestamps
    sorted_logs = sorted(logs, key=lambda x: parse_timestamp(x['time_logged']))

    previous_timestamp = None
    for entry in sorted_logs:
        timestamp = parse_timestamp(entry['time_logged'])
        user_input = entry.get('user_input', '')
        response_output = entry.get('response_output', '')

        # Detect conversation break (more than 5 minutes between events)
        if previous_timestamp and (timestamp - previous_timestamp).total_seconds() > 300:
            print("--- Conversation Break ---\n")

        # Print user and AI conversation in chronological order with the date and time
        print(f"{timestamp.strftime('%m/%d/%Y %I:%M:%S %p')}  User: {user_input}")
        print(f"{timestamp.strftime('%m/%d/%Y %I:%M:%S %p')}  GANGLIA: {response_output}")

        previous_timestamp = timestamp

