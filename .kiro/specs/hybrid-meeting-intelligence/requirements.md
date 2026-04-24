# Hybrid Meeting Intelligence System - Requirements

## Project Overview

Upgrade the existing AI Meeting Intelligence Platform into a production-grade Hybrid Meeting Intelligence System supporting both recorded and live meetings with advanced speaker diarization, multilingual support, and real-time transcription.

**Target**: SaaS-quality product comparable to Otter.ai, Fireflies.ai, Fathom

## Functional Requirements

### 1. Dashboard Landing Page

**Purpose**: Primary entry point for users to choose between upload or live meeting

**Features**:
- Beautiful SaaS-style dashboard with two prominent CTAs
- Option A: "Upload Recording" - for pre-recorded meetings
- Option B: "Start Live Meeting" - for real-time meeting capture
- Recent meetings list with status indicators
- User profile and settings access
- Meeting statistics (total meetings, total hours transcribed)

**Design Requirements**:
- Premium SaaS UI (similar to Otter.ai, Fireflies.ai)
- Responsive design (mobile, tablet, desktop)
- Dark/light mode support
- Smooth animations and transitions
- Loading states and error handling

### 2. Upload Recording Flow

**User Journey**:
1. User clicks "Upload Recording"
2. Selects audio file (mp3, wav, m4a, mp4, webm)
3. Enters meeting title and optional description
4. Clicks upload
5. System processes and displays results

**Supported Formats**:
- mp3 (MPEG Audio)
- wav (Waveform Audio)
- m4a (MPEG-4 Audio)
- mp4 (MPEG-4 Video)
- webm (WebM Audio/Video)

**Processing Pipeline**:
```
Audio File Upload
    ↓
Backend Receives File
    ↓
Chunk Audio (30-second chunks)
    ↓
Whisper Transcription (per chunk)
    ↓
Speaker Diarization (pyannote.audio)
    ↓
Merge Transcripts + Speaker Labels
    ↓
Store in Database
    ↓
Generate Summary (Groq LLM)
    ↓
Extract Insights (action items, decisions, deadlines)
    ↓
Generate Embeddings (sentence-transformers)
    ↓
Store Embeddings in pgvector
    ↓
Display Results on Dashboard
```

**Performance Requirements**:
- File upload: < 5 seconds
- Transcription: Real-time (1 hour audio ≈ 5-10 minutes processing)
- Speaker diarization: < 2 minutes per hour
- Summary generation: < 30 seconds
- Total processing: < 15 minutes for 1-hour meeting

### 3. Live Meeting Flow

**User Journey**:
1. User clicks "Start Live Meeting"
2. Browser requests permission to capture meeting tab audio
3. User selects meeting tab (Google Meet, Zoom, Teams, etc.)
4. System starts capturing audio
5. Real-time captions appear as user speaks
6. When meeting ends, system generates final transcript and insights

**Technical Flow**:
```
User Clicks "Start Live Meeting"
    ↓
Browser Requests getDisplayMedia() Permission
    ↓
User Selects Meeting Tab
    ↓
MediaRecorder Captures Audio Stream
    ↓
Every 3 Seconds: Create Audio Chunk
    ↓
Send Chunk via WebSocket to Backend
    ↓
Backend Transcribes Chunk (Whisper)
    ↓
Backend Performs Speaker Diarization (incremental)
    ↓
Send Transcript + Speaker Label via WebSocket
    ↓
Frontend Displays Live Caption
    ↓
User Ends Meeting
    ↓
Generate Final Transcript
    ↓
Generate Summary + Insights
    ↓
Display Results
```

**Real-time Requirements**:
- Audio chunk capture: Every 3 seconds
- WebSocket latency: < 500ms
- Transcription latency: < 2 seconds per chunk
- Caption display: < 1 second after transcription
- Support meetings up to 2 hours

### 4. Multilingual Support (CRITICAL)

**Requirement**: System must handle mixed-language meetings automatically

**Supported Language Combinations**:
- English + Hindi
- English + Gujarati
- English + Marathi
- Hindi only
- Spanish + English
- French + English
- And any combination Whisper supports

**Implementation**:
- Use Whisper's automatic language detection
- Detect language per audio chunk
- Preserve original language in transcript
- Optional: Provide English translation
- Maintain natural phrasing and context

**Example**:
```
Original Audio: "Kal deadline hai so please submit by evening"
Transcript: "Kal deadline hai so please submit by evening"
(NOT translated to English unless explicitly requested)
```

**Database Storage**:
- Store original language code (en, hi, gu, mr, es, fr, etc.)
- Store detected language per segment
- Store original transcript
- Store optional English translation
- Support language-specific search

