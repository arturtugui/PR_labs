# PR Lab 4 - Key-Value Store with Replication

## Implementation Plan (Python)

---

## 📋 Overview

Build a distributed key-value store with:

- **1 Leader** (accepts writes, replicates to followers)
- **5 Followers** (receive replications, serve reads)
- **Semi-synchronous replication** with configurable write quorum
- **Per-key sequence numbers** to prevent race conditions

---

## 🗂️ Project Structure

```
PR_lab_4/
├── server.py                 # Main server (acts as leader OR follower)
├── kv_store.py              # In-memory store with sequence numbers
├── replication_manager.py   # Leader's replication logic
├── requirements.txt         # Python dependencies
├── Dockerfile               # Container image
├── docker-compose.yml       # 6 containers (1 leader + 5 followers)
├── tests/
│   ├── integration_test.py  # Basic correctness test
│   └── performance_test.py  # Latency vs quorum analysis
└── README.md                # Setup and usage instructions
```

---

## 📝 Step-by-Step Implementation

### **Step 1: Core Data Store (`kv_store.py`)**

**What it does:** Thread-safe in-memory key-value store with per-key versioning

```python
import threading
from typing import Optional, Dict, Tuple

class ValueRecord:
    def __init__(self, value: str, seq: int):
        self.value = value
        self.seq = seq

    def to_dict(self):
        return {"value": self.value, "seq": self.seq}

class KVStore:
    def __init__(self):
        self._store: Dict[str, ValueRecord] = {}
        self._seq_counters: Dict[str, int] = {}  # Per-key sequence counter
        self._lock = threading.Lock()

    def put_with_seq(self, key: str, value: str) -> int:
        """Leader only: increment seq and store"""
        with self._lock:
            seq = self._seq_counters.get(key, 0) + 1
            self._seq_counters[key] = seq
            self._store[key] = ValueRecord(value, seq)
            return seq

    def replicate(self, key: str, value: str, seq: int) -> bool:
        """Follower only: apply if seq is higher"""
        with self._lock:
            existing = self._store.get(key)
            if existing is None or seq > existing.seq:
                self._store[key] = ValueRecord(value, seq)
                return True
            return False  # Stale write, ignored

    def get(self, key: str) -> Optional[ValueRecord]:
        with self._lock:
            return self._store.get(key)

    def dump(self) -> Dict[str, dict]:
        with self._lock:
            return {k: v.to_dict() for k, v in self._store.items()}
```

**Key concepts:**

- `put_with_seq()`: Leader increments sequence number atomically
- `replicate()`: Follower only applies if `incoming_seq > current_seq` (prevents race condition!)
- Thread-safe with locks

---

### **Step 2: Replication Manager (`replication_manager.py`)**

**What it does:** Leader sends replications to followers concurrently with simulated delays

```python
import os
import time
import random
import requests
import threading
from typing import List
from concurrent.futures import ThreadPoolExecutor, as_completed

class ReplicationManager:
    def __init__(self):
        self.follower_urls = os.getenv('FOLLOWERS', '').split(',')
        self.write_quorum = int(os.getenv('WRITE_QUORUM', '1'))
        self.min_delay = int(os.getenv('MIN_DELAY_MS', '0'))
        self.max_delay = int(os.getenv('MAX_DELAY_MS', '200'))
        self.timeout = int(os.getenv('REPLICATION_TIMEOUT_MS', '5000'))

    def replicate_to_followers(self, key: str, value: str, seq: int) -> bool:
        """
        Send replication to all followers concurrently.
        Returns True if write_quorum confirmations received.
        """
        confirmations = 0
        lock = threading.Lock()

        def replicate_to_one(follower_url: str):
            nonlocal confirmations
            try:
                # Simulate network lag
                delay_ms = random.randint(self.min_delay, self.max_delay)
                time.sleep(delay_ms / 1000.0)

                # Send POST /replicate
                response = requests.post(
                    f"{follower_url}/replicate",
                    json={"key": key, "value": value, "seq": seq},
                    timeout=2
                )

                if response.status_code == 200 and response.json().get('ok'):
                    with lock:
                        confirmations += 1

            except Exception as e:
                print(f"Replication to {follower_url} failed: {e}")

        # Execute concurrently
        with ThreadPoolExecutor(max_workers=len(self.follower_urls)) as executor:
            futures = [executor.submit(replicate_to_one, url) for url in self.follower_urls]

            # Wait for quorum or timeout
            start_time = time.time()
            while (time.time() - start_time) < (self.timeout / 1000.0):
                with lock:
                    if confirmations >= self.write_quorum:
                        return True
                time.sleep(0.01)  # Check every 10ms

        # Final check after all futures complete
        with lock:
            return confirmations >= self.write_quorum
```

**Key concepts:**

- `ThreadPoolExecutor`: Runs replications concurrently
- Random delay before each replication (simulates network lag)
- Waits until `write_quorum` confirmations received

---

### **Step 3: HTTP Server (`server.py`)**

**What it does:** Single Flask app that acts as leader or follower based on `ROLE` env var

