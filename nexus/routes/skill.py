from __future__ import annotations

import base64
import io
import os
import zipfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from config import SKILL_DOWNLOAD_ENABLED

router = APIRouter(tags=["skill"])

_SKILL_DIR = Path(
    os.environ.get(
        "SKILL_DIR",
        str(Path(__file__).resolve().parent.parent.parent / "agent-skill"),
    )
)


def _build_skill_zip() -> bytes:
    if not _SKILL_DIR.is_dir():
        raise HTTPException(status_code=503, detail="Skill directory not found")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(_SKILL_DIR.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(_SKILL_DIR))
    return buf.getvalue()


def _read_skill_markdown() -> str:
    if not _SKILL_DIR.is_dir():
        raise HTTPException(status_code=503, detail="Skill directory not found")
    skill_md = _SKILL_DIR / "SKILL.md"
    if not skill_md.is_file():
        raise HTTPException(status_code=503, detail="Skill file not found")
    return skill_md.read_text(encoding="utf-8")


@router.get("/skill")
async def get_skill():
    """Return SKILL.md instructions for agent setup."""
    return Response(
        content=_read_skill_markdown(),
        media_type="text/markdown; charset=utf-8",
    )


@router.get("/skill/download")
async def download_skill(request: Request):
    """Download the skill as a signed zip package.

    The ``X-Skill-Signature`` response header contains an Ed25519 detached
    signature of the zip bytes.  Verify it against the public key returned
    by ``GET /skill/pubkey``.
    """
    if not SKILL_DOWNLOAD_ENABLED:
        raise HTTPException(
            status_code=503, detail="Skill download is temporarily disabled"
        )

    signing_key = request.app.state.signing_key
    zip_bytes = _build_skill_zip()
    sig = signing_key.sign(zip_bytes).signature

    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": 'attachment; filename="fleet-of-institutes-skill.zip"',
            "X-Skill-Signature": base64.b64encode(sig).decode(),
            "X-Skill-Public-Key": base64.b64encode(
                bytes(signing_key.verify_key)
            ).decode(),
        },
    )


@router.get("/skill/pubkey")
async def get_skill_pubkey(request: Request):
    """Return the public key used to sign skill packages."""
    signing_key = request.app.state.signing_key
    return {
        "public_key": base64.b64encode(bytes(signing_key.verify_key)).decode(),
        "algorithm": "Ed25519",
    }
