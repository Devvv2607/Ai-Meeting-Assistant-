"""Test Summary model with structured insights fields"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.models.summary import Summary
from app.models.meeting import Meeting
from app.models.user import User
from datetime import datetime


def test_summary_json_fields():
    """Test that JSON fields can store and retrieve structured data"""
    db: Session = SessionLocal()
    
    try:
        # Create a test user if not exists
        user = db.query(User).filter(User.email == "test@example.com").first()
        if not user:
            user = User(
                email="test@example.com",
                username="testuser",
                hashed_password="dummy_hash"
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        
        # Create a test meeting
        meeting = Meeting(
            user_id=user.id,
            title="Test Meeting for Summary JSON Fields",
            status="completed",
            audio_url="test_audio.mp3",
            created_at=datetime.utcnow()
        )
        db.add(meeting)
        db.commit()
        db.refresh(meeting)
        
        # Create a summary with structured insights
        test_decisions = [
            {
                "decision": "Migrate to microservices architecture",
                "context": "To improve scalability and maintainability",
                "timestamp": "00:15:30"
            },
            {
                "decision": "Use PostgreSQL for primary database",
                "context": "Better JSON support and reliability",
                "timestamp": "00:22:45"
            }
        ]
        
        test_risks = [
            {
                "risk": "Tight deadline for Q2 release",
                "severity": "high",
                "mitigation": "Add two more developers to the team",
                "timestamp": "00:35:20"
            }
        ]
        
        test_next_steps = [
            {
                "step": "Create technical design document",
                "owner": "John Doe",
                "deadline": "2026-05-01",
                "timestamp": "00:45:10"
            },
            {
                "step": "Set up CI/CD pipeline",
                "owner": "Jane Smith",
                "deadline": "2026-05-05",
                "timestamp": "00:46:30"
            }
        ]
        
        test_topics = [
            {
                "topic": "Architecture Discussion",
                "start_time": "00:10:00",
                "end_time": "00:25:00",
                "duration_seconds": 900
            },
            {
                "topic": "Timeline and Resources",
                "start_time": "00:25:00",
                "end_time": "00:40:00",
                "duration_seconds": 900
            }
        ]
        
        test_analytics = {
            "duration_seconds": 3600,
            "speaker_count": 5,
            "total_words": 4500,
            "speakers": [
                {"name": "Speaker 1", "talk_time_seconds": 1200, "word_count": 1500},
                {"name": "Speaker 2", "talk_time_seconds": 900, "word_count": 1100},
                {"name": "Speaker 3", "talk_time_seconds": 600, "word_count": 800}
            ],
            "sentiment": "positive",
            "engagement_score": 0.85
        }
        
        summary = Summary(
            meeting_id=meeting.id,
            summary_text="Test meeting to verify JSON field functionality",
            key_points=["Point 1", "Point 2"],
            action_items=[{"item": "Test action", "owner": "Test User"}],
            decisions=test_decisions,
            risks=test_risks,
            next_steps=test_next_steps,
            topics=test_topics,
            meeting_analytics=test_analytics
        )
        
        db.add(summary)
        db.commit()
        db.refresh(summary)
        
        print("✓ Summary created successfully with ID:", summary.id)
        
        # Retrieve and verify the data
        retrieved_summary = db.query(Summary).filter(Summary.id == summary.id).first()
        
        assert retrieved_summary is not None, "Summary not found"
        print("✓ Summary retrieved successfully")
        
        # Verify decisions field
        assert retrieved_summary.decisions is not None, "Decisions field is None"
        assert len(retrieved_summary.decisions) == 2, "Decisions count mismatch"
        assert retrieved_summary.decisions[0]["decision"] == "Migrate to microservices architecture"
        print("✓ Decisions field verified")
        
        # Verify risks field
        assert retrieved_summary.risks is not None, "Risks field is None"
        assert len(retrieved_summary.risks) == 1, "Risks count mismatch"
        assert retrieved_summary.risks[0]["severity"] == "high"
        print("✓ Risks field verified")
        
        # Verify next_steps field
        assert retrieved_summary.next_steps is not None, "Next steps field is None"
        assert len(retrieved_summary.next_steps) == 2, "Next steps count mismatch"
        assert retrieved_summary.next_steps[0]["owner"] == "John Doe"
        print("✓ Next steps field verified")
        
        # Verify topics field
        assert retrieved_summary.topics is not None, "Topics field is None"
        assert len(retrieved_summary.topics) == 2, "Topics count mismatch"
        assert retrieved_summary.topics[0]["topic"] == "Architecture Discussion"
        print("✓ Topics field verified")
        
        # Verify meeting_analytics field
        assert retrieved_summary.meeting_analytics is not None, "Meeting analytics field is None"
        assert retrieved_summary.meeting_analytics["speaker_count"] == 5
        assert retrieved_summary.meeting_analytics["engagement_score"] == 0.85
        assert len(retrieved_summary.meeting_analytics["speakers"]) == 3
        print("✓ Meeting analytics field verified")
        
        # Test backward compatibility - old summaries without new fields should still work
        old_summary = Summary(
            meeting_id=meeting.id,
            summary_text="Old summary without new fields",
            key_points=["Old point"],
            action_items=[{"item": "Old action"}]
        )
        db.add(old_summary)
        db.commit()
        db.refresh(old_summary)
        
        assert old_summary.decisions is None, "Old summary should have None for new fields"
        assert old_summary.risks is None
        assert old_summary.next_steps is None
        assert old_summary.topics is None
        assert old_summary.meeting_analytics is None
        print("✓ Backward compatibility verified")
        
        print("\n✅ All tests passed! Summary model JSON fields are working correctly.")
        
        # Cleanup
        db.delete(summary)
        db.delete(old_summary)
        db.delete(meeting)
        db.commit()
        print("✓ Test data cleaned up")
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    test_summary_json_fields()