```python
import os
from flask import Flask, request, jsonify
from kv_store import KVStore
from replication_manager import ReplicationManager

app = Flask(__name__)
store = KVStore()
role = os.getenv('ROLE', 'follower')

# Leader only
if role == 'leader':
    replication_manager = ReplicationManager()

    @app.route('/put', methods=['POST'])
    def put():
        """Client write endpoint (leader only)"""
        data = request.json
        key = data.get('key')
        value = data.get('value')

        if not key or value is None:
            return jsonify({"ok": False, "message": "Missing key or value"}), 400

        # 1. Write locally and get sequence number
        seq = store.put_with_seq(key, value)

        # 2. Replicate to followers
        quorum_reached = replication_manager.replicate_to_followers(key, value, seq)

        if quorum_reached:
            return jsonify({"ok": True, "seq": seq, "message": "committed (quorum reached)"}), 200
        else:
            return jsonify({"ok": False, "message": "quorum not reached"}), 500

# Follower only
else:
    @app.route('/replicate', methods=['POST'])
    def replicate():
        """Receive replication from leader"""
        data = request.json
        key = data.get('key')
        value = data.get('value')
        seq = data.get('seq')

        if not key or value is None or seq is None:
            return jsonify({"ok": False}), 400

        # Apply atomically (only if seq > current)
        store.replicate(key, value, seq)

        return jsonify({"ok": True}), 200

# Both leader and followers
@app.route('/get', methods=['GET'])
def get():
    """Read key-value"""
    key = request.args.get('key')
    if not key:
        return jsonify({"error": "Missing key parameter"}), 400

    record = store.get(key)
    if record:
        return jsonify({"key": key, "value": record.value, "seq": record.seq}), 200
    else:
        return jsonify({"error": "Key not found"}), 404

@app.route('/dump', methods=['GET'])
def dump():
    """Return entire store (for testing)"""
    return jsonify({"entries": store.dump(), "role": role}), 200

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8000))
    print(f"Starting {role} on port {port}")
    app.run(host='0.0.0.0', port=port, threaded=True)
```

**Key concepts:**

- Flask with `threaded=True` handles concurrent requests
- Leader has `/put` endpoint, follower has `/replicate`
- Both have `/get` and `/dump`

---

### **Step 4: Python Dependencies (`requirements.txt`)**

```
Flask==3.0.0
requests==2.31.0
```

---

### **Step 5: Dockerfile**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copy Python files
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .
COPY kv_store.py .
COPY replication_manager.py .

# Expose port (will be overridden by docker-compose)
EXPOSE 8000

# Run the server
CMD ["python", "server.py"]
```

---

### **Step 6: Docker Compose (`docker-compose.yml`)**

```yaml
version: "3.8"

services:
  leader:
    build: .
    container_name: leader
    environment:
      - ROLE=leader
      - PORT=8000
      - FOLLOWERS=http://follower1:8001,http://follower2:8002,http://follower3:8003,http://follower4:8004,http://follower5:8005
      - MIN_DELAY_MS=0
      - MAX_DELAY_MS=200
      - WRITE_QUORUM=3
      - REPLICATION_TIMEOUT_MS=5000
    ports:
      - "8000:8000"
    networks:
      - kvnet

  follower1:
    build: .
    container_name: follower1
    environment:
      - ROLE=follower
      - PORT=8001
    ports:
      - "8001:8001"
    networks:
      - kvnet

  follower2:
    build: .
    container_name: follower2
    environment:
      - ROLE=follower
      - PORT=8002
    ports:
      - "8002:8002"
    networks:
      - kvnet

  follower3:
    build: .
    container_name: follower3
    environment:
      - ROLE=follower
      - PORT=8003
    ports:
      - "8003:8003"
    networks:
      - kvnet

  follower4:
    build: .
    container_name: follower4
    environment:
      - ROLE=follower
      - PORT=8004
    ports:
      - "8004:8004"
    networks:
      - kvnet

  follower5:
    build: .
    container_name: follower5
    environment:
      - ROLE=follower
      - PORT=8005
    ports:
      - "8005:8005"
    networks:
      - kvnet

networks:
  kvnet:
    driver: bridge
```

**To change write quorum:** Edit `WRITE_QUORUM=3` under leader service

---

### **Step 7: Integration Test (`tests/integration_test.py`)**

```python
import requests
import time

LEADER_URL = "http://localhost:8000"
FOLLOWER_URLS = [f"http://localhost:{8001+i}" for i in range(5)]

def test_basic_replication():
    """Test that writes replicate to followers"""

    # Write to leader
    response = requests.post(f"{LEADER_URL}/put", json={"key": "test1", "value": "hello"})
    assert response.status_code == 200
    data = response.json()
    assert data['ok'] == True
    seq = data['seq']

    # Wait for replication
    time.sleep(1)

    # Check leader
    leader_data = requests.get(f"{LEADER_URL}/get?key=test1").json()
    assert leader_data['value'] == "hello"
    assert leader_data['seq'] == seq

    # Check followers
    for follower_url in FOLLOWER_URLS:
        follower_data = requests.get(f"{follower_url}/get?key=test1").json()
        print(f"{follower_url}: {follower_data}")
        # Not all followers may have it if quorum < 5

