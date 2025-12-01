import requests
import time
from dotenv import dotenv_values

LEADER_URL = "http://localhost:8000"
FOLLOWER_URLS = [f"http://localhost:{8001+i}" for i in range(5)]

# Read configuration from .env
config = dotenv_values(".env")
WRITE_QUORUM = int(config.get('WRITE_QUORUM', 3))

def test_quorum_stops_early():
    """
    Test that with quorum=3, not all followers receive updates.
    
    With delays 100-5000ms and quorum=3:
    - Leader returns success after 3 followers confirm
    - Remaining 2 tasks should be cancelled
    - Since we check immediately, those 2 should not have the data yet
    """
    
    # Reset all stores
    for url in [LEADER_URL] + FOLLOWER_URLS:
        try:
            requests.post(f"{url}/reset", timeout=1)
        except:
            pass
    
    time.sleep(0.5)  # Let resets propagate
    
    # Perform 10 writes and collect results
    inconsistent_count = 0
    total_writes = 10
    
    for i in range(total_writes):
        key = f"key_{i}"
        value = f"value_{i}"
        
        # Write to leader
        response = requests.post(f"{LEADER_URL}/write", json={"key": key, "value": value}, timeout=15)
        
        if response.status_code != 200:
            print(f"Write {i} failed: {response.status_code}")
            continue
        
        # Check followers IMMEDIATELY (no sleep)
        # Count how many have the data
        followers_with_data = 0
        for follower_url in FOLLOWER_URLS:
            try:
                follower_response = requests.get(f"{follower_url}/get?key={key}", timeout=1)
                if follower_response.status_code == 200:
                    followers_with_data += 1
            except:
                pass
        
        print(f"Write {i}: {followers_with_data}/5 followers have data immediately")
        
        # If less than 5 followers have it, we have inconsistency!
        if followers_with_data < 5:
            inconsistent_count += 1
    
    print(f"\n=== RESULTS ===")
    print(f"Writes with inconsistent followers: {inconsistent_count}/{total_writes}")
    print(f"Inconsistency rate: {(inconsistent_count/total_writes)*100:.1f}%")
    
    if inconsistent_count > 0:
        print("\n✓ SUCCESS: Quorum mechanism working - some followers lagging!")
    else:
        print("\n✗ PROBLEM: All followers always have data - cancellation not working")

if __name__ == '__main__':
    print(f"=== QUORUM CANCELLATION TEST ===")
    print(f"Configuration from .env:")
    print(f"  WRITE_QUORUM = {WRITE_QUORUM}")
    print(f"  MIN_DELAY_MS = {config.get('MIN_DELAY_MS', 'N/A')}")
    print(f"  MAX_DELAY_MS = {config.get('MAX_DELAY_MS', 'N/A')}")
    print()
    
    test_quorum_stops_early()
