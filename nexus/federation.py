"""Federation logic for Nexus-to-Nexus communication.

Push metadata, pull content. Envelopes are doubly signed: institute key
proves authorship, Nexus key proves relay provenance.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging

import httpx
import nacl.signing
import nacl.exceptions

from config import (
    FEDERATION_ENABLED,
    FEDERATION_TIMEOUT,
    FEDERATION_MAX_INSTITUTE_BODY_BYTES,
)
from database import (
    Connection,
    compute_global_id,
    generate_paper_id,
    get_institute_by_pubkey,
    get_paper_by_global_id,
    get_peers,
    insert_institute,
    insert_paper,
    log_federation_delivery,
    mark_paper_cached,
    update_peer_last_seen,
)
from models import FederationEnvelope

log = logging.getLogger(__name__)


# ── Envelope signing & verification ─────────────────────────────────

def _envelope_signing_payload(envelope: FederationEnvelope) -> bytes:
    """Canonical bytes that the Nexus signature covers."""
    canonical = {
        "entity_type": envelope.entity_type,
        "payload": envelope.payload,
        "institute_body_b64": envelope.institute_body_b64,
        "institute_signature": envelope.institute_signature,
        "institute_public_key": envelope.institute_public_key,
        "institute_timestamp": envelope.institute_timestamp,
        "origin_nexus": envelope.origin_nexus,
        "hops": envelope.hops,
        "global_id": envelope.global_id,
    }
    return json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()


def sign_envelope(
    envelope: FederationEnvelope,
    signing_key: nacl.signing.SigningKey,
) -> FederationEnvelope:
    """Sign an envelope with a Nexus's private key."""
    pub_b64 = base64.b64encode(signing_key.verify_key.encode()).decode()
    payload_bytes = _envelope_signing_payload(envelope)
    sig = signing_key.sign(payload_bytes).signature
    sig_b64 = base64.b64encode(sig).decode()
    return envelope.model_copy(update={
        "nexus_signature": sig_b64,
        "nexus_public_key": pub_b64,
    })


def verify_nexus_signature(envelope: FederationEnvelope) -> bool:
    """Verify the forwarding Nexus's signature on the envelope."""
    if not envelope.nexus_signature or not envelope.nexus_public_key:
        return False
    try:
        sig = base64.b64decode(envelope.nexus_signature)
        pubkey_bytes = base64.b64decode(envelope.nexus_public_key)
        verify_key = nacl.signing.VerifyKey(pubkey_bytes)
        verify_key.verify(_envelope_signing_payload(envelope), sig)
        return True
    except (nacl.exceptions.BadSignatureError, Exception):
        return False


def verify_institute_signature(envelope: FederationEnvelope) -> bool:
    """Verify the authoring institute's signature on the original payload."""
    if not envelope.institute_signature or not envelope.institute_public_key:
        return envelope.entity_type == "institute"
    try:
        if envelope.institute_body_b64:
            # Quick size guard before decoding. Base64 expands by ~4/3.
            # Allow a small slack for padding.
            approx_decoded = (len(envelope.institute_body_b64) * 3) // 4
            if approx_decoded > FEDERATION_MAX_INSTITUTE_BODY_BYTES:
                return False
            body_bytes = base64.b64decode(envelope.institute_body_b64)
        else:
            # Backward-compatible fallback for older envelopes.
            body_bytes = json.dumps(envelope.payload, sort_keys=True, separators=(",", ":")).encode()
        signed_payload = body_bytes + b"\n" + envelope.institute_timestamp.encode()
        sig = base64.b64decode(envelope.institute_signature)
        pubkey_bytes = base64.b64decode(envelope.institute_public_key)
        verify_key = nacl.signing.VerifyKey(pubkey_bytes)
        verify_key.verify(signed_payload, sig)
        return True
    except (nacl.exceptions.BadSignatureError, Exception):
        return False


def verify_envelope(envelope: FederationEnvelope) -> bool:
    """Verify both signatures on a federation envelope."""
    if not verify_nexus_signature(envelope):
        log.warning("Envelope failed Nexus signature check: %s", envelope.global_id)
        return False
    if envelope.entity_type != "institute" and not verify_institute_signature(envelope):
        log.warning("Envelope failed institute signature check: %s", envelope.global_id)
        return False
    return True


# ── Outbound: push to peers ─────────────────────────────────────────

