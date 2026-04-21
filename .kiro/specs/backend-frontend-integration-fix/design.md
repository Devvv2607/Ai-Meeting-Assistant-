# Design Document: Backend-Frontend Integration Fix

## Overview

This design addresses critical issues in the AI Meeting Intelligence Platform's backend and ensures proper integration with the frontend. The system consists of a FastAPI backend, PostgreSQL database, Redis cache, Celery workers, and a Next.js frontend. The design focuses on fixing configuration issues, improving error handling, and ensuring seamless communication between all components.

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────┐
│                   Next.js Frontend                      │
│         (Port 3000, TypeScript + React)                 │
└────────────────────┬────────────────────────────────────┘
                     │ HTTP/REST + JWT
┌────────────────────▼────────────────────────────────────┐
│                FastAPI Backend (Port 8000)              │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Routers: Auth, Meetings, Transcripts            │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Services: Whisper, LLM, Embeddings, Audio      │  │
│  └──────────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
┌───────▼───────┐   │   ┌────────▼──────┐
│  PostgreSQL   │   │   │ Redis (Cache  │
│   Database    │   │   │  & Broker)    │
└───────────────┘   │   └────────┬──────┘
                    │            │
            ┌───────▼────────────▼───────┐
            │    Celery Workers          │
            │  (Async Processing)        │
            └────────────────────────────┘
                    │
            ┌───────▼────────┐
            │   AWS S3       │
            │ (Audio Storage)│
            └────────────────┘
```

### Data Flow

1. User authenticates via frontend → Backend validates → Returns JWT
2. User uploads audio → Backend saves to S3 → Creates meeting record → Enqueues Celery task
3. Celery worker processes audio → Transcribes → Generates embeddings → Creates summary
4. Frontend polls/fetches meeting status → Displays transcript and summary

## Components and Interfaces

### 1. Database Configuration Module

**Purpose**: Properly configure database connections with environment variable support

**Interface**:
```python
class Settings(BaseSettings):
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str
    DB_HOST: str
    DB_PORT: str
    
    @property
    def DATABASE_URL(self) -> str:
        # URL-encode password to handle special characters
        encoded_password = quote(self.DB_PASSWORD, safe='')
        return f"postgresql://{self.DB_USER}:{encoded_password}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
```

**Key Features**:
- URL-encode passwords to handle special characters like @, #, etc.
- Support both local and Docker configurations
- Provide clear error messages for missing variables
- Use connection pooling for performance

### 2. API Router Configuration

**Purpose**: Ensure all routes are properly prefixed and CORS is configured

**Interface**:
```python
app = FastAPI(title="AI Meeting Intelligence Platform")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://frontend:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers with proper prefix
app.include_router(auth_routes.router, prefix="/api/v1")
app.include_router(meeting_routes.router, prefix="/api/v1")
app.include_router(transcript_routes.router, prefix="/api/v1")
```

**Key Features**:
- All routes under /api/v1 prefix
- CORS enabled for frontend origins
- Proper error handling middleware
- Request/response logging

### 3. Authentication Service

**Purpose**: Handle user registration, login, and JWT token management

**Interface**:
```python
def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    
def create_access_token(data: dict, expires_delta: timedelta) -> str:
    """Create JWT access token"""
    
def verify_token(token: str) -> Optional[dict]:
    """Verify and decode JWT token"""
```

**Key Features**:
- Bcrypt password hashing with salt
- JWT tokens with expiration
- Token refresh mechanism
- Secure token validation

### 4. File Upload Handler

**Purpose**: Handle audio file uploads with validation and S3 storage

**Interface**:
```python
async def upload_meeting(
    title: str,
    file: UploadFile,
    description: Optional[str],
    current_user: User,
    db: Session
) -> Meeting:
    """
    1. Validate file type and size
    2. Save temporarily
    3. Upload to S3
    4. Create meeting record
    5. Enqueue processing task
    """
