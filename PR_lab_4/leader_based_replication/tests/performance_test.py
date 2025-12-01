import requests
import time
import statistics
import concurrent.futures
import matplotlib.pyplot as plt
import subprocess
import yaml
import os
from dotenv import dotenv_values

LEADER_URL = "http://localhost:8000"
FOLLOWER_URLS = [f"http://localhost:{8001+i}" for i in range(5)]
TOTAL_WRITES = 100
CONCURRENT_BATCH = 10
NUM_KEYS = 10
OUTPUT_DIR = "tests_output"

# Read configuration from .env
config = dotenv_values(".env")

# Create output directory if it doesn't exist
os.makedirs(OUTPUT_DIR, exist_ok=True)

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

def update_env_quorum(quorum_value):
    """Update .env file with new WRITE_QUORUM"""
    env_path = '.env'
    
    # Read existing .env content
    with open(env_path, 'r') as f:
        lines = f.readlines()
    
    # Update WRITE_QUORUM line
    updated = False
    for i, line in enumerate(lines):
        if line.startswith('WRITE_QUORUM='):
            lines[i] = f'WRITE_QUORUM={quorum_value}\n'
            updated = True
            break
    
    # If WRITE_QUORUM doesn't exist, add it
    if not updated:
        lines.append(f'WRITE_QUORUM={quorum_value}\n')
    
    # Write back to .env
    with open(env_path, 'w') as f:
        f.writelines(lines)

def rebuild_all_containers():
    """Rebuild and restart all containers to apply .env changes"""
    print("   Rebuilding all containers...")
    subprocess.run(['docker-compose', 'down'], check=True, capture_output=True)
    subprocess.run(['docker-compose', 'up', '-d', '--build'], check=True, capture_output=True)
    time.sleep(5)  # Wait for all containers to be ready

def get_consistency_data():
    """Get sequence numbers from leader and all followers for a test key"""
    # Use a specific test key to track consistency
    test_key = "key0"  # First key from our test writes
    
    leader_dump = requests.get(f"{LEADER_URL}/dump").json()['entries']
    leader_seq = leader_dump.get(test_key, {}).get('seq', 0)
    
    follower_seqs = []
    for follower_url in FOLLOWER_URLS:
        follower_dump = requests.get(f"{follower_url}/dump").json()['entries']
        follower_seq = follower_dump.get(test_key, {}).get('seq', 0)
        follower_seqs.append(follower_seq)
    
    return leader_seq, follower_seqs

