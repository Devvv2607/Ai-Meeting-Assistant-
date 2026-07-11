"""
Pytest configuration and fixtures for integration tests
"""

import pytest
import os
import sys
from pathlib import Path
import logging

# Add backend app to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def test_client():
    """Create test client for FastAPI app"""
    from fastapi.testclient import TestClient
    from app.main import app
    
    client = TestClient(app)
    logger.info("TestClient created")
    return client


@pytest.fixture
def db_session():
    """Create database session for testing"""
    from app.database import SessionLocal
    
    db = SessionLocal()
    yield db
    db.close()


@pytest.fixture
def test_user_data():
    """Sample user data for testing"""
    return {
        "email": f"test_{os.urandom(4).hex()}@example.com",
        "password": "test_password_123!@#",
        "full_name": "Test User"
    }


@pytest.fixture
def authenticated_client(test_client, test_user_data):
    """
    Create authenticated test client
    
    Automatically registers and logs in a test user
    """
    # Register user
    register_response = test_client.post(
        "/api/v1/auth/register",
        json={
            "email": test_user_data["email"],
            "password": test_user_data["password"],
            "full_name": test_user_data["full_name"]
        }
    )
    
    logger.info(f"Registration response: {register_response.status_code}")
    
    # Login
    login_response = test_client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user_data["email"],
            "password": test_user_data["password"]
        }
    )
    
    assert login_response.status_code == 200, \
        f"Login failed: {login_response.status_code} - {login_response.json()}"
    
    token = login_response.json()["access_token"]
    
    # Create new client with auth headers
    auth_client = test_client
    auth_client.headers = {"Authorization": f"Bearer {token}"}
    
    logger.info("Authenticated client created")
    return auth_client


@pytest.fixture
def current_user_id(test_client, test_user_data):
    """Get ID of current test user"""
    # Login to get token
    login_response = test_client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user_data["email"],
            "password": test_user_data["password"]
        }
    )
    
    if login_response.status_code != 200:
        return None
    
    token = login_response.json()["access_token"]
    
    # Get user info
    test_client.headers = {"Authorization": f"Bearer {token}"}
    user_response = test_client.get("/api/v1/auth/me")
    
    if user_response.status_code == 200:
        return user_response.json()["id"]
    
    return None


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


def pytest_configure(config):
    """Pytest configuration hook"""
    logger.info("Starting test suite")


def pytest_collection_modifyitems(config, items):
    """Modify test collection"""
    for item in items:
        # Add integration test marker
        if "test_" in item.nodeid:
            item.add_marker(pytest.mark.integration)
