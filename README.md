# Elevate AI Interview Prep

A Streamlit app for AI-powered interview practice using Gemini.

## Setup

1. Create a Python virtual environment:
   ```bash
   python -m venv .venv
   .\.venv\Scripts\activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and add your Gemini API key:
   ```bash
   copy .env.example .env
   ```
4. Run the app locally:
   ```bash
   streamlit run app.py
   ```

## Streamlit Deployment

- Use `app.py` as the Streamlit entrypoint.
- Add `GEMINI_API_KEY` to your Streamlit deployment secrets or environment variables.
- Do not upload `.env` to the repository.

## Notes

- `.gitignore` already excludes `.env`, `.venv`, `__pycache__`, and Streamlit secrets.
- Keep sensitive API keys out of source control.
