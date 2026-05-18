# ----------------------------------------------------------------------------------
# apply_agent.py
#
# Entry point for the automated Naukri job application agent.
#
# What this script does end to end:
#   1. Logs in to Naukri using credentials from the environment.
#   2. Searches for jobs across a curated set of keyword/location queries.
#   3. Deduplicates results and passes them through an AI scoring pipeline.
#   4. Iterates over jobs that passed the filter and applies to each one.
#   5. Handles questionnaires automatically using a static answer engine.
#   6. Skips jobs that redirect to an external company apply page.
#   7. Persists applied job IDs to a CSV so they are never applied to twice.
#   8. Prints a structured terminal summary at the end of each run.
#
# Dependencies:
#   - NaukriLoginClient   : handles login and session management
#   - NaukriJobClient     : wraps Naukri's internal job/apply APIs
#   - JobFilterPipeline2  : AI-based job relevance scorer
#   - colorama            : terminal color output
#
# Configuration:
#   Set USERNAME, PASSWORD, and OPEN_API_KEY in a .env file.
#   Adjust BQUERIES, EXPERIENCE_LEVELS, PAGES, and JOB_AGE inside
#   fetch_all_jobs() to tune what gets fetched each run.
# ----------------------------------------------------------------------------------

from src.client.naukri_client import NaukriLoginClient
from src.client.job_client import NaukriJobClient
from src.client.jop_classifier import JobFilterPipeline2
from src.exceptions.exceptions import NaukriAuthError, NaukriParseError
from dotenv import load_dotenv
from colorama import Fore, Back, Style, init
import os
import time
import csv
import logging
from datetime import datetime

load_dotenv()
init(autoreset=True)

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------------------
# Persistence — applied jobs CSV
#
# A flat CSV file is used as a lightweight store for applied job IDs. This
# prevents the agent from applying to the same job on subsequent runs.
# The file is appended to, never rewritten, so historical records are preserved.
# ----------------------------------------------------------------------------------

CSV_FILE = "applied_jobs.csv"


def load_applied_jobs() -> set:
    # Returns the set of job_ids already applied to in previous runs.
    # Returns an empty set if the file does not exist yet.
    if not os.path.exists(CSV_FILE):
        return set()
    with open(CSV_FILE, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return set(row["job_id"] for row in reader)


def save_applied_job(job) -> None:
    # Appends a single job record to the CSV after a successful apply.
    # Creates the file with a header row on first write.
    file_exists = os.path.exists(CSV_FILE)
    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        fieldnames = ["job_id", "title", "company", "applied_at"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            "job_id":     job.job_id,
            "title":      job.title,
            "company":    job.company,
            "applied_at": datetime.utcnow().isoformat(),
        })


# ----------------------------------------------------------------------------------
# Terminal display helpers
#
# All output is routed through these functions so the visual style stays
# consistent across the run. Nothing here affects business logic.
# ----------------------------------------------------------------------------------

LINE = f"{Fore.WHITE}{'─' * 68}{Style.RESET_ALL}"
THIN = f"{Fore.WHITE}{'·' * 68}{Style.RESET_ALL}"


def print_section_title(text: str) -> None:
    # Prints a bold titled section divider. Used to mark each major phase
    # of the run (login, fetch, filter, apply, summary).
    print(f"\n{LINE}")
    print(f"  {Fore.CYAN}{Style.BRIGHT}{text.upper()}{Style.RESET_ALL}")
    print(LINE)


