from __future__ import annotations

import base64
from datetime import datetime, timezone

import nacl.signing
import nacl.exceptions
from fastapi import Header, HTTPException, Request

from config import TIMESTAMP_MAX_AGE_SECONDS, WRITES_ENABLED
from database import get_institute_by_pubkey


async def get_request_body_bytes(request: Request) -> bytes:
    return await request.body()


def verify_signature(payload: bytes, signature_b64: str, public_key_b64: str) -> bool:
    try:
        sig = base64.b64decode(signature_b64)
        pubkey_bytes = base64.b64decode(public_key_b64)
        verify_key = nacl.signing.VerifyKey(pubkey_bytes)
        verify_key.verify(payload, sig)
        return True
    except (nacl.exceptions.BadSignatureError, Exception):
        return False


def _check_timestamp(timestamp_str: str) -> None:
    """Reject requests with stale or far-future timestamps."""
    try:
        ts = datetime.fromisoformat(timestamp_str)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=400,
            detail="Invalid X-Timestamp format (expected ISO 8601)",
        )
    age = abs((datetime.now(timezone.utc) - ts).total_seconds())
    if age > TIMESTAMP_MAX_AGE_SECONDS:
        raise HTTPException(
            status_code=401,
            detail=f"Request timestamp expired (max age {TIMESTAMP_MAX_AGE_SECONDS}s)",
        )


async def require_signed(
    request: Request,
    x_signature: str = Header(...),
    x_public_key: str = Header(...),
    x_timestamp: str = Header(...),
) -> dict:
    """FastAPI dependency that verifies Ed25519 signed requests.

    The signed payload is ``body + b"\\n" + timestamp.encode()`` so that the
    timestamp is covered by the signature and cannot be altered by a relay.
    Returns the institute dict for the authenticated caller.
    """
    if not WRITES_ENABLED:
        raise HTTPException(
            status_code=503, detail="Write operations are temporarily disabled"
        )

    _check_timestamp(x_timestamp)

    body = await request.body()
    signed_payload = body + b"\n" + x_timestamp.encode()

    if not verify_signature(signed_payload, x_signature, x_public_key):
        raise HTTPException(status_code=401, detail="Invalid signature")

    conn = request.app.state.db
    institute = get_institute_by_pubkey(conn, x_public_key)
    if not institute:
        raise HTTPException(
            status_code=403,
            detail="Public key not registered to any institute",
        )

    return institute
