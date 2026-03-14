from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from database import insert_institute, get_institute
from models import InstituteCreate, InstituteOut

router = APIRouter(prefix="/institutes", tags=["institutes"])


@router.post("", response_model=InstituteOut, status_code=201)
async def register_institute(body: InstituteCreate, request: Request):
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
        if "UNIQUE constraint" in str(e):
            raise HTTPException(status_code=409, detail="Public key already registered")
        raise
    return inst


@router.get("/{institute_id}", response_model=InstituteOut)
async def get_institute_profile(institute_id: str, request: Request):
    conn = request.app.state.db
    inst = get_institute(conn, institute_id)
    if not inst:
        raise HTTPException(status_code=404, detail="Institute not found")
    return inst
