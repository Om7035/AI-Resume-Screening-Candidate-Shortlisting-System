"""Entry point for AI Resume Screening & Candidate Shortlisting System."""

from __future__ import annotations

import argparse
import logging
from datetime import datetime
from pathlib import Path

from typing import Any

from config import settings
from emailer import notify_shortlisted_candidates
from resume_parser import process_resumes
from scorer import ResumeScorer
from utils import ensure_directory, print_ranked_candidates, read_text_file, save_json, setup_logging

logger = logging.getLogger(__name__)


def run_pipeline(
    resumes_dir: Path,
    job_description: str,
    top_n: int,
    send_email: bool,
) -> dict:
    """Run full resume screening flow and return structured output."""
    resumes = process_resumes(resumes_dir)
    scorer = ResumeScorer()

    logger.info("Scoring %d resumes", len(resumes))
    for resume in resumes:
        score_data = scorer.score_resume(resume_text=resume["resume_text"], job_description=job_description)
        resume.update(score_data)
        import time
        time.sleep(4)

    ranked: list[dict[str, Any]] = sorted(resumes, key=lambda item: item.get("score", 0), reverse=True)  # type: ignore
    shortlisted = ranked[: max(0, top_n)]

    print_ranked_candidates(ranked)

    email_summary = {"sent": 0, "failed": 0}
    if send_email and shortlisted:
        logger.info("Sending shortlist emails to top %d candidates", len(shortlisted))
        email_summary = notify_shortlisted_candidates(shortlisted)

    result = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "provider": settings.llm_provider,
        "total_resumes": len(resumes),
        "top_n": top_n,
        "email_notifications": email_summary,
        "ranked_candidates": ranked,
        "shortlisted_candidates": shortlisted,
    }
    return result


def parse_args() -> argparse.Namespace:
    """Parse command-line options for the script."""
    parser = argparse.ArgumentParser(description="AI Resume Screening & Candidate Shortlisting System")
    parser.add_argument("--resumes-dir", default=str(settings.resumes_dir), help="Folder containing PDF resumes")
    parser.add_argument(
        "--job-description-file",
        default=str(settings.job_description_file),
        help="Path to job description text file",
    )
    parser.add_argument("--job-description-text", default="", help="Raw job description text (overrides file)")
    parser.add_argument("--top-n", type=int, default=settings.shortlist_top_n, help="Number of top candidates")
    parser.add_argument(
        "--send-email",
        action="store_true",
        help="Send emails to shortlisted candidates using SMTP settings",
    )
    return parser.parse_args()


def main() -> None:
    """Bootstrap and execute the pipeline."""
    args = parse_args()

    ensure_directory(settings.output_dir)
    log_file = settings.output_dir / "app.log"
    setup_logging(log_file)

    logger.info("Starting AI Resume Screening system")

    if args.job_description_text.strip():
        job_description = args.job_description_text.strip()
    else:
        job_description = read_text_file(Path(args.job_description_file))

    result = run_pipeline(
        resumes_dir=Path(args.resumes_dir),
        job_description=job_description,
        top_n=args.top_n,
        send_email=args.send_email,
    )

    full_results_path = settings.output_dir / "results.json"
    shortlist_path = settings.output_dir / "shortlist.json"

    save_json(full_results_path, result)
    save_json(shortlist_path, result["shortlisted_candidates"])

    logger.info("Saved full results to %s", full_results_path)
    logger.info("Saved shortlist to %s", shortlist_path)
    logger.info("Pipeline completed successfully")


if __name__ == "__main__":
    main()
