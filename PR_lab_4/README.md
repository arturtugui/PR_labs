# Laboratory Work No. 4 Report: Distributed Key-Value Store with Leader-Based Replication

**Course:** Programare în Rețea

**Author:** Țugui Artur, FAF-231

---

## 1. Project Overview

### 1.1 Objectives

Implement a distributed key-value store with:

- **Single-leader replication architecture** (1 leader + 5 followers)
- **Semi-synchronous replication** with configurable write quorum
- **Concurrent request handling** on both leader and followers
- **Race condition prevention** using per-key sequence numbers
- **Performance analysis** comparing write latency across different quorum values

### 1.2 Directory Structure

```
PR_lab_4/leader_based_replication/
├── server.py                    # Main Flask server (leader/follower behavior)
├── kv_store.py                  # Thread-safe key-value store with versioning
├── replication_manager.py       # Leader's replication logic
├── requirements.txt             # Python dependencies (Flask, requests)
├── Dockerfile                   # Container image definition
├── docker-compose.yml           # Multi-container orchestration (1 leader + 5 followers)
├── tests/
│   ├── integration_test.py      # Basic correctness tests
│   ├── diagnostic_test.py       # Side-by-side data comparison tool
│   └── performance_test_manual.py # Latency vs quorum analysis
└── TESTING_COMMANDS.md          # Manual testing commands
```

---

## 2. Architecture & Design

### 2.1 Leader-Based Replication

**Leader responsibilities:**

- Accept all client write requests (POST `/write`)
- Assign monotonically increasing sequence numbers per key
- Replicate writes to all followers concurrently
- Wait for write quorum confirmations before returning success
- Serve read requests (GET `/get`)

**Follower responsibilities:**

- Accept replication requests from leader only (POST `/replicate`)
- Apply writes atomically using sequence number checks
- Ignore stale writes (older sequence numbers)
- Serve read requests (GET `/get`)

**Communication flow:**

```
Client → Leader (write) → Leader assigns seq → Leader writes locally
                                              ↓
                                    Concurrent replication to all followers
                                              ↓
                        Wait for WRITE_QUORUM confirmations (semi-synchronous)
                                              ↓
                                    Return success to client
```

### 2.2 Semi-Synchronous Replication

**Definition:** The leader waits for acknowledgments from **N out of M** followers before confirming a write to the client, where:

- **M = 5** (total number of followers)
- **N = WRITE_QUORUM** (configurable: 1-5)

**Characteristics:**

- **N = 1 (asynchronous-like):** Fastest, lowest durability
- **N = 5 (fully synchronous):** Slowest, highest durability
- **N = 3 (typical):** Balance between performance and consistency

**Implementation detail:**

```python
for future in as_completed(futures, timeout=...):
    if future.result():
        confirmations += 1
        if confirmations >= self.write_quorum:
            return True  # Early return when quorum reached!
```

This ensures we wait for the **N-th fastest** follower, not all M followers.

---

## 3. Data Store Implementation

### 3.1 Why Two Data Structures?

The `KVStore` class maintains **two separate dictionaries**:

```python
class KVStore:
    def __init__(self):
        self._store: Dict[str, ValueRecord] = {}        # Actual key-value storage
        self._seq_counters: Dict[str, int] = {}         # Per-key sequence counters
        self._lock = threading.Lock()
```

**Reason for separation:**

1. **`_store` (Dict[str, ValueRecord]):**

   - Stores the actual data: `key → ValueRecord(value, seq)`
   - Contains BOTH the current value AND its sequence number
   - Used by both leader and followers
   - Example: `{"key1": ValueRecord("hello", 5)}`

2. **`_seq_counters` (Dict[str, int]):**
   - **Leader-only** tracking of the next sequence number to assign
   - Simpler counter: `key → next_seq_number`
   - Used ONLY for generating new sequence numbers on writes
   - Example: `{"key1": 5}` means next write to key1 gets seq=6

**Why not merge them?**

- Followers don't need `_seq_counters` (they receive seq from leader)
- Separating concerns makes the code clearer
- Leader needs to atomically: increment counter → create ValueRecord → store

