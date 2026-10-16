"""SQLite database initialization for scraped LinkedIn jobs."""

import sqlite3
from pathlib import Path


def create_jobs_table(database_path: str | Path = "jobs.db") -> None:
    """Create the ``jobs`` table with columns matching :class:`Job`.

    Boolean fields are stored as SQLite integers (0 or 1). The database file
    and its parent directory are created when they do not already exist.
    """
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT NOT NULL DEFAULT '',
                title TEXT NOT NULL DEFAULT '',
                company TEXT NOT NULL DEFAULT '',
                location TEXT NOT NULL DEFAULT '',
                linkedin_url TEXT NOT NULL DEFAULT '',
                listed TEXT NOT NULL DEFAULT '',
                date_posted TEXT NOT NULL DEFAULT '',
                description TEXT NOT NULL DEFAULT '',
                easy_apply INTEGER NOT NULL DEFAULT 0 CHECK (easy_apply IN (0, 1)),
                apply_url TEXT NOT NULL DEFAULT '',
                applied INTEGER NOT NULL DEFAULT 0 CHECK (applied IN (0, 1))
            )
            """
        )


if __name__ == "__main__":
    create_jobs_table()
