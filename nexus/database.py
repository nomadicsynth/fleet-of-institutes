from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import datetime, timedelta, timezone

import pymysql
import pymysql.cursors

from config import MAX_FEED_OFFSET

_TABLES = [
    """
    CREATE TABLE IF NOT EXISTS institutes (
        id            VARCHAR(64) PRIMARY KEY,
        name          VARCHAR(255) NOT NULL,
        public_key    VARCHAR(255) NOT NULL,
        mission       TEXT NOT NULL,
        tags          VARCHAR(500) NOT NULL DEFAULT '',
        avatar_seed   VARCHAR(64) NOT NULL DEFAULT '',
        registered_at VARCHAR(64) NOT NULL,
        origin_nexus  VARCHAR(255) NOT NULL DEFAULT '',
        UNIQUE KEY uq_pubkey (public_key)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS papers (
        id                   VARCHAR(64) PRIMARY KEY,
        institute_id         VARCHAR(64) NOT NULL,
        title                VARCHAR(500) NOT NULL,
        summary              TEXT NOT NULL,
        content              LONGTEXT NOT NULL,
        tags                 VARCHAR(500) NOT NULL DEFAULT '',
        timestamp            VARCHAR(64) NOT NULL,
        supersedes           VARCHAR(64) NOT NULL DEFAULT '',
        retracts             VARCHAR(64) NOT NULL DEFAULT '',
        external_references  TEXT NOT NULL,
        global_id            VARCHAR(128) NOT NULL DEFAULT '',
        content_cached       TINYINT(1) NOT NULL DEFAULT 1,
        origin_nexus         VARCHAR(255) NOT NULL DEFAULT '',
        UNIQUE KEY uq_global_id (global_id),
        KEY idx_supersedes (supersedes),
        KEY idx_retracts (retracts),
        FOREIGN KEY (institute_id) REFERENCES institutes(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS citations (
        citing_paper_id VARCHAR(64) NOT NULL,
        cited_paper_id  VARCHAR(64) NOT NULL,
        PRIMARY KEY (citing_paper_id, cited_paper_id),
        FOREIGN KEY (citing_paper_id) REFERENCES papers(id),
        FOREIGN KEY (cited_paper_id) REFERENCES papers(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS reactions (
        id            INT AUTO_INCREMENT PRIMARY KEY,
        paper_id      VARCHAR(64) NOT NULL,
        institute_id  VARCHAR(64) NOT NULL,
        reaction_type VARCHAR(32) NOT NULL,
        created_at    VARCHAR(64) NOT NULL,
        UNIQUE KEY uq_reaction (paper_id, institute_id, reaction_type),
        FOREIGN KEY (paper_id) REFERENCES papers(id),
        FOREIGN KEY (institute_id) REFERENCES institutes(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS reviews (
        id              VARCHAR(64) PRIMARY KEY,
        paper_id        VARCHAR(64) NOT NULL,
        institute_id    VARCHAR(64) NOT NULL,
        summary         TEXT NOT NULL,
        strengths       TEXT NOT NULL,
        weaknesses      TEXT NOT NULL,
        questions       TEXT NOT NULL,
        recommendation  VARCHAR(16) NOT NULL,
        confidence      VARCHAR(16) NOT NULL DEFAULT 'medium',
        created_at      VARCHAR(64) NOT NULL,
        UNIQUE KEY uq_review (paper_id, institute_id),
        FOREIGN KEY (paper_id) REFERENCES papers(id),
        FOREIGN KEY (institute_id) REFERENCES institutes(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS peers (
        id         VARCHAR(64) PRIMARY KEY,
        url        VARCHAR(500) NOT NULL,
        public_key VARCHAR(255) NOT NULL DEFAULT '',
        added_at   VARCHAR(64) NOT NULL,
        last_seen  VARCHAR(64) NOT NULL DEFAULT '',
        UNIQUE KEY uq_url (url)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS federation_log (
        id          INT AUTO_INCREMENT PRIMARY KEY,
        peer_id     VARCHAR(64) NOT NULL,
        global_id   VARCHAR(128) NOT NULL,
        entity_type VARCHAR(32) NOT NULL,
        status      VARCHAR(16) NOT NULL DEFAULT 'pending',
        created_at  VARCHAR(64) NOT NULL,
        UNIQUE KEY uq_delivery (peer_id, global_id, entity_type)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
]


class Connection:
    """Thin wrapper around pymysql with a simple execute/commit API."""

    def __init__(self, **kwargs):
        self._config = kwargs
        self._conn = pymysql.connect(**kwargs)

    def execute(self, sql, params=None):
        self._conn.ping(reconnect=True)
        cursor = self._conn.cursor()
        cursor.execute(sql, params or ())
        return cursor

    def commit(self):
        self._conn.commit()

    def close(self):
        self._conn.close()


def get_connection(**overrides) -> Connection:
    config = {
        "host": os.environ.get("MYSQL_HOST", "localhost"),
        "port": int(os.environ.get("MYSQL_PORT", "3306")),
        "user": os.environ.get("MYSQL_USER", "nexus"),
        "password": os.environ.get("MYSQL_PASSWORD", "nexus"),
        "database": os.environ.get("MYSQL_DATABASE", "nexus"),
        "cursorclass": pymysql.cursors.DictCursor,
        "charset": "utf8mb4",
        "autocommit": True,
        **overrides,
    }
    return Connection(**config)


def init_db(conn: Connection) -> None:
    for ddl in _TABLES:
        conn.execute(ddl)
    conn.commit()


# ── Paper ID generation ─────────────────────────────────────────────

def compute_global_id(public_key: str, title: str, content: str, timestamp: str) -> str:
    """SHA-256 hash of canonical paper content. Deterministic across Nexuses."""
    payload = f"{public_key}\n{title}\n{content}\n{timestamp}"
    return hashlib.sha256(payload.encode()).hexdigest()


def generate_paper_id(global_id: str) -> str:
    """Human-readable ID: YYMM.<first 8 hex chars of global_id>."""
    now = datetime.now(timezone.utc)
    prefix = f"{now.year % 100:02d}{now.month:02d}"
    short_hash = global_id[:8]
    return f"{prefix}.{short_hash}"


def make_avatar_seed(name: str) -> str:
    return hashlib.sha256(name.encode()).hexdigest()[:12]


# ── Institute queries ───────────────────────────────────────────────

def insert_institute(
    conn: Connection,
    name: str,
    public_key: str,
    mission: str = "",
    tags: str = "",
    *,
    institute_id: str | None = None,
    registered_at: str | None = None,
    origin_nexus: str = "",
) -> dict:
    iid = institute_id or uuid.uuid4().hex
    avatar_seed = make_avatar_seed(name)
    ts = registered_at or datetime.now(timezone.utc).isoformat()
    conn.execute(
        """INSERT INTO institutes
           (id, name, public_key, mission, tags, avatar_seed, registered_at, origin_nexus)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
        (iid, name, public_key, mission, tags, avatar_seed, ts, origin_nexus),
    )
    conn.commit()
    return get_institute(conn, iid)


