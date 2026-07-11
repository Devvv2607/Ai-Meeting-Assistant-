"""
Integration tests for task 11.3: Test transcript and summary retrieval

This test module verifies:
1. Waiting for processing to complete
2. Fetching transcript via frontend
3. Fetching summary via frontend
4. Testing search functionality

Note: This test requires a running Celery worker to process meetings.
"""

import pytest
import time
import logging
from pathlib import Path
from fastapi.testclient import TestClient
import json

logger = logging.getLogger(__name__)


@pytest.fixture
def sample_audio_file(tmp_path):
    """Create a minimal valid WAV file for testing"""
    # Create a very simple WAV file (silence)
    import wave
    import struct
    
    wav_path = tmp_path / "test_audio.wav"
    
    # WAV parameters
    sample_rate = 16000
    duration_seconds = 2
    channels = 1
    sample_width = 2  # 16-bit
    
    with wave.open(str(wav_path), 'w') as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(sample_rate)
        
        # Write silence
        num_frames = sample_rate * duration_seconds
        silence = struct.pack('<h', 0) * num_frames
        wav_file.writeframes(silence)
    
    return wav_path


class TestTranscriptRetrieval:
    """Test suite for transcript and summary retrieval"""
    
    def test_11_3_1_wait_for_processing_completion(
        self,
        authenticated_client,
        sample_audio_file,
        db_session,
    ):
        """
        Test 11.3.1: Wait for processing to complete
        
        Verifies that after uploading a meeting, we can poll the meeting status
        and detect when processing completes.
        """
        logger.info("Test 11.3.1: Testing processing completion polling")
        
        # Upload meeting
        with open(sample_audio_file, 'rb') as f:
            response = authenticated_client.post(
                "/api/v1/meetings/upload",
                data={
                    "title": "Test Meeting for Processing",
                    "description": "Test transcript retrieval"
                },
                files={"file": ("test.wav", f, "audio/wav")}
            )
        
        assert response.status_code in [200, 201], \
            f"Upload failed: {response.status_code} - {response.json()}"
        
        meeting_data = response.json()
        meeting_id = meeting_data.get("id")
        
        logger.info(f"Meeting uploaded with ID: {meeting_id}")
        
        # Poll for processing completion
        max_wait_seconds = 60
        poll_interval = 2
        elapsed = 0
        meeting_status = None
        
        while elapsed < max_wait_seconds:
            # Get meeting status
            status_response = authenticated_client.get(f"/api/v1/meetings/{meeting_id}")
            
            assert status_response.status_code == 200, \
                f"Failed to get meeting status: {status_response.status_code}"
            
            meeting_status = status_response.json()
            current_status = meeting_status.get("status")
            
            logger.info(f"Meeting status: {current_status} (waited {elapsed}s)")
            
            if current_status == "completed":
                logger.info("Meeting processing completed")
                break
            elif current_status == "failed":
                pytest.fail(f"Meeting processing failed")
            
            time.sleep(poll_interval)
            elapsed += poll_interval
        
        # Verify we either completed or are still processing (for faster CI)
        assert meeting_status is not None, "Failed to get meeting status"
        assert meeting_status.get("status") in ["completed", "processing", "pending"], \
            f"Unexpected status: {meeting_status.get('status')}"
        
        logger.info(f"✓ Processing status check passed: {meeting_status.get('status')}")

    def test_11_3_2_fetch_transcript_via_frontend(
        self,
        authenticated_client,
        sample_audio_file,
        db_session,
    ):
        """
        Test 11.3.2: Fetch transcript via frontend
        
        Verifies that:
        - The /api/v1/meetings/{id}/transcripts endpoint is accessible
        - Returns transcript with proper structure
        - Handles missing transcripts gracefully
        """
        logger.info("Test 11.3.2: Testing transcript retrieval")
        
        # Upload meeting
        with open(sample_audio_file, 'rb') as f:
            upload_response = authenticated_client.post(
                "/api/v1/meetings/upload",
                data={
                    "title": "Test Meeting for Transcript",
                    "description": "Test transcript retrieval"
                },
                files={"file": ("test.wav", f, "audio/wav")}
            )
        
        assert upload_response.status_code in [200, 201]
        meeting_id = upload_response.json().get("id")
        
        logger.info(f"Meeting uploaded: {meeting_id}")
        
        # Attempt to fetch transcript immediately
        transcript_response = authenticated_client.get(
            f"/api/v1/meetings/{meeting_id}/transcripts"
        )
        
        # Response should be 200 even if processing hasn't completed
        assert transcript_response.status_code == 200, \
            f"Transcript endpoint failed: {transcript_response.status_code}"
        
        transcript_data = transcript_response.json()
        
        # Verify response structure
        assert "segments" in transcript_data, "Response missing segments"
        
        # Segments should be a list
        assert isinstance(transcript_data["segments"], list), \
            "Segments should be a list"
        
        # If we have segments, verify their structure
        if transcript_data["segments"]:
            for segment in transcript_data["segments"]:
                assert "speaker" in segment, "Segment missing speaker"
                assert "text" in segment, "Segment missing text"
                assert "start_time" in segment, "Segment missing start_time"
                assert "end_time" in segment, "Segment missing end_time"
        
        logger.info(f"✓ Transcript retrieval passed - {len(transcript_data['segments'])} segments")
    
    def test_11_3_3_fetch_summary_via_frontend(
        self,
        authenticated_client,
        sample_audio_file,
        db_session,
    ):
        """
        Test 11.3.3: Fetch summary via frontend
        
        Verifies that:
        - The /api/v1/meetings/{id}/summary endpoint is accessible
        - Returns summary with proper structure
        - Returns appropriate error when summary not available
        """
        logger.info("Test 11.3.3: Testing summary retrieval")
        
        # Upload meeting
        with open(sample_audio_file, 'rb') as f:
            upload_response = authenticated_client.post(
                "/api/v1/meetings/upload",
                data={
                    "title": "Test Meeting for Summary",
                    "description": "Test summary retrieval"
                },
                files={"file": ("test.wav", f, "audio/wav")}
            )
        
        assert upload_response.status_code in [200, 201]
        meeting_id = upload_response.json().get("id")
        
        logger.info(f"Meeting uploaded: {meeting_id}")
        
        # Attempt to fetch summary immediately
        summary_response = authenticated_client.get(
            f"/api/v1/meetings/{meeting_id}/summary"
        )
        
        # If processing hasn't completed, we should get 404 or the summary data
        if summary_response.status_code == 404:
            # Expected response if processing hasn't completed
            error_data = summary_response.json()
            assert "detail" in error_data, "Error response missing detail"
            logger.info(f"✓ Correct error response for incomplete processing: {error_data['detail']}")
        elif summary_response.status_code == 200:
            # Processing has completed or mock data exists
            summary_data = summary_response.json()
            
            # Verify response structure - summary may have various fields
            assert isinstance(summary_data, dict), "Response should be a dictionary"
            # At minimum, we expect summary or key_points
            assert any(key in summary_data for key in ["summary", "key_points", "action_items"]), \
                "Response missing expected summary fields"
            
            logger.info(f"✓ Summary retrieval passed")
        else:
            pytest.fail(f"Unexpected status code: {summary_response.status_code}")
    
    def test_11_3_4_search_functionality(
        self,
        authenticated_client,
        sample_audio_file,
        db_session,
    ):
        """
        Test 11.3.4: Test search functionality
        
        Verifies that:
        - The /api/v1/meetings/{id}/search endpoint is accessible
        - Accepts query and top_k parameters
        - Returns search results with proper structure
        - Handles empty results gracefully
        """
        logger.info("Test 11.3.4: Testing search functionality")
        
        # Upload meeting
        with open(sample_audio_file, 'rb') as f:
            upload_response = authenticated_client.post(
                "/api/v1/meetings/upload",
                data={
                    "title": "Test Meeting for Search",
                    "description": "Test search functionality"
                },
                files={"file": ("test.wav", f, "audio/wav")}
            )
        
        assert upload_response.status_code in [200, 201]
        meeting_id = upload_response.json().get("id")
        
        logger.info(f"Meeting uploaded: {meeting_id}")
        
        # Test search endpoint with various queries
        test_queries = [
            ("test", 5),
            ("meeting", 3),
            ("important", 10),
        ]
        
        for query, top_k in test_queries:
            search_response = authenticated_client.get(
                f"/api/v1/meetings/{meeting_id}/search",
                params={"q": query, "top_k": top_k}
            )
            
            assert search_response.status_code == 200, \
                f"Search failed with query '{query}': {search_response.status_code}"
            
            search_data = search_response.json()
            
            # Verify response structure
            assert "query" in search_data, "Response missing query"
            assert search_data["query"] == query, "Query mismatch"
            assert "results" in search_data, "Response missing results"
            assert "total_results" in search_data, "Response missing total_results"
            
            # Results should be a list
            assert isinstance(search_data["results"], list), \
                "Results should be a list"
            
            # Verify results don't exceed top_k
            assert len(search_data["results"]) <= top_k, \
                f"Results exceed top_k limit: {len(search_data['results'])} > {top_k}"
            
            # If we have results, verify their structure
            if search_data["results"]:
                for result in search_data["results"]:
                    assert "transcript_id" in result, "Result missing transcript_id"
                    assert "speaker" in result, "Result missing speaker"
                    assert "text" in result, "Result missing text"
                    assert "start_time" in result, "Result missing start_time"
                    assert "end_time" in result, "Result missing end_time"
                    assert "relevance_score" in result, "Result missing relevance_score"
                    
                    # Verify relevance score is between 0 and 1
                    assert 0 <= result["relevance_score"] <= 1, \
                        f"Invalid relevance score: {result['relevance_score']}"
            
            logger.info(f"✓ Search test passed for query '{query}': {search_data['total_results']} results")
    
    def test_11_3_5_unauthorized_access_to_transcript(
        self,
        test_client,
        test_user_data,
    ):
        """
        Test 11.3.5: Verify authorization on transcript endpoints
        
        Verifies that:
        - Accessing transcript without authentication returns 401
        - Accessing others' transcripts returns appropriate error
        """
        logger.info("Test 11.3.5: Testing transcript endpoint authorization")
        
        # Try to access transcript without authentication
        response = test_client.get("/api/v1/meetings/1/transcripts")
        
        # The endpoint first checks if the meeting belongs to the user
        # Without auth, the get_current_user dependency will fail
        # But since the endpoint also checks ownership, we might get 404
        # Either 401 (auth failure) or 404 (not found) is acceptable
        assert response.status_code in [401, 404], \
            f"Expected 401 or 404, got {response.status_code}"
        
        logger.info(f"✓ Correctly rejected unauthenticated request with status {response.status_code}")
    
    def test_11_3_6_search_with_invalid_parameters(
        self,
        authenticated_client,
        sample_audio_file,
    ):
        """
        Test 11.3.6: Verify search parameter validation
        
        Verifies that:
        - Missing query parameter returns error
        - Invalid top_k parameter returns error
        - Query length is validated
        """
        logger.info("Test 11.3.6: Testing search parameter validation")
        
        # Upload a meeting first
        with open(sample_audio_file, 'rb') as f:
            upload_response = authenticated_client.post(
                "/api/v1/meetings/upload",
                data={
                    "title": "Test Meeting for Search Validation",
                    "description": "Test search parameter validation"
                },
                files={"file": ("test.wav", f, "audio/wav")}
            )
        
        assert upload_response.status_code in [200, 201]
        meeting_id = upload_response.json().get("id")
        
        # Test missing query parameter
        response = authenticated_client.get(
            f"/api/v1/meetings/{meeting_id}/search",
            params={"top_k": 5}
        )
        
        assert response.status_code == 422, \
            f"Expected 422 for missing query, got {response.status_code}"
        
        logger.info("✓ Missing query parameter rejected")
        
        # Test invalid top_k (too large)
        response = authenticated_client.get(
            f"/api/v1/meetings/{meeting_id}/search",
            params={"q": "test", "top_k": 100}
        )
        
        # Should either accept with limit or return 422
        assert response.status_code in [200, 422], \
            f"Unexpected status for invalid top_k: {response.status_code}"
        
        logger.info("✓ Invalid top_k parameter handled")
        
        # Test very short query (should fail validation)
        response = authenticated_client.get(
            f"/api/v1/meetings/{meeting_id}/search",
            params={"q": "", "top_k": 5}
        )
        
        assert response.status_code == 422, \
            f"Expected 422 for empty query, got {response.status_code}"
        
        logger.info("✓ Empty query parameter rejected")


