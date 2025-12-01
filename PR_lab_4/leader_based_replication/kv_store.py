import threading
from typing import Optional, Dict

# ---------------------------------------------------------
# Simple key-value store:
# - Keys are unique; writing the same key overwrites the value and increments the leader's sequence.
# - Values can repeat across different keys or over time.
# - Leader maintains per-key sequence counters to assign strictly increasing sequence numbers for writes.
#   Followers do not use these counters directly; they rely on the seq in ValueRecord to detect stale writes.
# Each key maps to a mutable ValueRecord(value, seq), keeping the value and its version together
# while the key itself remains immutable, ensuring atomic and consistent updates for replication.
# ---------------------------------------------------------

# ---------------------------------------------------------
# Represents a stored value together with its sequence number.
# The sequence number is crucial for conflict resolution:
# followers only apply updates if the incoming sequence
# is newer than what they have (avoiding race conditions).
# ---------------------------------------------------------
class ValueRecord:
    def __init__(self, value: str, seq: int):
        # The actual value associated with a key
        self.value = value

        # The sequence number (monotonically increasing per key)
        # - Incremented by the leader
        # - Used by followers to avoid stale writes
        self.seq = seq

    # Converts this object into a simple dictionary format
    # Useful for JSON responses, debugging, and consistency checks
    def to_dict(self):
        return {"value": self.value, "seq": self.seq}


# ---------------------------------------------------------
# KVStore is the in-memory, thread-safe key-value storage.
# It is used by both leader and follower nodes:
#   - Leader increments sequence numbers and writes new values.
#   - Followers apply replicated updates from the leader.
#
# Responsibilities:
#   - Store (key → ValueRecord)
#   - Maintain per-key sequence counters (leader only)
#   - Ensure thread safety during concurrent access
# ---------------------------------------------------------
class KVStore:
    def __init__(self):
        # The actual key-value map
        # key: str → ValueRecord
        self._store: Dict[str, ValueRecord] = {}

        # Per-key sequence number tracker (leader-only)
        # - Ensures each write gets a strictly increasing sequence
        # - Followers ignore this; they only check seq in ValueRecord
        self._seq_counters: Dict[str, int] = {}

        # A lock protecting all read/write operations
        # Because requests run concurrently inside each container
        self._lock = threading.Lock()

    # -----------------------------------------------------
    # Leader-only method:
    # - Increments the sequence number for this key
    # - Stores the new ValueRecord
    # Returns the assigned sequence number.
    #
    # This seq is then sent to followers for replication.
    # -----------------------------------------------------
    def put_with_seq(self, key: str, value: str) -> int:
        """Leader only: increment seq and store"""
        with self._lock:
            # Get previous sequence (default 0), then increment
            seq = self._seq_counters.get(key, 0) + 1

            # Update internal sequence tracker
            self._seq_counters[key] = seq

            # Store the updated value + sequence
            self._store[key] = ValueRecord(value, seq)

            return seq

    # -----------------------------------------------------
    # Follower-only method:
    # Applies a replicated write *only if* the sequence
    # number is newer (higher) than what this follower has.
    #
    # This solves race conditions caused by:
    # - request delays (leader → follower)
    # - out-of-order message delivery
    #
    # Returns:
    #    True  = update applied
    #    False = stale write ignored
    # -----------------------------------------------------
    def replicate(self, key: str, value: str, seq: int) -> bool:
        """Follower only: apply if seq is higher"""
        with self._lock:
            existing = self._store.get(key)

            # If nothing exists OR incoming seq is newer → apply
            if existing is None or seq > existing.seq:
                self._store[key] = ValueRecord(value, seq)
                return True

            # Incoming write is older → ignore
            return False

    # -----------------------------------------------------
    # Returns the latest ValueRecord for a key.
    # Used by leader and followers to serve GET requests.
    # -----------------------------------------------------
    def get(self, key: str) -> Optional[ValueRecord]:
        with self._lock:
            return self._store.get(key)

    # -----------------------------------------------------
    # Returns the full store as a dictionary.
    # Used for:
    #   - debugging
    #   - verifying consistency at the end of the lab
    #   - integration tests
    # -----------------------------------------------------
    def dump(self) -> Dict[str, dict]:
        with self._lock:
            return {k: v.to_dict() for k, v in self._store.items()}
