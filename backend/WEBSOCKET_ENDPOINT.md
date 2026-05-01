# WebSocket Endpoint Documentation

## Overview

The WebSocket endpoint provides real-time bidirectional communication for live meeting audio streaming and transcription.

## Endpoint

```
ws://localhost:8000/ws/live/{session_token}?token={jwt_token}
```

### Parameters

- **session_token** (path parameter): Unique session identifier from the live session
- **token** (query parameter): JWT authentication token

## Authentication

The endpoint requires JWT authentication via query parameter. The token must contain:
- `user_id`: User's database ID
- `sub`: User's email address

The user must own the meeting associated with the session token.

## Connection Lifecycle

### 1. Connection Establishment

When a client connects successfully, the server sends:

```json
{
  "type": "connection_established",
  "message": "Connected to live meeting",
  "session_token": "abc123...",
  "meeting_id": 42,
  "user_id": 1
}
```

### 2. Heartbeat Mechanism

The server sends ping messages every 30 seconds:

```json
{
  "type": "ping",
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

Clients must respond with pong within 10 seconds:

```json
{
  "type": "pong",
  "timestamp": "2024-01-15T10:30:00.100Z"
}
```

If no pong is received, the connection is closed after 40 seconds (30s interval + 10s timeout).

### 3. Disconnection

Connections are closed when:
- Client disconnects gracefully
- Heartbeat timeout (no pong response)
- Authentication fails
- Session validation fails
- Internal server error

## Message Protocol

### Client → Server Messages

#### Audio Chunk

```json
{
  "type": "audio_chunk",
  "data": "<base64_encoded_audio>",
  "metadata": {
    "timestamp": "2024-01-15T10:30:00.000Z",
    "sequence": 42,
    "language_hint": "en"
  }
}
```

#### Control Message

```json
{
  "type": "control",
  "action": "pause|resume|end"
}
```

#### Pong Response

```json
{
  "type": "pong",
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

### Server → Client Messages

#### Transcript Segment

```json
{
  "type": "transcript",
  "data": {
    "id": 123,
    "speaker": "Speaker 1",
    "text": "Hello world",
    "start_time": 10.5,
    "end_time": 12.3,
    "confidence": 0.95
  }
}
```

#### Status Update

```json
{
  "type": "status",
  "status": "processing|acknowledged|completed",
  "message": "Optional status message"
}
```

#### Error Message

```json
{
  "type": "error",
  "message": "Error description"
}
```

#### Ping Message

```json
{
  "type": "ping",
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

## Error Handling

### Authentication Errors

- **Code**: 1008 (Policy Violation)
- **Reason**: "Authentication failed"
- **Cause**: Invalid or missing JWT token

### Authorization Errors

- **Code**: 1008 (Policy Violation)
- **Reason**: "Invalid or unauthorized session"
- **Cause**: Session doesn't exist, doesn't belong to user, or is not active

### Heartbeat Timeout

- **Code**: 1008 (Policy Violation)
- **Reason**: "Heartbeat timeout"
- **Cause**: No pong response received within timeout period

### Internal Errors

- **Code**: 1011 (Internal Error)
- **Reason**: "Internal server error"
- **Cause**: Unexpected server error during message processing

## Testing

### Prerequisites

1. Backend server running on `http://localhost:8000`
2. Test user created with email `test@example.com`
3. Virtual environment activated

### Run Test Script

```bash
cd backend
python test_websocket_connection.py
```

The test script will:
1. Create a test meeting and live session
2. Connect to the WebSocket endpoint
3. Test authentication
4. Test heartbeat mechanism (ping/pong)
5. Test control messages
6. Test audio chunk messages
7. Clean up test data

### Expected Output

```
================================================================================
WebSocket Connection Test
================================================================================

This test will:
  1. Create a test meeting and live session
  2. Connect to the WebSocket endpoint
  3. Test authentication
  4. Test heartbeat mechanism (ping/pong)
  5. Test control messages
  6. Test audio chunk messages

Make sure the backend server is running on http://localhost:8000
================================================================================

✓ Found test user: test@example.com (ID: 1)
✓ Created test meeting (ID: 42)
✓ Created live session (Token: abc123...)
✓ Generated JWT token

🔌 Connecting to WebSocket: ws://localhost:8000/ws/live/abc123...
✓ WebSocket connection established
✓ Received: connection_established - Connected to live meeting

💓 Testing heartbeat mechanism...
✓ Received ping at 2024-01-15T10:30:00.000Z
✓ Sent pong response

📤 Testing control message...
✓ Sent control message: {'type': 'control', 'action': 'pause'}
✓ Received: status - Control action 'pause' received

🎵 Testing audio chunk message...
✓ Sent audio chunk message
✓ Received: status - Audio chunk received

✅ All WebSocket tests passed!

🧹 Cleaned up test data
```

## Implementation Status

### ✅ Completed (Task 2.1)

- WebSocket endpoint `/ws/live/{session_token}` created
- JWT authentication via query parameter
- Connection lifecycle management (connect, disconnect, error handling)
- Ping/pong heartbeat mechanism (30-second interval)
- Endpoint registered in main.py
- Test script for connection verification

### 🔄 Pending (Future Tasks)

- Audio chunk processing (Task 7.1)
- Transcript segment broadcasting (Task 7.3)
- Control message handling (Task 7.5)
- Integration with AudioBuffer service (Task 3.1)
- Integration with WhisperService (Task 4.1)
- Integration with SpeakerDiarizationService (Task 5.1)

## Security Considerations

1. **Authentication**: JWT token required for all connections
2. **Authorization**: Users can only access their own sessions
3. **Session Validation**: Sessions must be ACTIVE or PAUSED
4. **Connection Monitoring**: Heartbeat mechanism detects stale connections
5. **Error Handling**: Graceful error handling with appropriate close codes

## Performance Considerations

1. **Async Processing**: All operations are asynchronous
2. **Connection Management**: Efficient connection tracking with dictionaries
3. **Heartbeat Tasks**: Separate async task per connection
4. **Resource Cleanup**: Proper cleanup on disconnect
5. **Database Sessions**: Database connections properly closed

## Next Steps

1. Implement audio chunk processing (Task 7.1)
2. Implement transcript broadcasting (Task 7.3)
3. Implement control message handling (Task 7.5)
4. Add property-based tests (Task 2.2)
5. Add session state preservation tests (Task 2.4)
