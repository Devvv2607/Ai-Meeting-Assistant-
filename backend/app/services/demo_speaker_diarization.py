"""
Demo script for SpeakerDiarizationService

This script demonstrates the speaker diarization service functionality
without requiring actual audio files or HuggingFace tokens.

Usage:
    python -m app.services.demo_speaker_diarization
"""

import asyncio
import numpy as np
from app.services.speaker_diarization import SpeakerDiarizationService


async def demo_speaker_identification():
    """Demonstrate speaker identification with mock embeddings"""
    
    print("=" * 70)
    print("Speaker Diarization Service Demo")
    print("=" * 70)
    print()
    
    # Create service instance
    service = SpeakerDiarizationService()
    
    # Mock the pipeline (since we don't have HuggingFace token)
    service.pipeline = "mock_pipeline"
    
    print("✓ Service initialized")
    print(f"  - Similarity threshold: {service.similarity_threshold}")
    print()
    
    # Simulate a meeting with 3 speakers
    session_id = "demo_meeting_001"
    
    print(f"Session: {session_id}")
    print("-" * 70)
    print()
    
    # Define mock speaker embeddings (in real scenario, these come from audio)
    speaker_embeddings = {
        "Alice": np.array([1.0, 0.2, 0.1]),
        "Bob": np.array([0.1, 1.0, 0.2]),
        "Charlie": np.array([0.2, 0.1, 1.0])
    }
    
    # Simulate a conversation with multiple turns
    conversation = [
        ("Alice", "Hello everyone, let's start the meeting."),
        ("Bob", "Good morning! I have the quarterly report ready."),
        ("Alice", "Great! Please go ahead and present."),
        ("Charlie", "Before we start, can I add an agenda item?"),
        ("Bob", "Sure, what would you like to discuss?"),
        ("Charlie", "I want to talk about the new project timeline."),
        ("Alice", "That sounds important. Let's add it to the agenda."),
        ("Bob", "Okay, let me share my screen now."),
        ("Alice", "We can see it. Please proceed."),
        ("Charlie", "The numbers look good so far."),
    ]
    
    print("Simulating conversation with speaker identification:")
    print()
    
    detected_speakers = {}
    
    for i, (actual_speaker, text) in enumerate(conversation, 1):
        # Get the embedding for this speaker
        embedding = speaker_embeddings[actual_speaker]
        
        # Add some noise to simulate variation in voice
        noisy_embedding = embedding + np.random.normal(0, 0.05, embedding.shape)
        
        # Identify speaker
        speaker_id, confidence = service._match_speaker(noisy_embedding, session_id)
        
        # Track mapping
        if actual_speaker not in detected_speakers:
            detected_speakers[actual_speaker] = speaker_id
        
        # Display result
        print(f"Turn {i:2d}: {speaker_id} (confidence: {confidence:.2f})")
        print(f"         Actual: {actual_speaker}")
        print(f"         Text: \"{text}\"")
        print()
    
    # Summary
    print("-" * 70)
    print("Summary:")
    print()
    
    session_speakers = service.get_session_speakers(session_id)
    print(f"Total speakers detected: {len(session_speakers)}")
    print()
    
    print("Speaker mapping:")
    for actual, detected in detected_speakers.items():
        print(f"  {actual:10s} → {detected}")
    print()
    
    # Demonstrate cosine similarity
    print("-" * 70)
    print("Cosine Similarity Examples:")
    print()
    
    alice_emb = speaker_embeddings["Alice"]
    bob_emb = speaker_embeddings["Bob"]
    
    # Same speaker (with noise)
    alice_noisy = alice_emb + np.random.normal(0, 0.05, alice_emb.shape)
    similarity_same = service._cosine_similarity(alice_emb, alice_noisy)
    print(f"Alice vs Alice (with noise): {similarity_same:.3f} → MATCH")
    
    # Different speakers
    similarity_diff = service._cosine_similarity(alice_emb, bob_emb)
    print(f"Alice vs Bob:                {similarity_diff:.3f} → NO MATCH")
    print()
    
    print(f"Threshold: {service.similarity_threshold}")
    print(f"  - Above threshold → Same speaker")
    print(f"  - Below threshold → Different speaker")
    print()
    
    # Clean up
    service.clear_session(session_id)
    print("-" * 70)
    print(f"✓ Session cleared: {session_id}")
    print()


