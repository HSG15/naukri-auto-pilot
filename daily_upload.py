"""
daily_upload.py — Naukri resume auto-uploader
Fetches resume from Google Drive, renames with today's date,
uploads to Naukri at 9 AM and 2 PM daily.

Setup:
  1. pip install -r requirements.txt schedule
  2. Copy .env.example → .env and fill values
  3. python daily_upload.py
"""

import os
import sys
import time
import logging
import schedule
import requests
from io import BytesIO
from datetime import datetime
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

# ── project imports ─────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))
from src.client.naukri_client import NaukriLoginClient
from src.exceptions.exceptions import NaukriClientError

# ── logging ─────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("daily_upload.log", encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)

load_dotenv()

# ── config (from .env) ───────────────────────────────────────────
NAUKRI_USERNAME   = os.getenv("NAUKRI_USERNAME", "")
NAUKRI_PASSWORD   = os.getenv("NAUKRI_PASSWORD", "")
GDRIVE_FILE_ID    = os.getenv("GDRIVE_FILE_ID", "")   # from share link
RESUME_BASE_NAME  = os.getenv("RESUME_BASE_NAME", "resume")   # e.g. "harishankar_resume"
HEADLINE          = os.getenv("NAUKRI_HEADLINE", "")          # optional profile headline update
UPLOAD_TIMES      = ["09:15", "14:00"]                        # 9:15 AM and 2 PM


# ── helpers ──────────────────────────────────────────────────────

def dated_filename() -> str:
    """e.g. Harishankar_Giri_Data_Engineer_Resume_18May2026.pdf"""
    return f"{RESUME_BASE_NAME}_{datetime.now().strftime('%d%b%Y')}.pdf"


def download_from_gdrive(file_id: str) -> bytes:
    """
    Download a file from Google Drive.
    Works for files shared as 'Anyone with the link can view'.
    Handles GDrive's virus-scan confirmation redirect for large files.
    """
    session = requests.Session()

    def _get(url, **kwargs):
        return session.get(url, timeout=30, **kwargs)

    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    resp = _get(url)
    resp.raise_for_status()

    # Large files → GDrive shows a confirm page instead of the file
    if b"virus scan warning" in resp.content.lower() or b"confirm" in resp.content[:500].lower():
        # Extract confirm token
        import re
        token_match = re.search(rb'confirm=([0-9A-Za-z_\-]+)', resp.content)
        if token_match:
            token = token_match.group(1).decode()
            confirm_url = f"{url}&confirm={token}"
            resp = _get(confirm_url)
            resp.raise_for_status()

    if resp.content[:4] != b"%PDF":
        raise ValueError(
            "Downloaded content is not a valid PDF. "
            "Check GDRIVE_FILE_ID and that the file is publicly shared."
        )

    log.info("Downloaded %.1f KB from GDrive", len(resp.content) / 1024)
    return resp.content


def upload_once():
    """Single upload cycle: login → download → rename → upload → (optional) headline."""
    log.info("=" * 55)
    log.info("Starting upload cycle at %s", datetime.now().strftime("%Y-%m-%d %H:%M"))

    # ── validate config ──────────────────────────────────────────
    missing = [k for k, v in {
        "NAUKRI_USERNAME": NAUKRI_USERNAME,
        "NAUKRI_PASSWORD": NAUKRI_PASSWORD,
        "GDRIVE_FILE_ID":  GDRIVE_FILE_ID,
    }.items() if not v]

    if missing:
        log.error("Missing env vars: %s  →  check your .env file", ", ".join(missing))
        return False

    # ── download resume from GDrive ──────────────────────────────
    try:
        pdf_bytes = download_from_gdrive(GDRIVE_FILE_ID)
    except Exception as exc:
        log.error("GDrive download failed: %s", exc)
        return False

    filename = dated_filename()
    log.info("Using filename: %s", filename)

    # ── write to temp file (NaukriClient expects a path or file-like) ─
    tmp_path = f"/tmp/{filename}"
    with open(tmp_path, "wb") as f:
        f.write(pdf_bytes)

    # ── login ────────────────────────────────────────────────────
    client = NaukriLoginClient(NAUKRI_USERNAME, NAUKRI_PASSWORD)
    try:
        client.login()
        log.info("Login successful")
    except NaukriClientError as exc:
        log.error("Login failed: %s", exc)
        return False

    # ── upload resume ────────────────────────────────────────────
    try:
        result = client.update_resume(tmp_path)
        log.info(
            "Resume uploaded  ✓  (profile_id=%s  status=%s)",
            result.profile_id, result.status_code,
        )
    except NaukriClientError as exc:
        log.error("Resume upload failed: %s", exc)
        return False
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    # ── optional: update headline ────────────────────────────────
    if HEADLINE:
        try:
            client.update_profile(headline=HEADLINE)
            log.info("Headline updated  ✓")
        except NaukriClientError as exc:
            log.warning("Headline update failed (non-fatal): %s", exc)

    log.info("Cycle complete  ✓")
    log.info("=" * 55)
    return True


# ── scheduler ────────────────────────────────────────────────────

def run_scheduler():
    for t in UPLOAD_TIMES:
        schedule.every().day.at(t).do(upload_once)
        log.info("Scheduled daily upload at %s", t)

    log.info("Scheduler running. Press Ctrl+C to stop.")
    log.info("Next run: %s", schedule.next_run())

    while True:
        schedule.run_pending()
        time.sleep(30)


# ── entry point ──────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Naukri daily resume uploader")
    parser.add_argument(
        "--now",
        action="store_true",
        help="Run one upload immediately and exit (useful for testing)",
    )
    args = parser.parse_args()

    if args.now:
        success = upload_once()
        sys.exit(0 if success else 1)
    else:
        run_scheduler()
