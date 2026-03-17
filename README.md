# AI Resume Screening & Candidate Shortlisting System

A beginner-friendly, production-style Python project that:

- Parses multiple PDF resumes from a folder (using **PyPDF**)
- Reads a job description from a text file or CLI input
- Scores each resume against the job description using an LLM API (**OpenAI** or **Gemini**, via `requests`)
- Ranks candidates and builds a shortlist
- Saves results to JSON files
- Optionally sends shortlist notification emails via Gmail SMTP
- Logs every major step to `output/app.log`

---

## Project Structure

```text
.
├── main.py
├── parser.py
├── scorer.py
├── emailer.py
├── utils.py
├── config.py
├── requirements.txt
├── .env.example
├── sample_data/
│   ├── job_description.txt
│   └── resumes/
│       ├── alice_johnson.pdf
│       ├── bob_smith.pdf
│       └── carol_lee.pdf
└── output/
```

---

## How It Works (End-to-End)

1. `main.py` loads configuration from environment variables.
2. `parser.py` scans the resume folder and extracts PDF text.
3. `scorer.py` sends resume + JD to OpenAI/Gemini and expects strict JSON: `{"score": <0-100>, "reason": "..."}`.
4. If LLM API call fails (no key/network), a fallback keyword-overlap scorer is used.
5. Candidates are ranked by score and top-N are shortlisted.
6. Results are saved:
   - `output/results.json` (full run details)
   - `output/shortlist.json` (shortlisted candidates only)
7. Optional: `emailer.py` sends notification emails to shortlisted candidates.

---

## Setup Instructions

## 1) Create and activate virtual environment

### Linux/macOS
```bash
python -m venv .venv
source .venv/bin/activate
```

### Windows (PowerShell)
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

## 2) Install dependencies

```bash
pip install -r requirements.txt
```

## 3) Configure environment variables

Copy example file and edit it:

```bash
cp .env.example .env
```

Required fields:

- For OpenAI:
  - `LLM_PROVIDER=openai`
  - `OPENAI_API_KEY=...`
- For Gemini:
  - `LLM_PROVIDER=gemini`
  - `GEMINI_API_KEY=...`
- For email sending:
  - `EMAIL_USERNAME=your_gmail@gmail.com`
  - `EMAIL_PASSWORD=your_gmail_app_password`

> Gmail note: Use an **App Password**, not your normal Gmail password.

## 4) Run the app

### Use sample data
```bash
python main.py
```

### Custom paths
```bash
python main.py --resumes-dir /path/to/resumes --job-description-file /path/to/jd.txt --top-n 5
```

### Pass job description directly from CLI
```bash
python main.py --job-description-text "Looking for a Python NLP engineer with ML and API experience"
```

### Send shortlist emails
```bash
python main.py --send-email
```

---

## CLI Options

- `--resumes-dir` : folder containing PDF resumes
- `--job-description-file` : path to a text file containing JD
- `--job-description-text` : raw JD string (overrides file)
- `--top-n` : number of candidates to shortlist
- `--send-email` : send email notifications to shortlisted candidates

---

## Output Files

- `output/results.json`:
  - all candidates
  - scores/reasons
  - ranking
  - shortlist
  - email summary
- `output/shortlist.json`:
  - only shortlisted candidates
- `output/app.log`:
  - detailed debug & error logs

---

## Notes for Beginners

- Start without email: run `python main.py` first.
- If API key is missing, scoring still works via fallback mode.
- Keep your `.env` private (never commit real keys/passwords).
- Add your own resumes in `sample_data/resumes/` as `.pdf` files.

---

## Production Tips

- Move secrets to a proper secret manager in deployment.
- Add retry logic and rate-limit handling for LLM APIs.
- Add schema validation for model responses.
- Add unit tests (parser, scorer fallback, email formatting).
- Run this pipeline on schedule (cron/Airflow) for large hiring workflows.
