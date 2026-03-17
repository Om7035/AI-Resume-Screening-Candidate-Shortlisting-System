"""PDF parsing logic for extracting resume text with PyPDF."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from pypdf import PdfReader

logger = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract all text from a PDF file."""
    logger.debug("Extracting text from PDF: %s", pdf_path)
    reader = PdfReader(str(pdf_path))
    text_chunks: list[str] = []

    for page_index, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        logger.debug("Extracted %d characters from page %d of %s", len(page_text), page_index, pdf_path.name)
        text_chunks.append(page_text)

    return "\n".join(text_chunks).strip()


def _extract_email(text: str) -> str:
    """Extract first email from plain text."""
    email_pattern = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
    match = re.search(email_pattern, text)
    return match.group(0) if match else ""


def process_resumes(folder_path: Path) -> list[dict[str, str]]:
    """Read all PDFs in a folder and return structured resume records."""
    logger.info("Scanning resume folder: %s", folder_path)

    if not folder_path.exists():
        raise FileNotFoundError(f"Resume folder not found: {folder_path}")

    records: list[dict[str, str]] = []
    pdf_files = sorted(folder_path.glob("*.pdf"))

    if not pdf_files:
        logger.warning("No PDF resumes found in %s", folder_path)

    for pdf_file in pdf_files:
        try:
            text = extract_text_from_pdf(pdf_file)
            candidate_name = pdf_file.stem.replace("_", " ").title()
            email = _extract_email(text)

            records.append(
                {
                    "file_name": pdf_file.name,
                    "file_path": str(pdf_file),
                    "candidate_name": candidate_name,
                    "email": email,
                    "resume_text": text,
                }
            )
            logger.info("Processed resume: %s", pdf_file.name)
        except Exception as error:  # continue processing remaining files
            logger.exception("Failed to process %s: %s", pdf_file, error)

    return records
