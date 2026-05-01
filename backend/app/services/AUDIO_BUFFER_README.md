# AudioBuffer Service

The AudioBuffer service handles buffering of audio chunks received from the frontend during live meeting sessions and assembles them into segments suitable for transcription.

## Overview

The AudioBuffer receives 100ms audio chunks from the frontend WebSocket connection and buffers them into 1-second segments that are optimal for Whisper transcription. It also handles audio format conversion from WebM/Opus (browser format) to WAV format (Whisper requirement).

## Key Features

- **Chunk Buffering**: Accumulates 100ms chunks into 1-second segments
- **Format Conversion**: Converts WebM/Opus to WAV at 16kHz (Whisper requirement)
- **Metadata Tracking**: Tracks sequence numbers and timestamps for each segment
- **Graceful Degradation**: Falls back to original audio data if conversion fails
- **Memory Efficient**: Clears buffer after each segment creation
- **Floating Point Safe**: Handles floating point precision issues in duration calculations

## Usage

### Basic Usage

```python
from backend.app.services.audio_buffer import AudioBuffer

# Initialize buffer with 1-second segments at 16kHz
buffer = AudioBuffer(segment_duration=1.0, sample_rate=16000)

# Add audio chunks as they arrive from WebSocket
for chunk_data in audio_stream:
    metadata = {
        'sequence_number': chunk_number,
        'timestamp': current_timestamp
    }
    
    segment = buffer.add_chunk(
        chunk=chunk_data,
        duration=0.1,  # 100ms chunks
        metadata=metadata
    )
    
    # Process segment when ready
    if segment:
        # Send to transcription service
        transcribe_audio(segment.data)
        print(f"Segment {segment.sequence_start}-{segment.sequence_end}: {segment.duration}s")

# Flush remaining audio when stream ends
final_segment = buffer.flush()
if final_segment:
    transcribe_audio(final_segment.data)
```

### Live Meeting Integration

```python
from backend.app.services.audio_buffer import AudioBuffer
from backend.app.services.whisper_service import whisper_service

class LiveSessionHandler:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.buffer = AudioBuffer(segment_duration=1.0)
    
    async def handle_audio_chunk(self, chunk: bytes, duration: float, metadata: dict):
        """Handle incoming audio chunk from WebSocket"""
        segment = self.buffer.add_chunk(chunk, duration, metadata)
        
        if segment:
            # Segment is ready for transcription
            await self.transcribe_segment(segment)
    
    async def transcribe_segment(self, segment):
        """Transcribe audio segment"""
        # Save segment to temp file
        temp_path = f"/tmp/segment_{segment.sequence_start}.wav"
        with open(temp_path, 'wb') as f:
            f.write(segment.data)
        
        # Transcribe using Whisper
        result = await whisper_service.transcribe_stream(segment.data)
        
        # Store transcript in database
        # ... (implementation details)
    
    async def end_session(self):
        """End session and process remaining audio"""
        final_segment = self.buffer.flush()
        if final_segment:
            await self.transcribe_segment(final_segment)
        
        # Get session statistics
        stats = self.buffer.get_stats()
        print(f"Session ended: {stats['total_segments']} segments processed")
```

### Pause and Resume

```python
# During active streaming
buffer = AudioBuffer(segment_duration=1.0)

# ... stream audio ...

# User pauses meeting
remaining = buffer.flush()  # Process remaining audio
if remaining:
    process_segment(remaining)

# User resumes meeting
buffer.reset()  # Clear buffer state

# ... continue streaming ...
```

## API Reference

### AudioBuffer Class

#### Constructor

```python
AudioBuffer(segment_duration: float = 1.0, sample_rate: int = 16000)
```

**Parameters:**
- `segment_duration`: Target duration for segments in seconds (default: 1.0)
- `sample_rate`: Audio sample rate in Hz (default: 16000 for Whisper)

#### Methods

##### add_chunk()

```python
add_chunk(chunk: bytes, duration: float, metadata: Optional[dict] = None) -> Optional[AudioSegment]
```

Add audio chunk to buffer and return segment if ready.

**Parameters:**
- `chunk`: Raw audio data bytes (WebM/Opus format from frontend)
- `duration`: Duration of the chunk in seconds
- `metadata`: Optional metadata (timestamp, sequence_number, etc.)

