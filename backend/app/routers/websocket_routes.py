"""
WebSocket routes for live meeting audio streaming.

This module provides WebSocket endpoints for real-time audio streaming,
transcription, and bidirectional communication during live meetings.
"""

import logging
import asyncio
import json
from typing import Dict, Optional
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.utils.auth_utils import verify_token
from app.models.live_session import LiveSession
from app.models.user import User
from app.services.live_audio_processor import LiveAudioProcessor

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])

# Heartbeat configuration
HEARTBEAT_INTERVAL = 30  # seconds
HEARTBEAT_TIMEOUT = 10  # seconds


class ConnectionManager:
    """
    Manages WebSocket connections for live meeting sessions.
    
    Handles connection lifecycle, heartbeat monitoring, and message broadcasting.
    """

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.heartbeat_tasks: Dict[str, asyncio.Task] = {}
        self.last_pong: Dict[str, datetime] = {}

    async def connect(self, session_token: str, websocket: WebSocket) -> None:
        """
        Accept and register a new WebSocket connection.
        
        Args:
            session_token: Unique session identifier
            websocket: WebSocket connection instance
        """
        await websocket.accept()
        self.active_connections[session_token] = websocket
        self.last_pong[session_token] = datetime.utcnow()
        
        # Start heartbeat monitoring
        task = asyncio.create_task(self._heartbeat_monitor(session_token))
        self.heartbeat_tasks[session_token] = task
        
        logger.info(f"WebSocket connected: {session_token}")

    def disconnect(self, session_token: str) -> None:
        """
        Disconnect and cleanup a WebSocket connection.
        
        Args:
            session_token: Session identifier to disconnect
        """
        if session_token in self.active_connections:
            del self.active_connections[session_token]
        
        if session_token in self.last_pong:
            del self.last_pong[session_token]
        
        # Cancel heartbeat task
        if session_token in self.heartbeat_tasks:
            self.heartbeat_tasks[session_token].cancel()
            del self.heartbeat_tasks[session_token]
        
        logger.info(f"WebSocket disconnected: {session_token}")

    async def send_message(self, session_token: str, message: dict) -> bool:
        """
        Send a JSON message to a specific connection.
        
        Args:
            session_token: Target session identifier
            message: Dictionary to send as JSON
            
        Returns:
            True if message sent successfully, False otherwise
        """
        if session_token not in self.active_connections:
            return False
        
        try:
            await self.active_connections[session_token].send_json(message)
            return True
        except Exception as e:
            logger.error(f"Error sending message to {session_token}: {str(e)}")
            return False

    async def _heartbeat_monitor(self, session_token: str) -> None:
        """
        Monitor connection health with ping/pong heartbeat.
        
        Sends ping messages every HEARTBEAT_INTERVAL seconds and checks
        for pong responses. Closes connection if no response within timeout.
        
        Args:
            session_token: Session to monitor
        """
        try:
            while session_token in self.active_connections:
                await asyncio.sleep(HEARTBEAT_INTERVAL)
                
                # Send ping
                success = await self.send_message(session_token, {
                    "type": "ping",
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                if not success:
                    logger.warning(f"Failed to send ping to {session_token}")
                    break
                
                # Wait for pong response
                await asyncio.sleep(HEARTBEAT_TIMEOUT)
                
                # Check if pong was received
                last_pong_time = self.last_pong.get(session_token)
                if last_pong_time:
                    time_since_pong = (datetime.utcnow() - last_pong_time).total_seconds()
                    if time_since_pong > (HEARTBEAT_INTERVAL + HEARTBEAT_TIMEOUT):
                        logger.warning(
                            f"No pong received from {session_token} "
                            f"for {time_since_pong:.1f}s, closing connection"
                        )
                        await self._close_stale_connection(session_token)
                        break
        except asyncio.CancelledError:
            logger.info(f"Heartbeat monitor cancelled for {session_token}")
        except Exception as e:
            logger.error(f"Heartbeat monitor error for {session_token}: {str(e)}")

    async def _close_stale_connection(self, session_token: str) -> None:
        """
        Close a stale connection that failed heartbeat check.
        
        Args:
            session_token: Session to close
        """
        if session_token in self.active_connections:
            try:
                await self.active_connections[session_token].close(
                    code=status.WS_1008_POLICY_VIOLATION,
                    reason="Heartbeat timeout"
                )
            except Exception as e:
                logger.error(f"Error closing stale connection {session_token}: {str(e)}")
            finally:
                self.disconnect(session_token)

    def update_pong(self, session_token: str) -> None:
        """
        Update last pong timestamp for a session.
        
        Args:
            session_token: Session that sent pong
        """
        self.last_pong[session_token] = datetime.utcnow()


# Global connection manager instance
manager = ConnectionManager()


async def authenticate_websocket(token: str, db: Session) -> Optional[User]:
    """
    Authenticate WebSocket connection using JWT token.
    
    Args:
        token: JWT token from query parameter
        db: Database session
        
    Returns:
        User object if authentication successful, None otherwise
    """
    try:
        payload = verify_token(token)
        if not payload:
            logger.warning("Invalid token provided")
            return None
        
        user_id = payload.get("user_id")
        if not user_id:
            logger.warning("Token missing user_id claim")
            return None
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.warning(f"User {user_id} not found")
            return None
        
        return user
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        return None


async def validate_session(
    session_token: str,
    user: User,
    db: Session
) -> Optional[LiveSession]:
    """
    Validate that session exists and belongs to the authenticated user.
    
    Args:
        session_token: Session token to validate
        user: Authenticated user
        db: Database session
        
    Returns:
        LiveSession object if valid, None otherwise
    """
    try:
        live_session = db.query(LiveSession).filter(
            LiveSession.session_token == session_token
        ).first()
        
        if not live_session:
            logger.warning(f"Session {session_token} not found")
            return None
        
        # Verify session belongs to user
        if live_session.meeting.user_id != user.id:
            logger.warning(
                f"User {user.id} attempted to access session "
                f"belonging to user {live_session.meeting.user_id}"
            )
            return None
        
        # Check session is active
        if live_session.status not in ["ACTIVE", "PAUSED"]:
            logger.warning(f"Session {session_token} is not active (status: {live_session.status})")
            return None
        
        return live_session
    except Exception as e:
        logger.error(f"Session validation error: {str(e)}")
        return None


@router.websocket("/ws/live/{session_token}")
async def websocket_live_endpoint(
    websocket: WebSocket,
    session_token: str,
    token: str = Query(..., description="JWT authentication token")
):
    """
    WebSocket endpoint for live audio streaming and real-time transcription.
    
    This endpoint handles:
    - JWT authentication via query parameter
    - Session validation and authorization
    - Audio chunk reception and processing
    - Transcript segment broadcasting
    - Control messages (pause, resume, end)
    - Ping/pong heartbeat mechanism
    
    Args:
        websocket: WebSocket connection
        session_token: Unique session identifier
        token: JWT authentication token (query parameter)
        
    Message Protocol:
        Client -> Server:
            - Binary audio data (WebM chunks from MediaRecorder)
            - {"type": "control", "action": "pause|resume|end"}
            - {"type": "pong", "timestamp": "..."}
        
        Server -> Client:
            - {"type": "transcript", "data": {...}}
            - {"type": "status", "status": "...", "message": "..."}
            - {"type": "ping", "timestamp": "..."}
            - {"type": "error", "message": "..."}
    """
    db = next(get_db())
    audio_processor = LiveAudioProcessor(db)
    
    try:
        # Authenticate user
        user = await authenticate_websocket(token, db)
        if not user:
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Authentication failed"
            )
            logger.warning(f"Authentication failed for session {session_token}")
            return
        
        # Validate session
        live_session = await validate_session(session_token, user, db)
        if not live_session:
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Invalid or unauthorized session"
            )
            logger.warning(
                f"Session validation failed for {session_token} "
                f"(user: {user.id})"
            )
            return
        
        # Accept connection
        await manager.connect(session_token, websocket)
        
        # Send connection confirmation
        await manager.send_message(session_token, {
            "type": "connection_established",
            "message": "Connected to live meeting",
            "session_token": session_token,
            "meeting_id": live_session.meeting_id,
            "user_id": user.id
        })
        
        logger.info(
            f"WebSocket connection established: session={session_token}, "
            f"user={user.id}, meeting={live_session.meeting_id}"
        )
        
        # Message handling loop
        while True:
            try:
                # Receive message (can be bytes, text, or JSON)
                message = await websocket.receive()
                
                # Handle binary audio data
                if "bytes" in message:
                    audio_data = message["bytes"]
                    
                    # Store audio chunk
                    audio_processor.store_audio_chunk(session_token, audio_data)
                    
                    chunk_count = audio_processor.get_chunk_count(session_token)
                    
                    logger.info(
                        f"Audio chunk stored for session {session_token}: "
                        f"{len(audio_data)} bytes (total chunks: {chunk_count})"
                    )
                    
                    # Send acknowledgment
                    await manager.send_message(session_token, {
                        "type": "status",
                        "status": "stored",
                        "message": f"Audio chunk {chunk_count} stored ({len(audio_data)} bytes)"
                    })
                    continue
                
                # Handle text/JSON messages
                elif "text" in message:
                    try:
                        json_data = json.loads(message["text"])
                        
                        message_type = json_data.get("type")
                        
                        if message_type == "pong":
                            # Update heartbeat timestamp
                            manager.update_pong(session_token)
                            logger.debug(f"Pong received from {session_token}")
                        
                        elif message_type == "control":
                            action = json_data.get("action")
                            logger.info(f"Control message received: {action} from {session_token}")
                            await manager.send_message(session_token, {
                                "type": "status",
                                "status": "acknowledged",
                                "message": f"Control action '{action}' received"
                            })
                        
                        else:
                            logger.warning(f"Unknown message type: {message_type}")
                            await manager.send_message(session_token, {
                                "type": "error",
                                "message": f"Unknown message type: {message_type}"
                            })
                    
                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid JSON received from {session_token}: {str(e)}")
                        await manager.send_message(session_token, {
                            "type": "error",
                            "message": "Invalid JSON format"
                        })
                
                # Handle disconnect
                else:
                    logger.info(f"WebSocket disconnect message received: {session_token}")
                    break
            
            except WebSocketDisconnect:
                logger.info(f"Client disconnected in main loop: {session_token}")
                break
            except Exception as e:
                logger.error(f"Unexpected error in message loop for {session_token}: {str(e)}", exc_info=True)
                break
    
    except WebSocketDisconnect:
        logger.info(f"Client disconnected: {session_token}")
        manager.disconnect(session_token)
    
    except Exception as e:
        logger.error(f"WebSocket error for {session_token}: {str(e)}")
        manager.disconnect(session_token)
        try:
            await websocket.close(
                code=status.WS_1011_INTERNAL_ERROR,
                reason="Internal server error"
            )
        except Exception:
            pass
    
    finally:
        db.close()
        manager.disconnect(session_token)
