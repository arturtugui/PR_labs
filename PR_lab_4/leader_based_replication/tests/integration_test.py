import requests
import time
from dotenv import dotenv_values

LEADER_URL = "http://localhost:8000"
FOLLOWER_URLS = [f"http://localhost:{8001+i}" for i in range(5)]

# Read configuration from .env
config = dotenv_values(".env")
WRITE_QUORUM = int(config.get('WRITE_QUORUM', 3))


def test_basic_replication():
    """Test that a write sent to the leader is correctly replicated to followers."""

    # Send a WRITE request to the leader replica
    response = requests.post(f"{LEADER_URL}/write", json={"key": "test1", "value": "hello"})
    
    if response.status_code != 200:
        print(f"ERROR: Write failed with status {response.status_code}")
        print(f"Response: {response.text}")
    
    assert response.status_code == 200
    data = response.json()

    # Leader responds with:
    #   ok=True → write accepted
    #   seq → leader's assigned sequence number for this write
    seq = data['seq']

    # Check followers immediately after quorum write completes
    # With quorum=3, only 3 should have the data immediately
    time.sleep(0.1)  # Minimal delay to ensure HTTP responses propagate

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
    """Test concurrent writes and check that at least quorum followers match the leader."""

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

    # Check followers IMMEDIATELY to see the effect of quorum
    # With low quorum, cancelled followers won't have latest data yet
    time.sleep(0.2)  # Minimal delay for HTTP responses to complete

    # ---- CHECK FINAL LEADER STATE ----
    leader_dump = requests.get(f"{LEADER_URL}/dump").json()

    leader_value = leader_dump['entries'].get('race_key', {})

    print(f"\nLeader: {leader_value}")

    # ---- VERIFY REPLICATION CONSISTENCY ----
    # With write quorum, at least WRITE_QUORUM followers must have the same seq as leader.
    # Others may lag (eventual consistency).
    consistent_followers = 0
    for follower_url in FOLLOWER_URLS:
        follower_dump = requests.get(f"{follower_url}/dump").json()
        follower_value = follower_dump['entries'].get('race_key', {})
        print(f"{follower_url}: {follower_value}")

        if follower_value and follower_value['seq'] == leader_value['seq']:
            consistent_followers += 1
    
    print(f"\nConsistent followers: {consistent_followers}/{len(FOLLOWER_URLS)} (quorum={WRITE_QUORUM})")
    assert consistent_followers >= WRITE_QUORUM, \
        f"Quorum not maintained! Only {consistent_followers} followers consistent, need {WRITE_QUORUM}"


if __name__ == "__main__":
    print(f"=== INTEGRATION TEST ===")
    print(f"Configuration from .env:")
    print(f"  WRITE_QUORUM = {WRITE_QUORUM}")
    print(f"  MIN_DELAY_MS = {config.get('MIN_DELAY_MS', 'N/A')}")
    print(f"  MAX_DELAY_MS = {config.get('MAX_DELAY_MS', 'N/A')}")
    print()
    
    print("Testing basic replication...")
    test_basic_replication()

    print("\nTesting consistency (race condition)...")
    test_consistency()
    
    print("\n All tests passed!")
