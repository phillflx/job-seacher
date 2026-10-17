"""Job model and SQLite persistence operations."""

import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Job:
    job_id: str = ""
    title: str = ""
    company: str = ""
    location: str = ""
    linkedin_url: str = ""
    listed: str = ""
    date_posted: str = ""
    description: str = ""
    easy_apply: bool = False
    apply_url: str = ""
    applied: bool = False


JOB_COLUMNS = (
    "job_id",
    "title",
    "company",
    "location",
    "linkedin_url",
    "listed",
    "date_posted",
    "description",
    "easy_apply",
    "apply_url",
    "applied",
)


def create_jobs_table(database_path: str | Path = "jobs.db") -> None:
    """Create the ``jobs`` table if it does not already exist."""
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


class Jobs:
    """SQLite repository for :class:`Job` records."""

    def __init__(self, database_path: str | Path = "jobs.db") -> None:
        self.database_path = Path(database_path)
        create_jobs_table(self.database_path)

    def create(self, job: Job) -> Job:
        """Insert *job* into the database and return it."""
        columns = ", ".join(JOB_COLUMNS)
        placeholders = ", ".join("?" for _ in JOB_COLUMNS)
        values = tuple(getattr(job, column) for column in JOB_COLUMNS)

        with closing(sqlite3.connect(self.database_path)) as connection:
            with connection:
                connection.execute(
                    f"INSERT INTO jobs ({columns}) VALUES ({placeholders})", values
                )
        return job

    def update(self, job: Job) -> Job:
        """Update an existing row matching *job.job_id* and return *job*.

        Raises ``LookupError`` if no row has that ID.
        """
        update_columns = JOB_COLUMNS[1:]
        assignments = ", ".join(f"{column} = ?" for column in update_columns)
        values = tuple(getattr(job, column) for column in update_columns) + (job.job_id,)

        with closing(sqlite3.connect(self.database_path)) as connection:
            with connection:
                cursor = connection.execute(
                    f"UPDATE jobs SET {assignments} WHERE job_id = ?", values
                )
        if cursor.rowcount == 0:
            raise LookupError(f"No job found with id {job.job_id!r}.")
        return job

    def get_by_id(self, id: str) -> Job:
        """Return the job with *id* or raise ``LookupError`` if it is absent."""
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                "SELECT * FROM jobs WHERE job_id = ? LIMIT 1", (id,)
            ).fetchone()

        if row is None:
            raise LookupError(f"No job found with id {id!r}.")
        return Job(**{column: row[column] for column in JOB_COLUMNS})
