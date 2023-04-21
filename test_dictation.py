from dictation import getDictatedInput

def main():
    listen_duration = 5  # Adjust the listening duration in seconds as needed
    device_index = 0  # Adjust the device index as needed
    
    result = getDictatedInput(listen_duration, device_index)

    if result is None:
        print("Test succeeded.")
    else:
        print(f"Test failed with an unexpected error: {result}")

if __name__ == '__main__':
    main()