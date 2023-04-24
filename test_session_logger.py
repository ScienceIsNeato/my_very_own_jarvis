import json
from session_logger import SessionEvent, Session, CLISessionLogger


def test_session_event():
    event = SessionEvent("Hello", "Hi")
    event_dict = event.to_dict()
    assert event_dict["user_input"] == "Hello"
    assert event_dict["response_output"] == "Hi"


def test_session():
    session_id = "1234"
    timestamp = "2023-04-25T12:30:45"
    conversation = [
        SessionEvent("Hello", "Hi"),
        SessionEvent("How are you?", "I'm doing well, thank you."),
    ]

    session = Session(session_id, timestamp, conversation)
    session_dict = session.to_dict()

    assert session_dict["sessionID"] == session_id
    assert session_dict["timestamp"] == timestamp
    assert len(session_dict["conversation"]) == len(conversation)

    for event, event_dict in zip(conversation, session_dict["conversation"]):
        assert event.to_dict() == event_dict


def test_cli_session_logger(tmpdir):
    session_logger = CLISessionLogger()

    # Log session interactions
    event1 = SessionEvent("Hello", "Hi")
    event2 = SessionEvent("How are you?", "I'm doing well, thank you.")
    session_logger.log_session_interaction(event1)
    session_logger.log_session_interaction(event2)

    # Check conversation
    assert len(session_logger.conversation) == 2

    # Finalize session and write to disk
    file_name = session_logger.finalize_session()

    # Read and parse the JSON file
    with open(file_name, "r") as f:
        json_data = json.load(f)

    # Check session data
    assert json_data["sessionID"] == session_logger.session_id
    assert len(json_data["conversation"]) == 2

