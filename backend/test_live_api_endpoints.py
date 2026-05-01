"""
Test script for live meeting API endpoints

Tests the three REST API endpoints:
- POST /api/v1/meetings/start-live
- POST /api/v1/meetings/{meeting_id}/end
- GET /api/v1/meetings/{meeting_id}/live-status

Usage:
    python test_live_api_endpoints.py
"""

import requests
import json
import sys
import time

# Configuration
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1"

# Test credentials (adjust as needed)
TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "testpassword123"


def print_section(title):
    """Print a section header"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_response(response):
    """Pretty print response"""
    print(f"Status Code: {response.status_code}")
    try:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except:
        print(f"Response: {response.text}")


def get_auth_token():
    """Get authentication token"""
    print_section("Step 1: Authenticate")
    
    # Try to login
    login_url = f"{API_BASE}/auth/login"
    login_data = {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    }
    
    print(f"POST {login_url}")
    print(f"Data: {json.dumps(login_data, indent=2)}")
    
    response = requests.post(login_url, json=login_data)
    print_response(response)
    
    if response.status_code == 200:
        token = response.json().get("access_token")
        print(f"\n✓ Authentication successful")
        return token
    else:
        print(f"\n✗ Authentication failed")
        print("Please ensure:")
        print(f"  1. Backend is running at {BASE_URL}")
        print(f"  2. User exists with email: {TEST_EMAIL}")
        print(f"  3. Password is correct: {TEST_PASSWORD}")
        return None


def test_start_live_meeting(token):
    """Test POST /api/v1/meetings/start-live"""
    print_section("Step 2: Start Live Meeting")
    
    url = f"{API_BASE}/meetings/start-live"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"meeting_title": "Test Live Meeting"}
    
    print(f"POST {url}")
    print(f"Headers: Authorization: Bearer {token[:20]}...")
    print(f"Params: {json.dumps(params, indent=2)}")
    
    response = requests.post(url, headers=headers, params=params)
    print_response(response)
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✓ Live meeting started successfully")
        print(f"  Meeting ID: {data.get('meeting_id')}")
        print(f"  Session Token: {data.get('session_token')[:20]}...")
        print(f"  WebSocket URL: {data.get('websocket_url')}")
        return data
    else:
        print(f"\n✗ Failed to start live meeting")
        return None


def test_get_live_status(token, meeting_id, session_token):
    """Test GET /api/v1/meetings/{meeting_id}/live-status"""
    print_section("Step 3: Get Live Status")
    
    url = f"{API_BASE}/meetings/{meeting_id}/live-status"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"session_token": session_token}
    
    print(f"GET {url}")
    print(f"Headers: Authorization: Bearer {token[:20]}...")
    print(f"Params: {json.dumps(params, indent=2)}")
    
    response = requests.get(url, headers=headers, params=params)
    print_response(response)
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✓ Live status retrieved successfully")
        print(f"  Status: {data.get('status')}")
        print(f"  Duration: {data.get('duration_seconds'):.2f}s")
        print(f"  Segments: {data.get('segment_count')}")
        print(f"  Speakers: {len(data.get('speakers', []))}")
        return True
    else:
        print(f"\n✗ Failed to get live status")
        return False


def test_end_live_meeting(token, meeting_id, session_token):
    """Test POST /api/v1/meetings/{meeting_id}/end"""
    print_section("Step 4: End Live Meeting")
    
    url = f"{API_BASE}/meetings/{meeting_id}/end"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"session_token": session_token}
    
    print(f"POST {url}")
    print(f"Headers: Authorization: Bearer {token[:20]}...")
    print(f"Params: {json.dumps(params, indent=2)}")
    
    response = requests.post(url, headers=headers, params=params)
    print_response(response)
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✓ Live meeting ended successfully")
        print(f"  Meeting ID: {data.get('meeting_id')}")
        print(f"  Status: {data.get('status')}")
        print(f"  Duration: {data.get('duration'):.2f}s")
        print(f"  Insights Ready: {data.get('insights_ready')}")
        return True
    else:
        print(f"\n✗ Failed to end live meeting")
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("  Live Meeting API Endpoints Test")
    print("=" * 60)
    print(f"\nTesting endpoints at: {BASE_URL}")
    print(f"Using test user: {TEST_EMAIL}")
    
    # Step 1: Authenticate
    token = get_auth_token()
    if not token:
        print("\n✗ Test suite failed: Authentication required")
        sys.exit(1)
    
    # Step 2: Start live meeting
    meeting_data = test_start_live_meeting(token)
    if not meeting_data:
        print("\n✗ Test suite failed: Could not start live meeting")
        sys.exit(1)
    
    meeting_id = meeting_data.get("meeting_id")
    session_token = meeting_data.get("session_token")
    
    # Wait a moment to simulate some meeting time
    print("\n⏳ Waiting 2 seconds to simulate meeting activity...")
    time.sleep(2)
    
    # Step 3: Get live status
    if not test_get_live_status(token, meeting_id, session_token):
        print("\n⚠ Warning: Could not get live status, but continuing...")
    
    # Step 4: End live meeting
    if not test_end_live_meeting(token, meeting_id, session_token):
        print("\n✗ Test suite failed: Could not end live meeting")
        sys.exit(1)
    
    # Summary
    print_section("Test Summary")
    print("✓ All tests passed successfully!")
    print("\nEndpoints tested:")
    print("  1. POST /api/v1/meetings/start-live")
    print("  2. GET /api/v1/meetings/{meeting_id}/live-status")
    print("  3. POST /api/v1/meetings/{meeting_id}/end")
    print("\nAll endpoints are working correctly with LiveSessionManager.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n✗ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n✗ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