def print_job_header(index: int, total: int, job, score=None, ai_detail=None) -> None:
    # Prints the full metadata block for a single job. Includes title, company,
    # job ID, URL, AI score with a visual bar, and skill tags if present.
    now = datetime.utcnow().strftime("%Y-%m-%d  %H:%M UTC")
    score_str = ""

    if score is not None:
        score_color = Fore.GREEN if score >= 70 else (Fore.YELLOW if score >= 50 else Fore.RED)
        score_bar   = _score_bar(score)
        score_str   = f"  {score_color}{score}/100{Style.RESET_ALL}  {score_bar}"

    print(f"\n{LINE}")
    print(
        f"  {Fore.CYAN}{Style.BRIGHT}JOB {index}/{total}{Style.RESET_ALL}"
        f"  {Fore.WHITE}{now}{Style.RESET_ALL}"
    )
    print(THIN)
    print(f"  {Fore.WHITE}Title   :{Style.RESET_ALL}  {Style.BRIGHT}{job.title}{Style.RESET_ALL}")
    print(f"  {Fore.WHITE}Company :{Style.RESET_ALL}  {Fore.YELLOW}{job.company}{Style.RESET_ALL}")
    print(f"  {Fore.WHITE}Job ID  :{Style.RESET_ALL}  {Fore.BLUE}{job.job_id}{Style.RESET_ALL}")
    print(f"  {Fore.WHITE}URL     :{Style.RESET_ALL}  {Fore.BLUE}https://www.naukri.com/job-listings-{job.job_id}{Style.RESET_ALL}")

    if score is not None:
        detail_text = f"  {Fore.WHITE}({ai_detail}){Style.RESET_ALL}" if ai_detail else ""
        print(f"  {Fore.WHITE}Score   :{Style.RESET_ALL}{score_str}{detail_text}")

    if job.tags:
        tag_str = "  ".join(f"{Fore.CYAN}[{t}]{Style.RESET_ALL}" for t in job.tags)
        print(f"  {Fore.WHITE}Tags    :{Style.RESET_ALL}  {tag_str}")


def _score_bar(score: int, width: int = 10) -> str:
    # Returns a small ASCII progress bar representing the AI score (0-100).
    # Color shifts from red to yellow to green as score increases.
    filled = int((score / 100) * width)
    bar    = "█" * filled + "░" * (width - filled)
    color  = Fore.GREEN if score >= 70 else (Fore.YELLOW if score >= 50 else Fore.RED)
    return f"{color}{bar}{Style.RESET_ALL}"


def print_status_applied(applied_at=None) -> None:
    ts = f"  {Fore.WHITE}at {applied_at}{Style.RESET_ALL}" if applied_at else ""
    print(f"  {Fore.GREEN}Status  :  Applied successfully{Style.RESET_ALL}{ts}")


def print_status_skipped_external() -> None:
    # External apply jobs cannot be submitted via the API. The URL is printed
    # in the job header so the user can open it manually if needed.
    print(f"  {Fore.YELLOW}Status  :  Skipped — external apply (open URL manually){Style.RESET_ALL}")


def print_status_failed(error) -> None:
    print(f"  {Fore.RED}Status  :  Failed — {error}{Style.RESET_ALL}")


def print_questionnaire_notice() -> None:
    print(f"  {Fore.CYAN}           Questionnaire detected, handling automatically{Style.RESET_ALL}")


def print_pipeline_results(final_jobs: list) -> None:
    # Prints a compact ranked table of every job that passed the AI filter,
    # sorted by score descending. Gives a quick overview before the apply loop.
    print_section_title(f"AI filter — {len(final_jobs)} jobs passed")
    col_w  = [4, 35, 28, 6]
    header = (
        f"  {Fore.WHITE}{'#':<{col_w[0]}}  "
        f"{'Title':<{col_w[1]}}  "
        f"{'Company':<{col_w[2]}}  "
        f"{'Score':>{col_w[3]}}{Style.RESET_ALL}"
    )
    print(header)
    print(f"  {Fore.WHITE}{'─' * sum(col_w)}{Style.RESET_ALL}")

    for i, job in enumerate(final_jobs, 1):
        score = job.get("score")
        score_color = (
            Fore.GREEN  if score and score >= 70 else
            Fore.YELLOW if score and score >= 50 else
            Fore.RED
        )
        score_display = f"{score_color}{score:>3}{Style.RESET_ALL}" if score is not None else "  ?"
        title   = (job.get("title")   or "")[:col_w[1]]
        company = (job.get("company") or "")[:col_w[2]]
        print(
            f"  {Fore.CYAN}{i:<{col_w[0]}}{Style.RESET_ALL}  "
            f"{title:<{col_w[1]}}  "
            f"{Fore.YELLOW}{company:<{col_w[2]}}{Style.RESET_ALL}  "
            f"{score_display}"
        )


