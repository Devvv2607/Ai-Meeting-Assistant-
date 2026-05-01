# Tab Audio Debugging Guide

## Issue Summary

**Problem**: Tab audio mode keeps transcribing "Thank you. Thank you." instead of actual Google Meet audio
**Status**: Microphone works perfectly, tab audio needs debugging

---

## Debugging Steps Added

### 1. Enhanced Logging

Added comprehensive console logging to track:
- Audio stream creation
- Audio track detection
- Video track removal
- MediaRecorder state
- Audio chunk sizes
- WebSocket transmission

### 2. Audio Track Validation

Added checks for:
- ✅ Audio track exists (throws error if missing)
- ✅ Audio track is enabled
- ✅ Audio track is not muted
- ✅ Audio track state is 'live'
- ✅ Audio track settings (sample rate, channels)

### 3. MediaRecorder Configuration

- Explicitly set MIME type: `audio/webm;codecs=opus`
- Added error handlers
- Added state change handlers
- Log chunk sizes and types

---

## How to Debug Tab Audio

### Step 1: Open Browser Console

1. Press `F12` to open Developer Tools
2. Go to the **Console** tab
3. Keep it open while testing

### Step 2: Test Tab Audio Capture

1. Open a Google Meet in Tab 1
2. Open http://localhost:3000/live-meeting in Tab 2
3. Select **Tab Audio** mode
4. Click "Start Meeting"
5. **Watch the console logs carefully**

### Step 3: Check Console Output

Look for these key messages:

#### ✅ **Success Indicators**:
```
Requesting display media (tab audio)...
Display media granted: MediaStream {...}
Audio tracks: [MediaStreamTrack {...}]
Audio track enabled: true
Audio track muted: false
Audio track label: "Tab audio"  // or similar
Audio track settings: {sampleRate: 48000, channelCount: 2}
MediaRecorder created with MIME type: audio/webm;codecs=opus
MediaRecorder started
Sending audio chunk: 1234 bytes, type: audio/webm
```

#### ❌ **Error Indicators**:
```
No audio track found! Make sure to check "Share audio"
Audio track is not live! Current state: ended
Skipping audio chunk: size=0
```

---

## Common Issues & Solutions

### Issue 1: "No audio track found"

**Cause**: "Share audio" checkbox was not checked

**Solution**:
1. When the browser shows the tab selection dialog
2. Look at the bottom of the dialog
3. **Check the "Share audio" or "Share tab audio" checkbox**
4. Then click "Share"

### Issue 2: Audio track exists but size=0

**Cause**: Selected tab has no audio playing

**Solution**:
1. Make sure Google Meet is actually playing audio
2. Unmute yourself in Google Meet
3. Have someone speak in the meeting
4. Or play a test sound in the tab

### Issue 3: Wrong tab selected

**Cause**: Selected a different tab (YouTube, etc.)

**Solution**:
1. When browser shows tab list, carefully select the **Google Meet tab**
2. Look for the tab title or preview
3. Make sure it's the active meeting tab

### Issue 4: Audio track label shows wrong source

**Cause**: Browser captured wrong audio source

**Solution**:
1. Check console log: `Audio track label: "..."`
2. If it says "System Audio" or wrong tab name, restart
3. Try again and select the correct tab

---

## Testing Checklist

Before reporting tab audio as broken, verify:

- [ ] Google Meet tab is open and active
- [ ] Google Meet has audio playing (someone speaking or test sound)
- [ ] Selected the correct Google Meet tab in the dialog
- [ ] Checked "Share audio" checkbox in the dialog
- [ ] Console shows "Audio tracks: [MediaStreamTrack {...}]" (not empty array)
- [ ] Console shows "Audio track enabled: true"
- [ ] Console shows "Sending audio chunk: X bytes" (X > 0)
- [ ] No error messages in console
- [ ] MediaRecorder state is "recording"

---

## Expected Console Output (Success)

