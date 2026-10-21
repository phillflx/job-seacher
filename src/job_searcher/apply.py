"""Apply to one saved LinkedIn job by its job ID."""

import argparse
import logging
from time import sleep

from dotenv import load_dotenv
load_dotenv()

from .job import Jobs
from .job_applier import JobApplier
from .profile_loader import load_profile
from .session_manager import SessionManager

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(description="Apply to one saved LinkedIn job.")
    parser.add_argument("--lu", required=True, help="LinkedIn username")
    parser.add_argument("--lpwd", required=True, help="LinkedIn password")
    parser.add_argument("--job_id", required=True, help="LinkedIn job ID")
    parser.add_argument(
        "--profile",
        default="career-profile",
        help="Directory containing profile TXT, Markdown, or PDF files",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    """Apply to one saved, unapplied Easy Apply job."""
    args = build_parser().parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    jobs = Jobs()
    try:
        job = jobs.get_by_id(args.job_id)
    except LookupError as error:
        raise SystemExit(str(error)) from error

    if job.applied:
        raise SystemExit(f"Job {args.job_id!r} is already marked as applied.")
    if not job.easy_apply:
        raise SystemExit(f"Job {args.job_id!r} is not marked as an Easy Apply job.")

    profile = load_profile(args.profile)
    logger.info("Applying to saved job_id=%s", job.job_id)

    session = SessionManager()
    try:
        session.authenticate(user=args.lu, password=args.lpwd)
        sleep(1)
        JobApplier(session, profile).apply_to_job(job)
    finally:
        session.driver.quit()


if __name__ == "__main__":
    main()
