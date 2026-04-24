# Design: Advanced Meeting Intelligence Features

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (Next.js)                       │
├─────────────────────────────────────────────────────────────┤
│  • PDF Export Button                                         │
│  • Language Selector                                         │
│  • Chatbot Interface                                         │
│  • Document Upload Widget                                   │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│                  Backend API (FastAPI)                       │
├─────────────────────────────────────────────────────────────┤
│  • PDF Generation Service                                    │
│  • Translation Service                                       │
│  • Chatbot Service (LLM Integration)                         │
│  • Document Processing Service                              │
│  • Chat History Management                                  │
└────────────────┬────────────────────────────────────────────┘
                 │
        ┌────────┴────────┬──────────────┬──────────────┐
        ▼                 ▼              ▼              ▼
    ┌────────┐      ┌──────────┐  ┌──────────┐  ┌──────────┐
    │Database│      │Translation│  │LLM API   │  │File Store│
    │        │      │API        │  │(Groq)    │  │(S3/Local)│
    └────────┘      └──────────┘  └──────────┘  └──────────┘
```

## Feature 1: PDF Export

### 1.1 PDF Generation Service

**File**: `backend/app/services/pdf_service.py`

```python
class PDFService:
    def generate_transcript_pdf(meeting_id: int, db: Session) -> bytes:
        """Generate PDF from meeting transcript"""
        # 1. Fetch meeting and transcript data
        # 2. Create PDF document
        # 3. Add header (meeting info)
        # 4. Add transcript segments
        # 5. Add footer (page numbers)
        # 6. Return PDF bytes
        
    def _format_transcript_segment(segment: Transcript) -> str:
        """Format single transcript segment"""
        # Format: [HH:MM:SS] Speaker: Text
```

### 1.2 PDF Export Endpoint

**File**: `backend/app/routers/export_routes.py`

```
GET /api/v1/meetings/{meeting_id}/transcript/pdf
├─ Authentication: Required
├─ Response: PDF file (application/pdf)
└─ Error Handling: 404 if meeting not found
```

### 1.3 Frontend PDF Download

**File**: `frontend/components/TranscriptExport.tsx`

```typescript
export function TranscriptExport({ meetingId }: Props) {
  const handleDownloadPDF = async () => {
    const response = await fetch(`/api/v1/meetings/${meetingId}/transcript/pdf`);
    const blob = await response.blob();
    // Trigger download
  };
  
  return <button onClick={handleDownloadPDF}>Download as PDF</button>;
}
```

## Feature 2: Multilingual Support

### 2.1 Translation Service

**File**: `backend/app/services/translation_service.py`

```python
class TranslationService:
    def __init__(self):
        self.translator = GoogleTranslator()  # or DeepL
        self.cache = {}  # Cache translations
    
    def translate_transcript(
        meeting_id: int, 
        target_language: str, 
        db: Session
    ) -> List[Dict]:
        """Translate all transcript segments"""
        # 1. Fetch transcript segments
        # 2. Check cache
        # 3. Translate each segment
        # 4. Cache results
        # 5. Return translated segments
    
    def translate_text(text: str, target_lang: str) -> str:
        """Translate single text"""
```

### 2.2 Translation Endpoint

**File**: `backend/app/routers/translation_routes.py`

```
POST /api/v1/meetings/{meeting_id}/transcript/translate
├─ Request: {"target_language": "es"}
├─ Response: {"segments": [...], "language": "es"}
└─ Caching: Results cached for 24 hours
```

### 2.3 Frontend Language Selector

**File**: `frontend/components/LanguageSelector.tsx`

```typescript
const SUPPORTED_LANGUAGES = {
  'en': 'English',
  'es': 'Spanish',
  'fr': 'French',
  'de': 'German',
  'it': 'Italian',
  'pt': 'Portuguese',
  'ru': 'Russian',
  'zh': 'Chinese',
  'ja': 'Japanese',
  'ko': 'Korean'
};

export function LanguageSelector({ meetingId }: Props) {
  const [selectedLang, setSelectedLang] = useState('en');
  const [translatedTranscript, setTranslatedTranscript] = useState(null);
  
  const handleTranslate = async (lang: string) => {
    const response = await fetch(
      `/api/v1/meetings/${meetingId}/transcript/translate`,
      { method: 'POST', body: JSON.stringify({ target_language: lang }) }
    );
    setTranslatedTranscript(await response.json());
  };
}
```

## Feature 3: Meeting Q&A Chatbot

### 3.1 Chatbot Service

**File**: `backend/app/services/chatbot_service.py`

```python
class ChatbotService:
    def __init__(self):
        self.llm = Groq(api_key=settings.GROQ_API_KEY)
    
    def answer_question(
        meeting_id: int,
        question: str,
        db: Session
    ) -> Dict:
        """Answer question about meeting"""
        # 1. Fetch transcript
        # 2. Create context from transcript
        # 3. Build prompt with context
        # 4. Call LLM
        # 5. Extract answer and sources
        # 6. Save to chat history
        # 7. Return answer with citations
    
    def _build_context(transcript_segments: List[Transcript]) -> str:
        """Build context string from transcript"""
        # Combine all segments into context
    
    def _extract_sources(answer: str, transcript: str) -> List[str]:
        """Extract relevant transcript segments as sources"""
```

### 3.2 Chat History Model

**File**: `backend/app/models/chat_message.py`

```python
class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    message = Column(Text)  # User question
    response = Column(Text)  # Chatbot answer
    sources = Column(JSON)  # Citation sources
    created_at = Column(DateTime, default=datetime.utcnow)
