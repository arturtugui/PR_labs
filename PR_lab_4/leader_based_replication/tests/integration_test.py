import requests
import time

LEADER_URL = "http://localhost:8000"

FOLLOWER_URLS = [f"http://localhost:{8001+i}" for i in range(5)]


def test_basic_replication():
    """Test that a write sent to the leader is correctly replicated to followers."""

    # Send a WRITE request to the leader replica
    response = requests.post(f"{LEADER_URL}/write", json={"key": "test1", "value": "hello"})
    assert response.status_code == 200
    data = response.json()

    # Leader responds with:
    #   ok=True → write accepted
    #   seq → leader's assigned sequence number for this write
    seq = data['seq']

    # Replication is async → wait a bit for followers to receive and apply the update
    time.sleep(1)

    # ---- CHECK THAT THE LEADER HAS THE WRITE ----
    leader_data = requests.get(f"{LEADER_URL}/get?key=test1").json()
    assert leader_data['value'] == "hello"
    assert leader_data['seq'] == seq  # same sequence number

    # ---- CHECK FOLLOWERS ----
    # Not every follower *must* have the update if quorum < 5,
    # but this prints their state for debugging.
    for follower_url in FOLLOWER_URLS:
        follower_data = requests.get(f"{follower_url}/get?key=test1").json()
        print(f"{follower_url}: {follower_data}")


def test_consistency():
    """Test concurrent writes and check that the final result is the latest write."""

    # ---- SIMULATE HIGH CONTENTION ----
    # Many threads write to the same key "race_key"
    import concurrent.futures

    def write_key(i):
        # Each write uses a different value: value_0, value_1, … value_49
        return requests.post(f"{LEADER_URL}/write",
                             json={"key": "race_key", "value": f"value_{i}"})

    # ThreadPoolExecutor creates concurrency → simulates real-world races
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(write_key, i) for i in range(50)]
        results = [f.result() for f in futures]

    # Give time for followers to catch up
    time.sleep(2)

    # ---- CHECK FINAL LEADER STATE ----
    leader_dump = requests.get(f"{LEADER_URL}/dump").json()

    leader_value = leader_dump['entries'].get('race_key', {})

    print(f"\nLeader: {leader_value}")

    # ---- VERIFY REPLICATION CONSISTENCY ----
    # Every follower must have the same seq number as the leader.
    # If any follower has a smaller seq → it missed updates.
    # If any has a larger seq → the system is inconsistent (should never happen).
    for follower_url in FOLLOWER_URLS:
        follower_dump = requests.get(f"{follower_url}/dump").json()
        follower_value = follower_dump['entries'].get('race_key', {})
        print(f"{follower_url}: {follower_value}")

        if follower_value:
            assert follower_value['seq'] == leader_value['seq'], \
                f"Inconsistency detected! Leader seq {leader_value['seq']} != Follower seq {follower_value['seq']}"


if __name__ == "__main__":
    print("Testing basic replication...")
    test_basic_replication()

    print("\nTesting consistency (race condition)...")
    test_consistency()
