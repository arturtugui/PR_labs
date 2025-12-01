import os
from flask import Flask, request, jsonify
from kv_store import KVStore
from replication_manager import ReplicationManager

# ---------------------------------------------------------
# Initialize Flask web application
# Flask handles HTTP requests (REST API endpoints)
# ---------------------------------------------------------
app = Flask(__name__)

# ---------------------------------------------------------
# Initialize an in-memory key-value store
# Used by both leader and follower nodes
# ---------------------------------------------------------
store = KVStore()

# ---------------------------------------------------------
# Determine the role of this node from environment variable
# 'leader' → node accepts client writes and replicates
# 'follower' → node only accepts replication from leader
# Default role is 'follower'
# ---------------------------------------------------------
role = os.getenv('ROLE', 'follower')

# ---------------------------------------------------------
# LEADER-SPECIFIC ENDPOINTS
# Only active if this node is the leader
# ---------------------------------------------------------
if role == 'leader':
    # Initialize replication manager for handling followers
    replication_manager = ReplicationManager()

    @app.route('/write', methods=['POST'])
    def write():
        """
        Client write endpoint (leader only)
        - Accepts JSON payload {"key": ..., "value": ...}
        - Stores value locally with an incremented sequence number
        - Replicates the write to followers
        - Returns success only if write_quorum of followers confirmed
        """
        data = request.json
        key = data.get('key')
        value = data.get('value')

        if not key or value is None:
            return jsonify({"ok": False, "message": "Missing key or value"}), 400

        seq = store.put_with_seq(key, value)

        quorum_reached = replication_manager.replicate_to_followers(key, value, seq)

        if quorum_reached:
            return jsonify({"ok": True, "seq": seq, "message": "committed (quorum reached)"}), 200
        else:
            return jsonify({"ok": False, "message": "quorum not reached"}), 500

# ---------------------------------------------------------
# FOLLOWER-SPECIFIC ENDPOINTS
# Only active if this node is a follower
# ---------------------------------------------------------
else:
    @app.route('/replicate', methods=['POST'])
    def replicate():
        """
        Receive replication from leader
        - Accepts JSON payload {"key": ..., "value": ..., "seq": ...}
        - Applies the update only if the incoming sequence number
          is higher than the current one (avoids stale writes)
        """
        data = request.json
        key = data.get('key')
        value = data.get('value')
        seq = data.get('seq')

        if not key or value is None or seq is None:
            return jsonify({"ok": False}), 400

        store.replicate(key, value, seq)

        return jsonify({"ok": True}), 200

# ---------------------------------------------------------
# ENDPOINTS AVAILABLE FOR BOTH LEADER AND FOLLOWERS
# ---------------------------------------------------------
@app.route('/get', methods=['GET'])
def get():
    """
    Read a key-value pair
    - Accepts query parameter 'key'
    - Returns the latest value and sequence number for that key
    """
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
    """
    Return the entire key-value store
    - Useful for testing, debugging, or verifying consistency
    """
    return jsonify({"entries": store.dump(), "role": role}), 200

# ---------------------------------------------------------
# Run the Flask application
# - Host 0.0.0.0 → accessible from outside Docker container
# - Port is configurable via environment variable PORT
# - threaded=True → allows multiple concurrent requests
# ---------------------------------------------------------
if __name__ == '__main__':
    port = int(os.getenv('PORT', 8000))
    print(f"Starting {role} on port {port}")
    app.run(host='0.0.0.0', port=port, threaded=True)