```

**Key Features**:
- File type validation (.wav, .mp3, .m4a, .mp4)
- File size limit (2GB)
- Temporary file cleanup
- S3 upload with error handling
- Async task triggering

### 5. Celery Task Processor

**Purpose**: Process audio files asynchronously

**Interface**:
```python
@celery_app.task(bind=True)
def process_meeting_task(self, meeting_id: int, audio_s3_path: str):
    """
    1. Download audio from S3
    2. Transcribe using Whisper
    3. Generate embeddings
    4. Create summary using LLM
    5. Store results in database
    6. Update meeting status
    """
```

**Key Features**:
- Progress tracking
- Error handling and retry logic
- Status updates (PENDING → PROCESSING → COMPLETED/FAILED)
- Resource cleanup

### 6. Frontend API Client

**Purpose**: Centralized API communication with authentication

**Interface**:
```typescript
class APIClient {
  private client: AxiosInstance;
  
  // Auth methods
  async register(email: string, password: string, fullName?: string)
  async login(email: string, password: string)
  
  // Meeting methods
  async uploadMeeting(title: string, file: File, description?: string)
  async getMeetings(skip: number, limit: number)
  async getMeeting(meetingId: number)
  
  // Transcript methods
  async getTranscript(meetingId: number)
  async getSummary(meetingId: number)
  async searchTranscript(meetingId: number, query: string, topK: number)
}
```

**Key Features**:
- Automatic JWT token injection
- 401 error handling with redirect
- FormData handling for file uploads
- Consistent error formatting

## Data Models

### User Model
```python
class User(Base):
    id: int (PK)
    email: str (unique, indexed)
    password_hash: str
    full_name: str (optional)
    is_active: bool (default=True)
    created_at: datetime
    updated_at: datetime
```

### Meeting Model
```python
class Meeting(Base):
    id: int (PK)
    user_id: int (FK → users.id)
    title: str
    description: str (optional)
    audio_url: str (S3 path)
    duration: float (seconds)
    status: str (PENDING/PROCESSING/COMPLETED/FAILED)
    celery_task_id: str (optional)
    created_at: datetime
    updated_at: datetime
```

### Transcript Model
```python
class Transcript(Base):
    id: int (PK)
    meeting_id: int (FK → meetings.id)
    speaker: str
    text: str
    start_time: float
    end_time: float
    embedding: bytes (JSON-encoded vector)
    created_at: datetime
```

### Summary Model
```python
class Summary(Base):
    id: int (PK)
    meeting_id: int (FK → meetings.id, unique)
    summary: str
    key_points: JSON (list of strings)
    action_items: JSON (list of strings)
    sentiment: str
    created_at: datetime
    updated_at: datetime
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Database Connection Validity
*For any* environment configuration with valid database credentials, initializing the database connection should succeed and allow query execution.
**Validates: Requirements 2.1, 2.2, 2.3, 2.4**

### Property 2: Password Encoding Security
*For any* password string, hashing it should produce a different hash each time (due to salt), and verifying the original password against any of those hashes should return True.
**Validates: Requirements 3.1**

### Property 3: JWT Token Round-Trip
*For any* valid user data payload, creating a JWT token and then verifying it should return the original payload data.
**Validates: Requirements 3.3, 3.5**

### Property 4: Authentication Rejection
*For any* invalid credentials (wrong email or wrong password), the login attempt should return a 401 error and not create a session.
**Validates: Requirements 3.4**

### Property 5: File Type Validation
*For any* file with an extension not in the allowed list (.wav, .mp3, .m4a, .mp4), the upload should be rejected with a 400 error.
**Validates: Requirements 4.1**

### Property 6: File Size Validation
*For any* file larger than 2GB, the upload should be rejected with a 400 error before processing.
**Validates: Requirements 4.2**

### Property 7: Meeting Status Progression
*For any* successfully created meeting, the status should progress from PENDING → PROCESSING → COMPLETED (or FAILED), never skipping states or going backwards.
**Validates: Requirements 5.2, 5.3, 5.4**

### Property 8: API Endpoint Consistency
*For any* API endpoint error response, the response should contain a "detail" field with a string or list describing the error.
**Validates: Requirements 6.3**

### Property 9: CORS Header Presence
*For any* API request from the frontend origin, the response should include appropriate CORS headers allowing the request.
**Validates: Requirements 6.5**