```javascript
// 1. Request display media
Requesting display media (tab audio)...

// 2. Permission granted
Display media granted: MediaStream {id: "...", active: true}

// 3. Tracks detected
All tracks: [MediaStreamTrack, MediaStreamTrack]
Audio tracks: [MediaStreamTrack {kind: "audio", ...}]
Video tracks: [MediaStreamTrack {kind: "video", ...}]

// 4. Audio track details
Audio track settings: {
  sampleRate: 48000,
  channelCount: 2,
  echoCancellation: true,
  noiseSuppression: true
}
Audio track enabled: true
Audio track muted: false
Audio track label: "Tab audio"

// 5. Video track removed
Stopping video track: Screen
Final audio stream tracks: [MediaStreamTrack {kind: "audio"}]

// 6. MediaRecorder setup
MediaRecorder created with MIME type: audio/webm;codecs=opus
MediaRecorder state: inactive

// 7. WebSocket connection
Connecting to WebSocket: ws://localhost:8000/ws/live/...
WebSocket connected

// 8. Recording started
MediaRecorder started
MediaRecorder state: recording

// 9. Audio chunks being sent
Sending audio chunk: 862 bytes, type: audio/webm
Sending audio chunk: 716 bytes, type: audio/webm
Sending audio chunk: 730 bytes, type: audio/webm
...
```

---

## Expected Console Output (Failure)

### Scenario 1: No Audio Checkbox

```javascript
Requesting display media (tab audio)...
Display media granted: MediaStream {...}
All tracks: [MediaStreamTrack {kind: "video"}]
Audio tracks: []  // ❌ EMPTY!
Video tracks: [MediaStreamTrack {kind: "video"}]

❌ Error: No audio track found! Make sure to check "Share audio" when selecting the tab.
```

### Scenario 2: Audio Track Dead

```javascript
Audio tracks: [MediaStreamTrack {kind: "audio", readyState: "ended"}]
❌ Error: Audio track is not live! Current state: ended
```

### Scenario 3: No Audio Data

```javascript
MediaRecorder started
Skipping audio chunk: size=0, wsState=1  // ❌ Size is 0!
Skipping audio chunk: size=0, wsState=1
Skipping audio chunk: size=0, wsState=1
```

---

## Browser Compatibility

### Chrome/Edge (Recommended)
- ✅ Full support for tab audio capture
- ✅ "Share audio" checkbox available
- ✅ Best audio quality

### Firefox
- ⚠️ Limited tab audio support
- ⚠️ May require additional permissions
- ⚠️ Audio quality may vary

### Safari
- ❌ No tab audio capture support
- ❌ Use microphone mode instead

---

## Alternative: System Audio Capture

If tab audio continues to fail, consider:

### Option 1: Use Microphone Mode
- Speak into your microphone during the Google Meet
- System will capture your voice directly
- Works reliably but only captures your side

### Option 2: Virtual Audio Cable (Advanced)
1. Install VB-Audio Virtual Cable or similar
2. Route Google Meet audio through virtual cable
3. Set virtual cable as microphone input
4. Use microphone mode to capture

### Option 3: Screen Recording Software
1. Use OBS or similar to record Google Meet
2. Extract audio from recording
3. Upload audio file for transcription

---

## Next Steps

1. **Test with console open** and share the console output
2. **Take screenshot** of the tab selection dialog showing "Share audio" checkbox
3. **Verify audio chunks** are being sent (size > 0)
4. **Check backend logs** to see if audio is being received

If all checks pass but transcription is still wrong, the issue is likely:
- Audio encoding/decoding mismatch
- Groq API receiving corrupted audio
- Audio file conversion issue (WebM → WAV)

---

## Success Criteria

Tab audio is working correctly when:
- ✅ Console shows audio track detected
- ✅ Console shows audio chunks > 0 bytes
- ✅ Backend logs show chunks received
- ✅ Audio file created with correct size
- ✅ Transcription matches actual Google Meet audio

---

## Contact Support

If issue persists after following this guide:
1. Share console output (full log)
2. Share backend logs (audio processing section)
3. Confirm browser and version
4. Confirm Google Meet audio is actually playing
5. Try with a different browser tab (YouTube video) to isolate issue