### 5. Advanced Speaker Diarization (CRITICAL)

**Requirement**: Accurate separation of multiple speakers with names/labels

**Implementation**:
- Use `pyannote.audio` for speaker diarization
- Detect speaker changes automatically
- Assign speaker labels (Speaker 1, Speaker 2, etc.)
- Merge with transcript segments
- Estimate number of speakers

**Output Format**:
```
00:00:15 Rahul (Speaker 1): Let's finalize the budget
00:00:22 Neha (Speaker 2): Deadline is Friday
00:00:28 Rahul (Speaker 1): I'll handle the reports
00:00:35 Neha (Speaker 2): Perfect, let's move forward
```

**Premium Feature** (Optional):
- Allow users to rename speakers manually
- Save speaker names for future meetings
- Speaker identification across meetings

**Requirements**:
- Detect speaker changes with < 500ms latency
- Timestamp each segment
- Merge transcript + speaker labels
- Estimate number of speakers automatically
- Handle overlapping speech
- Handle silence and background noise

### 6. Real-time Transcript UI

**Display During Live Meeting**:
- Live captions appear as meeting progresses
- Format: `HH:MM:SS Speaker: Text`
- Auto-scroll to latest line
- Highlight latest speaker segment
- Color-code different speakers
- Copy transcript functionality

**Example Display**:
```
00:01:22 Rahul: Let's begin the meeting
00:01:25 Neha: Sharing screen now
00:01:28 Rahul: Can everyone see the presentation?
00:01:32 Neha: Yes, looks good
```

**Features**:
- Auto-scroll to bottom
- Highlight current speaker
- Different colors for different speakers
- Timestamps for each segment
- Copy to clipboard
- Download transcript
- Search within transcript

### 7. Final AI Insights Using Groq

**Trigger**: When meeting ends or user clicks "Generate Insights"

**Prompt to Groq**:
```
Analyze the following meeting transcript and provide structured insights.
Return ONLY valid JSON with no additional text.

{
  "summary": "2-3 sentence summary of the meeting",
  "key_points": ["point 1", "point 2", "point 3"],
  "action_items": [
    {
      "task": "Description of the task",
      "owner": "Person responsible",
      "deadline": "Deadline if mentioned"
    }
  ],
  "decisions": ["Decision 1", "Decision 2"],
  "risks": ["Risk 1", "Risk 2"],
  "next_steps": ["Step 1", "Step 2"]
}
```

**Requirements**:
- Return clean, valid JSON only
- Extract action items with owners and deadlines
- Identify key decisions made
- Highlight risks and concerns
- Suggest next steps
- Generate within 30 seconds

### 8. Transcript Search

**Implementation**:
- Use sentence-transformers/all-MiniLM-L6-v2 for embeddings
- Store embeddings in pgvector
- Support semantic search

**Search Examples**:
- "What was the final deadline?"
- "Who discussed the budget?"
- "Marketing plan discussion"
- "When is the next meeting?"

**Features**:
- Semantic search (not just keyword matching)
- Return matching segments with timestamps
- Highlight matching text
- Show speaker name
- Support filtering by speaker
- Support filtering by date range

### 9. Database Schema

**Tables Required**:
1. `users` - User accounts
2. `meetings` - Meeting metadata
3. `transcripts` - Transcript segments with speaker labels
4. `speakers` - Speaker information per meeting
5. `insights` - Generated summaries and insights
6. `embeddings` - Vector embeddings for search
7. `live_sessions` - Active live meeting sessions
8. `chat_messages` - Chat history (from existing chatbot)
9. `documents` - Uploaded documents (from existing system)

**Key Relationships**:
- User → Meetings (1:N)
- Meeting → Transcripts (1:N)
- Meeting → Speakers (1:N)
- Meeting → Insights (1:1)
- Transcript → Embeddings (1:1)
- Meeting → LiveSessions (1:1)

### 10. API Endpoints

**Authentication**:
- `POST /api/v1/auth/register` - Register user
- `POST /api/v1/auth/login` - Login user
- `POST /api/v1/auth/verify-token` - Verify JWT token

**Meetings**:
- `GET /api/v1/meetings` - List user's meetings
- `POST /api/v1/meetings/upload` - Upload recording
- `POST /api/v1/meetings/start-live` - Start live meeting
- `GET /api/v1/meetings/{id}` - Get meeting details
- `PUT /api/v1/meetings/{id}` - Update meeting
- `DELETE /api/v1/meetings/{id}` - Delete meeting

