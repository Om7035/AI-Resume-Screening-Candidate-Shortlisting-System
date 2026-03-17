import logging

logger = logging.getLogger(__name__)


def notify_shortlisted_candidates(candidates: list[dict[str, str]]) -> dict[str, int]:
    """Mock sending email notifications."""
    logger.info("Mocking email send for %d candidates...", len(candidates))
    return {"sent": len(candidates), "failed": 0}
