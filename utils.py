"""General utility functions for the resume screening project."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any


def setup_logging(log_file: Path) -> None:
    """Configure logging to file and console."""
    log_file.parent.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def ensure_directory(path: Path) -> None:
    """Create directory if it does not exist."""
    path.mkdir(parents=True, exist_ok=True)


def read_text_file(path: Path) -> str:
    """Safely read a UTF-8 text file."""
    return path.read_text(encoding="utf-8").strip()


def save_json(path: Path, data: Any) -> None:
    """Write Python object as pretty JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)


def print_ranked_candidates(ranked_results: list[dict[str, Any]]) -> None:
    """Print a simple ranking table in the terminal."""
    print("\n=== Ranked Candidates ===")
    for rank, item in enumerate(ranked_results, start=1):
        name = item.get("candidate_name", "Unknown")
        score = item.get("score", 0)
        email = item.get("email", "N/A")
        reason = item.get("reason", "")
        print(f"{rank:>2}. {name:<25} Score: {score:>3} | Email: {email}")
        if reason:
            print(f"    Reason: {reason}")
    print("=========================\n")
