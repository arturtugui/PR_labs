import requests
import time
import statistics
import concurrent.futures
import matplotlib.pyplot as plt

LEADER_URL = "http://localhost:8000"
TOTAL_WRITES = 100
CONCURRENT_BATCH = 10
NUM_KEYS = 10

def send_write(key, value):
    """Send write and measure latency"""
    start = time.time()
    try:
        response = requests.post(f"{LEADER_URL}/write", json={"key": key, "value": value}, timeout=10)
        latency_ms = (time.time() - start) * 1000
        return latency_ms, response.status_code
    except Exception as e:
        return None, 500

def run_experiment():
    """Run 100 writes (10 at a time) and return average latency"""
    latencies = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENT_BATCH) as executor:
        futures = []
        for i in range(TOTAL_WRITES):
            key = f"key{i % NUM_KEYS}"
            value = f"value_{i}"
            futures.append(executor.submit(send_write, key, value))

        for future in concurrent.futures.as_completed(futures):
            latency, status = future.result()
            if latency and status == 200:
                latencies.append(latency)

    if latencies:
        return statistics.mean(latencies), statistics.stdev(latencies)
    return 0, 0

if __name__ == "__main__":
    print("="*80)
    print("PERFORMANCE TEST - Manual Quorum Testing")
    print("="*80)
    print("\nThis test will measure latency for CURRENT quorum setting.")
    print("You need to manually change WRITE_QUORUM and restart leader between runs.\n")
    
    quorums = [1, 2, 3, 4, 5]
    avg_latencies = []

    for quorum in quorums:
        print(f"\n{'='*80}")
        print(f"TEST FOR WRITE_QUORUM = {quorum}")
        print(f"{'='*80}")
        print("\nSteps:")
        print(f"  1. Edit docker-compose.yml: set WRITE_QUORUM={quorum}")
        print("  2. Run: docker-compose restart leader")
        print("  3. Wait for leader to be ready (3 seconds)")
        
        input(f"\nPress Enter when ready to test WRITE_QUORUM={quorum}...")

        print(f"\nRunning {TOTAL_WRITES} writes...")
        avg, std = run_experiment()
        avg_latencies.append(avg)
        print(f"Results: Average latency = {avg:.2f} ms (std dev: {std:.2f} ms)")

    # Plot results
    print("\nGenerating plot...")
    plt.figure(figsize=(10, 6))
    plt.plot(quorums, avg_latencies, marker='o', linewidth=2, markersize=8, color='#2E86AB')
    plt.xlabel('WRITE_QUORUM (number of follower confirmations)', fontsize=12)
    plt.ylabel('Average Write Latency (ms)', fontsize=12)
    plt.title('Write Quorum vs Average Latency', fontsize=14, fontweight='bold')
    plt.grid(True, alpha=0.3)
    plt.xticks(quorums)

    # Annotate points
    for q, lat in zip(quorums, avg_latencies):
        plt.annotate(f'{lat:.1f}ms', (q, lat), textcoords="offset points",
                    xytext=(0,10), ha='center', fontsize=10)

    plt.tight_layout()
    plt.savefig('quorum_vs_latency.png', dpi=300)
    print("Plot saved to quorum_vs_latency.png")
    plt.close()

    # Print summary
    print("\n" + "="*80)
    print("SUMMARY OF RESULTS")
    print("="*80)
    for q, lat in zip(quorums, avg_latencies):
        print(f"  WRITE_QUORUM={q}: {lat:.2f} ms")
    
    # Check if latencies are increasing
    print("\n" + "="*80)
    print("ANALYSIS")
    print("="*80)
    is_increasing = all(avg_latencies[i] <= avg_latencies[i+1] for i in range(len(avg_latencies)-1))
    
    if is_increasing:
        print("Result: CORRECT - Latency increases with quorum!")
        print("Explanation: Higher quorum = wait for more followers = higher latency")
    else:
        print("Result: UNEXPECTED - Latency does NOT strictly increase")
        print("Possible causes:")
        print("  - Network delays are too small (increase MAX_DELAY_MS)")
        print("  - Not enough writes to average out randomness")
        print("  - Timeout is too large (allows slow followers to respond)")
    
    print("\n" + "="*80)
    print("Performance test complete!")
    print("="*80)
