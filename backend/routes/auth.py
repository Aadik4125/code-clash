from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import os

from fastapi import APIRouter, Depends, Header, HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session as DBSession

from config import JWT_ACCESS_TOKEN_MINUTES, JWT_ALGORITHM, JWT_SECRET_KEY
from database import get_db
from models.user import User


router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class SignupRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    age: int | None = None
    gender: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


def _hash_password(password: str) -> str:
    return pwd_context.hash(password)


def _verify_legacy_pbkdf2(password: str, hashed_password: str) -> bool:
    try:
        scheme, salt_hex, digest_hex = hashed_password.split("$", 2)
    except ValueError:
        return False
    if scheme != "pbkdf2_sha256":
        return False
    salt = bytes.fromhex(salt_hex)
    expected = bytes.fromhex(digest_hex)
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
    return hmac.compare_digest(candidate, expected)


def _verify_password(password: str, hashed_password: str | None) -> bool:
    if not hashed_password:
        return False
    if hashed_password.startswith("pbkdf2_sha256$"):
        return _verify_legacy_pbkdf2(password, hashed_password)
    try:
        return pwd_context.verify(password, hashed_password)
    except Exception:
        return False


def _create_access_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=JWT_ACCESS_TOKEN_MINUTES)).timestamp()),
        "type": "access",
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def _serialize_user(user: User) -> dict[str, object | None]:
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "age": user.age,
        "gender": user.gender,
        "latest_csi_score": user.latest_csi_score,
        "total_sessions": user.total_sessions,
        "last_session_at": user.last_session_at.isoformat() if user.last_session_at else None,
    }


def _get_bearer_token(authorization: str | None) -> str:
    raw = (authorization or "").strip()
    if not raw.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    return raw.split(" ", 1)[1].strip()


def _get_current_user(db: DBSession, authorization: str | None) -> User:
    token = _get_bearer_token(authorization)
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_id = int(str(payload.get("sub")))
    except (JWTError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def require_current_user(
    authorization: str | None = Header(default=None),
    db: DBSession = Depends(get_db),
) -> User:
    return _get_current_user(db, authorization)


@router.post("/auth/signup")
def signup(payload: SignupRequest, db: DBSession = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")

    user = User(
        name=payload.name,
        email=payload.email,
        age=payload.age,
        gender=payload.gender,
        password_hash=_hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "access_token": _create_access_token(user.id),
        "token_type": "bearer",
        "user": _serialize_user(user),
    }


@router.post("/auth/login")
def login(payload: LoginRequest, db: DBSession = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not _verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # Upgrade legacy password hashes to bcrypt after a successful login.
    if user.password_hash and user.password_hash.startswith("pbkdf2_sha256$"):
        user.password_hash = _hash_password(payload.password)
        db.commit()
        db.refresh(user)

    return {
        "access_token": _create_access_token(user.id),
        "token_type": "bearer",
        "user": _serialize_user(user),
    }


@router.get("/auth/me")
def me(
    authorization: str | None = Header(default=None),
    db: DBSession = Depends(get_db),
):
    user = _get_current_user(db, authorization)
    return {"user": _serialize_user(user)}
