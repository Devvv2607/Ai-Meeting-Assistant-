# Live Meeting Feature - Quick Test Guide

## System Status

✅ **Backend**: Running on `http://localhost:8000`
✅ **Frontend**: Running on `http://localhost:3000`
✅ **Database**: PostgreSQL connected
✅ **All Dependencies**: Installed

## Quick Start Testing

### Step 1: Access the Application
1. Open browser and go to `http://localhost:3000`
2. Login with your credentials (or register if needed)

### Step 2: Navigate to Dashboard
1. After login, you'll see the Dashboard
2. You should see 4 cards:
   - **Upload Meeting** (Blue)
   - **Live Meeting** (Red) ← NEW
   - **Summary** (Indigo)
   - **Insights** (Purple)

### Step 3: Start a Live Meeting
1. Click the red **"Live Meeting"** card
2. Enter a meeting title (e.g., "Test Meeting")
3. Click **"Start Meeting"** button
4. Browser will ask for permission to capture audio
5. Click **"Allow"** or **"Share"**
6. Select the browser tab you want to capture (or your screen)
7. Click **"Share"** to confirm

### Step 4: Test Real-Time Transcript
1. Once sharing starts, you'll see the live meeting page
2. The page shows:
   - Meeting title at top
   - Duration timer (red, top right)
   - Live transcript area (dark background)
   - Download and End buttons at bottom

3. To test transcription:
   - Play audio from YouTube, Spotify, or any tab
   - Or speak into your microphone
   - You should see real-time captions appearing

### Step 5: Download Transcript
1. Click **"Download Transcript"** button
2. A `.txt` file will be downloaded with:
   - Timestamps
   - Speaker labels
   - Transcript text

### Step 6: End Meeting
1. Click **"End Meeting"** button
2. System will:
   - Stop recording
   - Finalize transcript
   - Save to database
   - Redirect to meeting details page

### Step 7: View Meeting Details
1. You'll see the meeting details page with:
   - Full transcript
   - Summary (if generated)
   - Chat interface
   - Download options

## What to Look For

### ✅ Working Features
- [ ] Dashboard shows "Live Meeting" button
- [ ] Can start a live meeting with title
- [ ] Browser asks for audio permission
- [ ] Can select tab/screen to share
- [ ] Real-time transcript appears
- [ ] Speaker labels show (Speaker 1, Speaker 2, etc.)
- [ ] Duration timer counts up
- [ ] Can download transcript as TXT
- [ ] Can end meeting
- [ ] Meeting saved to database
- [ ] Can view meeting details

### 🔍 Things to Check
1. **WebSocket Connection**
   - Open browser DevTools (F12)
   - Go to Network tab
   - Filter by "WS" (WebSocket)
   - You should see a WebSocket connection to `/api/v1/meetings/live/{token}`

2. **Backend Logs**
   - Check terminal running backend
   - Should see logs like:
     ```
     INFO: Request: POST /api/v1/meetings/start-live
     INFO: WebSocket connected: {session_token}
     INFO: Processed chunk for session {token}: Speaker 1
     ```

3. **Frontend Console**
   - Open browser DevTools (F12)
   - Go to Console tab
   - Should see messages like:
     ```
     WebSocket connected
     Received transcript: ...
     ```

4. **Database**
   - Check PostgreSQL for new records in:
     - `meetings` table (new meeting)
     - `live_sessions` table (session record)
     - `transcripts` table (transcript segments)
     - `speakers` table (speaker info)

## Troubleshooting

### Issue: "Start Meeting" button doesn't work
**Solution**: 
- Check if you're logged in
- Check browser console for errors
- Verify backend is running

### Issue: No audio permission dialog
**Solution**:
- Check browser permissions
- Try a different browser
- Check if browser supports `getDisplayMedia()`

### Issue: Transcript not appearing
**Solution**:
- Check WebSocket connection in DevTools
- Check backend logs for errors
- Verify audio is actually playing
- Try speaking into microphone

### Issue: WebSocket disconnects
**Solution**:
- Check network connection
- Verify backend is still running
- Check for firewall issues
- Try refreshing the page

### Issue: Meeting not saved
**Solution**:
- Check database connection
- Verify PostgreSQL is running
- Check backend logs for database errors
- Ensure user is authenticated

## API Endpoints to Test

### 1. Start Live Meeting
```bash
curl -X POST "http://localhost:8000/api/v1/meetings/start-live?meeting_title=Test" \
  -H "Authorization: Bearer {your_token}"
```

Expected Response:
```json
{
  "meeting_id": 1,
  "session_token": "uuid-string",
  "status": "ACTIVE"
}
```

### 2. Get Live Status
```bash
curl -X GET "http://localhost:8000/api/v1/meetings/1/live-status?session_token={token}" \
  -H "Authorization: Bearer {your_token}"
```

### 3. End Live Meeting
```bash
curl -X POST "http://localhost:8000/api/v1/meetings/1/end?session_token={token}" \
  -H "Authorization: Bearer {your_token}"
```

## Performance Metrics to Monitor

- **Audio Chunk Size**: 3 seconds
- **WebSocket Latency**: Should be < 500ms
- **Transcription Time**: Should be < 2 seconds per chunk
- **Memory Usage**: Monitor in DevTools (should be < 200MB)
- **CPU Usage**: Should be reasonable (< 50%)

## Next Steps After Testing

1. **Verify all features work** ✓
2. **Check for any errors** ✓
3. **Test with different audio sources** ✓
4. **Test with multiple speakers** ✓
5. **Test long meetings (30+ minutes)** ✓
6. **Test reconnection** ✓
7. **Provide feedback** ✓

## Known Limitations (Phase 1)

- Speaker detection is simplified (not using pyannote.audio yet)
- No multilingual support yet
- No sentiment analysis
- No speaker renaming
- No advanced analytics
- No email notifications

These will be added in Phase 2.

## Support

If you encounter any issues:
1. Check the troubleshooting section above
2. Review backend logs
3. Check browser console
4. Verify all services are running
5. Check database connection

---

**Ready to Test**: ✅ Yes
**Last Updated**: April 24, 2026
**Version**: 1.0.0
