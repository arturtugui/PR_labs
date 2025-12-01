import os
import time
import random
import requests
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# ---------------------------------------------------------
# Semi-synchronous replication with write quorum:
# - Leader writes locally and sends updates to followers concurrently.
# - Each follower applies updates only if the sequence number is newer.
# - The leader waits for a configurable "write quorum" of confirmations before
#   reporting success, ensuring that at least quorum followers are consistent.
# - Local locks prevent race conditions within a node.
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
    #   - Each follower is contacted in its own thread.
    #   - Network lag is simulated per follower to test concurrency.
    #   - Confirms writes based on follower responses and write quorum.
    #   - Busy waiting is replaced with futures and as_completed for efficiency.
    # -----------------------------------------------------
    def replicate_to_followers(self, key: str, value: str, seq: int) -> bool:
        confirmations = 0  # Number of followers that acknowledged

        # Shared lock ensures that concurrent threads safely update the shared counter.
        # If the lock were local to each thread, race conditions would occur.
        lock = threading.Lock()

        # -------------------------------------------------
        # Inner function: replicate to a single follower
        # -------------------------------------------------
        def replicate_to_one(follower_url: str) -> bool:
            try:
                # Simulate random network lag
                delay_ms = random.randint(self.min_delay, self.max_delay)
                time.sleep(delay_ms / 1000.0)

                # Send POST request to follower /replicate endpoint
                response = requests.post(
                    f"{follower_url}/replicate",
                    json={"key": key, "value": value, "seq": seq},
                    timeout=2
                )

                # Return True if follower confirms successfully
                return response.status_code == 200 and response.json().get('ok', False)

            except Exception as e:
                # Log failures but continue; does not crash the leader
                print(f"Replication to {follower_url} failed: {e}")
                return False

        # -------------------------------------------------
        # Execute replication concurrently to all followers
        # -------------------------------------------------
        with ThreadPoolExecutor(max_workers=len(self.follower_urls)) as executor:
            # Submit a task per follower
            futures = [executor.submit(replicate_to_one, url) for url in self.follower_urls]
            start_time = time.time()

            # Iterate over futures as they complete (efficient waiting)
            for future in as_completed(futures, timeout=self.timeout / 1000.0):
                if future.result():  # Increment only if follower confirmed
                    with lock:
                        confirmations += 1
                        # Immediately return True if quorum is reached
                        if confirmations >= self.write_quorum:
                            return True

        # Final check if timeout occurs before quorum
        return confirmations >= self.write_quorum
