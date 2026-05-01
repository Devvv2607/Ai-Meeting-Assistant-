"""
Test script for WebSocket live meeting connection.

This script tests the WebSocket endpoint with proper authentication.
"""

import asyncio
import websockets
import json
import sys

# Configuration
BACKEND_URL = "ws://localhost:8000"
SESSION_TOKEN = sys.argv[1] if len(sys.argv) > 1 else "test-session-token"
JWT_TOKEN = sys.argv[2] if len(sys.argv) > 2 else "test-jwt-token"


async def test_websocket_connection():
    """Test WebSocket connection with authentication."""
    
    ws_url = f"{BACKEND_URL}/ws/live/{SESSION_TOKEN}?token={JWT_TOKEN}"
    
    print(f"Connecting to: {ws_url}")
    
    try:
        async with websockets.connect(ws_url) as websocket:
            print("✓ WebSocket connected successfully!")
            
            # Wait for connection_established message
            response = await websocket.recv()
            data = json.loads(response)
            print(f"✓ Received: {data}")
            
            if data.get("type") == "connection_established":
                print("✓ Connection established!")
                print(f"  - Session Token: {data.get('session_token')}")
                print(f"  - Meeting ID: {data.get('meeting_id')}")
                print(f"  - User ID: {data.get('user_id')}")
            
            # Wait for ping
            print("\nWaiting for ping message...")
            response = await asyncio.wait_for(websocket.recv(), timeout=35)
            data = json.loads(response)
            print(f"✓ Received: {data}")
            
            if data.get("type") == "ping":
                print("✓ Ping received, sending pong...")
                await websocket.send(json.dumps({
                    "type": "pong",
                    "timestamp": data.get("timestamp")
                }))
                print("✓ Pong sent!")
            
            # Send a test audio chunk
            print("\nSending test audio chunk...")
            await websocket.send(json.dumps({
                "type": "audio_chunk",
                "data": "base64_encoded_audio_data_here",
                "metadata": {
                    "format": "webm",
                    "sample_rate": 48000
                }
            }))
            
            # Wait for response
            response = await asyncio.wait_for(websocket.recv(), timeout=5)
            data = json.loads(response)
            print(f"✓ Received: {data}")
            
            print("\n✓ All tests passed!")
            
    except websockets.exceptions.InvalidStatusCode as e:
        print(f"✗ Connection failed with status code: {e.status_code}")
        print(f"  Headers: {e.headers}")
    except asyncio.TimeoutError:
        print("✗ Timeout waiting for response")
    except Exception as e:
        print(f"✗ Error: {type(e).__name__}: {str(e)}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python test_websocket_live.py <session_token> <jwt_token>")
        print("\nExample:")
        print("  python test_websocket_live.py abc123 eyJhbGc...")
        print("\nYou can get these values from:")
        print("  1. Start a live meeting in the frontend")
        print("  2. Check the browser console for the session_token")
        print("  3. Get JWT token from localStorage.getItem('access_token')")
        sys.exit(1)
    
    asyncio.run(test_websocket_connection())
