import asyncio
from new_script import main as new_main

async def test_main():
    try:
        await asyncio.to_thread(new_main)
        print("Test succeeded.")
    except Exception as e:
        print(f"Test failed with an unexpected error: {e}")

if __name__ == '__main__':
    asyncio.run(test_main())