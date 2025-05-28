#!/usr/bin/env python3
"""
Test the asyncio fix independently
"""

import asyncio

# Test the same pattern used in chunk_lease
def test_asyncio_handling():
    async def async_function():
        await asyncio.sleep(0.1)
        return "Success!"
    
    try:
        # Check if we're already in an event loop
        loop = asyncio.get_running_loop()
        print("Already in event loop - handling with thread")
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, async_function())
            return future.result()
    except RuntimeError:
        # No event loop is running - this is the normal case
        print("No event loop - using asyncio.run")
        return asyncio.run(async_function())

if __name__ == "__main__":
    result = test_asyncio_handling()
    print(f"Result: {result}")