### 3.2 Per-Key Sequence Numbers

**Purpose:** Prevent race conditions from out-of-order message delivery

**How it works:**

**Leader side (assignment):**

```python
def put_with_seq(self, key: str, value: str) -> int:
    with self._lock:
        seq = self._seq_counters.get(key, 0) + 1  # Increment counter
        self._seq_counters[key] = seq              # Update counter
        self._store[key] = ValueRecord(value, seq) # Store with seq
        return seq
```

**Follower side (application):**

```python
def replicate(self, key: str, value: str, seq: int) -> bool:
    with self._lock:
        existing = self._store.get(key)

        # Only apply if incoming seq is HIGHER than current
        if existing is None or seq > existing.seq:
            self._store[key] = ValueRecord(value, seq)
            return True

        return False  # Stale write, ignored
```

**Example scenario (race condition prevention):**

```
Timeline:
- Client writes key="x" → Leader assigns seq=1, value="A"
- Client writes key="x" → Leader assigns seq=2, value="B"
- Leader sends both to followers concurrently

Follower 1 receives: seq=1, then seq=2 → Final state: ("B", 2) ✓
Follower 2 receives: seq=2, then seq=1 → Applies seq=2, ignores seq=1 → Final state: ("B", 2) ✓
```

Without sequence numbers, Follower 2 would end up with `("A", 1)` → **INCONSISTENCY!**

---

## 4. Replication Manager

### 4.1 Concurrent Replication with Delays

Simulates real-world network latency:

```python
def replicate_to_one(follower_url: str) -> bool:
    # Random delay between MIN_DELAY_MS and MAX_DELAY_MS
    delay_ms = random.randint(self.min_delay, self.max_delay)
    time.sleep(delay_ms / 1000.0)

    # Send HTTP POST /replicate
    response = requests.post(
        f"{follower_url}/replicate",
        json={"key": key, "value": value, "seq": seq},
        timeout=2
    )

    return response.status_code == 200 and response.json().get('ok')
```

### 4.2 Write Quorum Implementation

**Key challenge:** "Wait for N out of M tasks to complete" (order statistics problem)

**Solution using `as_completed`:**

```python
with ThreadPoolExecutor(max_workers=len(self.follower_urls)) as executor:
    futures = [executor.submit(replicate_to_one, url) for url in self.follower_urls]

    for future in as_completed(futures, timeout=self.timeout / 1000.0):
        if future.result():
            with lock:
                confirmations += 1
                if confirmations >= self.write_quorum:
                    return True  # Return immediately when quorum reached!
```

**Why this works:**

- `as_completed()` yields futures in the order they COMPLETE (not submission order)
- We return as soon as we get the N-th confirmation
- We don't wait for all M followers (that would be fully synchronous)

**Performance implication:**

- **Quorum = 1:** Wait for fastest follower → low latency
- **Quorum = 3:** Wait for 3rd-fastest (median) → medium latency
- **Quorum = 5:** Wait for slowest follower → high latency

---

## 5. Docker Configuration

### 5.1 Single Container Image, Multiple Roles

**Key insight:** Same code runs in all 6 containers, behavior determined by `ROLE` environment variable

```dockerfile
FROM python:3.11-slim
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY server.py kv_store.py replication_manager.py .

EXPOSE 8000
CMD ["python", "server.py"]
```

### 5.2 Docker Compose (Simplified)

```yaml
services:
  leader:
    build: .
    environment:
      - ROLE=leader
      - PORT=8000
      - FOLLOWERS=http://follower1:8001,http://follower2:8002,...
      - MIN_DELAY_MS=50
      - MAX_DELAY_MS=500
      - WRITE_QUORUM=3
      - REPLICATION_TIMEOUT_MS=10000
    ports: ["8000:8000"]
    networks: [kvnet]

  follower1:
    build: .
    environment:
      - ROLE=follower
      - PORT=8001
    ports: ["8001:8001"]
    networks: [kvnet]

  # ... follower2-5 similar ...
```

