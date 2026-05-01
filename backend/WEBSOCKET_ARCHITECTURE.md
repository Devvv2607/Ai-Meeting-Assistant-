# WebSocket Architecture - Task 2.1 Implementation

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Client (Browser/App)                        │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐            │
│  │ Audio Capture│  │   WebSocket  │  │  UI Controls │            │
│  │   Service    │──│    Client    │──│   (Pause/    │            │
│  │              │  │              │  │   Resume)    │            │
│  └──────────────┘  └──────────────┘  └──────────────┘            │
│                           │                                         │
└───────────────────────────┼─────────────────────────────────────────┘
                            │
                            │ WebSocket Connection
                            │ ws://localhost:8000/ws/live/{token}?token={jwt}
                            │
┌───────────────────────────┼─────────────────────────────────────────┐
│                           ▼                                         │
│                  FastAPI Backend Server                             │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │              WebSocket Endpoint Handler                      │  │
│  │         /ws/live/{session_token}?token={jwt}                │  │
│  │                                                              │  │
│  │  1. Authenticate JWT Token                                  │  │
│  │  2. Validate Session & Authorization                        │  │
│  │  3. Accept Connection                                       │  │
│  │  4. Start Heartbeat Monitor                                 │  │
│  │  5. Handle Messages                                         │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                           │                                         │
│  ┌────────────────────────┼────────────────────────────────────┐  │
│  │         ConnectionManager                                   │  │
│  │                                                             │  │
│  │  • active_connections: Dict[token, WebSocket]              │  │
│  │  • heartbeat_tasks: Dict[token, Task]                      │  │
│  │  • last_pong: Dict[token, datetime]                        │  │
│  │                                                             │  │
│  │  Methods:                                                   │  │
│  │  - connect(token, websocket)                               │  │
│  │  - disconnect(token)                                       │  │
│  │  - send_message(token, message)                            │  │
│  │  - _heartbeat_monitor(token)                               │  │
│  │  - update_pong(token)                                      │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                           │                                         │
│  ┌────────────────────────┼────────────────────────────────────┐  │
│  │         Authentication & Authorization                      │  │
│  │                                                             │  │
│  │  authenticate_websocket(token, db)                         │  │
│  │  ├─ Verify JWT token                                       │  │
│  │  ├─ Extract user_id                                        │  │
│  │  └─ Query User from database                               │  │
│  │                                                             │  │
│  │  validate_session(session_token, user, db)                 │  │
│  │  ├─ Query LiveSession from database                        │  │
│  │  ├─ Verify session belongs to user                         │  │
│  │  └─ Check session status (ACTIVE/PAUSED)                   │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                           │                                         │
│  ┌────────────────────────┼────────────────────────────────────┐  │
│  │              Database Models                                │  │
│  │                                                             │  │
│  │  ┌──────────┐  ┌──────────────┐  ┌──────────┐            │  │
│  │  │   User   │  │ LiveSession  │  │ Meeting  │            │  │
│  │  │          │  │              │  │          │            │  │
│  │  │ id       │  │ id           │  │ id       │            │  │
│  │  │ email    │  │ meeting_id   │  │ user_id  │            │  │
│  │  │ password │  │ session_token│  │ title    │            │  │
│  │  └──────────┘  │ status       │  │ status   │            │  │
│  │                │ started_at   │  └──────────┘            │  │
│  │                │ ended_at     │                           │  │
│  │                └──────────────┘                           │  │
│  └─────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

## Message Flow

### 1. Connection Establishment

```
Client                          Server
  │                               │
  │──── WebSocket Connect ───────▶│
  │     (with JWT token)          │
  │                               │
  │                               ├─ Authenticate JWT
  │                               ├─ Validate Session
  │                               ├─ Accept Connection
  │                               └─ Start Heartbeat
  │                               │
  │◀─── connection_established ───│
  │                               │
```

### 2. Heartbeat Mechanism

```
Client                          Server
  │                               │
  │                               ├─ Wait 30 seconds
  │                               │
  │◀────────── ping ──────────────│
  │                               │
  │────────── pong ───────────────▶│
  │                               ├─ Update last_pong
  │                               │
  │                               ├─ Wait 30 seconds
  │                               │
  │◀────────── ping ──────────────│
  │                               │
  │  (no response)                │
  │                               ├─ Wait 10 seconds
  │                               ├─ Check last_pong
  │                               ├─ Timeout detected
  │                               │
  │◀──── Connection Closed ───────│
  │     (code: 1008)              │
```

### 3. Audio Chunk Processing (Future)

```
Client                          Server
  │                               │
  │──── audio_chunk ──────────────▶│
  │     (base64 + metadata)       │
  │                               ├─ Buffer chunk
  │                               ├─ Create segment
  │                               ├─ Transcribe
  │                               └─ Diarize
  │                               │
  │◀──── transcript ──────────────│
  │     (speaker + text)          │
```

### 4. Control Messages (Future)

```
Client                          Server
  │                               │
  │──── control: pause ───────────▶│
  │                               ├─ Update session status
  │                               ├─ Stop processing
  │                               │
  │◀──── status: acknowledged ────│
  │                               │
  │──── control: resume ──────────▶│
  │                               ├─ Update session status
  │                               ├─ Resume processing
  │                               │
  │◀──── status: acknowledged ────│
```