def get_institute(conn: Connection, institute_id: str) -> dict | None:
    row = conn.execute("SELECT * FROM institutes WHERE id = %s", (institute_id,)).fetchone()
    if not row:
        return None
    d = dict(row)
    d["paper_count"] = conn.execute(
        "SELECT COUNT(*) AS cnt FROM papers WHERE institute_id = %s", (institute_id,)
    ).fetchone()["cnt"]
    d["citation_count"] = conn.execute(
        """SELECT COUNT(*) AS cnt FROM citations c
           JOIN papers p ON c.cited_paper_id = p.id
           WHERE p.institute_id = %s""",
        (institute_id,),
    ).fetchone()["cnt"]
    return d


def get_institute_by_pubkey(conn: Connection, public_key: str) -> dict | None:
    row = conn.execute("SELECT * FROM institutes WHERE public_key = %s", (public_key,)).fetchone()
    if not row:
        return None
    return dict(row)


# ── Paper queries ───────────────────────────────────────────────────

def insert_paper(
    conn: Connection,
    institute_id: str,
    title: str,
    summary: str = "",
    content: str = "",
    tags: str = "",
    cited_paper_ids: list[str] | None = None,
    *,
    paper_id: str | None = None,
    timestamp: str | None = None,
    supersedes: str = "",
    retracts: str = "",
    external_references: str = "",
    global_id: str = "",
    content_cached: bool = True,
    origin_nexus: str = "",
) -> dict:
    ts = timestamp or datetime.now(timezone.utc).isoformat()

    if not global_id:
        inst = get_institute(conn, institute_id)
        pub_key = inst["public_key"] if inst else ""
        global_id = compute_global_id(pub_key, title, content, ts)

    pid = paper_id or generate_paper_id(global_id)

    conn.execute(
        """INSERT INTO papers
           (id, institute_id, title, summary, content, tags, timestamp,
            supersedes, retracts, external_references, global_id, content_cached, origin_nexus)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (pid, institute_id, title, summary, content, tags, ts,
         supersedes, retracts, external_references, global_id,
         1 if content_cached else 0, origin_nexus),
    )
    for cited_id in cited_paper_ids or []:
        conn.execute(
            "INSERT IGNORE INTO citations (citing_paper_id, cited_paper_id) VALUES (%s,%s)",
            (pid, cited_id),
        )
    conn.commit()
    return get_paper(conn, pid)


def get_paper(conn: Connection, paper_id: str) -> dict | None:
    row = conn.execute("SELECT * FROM papers WHERE id = %s", (paper_id,)).fetchone()
    if not row:
        return None
    d = dict(row)

    inst = conn.execute("SELECT name FROM institutes WHERE id = %s", (d["institute_id"],)).fetchone()
    d["institute_name"] = inst["name"] if inst else ""

    d["citations_outgoing"] = [
        r["cited_paper_id"]
        for r in conn.execute("SELECT cited_paper_id FROM citations WHERE citing_paper_id = %s", (paper_id,)).fetchall()
    ]
    d["citations_incoming"] = [
        r["citing_paper_id"]
        for r in conn.execute("SELECT citing_paper_id FROM citations WHERE cited_paper_id = %s", (paper_id,)).fetchall()
    ]
    d["citation_count"] = len(d["citations_incoming"])

    reactions = conn.execute(
        """SELECT r.institute_id, i.name AS institute_name, r.reaction_type, r.created_at
           FROM reactions r JOIN institutes i ON r.institute_id = i.id
           WHERE r.paper_id = %s""",
        (paper_id,),
    ).fetchall()
    d["reactions"] = [dict(r) for r in reactions]

    d["reviews"] = get_reviews_for_paper(conn, paper_id)

    d["external_references"] = json.loads(d["external_references"]) if d.get("external_references") else []
    d["supersedes"] = d.get("supersedes", "")
    d["retracts"] = d.get("retracts", "")

    superseded_row = conn.execute(
        "SELECT id FROM papers WHERE supersedes = %s LIMIT 1", (paper_id,)
    ).fetchone()
    d["superseded_by"] = superseded_row["id"] if superseded_row else ""

    retracted_row = conn.execute(
        "SELECT id FROM papers WHERE retracts = %s LIMIT 1", (paper_id,)
    ).fetchone()
    d["retracted_by"] = retracted_row["id"] if retracted_row else ""

    d["content_cached"] = bool(d.get("content_cached", 1))

    return d


def get_paper_by_global_id(conn: Connection, global_id: str) -> dict | None:
    """Look up a paper by its canonical content hash."""
    row = conn.execute("SELECT id FROM papers WHERE global_id = %s", (global_id,)).fetchone()
    if not row:
        return None
    return get_paper(conn, row["id"])


def mark_paper_cached(conn: Connection, paper_id: str, content: str) -> None:
    """Fill in full content for a previously metadata-only stub."""
    conn.execute(
        "UPDATE papers SET content = %s, content_cached = 1 WHERE id = %s",
        (content, paper_id),
    )
    conn.commit()


def get_feed(
    conn: Connection,
    *,
    tag: str | None = None,
    institute: str | None = None,
    since: str | None = None,
    sort: str = "recent",
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict], int]:
    conditions: list[str] = []
    params: list = []

    if tag:
        conditions.append("p.tags LIKE %s")
        params.append(f"%{tag}%")
    if institute:
        conditions.append("p.institute_id = %s")
        params.append(institute)
    if since:
        conditions.append("p.timestamp >= %s")
        params.append(since)

    where = (" WHERE " + " AND ".join(conditions)) if conditions else ""

    total = conn.execute(f"SELECT COUNT(*) AS cnt FROM papers p{where}", params).fetchone()["cnt"]

    offset = (page - 1) * page_size
    if offset > MAX_FEED_OFFSET:
        return [], total

    order = "p.timestamp DESC"
    if sort == "cited":
        order = "citation_count DESC, p.timestamp DESC"

    rows = conn.execute(
        f"""SELECT p.*, i.name AS institute_name,
                   (SELECT COUNT(*) FROM citations WHERE cited_paper_id = p.id) AS citation_count
            FROM papers p
            JOIN institutes i ON p.institute_id = i.id
            {where}
            ORDER BY {order}
            LIMIT %s OFFSET %s""",
        [*params, page_size, offset],
    ).fetchall()

    papers = []
    for row in rows:
        d = dict(row)
        reaction_rows = conn.execute(
            "SELECT reaction_type, COUNT(*) AS cnt FROM reactions WHERE paper_id = %s GROUP BY reaction_type",
            (d["id"],),
        ).fetchall()
        d["reaction_counts"] = {r["reaction_type"]: r["cnt"] for r in reaction_rows}
        review_rows = conn.execute(
            "SELECT recommendation, COUNT(*) AS cnt FROM reviews WHERE paper_id = %s GROUP BY recommendation",
            (d["id"],),
        ).fetchall()
        d["review_counts"] = {r["recommendation"]: r["cnt"] for r in review_rows}
        papers.append(d)

    return papers, total


def get_trending(conn: Connection, hours: int = 24, limit: int = 20) -> list[dict]:
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    rows = conn.execute(
        """SELECT ranked.* FROM (
               SELECT p.*, i.name AS institute_name,
                      (SELECT COUNT(*) FROM citations WHERE cited_paper_id = p.id
                       AND citing_paper_id IN (SELECT id FROM papers WHERE timestamp >= %s)) AS recent_citations,
                      (SELECT COUNT(*) FROM reactions WHERE paper_id = p.id AND created_at >= %s) AS recent_reactions
               FROM papers p
               JOIN institutes i ON p.institute_id = i.id
           ) AS ranked
           WHERE recent_citations + recent_reactions > 0
           ORDER BY (recent_citations * 3 + recent_reactions) DESC
           LIMIT %s""",
        (cutoff, cutoff, limit),
    ).fetchall()
    papers = []
    for row in rows:
        d = dict(row)
        d["citation_count"] = d.pop("recent_citations", 0) + d.pop("recent_reactions", 0)
        reaction_rows = conn.execute(
            "SELECT reaction_type, COUNT(*) AS cnt FROM reactions WHERE paper_id = %s GROUP BY reaction_type",
            (d["id"],),
        ).fetchall()
        d["reaction_counts"] = {r["reaction_type"]: r["cnt"] for r in reaction_rows}
        review_rows = conn.execute(
            "SELECT recommendation, COUNT(*) AS cnt FROM reviews WHERE paper_id = %s GROUP BY recommendation",
            (d["id"],),
        ).fetchall()
        d["review_counts"] = {r["recommendation"]: r["cnt"] for r in review_rows}
        papers.append(d)
    return papers


# ── Citation & reaction queries ─────────────────────────────────────

def add_citation(conn: Connection, citing_paper_id: str, cited_paper_id: str) -> None:
    conn.execute(
        "INSERT IGNORE INTO citations (citing_paper_id, cited_paper_id) VALUES (%s,%s)",
        (citing_paper_id, cited_paper_id),
    )
    conn.commit()


def insert_review(
    conn: Connection,
    paper_id: str,
    institute_id: str,
    summary: str,
    strengths: str = "",
    weaknesses: str = "",
    questions: str = "",
    recommendation: str = "neutral",
    confidence: str = "medium",
) -> dict:
    paper = conn.execute("SELECT institute_id FROM papers WHERE id = %s", (paper_id,)).fetchone()
    if not paper:
        raise ValueError("Paper not found")
    if paper["institute_id"] == institute_id:
        raise ValueError("Cannot review your own paper")

    review_id = uuid.uuid4().hex
    ts = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """REPLACE INTO reviews
           (id, paper_id, institute_id, summary, strengths, weaknesses, questions, recommendation, confidence, created_at)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (review_id, paper_id, institute_id, summary, strengths, weaknesses, questions, recommendation, confidence, ts),
    )
    conn.commit()
    inst = conn.execute("SELECT name FROM institutes WHERE id = %s", (institute_id,)).fetchone()
    return {
        "id": review_id,
        "paper_id": paper_id,
        "institute_id": institute_id,
        "institute_name": inst["name"] if inst else "",
        "summary": summary,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "questions": questions,
        "recommendation": recommendation,
        "confidence": confidence,
        "created_at": ts,
    }


