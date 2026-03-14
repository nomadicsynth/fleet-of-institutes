from __future__ import annotations

import base64

import nacl.signing
import nacl.exceptions
from fastapi import Header, HTTPException, Request

from database import get_institute_by_pubkey


async def get_request_body_bytes(request: Request) -> bytes:
    return await request.body()


def verify_signature(body: bytes, signature_b64: str, public_key_b64: str) -> bool:
    try:
        sig = base64.b64decode(signature_b64)
        pubkey_bytes = base64.b64decode(public_key_b64)
        verify_key = nacl.signing.VerifyKey(pubkey_bytes)
        verify_key.verify(body, sig)
        return True
    except (nacl.exceptions.BadSignatureError, Exception):
        return False


async def require_signed(
    request: Request,
    x_signature: str = Header(...),
    x_public_key: str = Header(...),
) -> dict:
    """FastAPI dependency that verifies Ed25519 signed requests.

    Returns the institute dict for the authenticated caller.
    """
    body = await request.body()

    if not verify_signature(body, x_signature, x_public_key):
        raise HTTPException(status_code=401, detail="Invalid signature")

    conn = request.app.state.db
    institute = get_institute_by_pubkey(conn, x_public_key)
    if not institute:
        raise HTTPException(status_code=403, detail="Public key not registered to any institute")

    return institute