def print_fetch_progress(keyword: str, location: str, exp: int, page: int, fetched: int, new: int) -> None:
    # Prints a single progress line per search query showing how many jobs
    # were returned and how many were new (not seen in earlier queries).
    loc        = location or "All India"
    kw_display = keyword[:30].ljust(30)
    loc_display = loc[:12].ljust(12)
    new_color  = Fore.GREEN if new > 0 else Fore.WHITE
    print(
        f"  {Fore.WHITE}[{kw_display} | {loc_display} | exp={exp} | p{page}]{Style.RESET_ALL}"
        f"  {Fore.WHITE}{fetched:>3} fetched  "
        f"{new_color}{new:>3} new{Style.RESET_ALL}"
    )


def print_summary(total_found: int, total_allowed: int, applied: int, skipped_ext: int, failed: int) -> None:
    # Prints the final run summary table. Called once at the end of the script.
    print_section_title("run summary")
    rows = [
        ("Jobs fetched (total unique)", str(total_found),   Fore.WHITE),
        ("Jobs passed AI filter",       str(total_allowed), Fore.CYAN),
        ("Applied successfully",        str(applied),       Fore.GREEN),
        ("Skipped (external apply)",    str(skipped_ext),   Fore.YELLOW),
        ("Failed",                      str(failed),        Fore.RED),
    ]
    for label, value, color in rows:
        print(f"  {Fore.WHITE}{label:<30}{Style.RESET_ALL}  {color}{Style.BRIGHT}{value}{Style.RESET_ALL}")
    print(LINE + "\n")


# ----------------------------------------------------------------------------------
# Job fetching
#
# Runs a fixed set of search queries against the Naukri search API and
# collects results into a deduplicated list.
#
# Design decisions:
#   - Queries are hand-curated for the target stack (Node.js, Python, backend).
#   - Only Bangalore and Pune are targeted — highest product/startup density.
#   - Experience is fixed at 2 years. exp=3 pulled in too many senior roles.
#   - job_age=2 keeps results fresh, which improves apply response rates.
#   - 1 page per query. Quality drops sharply beyond page 2 on Naukri.
#   - 1.2s sleep between requests to avoid rate limiting.
#   - Deduplication is done by job_id across all queries before returning.
# ----------------------------------------------------------------------------------

def fetch_all_jobs(jc: NaukriJobClient) -> list:

    BQUERIES = [
        # Tier 1: exact stack match
        {"keyword": "Node.js backend developer", "location": "Bangalore"},
        {"keyword": "Python Developer",          "location": ""},
        {"keyword": "Node.js Developer",         "location": ""},
        {"keyword": "python backend developer",  "location": "Pune"},
    ]

    EXPERIENCE_LEVELS = [2]
    PAGES   = 1
    JOB_AGE = 2

    seen_ids = set()
    all_jobs = []

    print_section_title(
        f"fetching jobs  ({len(BQUERIES)} queries x {len(EXPERIENCE_LEVELS)} exp x {PAGES} page)"
    )

    for q in BQUERIES:
        for exp in EXPERIENCE_LEVELS:
            for page in range(1, PAGES + 1):
                try:
                    jobs = jc.search_jobs(
                        keyword=q["keyword"],
                        location=q["location"],
                        experience=exp,
                        job_age=JOB_AGE,
                        page=page,
                    )

                    # Deduplicate across queries using job_id.
                    new_jobs = []
                    for job in jobs:
                        job_id = getattr(job, "id", None) or getattr(job, "job_id", None)
                        if job_id and job_id not in seen_ids:
                            seen_ids.add(job_id)
                            new_jobs.append(job)

                    all_jobs.extend(new_jobs)
                    print_fetch_progress(
                        q["keyword"], q["location"], exp, page,
                        fetched=len(jobs),
                        new=len(new_jobs),
                    )

                    if len(jobs) == 0:
                        break

                    time.sleep(1.2)

                except Exception as e:
                    print(
                        f"  {Fore.RED}[FAIL]{Style.RESET_ALL}  "
                        f"{q['keyword']} @ {q['location']}  "
                        f"exp={exp} p={page}  ->  {e}"
                    )
                    time.sleep(3)

    print(f"\n  {Fore.CYAN}Total unique jobs collected: {Style.BRIGHT}{len(all_jobs)}{Style.RESET_ALL}")
    return all_jobs


