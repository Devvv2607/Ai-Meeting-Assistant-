# AI Meeting Intelligence Platform - Setup Instructions

## 📋 Quick Start

### Getting Started in 5 Minutes (Docker)

```bash
# 1. Clone/navigate to project
cd ai-meeting

# 2. Setup environment
cp .env.example .env
# Edit .env with your configuration

# 3. Start all services
docker-compose up -d

# 4. Wait for services to start
docker-compose ps

# 5. Access application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Getting Started Locally (Without Docker)

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

**Workers:**
```bash
cd backend
source venv/bin/activate
celery -A app.workers.celery_config worker --loglevel=info
```

## 📁 Project Contents

### Backend Files
- `backend/app/main.py` - FastAPI application entry point
- `backend/app/config.py` - Configuration settings
- `backend/app/database.py` - Database setup
- `backend/app/models/` - Database models (User, Meeting, Transcript, Summary)
- `backend/app/services/` - Core services (Whisper, LLM, Embeddings, Audio Processing)
- `backend/app/routers/` - API routes (Auth, Meetings, Transcripts)
- `backend/app/workers/` - Celery tasks and configuration
- `backend/requirements.txt` - Python dependencies
- `backend/Dockerfile` - Backend container
- `backend/Dockerfile.worker` - Celery worker container

### Frontend Files
- `frontend/app/` - Next.js app directory
- `frontend/app/login/page.tsx` - Login page
- `frontend/app/register/page.tsx` - Registration page
- `frontend/app/dashboard/page.tsx` - Dashboard listing meetings
- `frontend/app/upload/page.tsx` - Upload meeting page
- `frontend/app/meeting/[id]/page.tsx` - Meeting detail page
- `frontend/components/` - React components
  - `AudioUpload.tsx` - Drag-drop file upload
  - `TranscriptViewer.tsx` - Transcript display with sync
  - `SummaryPanel.tsx` - Summary and action items
  - `SearchBar.tsx` - Semantic search
- `frontend/services/api.ts` - API client
- `frontend/tailwind.config.js` - Tailwind CSS config
- `frontend/package.json` - Node.js dependencies

### Configuration Files
- `docker-compose.yml` - Multi-container setup
- `.env.example` - Environment variables template
- `README.md` - Main documentation
- `DEVELOPMENT.md` - Local development guide
- `API.md` - API documentation
- `DEPLOYMENT.md` - Production deployment guide

## 🔑 Key Features

### ✅ Implemented
- [x] User authentication (Register/Login/JWT)
- [x] Meeting upload (WAV, MP3, M4A, MP4)
- [x] Async processing pipeline
- [x] Whisper transcription
- [x] Speaker diarization (placeholder)
- [x] AI summaries and action items
- [x] Semantic search on transcripts
- [x] Responsive UI
- [x] Database with PostgreSQL
- [x] Redis caching
- [x] Celery async workers
- [x] Docker support

### 🚀 Quick Features (Can Be Added)
- [ ] Real-time transcription progress
- [ ] PDF export
- [ ] Email notifications
- [ ] Slack integration
- [ ] Calendar integration
- [ ] Advanced sentiment analysis
- [ ] Multi-language support

## 📊 Database Schema

### Users Table
```sql
CREATE TABLE users (
  id SERIAL PRIMARY KEY,
  email VARCHAR UNIQUE,
  password_hash VARCHAR,
  full_name VARCHAR,
  is_active BOOLEAN,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);
```

### Meetings Table
```sql
CREATE TABLE meetings (
  id SERIAL PRIMARY KEY,
  user_id INTEGER,
  title VARCHAR,
  description VARCHAR,
  audio_url VARCHAR,
  duration FLOAT,
  status ENUM,
  celery_task_id VARCHAR,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);
```

### Transcripts Table
```sql
CREATE TABLE transcripts (
  id SERIAL PRIMARY KEY,
  meeting_id INTEGER,
  speaker VARCHAR,
  text VARCHAR,
  start_time FLOAT,
  end_time FLOAT,
  embedding BYTEA,
  created_at TIMESTAMP
);
```

### Summaries Table
```sql
CREATE TABLE summaries (
  id SERIAL PRIMARY KEY,
  meeting_id INTEGER UNIQUE,
  summary VARCHAR,
  key_points JSON,
  action_items JSON,
  sentiment VARCHAR,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);
```

## 🔌 API Endpoints Summary

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/v1/auth/register` | Register user |
| POST | `/api/v1/auth/login` | Login user |
| POST | `/api/v1/meetings/upload` | Upload meeting |
| GET | `/api/v1/meetings` | List meetings |
| GET | `/api/v1/meetings/{id}` | Get meeting |
| GET | `/api/v1/meetings/{id}/transcript` | Get transcript |
| GET | `/api/v1/meetings/{id}/summary` | Get summary |
| GET | `/api/v1/meetings/{id}/search?q=` | Search transcript |

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Next.js Frontend                      │
│              (TypeScript + React)                       │
└────────────────────┬────────────────────────────────────┘
                     │ HTTP/REST
