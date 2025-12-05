# Performance Test Results

**Test Configuration:**
- MIN_DELAY_MS: 100
- MAX_DELAY_MS: 2000
- Total Writes: 100
- Concurrent Batch: 10

## Latency Results

| Quorum | Avg Latency (ms) |
|--------|------------------|
| 1 | 615.60 |
| 2 | 889.60 |
| 3 | 1238.83 |
| 4 | 1463.21 |
| 5 | 1823.65 |

## Consistency Results

### Quorum = 1
- Leader Sequence: 10
- Follower Sequences: [7, 4, 9, 10, 3]
- Consistent Followers: 1/5

### Quorum = 2
- Leader Sequence: 10
- Follower Sequences: [9, 5, 10, 8, 10]
- Consistent Followers: 2/5

### Quorum = 3
- Leader Sequence: 10
- Follower Sequences: [9, 9, 10, 10, 10]
- Consistent Followers: 3/5

### Quorum = 4
- Leader Sequence: 10
- Follower Sequences: [10, 10, 9, 10, 10]
- Consistent Followers: 4/5

### Quorum = 5
- Leader Sequence: 10
- Follower Sequences: [10, 10, 10, 10, 10]
- Consistent Followers: 5/5

## Analysis

**Latency Trend:** Latency increases with higher quorum values (expected - more followers must confirm).

**Consistency Observation:** Lower quorum values result in more inconsistent followers, demonstrating the trade-off between write latency and consistency guarantees.
