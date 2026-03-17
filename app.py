"""Flask web UI for the AI Resume Screening & Candidate Shortlisting System."""

from __future__ import annotations

import logging
import shutil
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request, send_file

# Ensure local project modules can be imported
sys.path.insert(0, str(Path(__file__).resolve().parent))

from resume_parser import process_resumes  # noqa: E402
from scorer import ResumeScorer  # noqa: E402
from utils import ensure_directory  # noqa: E402

logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB

# In-memory store: token -> absolute Path of the stored PDF
_resume_store: dict[str, Path] = {}

# Persistent temp dir that lives for the lifetime of the server process
_UPLOAD_DIR = Path(tempfile.mkdtemp(prefix="resume_screener_"))


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/resume/<token>")
def serve_resume(token: str):
    """Serve a previously uploaded PDF by its session token."""
    path = _resume_store.get(token)
    if not path or not path.exists():
        return "Resume not found or session expired.", 404
    return send_file(path, mimetype="application/pdf")


@app.route("/api/screen", methods=["POST"])
def screen_resumes():
    """Main pipeline endpoint: receive PDFs + JD, return ranked results."""
    try:
        # --- Parse form data ---
        job_description = request.form.get("job_description", "").strip()
        if not job_description:
            return jsonify({"error": "Job description is required."}), 400

        api_key = request.form.get("gemini_api_key", "").strip()
        provider = request.form.get("llm_provider", "gemini").strip()
        top_n = int(request.form.get("top_n", "3"))

        uploaded_files = request.files.getlist("resumes")
        if not uploaded_files or all(f.filename == "" for f in uploaded_files):
            return jsonify({"error": "At least one PDF resume is required."}), 400

        # --- Save uploaded PDFs to a persistent session directory ---
        session_id = uuid.uuid4().hex
        session_dir = _UPLOAD_DIR / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        for uploaded_file in uploaded_files:
            if uploaded_file.filename and uploaded_file.filename.lower().endswith(".pdf"):
                safe_name = Path(uploaded_file.filename).name
                dest = session_dir / safe_name
                uploaded_file.save(dest)
                # Register this PDF with a unique token for serving
                token = uuid.uuid4().hex
                _resume_store[token] = dest

        pdf_files = list(session_dir.glob("*.pdf"))
        if not pdf_files:
            return jsonify({"error": "No valid PDF files were uploaded."}), 400

        # Build a filename -> token lookup so we can attach URLs to results
        filename_to_token: dict[str, str] = {
            path: tok
            for tok, path in _resume_store.items()
            if path.parent == session_dir
        }

        # --- Inject runtime API key into global config for the scorer ---
        import config as _cfg
        _cfg.settings.llm_provider = provider
        if provider == "gemini" and api_key:
            _cfg.settings.gemini_api_key = api_key
        elif provider == "openai" and api_key:
            _cfg.settings.openai_api_key = api_key

        # --- Run pipeline ---
        resumes = process_resumes(session_dir)
        scorer = ResumeScorer(provider=provider)

        for i, resume in enumerate(resumes):
            resume.update(
                scorer.score_resume(
                    resume_text=resume["resume_text"],
                    job_description=job_description,
                )
            )
            # Delay between LLM calls to avoid rate limits (skip for fallback)
            if provider != "fallback" and i < len(resumes) - 1:
                time.sleep(3)

        ranked: list[dict[str, Any]] = sorted(  # type: ignore[assignment]
            resumes, key=lambda item: item.get("score", 0), reverse=True
        )

        # --- Intelligent shortlisting using Gemini's recommendation ---
        # Step 1: All candidates Gemini explicitly said "shortlist", sorted by score
        strong = [c for c in ranked
                  if c.get("recommendation") == "shortlist"
                  and c.get("score", 0) >= ResumeScorer.MIN_SCORE]
        # Step 2: Fill remaining slots with "consider" candidates (Gemini said maybe)
        consider = [c for c in ranked
                    if c.get("recommendation") == "consider"
                    and c.get("score", 0) >= ResumeScorer.MIN_SCORE]
        shortlisted = (strong + consider)[: max(0, top_n)]

        # Attach view URL and strip large fields from response
        for candidate in ranked:
            candidate.pop("resume_text", None)
            file_path_str = candidate.pop("file_path", None)
            if file_path_str:
                file_path = Path(file_path_str)
                tok = filename_to_token.get(file_path)
                candidate["resume_url"] = f"/resume/{tok}" if tok else None

        return jsonify({
            "total": len(ranked),
            "top_n": top_n,
            "provider": provider,
            "ranked": ranked,
            "shortlisted": shortlisted,
        })

    except Exception as exc:
        import traceback
        logger.error("Pipeline error: %s\n%s", exc, traceback.format_exc())
        return jsonify({"error": str(exc)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