### Property 10: Authorization Header Format
*For any* protected endpoint request, if the Authorization header is missing or malformed, the response should be 401 Unauthorized.
**Validates: Requirements 3.5, 6.4**

### Property 11: FormData Content-Type
*For any* file upload request, the Content-Type header should be multipart/form-data (set automatically by the browser/axios).
**Validates: Requirements 7.3**

### Property 12: Token Expiration Handling
*For any* expired JWT token, attempting to use it for authentication should return a 401 error and trigger frontend redirect to login.
**Validates: Requirements 7.2**

### Property 13: Environment Variable Validation
*For any* missing required environment variable, the application should fail to start with a clear error message indicating which variable is missing.
**Validates: Requirements 8.3**

### Property 14: Service Health Check
*For any* running service, the health check endpoint should return 200 status within the timeout period.
**Validates: Requirements 1.3, 1.4**

### Property 15: Database Transaction Rollback
*For any* database operation that raises an exception, the transaction should be rolled back and the database should remain in a consistent state.
**Validates: Requirements 9.2**

## Error Handling

### Error Categories

1. **Validation Errors (400)**
   - Invalid file type
   - File too large
   - Missing required fields
   - Invalid email format

2. **Authentication Errors (401)**
   - Invalid credentials
   - Expired token
   - Missing token
   - Malformed token

3. **Authorization Errors (403)**
   - Inactive user account
   - Insufficient permissions

4. **Not Found Errors (404)**
   - Meeting not found
   - User not found
   - Transcript not available

5. **Server Errors (500)**
   - Database connection failure
   - S3 upload failure
   - Celery task failure
   - External API failure

### Error Response Format

All errors follow this consistent format:
```json
{
  "detail": "Error message" | ["Error 1", "Error 2"]
}
```

### Error Handling Strategy

1. **Backend**:
   - Try-catch blocks around all database operations
   - Explicit rollback on errors
   - Detailed logging with context
   - User-friendly error messages (no stack traces in production)

2. **Frontend**:
   - Catch all API errors
   - Display user-friendly messages
   - Redirect on 401 errors
   - Retry logic for transient failures

3. **Celery Workers**:
   - Automatic retry with exponential backoff
   - Update meeting status to FAILED on permanent failure
   - Log full error traceback
   - Clean up resources on failure

## Testing Strategy

### Unit Tests

Unit tests verify specific examples and edge cases:

1. **Authentication Tests**
   - Test successful registration
   - Test duplicate email rejection
   - Test successful login
   - Test invalid credentials rejection
   - Test JWT token creation and verification

2. **File Upload Tests**
   - Test valid file upload
   - Test invalid file type rejection
   - Test file size limit enforcement
   - Test S3 upload success/failure

3. **Database Tests**
   - Test connection with valid credentials
   - Test connection with invalid credentials
   - Test transaction rollback on error
   - Test model relationships

4. **API Endpoint Tests**
   - Test each endpoint with valid input
   - Test each endpoint with invalid input
   - Test authentication requirements
   - Test CORS headers

### Property-Based Tests

Property tests verify universal properties across all inputs using a property-based testing library (pytest with Hypothesis for Python, fast-check for TypeScript):

1. **Property Test: Password Hashing**
   - Generate random passwords
   - Verify hash uniqueness (with salt)
   - Verify verification works
   - **Feature: backend-frontend-integration-fix, Property 2: Password Encoding Security**

2. **Property Test: JWT Round-Trip**
   - Generate random user payloads
   - Create token and verify
   - Check payload matches
   - **Feature: backend-frontend-integration-fix, Property 3: JWT Token Round-Trip**

3. **Property Test: File Type Validation**
   - Generate random file extensions
   - Verify only allowed types pass
   - **Feature: backend-frontend-integration-fix, Property 5: File Type Validation**

4. **Property Test: Meeting Status Progression**
   - Generate random meeting workflows
   - Verify status never goes backwards
   - **Feature: backend-frontend-integration-fix, Property 7: Meeting Status Progression**

