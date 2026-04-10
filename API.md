# API Documentation

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

All endpoints (except auth) require JWT bearer token in Authorization header:

```
Authorization: Bearer {access_token}
```

## Auth Endpoints

### Register User

Create a new user account.

**Request**
```
POST /auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "securepassword123",
  "full_name": "John Doe"
}
```

**Response (200)**
```json
{
  "id": 1,
  "email": "user@example.com",
  "full_name": "John Doe",
  "is_active": true,
  "created_at": "2024-01-15T10:30:00"
}
```

**Error Responses**
- `400`: Email already registered
- `422`: Validation error

---

### Login

Authenticate and receive access token.

**Request**
```
POST /auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response (200)**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": null,
  "token_type": "bearer",
  "expires_in": 1800
}
```

**Error Responses**
- `401`: Invalid credentials
- `403`: User account inactive

---

### Verify Token

Verify JWT token validity.

**Request**
```
POST /auth/verify-token
Content-Type: application/json

{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response (200)**
```json
{
  "valid": true,
  "user_id": 1,
  "email": "user@example.com"
}
```

**Error Responses**
- `401`: Invalid token

---

## Meeting Endpoints

### Upload Meeting

Upload audio file for processing.

**Request**
```
POST /meetings/upload
Authorization: Bearer {token}
Content-Type: multipart/form-data

Parameters:
- title: string (required) - Meeting title
- file: file (required) - Audio file (WAV, MP3, M4A, MP4)
- description: string (optional) - Meeting description
```

**Response (200)**
```json
{
  "id": 1,
  "user_id": 1,
  "title": "Q4 Planning Meeting",
  "description": "Quarterly planning session",
  "audio_url": "s3://ai-meeting-bucket/meetings/1/audio.wav",
  "duration": 3600.0,
  "status": "pending",
  "created_at": "2024-01-15T10:30:00",
  "updated_at": "2024-01-15T10:30:00"
}
```

**Error Responses**
- `400`: Unsupported format or file too large
- `401`: Unauthorized
- `500`: Upload failed

---

### List Meetings

Get all meetings for current user.

**Request**
```
GET /meetings?skip=0&limit=20
Authorization: Bearer {token}

Query Parameters:
- skip: integer (default 0) - Number of items to skip
- limit: integer (default 20) - Number of items to return (max 100)
```

**Response (200)**
```json
[
  {
    "id": 1,
    "title": "Q4 Planning Meeting",
    "status": "completed",
    "duration": 3600.0,
    "created_at": "2024-01-15T10:30:00"
  },
  {
    "id": 2,
    "title": "Team Sync",
    "status": "processing",
    "duration": 1800.0,
    "created_at": "2024-01-15T11:00:00"
  }
]
```

---

### Get Meeting

Get specific meeting details.

**Request**
```
GET /meetings/{meeting_id}
Authorization: Bearer {token}

Path Parameters:
- meeting_id: integer - Meeting ID
```

**Response (200)**
```json
{
  "id": 1,
  "user_id": 1,
  "title": "Q4 Planning Meeting",
  "description": "Quarterly planning session",
  "audio_url": "s3://ai-meeting-bucket/meetings/1/audio.wav",
  "duration": 3600.0,
  "status": "completed",
  "created_at": "2024-01-15T10:30:00",
  "updated_at": "2024-01-15T11:30:00"
}
```

**Error Responses**
- `401`: Unauthorized
- `404`: Meeting not found

---

### Update Meeting

Update meeting details.

**Request**
```
PUT /meetings/{meeting_id}
Authorization: Bearer {token}
Content-Type: application/json

