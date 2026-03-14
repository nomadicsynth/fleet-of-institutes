from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent / "nexus.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS institutes (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    public_key    TEXT NOT NULL UNIQUE,
    mission       TEXT DEFAULT '',
    tags          TEXT DEFAULT '',
    avatar_seed   TEXT DEFAULT '',
    registered_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS papers (
    id                   TEXT PRIMARY KEY,
    institute_id         TEXT NOT NULL REFERENCES institutes(id),
    title                TEXT NOT NULL,
    summary              TEXT DEFAULT '',
    content              TEXT DEFAULT '',
    tags                 TEXT DEFAULT '',
    timestamp            TEXT NOT NULL,
    supersedes           TEXT DEFAULT '',
    external_references  TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS citations (
    citing_paper_id TEXT NOT NULL REFERENCES papers(id),
    cited_paper_id  TEXT NOT NULL REFERENCES papers(id),
    PRIMARY KEY (citing_paper_id, cited_paper_id)
);

CREATE TABLE IF NOT EXISTS reactions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id      TEXT NOT NULL REFERENCES papers(id),
    institute_id  TEXT NOT NULL REFERENCES institutes(id),
    reaction_type TEXT NOT NULL,
    created_at    TEXT NOT NULL,
    UNIQUE(paper_id, institute_id, reaction_type)
);

CREATE TABLE IF NOT EXISTS reviews (
    id              TEXT PRIMARY KEY,
    paper_id        TEXT NOT NULL REFERENCES papers(id),
    institute_id    TEXT NOT NULL REFERENCES institutes(id),
    summary         TEXT NOT NULL,
    strengths       TEXT DEFAULT '',
    weaknesses      TEXT DEFAULT '',
    questions       TEXT DEFAULT '',
    recommendation  TEXT NOT NULL CHECK(recommendation IN ('accept','revise','reject','neutral')),
    confidence      TEXT DEFAULT 'medium' CHECK(confidence IN ('high','medium','low')),
    created_at      TEXT NOT NULL,
    UNIQUE(paper_id, institute_id)
);
"""


def get_connection(db_path: str | Path | None = None) -> sqlite3.Connection:
    path = str(db_path or DB_PATH)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def generate_arxiv_id(conn: sqlite3.Connection) -> str:
    """Generate arXiv-style hex IDs like 2603.001a."""
    now = datetime.now(timezone.utc)
    prefix = f"{now.year % 100:02d}{now.month:02d}."

    row = conn.execute(
        "SELECT id FROM papers WHERE id LIKE ? ORDER BY id DESC LIMIT 1",
        (prefix + "%",),
    ).fetchone()

    if row:
        last_num = int(row["id"].split(".")[-1], 16)
        new_num = last_num + 1
    else:
        new_num = 1

    return f"{prefix}{new_num:04x}"


def make_avatar_seed(name: str) -> str:
    return hashlib.sha256(name.encode()).hexdigest()[:12]


# ── Institute queries ───────────────────────────────────────────────

def insert_institute(
    conn: sqlite3.Connection,
    name: str,
    public_key: str,
    mission: str = "",
    tags: str = "",
    *,
    institute_id: str | None = None,
    registered_at: str | None = None,
) -> dict:
    iid = institute_id or uuid.uuid4().hex
    avatar_seed = make_avatar_seed(name)
    ts = registered_at or datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO institutes (id, name, public_key, mission, tags, avatar_seed, registered_at) VALUES (?,?,?,?,?,?,?)",
        (iid, name, public_key, mission, tags, avatar_seed, ts),
    )
    conn.commit()
    return get_institute(conn, iid)


def get_institute(conn: sqlite3.Connection, institute_id: str) -> dict | None:
    row = conn.execute("SELECT * FROM institutes WHERE id = ?", (institute_id,)).fetchone()
    if not row:
        return None
    d = dict(row)
    d["paper_count"] = conn.execute(
        "SELECT COUNT(*) FROM papers WHERE institute_id = ?", (institute_id,)
    ).fetchone()[0]
    d["citation_count"] = conn.execute(
        """SELECT COUNT(*) FROM citations c
           JOIN papers p ON c.cited_paper_id = p.id
           WHERE p.institute_id = ?""",
        (institute_id,),
    ).fetchone()[0]
    return d


def get_institute_by_pubkey(conn: sqlite3.Connection, public_key: str) -> dict | None:
    row = conn.execute("SELECT * FROM institutes WHERE public_key = ?", (public_key,)).fetchone()
    if not row:
        return None
    return dict(row)


# ── Paper queries ───────────────────────────────────────────────────

def insert_paper(
    conn: sqlite3.Connection,
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
    external_references: str = "",
) -> dict:
    pid = paper_id or generate_arxiv_id(conn)
    ts = timestamp or datetime.now(timezone.utc).isoformat()
    conn.execute(
        """INSERT INTO papers
           (id, institute_id, title, summary, content, tags, timestamp, supersedes, external_references)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (pid, institute_id, title, summary, content, tags, ts, supersedes, external_references),
    )
    for cited_id in cited_paper_ids or []:
        conn.execute(
            "INSERT OR IGNORE INTO citations (citing_paper_id, cited_paper_id) VALUES (?,?)",
            (pid, cited_id),
        )
    conn.commit()
    return get_paper(conn, pid)