def build_paper_metadata_envelope(
    paper: dict,
    institute_public_key: str,
    institute_signature: str,
    institute_timestamp: str,
    nexus_id: str,
    *,
    institute_body_b64: str = "",
) -> FederationEnvelope:
    """Build a metadata-only envelope for a locally published paper."""
    payload = {
        "id": paper["id"],
        "institute_id": paper["institute_id"],
        "title": paper["title"],
        "summary": paper.get("summary", ""),
        "tags": paper.get("tags", ""),
        "timestamp": paper["timestamp"],
        "supersedes": paper.get("supersedes", ""),
        "external_references": paper.get("external_references", []),
        "global_id": paper.get("global_id", ""),
    }
    return FederationEnvelope(
        entity_type="paper_metadata",
        payload=payload,
        institute_body_b64=institute_body_b64,
        institute_signature=institute_signature,
        institute_public_key=institute_public_key,
        institute_timestamp=institute_timestamp,
        origin_nexus=nexus_id,
        hops=[nexus_id],
        global_id=paper.get("global_id", ""),
    )


def build_review_envelope(
    review: dict,
    paper_global_id: str,
    institute_public_key: str,
    institute_signature: str,
    institute_timestamp: str,
    nexus_id: str,
    *,
    institute_body_b64: str = "",
) -> FederationEnvelope:
    """Build an envelope for a review."""
    global_id = hashlib.sha256(
        f"review:{institute_public_key}:{paper_global_id}".encode()
    ).hexdigest()
    payload = {**review, "paper_global_id": paper_global_id}
    return FederationEnvelope(
        entity_type="review",
        payload=payload,
        institute_body_b64=institute_body_b64,
        institute_signature=institute_signature,
        institute_public_key=institute_public_key,
        institute_timestamp=institute_timestamp,
        origin_nexus=nexus_id,
        hops=[nexus_id],
        global_id=global_id,
    )


def build_reaction_envelope(
    reaction: dict,
    paper_id: str,
    paper_global_id: str,
    institute_public_key: str,
    institute_signature: str,
    institute_timestamp: str,
    nexus_id: str,
    *,
    institute_body_b64: str = "",
) -> FederationEnvelope:
    """Build an envelope for a reaction."""
    global_id = hashlib.sha256(
        f"reaction:{institute_public_key}:{paper_global_id}:{reaction['reaction_type']}".encode()
    ).hexdigest()
    payload = {**reaction, "paper_id": paper_id, "paper_global_id": paper_global_id}
    return FederationEnvelope(
        entity_type="reaction",
        payload=payload,
        institute_body_b64=institute_body_b64,
        institute_signature=institute_signature,
        institute_public_key=institute_public_key,
        institute_timestamp=institute_timestamp,
        origin_nexus=nexus_id,
        hops=[nexus_id],
        global_id=global_id,
    )


def build_institute_envelope(
    institute: dict,
    nexus_id: str,
) -> FederationEnvelope:
    """Build an envelope for a new institute registration."""
    global_id = hashlib.sha256(
        f"institute:{institute.get('public_key', '')}".encode()
    ).hexdigest()
    payload = {
        "id": institute["id"],
        "name": institute["name"],
        "public_key": institute.get("public_key", ""),
        "mission": institute.get("mission", ""),
        "tags": institute.get("tags", ""),
        "registered_at": institute.get("registered_at", ""),
    }
    return FederationEnvelope(
        entity_type="institute",
        payload=payload,
        origin_nexus=nexus_id,
        hops=[nexus_id],
        global_id=global_id,
    )


async def forward_to_peers(
    conn: Connection,
    envelope: FederationEnvelope,
    signing_key: nacl.signing.SigningKey,
) -> None:
    """Push an envelope to all known peers (skipping those already in hops)."""
    if not FEDERATION_ENABLED:
        return

    signed = sign_envelope(envelope, signing_key)
    peers = get_peers(conn)
    envelope_data = signed.model_dump()

    for peer in peers:
        if peer["public_key"] in signed.hops:
            continue
        try:
            async with httpx.AsyncClient(timeout=FEDERATION_TIMEOUT) as client:
                resp = await client.post(
                    f"{peer['url']}/federation/ingest",
                    json=envelope_data,
                )
            if resp.status_code < 300:
                log_federation_delivery(conn, peer["id"], signed.global_id, signed.entity_type, "delivered")
                update_peer_last_seen(conn, peer["id"])
            else:
                log.warning("Peer %s rejected envelope %s: %s", peer["url"], signed.global_id, resp.status_code)
                log_federation_delivery(conn, peer["id"], signed.global_id, signed.entity_type, "failed")
        except Exception as exc:
            log.warning("Failed to forward to peer %s: %s", peer["url"], exc)
            log_federation_delivery(conn, peer["id"], signed.global_id, signed.entity_type, "failed")


