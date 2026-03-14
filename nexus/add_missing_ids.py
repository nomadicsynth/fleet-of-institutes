import sqlite3
import os
from data import DataManager

def add_missing_ids(db_path="nexus.db"):
    data_manager = DataManager(db_path)
    conn = data_manager.conn
    cursor = conn.cursor()

    # Delete all existing IDs
    cursor.execute("UPDATE papers SET id = NULL")

    # Find papers with missing IDs
    cursor.execute("SELECT rowid, * FROM papers WHERE id IS NULL OR id = ''")
    papers = cursor.fetchall()

    for paper in papers:
        rowid = paper[0]
        new_id = data_manager._generate_arxiv_id()
        cursor.execute("UPDATE papers SET id = ? WHERE rowid = ?", (new_id, rowid))

    conn.commit()
    conn.close()

def migrate_database(db_path="nexus.db"):
    temp_db_path = "nexus_temp.db"

    # Connect to the existing database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create a new temporary database with the updated schema
    temp_conn = sqlite3.connect(temp_db_path)
    temp_cursor = temp_conn.cursor()
    temp_cursor.execute(
        """CREATE TABLE papers (
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

    # Copy data from the old table to the new table
    cursor.execute("SELECT * FROM papers")
    rows = cursor.fetchall()
    for row in rows:
        temp_cursor.execute(
            "INSERT INTO papers (id, title, author, summary, content, tags, paper_references, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (None, *row[1:])  # Set ID to None for regeneration
        )

    temp_conn.commit()

    # Replace the old database with the new one
    conn.close()
    temp_conn.close()
    os.replace(temp_db_path, db_path)

    # Regenerate IDs
    add_missing_ids(db_path)

if __name__ == "__main__":
    migrate_database()