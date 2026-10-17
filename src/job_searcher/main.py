"""Command-line job search and Easy Apply workflow."""

import argparse
import logging
import sys
from time import sleep

from dotenv import load_dotenv
load_dotenv()

from .job import Jobs
from .job_applier import JobApplier
from .job_search import JobSearch
from .jobs_importer import JobsImporter
from .profile_loader import load_profile
from .session_manager import SessionManager

logger = logging.getLogger(__name__)

def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(description="Search LinkedIn jobs and optionally apply.")
    parser.add_argument("--lu", required=True, help="LinkedIn username")
    parser.add_argument("--lpwd", required=True, help="LinkedIn password")
    parser.add_argument(
        "--title", nargs="+", required=True, help="One or more job titles to search"
    )
    parser.add_argument(
        "--location", nargs="+", required=True, help="One or more locations to search"
    )
    parser.add_argument(
        "--limit", type=int, default=50, help="Maximum jobs to collect per search (default: 50)"
    )
    parser.add_argument(
        "--apply", action="store_true", help="Apply to stored, unapplied Easy Apply jobs"
    )
    parser.add_argument(
        "--profile",
        default="career-profile",
        help="Directory containing profile TXT, Markdown, or PDF files",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    """Search/import jobs for every title-location pair, then optionally apply."""
    args = build_parser().parse_args(argv)
    if args.limit <= 0:
        raise SystemExit("--limit must be greater than zero")

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logger.info(
        "Starting job workflow for %d titles x %d locations (limit=%d, apply=%s)",
        len(args.title), len(args.location), args.limit, args.apply,
    )

    session = SessionManager()
    try:
        session.authenticate(user=args.lu, password=args.lpwd)
        sleep(1)
        job_search = JobSearch(session)
        importer = JobsImporter()
        searched = 0
        inserted = 0

        for title in args.title:
            for location in args.location:
                logger.info("Searching title=%r at location=%r", title, location)
                try:
                    jobs = job_search.search(title, args.limit, location=location)
                    inserted_for_search = importer.persist_jobs(jobs)
                    searched += len(jobs)
                    inserted += inserted_for_search
                    logger.info(
                        "Search returned %d jobs; imported %d new jobs",
                        len(jobs), inserted_for_search,
                    )
                except Exception:
                    logger.exception("Search/import failed for title=%r location=%r", title, location)

        logger.info("Search/import phase complete: found=%d inserted=%d", searched, inserted)
        if not args.apply:
            return

        profile = load_profile(args.profile)
        pending_jobs = Jobs().get_unapplied_easy_apply(sys.maxsize)
        logger.info("Found %d unapplied Easy Apply jobs to process", len(pending_jobs))
        applier = JobApplier(session, profile)
        for index, job in enumerate(pending_jobs, start=1):
            logger.info(
                "Applying to job %d/%d (job_id=%s)",
                index, len(pending_jobs), job.job_id or "unknown",
            )
            try:
                applier.apply_to_job(job)
            except Exception:
                logger.exception("Application failed for job_id=%s", job.job_id or "unknown")
    finally:
        session.driver.quit()


if __name__ == "__main__":
    main()