# ── Inbound: receive from peer ──────────────────────────────────────

async def ingest_envelope(
    conn: Connection,
    envelope: FederationEnvelope,
    nexus_id: str,
    signing_key: nacl.signing.SigningKey,
) -> dict | None:
    """Process an incoming federation envelope. Returns the stored entity or None if duplicate."""
    if nexus_id in envelope.hops:
        return None

    existing = get_paper_by_global_id(conn, envelope.global_id)
    if existing and envelope.entity_type == "paper_metadata":
        return None

    if envelope.entity_type == "institute":
        return _ingest_institute(conn, envelope)
    elif envelope.entity_type == "paper_metadata":
        return await _ingest_paper_metadata(conn, envelope, nexus_id, signing_key)
    elif envelope.entity_type == "review":
        return _ingest_review(conn, envelope)
    elif envelope.entity_type == "reaction":
        return _ingest_reaction(conn, envelope)

    return None


def _ensure_institute_exists(conn: Connection, envelope: FederationEnvelope) -> dict | None:
    """Make sure the authoring institute exists locally (insert as federated if not)."""
    if not envelope.institute_public_key:
        return None
    inst = get_institute_by_pubkey(conn, envelope.institute_public_key)
    if inst:
        return inst
    payload = envelope.payload
    return insert_institute(
        conn,
        name=payload.get("institute_name", "Unknown Institute"),
        public_key=envelope.institute_public_key,
        mission="",
        tags="",
        origin_nexus=envelope.origin_nexus,
    )


def _ingest_institute(conn: Connection, envelope: FederationEnvelope) -> dict | None:
    """Store a federated institute registration."""
    payload = envelope.payload
    pub_key = payload.get("public_key", "")
    if not pub_key:
        return None
    existing = get_institute_by_pubkey(conn, pub_key)
    if existing:
        return existing
    return insert_institute(
        conn,
        name=payload.get("name", "Unknown Institute"),
        public_key=pub_key,
        mission=payload.get("mission", ""),
        tags=payload.get("tags", ""),
        institute_id=payload.get("id"),
        registered_at=payload.get("registered_at"),
        origin_nexus=envelope.origin_nexus,
    )


async def _ingest_paper_metadata(
    conn: Connection,
    envelope: FederationEnvelope,
    nexus_id: str,
    signing_key: nacl.signing.SigningKey,
) -> dict | None:
    """Store a paper metadata stub from a peer."""
    _ensure_institute_exists(conn, envelope)
    payload = envelope.payload

    inst = get_institute_by_pubkey(conn, envelope.institute_public_key) if envelope.institute_public_key else None
    if not inst:
        log.warning("Cannot ingest paper — unknown institute: %s", envelope.institute_public_key)
        return None

    global_id = payload.get("global_id", envelope.global_id)
    paper_id = payload.get("id") or generate_paper_id(global_id)

    ext_refs = payload.get("external_references", [])
    if isinstance(ext_refs, list):
        ext_refs = json.dumps(ext_refs) if ext_refs else ""

    try:
        paper = insert_paper(
            conn,
            institute_id=inst["id"],
            title=payload.get("title", ""),
            summary=payload.get("summary", ""),
            content="",
            tags=payload.get("tags", ""),
            paper_id=paper_id,
            timestamp=payload.get("timestamp"),
            supersedes=payload.get("supersedes", ""),
            external_references=ext_refs,
            global_id=global_id,
            content_cached=False,
            origin_nexus=envelope.origin_nexus,
        )
    except Exception as exc:
        if "Duplicate" in str(exc):
            return None
        raise

    re_envelope = envelope.model_copy(update={"hops": [*envelope.hops, nexus_id]})
    await forward_to_peers(conn, re_envelope, signing_key)

    return paper


def _ingest_review(conn: Connection, envelope: FederationEnvelope) -> dict | None:
    """Store a federated review."""
    _ensure_institute_exists(conn, envelope)
    payload = envelope.payload
    inst = get_institute_by_pubkey(conn, envelope.institute_public_key) if envelope.institute_public_key else None
    if not inst:
        return None

    paper_global_id = payload.get("paper_global_id", "")
    paper = get_paper_by_global_id(conn, paper_global_id) if paper_global_id else None
    if not paper:
        log.warning("Cannot ingest review — paper not found: %s", paper_global_id)
        return None

    from database import insert_review
    try:
        return insert_review(
            conn,
            paper_id=paper["id"],
            institute_id=inst["id"],
            summary=payload.get("summary", ""),
            strengths=payload.get("strengths", ""),
            weaknesses=payload.get("weaknesses", ""),
            questions=payload.get("questions", ""),
            recommendation=payload.get("recommendation", "neutral"),
            confidence=payload.get("confidence", "medium"),
        )
    except ValueError:
        return None


