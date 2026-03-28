"""
Database-backed multi-user authentication for Scout.
- Users register with a username + password
- A one-time recovery code is generated and shown at registration (save it!)
- Tokens are HMAC-SHA256 signed, no external JWT library needed

SCOUT_SECRET_KEY must be set in .env for tokens to work across restarts.
If not set, a random key is generated at startup (tokens expire on restart).
"""
import base64
import hashlib
import hmac
import json
import os
import secrets
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.db.database import get_db
from backend.models.user import User

router = APIRouter()
security = HTTPBearer(auto_error=False)

# Fall back to a random key if not configured (tokens won't survive restart)
_SECRET_KEY = os.getenv("SCOUT_SECRET_KEY") or secrets.token_hex(32)
AUTH_ENABLED = True  # Always enabled — DB-backed auth is always on


# ---------------------------------------------------------------------------
# Token helpers
# ---------------------------------------------------------------------------

def _sign(payload: str) -> str:
    return hmac.new(_SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()


def create_token(user_id: str, username: str) -> str:
    payload = json.dumps(
        {"sub": user_id, "username": username, "iat": int(time.time())},
        separators=(",", ":"),
    )
    encoded = base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")
    sig = _sign(encoded)
    return f"{encoded}.{sig}"


def verify_token(token: str) -> dict | None:
    """Returns decoded payload dict or None if invalid."""
    try:
        encoded, sig = token.rsplit(".", 1)
        if not hmac.compare_digest(_sign(encoded), sig):
            return None
        return json.loads(base64.urlsafe_b64decode(encoded + "=="))
    except Exception:
        return None


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------

async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Returns {'id': ..., 'username': ...} or raises 401."""
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = verify_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # Verify user still exists and is active
    result = await db.execute(select(User).where(User.id == payload["sub"]))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Account not found or deactivated")

    return {"id": user.id, "username": user.username}


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    confirm_password: str


class RecoverRequest(BaseModel):
    username: str
    recovery_code: str
    new_password: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/register")
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new account. Returns a one-time recovery code — save it!"""
    if len(body.username.strip()) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters")
    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    if body.password != body.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    username = body.username.strip().lower()

    # Check unique
    result = await db.execute(select(User).where(User.username == username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already taken")

    # Generate recovery code
    recovery_code = secrets.token_urlsafe(16)  # ~22 characters, easy to save
    recovery_code_hash = hash_password(recovery_code)

    user = User(
        id=str(uuid.uuid4()),
        username=username,
        password_hash=hash_password(body.password),
        recovery_code_hash=recovery_code_hash,
    )
    db.add(user)
    await db.commit()

    token = create_token(user.id, user.username)
    return {
        "token": token,
        "username": user.username,
        "recovery_code": recovery_code,  # Only shown ONCE — user must save this
        "message": "Account created. Save your recovery code — it cannot be shown again.",
    }


@router.post("/login")
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Exchange credentials for a bearer token."""
    username = body.username.strip().lower()
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    if not user or not user.is_active or user.password_hash != hash_password(body.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_token(user.id, user.username)
    return {"token": token, "username": user.username}


@router.post("/recover")
async def recover_account(body: RecoverRequest, db: AsyncSession = Depends(get_db)):
    """Reset password using a recovery code."""
    if len(body.new_password) < 6:
        raise HTTPException(status_code=400, detail="New password must be at least 6 characters")

    username = body.username.strip().lower()
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    if not user or not user.recovery_code_hash:
        raise HTTPException(status_code=400, detail="User not found or no recovery code set")

    if user.recovery_code_hash != hash_password(body.recovery_code):
        raise HTTPException(status_code=400, detail="Invalid recovery code")

    # Reset password and generate a new recovery code
    new_recovery_code = secrets.token_urlsafe(16)
    user.password_hash = hash_password(body.new_password)
    user.recovery_code_hash = hash_password(new_recovery_code)
    await db.commit()

    token = create_token(user.id, user.username)
    return {
        "token": token,
        "username": user.username,
        "new_recovery_code": new_recovery_code,
        "message": "Password reset successful. Save your new recovery code.",
    }


@router.get("/me")
async def me(current_user: dict = Depends(get_current_user)):
    return {"username": current_user["username"], "user_id": current_user["id"], "auth_enabled": True}
