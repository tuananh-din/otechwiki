import os
import sys
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError

# Mocking settings from config
SECRET_KEY = "change-this-secret-key-in-production"
ALGORITHM = "HS256"

def test_jwt():
    print(f"Testing JWT with SECRET={SECRET_KEY}, ALGO={ALGORITHM}")
    
    # payload
    payload = {"sub": "1", "exp": datetime.now(timezone.utc) + timedelta(minutes=60)}
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    print(f"Generated Token: {token}")
    
    try:
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        print(f"Decoded Payload: {decoded}")
        assert decoded["sub"] == "1"
        print("✅ JWT Encode/Decode Match!")
    except JWTError as e:
        print(f"❌ JWT Error: {e}")

if __name__ == "__main__":
    test_jwt()
