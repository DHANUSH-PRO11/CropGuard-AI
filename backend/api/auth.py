import os
import hmac
import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, Header
from jose import jwt, JWTError
from supabase import Client

from config.database import get_supabase
from config import local_db
from schemas import schemas

logger = logging.getLogger(__name__)

router = APIRouter()

# Secret key for JWT signing
JWT_SECRET = os.environ.get("JWT_SECRET", "agronex-secure-jwt-signing-key-2026")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30

def hash_password(password: str) -> str:
    """Hashes password with PBKDF2-HMAC-SHA256 and unique 16-byte salt."""
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return f"{salt.hex()}:{key.hex()}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies plain password against stored salt:hash."""
    try:
        parts = hashed_password.split(":")
        if len(parts) != 2:
            return False
        salt = bytes.fromhex(parts[0])
        expected_key = bytes.fromhex(parts[1])
        actual_key = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, 100_000)
        return hmac.compare_digest(expected_key, actual_key)
    except Exception:
        return False

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        return None

@router.post("/register", response_model=schemas.UserResponse)
def register(user: schemas.UserCreate, db: Optional[Client] = Depends(get_supabase)):
    """Registers a new farmer user in Supabase or local offline storage."""
    if len(user.password.strip()) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters long."
        )

    clean_mobile = user.mobile.strip()
    clean_email = user.email.strip().lower() if user.email else None
    hashed = hash_password(user.password)

    # 1. Supabase Cloud DB branch if available
    if db is not None:
        try:
            # Check for existing mobile/email
            query = db.table("users").select("id").eq("mobile", clean_mobile)
            existing = query.execute()
            if existing.data and len(existing.data) > 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A user with this mobile number already exists."
                )

            record = {
                "name": user.name.strip(),
                "mobile": clean_mobile,
                "email": clean_email,
                "hashed_password": hashed,
                "location": user.location or "Tamil Nadu",
                "preferred_language": user.preferred_language or "en"
            }
            res = db.table("users").insert(record).execute()
            created = res.data[0] if res.data else record
            return {
                "id": created.get("id", clean_mobile),
                "name": created.get("name", user.name),
                "mobile": created.get("mobile", clean_mobile),
                "email": created.get("email"),
                "location": created.get("location"),
                "preferred_language": created.get("preferred_language", "en")
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"Supabase registration error: {e}. Falling back to local database.")

    # 2. Local Fallback Database branch
    existing_user = local_db.find_user_by_identifier(clean_mobile)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this mobile number already exists."
        )

    saved = local_db.save_user({
        "name": user.name.strip(),
        "mobile": clean_mobile,
        "email": clean_email,
        "hashed_password": hashed,
        "location": user.location or "Tamil Nadu",
        "preferred_language": user.preferred_language or "en"
    })
    return saved

@router.post("/login")
def login(credentials: schemas.UserLogin, db: Optional[Client] = Depends(get_supabase)):
    """Authenticates farmer with mobile/email and password, returning JWT access token."""
    identifier = credentials.username.strip()
    password = credentials.password

    matched_user = None

    # 1. Try Supabase Cloud DB if available
    if db is not None:
        try:
            # Check mobile first
            res = db.table("users").select("*").eq("mobile", identifier).execute()
            if res.data and len(res.data) > 0:
                matched_user = res.data[0]
            else:
                # Check email
                res = db.table("users").select("*").eq("email", identifier.lower()).execute()
                if res.data and len(res.data) > 0:
                    matched_user = res.data[0]
        except Exception as e:
            logger.warning(f"Supabase login lookup failed: {e}. Falling back to local DB.")

    # 2. Try Local Fallback DB
    if not matched_user:
        matched_user = local_db.find_user_by_identifier(identifier)

    # 3. Verify password
    if not matched_user or not verify_password(password, matched_user.get("hashed_password", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials. Please verify your mobile number/email and password."
        )

    user_payload = {
        "id": str(matched_user.get("id")),
        "name": matched_user.get("name"),
        "mobile": matched_user.get("mobile"),
        "email": matched_user.get("email"),
        "location": matched_user.get("location"),
        "preferred_language": matched_user.get("preferred_language", "en")
    }

    token = create_access_token(data={"sub": user_payload["id"], "name": user_payload["name"], "mobile": user_payload["mobile"]})

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user_payload
    }

@router.get("/me", response_model=schemas.UserResponse)
def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Optional[Client] = Depends(get_supabase)
):
    """Returns the authenticated user details from JWT token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization token required."
        )

    token = authorization.split(" ", 1)[1].strip()
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token."
        )

    user_id = payload["sub"]

    # Check Supabase
    if db is not None:
        try:
            res = db.table("users").select("id, name, mobile, email, location, preferred_language").eq("id", user_id).execute()
            if res.data and len(res.data) > 0:
                return res.data[0]
        except Exception as e:
            logger.warning(f"Supabase lookup error for user {user_id}: {e}")

    # Check local db
    local_user = local_db.find_user_by_id(user_id)
    if local_user:
        return local_user

    # Fallback to payload data
    return {
        "id": user_id,
        "name": payload.get("name", "Farmer"),
        "mobile": payload.get("mobile", "9876543210"),
        "email": None,
        "location": "Tamil Nadu",
        "preferred_language": "en"
    }
