"""LLM scoring logic for resume-job matching."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import requests

from config import settings

logger = logging.getLogger(__name__)


class ResumeScorer:
    """Scores resumes against a job description using Gemini API."""

    def __init__(self, provider: str | None = None) -> None:
        self.provider = (provider or settings.llm_provider).lower()

    def score_resume(self, resume_text: str, job_description: str) -> dict[str, Any]:
        """Score a single resume and return a normalized result dictionary."""
        prompt = self._build_prompt(resume_text=resume_text, job_description=job_description)

        try:
            if self.provider != "gemini":
                raise ValueError(
                    f"Unsupported provider '{self.provider}'. Set LLM_PROVIDER=gemini for free-tier usage."
                )

            raw_content = self._call_gemini(prompt)
            parsed = self._parse_llm_json(raw_content)
            score = int(max(0, min(100, parsed.get("score", 0))))
            reason = str(parsed.get("reason", "No reason provided by model.")).strip()
            return {"score": score, "reason": reason, "source": "llm"}
        except Exception as error:
            logger.exception("LLM scoring failed; using fallback scorer: %s", error)
            fallback_score, fallback_reason = self._fallback_score(resume_text, job_description)
            return {"score": fallback_score, "reason": fallback_reason, "source": "fallback"}

    @staticmethod
    def _build_prompt(resume_text: str, job_description: str) -> str:
        """Create the prompt sent to Gemini."""
        return f"""
You are an AI recruiter.
Compare the candidate resume with the job description.
Return STRICT JSON only:
{{"score": <integer between 0 and 100>, "reason": "<short explanation>"}}

JOB DESCRIPTION:
{job_description[:6000]}

RESUME:
{resume_text[:6000]}
""".strip()

    @staticmethod
    def _parse_llm_json(raw_content: str) -> dict[str, Any]:
        """Parse JSON object from model output (robustly)."""
        content = raw_content.strip()
        content = re.sub(r"^```json\s*|```$", "", content, flags=re.IGNORECASE | re.MULTILINE).strip()

        json_match = re.search(r"\{.*\}", content, flags=re.DOTALL)
        candidate = json_match.group(0) if json_match else content
        return json.loads(candidate)

    def _call_gemini(self, prompt: str) -> str:
        """Call Gemini generateContent API."""
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is missing")

        model = settings.gemini_model
        url = f"{settings.gemini_base_url.rstrip('/')}/{model}:generateContent?key={settings.gemini_api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "response_mime_type": "application/json",
            },
        }

        logger.debug("Calling Gemini API model=%s", model)
        response = requests.post(url, json=payload, timeout=settings.request_timeout_seconds)
        response.raise_for_status()
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]

    @staticmethod
    def _fallback_score(resume_text: str, job_description: str) -> tuple[int, str]:
        """Simple keyword overlap fallback when API key/network is unavailable."""
        jd_words = {word.lower() for word in re.findall(r"[A-Za-z]{3,}", job_description)}
        resume_words = {word.lower() for word in re.findall(r"[A-Za-z]{3,}", resume_text)}
        if not jd_words:
            return 0, "Fallback scorer: empty job description."

        overlap = jd_words & resume_words
        score = int((len(overlap) / len(jd_words)) * 100)
        reason = f"Fallback scorer used. Keyword overlap: {len(overlap)} of {len(jd_words)} keywords."
        return max(0, min(100, score)), reason
