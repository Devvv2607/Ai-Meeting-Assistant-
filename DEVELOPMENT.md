# Local Development Guide

## Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 15
- Redis 7
- Git

## Backend Development Setup

### 1. Install Python Dependencies

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Setup Database

```bash
# Ensure PostgreSQL is running
# Edit DATABASE_URL in .env if using different credentials

# Create database
createdb -U aiuser ai_meeting
```

### 3. Configure Environment

```bash
# Copy example env
cp ../.env.example .env

# Edit .env with your local settings
```

### 4. Run Backend

```bash
# Activate venv
source venv/bin/activate

# Start FastAPI
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The backend will be available at http://localhost:8000

API documentation will be available at http://localhost:8000/docs

### 5. Run Celery Worker (in another terminal)

```bash
# Activate venv
source venv/bin/activate

# Start Celery worker
celery -A app.workers.celery_config worker --loglevel=info
```

## Frontend Development Setup

### 1. Install Node Dependencies

```bash
cd frontend

# Install dependencies
npm install
```

### 2. Configure Environment

```bash
# Create environment file
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
```

### 3. Run Frontend

```bash
# Start development server
npm run dev

# Frontend will be available at http://localhost:3000
```

## Running Redis

### Option 1: Using Docker

```bash
docker run -d --name redis -p 6379:6379 redis:7-alpine
```

### Option 2: Install Locally

**macOS (Homebrew)**
```bash
brew install redis
brew services start redis
```

**Linux (Ubuntu)**
```bash
sudo apt-get install redis-server
sudo systemctl start redis-server
```

**Windows**
- Download from https://github.com/microsoftarchive/redis/releases
- Or use WSL with Linux instructions above

## Testing the System

### 1. Create Test User

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpassword123",
    "full_name": "Test User"
  }'
```

### 2. Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpassword123"
  }'

# Save the access_token
```

### 3. Create Sample Audio File

```bash
# Create a simple audio file for testing (5 seconds of silence)
ffmpeg -f lavfi -i anullsrc=r=16000:cl=mono -t 5 -q:a 9 -acodec libmp3lame test_audio.mp3
```

### 4. Upload Meeting

```bash
TOKEN="your_access_token_here"

curl -X POST http://localhost:8000/api/v1/meetings/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "title=Test Meeting" \
  -F "file=@test_audio.mp3" \
  -F "description=A test meeting"
```

### 5. Monitor Processing

```bash
# Check meeting list
curl -X GET http://localhost:8000/api/v1/meetings \
  -H "Authorization: Bearer $TOKEN"

# Get specific meeting
curl -X GET http://localhost:8000/api/v1/meetings/1 \
  -H "Authorization: Bearer $TOKEN"

# Check transcript (after processing)
curl -X GET http://localhost:8000/api/v1/meetings/1/transcript \
  -H "Authorization: Bearer $TOKEN"

# Get summary
curl -X GET http://localhost:8000/api/v1/meetings/1/summary \
  -H "Authorization: Bearer $TOKEN"
```

## Debug Mode

### Enable Debug Logging

```bash
# Backend
DEBUG=True uvicorn app.main:app --reload

# Frontend
npm run dev
```

### View Database Queries

```bash
# Edit app/database.py and change:
# echo=settings.DEBUG to echo=True
```

### Watch Celery Tasks

```bash
# In another terminal
celery -A app.workers.celery_config events

# Or with Flower web UI
pip install flower
celery -A app.workers.celery_config flower
# Visit http://localhost:5555
```

## VS Code Setup

### Extensions

- Python
- Pylance
- FastAPI
- ES7+ React/Redux/React-Native snippets
- Tailwind CSS IntelliSense
- Thunder Client (for API testing)

### Debug Configuration

Create `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": ["app.main:app", "--reload"],
      "jinja": true,
      "cwd": "${workspaceFolder}/backend"
    }
  ]
}
```

## Common Issues

### Port Already in Use

```bash
# Find process using port
lsof -i :8000  # Backend
lsof -i :3000  # Frontend
lsof -i :5432 # PostgreSQL
lsof -i :6379 # Redis

# Kill process
kill -9 <PID>
```

### PostgreSQL Connection Error

```bash
# Check if PostgreSQL is running
psql -U aiuser -d ai_meeting -c "SELECT 1"

# If not installed, install it or use Docker
```

### Redis Connection Error

```bash
# Check if Redis is running
redis-cli ping

# Should return: PONG
```

### Module Not Found

```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Clear Python cache
find . -type d -name __pycache__ -exec rm -r {} +
```

### CUDA/GPU Issues

```bash
# Use CPU only
export DEVICE=cpu
```

## Database Management

### View Database

```bash
psql -U aiuser -d ai_meeting

# Useful commands
\dt              # List tables
\d meetings      # Describe table
SELECT * FROM users;
```

### Reset Database

```bash
# Drop and recreate
dropdb -U aiuser ai_meeting
createdb -U aiuser ai_meeting

# Recreate tables
python -c "from app.database import Base, engine; Base.metadata.create_all(bind=engine)"
```

## Performance Testing

### Load Testing Backend

```bash
pip install locust

# Create locustfile.py and run tests
locust -f locustfile.py -u 100 -r 10 -t 5m --headless -H http://localhost:8000
```

### Monitor Resources

```bash
# View Docker stats
docker stats

# View system resources
top
```

## Git Workflow

```bash
# Create feature branch
git checkout -b feature/new-feature

# Make changes
git add .

# Commit
git commit -m "Add new feature"

# Push
git push origin feature/new-feature

# Create pull request
```

## Code Style

### Python (Backend)

```bash
# Install formatter
pip install black isort flake8

# Format code
black app/
isort app/

# Lint
flake8 app/
```

### TypeScript (Frontend)

```bash
# Lint
npm run lint

# Fix
npm run lint -- --fix
```

## Useful Commands

```bash
# View all routes
curl http://localhost:8000/openapi.json | jq .

# Test health
curl http://localhost:8000/health

# Watch logs
docker-compose logs -f

# Restart services
docker-compose restart

# Clean up
docker-compose down -v
```

## Next Steps

1. ✅ Backend and frontend are running
2. ✅ Test with sample audio files
3. ✅ Explore the API documentation at http://localhost:8000/docs
4. ✅ Build new features
5. ✅ Deploy to production

For more details, see the main README.md
