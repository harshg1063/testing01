"""
export_run_results.py
---------------------
Pulls all test results from a TestRail run and writes a CSV that can be
opened directly in Excel.

Columns exported:
  run_id, case_id, test_id, title, status, automation_status,
  comment, defects, test_url, case_url

Usage (from repo root, venv activated):
    python testrail_validation/export_run_results.py [RUN_ID]

Defaults to run 1077250 if no argument is given.
Output file: testrail_validation/run_<RUN_ID>_results.csv

Requires testrail_validation/.env:
    TESTRAIL_URL=...
    TESTRAIL_USERNAME=...
    TESTRAIL_API_KEY=...
"""

import csv
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from requests.exceptions import ChunkedEncodingError, ConnectionError

# ── Env ────────────────────────────────────────────────────────────────────────
ENV_FILE = Path(__file__).parent / ".env"
load_dotenv(ENV_FILE)

TESTRAIL_URL     = os.environ.get("TESTRAIL_URL", "").strip().rstrip("/")
TESTRAIL_USERNAME = os.environ.get("TESTRAIL_USERNAME", "").strip()
TESTRAIL_API_KEY = os.environ.get("TESTRAIL_API_KEY", "").strip()

if not all([TESTRAIL_URL, TESTRAIL_USERNAME, TESTRAIL_API_KEY]):
    sys.exit(
        "ERROR: TESTRAIL_URL, TESTRAIL_USERNAME, and TESTRAIL_API_KEY "
        "must all be set in testrail_validation/.env"
    )

sys.path.insert(0, str(Path(__file__).parent.parent))
from libs.testrail.testrail_api import TestRailAPI

api = TestRailAPI(TESTRAIL_USERNAME, TESTRAIL_API_KEY, TESTRAIL_URL)

RUN_ID = int(sys.argv[1]) if len(sys.argv) > 1 else 1077250
PAGE_SIZE = 100
MAX_RETRIES = 3
RETRY_DELAY = 3  # seconds

# ── Status label map (seeded with known defaults, extended from API) ───────────
STATUS_LABELS = {
    1: "Passed",
    2: "Blocked",
    3: "Untested",
    4: "Retest",
    5: "Failed",
    7: "Skipped",
}


def load_status_labels() -> None:
    """Extend STATUS_LABELS with any custom statuses defined in this TestRail instance."""
    try:
        statuses = api.send_get("get_statuses")
        if isinstance(statuses, list):
            for s in statuses:
                STATUS_LABELS.setdefault(s["id"], s.get("label", str(s["id"])))
    except Exception as exc:
        print(f"  Warning: could not load custom status labels ({exc})")


def paginate(endpoint: str, list_key: str, extra_params: dict = None) -> list:
    """Fetch all pages from a paginated TestRail endpoint with retry logic.

    TestRail v2 returns a dict with a '_links.next' key when more pages exist.
    We use that as the primary pagination signal to avoid infinite loops when
    the server ignores limit/offset parameters.
    """
    items = []
    offset = 0

    while True:
        params = {"limit": PAGE_SIZE, "offset": offset, **(extra_params or {})}

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = api.send_get(endpoint, params=params)
                break
            except (ChunkedEncodingError, ConnectionError) as exc:
                if attempt == MAX_RETRIES:
                    raise
                print(f"  Network error on attempt {attempt}/{MAX_RETRIES}, retrying in {RETRY_DELAY}s... ({exc})")
                time.sleep(RETRY_DELAY)

        if isinstance(response, dict):
            batch = response.get(list_key, [])
            # _links.next is the reliable "more pages" indicator in TestRail v2
            has_next = bool(response.get("_links", {}).get("next"))
        else:
            # Bare list — entire dataset returned at once
            batch = response
            has_next = False

        items.extend(batch)
        print(f"    ... fetched {len(items)} so far", end="\r")

        if not has_next:
            break
        offset += PAGE_SIZE

    print()  # newline after the \r progress line
    return items


