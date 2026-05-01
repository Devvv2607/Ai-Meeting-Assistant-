# Quick Fix Guide - Capture Your Voice in Google Meet

## The Problem
You were only getting the other person's voice in the transcript, not your own.

## The Solution
Use **"Screen Only"** mode and make sure you're **UNMUTED** in Google Meet!

## Step-by-Step Instructions

### 1. Start the Meeting
- Go to Live Meeting page
- Enter meeting title
- Select **"🖥️ Screen Only"** (NOT "Both")
- Click "Start Meeting"

### 2. Share Your Screen
When the browser asks to share:
- ✅ Select **"Entire Screen"** (NOT "Chrome Tab")
- ✅ Check the **"Share audio"** checkbox
- ✅ Click "Share"

### 3. During the Meeting
- ✅ **UNMUTE yourself in Google Meet** when you want to speak
- ✅ Speak normally
- ✅ Your voice will be captured along with others

### 4. End the Meeting
- Click "End Meeting"
- Wait for processing
- Check the transcript - both you and the other person should be there!

## Why This Works

**Google Meet's Echo Cancellation**:
- Google Meet removes your voice from the audio OUTPUT to prevent echo
- BUT when you're UNMUTED, your voice is part of the MIXED audio
- Screen sharing captures this mixed audio, including your voice!

**Why "Both" Mode Doesn't Work**:
- Google Meet is already using your microphone
- Browser can't access the same microphone twice
- Results in only system audio being captured

## What Was Fixed

### Backend Fix
- ✅ Added missing `diarize_audio()` method
- ✅ Proper fallback when speaker diarization is unavailable
- ✅ No more errors in the logs

### Frontend Fix
- ✅ Better error handling for microphone access
- ✅ Clearer instructions in the UI
- ✅ Improved audio mixing with higher gains

## Testing Checklist

- [ ] Select "Screen Only" mode
- [ ] Choose "Entire Screen" (not Chrome Tab)
- [ ] Check "Share audio" checkbox
- [ ] Unmute yourself in Google Meet
- [ ] Speak during the meeting
- [ ] End meeting and check transcript
- [ ] Both participants should be in the transcript

## Troubleshooting

### Still not capturing your voice?
1. **Check if you're unmuted** in Google Meet (most common issue!)
2. **Verify "Share audio" was checked** when sharing screen
3. **Make sure you selected "Entire Screen"** not "Chrome Tab"
4. **Check browser console** for any error messages

### Transcript shows "Thank you" repeatedly?
- This was the old bug - should be fixed now
- If it still happens, check that you selected "Entire Screen" not "Chrome Tab"

### Speaker diarization not working?
- This is expected - pyannote.audio is not installed
- All speakers will show as "Speaker 1"
- To fix: Install pyannote.audio and set HUGGINGFACE_TOKEN

## Quick Test

1. Start a test meeting with yourself (open Google Meet in two tabs)
2. Use "Screen Only" mode
3. Unmute and say something in the meeting
4. End the meeting
5. Check if your words appear in the transcript

## Need Help?

Check the logs:
- **Frontend**: Open browser console (F12)
- **Backend**: Check terminal where server is running

Look for:
- ✅ "Display stream: MediaStream"
- ✅ "Audio track found"
- ✅ "Transcription complete"
- ✅ "Speaker diarization complete" (or fallback message)

---

**TL;DR**: Use "Screen Only" mode, select "Entire Screen", check "Share audio", and UNMUTE yourself in Google Meet!