def get_reviews_for_paper(conn: Connection, paper_id: str) -> list[dict]:
    rows = conn.execute(
        """SELECT rv.*, i.name AS institute_name
           FROM reviews rv JOIN institutes i ON rv.institute_id = i.id
           WHERE rv.paper_id = %s
           ORDER BY rv.created_at""",
        (paper_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_review(conn: Connection, review_id: str) -> dict | None:
    row = conn.execute(
        """SELECT rv.*, i.name AS institute_name
           FROM reviews rv JOIN institutes i ON rv.institute_id = i.id
           WHERE rv.id = %s""",
        (review_id,),
    ).fetchone()
    return dict(row) if row else None


def add_reaction(
    conn: Connection, paper_id: str, institute_id: str, reaction_type: str
) -> dict:
    ts = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "REPLACE INTO reactions (paper_id, institute_id, reaction_type, created_at) VALUES (%s,%s,%s,%s)",
        (paper_id, institute_id, reaction_type, ts),
    )
    conn.commit()
    inst = conn.execute("SELECT name FROM institutes WHERE id = %s", (institute_id,)).fetchone()
    return {
        "institute_id": institute_id,
        "institute_name": inst["name"] if inst else "",
        "reaction_type": reaction_type,
        "created_at": ts,
    }


# ── Peer queries ────────────────────────────────────────────────────

def insert_peer(
    conn: Connection,
    url: str,
    public_key: str = "",
    *,
    peer_id: str | None = None,
) -> dict:
    pid = peer_id or uuid.uuid4().hex
    ts = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT IGNORE INTO peers (id, url, public_key, added_at) VALUES (%s,%s,%s,%s)",
        (pid, url.rstrip("/"), public_key, ts),
    )
    conn.commit()
    return {"id": pid, "url": url.rstrip("/"), "public_key": public_key, "added_at": ts, "last_seen": ""}


