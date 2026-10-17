"""Compatibility entry point for initializing the jobs database."""

from .job import create_jobs_table


if __name__ == "__main__":
    create_jobs_table()
