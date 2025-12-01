import requests
import time
from dotenv import dotenv_values

LEADER_URL = "http://localhost:8000"
FOLLOWER_URLS = [f"http://localhost:{8001+i}" for i in range(5)]

# Read configuration from .env
config = dotenv_values(".env")
WRITE_QUORUM = int(config.get('WRITE_QUORUM', 3))

def test_single_write_quorum():
    """
    Test with a SINGLE write to clearly show that only quorum followers get the data.
    
    With WRITE_QUORUM=1:
    - Only 1 follower should have the data immediately
    - The other 4 should be cancelled and not have it
    """
    
    print(f"=== SINGLE WRITE QUORUM TEST ===")
    print(f"Configuration from .env:")
    print(f"  WRITE_QUORUM = {WRITE_QUORUM}")
    print(f"  MIN_DELAY_MS = {config.get('MIN_DELAY_MS', 'N/A')}")
    print(f"  MAX_DELAY_MS = {config.get('MAX_DELAY_MS', 'N/A')}")
    print()
    
    # Reset all stores
    print("Resetting all stores...")
    for url in [LEADER_URL] + FOLLOWER_URLS:
        try:
            requests.post(f"{url}/reset", timeout=1)
        except:
            pass
    
    time.sleep(0.5)
    
    # Perform SINGLE write
    print("Performing single write to leader...")
    response = requests.post(f"{LEADER_URL}/write", json={"key": "single_key", "value": "single_value"}, timeout=15)
    
    if response.status_code != 200:
        print(f"ERROR: Write failed with status {response.status_code}")
        return
    
    print(f"Write successful! Leader returned: {response.json()}")
    
    # Check followers IMMEDIATELY (no delay)
    print("\nChecking followers IMMEDIATELY after write returns:")
    followers_with_data = 0
    for i, follower_url in enumerate(FOLLOWER_URLS, 1):
        try:
            follower_response = requests.get(f"{follower_url}/get?key=single_key", timeout=1)
            if follower_response.status_code == 200:
                data = follower_response.json()
                print(f"  Follower {i}: HAS DATA - seq={data['seq']}, value={data['value']}")
                followers_with_data += 1
            else:
                print(f"  Follower {i}: NO DATA (cancelled/not reached yet)")
        except Exception as e:
            print(f"  Follower {i}: NO DATA (error: {e})")
    
    print(f"\n=== RESULTS ===")
    print(f"Followers with data immediately: {followers_with_data}/5")
    print(f"Expected: ~{WRITE_QUORUM} (should be close to WRITE_QUORUM)")
    
    if followers_with_data <= WRITE_QUORUM + 1:  # Allow +1 for timing
        print("\n✓ SUCCESS: Quorum mechanism working correctly!")
        print(f"  Only {followers_with_data} followers have data (quorum={WRITE_QUORUM})")
    else:
        print(f"\n✗ UNEXPECTED: Too many followers have data")
        print(f"  Expected ~{WRITE_QUORUM}, but {followers_with_data} have it")
    
    # Wait and check again to show eventual consistency
    print("\n--- Waiting 3 seconds for eventual consistency ---")
    time.sleep(3)
    
    print("\nChecking followers after 3 seconds:")
    followers_with_data_later = 0
    for i, follower_url in enumerate(FOLLOWER_URLS, 1):
        try:
            follower_response = requests.get(f"{follower_url}/get?key=single_key", timeout=1)
            if follower_response.status_code == 200:
                data = follower_response.json()
                print(f"  Follower {i}: HAS DATA - seq={data['seq']}")
                followers_with_data_later += 1
            else:
                print(f"  Follower {i}: Still no data")
        except:
            print(f"  Follower {i}: Still no data")
    
    print(f"\nFollowers with data after wait: {followers_with_data_later}/5")
    print("(Should still be close to quorum - cancelled tasks don't retry)")

if __name__ == '__main__':
    test_single_write_quorum()