# ----------------------------------------------------------------------------------
# Main — orchestrates the full agent run
# ----------------------------------------------------------------------------------

if __name__ == "__main__":

    username = os.getenv("USERNAME")
    password = os.getenv("PASSWORD")
    ai_key   = os.getenv("OPEN_API_KEY")

    # Step 1: authenticate and establish session.
    print_section_title("logging in to naukri")
    client = NaukriLoginClient(username, password)
    client.login()
    print(f"  {Fore.GREEN}Logged in as {Fore.YELLOW}{username}{Style.RESET_ALL}")

    # Step 2: fetch raw jobs from search API.
    jc   = NaukriJobClient(client)
    jobs = fetch_all_jobs(jc)

    if not jobs:
        print(f"\n{Fore.YELLOW}  No jobs found. Exiting.{Style.RESET_ALL}")
        exit(0)

    # Step 3: run AI filter pipeline. Jobs are scored and ranked. Only those
    # above the pipeline's threshold are passed to the apply loop.
    print_section_title("running AI filter pipeline")
    pipeline   = JobFilterPipeline2(openai_api_key=ai_key)
    final_jobs = pipeline.run(jobs)

    # Build a lookup from job_id to the pipeline result dict (score, ai_detail, etc.)
    score_map    = {j["job_id"]: j for j in final_jobs}
    allow        = set(score_map.keys())

    print_pipeline_results(final_jobs)

    # Step 4: apply loop. Iterates only over jobs that passed the AI filter.
    applied_jobs_set = load_applied_jobs()

    applied_count = 0
    skipped_ext   = 0
    failed_count  = 0

    allowed_jobs = [j for j in jobs if j.job_id in allow]
    print_section_title(f"applying to {len(allowed_jobs)} filtered jobs")

    for index, job in enumerate(allowed_jobs, start=1):
        meta      = score_map.get(job.job_id, {})
        score     = meta.get("score")
        ai_detail = meta.get("ai_detail")

        print_job_header(
            index=index,
            total=len(allowed_jobs),
            job=job,
            score=score,
            ai_detail=ai_detail,
        )

        # External apply jobs cannot be submitted via the API, skip them.
        if jc.is_external_apply(job.job_id):
            print_status_skipped_external()
            skipped_ext += 1
            continue

        # Use the first two tags as mandatory skills and the rest as optional.
        # This maps the job's skill tags to the apply payload fields.
        mandatory = job.tags[:2] if job.tags else []
        optional  = job.tags[2:] if len(job.tags) > 2 else []

        try:
            result   = jc.apply_job(
                job,
                mandatory_skills=mandatory,
                optional_skills=optional,
                source="search",
            )

            job_result = (result.get("jobs") or [{}])[0]

            # If the apply response contains a questionnaire, answer it and
            # re-submit. This is a two-step apply flow used by some employers.
            if job_result.get("questionnaire"):
                print_questionnaire_notice()
                sid    = datetime.utcnow().strftime("%Y%m%d%H%M%S") + "0000000"
                result = jc.handle_static_questionnaire_and_apply(
                    job,
                    questionnaire=job_result["questionnaire"],
                    sid=sid,
                    mandatory_skills=mandatory,
                    optional_skills=optional,
                    source="search",
                )

            applied_at = datetime.utcnow().strftime("%H:%M:%S UTC")
            print_status_applied(applied_at)
            save_applied_job(job)
            applied_jobs_set.add(job.job_id)
            applied_count += 1

        except Exception as e:
            print_status_failed(e)
            failed_count += 1

        # Delay between applies to avoid triggering rate limits.
        time.sleep(3)

    # Step 5: print final run summary.
    print_summary(
        total_found=len(jobs),
        total_allowed=len(allowed_jobs),
        applied=applied_count,
        skipped_ext=skipped_ext,
        failed=failed_count,
    )