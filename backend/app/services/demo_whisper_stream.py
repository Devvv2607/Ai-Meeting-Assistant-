"""Demonstration of WhisperService streaming transcription

This script demonstrates how to use the new transcribe_stream() method
for real-time audio transcription in live meetings.
"""

import asyncio
import wave
import struct
import io
from app.services.whisper_service import WhisperService
from app.services.audio_buffer import AudioBuffer


def generate_test_audio(duration_sec: float = 1.0, sample_rate: int = 16000) -> bytes:
    """Generate test audio in WAV format
    
    Args:
        duration_sec: Duration in seconds
        sample_rate: Sample rate in Hz
        
    Returns:
        WAV audio bytes
    """
    num_samples = int(sample_rate * duration_sec)
    
    # Generate simple tone
    samples = []
    for i in range(num_samples):
        # Create a simple pattern
        value = int(32767 * 0.3 * (i % 100) / 100)
        samples.append(struct.pack('<h', value))
    
    # Create WAV file
    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b''.join(samples))
    
    return wav_buffer.getvalue()


async def demo_streaming_transcription():
    """Demonstrate streaming transcription workflow"""
    print("=" * 60)
    print("WhisperService Streaming Transcription Demo")
    print("=" * 60)
    print()
    
    # Initialize services
    print("1. Initializing services...")
    whisper_service = WhisperService()
    audio_buffer = AudioBuffer(segment_duration=1.0, sample_rate=16000)
    
    if not whisper_service.groq_client:
        print("   ⚠️  Groq client not initialized")
        print("   This demo will show the structure but won't make real API calls")
    else:
        print("   ✓ WhisperService initialized with Groq")
    
    print("   ✓ AudioBuffer initialized (1-second segments)")
    print()
    
    # Simulate streaming audio chunks
    print("2. Simulating audio stream...")
    print("   Streaming 10 chunks of 100ms each (= 1 second total)")
    print()
    
    segment_count = 0
    
    for i in range(10):
        # Generate 100ms audio chunk
        chunk = generate_test_audio(duration_sec=0.1)
        
        print(f"   Chunk {i+1}/10: {len(chunk)} bytes, 100ms")
        
        # Add to buffer
        metadata = {
            'timestamp': i * 100,
            'sequence_number': i
        }
        
        segment = audio_buffer.add_chunk(
            chunk=chunk,
            duration=0.1,
            metadata=metadata
        )
        
        # When segment is ready, transcribe it
        if segment:
            segment_count += 1
            print()
            print(f"   ✓ Segment #{segment_count} ready!")
            print(f"     - Duration: {segment.duration:.2f}s")
            print(f"     - Size: {len(segment.data)} bytes")
            print(f"     - Sequence: {segment.sequence_start}-{segment.sequence_end}")
            print()
            
            # Transcribe the segment
            print("3. Transcribing segment...")
            
            try:
                result = await whisper_service.transcribe_stream(
                    audio_segment=segment.data,
                    language="en"
                )
                
                print("   ✓ Transcription complete!")
                print(f"     - Text: {result['text']}")
                print(f"     - Confidence: {result['confidence']:.2f}")
                print(f"     - Language: {result['language']}")
                
            except Exception as e:
                print(f"   ✗ Transcription failed: {e}")
    
    print()
    
    # Show buffer statistics
    print("4. Buffer statistics:")
    stats = audio_buffer.get_stats()
    print(f"   - Total segments created: {stats['total_segments']}")
    print(f"   - Buffered chunks: {stats['buffer_chunks']}")
    print(f"   - Buffer duration: {stats['buffer_duration']:.2f}s")
    print()
    
    print("=" * 60)
    print("Demo complete!")
    print("=" * 60)


async def demo_multilingual_transcription():
    """Demonstrate multilingual transcription"""
    print()
    print("=" * 60)
    print("Multilingual Transcription Demo")
    print("=" * 60)
    print()
    
    whisper_service = WhisperService()
    
    # Test different languages
    languages = ["en", "hi", "mr", "ta"]
    
    print("Testing language support:")
    print()
    
    for lang in languages:
        audio = generate_test_audio(duration_sec=1.0)
        
        print(f"Language: {lang}")
        
        try:
            result = await whisper_service.transcribe_stream(
                audio_segment=audio,
                language=lang
            )
            
            print(f"  ✓ Transcription: {result['text'][:50]}...")
            print(f"  ✓ Detected language: {result['language']}")
            print()
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
            print()


async def demo_error_handling():
    """Demonstrate error handling"""
    print()
    print("=" * 60)
    print("Error Handling Demo")
    print("=" * 60)
    print()
    
    whisper_service = WhisperService()
    
    # Test with empty audio
    print("1. Testing with empty audio:")
    result = await whisper_service.transcribe_stream(
        audio_segment=b'',
        language="en"
    )
    print(f"   Result: {result}")
    print()
    
    # Test with invalid audio
    print("2. Testing with invalid audio:")
    result = await whisper_service.transcribe_stream(
        audio_segment=b'invalid audio data',
        language="en"
    )
    print(f"   Result: {result}")
    print()
    
    # Test without Groq client
    print("3. Testing without Groq client:")
    service_no_groq = WhisperService()
    service_no_groq.groq_client = None
    
    result = await service_no_groq.transcribe_stream(
        audio_segment=generate_test_audio(),
        language="en"
    )
    print(f"   Result: {result}")
    print()


async def main():
    """Run all demos"""
    await demo_streaming_transcription()
    await demo_multilingual_transcription()
    await demo_error_handling()


if __name__ == "__main__":
    asyncio.run(main())
