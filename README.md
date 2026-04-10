# AI Meeting Intelligence Platform

A production-ready AI meeting intelligence platform that converts meeting recordings into structured insights using advanced AI models.

## Features

✨ **Core Features**
- 🎙️ Auto Speech-to-Text Transcription (Whisper)
- 👥 Speaker Diarization
- 📝 AI-Generated Summaries
- ✅ Action Item Extraction
- 🔍 Semantic Search on Transcripts
- 🎯 Key Discussion Points
- 📊 Sentiment Analysis
- ⚡ Asynchronous Processing
- 🔐 JWT Authentication
- 📱 Responsive UI
- 🐳 Docker Ready

## Tech Stack

**Backend**
- FastAPI (Python web framework)
- PostgreSQL (Database)
- SQLAlchemy (ORM)
- Celery + Redis (Async processing)
- Whisper (Speech-to-text)
- Sentence Transformers (Embeddings)
- Mistral/LLaMA API (AI summaries)

**Frontend**
- Next.js 14 (React framework)
- TypeScript
- Tailwind CSS
- Axios (HTTP client)
- React Icons
- React Dropzone

**Infrastructure**
- Docker & Docker Compose
- PostgreSQL
- Redis
- AWS S3

## Project Structure

```
ai-meeting/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models/
│   │   ├── services/
│   │   ├── routes/
│   │   ├── schemas/
│   │   ├── utils/
│   │   └── workers/
│   ├── requirements.txt
│   ├── Dockerfile
│   └── Dockerfile.worker
├── frontend/
│   ├── app/
│   ├── components/
│   ├── services/
│   ├── package.json
│   ├── tailwind.config.js
│   └── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

## Quick Start

### Prerequisites

- Docker & Docker Compose
- OR Python 3.11+ and Node.js 18+
- AWS Account (for S3)

### Option 1: Docker (Recommended)

1. Clone repository
```bash
cd ai-meeting
```

2. Create .env file
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Start services
```bash
docker-compose up -d
```

4. Wait for services to start
```bash
# Check services
docker-compose ps

# View logs
docker-compose logs -f backend
```

5. Access application
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Option 2: Local Development

**Backend Setup**

```bash
# Navigate to backend
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp ../.env.example .env

# Run migrations (if using Alembic)
# alembic upgrade head

# Start FastAPI
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Celery Worker**

```bash
# In another terminal
cd backend
source venv/bin/activate
celery -A app.workers.celery_config worker --loglevel=info
```

**Frontend Setup**

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Create .env.local
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

# Start development server
npm run dev
```

Access frontend at http://localhost:3000

## Database Setup

### Using Docker

Database is automatically initialized with docker-compose.

### Manual Setup

```bash
# Connect to PostgreSQL
psql -U aiuser -d ai_meeting -h localhost

# Run migrations
cd backend
alembic upgrade head
```

## API Documentation

### Authentication

**Register**
```bash
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123",
  "full_name": "John Doe"
}
```

**Login**
```bash
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123"
}

# Response
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### Meetings

**Upload Meeting**
```bash
POST /api/v1/meetings/upload
Authorization: Bearer {token}
Content-Type: multipart/form-data

Parameters:
- title: string (required)
- file: file (required) - audio file (WAV, MP3, M4A, MP4)
- description: string (optional)
```

**List Meetings**
```bash
GET /api/v1/meetings?skip=0&limit=20
Authorization: Bearer {token}
```

**Get Meeting Details**
```bash
GET /api/v1/meetings/{meeting_id}
Authorization: Bearer {token}
```

**Update Meeting**
```bash
PUT /api/v1/meetings/{meeting_id}
Authorization: Bearer {token}
Content-Type: application/json

{
  "title": "Updated Title",
  "description": "Updated description"
}
```

**Delete Meeting**
```bash
DELETE /api/v1/meetings/{meeting_id}
Authorization: Bearer {token}
```

### Transcripts

**Get Transcript**
```bash
GET /api/v1/meetings/{meeting_id}/transcript
Authorization: Bearer {token}
```

**Get Summary**
```bash
GET /api/v1/meetings/{meeting_id}/summary
Authorization: Bearer {token}
```

**Search Transcript**
```bash
GET /api/v1/meetings/{meeting_id}/search?q=deadline&top_k=5
Authorization: Bearer {token}
```

## Configuration

### Whisper Model Options

```
- tiny   (39M) - Fastest
- base   (74M) - Default, good balance
- small  (244M)
- medium (769M)
- large  (1550M) - Most accurate
```

### Environment Variables

**Backend**
```
DATABASE_URL=postgresql://user:password@localhost:5432/db
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-secret-key
WHISPER_MODEL=base
DEVICE=cpu  # or cuda for GPU
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
S3_BUCKET_NAME=your-bucket
DEBUG=False
```

