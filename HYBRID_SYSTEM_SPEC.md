# Hybrid Meeting Intelligence System - Complete Specification

## Executive Summary

This document outlines the complete upgrade of your AI Meeting Intelligence Platform into a production-grade Hybrid Meeting Intelligence System comparable to Otter.ai, Fireflies.ai, and Fathom.

**Key Capabilities**:
- ✅ Upload pre-recorded meetings (mp3, wav, m4a, mp4, webm)
- ✅ Capture live meetings from browser (Google Meet, Zoom, Teams)
- ✅ Real-time transcription with live captions
- ✅ Advanced speaker diarization (multiple speakers with names)
- ✅ Multilingual support (mixed-language meetings)
- ✅ AI-powered insights (summary, action items, decisions)
- ✅ Semantic search with embeddings
- ✅ Professional SaaS UI

**Timeline**: 21 days
**Technology Stack**: FastAPI, Next.js, PostgreSQL, pyannote.audio, Whisper, Groq LLM

---

## Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                    Frontend (Next.js)                            │
│  Dashboard │ Upload │ Live Meeting │ Meeting Details │ Settings  │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTP/WebSocket
┌────────────────────────▼────────────────────────────────────────┐
│                    API Gateway (FastAPI)                         │
│  Auth │ Meetings │ WebSocket │ Transcripts │ Insights │ Search   │
└────────────────────────┬────────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
┌───────▼────────┐ ┌────▼──────────┐ ┌──▼──────────────┐
│  Services      │ │  Background   │ │  External APIs  │
│ Transcription  │ │ Celery Tasks  │ │ Groq LLM        │
│ Diarization    │ │ Redis Queue   │ │ Whisper API     │
│ Embedding      │ │ Worker Pool   │ │ HuggingFace     │
│ Summary        │ │               │ │                 │
└────────────────┘ └───────────────┘ └─────────────────┘
        │
