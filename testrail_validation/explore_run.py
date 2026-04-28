"""
explore_run.py
--------------
Pulls a sample of raw data from a TestRail run so we can inspect which fields
are available before writing the final export script.

Usage (from the repo root, with venv activated):
    python testrail_validation/explore_run.py [RUN_ID]

Defaults to run R1077250 if no argument is given.

Requires a filled-in testrail_validation/.env file:
    TESTRAIL_URL=...
    TESTRAIL_USERNAME=...
    TESTRAIL_API_KEY=...
"""

import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# ── Load .env ──────────────────────────────────────────────────────────────────
ENV_FILE = Path(__file__).parent / ".env"
load_dotenv(ENV_FILE)

TESTRAIL_URL      = os.environ.get("TESTRAIL_URL", "").strip()
TESTRAIL_USERNAME  = os.environ.get("TESTRAIL_USERNAME", "").strip()
TESTRAIL_API_KEY  = os.environ.get("TESTRAIL_API_KEY", "").strip()

if not all([TESTRAIL_URL, TESTRAIL_USERNAME, TESTRAIL_API_KEY]):
    sys.exit(
        "ERROR: TESTRAIL_URL, TESTRAIL_USERNAME, and TESTRAIL_API_KEY "
        "must all be set in testrail_validation/.env"
    )

# ── TestRail client ────────────────────────────────────────────────────────────
# Re-use the project's existing API wrapper so we don't duplicate auth logic.
sys.path.insert(0, str(Path(__file__).parent.parent))
from libs.testrail.testrail_api import TestRailAPI

api = TestRailAPI(TESTRAIL_USERNAME, TESTRAIL_API_KEY, TESTRAIL_URL)

# ── Run ID ────────────────────────────────────────────────────────────────────
run_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1077250

print(f"\n{'='*60}")
print(f" Exploring TestRail run R{run_id}")
print(f"{'='*60}\n")

# ── 1. Run metadata ────────────────────────────────────────────────────────────
print("── get_run ──────────────────────────────────────────────────")
run = api.get_run(run_id)
print(json.dumps(run, indent=2))

# ── 2. Tests in the run (first page) ─────────────────────────────────────────
print("\n── get_tests (first 5 records shown) ───────────────────────")
tests_response = api.send_get(f"get_tests/{run_id}", params={"limit": 5, "offset": 0})
tests = tests_response.get("tests", tests_response) if isinstance(tests_response, dict) else tests_response

if isinstance(tests, list):
    sample = tests[:5]
else:
    sample = tests

print(json.dumps(sample, indent=2))

# ── 3. Results for those tests ────────────────────────────────────────────────
print("\n── get_results_for_run (first 5 records shown) ─────────────")
results_response = api.send_get(
    f"get_results_for_run/{run_id}",
    params={"limit": 5, "offset": 0}
)
results = results_response.get("results", results_response) if isinstance(results_response, dict) else results_response

if isinstance(results, list):
    result_sample = results[:5]
else:
    result_sample = results

print(json.dumps(result_sample, indent=2))

# ── 4. Single case — to expose custom fields ─────────────────────────────────
if isinstance(tests, list) and len(tests) > 0:
    first_case_id = tests[0].get("case_id")
    if first_case_id:
        print(f"\n── get_case (case_id={first_case_id}) — to inspect custom fields ─")
        case = api.get_case(first_case_id)
        print(json.dumps(case, indent=2))

print(f"\n{'='*60}")
print(" Field names collected above are the inputs for the final")
print(" export script.  Fill in .env and share the output so we")
print(" can confirm the exact custom-field key for automation status.")
print(f"{'='*60}\n")