**Frontend**
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Performance Optimization

### Processing Pipeline

1. **Audio Chunking**: Splits large files (up to 2 hours) into 5-minute chunks
2. **Parallel Transcription**: Processes multiple chunks simultaneously
3. **Async Processing**: Celery workers handle heavy lifting off the main thread
4. **Caching**: Redis caches frequently accessed data
5. **Vector Search**: pgvector provides efficient semantic search

### Target Performance
- 2-hour audio: ~10 minutes processing time
- Transcript search: <1 second response time
- Concurrent uploads: Unlimited (with queue management)

## Security Features

- ✅ JWT token authentication
- ✅ Rate limiting (100 requests/hour)
- ✅ File type validation
- ✅ File size limits (2GB max)
- ✅ SQL injection prevention (SQLAlchemy ORM)
- ✅ CORS protection
- ✅ Secure password hashing (bcrypt)

## Monitoring & Logging

### View Logs

```bash
# Backend logs
docker-compose logs -f backend

# Celery worker logs
docker-compose logs -f celery

# Frontend logs
docker-compose logs -f frontend

# Database logs
docker-compose logs -f postgres
```

### Health Checks

All services have built-in health checks:

```bash
# Check service health
curl http://localhost:8000/health
curl http://localhost:3000/health
```

## Troubleshooting

### Out of Memory

If processing large files fails:
1. Reduce `CELERY_CONCURRENCY` (default 2)
2. Use smaller Whisper model
3. Increase container memory limit

### CUDA/GPU Issues

```bash
# CPU-only mode
DEVICE=cpu docker-compose up -d

# GPU mode (requires NVIDIA Docker)
DEVICE=cuda docker-compose up -d
```

### Database Connection

```bash
# Test connection
docker-compose exec postgres psql -U aiuser -d ai_meeting -c "SELECT 1"

# Check logs
docker-compose logs postgres
```

## API Examples

### Complete Workflow

```bash
# 1. Register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123",
    "full_name": "John Doe"
  }'

# 2. Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123"
  }' | jq -r '.access_token')

# 3. Upload meeting
curl -X POST http://localhost:8000/api/v1/meetings/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "title=Team Meeting" \
  -F "file=@meeting.wav" \
  -F "description=Q4 Planning"

# 4. Get meetings (wait for processing)
curl -X GET http://localhost:8000/api/v1/meetings \
  -H "Authorization: Bearer $TOKEN"

# 5. Get transcript
curl -X GET http://localhost:8000/api/v1/meetings/1/transcript \
  -H "Authorization: Bearer $TOKEN"

# 6. Get summary
curl -X GET http://localhost:8000/api/v1/meetings/1/summary \
  -H "Authorization: Bearer $TOKEN"

# 7. Search
curl -X GET "http://localhost:8000/api/v1/meetings/1/search?q=deadline&top_k=5" \
  -H "Authorization: Bearer $TOKEN"
```

## Bonus Features

### Real-time Progress
The processing pipeline provides real-time progress updates through Celery task states.

### Sentiment Analysis
Automatically analyzes meeting tone (positive/neutral/negative).

### PDF Export
Generate meeting notes as PDF (can be added via additional endpoints).

## Development

### Add New API Endpoint

1. Create schema in `app/schemas/`
2. Create route in `app/routers/`
3. Add route to `app/main.py`

### Add New Worker Task

1. Define task in `app/workers/tasks.py`
2. Use `@celery_app.task` decorator

### Extend Frontend

Components are located in `frontend/components/`

## Production Deployment

### Prerequisites
- AWS S3 bucket
- RDS PostgreSQL database
- ElastiCache Redis
- EC2 or ECS for containers

### Deployment Steps

1. **Environment Setup**
```bash
# Create production .env
export DATABASE_URL=production_db_url
export REDIS_URL=production_redis_url
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export SECRET_KEY=production_secret_key
export DEBUG=False
```

2. **Build & Push Docker Images**
```bash
docker build -t ai-meeting-backend:latest ./backend
docker build -t ai-meeting-frontend:latest ./frontend
# Push to ECR/Docker Hub
```

3. **Deploy to AWS ECS**
```bash
# Update task definitions and deploy
aws ecs update-service --cluster ai-meeting --service backend --force-new-deployment
```

## Contributing

1. Fork repository
2. Create feature branch
3. Make changes
4. Submit pull request

## License

MIT License - See LICENSE file

## Support

For issues and questions:
- GitHub Issues
- Email: support@example.com

## Roadmap

- [ ] Real-time transcription
- [ ] Multi-language support
- [ ] Video transcription
- [ ] Calendar integration
- [ ] Slack notifications
- [ ] Email reports
- [ ] Meeting recordings storage
- [ ] Advanced analytics

---

Built with ❤️ for better meetings