def test_consistency():
    """Test race condition - concurrent writes to same key"""

    # Many concurrent writes to same key
    import concurrent.futures

    def write_key(i):
        return requests.post(f"{LEADER_URL}/put", json={"key": "race_key", "value": f"value_{i}"})

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(write_key, i) for i in range(50)]
        results = [f.result() for f in futures]

    # Wait for all replications
    time.sleep(2)

    # Get final state from all nodes
    leader_dump = requests.get(f"{LEADER_URL}/dump").json()
    leader_value = leader_dump['entries'].get('race_key', {})

    print(f"\nLeader: {leader_value}")

    for follower_url in FOLLOWER_URLS:
        follower_dump = requests.get(f"{follower_url}/dump").json()
        follower_value = follower_dump['entries'].get('race_key', {})
        print(f"{follower_url}: {follower_value}")

        # With seq check: all should match leader's seq
        if follower_value:
            assert follower_value['seq'] == leader_value['seq'], \
                f"Inconsistency detected! Leader seq {leader_value['seq']} != Follower seq {follower_value['seq']}"

if __name__ == "__main__":
    print("Testing basic replication...")
    test_basic_replication()

    print("\nTesting consistency (race condition)...")
    test_consistency()

    print("\n✅ All tests passed!")
```

---

### **Step 8: Performance Test (`tests/performance_test.py`)**

```python
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

def send_put(key, value):
    """Send write and measure latency"""
    start = time.time()
    try:
        response = requests.post(f"{LEADER_URL}/put", json={"key": key, "value": value}, timeout=10)
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
            futures.append(executor.submit(send_put, key, value))

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
        print(f"\n📊 Testing WRITE_QUORUM = {quorum}")

        # Update and restart (or do manually)
        # update_docker_compose_quorum(quorum)
        # restart_leader()

        input(f"Press Enter after setting WRITE_QUORUM={quorum} and restarting leader...")

        avg, std = run_experiment()
        avg_latencies.append(avg)
        print(f"   Average latency: {avg:.2f} ms (±{std:.2f})")

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
    print("\n📈 Plot saved to quorum_vs_latency.png")
    plt.show()

    # Check consistency
    print("\n🔍 Checking consistency across replicas...")
    time.sleep(2)

    leader_dump = requests.get(f"{LEADER_URL}/dump").json()['entries']
    follower_urls = [f"http://localhost:{8001+i}" for i in range(5)]

    for follower_url in follower_urls:
        follower_dump = requests.get(f"{follower_url}/dump").json()['entries']

        mismatches = 0
        for key in leader_dump:
            if key in follower_dump:
                if leader_dump[key]['seq'] != follower_dump[key]['seq']:
                    mismatches += 1

        print(f"{follower_url}: {len(follower_dump)}/{len(leader_dump)} keys, {mismatches} mismatches")
```

---

## 🚀 Running the Lab

### Build and start containers:

```bash
cd PR_lab_4
docker-compose up --build -d
```

### Check logs:

```bash
docker-compose logs -f leader
docker-compose logs -f follower1
```

### Test manually:

```bash
# Write to leader
curl -X POST http://localhost:8000/put -H "Content-Type: application/json" -d '{"key":"test","value":"hello"}'

# Read from leader
curl http://localhost:8000/get?key=test

# Read from follower
curl http://localhost:8001/get?key=test

# Dump all data
curl http://localhost:8000/dump
```

### Run tests:

```bash
python tests/integration_test.py
python tests/performance_test.py
```

### Stop containers:

```bash
docker-compose down
```

---

## 📊 Expected Results

### Latency vs Quorum:

- **Quorum 1**: ~50-70ms (only 1 confirmation needed)
- **Quorum 3**: ~100-120ms (wait for 3rd-slowest follower)
- **Quorum 5**: ~150-200ms (wait for slowest follower)

**Explanation:** Higher quorum = wait for more (slower) followers = higher latency

### Consistency Check:

- **Without seq numbers**: Followers have different values (race condition!)
- **With seq numbers**: All followers have same seq as leader ✅

**Race condition:** Concurrent writes arrive out-of-order at followers. Seq numbers ensure only newest write is kept.

---

## 🎯 Key Takeaways

1. **Semi-synchronous replication**: Balance between consistency and availability
2. **Write quorum**: Trade-off between durability and latency
3. **Race conditions**: Concurrent + async = out-of-order delivery
4. **Solution**: Sequence numbers + atomic apply-if-higher

---

## 🔧 Troubleshooting

- **Quorum never reached**: Check `FOLLOWERS` URLs in docker-compose
- **Connection errors**: Ensure all containers are on same network (`kvnet`)
- **Port conflicts**: Change ports if 8000-8005 already in use
- **Slow tests**: Increase `REPLICATION_TIMEOUT_MS`
