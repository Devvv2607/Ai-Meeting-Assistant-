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
from app.models.transcript import Transcript
from app.models.meeting import Meeting
from app.services.live_audio_processor import LiveAudioProcessor
from app.services.live_audio_recorder import live_audio_recorder

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])

# Heartbeat configuration
HEARTBEAT_INTERVAL = 30  # seconds
HEARTBEAT_TIMEOUT = 10  # seconds

# Approximate duration of each audio segment the frontend streams (seconds).
# Used only to assign monotonic start/end timestamps to live transcript rows.
SEGMENT_SECONDS = 4.0

# Common single-word/filler hallucinations Whisper emits on silent segments.
_NOISE_TEXT = {
    "you", "thank you.", "thank you", "thanks for watching!", "thanks for watching.",
    ".", "bye.", "bye", "okay.", "ok.", "so.", "uh.", "um.",
}


def _is_noise(text: str) -> bool:
    """Filter out empty / silence-hallucination transcripts."""
    t = text.strip().lower()
    return len(t) < 2 or t in _NOISE_TEXT


def _transcribe_webm_segment(whisper_service, data: bytes) -> tuple:
    """Write a standalone WebM segment to a temp file and transcribe via Groq.

    Returns (text, detected_language). Defined at module scope (not per-message)
    and intended to run inside ``asyncio.to_thread`` so the blocking Groq call
    does not stall the event loop.
    """
    import tempfile
    import os as _os

    tmp = tempfile.NamedTemporaryFile(suffix=".webm", delete=False)
    try:
        tmp.write(data)
        tmp.close()
        segs = whisper_service.transcribe(tmp.name)
        if not segs:
            return "", None
        seg = segs[0]
        return seg.get("text", ""), seg.get("language")
    finally:
        try:
            _os.remove(tmp.name)
        except Exception:
            pass


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
    # Bound before the try so the finally can finalize the recording even if
    # authentication/validation fails or the connection ends abnormally.
    meeting_id = None

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
        
        # Cache the meeting id once (avoids a DB re-query per segment after the
        # ORM object is expired by commit()).
        meeting_id = live_session.meeting_id

        # Running audio-time cursor (seconds) used as a fallback when the client
        # does not supply real per-segment timing. Advances for EVERY received
        # segment (including filtered-silence ones) so timestamps track real
        # audio position rather than collapsing.
        audio_offset = 0.0
        # Timing supplied by the client for the NEXT binary segment, if any.
        pending_time: Optional[tuple] = None

        # Message handling loop
        while True:
            try:
                # Receive message (can be bytes, text, or JSON)
                message = await websocket.receive()

                # Handle binary audio data: each message is a standalone WebM
                # segment from the browser. Transcribe it via Groq (off the event
                # loop), persist it, and broadcast the transcript to the client.
                if "bytes" in message:
                    audio_data = message["bytes"]

                    # Persist the raw audio (decode→append PCM) for end-of-meeting
                    # diarization. Runs in a worker thread so the blocking ffmpeg
                    # decode does not stall the event loop. EVERY segment is
                    # captured — including silence/noise ones filtered from the
                    # transcript — so the saved file's duration matches the
                    # real session length.
                    try:
                        await asyncio.to_thread(
                            live_audio_recorder.append_segment, meeting_id, audio_data
                        )
                    except Exception as e:
                        logger.warning(f"Live audio capture failed for {session_token}: {e}")

                    # Determine this segment's start/end. Prefer the real timing
                    # the client measured; fall back to the running offset.
                    if pending_time is not None:
                        start_time, end_time = pending_time
                        pending_time = None
                        audio_offset = end_time
                    else:
                        start_time = audio_offset
                        end_time = audio_offset + SEGMENT_SECONDS
                        audio_offset = end_time

                    # Run the blocking Groq call in a worker thread so heartbeats
                    # and other sessions are not blocked.
                    detected_language = None
                    try:
                        text, detected_language = await asyncio.to_thread(
                            _transcribe_webm_segment,
                            audio_processor.whisper_service,
                            audio_data,
                        )
                    except Exception as e:
                        logger.error(f"Live transcription error for {session_token}: {e}")
                        text = ""

                    text = (text or "").strip()
                    if not text or _is_noise(text):
                        continue

                    segment_language = detected_language or "unknown"

                    # Persist the segment so the meeting detail page shows it too.
                    try:
                        transcript_row = Transcript(
                            meeting_id=meeting_id,
                            text=text,
                            speaker="Speaker 1",
                            language=segment_language,
                            start_time=start_time,
                            end_time=end_time,
                            confidence=0.9,
                            is_final=True,
                        )
                        db.add(transcript_row)
                        db.commit()
                    except Exception as e:
                        logger.error(f"Failed to persist live transcript for {session_token}: {e}")
                        db.rollback()

                    logger.info(
                        f"Live transcript [{session_token}] @{start_time:.1f}s: "
                        f"{len(text)} chars"
                    )

                    # Broadcast to the client (flat shape the frontend expects).
                    await manager.send_message(session_token, {
                        "type": "transcript",
                        "text": text,
                        "speaker": "Speaker 1",
                        "language": segment_language,
                        "timestamp": datetime.utcnow().isoformat(),
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

                        elif message_type == "segment":
                            # Real timing the client measured for the NEXT binary
                            # segment it is about to send.
                            try:
                                pending_time = (
                                    float(json_data.get("start", 0.0)),
                                    float(json_data.get("end", 0.0)),
                                )
                            except (TypeError, ValueError):
                                pending_time = None

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
        # Finalize the captured audio into ONE decodable WAV and store its path on
        # the meeting so the later diarization task can find it. Runs on
        # meeting-end AND on disconnect/error so an abnormal end never loses the file.
        if meeting_id is not None:
            try:
                wav_path = await asyncio.to_thread(live_audio_recorder.finalize, meeting_id)
                if wav_path:
                    try:
                        db.rollback()  # clear any failed transaction from the loop
                    except Exception:
                        pass
                    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
                    if meeting:
                        meeting.audio_url = wav_path
                        db.commit()
                        logger.info(
                            f"Stored live audio path on meeting {meeting_id}: {wav_path}"
                        )
            except Exception as e:
                logger.error(
                    f"Failed to finalize/persist live audio for meeting {meeting_id}: {e}"
                )
                try:
                    live_audio_recorder.discard(meeting_id)
                except Exception:
                    pass

        db.close()
        manager.disconnect(session_token)
