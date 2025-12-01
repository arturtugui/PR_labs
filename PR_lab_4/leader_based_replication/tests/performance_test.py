import requests
import time
import statistics
import concurrent.futures
import matplotlib.pyplot as plt
import subprocess
import yaml

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

def update_docker_compose_quorum(quorum_value):
    """Update docker-compose.yml with new WRITE_QUORUM"""
    with open('docker-compose.yml', 'r') as f:
        compose = yaml.safe_load(f)

    compose['services']['leader']['environment'] = [
        env if not env.startswith('WRITE_QUORUM=') else f'WRITE_QUORUM={quorum_value}'
        for env in compose['services']['leader']['environment']
    ]

    with open('docker-compose.yml', 'w') as f:
        yaml.dump(compose, f)

def restart_leader():
    """Restart leader container"""
    subprocess.run(['docker-compose', 'restart', 'leader'], check=True)
    time.sleep(3)  # Wait for leader to be ready

if __name__ == "__main__":
    quorums = [1, 2, 3, 4, 5]
    avg_latencies = []

    for quorum in quorums:
        print(f"\nTesting WRITE_QUORUM = {quorum}")

        # Update docker-compose and restart leader automatically
        update_docker_compose_quorum(quorum)
        restart_leader()

        avg, std = run_experiment()
        avg_latencies.append(avg)
        print(f"   Average latency: {avg:.2f} ms (std dev: {std:.2f})")

    # Plot results
    plt.figure(figsize=(10, 6))
    plt.plot(quorums, avg_latencies, marker='o', linewidth=2, markersize=8)
    plt.xlabel('WRITE_QUORUM (number of follower confirmations)', fontsize=12)
    plt.ylabel('Average Write Latency (ms)', fontsize=12)
    plt.title('Write Quorum vs Average Latency', fontsize=14)
    plt.grid(True, alpha=0.3)
    plt.xticks(quorums)

    # Annotate points
    for q, lat in zip(quorums, avg_latencies):
        plt.annotate(f'{lat:.1f}ms', (q, lat), textcoords="offset points",
                    xytext=(0,10), ha='center')

    plt.tight_layout()
    plt.savefig('quorum_vs_latency.png', dpi=300)
    print("\nPlot saved to quorum_vs_latency.png")
    plt.close()  # Close instead of show() so program doesn't block

    # Check consistency
    print("\nChecking consistency across replicas...")
    time.sleep(2)

    leader_dump = requests.get(f"{LEADER_URL}/dump").json()['entries']
    follower_urls = [f"http://localhost:{8001+i}" for i in range(5)]

    print(f"\nLeader has {len(leader_dump)} keys")
    
    for follower_url in follower_urls:
        follower_dump = requests.get(f"{follower_url}/dump").json()['entries']

        mismatches = 0
        missing = 0
        for key in leader_dump:
            if key not in follower_dump:
                missing += 1
            elif leader_dump[key]['seq'] != follower_dump[key]['seq']:
                mismatches += 1

        status = "OK" if mismatches == 0 else "LAG"
        print(f"{follower_url}: {len(follower_dump)}/{len(leader_dump)} keys, {missing} missing, {mismatches} older seq [{status}]")
    
    print("\nNote: Followers may lag behind due to different quorum values during tests.")
    print("This is EXPECTED behavior in semi-synchronous replication!")
    print("In production, lagging followers would eventually catch up.")
    print("\nPerformance test complete!")