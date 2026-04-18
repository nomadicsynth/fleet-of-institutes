from __future__ import annotations

import base64
import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from config import FEDERATION_ENABLED, FEDERATION_MAX_INSTITUTE_BODY_BYTES
from database import (
    get_paper,
    get_paper_by_global_id,
    get_peers,
    get_papers_since,
    insert_peer,
    remove_peer,
    get_peer_by_url,
    update_peer_public_key,
    update_peer_last_seen,
)
from federation import (
    ingest_envelope,
    verify_envelope,
    forward_to_peers,
    sign_envelope,
)
from models import FederationEnvelope, NexusIdentity, PeerOut

log = logging.getLogger(__name__)

router = APIRouter(prefix="/federation", tags=["federation"])


def _require_federation():
    if not FEDERATION_ENABLED:
        raise HTTPException(status_code=503, detail="Federation is disabled")


@router.post("/ingest", status_code=202)
async def receive_envelope(
    envelope: FederationEnvelope,
    request: Request,
    background_tasks: BackgroundTasks,
):
    """Accept a federation envelope from a peer Nexus."""
    _require_federation()

    # Guard against oversized base64 payloads (DoS).
    if envelope.institute_body_b64:
        approx_decoded = (len(envelope.institute_body_b64) * 3) // 4
        if approx_decoded > FEDERATION_MAX_INSTITUTE_BODY_BYTES:
            raise HTTPException(status_code=413, detail="Federation envelope body too large")

    if not verify_envelope(envelope):
        raise HTTPException(status_code=401, detail="Invalid envelope signature")

    conn = request.app.state.db
    nexus_id = request.app.state.nexus_id

    result = await ingest_envelope(
        conn, envelope, nexus_id, request.app.state.signing_key,
    )

    return {"status": "accepted" if result else "duplicate"}


@router.get("/papers/{global_id}")
async def serve_paper_content(global_id: str, request: Request):
    """Serve full paper content for a given global_id. Used by peers for lazy fetch."""
    conn = request.app.state.db
    paper = get_paper_by_global_id(conn, global_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    if not paper.get("content_cached", True):
        raise HTTPException(status_code=404, detail="Content not cached on this Nexus")
    return {
        "global_id": global_id,
        "content": paper.get("content", ""),
        "id": paper["id"],
    }


@router.get("/sync")
async def sync_envelopes(
    request: Request,
    since: str = "",
    limit: int = 100,
):
    """Return metadata envelopes for catch-up sync. Used by peers on startup."""
    conn = request.app.state.db
    limit = min(limit, 500)

    papers = get_papers_since(conn, since, limit)
    nexus_id = request.app.state.nexus_id
    signing_key = request.app.state.signing_key

    envelopes = []
    for paper in papers:
        envelope = FederationEnvelope(
            entity_type="paper_metadata",
            payload={
                "id": paper["id"],
                "institute_id": paper["institute_id"],
                "title": paper["title"],
                "summary": paper.get("summary", ""),
                "tags": paper.get("tags", ""),
                "timestamp": paper["timestamp"],
                "supersedes": paper.get("supersedes", ""),
                "retracts": paper.get("retracts", ""),
                "external_references": paper.get("external_references", ""),
                "global_id": paper.get("global_id", ""),
            },
            institute_public_key=paper.get("institute_public_key", ""),
            origin_nexus=paper.get("origin_nexus", "") or nexus_id,
            hops=[nexus_id],
            global_id=paper.get("global_id", ""),
        )
        signed = sign_envelope(envelope, signing_key)
        envelopes.append(signed.model_dump())

    return {"envelopes": envelopes, "count": len(envelopes)}


@router.get("/identity", response_model=NexusIdentity)
async def get_identity(request: Request):
    """Return this Nexus's public key. Used during peering handshake."""
    nexus_id = request.app.state.nexus_id
    return NexusIdentity(public_key=nexus_id)


@router.post("/peers", response_model=PeerOut, status_code=201)
async def add_peer(request: Request, url: str):
    """Register a new peer Nexus."""
    _require_federation()
    conn = request.app.state.db

    url = url.rstrip("/")
    existing = get_peer_by_url(conn, url)
    if existing:
        return existing

    import httpx
    public_key = ""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{url}/federation/identity")
        if resp.status_code == 200:
            public_key = resp.json().get("public_key", "")
    except Exception as exc:
        log.warning("Could not reach peer %s for identity handshake: %s", url, exc)

    peer = insert_peer(conn, url, public_key)
    return peer


@router.get("/peers", response_model=list[PeerOut])
async def list_peers(request: Request):
    """List all known peers."""
    conn = request.app.state.db
    return get_peers(conn)


@router.delete("/peers/{peer_id}", status_code=204)
async def delete_peer(peer_id: str, request: Request):
    """Remove a peer."""
    _require_federation()
    conn = request.app.state.db
    if not remove_peer(conn, peer_id):
        raise HTTPException(status_code=404, detail="Peer not found")
