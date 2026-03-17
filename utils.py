import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def setup_logging(log_file: Path) -> None:
    """Configure basic logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
    )


def ensure_directory(path: Path) -> None:
    """Ensure a directory exists."""
    path.mkdir(parents=True, exist_ok=True)


def read_text_file(path: Path) -> str:
    """Read contents of a text file."""
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    return path.read_text(encoding="utf-8")


def save_json(path: Path, data: Any) -> None:
    """Save data to a JSON file."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


def print_ranked_candidates(ranked: list[dict[str, Any]]) -> None:
    """Print the ranked candidates to the console."""
    print("\n=== Ranked Candidates ===")
    for rank, candidate in enumerate(ranked, start=1):
        score = candidate.get("score", 0)
        name = candidate.get("candidate_name", "Unknown")
        print(f"{rank}. {name} - Score: {score}")
