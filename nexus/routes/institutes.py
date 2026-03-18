from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from config import REGISTRATION_ENABLED, FEDERATION_ENABLED
from database import insert_institute, get_institute
from models import InstituteCreate, InstituteOut

router = APIRouter(prefix="/institutes", tags=["institutes"])


@router.post("", response_model=InstituteOut, status_code=201)
async def register_institute(
    body: InstituteCreate,
    request: Request,
    background_tasks: BackgroundTasks,
):
    if not REGISTRATION_ENABLED:
        raise HTTPException(
            status_code=503, detail="Registration is temporarily disabled"
        )

    conn = request.app.state.db
    try:
        inst = insert_institute(
            conn,
            name=body.name,
            public_key=body.public_key,
            mission=body.mission,
            tags=body.tags,
        )
    except Exception as e:
        if "Duplicate entry" in str(e) or "UNIQUE constraint" in str(e):
            raise HTTPException(status_code=409, detail="Public key already registered")
        raise

    if FEDERATION_ENABLED:
        from federation import build_institute_envelope, forward_to_peers
        nexus_id = request.app.state.nexus_id
        signing_key = request.app.state.signing_key
        envelope = build_institute_envelope(inst, nexus_id)
        background_tasks.add_task(forward_to_peers, conn, envelope, signing_key)

    return inst


@router.get("/{institute_id}", response_model=InstituteOut)
async def get_institute_profile(institute_id: str, request: Request):
    conn = request.app.state.db
    inst = get_institute(conn, institute_id)
    if not inst:
        raise HTTPException(status_code=404, detail="Institute not found")
    return inst
