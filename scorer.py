"""LLM scoring logic for resume-job matching with multi-dimensional evaluation."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import requests

from config import settings

logger = logging.getLogger(__name__)


class ResumeScorer:
    """
    Scores resumes against a job description using OpenAI or Gemini APIs.

    Evaluation dimensions (each 0-100):
      • technical_score    – How well hard skills / tech stack match the JD
      • experience_score   – Relevance & seniority of work history
      • education_score    – Qualification & certification fit
      • suitability_score  – Overall role suitability (culture, domain, soft skills)
      • overall_score      – Weighted composite (used for ranking)

    Gemini also returns an explicit recommendation:
      "shortlist" | "consider" | "reject"

    Shortlisting rule (applied in app.py):
      1. All candidates with recommendation == "shortlist", sorted by overall_score desc
      2. If slots remain, fill with "consider" candidates sorted by overall_score desc
      3. Threshold: candidates with overall_score < MIN_SCORE are always excluded
    """

    MIN_SCORE = 40  # Candidates below this are never shortlisted

    def __init__(self, provider: str | None = None) -> None:
        self.provider = (provider or settings.llm_provider).lower()

    def score_resume(self, resume_text: str, job_description: str) -> dict[str, Any]:
        """Score a single resume and return a rich evaluation dictionary."""

        # Explicit fallback mode — skip LLM, use keyword overlap
        if self.provider == "fallback":
            return self._fallback_result(resume_text, job_description)

        prompt = self._build_prompt(resume_text=resume_text, job_description=job_description)

        try:
            if self.provider == "openai":
                raw_content = self._call_openai(prompt)
            elif self.provider == "gemini":
                raw_content = self._call_gemini(prompt)
            else:
                raise ValueError(f"Unsupported LLM provider: {self.provider}")

            return self._parse_and_normalize(raw_content, source="llm")

        except Exception as error:
            logger.exception("LLM scoring failed; using fallback scorer: %s", error)
            return self._fallback_result(resume_text, job_description)

    # ------------------------------------------------------------------
    # Prompt
    # ------------------------------------------------------------------

    @staticmethod
    def _build_prompt(resume_text: str, job_description: str) -> str:
        jd_snippet: str = job_description[:5000]
        resume_snippet: str = resume_text[:5000]
        return f"""
You are a senior technical recruiter performing a rigorous resume evaluation.

Analyze the candidate resume against the job description below.
Return ONLY a single valid JSON object — no markdown, no extra text.

Required JSON schema:
{{
  "overall_score": <integer 0-100>,
  "technical_score": <integer 0-100>,
  "experience_score": <integer 0-100>,
  "education_score": <integer 0-100>,
  "suitability_score": <integer 0-100>,
  "recommendation": "<shortlist | consider | reject>",
  "strengths": ["<strength 1>", "<strength 2>", "<strength 3>"],
  "gaps": ["<gap 1>", "<gap 2>"],
  "reason": "<1-2 sentence summary of the evaluation>"
}}

Scoring rubric:
- technical_score: Hard skills, programming languages, frameworks, tools that match the JD
- experience_score: Years of relevant experience, seniority level, domain relevance
- education_score: Degree, certifications, training relevant to the role
- suitability_score: Overall role fit — soft skills, projects, domain knowledge, culture signals
- overall_score: Weighted average (technical 40%, experience 35%, education 10%, suitability 15%)

Recommendation rules:
- "shortlist": overall_score >= 65 AND technical_score >= 60 AND experience_score >= 60
- "consider":  overall_score >= 45 OR (technical_score >= 55 and the candidate shows strong potential)
- "reject":    overall_score < 45 OR critical skill gaps that cannot be overlooked

JOB DESCRIPTION:
{jd_snippet}

RESUME:
{resume_snippet}
""".strip()

    # ------------------------------------------------------------------
    # API calls
    # ------------------------------------------------------------------

    def _call_openai(self, prompt: str) -> str:
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is missing")
        url = f"{settings.openai_base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": settings.openai_model,
            "messages": [
                {"role": "system", "content": "You are a strict JSON generator. Return only raw JSON, no markdown."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }
        logger.debug("Calling OpenAI API model=%s", settings.openai_model)
        response = requests.post(url, headers=headers, json=payload, timeout=settings.request_timeout_seconds)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    def _call_gemini(self, prompt: str) -> str:
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is missing")
        model = settings.gemini_model
        url = f"{settings.gemini_base_url.rstrip('/')}/{model}:generateContent?key={settings.gemini_api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json",
            },
        }
        logger.debug("Calling Gemini API model=%s", model)
        response = requests.post(url, json=payload, timeout=settings.request_timeout_seconds)
        response.raise_for_status()
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]

    # ------------------------------------------------------------------
    # Parsing & normalization
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_and_normalize(raw_content: str, source: str) -> dict[str, Any]:
        raw_content = raw_content.strip()
        json_match = re.search(r"\{.*\}", raw_content, flags=re.DOTALL)
        candidate = json_match.group(0) if json_match else raw_content
        parsed = json.loads(candidate)

        def clamp(v: Any) -> int:
            try:
                return int(max(0, min(100, v)))
            except (TypeError, ValueError):
                return 0

        overall = clamp(parsed.get("overall_score", 0))
        recommendation = str(parsed.get("recommendation", "consider")).lower().strip()
        if recommendation not in ("shortlist", "consider", "reject"):
            recommendation = "consider"

        strengths = parsed.get("strengths", [])
        if not isinstance(strengths, list):
            strengths = []
        gaps = parsed.get("gaps", [])
        if not isinstance(gaps, list):
            gaps = []

        return {
            "score": overall,  # kept for backward compat / ranking sort key
            "overall_score": overall,
            "technical_score": clamp(parsed.get("technical_score", 0)),
            "experience_score": clamp(parsed.get("experience_score", 0)),
            "education_score": clamp(parsed.get("education_score", 0)),
            "suitability_score": clamp(parsed.get("suitability_score", 0)),
            "recommendation": recommendation,
            "strengths": strengths[:5],
            "gaps": gaps[:5],
            "reason": str(parsed.get("reason", "")).strip(),
            "source": source,
        }

    # ------------------------------------------------------------------
    # Fallback: keyword overlap (when no API key / API fails)
    # ------------------------------------------------------------------

    @staticmethod
    def _fallback_result(resume_text: str, job_description: str) -> dict[str, Any]:
        jd_words = {w.lower() for w in re.findall(r"[A-Za-z]{3,}", job_description)}
        resume_words = {w.lower() for w in re.findall(r"[A-Za-z]{3,}", resume_text)}
        if not jd_words:
            overall = 0
            reason = "Fallback scorer: empty job description."
        else:
            overlap = jd_words & resume_words
            overall = int(max(0, min(100, (len(overlap) / len(jd_words)) * 100)))
            reason = (
                f"Keyword-overlap fallback: {len(overlap)} of {len(jd_words)} JD keywords matched in resume. "
                "No LLM was used — add an API key for semantic evaluation."
            )

        recommendation = "shortlist" if overall >= 65 else ("consider" if overall >= 45 else "reject")
        return {
            "score": overall,
            "overall_score": overall,
            "technical_score": overall,
            "experience_score": overall,
            "education_score": overall,
            "suitability_score": overall,
            "recommendation": recommendation,
            "strengths": [],
            "gaps": [],
            "reason": reason,
            "source": "fallback",
        }
