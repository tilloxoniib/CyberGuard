import asyncio
from cleaner_service import CleanerService

async def test():
    print("--- TESTING CLEANER SERVICE ---")
    service = CleanerService(session_path="test_session")
    
    print("1. Checking auth...")
    # Give the thread a moment to start
    await asyncio.sleep(1)
    
    is_auth = service.check_auth()
    print(f"Auth status: {is_auth}")
    
    if not is_auth:
        print("2. Sending code to a test number (invalid to fail safely)...")
        # We won't actually send to a real number to avoid spam, 
        # but we want to see if the client connects.
        # Use a dummy number that fails validation or just check connection.
        
        # Actually, let's just check if client connects.
        # Accessing private method for testing is okay here
        try:
            future = asyncio.run_coroutine_threadsafe(service._check_auth_async(), service.loop)
            res = future.result(timeout=10)
            print(f"Connection & Auth check result: {res}")
            print("Service seems to be initializing correctly.")
        except Exception as e:
            print(f"ERROR: {e}")

    print("--- TEST FINISHED ---")
    # Clean up
    service.is_running = False

if __name__ == "__main__":
    asyncio.run(test())
