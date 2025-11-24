"""WebSocket endpoints for live job updates."""
from typing import List, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from models.rocket_job import RocketJob
import uuid

router = APIRouter(prefix="/api/v1/ws", tags=["websockets"])


class ConnectionManager:
    """Manages WebSocket connections."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.user_connections: dict = {}  # Map user_id to list of connections
    
    async def connect(self, websocket: WebSocket, user_id: Optional[uuid.UUID] = None):
        """Accept a WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = []
            self.user_connections[user_id].append(websocket)
    
    def disconnect(self, websocket: WebSocket, user_id: Optional[uuid.UUID] = None):
        """Remove a WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if user_id and user_id in self.user_connections:
            if websocket in self.user_connections[user_id]:
                self.user_connections[user_id].remove(websocket)
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send a message to a specific connection."""
        await websocket.send_json(message)
    
    async def broadcast(self, message: dict):
        """Broadcast a message to all connected clients."""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"Error broadcasting to connection: {e}")
    
    async def broadcast_to_user(self, message: dict, user_id: uuid.UUID):
        """Broadcast a message to all connections for a specific user."""
        if user_id in self.user_connections:
            for connection in self.user_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    print(f"Error sending to user connection: {e}")


manager = ConnectionManager()


@router.websocket("/jobs")
async def websocket_jobs(
    websocket: WebSocket,
    user_id: Optional[str] = Query(None, description="Optional: filter to user-specific jobs")
):
    """WebSocket endpoint for live job updates.
    
    Supports subscription to all jobs or user-specific jobs.
    Sends messages on job state changes.
    """
    # For simplicity, we'll accept connections without authentication
    # In production, you should validate the JWT token from query params or headers
    parsed_user_id = None
    if user_id:
        try:
            parsed_user_id = uuid.UUID(user_id)
        except ValueError:
            await websocket.close(code=1008, reason="Invalid user_id format")
            return
    
    await manager.connect(websocket, parsed_user_id)
    
    try:
        # Send initial connection confirmation
        await manager.send_personal_message(
            {"type": "connected", "message": "Connected to job updates"},
            websocket
        )
        
        # Keep connection alive and handle incoming messages
        while True:
            data = await websocket.receive_text()
            # Echo back or handle client messages if needed
            await manager.send_personal_message(
                {"type": "echo", "data": data},
                websocket
            )
    except WebSocketDisconnect:
        manager.disconnect(websocket, parsed_user_id)


# Helper function to broadcast job updates (can be called from other parts of the app)
async def broadcast_job_update(job: RocketJob, user_id: Optional[uuid.UUID] = None):
    """Broadcast a job update to connected clients."""
    message = {
        "type": "job_update",
        "job": {
            "id": str(job.id),
            "state": job.state.value,
            "source": job.source,
            "destination": job.destination,
            "location": job.location,
            "estimated_time": job.estimated_time,
            "status": job.status.value,
            "updated_at": job.updated_at.isoformat()
        }
    }
    
    if user_id:
        await manager.broadcast_to_user(message, user_id)
    else:
        await manager.broadcast(message)

