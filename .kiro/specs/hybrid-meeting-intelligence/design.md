# Hybrid Meeting Intelligence System - Design

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (Next.js)                        │
├─────────────────────────────────────────────────────────────────┤
│  Dashboard │ Upload │ Live Meeting │ Meeting Details │ Settings  │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTP/WebSocket
┌────────────────────────▼────────────────────────────────────────┐
│                    API Gateway (FastAPI)                         │
├─────────────────────────────────────────────────────────────────┤
│  Auth Routes │ Meeting Routes │ WebSocket Handler │ Export Routes│
└────────────────────────┬────────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
┌───────▼────────┐ ┌────▼──────────┐ ┌──▼──────────────┐
│  Services      │ │  Background   │ │  External APIs  │
├────────────────┤ ├───────────────┤ ├─────────────────┤
│ Transcription  │ │ Celery Tasks  │ │ Groq LLM        │
│ Diarization    │ │ Redis Queue   │ │ Whisper API     │
│ Embedding      │ │ Worker Pool   │ │ HuggingFace     │
│ Summary        │ │               │ │                 │
└────────────────┘ └───────────────┘ └─────────────────┘
        │
┌───────▼────────────────────────────────────────────┐
│           Database (PostgreSQL)                     │
├────────────────────────────────────────────────────┤
│ Users │ Meetings │ Transcripts │ Speakers │ Insights│
│ Embeddings (pgvector) │ LiveSessions │ ChatMessages│
└────────────────────────────────────────────────────┘
```

## Database Schema

### Users Table
```sql
CREATE TABLE users (
  id SERIAL PRIMARY KEY,
  email VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  full_name VARCHAR(255),
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```

### Meetings Table
```sql
CREATE TABLE meetings (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id),
  title VARCHAR(255) NOT NULL,
  description TEXT,
  meeting_type VARCHAR(20), -- 'upload' or 'live'
  status VARCHAR(20), -- 'pending', 'processing', 'completed', 'failed'
  duration FLOAT, -- in seconds
  language VARCHAR(10), -- detected language code
  audio_url VARCHAR(500),
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### Transcripts Table
```sql
CREATE TABLE transcripts (
  id SERIAL PRIMARY KEY,
  meeting_id INTEGER NOT NULL REFERENCES meetings(id),
  speaker_id INTEGER REFERENCES speakers(id),
  speaker_name VARCHAR(255),
  text TEXT NOT NULL,
  start_time FLOAT, -- in seconds
  end_time FLOAT,
  language VARCHAR(10), -- language of this segment
  confidence FLOAT, -- transcription confidence
  created_at TIMESTAMP DEFAULT NOW(),
  FOREIGN KEY (meeting_id) REFERENCES meetings(id)
);

CREATE INDEX idx_transcripts_meeting ON transcripts(meeting_id);
CREATE INDEX idx_transcripts_speaker ON transcripts(speaker_id);
```

### Speakers Table
```sql
CREATE TABLE speakers (
  id SERIAL PRIMARY KEY,
  meeting_id INTEGER NOT NULL REFERENCES meetings(id),
  speaker_number INTEGER, -- Speaker 1, Speaker 2, etc.
  speaker_name VARCHAR(255), -- User-provided name
  talk_time FLOAT, -- total talk time in seconds
  word_count INTEGER,
  created_at TIMESTAMP DEFAULT NOW(),
  FOREIGN KEY (meeting_id) REFERENCES meetings(id)
);
```

### Insights Table
```sql
CREATE TABLE insights (
  id SERIAL PRIMARY KEY,
  meeting_id INTEGER NOT NULL UNIQUE REFERENCES meetings(id),
  summary TEXT,
  key_points TEXT[], -- JSON array
  action_items JSONB, -- JSON with task, owner, deadline
  decisions TEXT[],
  risks TEXT[],
  next_steps TEXT[],
  generated_at TIMESTAMP DEFAULT NOW(),
  FOREIGN KEY (meeting_id) REFERENCES meetings(id)
);
```

### Embeddings Table (pgvector)
```sql
CREATE TABLE embeddings (
  id SERIAL PRIMARY KEY,
  transcript_id INTEGER NOT NULL UNIQUE REFERENCES transcripts(id),
  embedding vector(384), -- all-MiniLM-L6-v2 produces 384-dim vectors
  created_at TIMESTAMP DEFAULT NOW(),
  FOREIGN KEY (transcript_id) REFERENCES transcripts(id)
);

CREATE INDEX idx_embeddings_vector ON embeddings USING ivfflat (embedding vector_cosine_ops);
```

### Live Sessions Table
```sql
CREATE TABLE live_sessions (
  id SERIAL PRIMARY KEY,
  meeting_id INTEGER NOT NULL UNIQUE REFERENCES meetings(id),
  session_token VARCHAR(255) UNIQUE,
  started_at TIMESTAMP DEFAULT NOW(),
  ended_at TIMESTAMP,
  status VARCHAR(20), -- 'active', 'ended', 'error'
  FOREIGN KEY (meeting_id) REFERENCES meetings(id)
);
```

## Backend Architecture

### Folder Structure
```
backend/
├── app/
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── meeting.py
│   │   ├── transcript.py
│   │   ├── speaker.py
│   │   ├── insight.py
│   │   ├── embedding.py
│   │   └── live_session.py
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth_routes.py
│   │   ├── meeting_routes.py
│   │   ├── live_routes.py
│   │   ├── transcript_routes.py
│   │   ├── insight_routes.py
│   │   └── export_routes.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── transcription_service.py
│   │   ├── diarization_service.py
│   │   ├── embedding_service.py
│   │   ├── summary_service.py
│   │   ├── audio_processor_service.py
│   │   ├── live_meeting_service.py
│   │   └── search_service.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── meeting_schema.py
│   │   ├── transcript_schema.py
│   │   └── insight_schema.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── auth_utils.py
│   │   ├── audio_utils.py
│   │   └── websocket_utils.py
│   ├── workers/
│   │   ├── __init__.py
│   │   ├── celery_config.py
│   │   └── tasks.py
│   ├── config.py
│   ├── database.py
│   └── main.py
├── requirements.txt
└── start_server.py
```

### Key Services

#### 1. TranscriptionService
```python
class TranscriptionService:
    def transcribe_chunk(audio_bytes: bytes) -> TranscriptSegment
    def transcribe_file(file_path: str) -> List[TranscriptSegment]
    def detect_language(audio_bytes: bytes) -> str
```

#### 2. DiarizationService
```python
class DiarizationService:
    def diarize_audio(audio_path: str) -> List[SpeakerSegment]
    def merge_with_transcript(transcripts, diarization) -> List[TranscriptWithSpeaker]
    def estimate_speaker_count(diarization) -> int
```

#### 3. EmbeddingService
```python
class EmbeddingService:
    def generate_embedding(text: str) -> np.ndarray
    def search_similar(query: str, meeting_id: int, top_k: int) -> List[SearchResult]
```

#### 4. SummaryService
```python
class SummaryService:
    def generate_insights(transcript: str) -> InsightData
    def extract_action_items(transcript: str) -> List[ActionItem]
```

#### 5. LiveMeetingService
```python
class LiveMeetingService:
    def create_session(meeting_id: int) -> LiveSession
    def process_chunk(session_id: str, audio_chunk: bytes) -> TranscriptSegment
    def end_session(session_id: str) -> Meeting
```

## Frontend Architecture

### Folder Structure
```
frontend/
├── app/
│   ├── layout.tsx
│   ├── page.tsx
│   ├── login/
│   │   └── page.tsx
│   ├── register/
│   │   └── page.tsx
│   ├── dashboard/
│   │   └── page.tsx
│   ├── upload/
│   │   └── page.tsx
│   ├── live-meeting/
│   │   └── page.tsx
│   ├── meeting/
│   │   └── [id]/
│   │       └── page.tsx
│   └── settings/
│       └── page.tsx
├── components/
│   ├── Navigation.tsx
│   ├── Dashboard/
│   │   ├── DashboardHero.tsx
│   │   ├── UploadCard.tsx
│   │   ├── LiveMeetingCard.tsx
│   │   └── RecentMeetings.tsx
│   ├── Upload/
│   │   ├── FileUploader.tsx
│   │   ├── UploadProgress.tsx
│   │   └── ProcessingStatus.tsx
│   ├── LiveMeeting/
│   │   ├── AudioCapture.tsx
│   │   ├── LiveTranscript.tsx
│   │   ├── SpeakerIndicator.tsx
│   │   └── MeetingControls.tsx
│   ├── Meeting/
│   │   ├── TranscriptViewer.tsx
│   │   ├── SummaryPanel.tsx
│   │   ├── InsightsPanel.tsx
│   │   ├── SpeakerAnalytics.tsx
│   │   ├── SearchBar.tsx
│   │   └── ExportOptions.tsx
│   └── Common/
│       ├── LoadingSpinner.tsx
│       ├── ErrorBoundary.tsx
│       └── Toast.tsx
├── services/
│   ├── api.ts
│   ├── websocket.ts
│   ├── audio.ts
│   └── storage.ts
├── hooks/
│   ├── useAuth.ts
│   ├── useWebSocket.ts
│   ├── useAudioCapture.ts
│   └── useMeeting.ts
├── types/
│   ├── index.ts
│   ├── meeting.ts
│   ├── transcript.ts
│   └── api.ts
├── styles/
│   ├── globals.css
│   └── components.css
└── utils/
    ├── format.ts
    ├── validation.ts
    └── constants.ts
```

### Key Components

#### Dashboard
- Hero section with upload/live options
- Recent meetings list
- Statistics (total meetings, hours transcribed)
- Quick actions

#### Upload Page
- File input with drag-and-drop
- File validation
- Upload progress
- Processing status

#### Live Meeting Page
- Audio capture setup
- Real-time transcript display
- Speaker indicator
- Meeting controls (pause, stop, end)
- Live captions

#### Meeting Details Page
- Full transcript with speaker labels
- Summary and insights
- Action items with owners
- Speaker analytics
- Search functionality
- Export options

## WebSocket Protocol

### Live Meeting WebSocket

**Connection**:
```
WS /api/v1/meetings/live/{meeting_id}
Headers: Authorization: Bearer {token}
```

**Client → Server** (Audio Chunk):
```json
{
  "type": "audio_chunk",
  "data": "base64_encoded_audio",
  "timestamp": 1234567890,
  "duration": 3.0
}
```

**Server → Client** (Transcript):
```json
{
  "type": "transcript",
  "segment_id": 1,
  "speaker": "Rahul",
  "speaker_id": 1,
  "text": "Let's begin the meeting",
  "start_time": 15.2,
  "end_time": 18.5,
  "language": "en",
  "confidence": 0.95
}
```

**Server → Client** (Status):
```json
{
  "type": "status",
  "status": "processing",
  "message": "Transcribing audio chunk...",
  "speakers_detected": 2
}
```

**Server → Client** (Error):
```json
{
  "type": "error",
  "error": "Audio processing failed",
  "message": "Invalid audio format"
}
```

## Data Flow Diagrams

### Upload Recording Flow
```
User Upload
    ↓
Validate File
    ↓
Store in S3/Local
    ↓
Queue Transcription Task
    ↓
[Background Worker]
    ├─ Chunk Audio (30s chunks)
    ├─ Transcribe Each Chunk (Whisper)
    ├─ Detect Language
    ├─ Perform Diarization (pyannote)
    ├─ Merge Transcripts + Speakers
    ├─ Store in Database
    ├─ Generate Embeddings
    ├─ Store Embeddings in pgvector
    └─ Generate Summary (Groq)
    ↓
Update Meeting Status
    ↓
Notify Frontend
    ↓
Display Results
```

### Live Meeting Flow
```
User Starts Live Meeting
    ↓
Request getDisplayMedia() Permission
    ↓
User Selects Meeting Tab
    ↓
Create Live Session
    ↓
Start MediaRecorder
    ↓
Every 3 Seconds:
    ├─ Capture Audio Chunk
    ├─ Send via WebSocket
    ├─ Backend Transcribes (Whisper)
    ├─ Backend Diarizes (incremental)
    ├─ Send Transcript via WebSocket
    └─ Frontend Displays Caption
    ↓
User Ends Meeting
    ↓
Finalize Transcript
    ↓
Generate Summary + Insights
    ↓
Store in Database
    ↓
Display Results
```

### Search Flow
```
User Enters Search Query
    ↓
Generate Query Embedding
    ↓
Search pgvector (cosine similarity)
    ↓
Retrieve Top-K Results
    ↓
Fetch Full Transcript Segments
    ↓
Return with Timestamps + Speaker
    ↓
Display Results
```

## API Response Formats

### Meeting Object
```json
{
  "id": 1,
  "title": "Q1 Planning Meeting",
  "description": "Quarterly planning and budget discussion",
  "meeting_type": "live",
  "status": "completed",
  "duration": 3600,
  "language": "en",
  "created_at": "2024-04-24T10:00:00Z",
  "updated_at": "2024-04-24T11:00:00Z",
  "speaker_count": 3,
  "transcript_segments": 150
}
```

### Transcript Segment Object
```json
{
  "id": 1,
  "meeting_id": 1,
  "speaker_id": 1,
  "speaker_name": "Rahul",
  "text": "Let's finalize the budget",
  "start_time": 15.2,
  "end_time": 18.5,
  "language": "en",
  "confidence": 0.95
}
```

### Insight Object
```json
{
  "id": 1,
  "meeting_id": 1,
  "summary": "Team discussed Q1 budget allocation and timeline.",
  "key_points": [
    "Budget increased by 20%",
    "Deadline moved to March 31",
    "New team member joining next week"
  ],
  "action_items": [
    {
      "task": "Finalize budget breakdown",
      "owner": "Rahul",
      "deadline": "2024-04-26"
    }
  ],
  "decisions": [
    "Approved Q1 budget",
    "Hired new developer"
  ],
  "risks": [
    "Tight timeline for implementation"
  ],
  "next_steps": [
    "Send budget to finance",
    "Schedule kickoff meeting"
  ]
}
```

## Security Considerations

1. **Authentication**: JWT tokens with expiration
2. **Authorization**: User can only access their own meetings
3. **WebSocket Security**: Validate token on connection
4. **File Upload**: Validate file type and size
5. **Audio Processing**: Secure temporary file handling
6. **API Rate Limiting**: Prevent abuse
7. **HTTPS/WSS**: Encrypted communication
8. **CORS**: Properly configured

## Performance Optimization

1. **Async Processing**: Use FastAPI async for I/O
2. **Background Tasks**: Celery for heavy processing
3. **Caching**: Redis for frequently accessed data
4. **Database Indexing**: Indexes on meeting_id, user_id
5. **Vector Search**: pgvector with IVFFLAT index
6. **Chunk Processing**: Process audio in 30-second chunks
7. **Connection Pooling**: Database connection pool
8. **CDN**: Serve static assets from CDN

## Deployment Architecture

```
┌─────────────────────────────────────────┐
│         Docker Compose (Local)          │
├─────────────────────────────────────────┤
│ Frontend (Next.js) │ Backend (FastAPI)  │
│ PostgreSQL         │ Redis              │
│ Celery Worker      │ Nginx (Reverse Proxy)
└─────────────────────────────────────────┘
```

## Error Handling Strategy

1. **Validation Errors**: Return 400 with details
2. **Authentication Errors**: Return 401
3. **Authorization Errors**: Return 403
4. **Not Found**: Return 404
5. **Server Errors**: Return 500 with error ID
6. **WebSocket Errors**: Send error message and reconnect
7. **Processing Errors**: Retry with exponential backoff
8. **User Feedback**: Toast notifications for all errors

## Monitoring & Logging

1. **Application Logs**: FastAPI logging
2. **Error Tracking**: Sentry integration
3. **Performance Monitoring**: APM tools
4. **Database Monitoring**: Query performance
5. **WebSocket Monitoring**: Connection health
6. **Audio Processing**: Processing time tracking
7. **User Analytics**: Usage patterns