**Network:** All containers on same bridge network (`kvnet`) for inter-container communication

---

## 6. API Endpoints

### 6.1 Leader Endpoints

**POST `/write` - Client write request**

```json
Request:  {"key": "user1", "value": "Alice"}
Response: {"ok": true, "seq": 5, "message": "committed (quorum reached)"}
```

**GET `/get?key=user1` - Read value**

```json
Response: {"key": "user1", "value": "Alice", "seq": 5}
```

**GET `/dump` - Dump entire store (debugging)**

```json
Response: {"entries": {"user1": {"value": "Alice", "seq": 5}}, "role": "leader"}
```

### 6.2 Follower Endpoints

**POST `/replicate` - Receive replication from leader**

```json
Request:  {"key": "user1", "value": "Alice", "seq": 5}
Response: {"ok": true}
```

**GET `/get?key=user1` - Read value (same as leader)**

**GET `/dump` - Dump entire store (same as leader)**

---

## 7. Testing & Results

### 7.1 Integration Test

**Purpose:** Verify basic replication and consistency

```python
# Write to leader
response = requests.post(f"{LEADER_URL}/write", json={"key": "test1", "value": "hello"})
assert response.json()['ok'] == True

# Wait for replication
time.sleep(1)

# Check followers
for follower_url in FOLLOWER_URLS:
    data = requests.get(f"{follower_url}/get?key=test1").json()
    # At least WRITE_QUORUM followers should have the data
```

### 7.2 Diagnostic Test Output

```
DATA COMPARISON TABLE
Key        | Leader          | F1              | F2              | F3              | F4              | F5
key0       | v:value_15, s:4 | v:value_15, s:4 OK | v:value_15, s:4 OK | v:value_15, s:4 OK | v:value_10, s:3 LAG | v:value_5, s:2 LAG
key1       | v:value_16, s:4 | v:value_16, s:4 OK | v:value_16, s:4 OK | v:value_16, s:4 OK | v:value_16, s:4 OK | v:value_11, s:3 LAG
...

CONSISTENCY ANALYSIS
Follower 1: 5/5 match (100%), 0 lag, 0 missing
Follower 2: 5/5 match (100%), 0 lag, 0 missing
Follower 3: 5/5 match (100%), 0 lag, 0 missing
Follower 4: 3/5 match (60%), 2 lag, 0 missing
Follower 5: 2/5 match (40%), 3 lag, 0 missing
```

**Interpretation (with WRITE_QUORUM=3):**

- Followers 1-3 are always in sync (part of quorum)
- Followers 4-5 may lag behind (eventual consistency)
- This is **EXPECTED and CORRECT** behavior for semi-synchronous replication

### 7.3 Performance Test Results (Expected)

**Test setup:**

- 100 concurrent writes (10 at a time)
- 10 keys (each written 10 times)
- Delays: [50ms, 500ms]

**Expected latency trend:**

| WRITE_QUORUM | Expected Latency | Explanation                   |
| ------------ | ---------------- | ----------------------------- |
| 1            | ~100-150ms       | Wait for fastest follower     |
| 2            | ~200-250ms       | Wait for 2nd-fastest          |
| 3            | ~300-350ms       | Wait for median (3rd-fastest) |
| 4            | ~400-450ms       | Wait for 4th-fastest          |
| 5            | ~500-550ms       | Wait for slowest follower     |

**Mathematical basis:** This is the **k-th order statistic** of 5 random variables uniformly distributed in [50, 500].

---

## 8. Key Concepts & Lessons Learned

### 8.1 Race Condition in Distributed Systems

**The problem:** Without sequence numbers, concurrent writes to the same key can arrive out-of-order at different followers, causing inconsistent final states.

**The solution:** Leader-assigned monotonically increasing sequence numbers + follower-side atomic compare-and-update.

### 8.2 Semi-Synchronous Replication Trade-offs

| Aspect            | Low Quorum (N=1)              | High Quorum (N=5)               |
| ----------------- | ----------------------------- | ------------------------------- |
| **Write Latency** | Low                           | High                            |
| **Durability**    | Low (only 2 copies: leader+1) | High (6 copies: leader+5)       |
| **Availability**  | High (tolerates 4 failures)   | Low (any failure blocks writes) |
| **Consistency**   | Eventual                      | Strong                          |

