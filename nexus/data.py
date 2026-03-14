import sqlite3
from datetime import datetime


class DataManager:
    def __init__(self, db_path="nexus.db", db_type="sqlite"):
        self.db_type = db_type
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._enable_wal_mode()
        self._create_tables()

    def _enable_wal_mode(self):
        if self.db_type == "sqlite":
            self.conn.execute("PRAGMA journal_mode=WAL;")

    def _create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS papers (
            id TEXT PRIMARY KEY,
            title TEXT,
            author TEXT,
            summary TEXT,
            content TEXT,
            tags TEXT,
            paper_references TEXT,
            timestamp TEXT
        )"""
        )
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS institutes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                author TEXT UNIQUE,
                mission TEXT,
                tags TEXT,
                registered_at TEXT
            )"""
        )
        self.conn.commit()

    def _generate_arxiv_id(self):
        now = datetime.now()
        year = str(now.year)[-2:]  # e.g. "25"
        month = f"{now.month:02d}"  # e.g. "04"
        prefix = f"{year}{month}."

        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM papers WHERE id LIKE ? ORDER BY id DESC LIMIT 1", (prefix + "%",))
        last_id = cursor.fetchone()

        if last_id:
            last_num = int(last_id[0].split(".")[-1], 16)  # Parse as hexadecimal
            new_num = last_num + 1
        else:
            new_num = 1

        return f"{prefix}{new_num:04x}"

    def add_paper(self, title, author, summary, content, tags, paper_references, timestamp):
        paper_id = self._generate_arxiv_id()
        cursor = self.conn.cursor()
        cursor.execute(
            """INSERT INTO papers (id, title, author, summary, content, tags, paper_references, timestamp)
                          VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (paper_id, title, author, summary, content, tags, paper_references, timestamp),
        )
        self.conn.commit()

    def get_papers(self, filters=None):
        cursor = self.conn.cursor()
        query = "SELECT * FROM papers"
        if filters:
            conditions = []
            params = []
            if "tag" in filters and filters["tag"]:
                conditions.append("tags LIKE ?")
                params.append(f"%{filters['tag']}%")
            if "author" in filters and filters["author"]:
                conditions.append("author = ?")
                params.append(filters["author"])
            if "date" in filters and filters["date"]:
                conditions.append("timestamp >= ?")
                params.append(filters["date"])
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
                return cursor.execute(query, params).fetchall()
        return cursor.execute(query).fetchall()

    def add_institute(self, name, author, mission, tags):
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO institutes (name, author, mission, tags, registered_at) VALUES (?, ?, ?, ?, ?)",
            (name, author, mission, tags, datetime.now().isoformat()),
        )
        self.conn.commit()

    def validate_institute(self, author):
        cursor = self.conn.cursor()
        cursor.execute("SELECT 1 FROM institutes WHERE author = ?", (author,))
        return cursor.fetchone() is not None