async def demo_session_management():
    """Demonstrate session management features"""
    
    print("=" * 70)
    print("Session Management Demo")
    print("=" * 70)
    print()
    
    service = SpeakerDiarizationService()
    service.pipeline = "mock_pipeline"
    
    # Create multiple sessions
    sessions = ["meeting_001", "meeting_002", "meeting_003"]
    
    print("Creating multiple sessions with speakers:")
    print()
    
    for session_id in sessions:
        # Add 2-3 speakers per session
        num_speakers = np.random.randint(2, 4)
        
        for i in range(num_speakers):
            embedding = np.random.rand(3)
            speaker_id, _ = service._match_speaker(embedding, session_id)
        
        speakers = service.get_session_speakers(session_id)
        print(f"  {session_id}: {len(speakers)} speakers")
    
    print()
    print(f"Total active sessions: {len(service.speaker_embeddings)}")
    print()
    
    # Clear one session
    print(f"Clearing session: {sessions[0]}")
    service.clear_session(sessions[0])
    print(f"Remaining sessions: {len(service.speaker_embeddings)}")
    print()
    
    # Clear all sessions
    print("Clearing all remaining sessions:")
    for session_id in sessions[1:]:
        service.clear_session(session_id)
    
    print(f"Total active sessions: {len(service.speaker_embeddings)}")
    print()


async def demo_edge_cases():
    """Demonstrate edge case handling"""
    
    print("=" * 70)
    print("Edge Cases Demo")
    print("=" * 70)
    print()
    
    service = SpeakerDiarizationService()
    service.pipeline = "mock_pipeline"
    
    session_id = "edge_case_session"
    
    # Test 1: Zero vector
    print("Test 1: Zero vector embedding")
    zero_embedding = np.array([0.0, 0.0, 0.0])
    speaker_id, confidence = service._match_speaker(zero_embedding, session_id)
    print(f"  Result: {speaker_id} (confidence: {confidence:.2f})")
    print()
    
    # Test 2: Very similar speakers (just above threshold)
    print("Test 2: Very similar speakers (edge of threshold)")
    emb1 = np.array([1.0, 0.0, 0.0])
    emb2 = np.array([0.71, 0.71, 0.0])  # ~45 degree angle, similarity ~0.71
    
    service.clear_session(session_id)
    speaker_id1, _ = service._match_speaker(emb1, session_id)
    speaker_id2, conf2 = service._match_speaker(emb2, session_id)
    
    similarity = service._cosine_similarity(emb1, emb2)
    print(f"  Similarity: {similarity:.3f}")
    print(f"  Threshold: {service.similarity_threshold}")
    print(f"  Speaker 1: {speaker_id1}")
    print(f"  Speaker 2: {speaker_id2} (confidence: {conf2:.2f})")
    
    if speaker_id1 == speaker_id2:
        print(f"  → Matched as same speaker")
    else:
        print(f"  → Detected as different speakers")
    print()
    
    # Test 3: Many speakers in one session
    print("Test 3: Many speakers in one session")
    service.clear_session(session_id)
    
    num_speakers = 10
    for i in range(num_speakers):
        # Create distinct embeddings
        embedding = np.zeros(10)
        embedding[i] = 1.0
        service._match_speaker(embedding, session_id)
    
    speakers = service.get_session_speakers(session_id)
    print(f"  Created {num_speakers} speakers")
    print(f"  Detected {len(speakers)} unique speakers")
    print()
    
    service.clear_session(session_id)


async def main():
    """Run all demos"""
    await demo_speaker_identification()
    await demo_session_management()
    await demo_edge_cases()
    
    print("=" * 70)
    print("Demo Complete!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