def get_automation_status_labels() -> dict:
    """
    Returns a mapping of {option_id: label} for the custom_automation_statusess
    field by querying get_case_fields.  Falls back to an empty dict on error.
    """
    try:
        fields = api.send_get("get_case_fields")
        if not isinstance(fields, list):
            return {}
        for field in fields:
            if field.get("system_name") == "custom_automation_statusess":
                configs = field.get("configs", [])
                options = {}
                for cfg in configs:
                    for item in cfg.get("options", {}).get("items", "").splitlines():
                        item = item.strip()
                        if "," in item:
                            opt_id_str, label = item.split(",", 1)
                            try:
                                options[int(opt_id_str.strip())] = label.strip()
                            except ValueError:
                                pass
                return options
    except Exception as exc:
        print(f"  Warning: could not decode automation status labels ({exc})")
    return {}


def format_automation_status(ids: list, label_map: dict) -> str:
    if not ids:
        return ""
    return "; ".join(label_map.get(i, str(i)) for i in ids)


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    print(f"\nFetching run R{RUN_ID} from {TESTRAIL_URL} ...")

    # Run metadata (for the URL)
    run = api.get_run(RUN_ID)
    run_url = run.get("url", f"{TESTRAIL_URL}/index.php?/runs/view/{RUN_ID}")
    print(f"  Run: {run.get('name')}  |  {run_url}")

    # Status labels (includes custom statuses)
    print("  Fetching status definitions ...")
    load_status_labels()

    # Automation status label map
    print("  Fetching custom field definitions ...")
    auto_status_labels = get_automation_status_labels()
    if auto_status_labels:
        print(f"  Automation status options: {auto_status_labels}")
    else:
        print("  (Could not load automation status labels — raw IDs will be used)")

    # All tests in the run
    print("  Fetching tests (may take a moment for large runs) ...")
    tests = paginate(f"get_tests/{RUN_ID}", "tests")
    print(f"  → {len(tests)} tests retrieved")

    # All results for the run — we want the most recent result per test
    print("  Fetching results ...")
    results_raw = paginate(f"get_results_for_run/{RUN_ID}", "results")
    print(f"  → {len(results_raw)} result records retrieved")

    # Build latest-result lookup keyed by test_id
    # TestRail returns results newest-first, so first seen = most recent
    latest_result: dict = {}
    for r in results_raw:
        tid = r["test_id"]
        if tid not in latest_result:
            latest_result[tid] = r

    # ── Assemble rows ──────────────────────────────────────────────────────────
    rows = []
    for test in tests:
        test_id  = test["id"]
        case_id  = test["case_id"]
        status   = STATUS_LABELS.get(test["status_id"], str(test["status_id"]))
        auto_ids = test.get("custom_automation_statusess") or []
        auto_lbl = format_automation_status(auto_ids, auto_status_labels)

        result   = latest_result.get(test_id, {})
        comment  = (result.get("comment") or "").replace("\n", " ").replace("\r", "")
        defects  = result.get("defects") or ""

        test_url = f"{TESTRAIL_URL}/index.php?/tests/view/{test_id}"
        case_url = f"{TESTRAIL_URL}/index.php?/cases/view/{case_id}"

        rows.append({
            "run_id":             RUN_ID,
            "case_id":            case_id,
            "test_id":            test_id,
            "title":              test.get("title", ""),
            "status":             status,
            "automation_status":  auto_lbl,
            "comment":            comment,
            "defects":            defects,
            "test_url":           test_url,
            "case_url":           case_url,
        })

    # ── Write CSV ──────────────────────────────────────────────────────────────
    out_dir = Path(__file__).parent
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"run_{RUN_ID}_results_{timestamp}.csv"

    fieldnames = [
        "run_id", "case_id", "test_id", "title",
        "status", "automation_status",
        "comment", "defects",
        "test_url", "case_url",
    ]

    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nDone! {len(rows)} rows written to:\n  {out_path}\n")


if __name__ == "__main__":
    main()
