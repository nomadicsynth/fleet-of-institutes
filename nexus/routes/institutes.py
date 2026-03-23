from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from pymysql.constants import ER
from pymysql.err import IntegrityError, OperationalError

from config import REGISTRATION_ENABLED, FEDERATION_ENABLED
from database import insert_institute, get_institute
from models import InstituteCreate, InstituteOut

router = APIRouter(prefix="/institutes", tags=["institutes"])


def _dup_key_message(exc: BaseException) -> str | None:
    """MySQL/MariaDB duplicate key: errno 1062, message names the unique index."""
    if not isinstance(exc, (IntegrityError, OperationalError)) or len(exc.args) < 2:
        return None
    if exc.args[0] != ER.DUP_ENTRY:
        return None
    return str(exc.args[1])


@router.post("/register", response_model=InstituteOut, status_code=201)
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
            origin_nexus=request.app.state.nexus_id,
        )
    except (IntegrityError, OperationalError) as e:
        msg = _dup_key_message(e)
        if msg is not None:
            if "uq_origin_name" in msg:
                raise HTTPException(
                    status_code=409,
                    detail="Institute name already taken on this Nexus",
                ) from e
            if "uq_pubkey" in msg:
                raise HTTPException(
                    status_code=409,
                    detail="Public key already registered",
                ) from e
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