```

### 3.3 Chatbot Endpoints

**File**: `backend/app/routers/chatbot_routes.py`

```
POST /api/v1/meetings/{meeting_id}/chat
├─ Request: {"message": "What were the action items?"}
├─ Response: {"answer": "...", "sources": [...]}
└─ Streaming: Optional WebSocket for real-time responses

GET /api/v1/meetings/{meeting_id}/chat/history
├─ Response: List of chat messages
└─ Pagination: Supported

DELETE /api/v1/meetings/{meeting_id}/chat/history
├─ Clears all chat messages for meeting
└─ Requires authentication
```

### 3.4 Frontend Chatbot Component

**File**: `frontend/components/MeetingChatbot.tsx`

```typescript
export function MeetingChatbot({ meetingId }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  
  const handleSendMessage = async (message: string) => {
    setLoading(true);
    const response = await fetch(
      `/api/v1/meetings/${meetingId}/chat`,
      { method: 'POST', body: JSON.stringify({ message }) }
    );
    const data = await response.json();
    setMessages([...messages, { role: 'user', content: message }]);
    setMessages([...messages, { role: 'assistant', content: data.answer }]);
    setLoading(false);
  };
  
  return (
    <div className="chatbot-container">
      <div className="messages">
        {messages.map(msg => (
          <div key={msg.id} className={`message ${msg.role}`}>
            {msg.content}
            {msg.sources && <Sources sources={msg.sources} />}
          </div>
        ))}
      </div>
      <input 
        value={input}
        onChange={e => setInput(e.target.value)}
        onKeyPress={e => e.key === 'Enter' && handleSendMessage(input)}
        placeholder="Ask about the meeting..."
      />
    </div>
  );
}
```

## Feature 4: Document Context Upload

### 4.1 Document Model

**File**: `backend/app/models/document.py`

```python
class Document(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    filename = Column(String(255))
    file_path = Column(String(500))  # S3 or local path
    file_size = Column(Integer)
    file_type = Column(String(50))  # pdf, docx, txt
    content = Column(Text)  # Extracted text
    created_at = Column(DateTime, default=datetime.utcnow)
```

### 4.2 Document Processing Service

**File**: `backend/app/services/document_service.py`

```python
class DocumentService:
    ALLOWED_TYPES = ['pdf', 'docx', 'txt']
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    
    def process_document(file: UploadFile, meeting_id: int) -> Document:
        """Process uploaded document"""
        # 1. Validate file type and size
        # 2. Extract text content
        # 3. Store in database
        # 4. Index for search
        # 5. Return document metadata
    
    def extract_text(file_path: str, file_type: str) -> str:
        """Extract text from document"""
        # Handle PDF, DOCX, TXT
    
    def search_documents(meeting_id: int, query: str) -> List[Document]:
        """Search documents by content"""
```

### 4.3 Document Upload Endpoint

**File**: `backend/app/routers/document_routes.py`

```
POST /api/v1/meetings/{meeting_id}/documents
├─ Request: FormData with file
├─ Response: {"id": 1, "filename": "...", "size": 1024}
└─ Validation: File type, size, malware scan

GET /api/v1/meetings/{meeting_id}/documents
├─ Response: List of documents
└─ Pagination: Supported

DELETE /api/v1/meetings/{meeting_id}/documents/{doc_id}
├─ Deletes document
└─ Requires authentication
```

### 4.4 Enhanced Chatbot with Documents

**File**: `backend/app/services/chatbot_service.py` (updated)

```python
def answer_question_with_documents(
    meeting_id: int,
    question: str,
    db: Session
) -> Dict:
    """Answer question using transcript + documents"""
    # 1. Fetch transcript
    # 2. Fetch documents
    # 3. Search documents for relevant content
    # 4. Build combined context
    # 5. Call LLM with context
    # 6. Return answer with sources (transcript + documents)
```

## Database Schema Changes

### New Tables
- `chat_messages` - Store chatbot conversations
- `documents` - Store uploaded documents
- `translation_cache` - Cache translations

### Modified Tables
- `transcripts` - Already updated to TEXT type

## API Summary

| Feature | Method | Endpoint | Purpose |
|---------|--------|----------|---------|
| PDF Export | GET | `/api/v1/meetings/{id}/transcript/pdf` | Download transcript as PDF |
| Translation | POST | `/api/v1/meetings/{id}/transcript/translate` | Translate transcript |
| Chatbot | POST | `/api/v1/meetings/{id}/chat` | Ask question about meeting |
| Chat History | GET | `/api/v1/meetings/{id}/chat/history` | Get chat messages |
| Documents | POST | `/api/v1/meetings/{id}/documents` | Upload document |
| Documents | GET | `/api/v1/meetings/{id}/documents` | List documents |
| Documents | DELETE | `/api/v1/meetings/{id}/documents/{doc_id}` | Delete document |

## Technology Stack

- **PDF Generation**: reportlab or pypdf
- **Translation**: Google Translate API or DeepL
- **LLM**: Groq (already configured)
- **Document Processing**: PyPDF2, python-docx, python-pptx
- **Frontend**: React, TypeScript, Tailwind CSS
- **Database**: PostgreSQL (existing)

## Performance Considerations

- Cache translations for 24 hours
- Lazy load chat history
- Stream chatbot responses
- Index documents for fast search
- Compress PDFs before download
- Rate limit chatbot to 10 requests/minute per user

## Security Considerations

- Validate file uploads (type, size, content)
- Scan documents for malware
- Sanitize user input for chatbot
- Enforce user authentication
- Encrypt sensitive data
- Log all operations