**Live Meeting WebSocket**:
- `WS /api/v1/meetings/live/{meeting_id}` - WebSocket for live audio chunks
  - Client sends: Audio chunks (3-second intervals)
  - Server sends: Transcribed text + speaker label

**Meeting Processing**:
- `POST /api/v1/meetings/{id}/end` - End live meeting and generate insights
- `GET /api/v1/meetings/{id}/transcript` - Get full transcript
- `GET /api/v1/meetings/{id}/insights` - Get generated insights
- `GET /api/v1/meetings/{id}/search?q=query` - Search transcript

**Speakers**:
- `GET /api/v1/meetings/{id}/speakers` - Get speakers for meeting
- `PUT /api/v1/meetings/{id}/speakers/{speaker_id}` - Rename speaker

**Export**:
- `GET /api/v1/meetings/{id}/transcript/pdf` - Download PDF (existing)
- `POST /api/v1/meetings/{id}/transcript/translate` - Translate (existing)

### 11. Performance Requirements

**Scalability**:
- Support meetings up to 2 hours
- Handle 100+ concurrent live meetings
- Process 1000+ meetings per day

**Latency**:
- Live caption display: < 1 second
- Chunk processing: < 2 seconds
- Search results: < 500ms
- API response: < 200ms

**Resource Usage**:
- Memory: < 500MB per live session
- CPU: Efficient async processing
- Storage: Optimized with compression
- Bandwidth: Efficient chunk streaming

**Optimization Strategies**:
- Async FastAPI for concurrent requests
- Redis for caching and queuing
- Background workers for heavy processing
- Chunk batching for efficiency
- Connection pooling for database
- WebSocket for real-time communication

### 12. Frontend Pages

**Required Pages**:
1. `/login` - User login
2. `/register` - User registration
3. `/dashboard` - Main dashboard with upload/live options
4. `/upload` - Upload recording page
5. `/live-meeting` - Live meeting capture page
6. `/meeting/[id]` - Meeting details and results page
7. `/settings` - User settings

**Components**:
- Navigation bar
- Upload form
- Live meeting recorder
- Real-time transcript display
- Transcript viewer
- Summary panel
- Insights display
- Search interface
- Speaker management

### 13. UI Output Page

**After Meeting Completes, Show**:
1. **Transcript** - Full transcript with speaker labels and timestamps
2. **Summary** - 2-3 sentence summary
3. **Key Points** - Bulleted list of key points
4. **Action Items** - Tasks with owners and deadlines
5. **Decisions** - Key decisions made
6. **Speakers** - List of speakers with talk time
7. **Search** - Search within transcript
8. **Download** - Download as PDF, TXT, or JSON
9. **Share** - Share meeting with others
10. **Chat** - Ask questions about the meeting (existing chatbot)

### 14. Bonus Features (Recommended)

**If Time Permits**:
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

### 15. Code Quality Requirements

**Standards**:
- Production-grade clean code
- Modular folder structure
- Reusable services and utilities
- Type-safe frontend code (TypeScript)
- Comprehensive comments
- Proper exception handling
- Loading states and error messages
- WebSocket reconnection logic
- Graceful degradation

**Testing**:
- Unit tests for services
- Integration tests for APIs
- E2E tests for critical flows
- Error scenario testing

**Documentation**:
- README with setup instructions
- API documentation
- Component documentation
- Architecture diagrams
- Deployment guide

## Non-Functional Requirements

### Security
- JWT authentication
- HTTPS/WSS for WebSocket
- Input validation
- SQL injection prevention
- CORS configuration
- Rate limiting
- File upload validation

### Reliability
- Error handling and recovery
- WebSocket reconnection
- Graceful degradation
- Data persistence
- Backup strategy

### Maintainability
- Clean code structure
- Comprehensive logging
- Monitoring and alerts
- Version control
- Documentation

### Accessibility
- WCAG 2.1 compliance
- Keyboard navigation
- Screen reader support
- Color contrast
- Alt text for images

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

## Timeline Estimate

- Phase 1: Database & Backend Setup (2-3 days)
- Phase 2: Upload Recording Flow (2-3 days)
- Phase 3: Live Meeting Capture (3-4 days)
- Phase 4: Speaker Diarization (2-3 days)
- Phase 5: Frontend UI & Integration (3-4 days)
- Phase 6: Testing & Optimization (2-3 days)
- **Total: 14-20 days**

## Deliverables

1. Full backend code (FastAPI)
2. Full frontend code (Next.js)
3. Database migrations
4. .env.example with all required variables
5. README with setup guide
6. Local run instructions
7. Docker setup (optional)
8. API documentation
9. Architecture diagrams
10. Deployment guide