┌────────────────────▼────────────────────────────────────┐
│                   FastAPI Backend                       │
│         (Auth, Upload, Transcript, Search API)         │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
┌───────▼───────┐   │   ┌────────▼──────┐
│  PostgreSQL   │   │   │ Celery Queue  │
│   Database    │   │   └────────┬──────┘
└───────────────┘   │            │
                    │   ┌────────▼──────────┐
                    │   │  Celery Workers  │
                    │   │ (Process Audio)  │
                    │   └────────┬─────────┘
                    │            │
        ┌───────────┼────────────┤
        │           │            │
   ┌────▼─────┐ ┌──▼────┐  ┌────▼─────┐
   │ Whisper  │ │  LLM  │  │Embeddings│
   │(Transcr.)│ │(Summary)  │(Search) │
   └──────────┘ └────────┘  └─────────┘
        │           │            │
        └───────────┼────────────┘
                    │
            ┌───────▼────────┐
            │   Redis Cache  │
            └────────────────┘
                    │
            ┌───────▼────────┐
            │   AWS S3       │
            │ (Audio Storage)│
            └────────────────┘
```

## 🛠️ Technology Stack

**Backend**
- Framework: FastAPI
- Database: PostgreSQL
- Cache: Redis
- Task Queue: Celery
- ORM: SQLAlchemy
- Auth: JWT + bcrypt
- AI Models: Whisper, Sentence Transformers, Mistral/LLaMA
- Storage: AWS S3

**Frontend**
- Framework: Next.js 14
- Language: TypeScript
- Styling: Tailwind CSS
- HTTP Client: Axios
- State: Zustand (ready to add)

**Infrastructure**
- Containerization: Docker
- Orchestration: Docker Compose
- Deployment: AWS ECS/Fargate
- Database: AWS RDS PostgreSQL
- Cache: AWS ElastiCache Redis
- CDN: CloudFront
- DNS: Route53

## 📝 Environment Variables

Required variables in `.env`:

```bash
# Database
DATABASE_URL=postgresql://aiuser:aipassword@localhost:5432/ai_meeting

# JWT
SECRET_KEY=your-super-secret-key
ALGORITHM=HS256

# AWS S3
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
S3_BUCKET_NAME=ai-meeting-bucket

# Model Settings
WHISPER_MODEL=base
DEVICE=cpu

# API
DEBUG=False
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## 📊 Performance Targets

- 2-hour audio processing: ~10 minutes
- Transcript search: <1 second
- API response time: <500ms
- Concurrent connections: Unlimited (with queue management)
- Max file size: 2GB

## 🔐 Security Features

- JWT authentication
- Rate limiting (100 req/hour)
- File validation
- SQL injection prevention
- CORS protection
- Bcrypt password hashing
- Secure S3 access

## 🔍 Monitoring & Logs

```bash
# View all logs
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f celery

# Health check
curl http://localhost:8000/health
curl http://localhost:3000
```

## 🚀 Deployment

### To AWS (Production)

See `DEPLOYMENT.md` for step-by-step instructions:

1. Create AWS infrastructure (RDS, ElastiCache, S3)
2. Build and push Docker images to ECR
3. Create ECS cluster
4. Deploy services
5. Configure load balancer
6. Set up SSL/TLS
7. Enable auto-scaling

## 📚 Documentation Files

- **README.md** - Main overview and setup
- **DEVELOPMENT.md** - Local development guide
- **API.md** - Complete API documentation
- **DEPLOYMENT.md** - Production deployment guide
- **.env.example** - Environment variables template

## 🧪 Testing the System

### Manual Test Flow

1. **Register User**
   ```bash
   curl -X POST http://localhost:8000/api/v1/auth/register \
     -H "Content-Type: application/json" \
     -d '{"email":"test@example.com","password":"test123","full_name":"Test User"}'
   ```

2. **Login**
   ```bash
   curl -X POST http://localhost:8000/api/v1/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email":"test@example.com","password":"test123"}'
   ```

3. **Upload Meeting**
   ```bash
   curl -X POST http://localhost:8000/api/v1/meetings/upload \
     -H "Authorization: Bearer {token}" \
     -F "title=Test Meeting" \
     -F "file=@sample_audio.wav"
   ```

4. **Check Status** (wait for processing)
   ```bash
   curl -X GET http://localhost:8000/api/v1/meetings/1 \
     -H "Authorization: Bearer {token}"
   ```

5. **Get Transcript**
   ```bash
   curl -X GET http://localhost:8000/api/v1/meetings/1/transcript \
     -H "Authorization: Bearer {token}"
   ```

6. **Get Summary**
   ```bash
   curl -X GET http://localhost:8000/api/v1/meetings/1/summary \
     -H "Authorization: Bearer {token}"
   ```

7. **Search**
   ```bash
   curl -X GET "http://localhost:8000/api/v1/meetings/1/search?q=keyword" \
     -H "Authorization: Bearer {token}"
   ```

## 📞 Support

For issues:
1. Check `DEVELOPMENT.md` troubleshooting section
2. Review Docker logs: `docker-compose logs`
3. Check database: `psql -U aiuser -d ai_meeting`
4. Verify services: `docker-compose ps`

## 📋 Next Steps

1. ✅ Setup local development environment
2. ✅ Test all features
3. ✅ Customize UI/branding
4. ✅ Add additional features (email, Slack, etc.)
5. ✅ Deploy to production (see DEPLOYMENT.md)
6. ✅ Monitor and optimize

## 🎉 You're All Set!

Your AI Meeting Intelligence Platform is ready to use!

### Quick Access

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Database**: localhost:5432
- **Redis**: localhost:6379

Start with tasks in this order:
1. Read README.md
2. Follow DEVELOPMENT.md
3. Test using API.md examples
4. Deploy using DEPLOYMENT.md

Enjoy building amazing meeting intelligence! 🚀
