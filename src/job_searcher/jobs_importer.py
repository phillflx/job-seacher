"""Persist scraped jobs in the project's SQLite database."""

import logging
import sqlite3
from pathlib import Path
from typing import Iterable

from .job import Job, create_jobs_table, JOB_COLUMNS

logger = logging.getLogger(__name__)


class JobsImporter:
    """Insert jobs into SQLite, skipping jobs that are already present."""

    def __init__(self, database_path: str | Path = "jobs.db") -> None:
        logger.info("JobsImporter.__init__(database_path=%s)", database_path)
        self.database_path = Path(database_path)
        create_jobs_table(self.database_path)

    def persist_jobs(self, jobs: Iterable[Job]) -> int:
        """Insert new jobs and return how many rows were added.

        Jobs are considered duplicates when their non-empty LinkedIn job ID
        matches. If an ID is unavailable, their LinkedIn URL is used instead.
        """
        jobs_count = len(jobs) if hasattr(jobs, "__len__") else "unknown"
        logger.info(
            "JobsImporter.persist_jobs(jobs_type=%s, jobs_count=%s)",
            type(jobs).__name__, jobs_count,
        )
        inserted = 0
        placeholders = ", ".join("?" for _ in JOB_COLUMNS)
        columns = ", ".join(JOB_COLUMNS)

        with sqlite3.connect(self.database_path) as connection:
            for job in jobs:
                if None in [job.title, job.company, job.location]:
                    continue

                values = tuple(getattr(job, column) for column in JOB_COLUMNS)
                job_id = str(getattr(job, "job_id", "") or "").strip()
                linkedin_url = str(getattr(job, "linkedin_url", "") or "").strip()

                if job_id:
                    exists = connection.execute(
                        "SELECT 1 FROM jobs WHERE job_id = ? LIMIT 1", (job_id,)
                    ).fetchone()
                elif linkedin_url:
                    exists = connection.execute(
                        "SELECT 1 FROM jobs WHERE linkedin_url = ? LIMIT 1", (linkedin_url,)
                    ).fetchone()
                else:
                    # Without a stable LinkedIn identifier, use the available
                    # descriptive fields to avoid inserting the same listing twice.
                    exists = connection.execute(
                        """SELECT 1 FROM jobs
                           WHERE job_id = '' AND linkedin_url = ''
                             AND title = ? AND company = ? AND location = ?
                             AND date_posted = ?
                           LIMIT 1""",
                        (
                            getattr(job, "title", ""),
                            getattr(job, "company", ""),
                            getattr(job, "location", ""),
                            getattr(job, "date_posted", ""),
                        ),
                    ).fetchone()

                if exists:
                    continue

                connection.execute(
                    f"INSERT INTO jobs ({columns}) VALUES ({placeholders})", values
                )
                inserted += 1

        return inserted