### 8.3 Concurrency Control

**Three levels of concurrency:**

1. **Client-to-leader:** Multiple clients write concurrently (Flask `threaded=True`)
2. **Leader-to-followers:** Replication requests sent concurrently (`ThreadPoolExecutor`)
3. **Follower internal:** Each follower handles replications concurrently (Flask `threaded=True`)

**Synchronization:** Thread locks (`threading.Lock`) protect shared state (`_store`, `_seq_counters`, `confirmations`)

### 8.4 Order Statistics Problem

**Question:** If you have 5 tasks with random completion times in [a, b], how long does it take for the k-th task to complete?

**Answer:** The k-th order statistic follows a Beta distribution:

- E[X₍₁₎] ≈ a + (b-a)/6 (minimum)
- E[X₍₃₎] ≈ a + (b-a)/2 (median)
- E[X₍₅₎] ≈ a + 5(b-a)/6 (maximum)

This explains why quorum=3 should give approximately median latency.

---

## 9. Known Issues & Future Work

### 9.1 Current Issues

1. **Latency not strictly increasing:** Random delays may not provide enough separation between quorum values in small-scale tests
2. **No leader election:** If leader fails, system stops (no automatic failover)
3. **No persistent storage:** All data lost on container restart
4. **Network delays are simulated:** Real networks have more complex behavior (jitter, packet loss, reordering)

### 9.2 Potential Improvements

1. **Increase delay range:** Use [100ms, 2000ms] for clearer quorum differences
2. **Add leader election:** Implement Raft or Paxos for automatic failover
3. **Persistent replication log:** Write-ahead log for durability
4. **Conflict resolution:** Handle concurrent writes to same key with version vectors or CRDTs
5. **Read quorums:** Allow configurable read quorums for linearizable reads
6. **Monitoring dashboard:** Real-time view of replication lag per follower

---

## 10. Running the Lab

### 10.1 Setup

```powershell
cd PR_lab_4/leader_based_replication

# Start all containers
docker-compose up --build -d

# Check status
docker ps

# View logs
docker-compose logs -f leader
```

### 10.2 Manual Testing

```powershell
# Write to leader
curl.exe -X POST http://localhost:8000/write -H "Content-Type: application/json" -d '{"key":"test","value":"hello"}'

# Read from leader
curl.exe http://localhost:8000/get?key=test

# Read from follower
curl.exe http://localhost:8001/get?key=test

# Dump all data
curl.exe http://localhost:8000/dump
```

### 10.3 Automated Tests

```powershell
# Integration test
py .\tests\integration_test.py

# Diagnostic test (side-by-side comparison)
py .\tests\diagnostic_test.py

# Performance test (manual quorum changes)
py .\tests\performance_test_manual.py
```

### 10.4 Cleanup

```powershell
# Stop and remove containers
docker-compose down

# Remove images
docker-compose down --rmi all
```

---

## 11. References

1. Kleppmann, M. (2017). _Designing Data-Intensive Applications_, Chapter 5: Replication
2. Ongaro, D., & Ousterhout, J. (2014). _In Search of an Understandable Consensus Algorithm (Raft)_
3. PostgreSQL Documentation: Streaming Replication
4. MySQL Documentation: Semi-Synchronous Replication

---

## 12. Conclusion

This laboratory work demonstrates the fundamental concepts of distributed database replication:

- **Leader-based architecture** provides a simple and effective replication model
- **Semi-synchronous replication** offers a tunable trade-off between performance and durability
- **Sequence numbers** are essential for preventing race conditions in distributed systems
- **Order statistics** explain the relationship between write quorum and latency

The implementation successfully handles concurrent requests, prevents race conditions through versioning, and demonstrates the performance characteristics of different quorum configurations. While simplified compared to production systems (no leader election, no persistence), it captures the core challenges and solutions in distributed data storage.

---

**End of Report**
