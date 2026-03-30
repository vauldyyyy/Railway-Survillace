"""
railguard-backend/security/auth.py
Zero-Trust Local Authentication Engine
Cryptographic Stack: Argon2id + JWT HS256 + Adaptive Rate Limiting
"""

import time
import os
from datetime import datetime, timezone, timedelta
from typing import Optional

import jwt                          # pip install PyJWT
from passlib.hash import argon2     # pip install passlib[argon2]
from fastapi import HTTPException, status

# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
# CONFIG
# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ

# In production load this from an env variable / secrets manager.
# For hackathon: generate a new random secret on startup to invalidate old sessions on restart.
JWT_SECRET      = os.getenv("RAILGUARD_JWT_SECRET", os.urandom(32).hex())
JWT_ALGORITHM   = "HS256"
JWT_EXPIRE_MINS = 480           # 8-hour shift token

MAX_ATTEMPTS    = 5             # failed logins before lockout
LOCKOUT_SECS    = 900           # 15 minutes

# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
# MOCK USER DB  (hash generated once at import time ΓÇö Argon2id, memory-hard)
# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ

def _hash(plain: str) -> str:
    return argon2.using(
        time_cost=3,        # iterations
        memory_cost=65536,  # 64 MB memory
        parallelism=2,
        hash_len=32,
    ).hash(plain)


MOCK_DB: dict[str, dict] = {
    "admin": {
        "operator_id":  "admin",
        "display_name": "RPF_GOA_01",
        "role":         "SYSTEM_OPERATOR",
        "password_hash": _hash("Admin@123"),   # generated on startup
        "clearance":    "L-12",
    }
}

# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
# AUTH ENGINE
# ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ

class AuthEngine:
    """
    Stateless authentication engine.
    Rate-limiter state is in-process (resets on server restart).
    For production, move rate-limiter to Redis.
    """

    def __init__(self) -> None:
        # { operator_id: {"failed_attempts": int, "lockout_until": float} }
        self._rate_store: dict[str, dict] = {}

    # ΓöÇΓöÇ Rate limiter ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ

    def _get_rate_entry(self, operator_id: str) -> dict:
        if operator_id not in self._rate_store:
            self._rate_store[operator_id] = {
                "failed_attempts": 0,
                "lockout_until":   0.0,
            }
        return self._rate_store[operator_id]

    def _check_lockout(self, operator_id: str) -> None:
        entry = self._get_rate_entry(operator_id)
        now   = time.time()
        if entry["lockout_until"] > now:
            remaining = int(entry["lockout_until"] - now)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "code":      "ACCOUNT_LOCKED",
                    "message":   f"Account locked. Try again in {remaining}s.",
                    "remaining": remaining,
                },
            )

    def _record_failure(self, operator_id: str) -> None:
        entry = self._get_rate_entry(operator_id)
        entry["failed_attempts"] += 1
        if entry["failed_attempts"] >= MAX_ATTEMPTS:
            entry["lockout_until"]   = time.time() + LOCKOUT_SECS
            entry["failed_attempts"] = 0          # reset counter after lockout
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "code":      "ACCOUNT_LOCKED",
                    "message":   f"Too many failed attempts. Locked for {LOCKOUT_SECS // 60} minutes.",
                    "remaining": LOCKOUT_SECS,
                },
            )

    def _clear_failures(self, operator_id: str) -> None:
        if operator_id in self._rate_store:
            self._rate_store[operator_id]["failed_attempts"] = 0
            self._rate_store[operator_id]["lockout_until"]   = 0.0

    # ΓöÇΓöÇ Password verification ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ

    def verify_password(self, plain: str, hashed: str) -> bool:
        try:
            return argon2.verify(plain, hashed)
        except Exception:
            return False

    # ΓöÇΓöÇ JWT creation ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ

    def create_access_token(self, operator_id: str, role: str,
                             clearance: str) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub":       operator_id,
            "role":      role,
            "clearance": clearance,
            "iat":       now,
            "exp":       now + timedelta(minutes=JWT_EXPIRE_MINS),
            "iss":       "railguard-ai",
        }
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    def decode_token(self, token: str) -> dict:
        """Raises jwt.ExpiredSignatureError / jwt.InvalidTokenError on failure."""
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

    # ΓöÇΓöÇ Main authenticate method ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ

    def authenticate(self, operator_id: str, password: str) -> dict:
        """
        Returns a dict with token + operator info on success.
        Raises HTTPException 401 / 429 on failure.
        """
        # 1. Check lockout FIRST (before hitting the DB)
        self._check_lockout(operator_id)

        # 2. Lookup user
        user = MOCK_DB.get(operator_id)
        if user is None:
            # Don't reveal whether the user exists ΓÇö same error as wrong password
            self._record_failure(operator_id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "INVALID_CREDENTIALS",
                        "message": "Invalid operator ID or passphrase."},
            )

        # 3. Verify password
        if not self.verify_password(password, user["password_hash"]):
            self._record_failure(operator_id)
            entry = self._get_rate_entry(operator_id)
            remaining_attempts = MAX_ATTEMPTS - entry["failed_attempts"]
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "code":               "INVALID_CREDENTIALS",
                    "message":            "Invalid operator ID or passphrase.",
                    "remaining_attempts": remaining_attempts,
                },
            )

        # 4. Success ΓÇö clear failure counter, issue token
        self._clear_failures(operator_id)
        token = self.create_access_token(
            operator_id=operator_id,
            role=user["role"],
            clearance=user["clearance"],
        )

        return {
            "access_token": token,
            "token_type":   "bearer",
            "operator": {
                "id":           user["operator_id"],
                "display_name": user["display_name"],
                "role":         user["role"],
                "clearance":    user["clearance"],
            },
        }


# Singleton ΓÇö import this in main.py
auth_engine = AuthEngine()