## Component Responsibilities

### ConnectionManager
- **Purpose**: Manage WebSocket connection lifecycle
- **Responsibilities**:
  - Accept and register connections
  - Track active connections by session_token
  - Monitor connection health with heartbeat
  - Send messages to specific connections
  - Clean up on disconnect
- **State**:
  - `active_connections`: Maps session_token to WebSocket
  - `heartbeat_tasks`: Maps session_token to async Task
  - `last_pong`: Maps session_token to last pong timestamp

### Authentication Layer
- **Purpose**: Verify user identity and authorization
- **Functions**:
  - `authenticate_websocket()`: Validate JWT token
  - `validate_session()`: Verify session ownership and status
- **Security**:
  - JWT token validation
  - User existence check
  - Session ownership verification
  - Session status validation

### WebSocket Endpoint
- **Purpose**: Handle WebSocket connections and messages
- **Responsibilities**:
  - Authenticate incoming connections
  - Validate session authorization
  - Accept WebSocket connection
  - Handle message protocol
  - Manage connection lifecycle
  - Handle errors gracefully

## Heartbeat Mechanism Details

### Configuration
```python
HEARTBEAT_INTERVAL = 30  # seconds between pings
HEARTBEAT_TIMEOUT = 10   # seconds to wait for pong
```

### Process
1. **Start**: When connection is accepted
2. **Loop**:
   - Wait `HEARTBEAT_INTERVAL` seconds
   - Send ping message with timestamp
   - Wait `HEARTBEAT_TIMEOUT` seconds
   - Check if pong was received
   - If no pong: close connection
   - If pong received: continue loop
3. **Stop**: When connection closes or task is cancelled

### Timeout Detection
```python
time_since_pong = (now - last_pong_time).total_seconds()
if time_since_pong > (HEARTBEAT_INTERVAL + HEARTBEAT_TIMEOUT):
    # Connection is stale, close it
    close_connection()
```

## Error Handling

### Authentication Failures
- **Trigger**: Invalid JWT token, missing user_id, user not found
- **Action**: Close connection with code 1008 (Policy Violation)
- **Reason**: "Authentication failed"

### Authorization Failures
- **Trigger**: Session not found, wrong user, inactive session
- **Action**: Close connection with code 1008 (Policy Violation)
- **Reason**: "Invalid or unauthorized session"

### Heartbeat Timeouts
- **Trigger**: No pong response within timeout period
- **Action**: Close connection with code 1008 (Policy Violation)
- **Reason**: "Heartbeat timeout"

### Internal Errors
- **Trigger**: Unexpected exceptions during message processing
- **Action**: Close connection with code 1011 (Internal Error)
- **Reason**: "Internal server error"

## Security Features

### 1. Authentication
- JWT token required in query parameter
- Token must contain valid user_id and email
- User must exist in database

### 2. Authorization
- Session must exist in database
- Session must belong to authenticated user
- Session must be in ACTIVE or PAUSED status

### 3. Connection Monitoring
- Heartbeat mechanism detects stale connections
- Automatic cleanup of dead connections
- Prevents resource exhaustion

### 4. Resource Management
- Proper cleanup on disconnect
- Database sessions properly closed
- Async tasks cancelled on disconnect

## Performance Characteristics

### Scalability
- **Concurrent Connections**: Supports multiple simultaneous connections
- **Memory Usage**: O(n) where n = number of active connections
- **CPU Usage**: Minimal, mostly I/O bound
- **Database**: One query per connection establishment

### Efficiency
- **Connection Lookup**: O(1) dictionary lookup
- **Message Sending**: O(1) per message
- **Heartbeat**: One async task per connection
- **Cleanup**: O(1) per disconnect

### Resource Usage
- **Per Connection**:
  - 1 WebSocket object
  - 1 async Task (heartbeat)
  - 1 datetime object (last_pong)
  - Minimal memory overhead

## Testing Strategy

### Unit Tests
- Test ConnectionManager methods
- Test authentication function
- Test session validation function
- Test heartbeat mechanism

### Integration Tests
- Test full connection flow
- Test authentication failures
- Test authorization failures
- Test heartbeat timeout
- Test message protocol

### Manual Testing
- Use test_websocket_connection.py script
- Verify connection establishment
- Verify heartbeat mechanism
- Verify message handling
- Verify error handling

## Future Enhancements

### Task 7.1: Audio Chunk Processing
- Receive audio chunks from client
- Buffer chunks into segments
- Pass to transcription service

### Task 7.3: Transcript Broadcasting
- Receive transcribed segments
- Broadcast to connected clients
- Handle duplicate detection

### Task 7.5: Control Message Handling
- Implement pause action
- Implement resume action
- Implement end action
- Update session status

### Optional: Multi-Instance Support
- Use Redis for connection state
- Support horizontal scaling
- Implement connection migration

## Conclusion

The WebSocket endpoint implementation provides a robust foundation for real-time communication in the live meeting system. It includes:

✅ Secure authentication and authorization  
✅ Reliable connection monitoring  
✅ Comprehensive error handling  
✅ Efficient resource management  
✅ Extensible message protocol  
✅ Complete documentation and testing

The implementation is ready for integration with audio processing, transcription, and other live meeting features.
