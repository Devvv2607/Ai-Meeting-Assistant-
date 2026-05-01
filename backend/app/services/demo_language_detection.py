"""Demo script for language detection service.

This script demonstrates how to use the LanguageDetector service
with audio segments from the AudioBuffer.
"""

import logging
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.language_detector import LanguageDetector
from app.services.audio_buffer import AudioBuffer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def demo_language_detection():
    """Demonstrate language detection workflow."""
    
    logger.info("=" * 60)
    logger.info("Language Detection Service Demo")
    logger.info("=" * 60)
    
    # Initialize language detector
    logger.info("\n1. Initializing LanguageDetector...")
    detector = LanguageDetector()
    
    # Show supported languages
    logger.info("\n2. Supported Languages:")
    supported = detector.get_supported_languages()
    for code, name in supported.items():
        logger.info(f"   - {name} ({code})")
    
    # Simulate language detection workflow
    logger.info("\n3. Language Detection Workflow:")
    logger.info("   In a live meeting scenario:")
    logger.info("   a) Frontend captures audio and streams to backend")
    logger.info("   b) Backend buffers audio chunks into segments")
    logger.info("   c) First 5 seconds of audio is used for language detection")
    logger.info("   d) Detected language is used for transcription")
    
    # Example: Check if a language is supported
    logger.info("\n4. Checking Language Support:")
    test_languages = ['en', 'hi', 'mr', 'fr', 'de']
    for lang in test_languages:
        is_supported = detector.is_supported(lang)
        status = "✓ Supported" if is_supported else "✗ Not supported"
        logger.info(f"   {lang}: {status}")
    
    # Example workflow with AudioBuffer
    logger.info("\n5. Integration with AudioBuffer:")
    logger.info("   a) AudioBuffer receives 100ms chunks from frontend")
    logger.info("   b) Buffers them into 1-second segments")
    logger.info("   c) First 5 segments (5 seconds) sent to LanguageDetector")
    logger.info("   d) Language detection result used for transcription")
    
    # Show example result structure
    logger.info("\n6. Example Detection Result:")
    example_result = {
        'language': 'en',
        'language_name': 'English',
        'confidence': 0.95,
        'supported': True
    }
    logger.info(f"   {example_result}")
    
    logger.info("\n7. Decision Logic:")
    logger.info("   - If confidence >= 90%: Proceed with detected language")
    logger.info("   - If confidence < 90%: Prompt user to confirm language")
    logger.info("   - If language not supported: Fall back to English with warning")
    
    logger.info("\n" + "=" * 60)
    logger.info("Demo Complete!")
    logger.info("=" * 60)


def demo_audio_buffer_integration():
    """Demonstrate integration between AudioBuffer and LanguageDetector."""
    
    logger.info("\n" + "=" * 60)
    logger.info("AudioBuffer + LanguageDetector Integration")
    logger.info("=" * 60)
    
    # Initialize components
    audio_buffer = AudioBuffer(segment_duration=1.0)
    language_detector = LanguageDetector()
    
    logger.info("\n1. Simulating Live Meeting Audio Stream:")
    logger.info("   - Frontend sends 100ms audio chunks")
    logger.info("   - Backend buffers into 1-second segments")
    logger.info("   - First 5 segments used for language detection")
    
    # Simulate receiving audio chunks
    logger.info("\n2. Buffering Audio Chunks:")
    segments_for_detection = []
    
    for i in range(50):  # 50 chunks = 5 seconds
        # Simulate receiving a 100ms chunk
        chunk_data = b'fake_audio_chunk_' + str(i).encode()
        chunk_duration = 0.1  # 100ms
        
        # Add to buffer
        segment = audio_buffer.add_chunk(
            chunk_data,
            chunk_duration,
            metadata={'sequence_number': i, 'timestamp': i * 0.1}
        )
        
        # If a segment is ready, collect it for language detection
        if segment:
            segments_for_detection.append(segment)
            logger.info(f"   Segment #{len(segments_for_detection)} ready: {segment.duration:.1f}s")
    
    logger.info(f"\n3. Collected {len(segments_for_detection)} segments for language detection")
    
    # In a real scenario, we would:
    # 1. Combine the first 5 segments into a single audio file
    # 2. Call language_detector.detect_language(combined_audio)
    # 3. Use the result to configure transcription
    
    logger.info("\n4. Language Detection Process:")
    logger.info("   a) Combine first 5 segments (5 seconds of audio)")
    logger.info("   b) Save to temporary WAV file")
    logger.info("   c) Call Whisper API for language detection")
    logger.info("   d) Parse response for language code and confidence")
    logger.info("   e) Return result to session manager")
    
    logger.info("\n5. Session Manager Actions:")
    logger.info("   - If confidence >= 90%: Set language for transcription")
    logger.info("   - If confidence < 90%: Send language options to frontend")
    logger.info("   - Frontend shows language selection dialog if needed")
    logger.info("   - User confirms or selects language")
    logger.info("   - Session continues with confirmed language")
    
    logger.info("\n" + "=" * 60)
    logger.info("Integration Demo Complete!")
    logger.info("=" * 60)


if __name__ == "__main__":
    # Run demos
    demo_language_detection()
    demo_audio_buffer_integration()
