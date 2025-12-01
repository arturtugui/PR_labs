import os
import asyncio
import random
import httpx

# ---------------------------------------------------------
# Semi-synchronous replication with write quorum:
# - Leader writes locally and sends updates to followers concurrently.
# - Each follower applies updates only if the sequence number is newer.
# - The leader waits for a configurable "write quorum" of confirmations before
#   reporting success, ensuring that at least quorum followers are consistent.
# - Async/await enables true task cancellation after quorum is reached.
# - Followers not in the quorum may lag temporarily, achieving eventual consistency.
# ---------------------------------------------------------
class ReplicationManager:
    def __init__(self):
        # List of follower HTTP endpoints (from env var FOLLOWERS)
        self.follower_urls = os.getenv('FOLLOWERS', '').split(',')

        # Minimum number of followers that must confirm a write
        # for the leader to report success
        self.write_quorum = int(os.getenv('WRITE_QUORUM', '1'))

        # Minimum and maximum artificial network delay (ms) to simulate lag
        self.min_delay = int(os.getenv('MIN_DELAY_MS', '0'))
        self.max_delay = int(os.getenv('MAX_DELAY_MS', '200'))

        # Timeout for waiting for quorum (ms)
        self.timeout = int(os.getenv('REPLICATION_TIMEOUT_MS', '5000'))

    # -----------------------------------------------------
    # Sends replication requests to all followers concurrently.
    #
    # Parameters:
    #   key   : str  → key being written
    #   value : str  → value being written
    #   seq   : int  → sequence number assigned by the leader
    #
    # Returns:
    #   True  → write_quorum followers confirmed
    #   False → quorum not reached within timeout
    #
    # Notes:
    #   - Each follower is contacted in its own async task.
    #   - Network lag is simulated per follower to test concurrency.
    #   - Tasks are cancelled immediately after quorum is reached.
    #   - Async/await allows true mid-execution cancellation.
    # -----------------------------------------------------
    async def replicate_to_followers(self, key: str, value: str, seq: int) -> bool:
        confirmations = 0
        tasks = []
        
        # Shared event to signal when quorum is reached
        quorum_event = asyncio.Event()

        # -------------------------------------------------
        # Inner coroutine: replicate to a single follower
        # -------------------------------------------------
        async def replicate_to_one(follower_url: str, client: httpx.AsyncClient) -> bool:
            try:
                # Simulate random network lag - but check for cancellation every 100ms
                delay_ms = random.randint(self.min_delay, self.max_delay)
                delay_seconds = delay_ms / 1000.0
                
                # Wait with timeout so we can be interrupted by quorum_event
                try:
                    await asyncio.wait_for(quorum_event.wait(), timeout=delay_seconds)
                    # Quorum reached during delay - stop here
                    print(f"Replication to {follower_url} stopped (quorum reached during delay)")
                    return False
                except asyncio.TimeoutError:
                    # Delay completed, quorum not reached yet - proceed with request
                    pass

                # Check again before sending request
                if quorum_event.is_set():
                    print(f"Replication to {follower_url} skipped (quorum already reached)")
                    return False

                # Send POST request to follower /replicate endpoint
                response = await client.post(
                    f"{follower_url}/replicate",
                    json={"key": key, "value": value, "seq": seq},
                    timeout=2.0
                )

                # Return True if follower confirms successfully
                return response.status_code == 200 and response.json().get('ok', False)

            except asyncio.CancelledError:
                # Task was cancelled after quorum reached
                print(f"Replication to {follower_url} cancelled (quorum already reached)")
                raise
            except Exception as e:
                # Log failures but continue; does not crash the leader
                print(f"Replication to {follower_url} failed: {e}")
                return False

        # -------------------------------------------------
        # Execute replication concurrently to all followers
        # -------------------------------------------------
        async with httpx.AsyncClient() as client:
            # Create tasks for all followers
            tasks = [asyncio.create_task(replicate_to_one(url, client)) for url in self.follower_urls]

            try:
                # Wait for tasks to complete, checking after each one
                for coro in asyncio.as_completed(tasks):
                    try:
                        result = await coro
                        if result:
                            confirmations += 1
                            print(f"Confirmation received: {confirmations}/{self.write_quorum}")
                            # Check if we've reached quorum
                            if confirmations >= self.write_quorum:
                                # Signal other tasks to stop
                                quorum_event.set()
                                # Wait briefly for other tasks to notice and stop
                                await asyncio.sleep(0.1)
                                # Cancel any remaining tasks
                                for task in tasks:
                                    if not task.done():
                                        task.cancel()
                                await asyncio.gather(*tasks, return_exceptions=True)
                                return True
                    except asyncio.CancelledError:
                        # Expected for cancelled tasks
                        pass
                    except Exception as e:
                        print(f"Task error: {e}")

            except asyncio.TimeoutError:
                # Timeout expired before quorum reached
                for task in tasks:
                    if not task.done():
                        task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)

        return confirmations >= self.write_quorum
