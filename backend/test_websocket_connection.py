"""
Simple WebSocket client test for live meeting endpoint.

This script tests the WebSocket connection, authentication, and heartbeat mechanism.
"""

import asyncio
import json
import sys
from datetime import datetime
import websockets
from app.utils.auth_utils import create_access_token
from app.database import SessionLocal
from app.models.user import User
from app.models.meeting import Meeting
from app.models.live_session import LiveSession
import secrets


async def test_websocket_connection():
    """Test WebSocket connection with authentication"""
    
    # Setup database
    db = SessionLocal()
    
    try:
        # Get or create test user
        test_user = db.query(User).filter(User.email == "test@example.com").first()
        if not test_user:
            print("❌ Test user not found. Please create a user with email 'test@example.com'")
            return False
        
        print(f"✓ Found test user: {test_user.email} (ID: {test_user.id})")
        
        # Create test meeting
        meeting = Meeting(
            user_id=test_user.id,
            title="WebSocket Test Meeting",
            status="PROCESSING",
            audio_url=""
        )
        db.add(meeting)
        db.commit()
        db.refresh(meeting)
        print(f"✓ Created test meeting (ID: {meeting.id})")
        
        # Create test live session
        session_token = secrets.token_urlsafe(32)
        live_session = LiveSession(
            meeting_id=meeting.id,
            session_token=session_token,
            status="ACTIVE",
            started_at=datetime.utcnow()
        )
        db.add(live_session)
        db.commit()
        print(f"✓ Created live session (Token: {session_token[:20]}...)")
        
        # Generate JWT token
        token = create_access_token(
            data={"user_id": test_user.id, "sub": test_user.email}
        )
        print(f"✓ Generated JWT token")
        
        # Connect to WebSocket
        ws_url = f"ws://localhost:8000/ws/live/{session_token}?token={token}"
        print(f"\n🔌 Connecting to WebSocket: {ws_url[:80]}...")
        
        async with websockets.connect(ws_url) as websocket:
            print("✓ WebSocket connection established")
            
            # Receive connection confirmation
            response = await websocket.recv()
            data = json.loads(response)
            print(f"✓ Received: {data.get('type')} - {data.get('message')}")
            
            if data.get("type") != "connection_established":
                print(f"❌ Unexpected response type: {data.get('type')}")
                return False
            
            # Test heartbeat mechanism
            print("\n💓 Testing heartbeat mechanism...")
            
            # Wait for ping
            ping_received = False
            for _ in range(35):  # Wait up to 35 seconds for ping
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    data = json.loads(response)
                    
                    if data.get("type") == "ping":
                        print(f"✓ Received ping at {data.get('timestamp')}")
                        ping_received = True
                        
                        # Send pong response
                        pong_message = {
                            "type": "pong",
                            "timestamp": datetime.utcnow().isoformat()
                        }
                        await websocket.send(json.dumps(pong_message))
                        print(f"✓ Sent pong response")
                        break
                except asyncio.TimeoutError:
                    continue
            
            if not ping_received:
                print("❌ No ping received within 35 seconds")
                return False
            
            # Test sending a control message
            print("\n📤 Testing control message...")
            control_message = {
                "type": "control",
                "action": "pause"
            }
            await websocket.send(json.dumps(control_message))
            print(f"✓ Sent control message: {control_message}")
            
            # Receive response
            response = await websocket.recv()
            data = json.loads(response)
            print(f"✓ Received: {data.get('type')} - {data.get('message')}")
            
            # Test sending audio chunk placeholder
            print("\n🎵 Testing audio chunk message...")
            audio_message = {
                "type": "audio_chunk",
                "data": "base64_encoded_audio_data_placeholder",
                "metadata": {
                    "timestamp": datetime.utcnow().isoformat(),
                    "sequence": 1
                }
            }
            await websocket.send(json.dumps(audio_message))
            print(f"✓ Sent audio chunk message")
            
            # Receive response
            response = await websocket.recv()
            data = json.loads(response)
            print(f"✓ Received: {data.get('type')} - {data.get('message')}")
            
            print("\n✅ All WebSocket tests passed!")
            return True
    
    except websockets.exceptions.InvalidStatusCode as e:
        print(f"❌ WebSocket connection failed with status code: {e.status_code}")
        print(f"   This might indicate authentication or authorization failure")
        return False
    
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Cleanup
        try:
            if 'live_session' in locals():
                db.delete(live_session)
            if 'meeting' in locals():
                db.delete(meeting)
            db.commit()
            print("\n🧹 Cleaned up test data")
        except Exception as e:
            print(f"⚠️  Cleanup warning: {str(e)}")
        finally:
            db.close()


def main():
    """Main entry point"""
    print("=" * 80)
    print("WebSocket Connection Test")
    print("=" * 80)
    print("\nThis test will:")
    print("  1. Create a test meeting and live session")
    print("  2. Connect to the WebSocket endpoint")
    print("  3. Test authentication")
    print("  4. Test heartbeat mechanism (ping/pong)")
    print("  5. Test control messages")
    print("  6. Test audio chunk messages")
    print("\nMake sure the backend server is running on http://localhost:8000")
    print("=" * 80)
    print()
    
    try:
        result = asyncio.run(test_websocket_connection())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)


if __name__ == "__main__":
    main()