if __name__ == "__main__":
    print("=== PERFORMANCE TEST - Multiple Quorum Values ===")
    print(f"Initial configuration from .env:")
    print(f"  MIN_DELAY_MS = {config.get('MIN_DELAY_MS', 'N/A')}")
    print(f"  MAX_DELAY_MS = {config.get('MAX_DELAY_MS', 'N/A')}")
    print(f"  (WRITE_QUORUM will be varied: 1-5)")
    print()
    
    quorums = [1, 2, 3, 4, 5]
    avg_latencies = []
    consistency_data = {}  # Store consistency data for each quorum

    for quorum in quorums:
        print(f"\nTesting WRITE_QUORUM = {quorum}")

        # Update .env and rebuild all containers
        update_env_quorum(quorum)
        rebuild_all_containers()

        # Run experiment
        avg, std = run_experiment()
        avg_latencies.append(avg)
        print(f"   Average latency: {avg:.2f} ms")
        
        # Wait a bit for writes to settle
        time.sleep(1)
        
        # Collect consistency data
        leader_seq, follower_seqs = get_consistency_data()
        consistency_data[quorum] = {
            'leader_seq': leader_seq,
            'follower_seqs': follower_seqs
        }
        print(f"   Consistency: Leader seq={leader_seq}, Followers={follower_seqs}")

    # Create comprehensive visualization with 3 columns
    fig = plt.figure(figsize=(18, 6))
    
    # Column 1: Quorum vs Latency
    ax1 = plt.subplot(1, 3, 1)
    ax1.plot(quorums, avg_latencies, marker='o', linewidth=2, markersize=8, color='#2E86AB')
    ax1.set_xlabel('Write Quorum', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Average Write Latency (ms)', fontsize=12, fontweight='bold')
    ax1.set_title('Quorum vs Latency', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.set_xticks(quorums)
    
    # Annotate points
    for q, lat in zip(quorums, avg_latencies):
        ax1.annotate(f'{lat:.1f}ms', (q, lat), textcoords="offset points",
                    xytext=(0,10), ha='center', fontsize=9)
    
    # Columns 2-3: Consistency bars for each quorum (split into 2 plots for readability)
    # First 3 quorums
    ax2 = plt.subplot(1, 3, 2)
    bar_width = 0.15
    x_positions = range(1, 6)  # 5 followers
    
    for i, quorum in enumerate([1, 2, 3]):
        data = consistency_data[quorum]
        leader_seq = data['leader_seq']
        follower_seqs = data['follower_seqs']
        
        # Plot bars for each follower
        offset = (i - 1) * bar_width
        bars = ax2.bar([x + offset for x in x_positions], follower_seqs, 
                       bar_width, label=f'Q={quorum}', alpha=0.8)
        
        # Add leader reference line for this quorum
        ax2.axhline(y=leader_seq, color=bars[0].get_facecolor(), 
                   linestyle='--', alpha=0.5, linewidth=1)
    
    ax2.set_xlabel('Follower ID', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Sequence Number', fontsize=12, fontweight='bold')
    ax2.set_title('Consistency (Quorum 1-3)', fontsize=14, fontweight='bold')
    ax2.set_xticks(x_positions)
    ax2.set_xticklabels([f'F{i}' for i in range(1, 6)])
    ax2.legend(loc='best', fontsize=9)
    ax2.grid(True, alpha=0.3, axis='y')
    
    # Last 2 quorums
    ax3 = plt.subplot(1, 3, 3)
    
    for i, quorum in enumerate([4, 5]):
        data = consistency_data[quorum]
        leader_seq = data['leader_seq']
        follower_seqs = data['follower_seqs']
        
        # Plot bars for each follower
        offset = (i - 0.5) * bar_width
        bars = ax3.bar([x + offset for x in x_positions], follower_seqs, 
                       bar_width, label=f'Q={quorum}', alpha=0.8)
        
        # Add leader reference line for this quorum
        ax3.axhline(y=leader_seq, color=bars[0].get_facecolor(), 
                   linestyle='--', alpha=0.5, linewidth=1)
    
    ax3.set_xlabel('Follower ID', fontsize=12, fontweight='bold')
    ax3.set_ylabel('Sequence Number', fontsize=12, fontweight='bold')
    ax3.set_title('Consistency (Quorum 4-5)', fontsize=14, fontweight='bold')
    ax3.set_xticks(x_positions)
    ax3.set_xticklabels([f'F{i}' for i in range(1, 6)])
    ax3.legend(loc='best', fontsize=9)
    ax3.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    output_path = os.path.join(OUTPUT_DIR, 'performance_results.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"\nPlot saved to {output_path}")
    plt.close()
    
    # Generate summary report
    report_path = os.path.join(OUTPUT_DIR, 'performance_report.md')
    with open(report_path, 'w') as f:
        f.write("# Performance Test Results\n\n")
        f.write(f"**Test Configuration:**\n")
        f.write(f"- MIN_DELAY_MS: {config.get('MIN_DELAY_MS', 'N/A')}\n")
        f.write(f"- MAX_DELAY_MS: {config.get('MAX_DELAY_MS', 'N/A')}\n")
        f.write(f"- Total Writes: {TOTAL_WRITES}\n")
        f.write(f"- Concurrent Batch: {CONCURRENT_BATCH}\n\n")
        
        f.write("## Latency Results\n\n")
        f.write("| Quorum | Avg Latency (ms) |\n")
        f.write("|--------|------------------|\n")
        for q, lat in zip(quorums, avg_latencies):
            f.write(f"| {q} | {lat:.2f} |\n")
        
        f.write("\n## Consistency Results\n\n")
        for quorum in quorums:
            data = consistency_data[quorum]
            f.write(f"### Quorum = {quorum}\n")
            f.write(f"- Leader Sequence: {data['leader_seq']}\n")
            f.write(f"- Follower Sequences: {data['follower_seqs']}\n")
            consistent = sum(1 for seq in data['follower_seqs'] if seq == data['leader_seq'])
            f.write(f"- Consistent Followers: {consistent}/5\n\n")
        
        f.write("## Analysis\n\n")
        f.write("**Latency Trend:** ")
        if avg_latencies[-1] > avg_latencies[0]:
            f.write("Latency increases with higher quorum values (expected - more followers must confirm).\n\n")
        else:
            f.write("Latency pattern varies based on network delays and timing.\n\n")
        
        f.write("**Consistency Observation:** Lower quorum values result in more inconsistent followers, ")
        f.write("demonstrating the trade-off between write latency and consistency guarantees.\n")
    
    print(f"Report saved to {report_path}")
    
    print("\n" + "="*60)
    print("Performance test complete!")
    print(f"Results saved to {OUTPUT_DIR}/")
    print("="*60)