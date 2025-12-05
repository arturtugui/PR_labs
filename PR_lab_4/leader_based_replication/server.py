import os
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from kv_store import KVStore
from replication_manager import ReplicationManager
import uvicorn

# ---------------------------------------------------------
# Initialize FastAPI web application
# FastAPI handles HTTP requests (REST API endpoints)
# ---------------------------------------------------------
app = FastAPI()

# ---------------------------------------------------------
# Request/Response models for type validation
# ---------------------------------------------------------
class WriteRequest(BaseModel):
    key: str
    value: str

class ReplicateRequest(BaseModel):
    key: str
    value: str
    seq: int

class WriteResponse(BaseModel):
    ok: bool
    seq: int = None
    message: str

class GetResponse(BaseModel):
    key: str
    value: str
    seq: int

class DumpResponse(BaseModel):
    entries: dict
    role: str

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

    @app.post('/write', response_model=WriteResponse)
    async def write(request: WriteRequest):
        """
        Client write endpoint (leader only)
        - Accepts JSON payload {"key": ..., "value": ...}
        - Stores value locally with an incremented sequence number
        - Replicates the write to followers asynchronously
        - Returns success only if write_quorum of followers confirmed
        """
        key = request.key
        value = request.value

        seq = store.put_with_seq(key, value)

        quorum_reached = await replication_manager.replicate_to_followers(key, value, seq)

        if quorum_reached:
            return WriteResponse(ok=True, seq=seq, message="committed (quorum reached)")
        else:
            raise HTTPException(status_code=500, detail="quorum not reached")

# ---------------------------------------------------------
# FOLLOWER-SPECIFIC ENDPOINTS
# Only active if this node is a follower
# ---------------------------------------------------------
else:
    @app.post('/replicate')
    async def replicate(request: ReplicateRequest):
        """
        Receive replication from leader
        - Accepts JSON payload {"key": ..., "value": ..., "seq": ...}
        - Applies the update only if the incoming sequence number
          is higher than the current one (avoids stale writes)
        """
        key = request.key
        value = request.value
        seq = request.seq

        store.replicate(key, value, seq)

        return {"ok": True}

# ---------------------------------------------------------
# ENDPOINTS AVAILABLE FOR BOTH LEADER AND FOLLOWERS
# ---------------------------------------------------------
@app.get('/get', response_model=GetResponse)
async def get(key: str = Query(..., description="Key to retrieve")):
    """
    Read a key-value pair
    - Accepts query parameter 'key'
    - Returns the latest value and sequence number for that key
    """
    record = store.get(key)
    if record:
        return GetResponse(key=key, value=record.value, seq=record.seq)
    else:
        raise HTTPException(status_code=404, detail="Key not found")

@app.get('/dump', response_model=DumpResponse)
async def dump():
    """
    Return the entire key-value store
    - Useful for testing, debugging, or verifying consistency
    """
    return DumpResponse(entries=store.dump(), role=role)

@app.post('/reset')
async def reset():
    """
    Clear the entire key-value store
    - Used for testing to reset state between test runs
    """
    store.clear()
    return {"ok": True, "message": "Store cleared"}

# ---------------------------------------------------------
# Run the FastAPI application with uvicorn
# - Host 0.0.0.0 → accessible from outside Docker container
# - Port is configurable via environment variable PORT
# ---------------------------------------------------------
if __name__ == '__main__':
    port = int(os.getenv('PORT', 8000))
    print(f"Starting {role} on port {port}")
    uvicorn.run(app, host='0.0.0.0', port=port)