┌───────▼────────────────────────────────────────────┐
│           Database (PostgreSQL)                     │
│ Users │ Meetings │ Transcripts │ Speakers │ Insights│
│ Embeddings (pgvector) │ LiveSessions │ ChatMessages│
└────────────────────────────────────────────────────┘
```

---

## Feature Specifications

### 1. Dashboard Landing Page

**Purpose**: Primary entry point for users

**Two Main Options**:
1. **Upload Recording** - Upload pre-recorded meetings
2. **Start Live Meeting** - Capture live meeting audio

**Additional Features**:
- Recent meetings list with status
- Statistics (total meetings, hours transcribed)
- User profile and settings
- Premium SaaS UI design

**Design**: Similar to Otter.ai, Fireflies.ai, Fathom

---

### 2. Upload Recording Flow

**Supported Formats**: mp3, wav, m4a, mp4, webm

**Processing Pipeline**:
```
Upload → Validate → Chunk (30s) → Transcribe → Diarize → 
Merge → Store → Embed → Summarize → Display
```

**Performance**:
- Upload: < 5 seconds
- Processing: < 15 minutes for 1-hour meeting
- Transcription: Real-time
- Speaker diarization: < 2 minutes per hour
- Summary: < 30 seconds

---

### 3. Live Meeting Capture

**How It Works**:
1. User clicks "Start Live Meeting"
2. Browser requests permission to capture meeting tab audio
3. User selects meeting tab (Google Meet, Zoom, Teams, etc.)
4. System captures audio and displays real-time captions
5. When meeting ends, generates final transcript and insights

**Technical Details**:
- Uses `navigator.mediaDevices.getDisplayMedia()`
- Captures 3-second audio chunks
- Sends chunks via WebSocket to backend
- Backend transcribes in real-time
- Frontend displays live captions

**Real-time Requirements**:
- Audio chunk capture: Every 3 seconds
- WebSocket latency: < 500ms
- Transcription latency: < 2 seconds per chunk
- Caption display: < 1 second after transcription

---

### 4. Speaker Diarization (CRITICAL)

**What It Does**: Automatically separates multiple speakers with accurate labels

**Output Format**:
```
00:00:15 Rahul (Speaker 1): Let's finalize the budget
00:00:22 Neha (Speaker 2): Deadline is Friday
00:00:28 Rahul (Speaker 1): I'll handle the reports
```

**Technology**: pyannote.audio

**Features**:
- Detect speaker changes automatically
- Assign speaker labels (Speaker 1, Speaker 2, etc.)
- Estimate number of speakers
- Handle overlapping speech
- Handle silence and background noise

**Premium Feature** (Optional):
- Allow users to rename speakers manually
- Save speaker names for future meetings

---

### 5. Multilingual Support (CRITICAL)

**Supported Combinations**:
- English + Hindi
- English + Gujarati
- English + Marathi
- Hindi only
- Spanish + English
- French + English
- Any combination Whisper supports

**How It Works**:
- Automatic language detection per audio chunk
- Preserve original language in transcript
- Optional English translation
- Maintain natural phrasing

**Example**:
```
Original: "Kal deadline hai so please submit by evening"
Transcript: "Kal deadline hai so please submit by evening"
(NOT translated unless explicitly requested)
```

---

### 6. Real-time Transcript UI

**Display During Live Meeting**:
```
00:01:22 Rahul: Let's begin the meeting
00:01:25 Neha: Sharing screen now
00:01:28 Rahul: Can everyone see the presentation?
00:01:32 Neha: Yes, looks good
```

**Features**:
- Auto-scroll to latest line
- Highlight current speaker
- Different colors for different speakers
- Timestamps for each segment
- Copy to clipboard
- Download transcript

---

### 7. AI Insights Generation

**Triggered**: When meeting ends or user clicks "Generate Insights"

**Generated Insights**:
```json
{
  "summary": "2-3 sentence summary",
  "key_points": ["point 1", "point 2", "point 3"],
  "action_items": [
    {
      "task": "Description",
      "owner": "Person responsible",
      "deadline": "Deadline if mentioned"
    }
  ],
  "decisions": ["Decision 1", "Decision 2"],
  "risks": ["Risk 1", "Risk 2"],
  "next_steps": ["Step 1", "Step 2"]
}
```

**Technology**: Groq LLM (llama-3.3-70b-versatile)

---

### 8. Transcript Search

**How It Works**:
- Generate embeddings for each transcript segment
- Store embeddings in pgvector
- Perform semantic search (not just keyword matching)
- Return matching segments with timestamps

**Search Examples**:
- "What was the final deadline?"
- "Who discussed the budget?"
- "Marketing plan discussion"
- "When is the next meeting?"

**Technology**: sentence-transformers/all-MiniLM-L6-v2 + pgvector

---

## Database Schema

### Key Tables

**Users**
- id, email, password_hash, full_name, is_active, created_at

**Meetings**
- id, user_id, title, description, meeting_type (upload/live), status, duration, language, audio_url, created_at

**Transcripts**
- id, meeting_id, speaker_id, speaker_name, text, start_time, end_time, language, confidence, created_at

**Speakers**
- id, meeting_id, speaker_number, speaker_name, talk_time, word_count, created_at

**Insights**
- id, meeting_id, summary, key_points[], action_items[], decisions[], risks[], next_steps[], generated_at

**Embeddings** (pgvector)
- id, transcript_id, embedding (384-dim vector), created_at

**LiveSessions**
- id, meeting_id, session_token, started_at, ended_at, status, created_at

---

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register user
- `POST /api/v1/auth/login` - Login user
- `POST /api/v1/auth/verify-token` - Verify JWT token

### Meetings
- `GET /api/v1/meetings` - List user's meetings
- `POST /api/v1/meetings/upload` - Upload recording
- `POST /api/v1/meetings/start-live` - Start live meeting
- `GET /api/v1/meetings/{id}` - Get meeting details
- `PUT /api/v1/meetings/{id}` - Update meeting
- `DELETE /api/v1/meetings/{id}` - Delete meeting

### Live Meeting WebSocket
- `WS /api/v1/meetings/live/{meeting_id}` - WebSocket for live audio chunks

### Meeting Processing
- `POST /api/v1/meetings/{id}/end` - End live meeting
- `GET /api/v1/meetings/{id}/transcript` - Get full transcript
- `GET /api/v1/meetings/{id}/insights` - Get insights
- `GET /api/v1/meetings/{id}/search?q=query` - Search transcript

### Speakers
- `GET /api/v1/meetings/{id}/speakers` - Get speakers
- `PUT /api/v1/meetings/{id}/speakers/{speaker_id}` - Rename speaker

### Export (Existing)
- `GET /api/v1/meetings/{id}/transcript/pdf` - Download PDF
- `POST /api/v1/meetings/{id}/transcript/translate` - Translate

---

## Frontend Pages

1. **Dashboard** (`/dashboard`)
   - Upload and live meeting cards
   - Recent meetings list
   - Statistics

2. **Upload** (`/upload`)
   - File upload with drag-and-drop
   - File validation
   - Upload progress
   - Processing status

3. **Live Meeting** (`/live-meeting`)
   - Audio capture setup
   - Real-time transcript display
   - Speaker indicator
   - Meeting controls

4. **Meeting Details** (`/meeting/[id]`)
   - Full transcript with speaker labels
   - Summary and insights
   - Action items
   - Speaker analytics
   - Search interface
   - Export options

5. **Settings** (`/settings`)
   - User profile
   - Preferences
   - Account management

---

## Technology Stack

### Backend
- **Framework**: FastAPI + Uvicorn
- **Database**: PostgreSQL 15 + pgvector
- **Cache/Queue**: Redis
- **Task Queue**: Celery
- **AI/ML**: 
  - Whisper API (transcription)
  - pyannote.audio (speaker diarization)
  - sentence-transformers (embeddings)
  - Groq LLM (insights)
- **Authentication**: JWT
- **ORM**: SQLAlchemy
- **WebSocket**: python-socketio

### Frontend
- **Framework**: Next.js 14.2.35
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **HTTP Client**: Axios
- **State Management**: React Hooks
- **Audio**: MediaRecorder API, Web Audio API

### Infrastructure
- **Containerization**: Docker & Docker Compose
- **Storage**: Local or AWS S3
- **API Documentation**: Swagger UI / ReDoc

---

## Performance Requirements

### Scalability
- Support meetings up to 2 hours
- Handle 100+ concurrent live meetings
- Process 1000+ meetings per day

### Latency
- Live caption display: < 1 second
- Chunk processing: < 2 seconds
- Search results: < 500ms
- API response: < 200ms

### Resource Usage
- Memory: < 500MB per live session
- CPU: Efficient async processing
- Storage: Optimized with compression
- Bandwidth: Efficient chunk streaming

---

## Implementation Phases

### Phase 1: Database & Backend Setup (3 days)
- Create database schema
- Update models
- Add dependencies
- Set up project structure

### Phase 2: Upload Recording Flow (3 days)
- Audio processing service
- Transcription service
- Speaker diarization service
- Upload endpoint
- Background processing pipeline

### Phase 3: Live Meeting Capture (4 days)
- WebSocket infrastructure
- Live meeting service
- Live meeting endpoints
- Real-time transcription
- Session management

### Phase 4: Speaker Diarization & Multilingual (3 days)
- Advanced speaker diarization
- Speaker management
- Multilingual support
- Transcript merging

### Phase 5: Frontend UI & Integration (4 days)
- Dashboard page
- Upload page
- Live meeting page
- Real-time transcript UI
- Meeting details page
- API integration

### Phase 6: Search & Insights (2 days)
- Transcript search
- AI insights generation
- Insights display
- Speaker analytics

### Phase 7: Testing & Optimization (2 days)
- Backend testing
- Frontend testing
- Performance optimization
- Documentation

**Total: 21 days**

---

## Bonus Features (Optional)

1. **AI Chat with Meeting** - Ask questions about meeting content
2. **Sentiment Analysis** - Analyze sentiment per speaker
3. **Speaker Talk Time Analytics** - Show who spoke most
4. **Auto Email Meeting Notes** - Send summary via email
5. **Calendar Integration** - Add to Google Calendar, Outlook
6. **Meeting Comparison** - Compare transcripts from multiple meetings
7. **Custom Prompts** - Allow users to create custom summary prompts
8. **Speaker Identification** - Identify speakers by voice across meetings
9. **Noise Filtering** - Remove background noise from audio
10. **Real-time Translation** - Translate captions in real-time

---

## Code Quality Standards

- Production-grade clean code
- Modular folder structure
- Reusable services and utilities
- Type-safe frontend code (TypeScript)
- Comprehensive comments
- Proper exception handling
- Loading states and error messages
- WebSocket reconnection logic
- Graceful degradation

---

## Security Considerations

- JWT authentication with expiration
- HTTPS/WSS for WebSocket
- Input validation
- SQL injection prevention
- CORS configuration
- Rate limiting
- File upload validation
- User ownership validation

---

## Success Criteria

✅ Dashboard with upload and live meeting options
✅ Upload recording flow working end-to-end
✅ Live meeting capture with real-time captions
✅ Accurate speaker diarization
✅ Multilingual support working
✅ Transcript search with embeddings
✅ AI insights generation
✅ Professional SaaS UI
✅ All endpoints tested and working
✅ Performance requirements met
✅ Production-ready code quality
✅ Comprehensive documentation

---

## Deliverables

1. Full backend code (FastAPI)
2. Full frontend code (Next.js)
3. Database migrations
4. .env.example with all required variables
5. README with setup guide
6. Local run instructions
7. Docker setup
8. API documentation
9. Architecture diagrams
10. Deployment guide

---

## Next Steps

1. Review and approve this specification
2. Set up development environment
3. Begin Phase 1: Database & Backend Setup
4. Follow implementation phases sequentially
5. Test each phase before moving to next
6. Deploy to production when complete

---

**Specification Version**: 1.0.0
**Last Updated**: April 24, 2026
**Status**: Ready for Implementation
