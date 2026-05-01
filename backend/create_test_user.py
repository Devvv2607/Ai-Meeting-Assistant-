"""
Create or update test user for API testing
"""

from app.database import SessionLocal
from app.models.user import User
from app.utils.auth_utils import hash_password

def create_test_user():
    db = SessionLocal()
    try:
        # Check if user exists
        user = db.query(User).filter(User.email == "test@example.com").first()
        
        if user:
            # Update password
            user.password_hash = hash_password("testpassword123")
            print(f"Updated password for existing user: {user.email}")
        else:
            # Create new user
            user = User(
                email="test@example.com",
                full_name="Test User",
                password_hash=hash_password("testpassword123")
            )
            db.add(user)
            print(f"Created new user: test@example.com")
        
        db.commit()
        print("✓ Test user ready")
        print("  Email: test@example.com")
        print("  Password: testpassword123")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_test_user()