{
  "title": "Updated Title",
  "description": "Updated description"
}
```

**Response (200)**
```json
{
  "id": 1,
  "user_id": 1,
  "title": "Updated Title",
  "description": "Updated description",
  "audio_url": "s3://ai-meeting-bucket/meetings/1/audio.wav",
  "duration": 3600.0,
  "status": "completed",
  "created_at": "2024-01-15T10:30:00",
  "updated_at": "2024-01-15T12:00:00"
}
```

---

### Delete Meeting

Delete a meeting and associated data.

**Request**
```
DELETE /meetings/{meeting_id}
Authorization: Bearer {token}
```

**Response (200)**
```json
{
  "message": "Meeting deleted successfully"
}
```

---

## Transcript Endpoints

### Get Full Transcript

Get all transcript segments for a meeting.

**Request**
```
GET /meetings/{meeting_id}/transcript
Authorization: Bearer {token}
```

**Response (200)**
```json
{
  "meeting_id": 1,
  "segments": [
    {
      "id": 1,
      "meeting_id": 1,
      "speaker": "Speaker 1",
      "text": "Good morning everyone, welcome to the meeting",
      "start_time": 0.0,
      "end_time": 3.5,
      "created_at": "2024-01-15T11:30:00"
    },
    {
      "id": 2,
      "meeting_id": 1,
      "speaker": "Speaker 2",
      "text": "Thank you for joining. Let's start with the agenda.",
      "start_time": 3.5,
      "end_time": 8.2,
      "created_at": "2024-01-15T11:30:00"
    }
  ],
  "total_duration": 3600.0
}
```

**Error Responses**
- `401`: Unauthorized
- `404`: Meeting not found

---

### Get Summary

Get AI-generated summary and insights for a meeting.

**Request**
```
GET /meetings/{meeting_id}/summary
Authorization: Bearer {token}
```

**Response (200)**
```json
{
  "id": 1,
  "meeting_id": 1,
  "summary": "The Q4 planning meeting covered strategic initiatives including product roadmap, team expansion plans, and budget allocation. Key decisions were made on feature priorities.",
  "key_points": [
    "Product roadmap approved for Q4",
    "Team expansion budget increased by 20%",
    "New customer acquisition strategy discussed",
    "Timeline for feature releases finalized"
  ],
  "action_items": [
    {
      "task": "Prepare detailed product roadmap",
      "owner": "Product Manager",
      "due_date": "End of week"
    },
    {
      "task": "Submit hiring requirements",
      "owner": "HR Manager",
      "due_date": "Next Monday"
    },
    {
      "task": "Schedule customer interviews",
      "owner": "Sales Lead",
      "due_date": "Next two weeks"
    }
  ],
  "sentiment": "positive",
  "created_at": "2024-01-15T11:35:00",
  "updated_at": "2024-01-15T11:35:00"
}
```

**Error Responses**
- `401`: Unauthorized
- `404`: Meeting or summary not found
- `404`: Summary not available yet (still processing)

---

### Search Transcript

Search transcript segments using semantic search.

**Request**
```
GET /meetings/{meeting_id}/search?q=deadline&top_k=5
Authorization: Bearer {token}

Query Parameters:
- q: string (required) - Search query
- top_k: integer (default 5) - Number of top results (1-50)
```

**Response (200)**
```json
{
  "query": "deadline",
  "results": [
    {
      "transcript_id": 5,
      "speaker": "Speaker 1",
      "text": "We need to finalize the deadline for the Q4 launch by next Friday.",
      "start_time": 125.5,
      "end_time": 132.3,
      "relevance_score": 0.92
    },
    {
      "transcript_id": 8,
      "speaker": "Speaker 2",
      "text": "The deadline for submissions is December 31st.",
      "start_time": 245.0,
      "end_time": 250.5,
      "relevance_score": 0.88
    }
  ],
  "total_results": 2
}
```

**Error Responses**
- `401`: Unauthorized
- `404`: Meeting not found
- `422`: Query validation error

---

## Status Codes

| Code | Meaning |
|------|---------|
| 200 | OK - Request successful |
| 201 | Created - Resource created |
| 400 | Bad Request - Invalid parameters |
| 401 | Unauthorized - Missing/invalid token |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource not found |
| 422 | Unprocessable Entity - Validation error |
| 500 | Internal Server Error - Server error |

---

## Error Response Format

```json
{
  "detail": "Error message describing what went wrong"
}
```

---

## Rate Limiting

API Rate limit: 100 requests per hour per user

Response headers indicate rate limit status:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1705330800
```

---

## Pagination

List endpoints support pagination:

```
GET /meetings?skip=0&limit=20
```

- `skip`: Number of items to skip (default: 0)
- `limit`: Number of items per page (default: 20, max: 100)

---

## WebSocket Support (Future)

Real-time processing updates available via WebSocket:

```
ws://localhost:8000/ws/meetings/{meeting_id}
```

---

## Complete Example Flow

```bash
# 1. Register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "MySecurePassword123!",
    "full_name": "Jane Smith"
  }'

# 2. Login
ACCESS_TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "MySecurePassword123!"
  }' | jq -r '.access_token')

# 3. Upload meeting
MEETING_ID=$(curl -s -X POST http://localhost:8000/api/v1/meetings/upload \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "title=Team Standup" \
  -F "file=@meeting.wav" \
  -F "description=Daily team sync" | jq -r '.id')

# 4. Check status (wait for processing)
curl -X GET http://localhost:8000/api/v1/meetings/$MEETING_ID \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq .

# 5. Get transcript
curl -X GET http://localhost:8000/api/v1/meetings/$MEETING_ID/transcript \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq .

# 6. Get summary
curl -X GET http://localhost:8000/api/v1/meetings/$MEETING_ID/summary \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq .

# 7. Search
curl -X GET "http://localhost:8000/api/v1/meetings/$MEETING_ID/search?q=deadline&top_k=5" \
  -H "Authorization: Bearer $ACCESS_TOKEN" | jq .
```

---

## Using cURL with JSON

Common headers:
```bash
-H "Content-Type: application/json" \
-H "Authorization: Bearer {access_token}"
```

Parse JSON response:
```bash
| jq .              # Pretty print
| jq '.field'       # Extract field
| jq '.[] | .field' # Extract from array
```

---

## Using Postman

1. Create new collection
2. Set base URL: `http://localhost:8000/api/v1`
3. Add Authorization variable: `{access_token}`
4. Set pre-request script to refresh token if needed

---

For more information, see the Interactive API docs at:
`http://localhost:8000/docs`
