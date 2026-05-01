# Live Meeting Feature - Run Commands

## Prerequisites

- Python 3.10+ installed
- Node.js 18+ installed
- PostgreSQL running
- Virtual environment: `venv_local`

## Starting the System

### Terminal 1: Start Backend

```bash
# Activate virtual environment
. venv_local/Scripts/Activate.ps1

# Start backend server
python backend/start_server.py
```

**Expected Output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [xxxxx] using WatchFiles
```

### Terminal 2: Start Frontend

```bash
# Navigate to frontend directory
cd frontend

# Start development server
npm run dev
```

**Expected Output:**
```
> ai-meeting-frontend@1.0.0 dev
> next dev
▲ Next.js 14.2.35
- Local:        http://localhost:3000 ✓
✓ Ready in 3.3s
```

## Accessing the Application

### Frontend
- **URL**: `http://localhost:3000`
- **Login**: Use your credentials

### Backend API
- **URL**: `http://localhost:8000`
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## Testing the Feature

### Quick Test (5 minutes)

1. Open `http://localhost:3000` in browser
2. Login with your credentials
3. Click the red "Live Meeting" button on dashboard
4. Enter a meeting title
5. Click "Start Meeting"
6. Grant browser permissions
7. Select a tab to capture audio
8. Speak or play audio
9. See real-time transcript
10. Click "Download Transcript"
11. Click "End Meeting"

### Full Test (30 minutes)

See `LIVE_MEETING_TEST_GUIDE.md` for comprehensive testing.

## Useful Commands

### Backend Commands

```bash
# Activate virtual environment
. venv_local/Scripts/Activate.ps1

# Install dependencies
pip install -r backend/requirements.txt

# Run backend
python backend/start_server.py

# Run with specific port
python backend/start_server.py --port 8001

# Check if port is in use
netstat -ano | findstr :8000

# Kill process on port 8000
taskkill /PID {pid} /F
```

### Frontend Commands

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Start production server
npm start

# Run linter
npm run lint

# Format code
npm run format
```

### Database Commands

```bash
# Connect to PostgreSQL
psql -U {user} -d ai_meeting

# List all tables
\dt

# View live_sessions table
SELECT * FROM live_sessions;

# View speakers table
SELECT * FROM speakers;

# View meetings table
SELECT * FROM meetings;

# View transcripts table
SELECT * FROM transcripts;

# Count records
SELECT COUNT(*) FROM live_sessions;
```

### Git Commands (When Ready)

```bash
# Check status
git status

# Add all changes
git add .

# Commit changes
git commit -m "feat: Add live meeting capture feature"

# Push to GitHub
git push origin main
```

## Stopping Services

### Stop Backend
```bash
# Press Ctrl+C in the backend terminal
```

### Stop Frontend
```bash
# Press Ctrl+C in the frontend terminal
```

### Stop PostgreSQL (if running locally)
```bash
# Windows
net stop PostgreSQL

# Or use Services app
```

## Troubleshooting Commands

### Check Python Version
```bash
python --version
```

### Check Node Version
```bash
node --version
npm --version
```

### Check if Ports are in Use
```bash
# Check port 8000
netstat -ano | findstr :8000

# Check port 3000
netstat -ano | findstr :3000

# Check port 5432 (PostgreSQL)
netstat -ano | findstr :5432
```

### Clear Cache and Reinstall

```bash
# Frontend
cd frontend
rm -r node_modules .next
npm install
npm run dev

# Backend
pip install --upgrade pip
pip install -r backend/requirements.txt
python backend/start_server.py
```

### View Logs

```bash
# Backend logs are printed to terminal

# Frontend logs are in browser console (F12)

# PostgreSQL logs (Windows)
# C:\Program Files\PostgreSQL\{version}\data\log\
```

## Environment Variables

### Backend (.env)
```
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_NAME=ai_meeting
DB_HOST=localhost
DB_PORT=5433
GROQ_API_KEY=your_groq_api_key
SECRET_KEY=your-secret-key
```

### Frontend (.env.local)
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Development Workflow

### 1. Start Services
```bash
# Terminal 1
. venv_local/Scripts/Activate.ps1
python backend/start_server.py

# Terminal 2
cd frontend
npm run dev
```

### 2. Make Changes
- Edit backend files → Auto-reload
- Edit frontend files → Auto-reload

### 3. Test Changes
- Backend: `http://localhost:8000/docs`
- Frontend: `http://localhost:3000`

### 4. Check Logs
- Backend: Terminal output
- Frontend: Browser console (F12)

### 5. Commit Changes
```bash
git add .
git commit -m "Your message"
```

## Performance Monitoring

### Backend Performance
```bash
# Check memory usage
# Task Manager → Python process

# Check CPU usage
# Task Manager → Python process

# Check response times
# Browser DevTools → Network tab
```

### Frontend Performance
```bash
# Open DevTools (F12)
# Go to Performance tab
# Record and analyze
```

### Database Performance
```bash
# Check query performance
# PostgreSQL logs

# Check table sizes
SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) 
FROM pg_tables 
WHERE schemaname != 'pg_catalog' 
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

## Deployment Commands (Future)

```bash
# Build Docker image
docker build -t ai-meeting-backend -f backend/Dockerfile .

# Run Docker container
docker run -p 8000:8000 ai-meeting-backend

# Docker Compose
docker-compose up -d

# Stop Docker Compose
docker-compose down
```

## Useful Aliases (Optional)

Add to PowerShell profile:
```powershell
# Start backend
function Start-Backend {
    . venv_local/Scripts/Activate.ps1
    python backend/start_server.py
}

# Start frontend
function Start-Frontend {
    cd frontend
    npm run dev
}

# Start both
function Start-All {
    Start-Backend &
    Start-Frontend
}
```

## Quick Reference

| Task | Command |
|------|---------|
| Start Backend | `. venv_local/Scripts/Activate.ps1` then `python backend/start_server.py` |
| Start Frontend | `cd frontend` then `npm run dev` |
| Access Frontend | `http://localhost:3000` |
| Access Backend | `http://localhost:8000` |
| API Docs | `http://localhost:8000/docs` |
| Check Port 8000 | `netstat -ano \| findstr :8000` |
| Kill Port 8000 | `taskkill /PID {pid} /F` |
| Install Backend Deps | `pip install -r backend/requirements.txt` |
| Install Frontend Deps | `npm install` |
| View Backend Logs | Terminal output |
| View Frontend Logs | Browser console (F12) |

## Common Issues & Solutions

### Port Already in Use
```bash
# Find process using port
netstat -ano | findstr :8000

# Kill process
taskkill /PID {pid} /F

# Restart service
python backend/start_server.py
```

### Module Not Found
```bash
# Reinstall dependencies
pip install -r backend/requirements.txt
npm install
```

### Database Connection Error
```bash
# Check PostgreSQL is running
# Verify connection string in .env
# Check database exists
```

### WebSocket Connection Failed
```bash
# Check backend is running
# Check firewall settings
# Check browser console for errors
```

## Next Steps

1. ✅ Start both services
2. ✅ Test the feature
3. ✅ Verify functionality
4. ✅ Check logs
5. ✅ Provide feedback
6. ⏳ Push to GitHub (when ready)

---

**Version**: 1.0.0
**Last Updated**: April 24, 2026
**Status**: Ready to Use