5. **Property Test: Error Response Format**
   - Generate random error scenarios
   - Verify all have "detail" field
   - **Feature: backend-frontend-integration-fix, Property 8: API Endpoint Consistency**

### Integration Tests

1. **End-to-End Flow**
   - Register → Login → Upload → Check Status → Get Transcript → Get Summary
   - Verify each step completes successfully
   - Verify data consistency across steps

2. **Service Dependencies**
   - Test backend starts after PostgreSQL is ready
   - Test Celery worker starts after Redis is ready
   - Test frontend can reach backend

3. **Error Recovery**
   - Test database reconnection after failure
   - Test S3 retry logic
   - Test Celery task retry

### Testing Configuration

- Minimum 100 iterations per property test
- Use test database (separate from development)
- Mock external services (S3, LLM) in unit tests
- Use real services in integration tests
- Run tests in CI/CD pipeline

## Implementation Notes

### Critical Fixes Required

1. **Database URL Encoding**
   - Current: Password with @ character breaks connection
   - Fix: Use `urllib.parse.quote()` to encode password
   - Location: `backend/app/config.py`

2. **Router Prefix Consistency**
   - Current: Some routes missing /api/v1 prefix
   - Fix: Ensure all routers include prefix in main.py
   - Location: `backend/app/main.py`

3. **CORS Configuration**
   - Current: Allows all origins (*)
   - Fix: Specify frontend origins explicitly
   - Location: `backend/app/main.py`

4. **Environment Variable Validation**
   - Current: Silent failures on missing variables
   - Fix: Add startup validation with clear errors
   - Location: `backend/app/config.py`

5. **Frontend API URL**
   - Current: May not be set correctly
   - Fix: Ensure NEXT_PUBLIC_API_URL is used consistently
   - Location: `frontend/services/api.ts`

6. **Docker Service Dependencies**
   - Current: Services may start before dependencies are ready
   - Fix: Add proper health checks and depends_on conditions
   - Location: `docker-compose.yml`

7. **Error Response Consistency**
   - Current: Some endpoints return different error formats
   - Fix: Standardize all error responses to use "detail" field
   - Location: All router files

8. **File Upload Content-Type**
   - Current: May set wrong Content-Type for FormData
   - Fix: Let axios/browser handle Content-Type automatically
   - Location: `frontend/services/api.ts`

### Performance Considerations

1. **Database Connection Pooling**
   - Use SQLAlchemy pool_size=20, max_overflow=40
   - Prevents connection exhaustion under load

2. **Redis Caching**
   - Cache frequently accessed data (user info, meeting metadata)
   - Set appropriate TTL values

3. **Celery Concurrency**
   - Default: 2 workers
   - Adjust based on available CPU/memory

4. **Audio Chunking**
   - Split large files into 5-minute chunks
   - Process chunks in parallel

### Security Considerations

1. **Password Storage**
   - Use bcrypt with automatic salt
   - Never log passwords

2. **JWT Tokens**
   - Short expiration (30 minutes)
   - Secure secret key (not default)
   - HTTPS only in production

3. **File Upload**
   - Validate file type by content, not just extension
   - Scan for malware (optional)
   - Limit file size

4. **SQL Injection**
   - Use SQLAlchemy ORM (parameterized queries)
   - Never concatenate user input into queries

5. **CORS**
   - Restrict to known frontend origins
   - Don't use wildcard (*) in production

### Deployment Checklist

1. Set all environment variables in .env
2. Generate secure SECRET_KEY
3. Configure AWS credentials for S3
4. Set up PostgreSQL database
5. Set up Redis instance
6. Build Docker images
7. Run docker-compose up
8. Verify health checks pass
9. Test authentication flow
10. Test file upload flow
11. Monitor logs for errors
12. Set up monitoring/alerting

## Conclusion

This design addresses the core issues in the backend-frontend integration by:
1. Fixing database configuration with proper URL encoding
2. Standardizing API routes and error responses
3. Ensuring proper CORS configuration
4. Implementing robust error handling
5. Adding comprehensive testing strategy
6. Documenting all critical fixes needed

The implementation will follow the task list to systematically fix each issue and verify proper integration between all components.