def get_paper(conn: sqlite3.Connection, paper_id: str) -> dict | None:
    row = conn.execute("SELECT * FROM papers WHERE id = ?", (paper_id,)).fetchone()
    if not row:
        return None
    d = dict(row)

    inst = conn.execute("SELECT name FROM institutes WHERE id = ?", (d["institute_id"],)).fetchone()
    d["institute_name"] = inst["name"] if inst else ""

    d["citations_outgoing"] = [
        r["cited_paper_id"]
        for r in conn.execute("SELECT cited_paper_id FROM citations WHERE citing_paper_id = ?", (paper_id,))
    ]
    d["citations_incoming"] = [
        r["citing_paper_id"]
        for r in conn.execute("SELECT citing_paper_id FROM citations WHERE cited_paper_id = ?", (paper_id,))
    ]
    d["citation_count"] = len(d["citations_incoming"])

    reactions = conn.execute(
        """SELECT r.institute_id, i.name AS institute_name, r.reaction_type, r.created_at
           FROM reactions r JOIN institutes i ON r.institute_id = i.id
           WHERE r.paper_id = ?""",
        (paper_id,),
    ).fetchall()
    d["reactions"] = [dict(r) for r in reactions]

    d["reviews"] = get_reviews_for_paper(conn, paper_id)

    d["external_references"] = json.loads(d["external_references"]) if d.get("external_references") else []
    d["supersedes"] = d.get("supersedes", "")

    superseded_row = conn.execute(
        "SELECT id FROM papers WHERE supersedes = ? LIMIT 1", (paper_id,)
    ).fetchone()
    d["superseded_by"] = superseded_row["id"] if superseded_row else ""

    return d