def _ingest_reaction(conn: Connection, envelope: FederationEnvelope) -> dict | None:
    """Store a federated reaction."""
    _ensure_institute_exists(conn, envelope)
    payload = envelope.payload
    inst = get_institute_by_pubkey(conn, envelope.institute_public_key) if envelope.institute_public_key else None
    if not inst:
        return None

    paper_global_id = payload.get("paper_global_id", "")
    paper = get_paper_by_global_id(conn, paper_global_id) if paper_global_id else None
    if not paper:
        paper_id = payload.get("paper_id", "")
        if paper_id:
            from database import get_paper
            paper = get_paper(conn, paper_id)
    if not paper:
        log.warning("Cannot ingest reaction — paper not found: %s", payload.get("paper_global_id"))
        return None

    from database import add_reaction
    return add_reaction(conn, paper["id"], inst["id"], payload.get("reaction_type", "endorse"))


# ── Lazy content fetch ──────────────────────────────────────────────

async def fetch_paper_content(conn: Connection, paper: dict) -> dict | None:
    """Fetch full content for a metadata-only stub from the origin or any peer."""
    global_id = paper.get("global_id", "")
    if not global_id:
        return None

    peers = get_peers(conn)
    origin = paper.get("origin_nexus", "")

    urls_to_try: list[str] = []
    for peer in peers:
        if peer["public_key"] == origin:
            urls_to_try.insert(0, peer["url"])
        else:
            urls_to_try.append(peer["url"])

    for peer_url in urls_to_try:
        try:
            async with httpx.AsyncClient(timeout=FEDERATION_TIMEOUT) as client:
                resp = await client.get(f"{peer_url}/federation/papers/{global_id}")
            if resp.status_code == 200:
                data = resp.json()
                content = data.get("content", "")
                if content:
                    mark_paper_cached(conn, paper["id"], content)
                    paper["content"] = content
                    paper["content_cached"] = True
                    return paper
        except Exception as exc:
            log.warning("Failed to fetch paper content from %s: %s", peer_url, exc)

    return None


# ── Startup sync ────────────────────────────────────────────────────

async def sync_metadata_from_peer(
    conn: Connection,
    peer_url: str,
    nexus_id: str,
    signing_key: nacl.signing.SigningKey,
    since: str = "",
) -> int:
    """Pull metadata envelopes from a peer for catch-up. Returns count ingested."""
    count = 0
    cursor = since

    try:
        async with httpx.AsyncClient(timeout=FEDERATION_TIMEOUT) as client:
            while True:
                params = {"limit": "100"}
                if cursor:
                    params["since"] = cursor
                resp = await client.get(f"{peer_url}/federation/sync", params=params)
                if resp.status_code != 200:
                    break
                data = resp.json()
                envelopes = data.get("envelopes", [])
                if not envelopes:
                    break
                for env_data in envelopes:
                    envelope = FederationEnvelope(**env_data)
                    result = await ingest_envelope(conn, envelope, nexus_id, signing_key)
                    if result:
                        count += 1
                    cursor = env_data.get("payload", {}).get("timestamp", cursor)
                if len(envelopes) < 100:
                    break
    except Exception as exc:
        log.warning("Sync from %s failed: %s", peer_url, exc)

    return count


# ── Retry failed deliveries ─────────────────────────────────────────

async def retry_failed_deliveries(
    conn: Connection,
    signing_key: nacl.signing.SigningKey,
) -> int:
    """Retry envelopes that previously failed to deliver. Returns count retried."""
    from database import get_failed_deliveries
    failures = get_failed_deliveries(conn)
    retried = 0

    for failure in failures:
        peer_url = failure.get("peer_url", "")
        if not peer_url:
            continue
        try:
            async with httpx.AsyncClient(timeout=FEDERATION_TIMEOUT) as client:
                resp = await client.get(f"{peer_url}/federation/identity")
            if resp.status_code == 200:
                update_peer_last_seen(conn, failure["peer_id"])
                log_federation_delivery(
                    conn, failure["peer_id"], failure["global_id"],
                    failure["entity_type"], "retry_pending",
                )
                retried += 1
        except Exception:
            pass

    return retried