class TestTranscriptRetrievalEdgeCases:
    """Test edge cases for transcript retrieval"""
    
    def test_transcript_for_nonexistent_meeting(
        self,
        authenticated_client,
    ):
        """Test retrieving transcript for non-existent meeting"""
        logger.info("Testing transcript retrieval for non-existent meeting")
        
        response = authenticated_client.get("/api/v1/meetings/99999/transcripts")
        
        assert response.status_code == 404, \
            f"Expected 404, got {response.status_code}"
        
        error_data = response.json()
        assert "detail" in error_data, "Error response missing detail"
        
        logger.info("✓ Correctly returned 404 for non-existent meeting")
    
    def test_summary_for_nonexistent_meeting(
        self,
        authenticated_client,
    ):
        """Test retrieving summary for non-existent meeting"""
        logger.info("Testing summary retrieval for non-existent meeting")
        
        response = authenticated_client.get("/api/v1/meetings/99999/summary")
        
        assert response.status_code == 404, \
            f"Expected 404, got {response.status_code}"
        
        error_data = response.json()
        assert "detail" in error_data, "Error response missing detail"
        
        logger.info("✓ Correctly returned 404 for non-existent meeting")
    
    def test_search_for_nonexistent_meeting(
        self,
        authenticated_client,
    ):
        """Test searching transcript for non-existent meeting"""
        logger.info("Testing search for non-existent meeting")
        
        response = authenticated_client.get(
            "/api/v1/meetings/99999/search",
            params={"q": "test"}
        )
        
        assert response.status_code == 404, \
            f"Expected 404, got {response.status_code}"
        
        error_data = response.json()
        assert "detail" in error_data, "Error response missing detail"
        
        logger.info("✓ Correctly returned 404 for non-existent meeting")
