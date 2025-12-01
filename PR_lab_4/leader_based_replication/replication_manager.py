import os
import time
import random
import requests
import threading
from typing import List
from concurrent.futures import ThreadPoolExecutor, as_completed

# ---------------------------------------------------------
# ReplicationManager handles semi-synchronous replication
# from the leader to multiple followers.
#
# Responsibilities:
#   - Read configuration from environment variables
#   - Send replication requests concurrently
#   - Count confirmations and enforce a configurable write quorum
#   - Simulate network lag for testing race conditions
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
    # -----------------------------------------------------
    def replicate_to_followers(self, key: str, value: str, seq: int) -> bool:
        confirmations = 0  # Number of followers that acknowledged
        lock = threading.Lock()  # Protects shared counter

        # -------------------------------------------------
        # Inner function: replicate to a single follower
        # -------------------------------------------------
        def replicate_to_one(follower_url: str):
            nonlocal confirmations
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

                # If follower confirms, increment the counter
                if response.status_code == 200 and response.json().get('ok'):
                    with lock:
                        confirmations += 1

            except Exception as e:
                # Log failures but continue
                print(f"Replication to {follower_url} failed: {e}")

        # -------------------------------------------------
        # Execute replication concurrently to all followers
        # -------------------------------------------------
        with ThreadPoolExecutor(max_workers=len(self.follower_urls)) as executor:
            futures = [executor.submit(replicate_to_one, url) for url in self.follower_urls]

            # Wait for quorum or until timeout
            start_time = time.time()
            while (time.time() - start_time) < (self.timeout / 1000.0):
                with lock:
                    if confirmations >= self.write_quorum:
                        return True  # Quorum reached
                time.sleep(0.01)  # Check every 10ms

        # Final check after timeout
        with lock:
            return confirmations >= self.write_quorum