def get_peers(conn: Connection) -> list[dict]:
    rows = conn.execute("SELECT * FROM peers ORDER BY added_at").fetchall()
    return [dict(r) for r in rows]


def remove_peer(conn: Connection, peer_id: str) -> bool:
    cursor = conn.execute("DELETE FROM peers WHERE id = %s", (peer_id,))
    conn.commit()
    return cursor.rowcount > 0


def update_peer_last_seen(conn: Connection, peer_id: str) -> None:
    ts = datetime.now(timezone.utc).isoformat()
    conn.execute("UPDATE peers SET last_seen = %s WHERE id = %s", (ts, peer_id))
    conn.commit()


def update_peer_public_key(conn: Connection, peer_id: str, public_key: str) -> None:
    conn.execute("UPDATE peers SET public_key = %s WHERE id = %s", (public_key, peer_id))
    conn.commit()


def get_peer_by_url(conn: Connection, url: str) -> dict | None:
    row = conn.execute("SELECT * FROM peers WHERE url = %s", (url.rstrip("/"),)).fetchone()
    return dict(row) if row else None


# ── Federation log queries ──────────────────────────────────────────

def log_federation_delivery(
    conn: Connection,
    peer_id: str,
    global_id: str,
    entity_type: str,
    status: str = "pending",
) -> None:
    ts = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """INSERT INTO federation_log (peer_id, global_id, entity_type, status, created_at)
           VALUES (%s,%s,%s,%s,%s)
           ON DUPLICATE KEY UPDATE status = %s""",
        (peer_id, global_id, entity_type, status, ts, status),
    )
    conn.commit()


def get_failed_deliveries(conn: Connection, limit: int = 100) -> list[dict]:
    rows = conn.execute(
        """SELECT fl.*, p.url AS peer_url FROM federation_log fl
           JOIN peers p ON fl.peer_id = p.id
           WHERE fl.status = 'failed'
           ORDER BY fl.created_at
           LIMIT %s""",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_papers_since(conn: Connection, since: str, limit: int = 100) -> list[dict]:
    """Return paper metadata (no content) for federation sync."""
    rows = conn.execute(
        """SELECT p.id, p.institute_id, p.title, p.summary, p.tags,
                  p.timestamp, p.supersedes, p.retracts, p.external_references,
                  p.global_id, p.origin_nexus, i.name AS institute_name,
                  i.public_key AS institute_public_key
           FROM papers p
           JOIN institutes i ON p.institute_id = i.id
           WHERE p.timestamp >= %s
           ORDER BY p.timestamp
           LIMIT %s""",
        (since, limit),
    ).fetchall()
    return [dict(r) for r in rows]
