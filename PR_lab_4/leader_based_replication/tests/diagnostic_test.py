import requests
import time
import concurrent.futures

LEADER_URL = "http://localhost:8000"
FOLLOWER_URLS = [f"http://localhost:{8001+i}" for i in range(5)]

# Small test with only 20 writes
TOTAL_WRITES = 20
CONCURRENT_BATCH = 5
NUM_KEYS = 5  # keys: key0, key1, key2, key3, key4

def send_write(key, value):
    """Send write and measure latency"""
    start = time.time()
    try:
        response = requests.post(f"{LEADER_URL}/write", json={"key": key, "value": value}, timeout=10)
        latency_ms = (time.time() - start) * 1000
        return key, value, latency_ms, response.status_code, response.json() if response.status_code == 200 else None
    except Exception as e:
        return key, value, None, 500, str(e)

def run_writes():
    """Run writes concurrently"""
    results = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENT_BATCH) as executor:
        futures = []
        for i in range(TOTAL_WRITES):
            key = f"key{i % NUM_KEYS}"
            value = f"value_{i}"
            futures.append(executor.submit(send_write, key, value))

        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            results.append(result)
            key, value, latency, status, response = result
            if status == 200:
                seq = response.get('seq', 'N/A')
                print(f"  Write {key}={value} -> seq={seq}, latency={latency:.0f}ms")
            else:
                print(f"  Write {key}={value} -> FAILED")
    
    return results

def get_all_data():
    """Fetch data from leader and all followers"""
    data = {}
    
    # Get leader data
    leader_dump = requests.get(f"{LEADER_URL}/dump").json()
    data['leader'] = leader_dump['entries']
    
    # Get follower data
    for i, follower_url in enumerate(FOLLOWER_URLS):
        follower_dump = requests.get(f"{follower_url}/dump").json()
        data[f'follower{i+1}'] = follower_dump['entries']
    
    return data

def print_comparison_table(data):
    """Print side-by-side comparison of all nodes"""
    keys = sorted(data['leader'].keys())
    
    print("\n" + "="*120)
    print("DATA COMPARISON TABLE")
    print("="*120)
    print(f"{'Key':<10} | {'Leader':<15} | {'F1':<15} | {'F2':<15} | {'F3':<15} | {'F4':<15} | {'F5':<15}")
    print("-"*120)
    
    for key in keys:
        leader_val = data['leader'].get(key, {})
        leader_str = f"v:{leader_val.get('value', 'N/A')[-8:]}, s:{leader_val.get('seq', 0)}"
        
        f1_val = data['follower1'].get(key, {})
        f1_str = f"v:{f1_val.get('value', 'N/A')[-8:]}, s:{f1_val.get('seq', 0)}"
        f1_match = "OK" if f1_val.get('seq') == leader_val.get('seq') else "LAG"
        
        f2_val = data['follower2'].get(key, {})
        f2_str = f"v:{f2_val.get('value', 'N/A')[-8:]}, s:{f2_val.get('seq', 0)}"
        f2_match = "OK" if f2_val.get('seq') == leader_val.get('seq') else "LAG"
        
        f3_val = data['follower3'].get(key, {})
        f3_str = f"v:{f3_val.get('value', 'N/A')[-8:]}, s:{f3_val.get('seq', 0)}"
        f3_match = "OK" if f3_val.get('seq') == leader_val.get('seq') else "LAG"
        
        f4_val = data['follower4'].get(key, {})
        f4_str = f"v:{f4_val.get('value', 'N/A')[-8:]}, s:{f4_val.get('seq', 0)}"
        f4_match = "OK" if f4_val.get('seq') == leader_val.get('seq') else "LAG"
        
        f5_val = data['follower5'].get(key, {})
        f5_str = f"v:{f5_val.get('value', 'N/A')[-8:]}, s:{f5_val.get('seq', 0)}"
        f5_match = "OK" if f5_val.get('seq') == leader_val.get('seq') else "LAG"
        
        print(f"{key:<10} | {leader_str:<15} | {f1_str:<13} {f1_match} | {f2_str:<13} {f2_match} | {f3_str:<13} {f3_match} | {f4_str:<13} {f4_match} | {f5_str:<13} {f5_match}")
    
    print("="*120)
    print("\nLegend: v = value (last 8 chars), s = sequence number")
    print("        OK = matches leader, LAG = behind leader\n")

def analyze_consistency(data):
    """Analyze consistency across replicas"""
    keys = sorted(data['leader'].keys())
    
    print("\nCONSISTENCY ANALYSIS")
    print("-"*60)
    
    for i in range(1, 6):
        follower_name = f'follower{i}'
        matches = 0
        lags = 0
        missing = 0
        
        for key in keys:
            leader_seq = data['leader'][key]['seq']
            follower_data = data[follower_name].get(key)
            
            if follower_data is None:
                missing += 1
            elif follower_data['seq'] == leader_seq:
                matches += 1
            else:
                lags += 1
        
        total = len(keys)
        match_pct = (matches / total * 100) if total > 0 else 0
        print(f"Follower {i}: {matches}/{total} match ({match_pct:.0f}%), {lags} lag, {missing} missing")

if __name__ == "__main__":
    print("DIAGNOSTIC TEST - Small Write Test with Full Data Output")
    print("="*120)
    
    # Check current quorum setting
    try:
        leader_dump = requests.get(f"{LEADER_URL}/dump").json()
        print(f"\nCurrent setup: Leader is running")
    except:
        print("\nERROR: Leader is not running! Start with 'docker-compose up -d'")
        exit(1)
    
    print(f"\nTest parameters:")
    print(f"  - Total writes: {TOTAL_WRITES}")
    print(f"  - Concurrent batch: {CONCURRENT_BATCH}")
    print(f"  - Number of keys: {NUM_KEYS}")
    print(f"  - Each key will be written {TOTAL_WRITES // NUM_KEYS} times\n")
    
    input("Press Enter to start writing (make sure docker-compose is up with desired WRITE_QUORUM)...")
    
    print("\nPerforming writes...")
    results = run_writes()
    
    print("\nWaiting 3 seconds for replication to complete...")
    time.sleep(3)
    
    print("\nFetching data from all nodes...")
    data = get_all_data()
    
    print_comparison_table(data)
    analyze_consistency(data)
    
    print("\nTest complete!")
    print("\nTo test different quorums:")
    print("  1. Edit docker-compose.yml and change WRITE_QUORUM")
    print("  2. Run: docker-compose restart leader")
    print("  3. Run this test again")