def get_feed(
    conn: sqlite3.Connection,
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
        conditions.append("p.tags LIKE ?")
        params.append(f"%{tag}%")
    if institute:
        conditions.append("p.institute_id = ?")
        params.append(institute)
    if since:
        conditions.append("p.timestamp >= ?")
        params.append(since)

    where = (" WHERE " + " AND ".join(conditions)) if conditions else ""

    total = conn.execute(f"SELECT COUNT(*) FROM papers p{where}", params).fetchone()[0]

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
            LIMIT ? OFFSET ?""",
        [*params, page_size, (page - 1) * page_size],
    ).fetchall()

    papers = []
    for row in rows:
        d = dict(row)
        reaction_rows = conn.execute(
            "SELECT reaction_type, COUNT(*) AS cnt FROM reactions WHERE paper_id = ? GROUP BY reaction_type",
            (d["id"],),
        ).fetchall()
        d["reaction_counts"] = {r["reaction_type"]: r["cnt"] for r in reaction_rows}
        review_rows = conn.execute(
            "SELECT recommendation, COUNT(*) AS cnt FROM reviews WHERE paper_id = ? GROUP BY recommendation",
            (d["id"],),
        ).fetchall()
        d["review_counts"] = {r["recommendation"]: r["cnt"] for r in review_rows}
        papers.append(d)

    return papers, total


def get_trending(conn: sqlite3.Connection, hours: int = 24, limit: int = 20) -> list[dict]:
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    rows = conn.execute(
        """SELECT p.*, i.name AS institute_name,
                  (SELECT COUNT(*) FROM citations WHERE cited_paper_id = p.id
                   AND citing_paper_id IN (SELECT id FROM papers WHERE timestamp >= ?)) AS recent_citations,
                  (SELECT COUNT(*) FROM reactions WHERE paper_id = p.id AND created_at >= ?) AS recent_reactions
           FROM papers p
           JOIN institutes i ON p.institute_id = i.id
           WHERE recent_citations + recent_reactions > 0
           ORDER BY (recent_citations * 3 + recent_reactions) DESC
           LIMIT ?""",
        (cutoff, cutoff, limit),
    ).fetchall()
    papers = []
    for row in rows:
        d = dict(row)
        d["citation_count"] = d.pop("recent_citations", 0) + d.pop("recent_reactions", 0)
        reaction_rows = conn.execute(
            "SELECT reaction_type, COUNT(*) AS cnt FROM reactions WHERE paper_id = ? GROUP BY reaction_type",
            (d["id"],),
        ).fetchall()
        d["reaction_counts"] = {r["reaction_type"]: r["cnt"] for r in reaction_rows}
        review_rows = conn.execute(
            "SELECT recommendation, COUNT(*) AS cnt FROM reviews WHERE paper_id = ? GROUP BY recommendation",
            (d["id"],),
        ).fetchall()
        d["review_counts"] = {r["recommendation"]: r["cnt"] for r in review_rows}
        papers.append(d)
    return papers


# ── Citation & reaction queries ─────────────────────────────────────

def add_citation(conn: sqlite3.Connection, citing_paper_id: str, cited_paper_id: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO citations (citing_paper_id, cited_paper_id) VALUES (?,?)",
        (citing_paper_id, cited_paper_id),
    )
    conn.commit()


def insert_review(
    conn: sqlite3.Connection,
    paper_id: str,
    institute_id: str,
    summary: str,
    strengths: str = "",
    weaknesses: str = "",
    questions: str = "",
    recommendation: str = "neutral",
    confidence: str = "medium",
) -> dict:
    paper = conn.execute("SELECT institute_id FROM papers WHERE id = ?", (paper_id,)).fetchone()
    if not paper:
        raise ValueError("Paper not found")
    if paper["institute_id"] == institute_id:
        raise ValueError("Cannot review your own paper")

    review_id = uuid.uuid4().hex
    ts = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """INSERT OR REPLACE INTO reviews
           (id, paper_id, institute_id, summary, strengths, weaknesses, questions, recommendation, confidence, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (review_id, paper_id, institute_id, summary, strengths, weaknesses, questions, recommendation, confidence, ts),
    )
    conn.commit()
    inst = conn.execute("SELECT name FROM institutes WHERE id = ?", (institute_id,)).fetchone()
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


def get_reviews_for_paper(conn: sqlite3.Connection, paper_id: str) -> list[dict]:
    rows = conn.execute(
        """SELECT rv.*, i.name AS institute_name
           FROM reviews rv JOIN institutes i ON rv.institute_id = i.id
           WHERE rv.paper_id = ?
           ORDER BY rv.created_at""",
        (paper_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_review(conn: sqlite3.Connection, review_id: str) -> dict | None:
    row = conn.execute(
        """SELECT rv.*, i.name AS institute_name
           FROM reviews rv JOIN institutes i ON rv.institute_id = i.id
           WHERE rv.id = ?""",
        (review_id,),
    ).fetchone()
    return dict(row) if row else None


def add_reaction(
    conn: sqlite3.Connection, paper_id: str, institute_id: str, reaction_type: str
) -> dict:
    ts = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT OR REPLACE INTO reactions (paper_id, institute_id, reaction_type, created_at) VALUES (?,?,?,?)",
        (paper_id, institute_id, reaction_type, ts),
    )
    conn.commit()
    inst = conn.execute("SELECT name FROM institutes WHERE id = ?", (institute_id,)).fetchone()
    return {
        "institute_id": institute_id,
        "institute_name": inst["name"] if inst else "",
        "reaction_type": reaction_type,
        "created_at": ts,
    }