**Returns:**
- `AudioSegment` if a complete segment is ready, `None` otherwise

##### flush()

```python
flush() -> Optional[AudioSegment]
```

Flush remaining audio in buffer as a segment. Call this when the audio stream ends.

**Returns:**
- `AudioSegment` with remaining audio, or `None` if buffer is empty

##### get_stats()

```python
get_stats() -> dict
```

Get buffer statistics.

**Returns:**
```python
{
    'total_segments': int,      # Total segments created
    'buffer_chunks': int,        # Current chunks in buffer
    'buffer_duration': float,    # Current buffer duration in seconds
    'segment_duration': float,   # Target segment duration
    'sample_rate': int          # Audio sample rate
}
```

##### reset()

```python
reset() -> None
```

Reset buffer state. Clears all buffered data and resets counters.

### AudioSegment Dataclass

```python
@dataclass
class AudioSegment:
    data: bytes              # Audio data in WAV format
    duration: float          # Duration in seconds
    timestamp: datetime      # Creation timestamp
    sequence_start: int      # Starting sequence number
    sequence_end: int        # Ending sequence number
```

## Audio Format Conversion

The AudioBuffer automatically converts audio from WebM/Opus (browser format) to WAV format at 16kHz (Whisper requirement) using pydub.

**Conversion Process:**
1. Attempts to load audio as WebM, Ogg, or Opus
2. Converts stereo to mono if necessary
3. Resamples to 16kHz if necessary
4. Exports as WAV format

**Fallback Behavior:**
- If pydub is not available, returns original audio data
- If conversion fails, returns original audio data
- Logs warnings but continues operation

**Dependencies:**
- `pydub`: Audio processing library
- `ffmpeg`: Required by pydub for format conversion

## Performance Characteristics

- **Memory Efficient**: Buffer is cleared after each segment creation
- **No Memory Leaks**: Tested with 100+ segments without memory accumulation
- **Floating Point Safe**: Uses epsilon tolerance (1ms) for duration comparisons
- **Error Resilient**: Continues operation even if audio conversion fails

## Testing

The AudioBuffer has comprehensive test coverage:

- **Unit Tests**: 27 tests covering all methods and edge cases
- **Integration Tests**: 11 tests covering realistic usage scenarios
- **Total Coverage**: 38 tests, all passing

Run tests:
```bash
# Unit tests
python -m pytest backend/app/services/test_audio_buffer.py -v

# Integration tests
python -m pytest backend/app/services/test_audio_buffer_integration.py -v

# All tests
python -m pytest backend/app/services/test_audio_buffer*.py -v
```

## Requirements

From `requirements.txt`:
```
pydub
```

System requirements:
- `ffmpeg` must be installed and available in PATH for audio conversion

## Implementation Notes

### Floating Point Precision

The buffer uses an epsilon tolerance (1ms) when comparing durations to handle floating point precision issues:

```python
EPSILON = 0.001  # 1ms tolerance
if self.buffer_duration >= (self.segment_duration - EPSILON):
    return self._create_segment()
```

This ensures that `0.1 * 10 = 0.9999999999999999` is treated as `1.0`.

### Error Handling

The buffer is designed to be resilient:
- Empty chunks are skipped with a warning
- Audio conversion failures fall back to original data
- Errors during segment creation clear the buffer to prevent corruption
- All errors are logged for debugging

### Thread Safety

The AudioBuffer is **not thread-safe**. Each WebSocket connection should have its own AudioBuffer instance. For concurrent sessions, use separate buffer instances per session.

## Future Enhancements

Potential improvements for future versions:

1. **Adaptive Buffering**: Adjust segment duration based on network conditions
2. **Quality Metrics**: Track audio quality metrics (volume, noise level)
3. **Compression**: Optional compression for storage efficiency
4. **Streaming Conversion**: Convert audio without loading entire segment into memory
5. **Multi-format Support**: Support additional input formats beyond WebM/Opus

## Related Components

- `WhisperService`: Transcribes audio segments
- `LiveSessionManager`: Manages live session state
- `WebSocket Server`: Receives audio chunks from frontend
- `AudioCaptureService` (Frontend): Captures and sends audio chunks

## License

Part of the AI Meeting Intelligence Platform.
