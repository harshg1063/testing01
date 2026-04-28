import argparse
import base64
import glob
import io
import os
import smtplib
import sys
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from xml.etree import ElementTree
from collections import Counter

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import html

MAX_ERROR_MESSAGE_LENGTH = 300
MAX_FAILURES_TO_SHOW = 25
DEFAULT_RECIPIENTS = ["ASQE-PS-AutomationResults@external.groups.hp.com"]

def _get_direct_child(elem, *names: str):
    """
    Return the first direct child whose tag exactly matches one of `names`.
    Matches your current JUnit XML:
        <testcase> <failure>...</failure> </testcase>
    """
    for child in list(elem):
        if isinstance(child.tag, str) and child.tag in names:
            return child
    return None


def _get_testrail_ids_from_testcase(testcase) -> str:
    """
    Extract TestRail case IDs from <property name="testrail_case_id" ...> under this testcase.
    Returns a comma-separated string or "" if not present.
    """
    ids: list[str] = []
    for props in testcase.findall("properties"):
        for prop in props.findall("property"):
            if prop.get("name") == "testrail_case_id":
                value = prop.get("value")
                if value and value not in ids:
                    ids.append(value)
    return ", ".join(ids)

def _escape_html(text: str) -> str:
    """
    Safely escape text for insertion into HTML content.

    Uses html.escape to handle &, <, > and (optionally) quotes.
    """
    if text is None:
        return ""
    return html.escape(str(text), quote=False)

def _get_module_from_testcase(testcase) -> str:
    """
    Derive a logical module name from the JUnit classname.

    Example:
      classname="tests.hp_app.smart_experience.test_smart_experience_common_02.Test_Suite_Smart_Experience"
      -> parts = ["tests","hp_app","smart_experience",...]
      -> module = "smart_experience" (3rd segment, index 2)

    If classname is missing or too short, returns "Unknown".
    """
    classname = testcase.get("classname") or ""
    parts = classname.split(".")
    if len(parts) >= 3:
        return parts[2]
    return "Unknown"


# -------------------- PARSE TEST RESULTS --------------------
def parse_test_results(path):
    # Handle both file and directory inputs
    if os.path.isfile(path):
        xml_files = [path]
    elif os.path.isdir(path):
        xml_files = glob.glob(os.path.join(path, "**", "*.xml"), recursive=True)
    else:
        xml_files = []

    suites: dict[str, dict] = {}
    totals = {
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "total": 0,
        "execution_time": 0.0,
        "others": 0,
    }
    # per-module aggregates
    module_totals: dict[str, dict[str, int]] = {}


    for xml_file in xml_files:
        try:
            # FILE VERIFICATION
            file_stat = os.stat(xml_file)
            file_size = file_stat.st_size
            mod_time = datetime.fromtimestamp(file_stat.st_mtime).strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            root = ElementTree.parse(xml_file).getroot()

            # COUNT ALL FAILURES / ERRORS IN THE XML BEFORE PARSING
            all_failures = root.findall(".//failure")
            all_errors = root.findall(".//error")


            suite_nodes = (
                root.findall(".//testsuite")
                if root.tag == "testsuites"
                else [root]
                if root.tag == "testsuite"
                else root.findall(".//testsuite")
            )


            for suite_node in suite_nodes:
                suite_name = suite_node.get("name") or os.path.basename(xml_file)

                if suite_name not in suites:
                    suites[suite_name] = {
                        "name": suite_name,
                        "passed": 0,
                        "failed": 0,
                        "skipped": 0,
                        "total": 0,
                        "failed_tests": [],
                        "skipped_tests": [],
                        "execution_time": 0.0,
                    }
                suite_time = float(suite_node.get("time", 0))
                suites[suite_name]["execution_time"] += suite_time
                totals["execution_time"] += suite_time

                testcases = suite_node.findall(".//testcase")
                print(
                    f"DEBUG: Suite '{suite_name}' has {len(testcases)} testcases",
                    file=sys.stderr,
                )

                # Actual counting + module aggregation
                for testcase in testcases:
                    test_name = testcase.get("name", "")
                    failure = _get_direct_child(testcase, "failure", "error")
                    skipped = _get_direct_child(testcase, "skipped")
                    module_name = _get_module_from_testcase(testcase)

                    # Ensure module bucket exists
                    mt = module_totals.setdefault(
                        module_name,
                        {
                            "total": 0,
                            "passed": 0,
                            "failed": 0,
                            "skipped": 0,
                        },
                    )

                    if failure is not None:
                        msg = failure.get("message") or ""
                        if not msg and failure.text:
                            msg = failure.text
                        msg = str(msg)[:MAX_ERROR_MESSAGE_LENGTH]

                        testrail_ids = _get_testrail_ids_from_testcase(testcase)

                        suites[suite_name]["failed"] += 1
                        suites[suite_name]["failed_tests"].append(
                            {
                                "name": test_name,
                                "msg": msg,
                                "testrail_ids": testrail_ids,
                                "module": module_name,
                            }
                        )
                        totals["failed"] += 1

                        mt["failed"] += 1
                        print(
                            f"DEBUG: ✓ FAILED test detected: {test_name} (module={module_name})",
                            file=sys.stderr,
                        )

                    elif skipped is not None:
                        skip_reason = skipped.get("message") or "No reason provided"

                        suites[suite_name]["skipped"] += 1
                        suites[suite_name]["skipped_tests"].append(
                            {
                                "name": test_name,
                                "reason": skip_reason,
                                "module": module_name,
                            }
                        )
                        totals["skipped"] += 1
                        mt["skipped"] += 1

                    else:
                        suites[suite_name]["passed"] += 1
                        totals["passed"] += 1
                        mt["passed"] += 1

                    suites[suite_name]["total"] += 1
                    totals["total"] += 1
                    mt["total"] += 1

        except Exception as e:
            print(f"Warning: failed parsing {xml_file}: {e}", file=sys.stderr)
            import traceback

            traceback.print_exc(file=sys.stderr)

    print("DEBUG: ========================================", file=sys.stderr)
    print(
        f"DEBUG: TOTALS - Passed: {totals['passed']}, "
        f"Failed: {totals['failed']}, Skipped: {totals['skipped']}, Total: {totals['total']}",
        file=sys.stderr,
    )

    failed_suites_debug = [
        (
            s["name"],
            s["failed"],
            len(s["failed_tests"]),
            [ft["name"] for ft in s["failed_tests"]],
        )
        for s in suites.values()
        if s["failed"] > 0
    ]


    totals["others"] = max(
        0, totals["total"] - (totals["passed"] + totals["failed"] + totals["skipped"])
    )
    # return module_totals as third value
    return list(suites.values()), totals, module_totals


# -------------------- BASELINE RESULTS --------------------
def parse_baseline(path):
    if not path or not os.path.isdir(path):
        return None
    try:
        _, totals, _ = parse_test_results(path)
        return totals
    except Exception:
        return None


# -------------------- PIE CHART --------------------
def generate_pie_chart(passed, failed, skipped, others):
    total = passed + failed + skipped + others
    if total == 0:
        return ""
    sizes = [passed, failed, skipped, others]
    colors = ["#4CAF50", "#FF6B6B", "#FFC107", "#D3D3D3"]
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.pie(
        sizes,
        colors=colors,
        startangle=90,
        autopct="%1.1f%%",
        textprops={"fontsize": 10},
    )
    ax.set_title("Test Results")
    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight")
    img = base64.b64encode(buf.getvalue()).decode()
    plt.close()
    return (
        f'<img src="data:image/png;base64,{img}" width="300" height="300" '
        f'style="display:block; border:0;" />'
    )


def _format_execution_time(seconds: float) -> str:
    """Format seconds into 'Xh Ym Zs', 'Xm Ys', or 'Xs'."""
    total_seconds = int(seconds)
    hours, rem = divmod(total_seconds, 3600)
    minutes, secs = divmod(rem, 60)

    parts = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    # Always show seconds if there is no other part, or if secs > 0
    if secs or not parts:
        parts.append(f"{secs}s")
    return " ".join(parts)

def _build_unique_errors_section(suites):
    """
    Build a summary of unique error messages with their counts.
    Returns HTML table showing error message and count of occurrences.
    """
    # Collect all error messages from all failed tests
    error_messages = []
    for suite in suites:
        if suite["failed"] > 0:
            for ft in suite.get("failed_tests", []):
                msg = ft.get("msg", "").strip()
                if msg:
                    error_messages.append(msg)

    if not error_messages:
        return ""

    # Count unique error messages
    error_counter = Counter(error_messages)

    # Sort by count (most frequent first)
    sorted_errors = sorted(error_counter.items(), key=lambda x: x[1], reverse=True)

    # Build HTML rows for unique errors
    error_rows = ""
    for error_msg, count in sorted_errors:
        safe_msg = _escape_html(error_msg)
        error_rows += f"""
        <tr>
            <td style="padding:8px 10px; border:1px solid #ccc; font-size:12px; text-align:center;">
                {count}
            </td>
            <td style="padding:8px 10px; border:1px solid #ccc; font-size:12px; color:#FF6B6B;">
                {safe_msg}
            </td>
        </tr>"""

    unique_error_section = f"""
    <h3 style="color:#FF6B6B; margin-top:24px;">Unique Errors ({len(sorted_errors)} unique)</h3>

    <table style="border-collapse:collapse; width:100%; font-family:Arial,sans-serif; font-size:12px;">
        <thead>
            <tr style="background-color:#FF6B6B; color:white;">
                <th style="padding:8px 10px; border:1px solid #ccc; text-align:center; width:80px;">Count</th>
                <th style="padding:8px 10px; border:1px solid #ccc; text-align:left;">Error Message</th>
            </tr>
        </thead>
        <tbody>
            {error_rows}
        </tbody>
    </table>
    """

    return unique_error_section

def _build_skipped_tests_section(suites):
    """
    Build a summary of skipped tests with their reasons.
    Returns HTML table showing skipped test name, module, and skip reason.
    """
    # Collect all skipped tests from all suites
    all_skipped_tests = []
    for suite in sorted(suites, key=lambda s: s["name"]):
        if suite["skipped"] > 0:
            for st in suite.get("skipped_tests", []):
                module_name = st.get("module") or "Unknown"
                all_skipped_tests.append((module_name, st))

    if not all_skipped_tests:
        return ""

    total_skipped = len(all_skipped_tests)

    # Count unique skip reasons
    skip_reasons = {}
    for _, st in all_skipped_tests:
        reason = st.get("reason", "No reason provided").strip()
        skip_reasons[reason] = skip_reasons.get(reason, 0) + 1

    # Build HTML rows for skipped tests
    skipped_rows = ""
    for module_name, st in all_skipped_tests:
        test_name = st.get("name", "Unknown")
        reason = st.get("reason", "No reason provided")

        safe_module = _escape_html(module_name)
        safe_test_name = _escape_html(test_name)
        safe_reason = _escape_html(reason)

        skipped_rows += f"""
        <tr>
            <td style="padding:8px 10px; border:1px solid #ccc; font-size:12px;">
                {safe_module}
            </td>
            <td style="padding:8px 10px; border:1px solid #ccc; font-size:12px;">
                {safe_test_name}
            </td>
            <td style="padding:8px 10px; border:1px solid #ccc; font-size:12px; color:#FFC107;">
                {safe_reason}
            </td>
        </tr>"""

    skipped_section = f"""
    <h3 style="color:#FFC107; margin-top:24px;">Skipped Tests ({total_skipped} total)</h3>

    <p style="margin: 10px 0; font-size: 13px;">
        <strong>Skip Reason Summary:</strong><br>"""

    for reason, count in sorted(skip_reasons.items(), key=lambda x: x[1], reverse=True):
        safe_reason = _escape_html(reason)
        skipped_section += f"        {count}× {safe_reason}<br>\n"

    skipped_section += f"""    </p>

    <table style="border-collapse:collapse; width:100%; font-family:Arial,sans-serif; font-size:12px;">
        <thead>
            <tr style="background-color:#FFC107; color:black;">
                <th style="padding:8px 10px; border:1px solid #ccc; text-align:left;">Module</th>
                <th style="padding:8px 10px; border:1px solid #ccc; text-align:left;">Test</th>
                <th style="padding:8px 10px; border:1px solid #ccc; text-align:left;">Skip Reason</th>
            </tr>
        </thead>
        <tbody>
            {skipped_rows}
        </tbody>
    </table>
    """

    return skipped_section

# -------------------- BUILD HTML --------------------
def build_html(suites, totals, module_totals, name, url, date, baseline):
    pass_rate = (totals["passed"] / totals["total"] * 100) if totals["total"] else 0
    execution_time_str = _format_execution_time(totals["execution_time"])

    # Original dynamic header logic (COMMENTED OUT for now):
    # status_color = "#2e7d32" if totals["failed"] == 0 else "#c62828"

    # Static header color for now. When ready to switch back to dynamic, use status_color above.
    header_color = "#333333"

    # Failure breakdown (existing vs new)
    existing = 0
    new = totals["failed"]
    if baseline:
        existing = min(baseline.get("failed", 0), totals["failed"])
        new = totals["failed"] - existing

    pie_chart_html = generate_pie_chart(
        totals["passed"], totals["failed"], totals["skipped"], totals["others"]
    )

    # Build unique errors section
    unique_errors_section = _build_unique_errors_section(suites)

    # Build skipped tests section
    skipped_tests_section = _build_skipped_tests_section(suites)

    # Failures section (old individual failures view - now optional/supplementary)
    failures_section = ""
    if totals["failed"] > 0:
        total_failed = totals["failed"]

        failure_breakdown = f"""
        <p style="margin: 10px 0; font-size: 13px;">
            <strong>Failure Breakdown:</strong>
            Existing: <span style="color: #FF9800;">{existing}</span>
            | New: <span style="color: #FF6B6B;">{new}</span>
        </p>"""

        failure_rows = ""
        note_html = ""

        # Flatten all failed tests into a list of (module_name, failed_test_dict)
        all_failed_tests = []
        for suite in sorted(suites, key=lambda s: s["name"]):
            if suite["failed"] > 0:
                for ft in suite.get("failed_tests", []):
                    module_name = ft.get("module") or "Unknown"
                    all_failed_tests.append((module_name, ft))

        if total_failed <= MAX_FAILURES_TO_SHOW:
            to_show = all_failed_tests
        else:
            to_show = all_failed_tests[:MAX_FAILURES_TO_SHOW]
            note_html = f"""
            <p style="color:#666; font-size:12px; background-color:#f5f5f5; padding:10px;
                      border-left:4px solid #FF6B6B; margin-top:10px;">
                Showing first {MAX_FAILURES_TO_SHOW} of {total_failed} individual test failures.
                See "Unique Errors" section above for error pattern summary.
            </p>
            """

        for module_name, ft in to_show:
            test_name = ft.get("name", "Unknown")
            msg = ft.get("msg", "")
            testrail_ids = ft.get("testrail_ids") or "-"

            # Escape all user-controlled values for safe HTML insertion
            safe_module = _escape_html(module_name)
            safe_test_name = _escape_html(test_name)
            safe_testrail_ids = _escape_html(testrail_ids)
            # Escape and sanitize message: escape HTML, then truncate to first line and max length
            safe_msg = _escape_html(msg)
            safe_msg = safe_msg.split("\n")[0][:300]

            failure_rows += f"""
            <tr>
                <td style="padding:8px 10px; border:1px solid #ccc; font-size:12px;">
                    {safe_module}
                </td>
                <td style="padding:8px 10px; border:1px solid #ccc; font-size:12px;">
                    {safe_test_name}
                </td>
                <td style="padding:8px 10px; border:1px solid #ccc; font-size:12px;">
                    {safe_testrail_ids}
                </td>
                <td style="padding:8px 10px; border:1px solid #ccc; color:#FF6B6B; font-size:11px;">
                    {safe_msg}
                </td>
            </tr>"""
        
        #If we ever have to add the all failed tests to the email, uncomment these lines
        # failures_section = f"""
        # <h3 style="color:#FF6B6B; margin-top:24px;">Individual Failed Tests ({total_failed} total)</h3>
        # {failure_breakdown}
        # 
        # <table style="border-collapse:collapse; width:100%; font-family:Arial,sans-serif; font-size:12px;">
        #     <thead>
        #         <tr style="background-color:#FF6B6B; color:white;">
        #             <th style="padding:8px 10px; border:1px solid #ccc; text-align:left;">Module</th>
        #             <th style="padding:8px 10px; border:1px solid #ccc; text-align:left;">Test</th>
        #             <th style="padding:8px 10px; border:1px solid #ccc; text-align:left;">TestRail ID</th>
        #             <th style="padding:8px 10px; border:1px solid #ccc; text-align:left;">Failure Message</th>
        #         </tr>
        #     </thead>
        #     <tbody>
        #         {
        # failure_rows
        # if failure_rows
        # else '<tr><td colspan="4">No failure details found</td></tr>'
        # }
        #     </tbody>
        # </table>
        # {note_html}
        # """

    # Build module summary rows from accurate module_totals
    module_rows = ""
    for module_name in sorted(module_totals.keys()):
        mt = module_totals[module_name]
        module_rows += f"""
        <tr>
            <td>{module_name}</td>
            <td align="center">{mt['total']}</td>
            <td align="center" style="color:#2e7d32;"><b>{mt['passed']}</b></td>
            <td align="center" style="color:#c62828;"><b>{mt['failed']}</b></td>
            <td align="center" style="color:#f9a825;"><b>{mt['skipped']}</b></td>
        </tr>
        """

    # HTML wrapper
    html = f"""
    <html>
    <body style="margin:0; padding:0; background-color:#f4f6f8; font-family:Arial, sans-serif;">

    <table width="100%" cellpadding="0" cellspacing="0" border="0">
      <tr>
        <td align="center">

          <table width="800" cellpadding="0" cellspacing="0" border="0"
                 style="background:#ffffff; border:1px solid #ddd;">

            <tr>
              <td style="background:{header_color}; color:white; padding:14px;
                         font-size:18px; font-weight:bold;">
                {name}
              </td>
            </tr>

            <tr>
              <td style="padding:10px 14px; font-size:16px; color:#555;">
                {date} |
                <a href="{url}" style="color:#0078D4; text-decoration:none;">View Pipeline</a>
              </td>
            </tr>

            <tr>
              <td style="padding:14px;">
                <table width="100%" cellpadding="6" cellspacing="0" border="0">
                  <tr>
                    <td align="center" bgcolor="#f4f6f8">
                      <b>Total</b><br>{totals['total']}
                    </td>
                    <td align="center" bgcolor="#e6f4ea">
                      <b style="color:#2e7d32;">Passed</b><br>{totals['passed']}
                    </td>
                    <td align="center" bgcolor="#fdecea">
                      <b style="color:#c62828;">Failed</b><br>{totals['failed']}
                    </td>
                    <td align="center" bgcolor="#fff8e1">
                      <b style="color:#f9a825;">Skipped</b><br>{totals['skipped']}
                    </td>
                  </tr>
                </table>

                <table width="100%" cellpadding="0" cellspacing="0" border="0"
                       style="margin-top:10px;">
                  <tr>
                    <td style="background:#ddd; height:10px;">
                      <table width="{pass_rate}%" cellpadding="0" cellspacing="0" border="0">
                        <tr>
                          <td style="background:#4CAF50; height:10px;"></td>
                        </tr>
                      </table>
                    </td>
                  </tr>
                </table>

                <p style="font-size:16px; margin-top:8px;">
                  <span style="font-weight:bold;">Pass Rate:</span>
                  <b>{pass_rate:.1f}%</b>
                  &nbsp;|&nbsp;
                  <span style="font-weight:bold;">Execution Time:</span>
                  <b>{execution_time_str}</b>
                </p>
              </td>
            </tr>

            <tr>
              <td align="center" style="padding:10px;">
                {pie_chart_html}
              </td>
            </tr>

            <tr>
              <td style="padding:14px;">
                <h3 style="margin-bottom:8px;">Results by Module</h3>

                <table width="100%" cellpadding="6" cellspacing="0" border="1"
                       style="border:1px solid #ddd;">
                  <tr style="background-color:#424242; color:white; font-weight:bold;">
                    <th align="left" style="padding:8px 10px; border:1px solid #ccc;">Module</th>
                    <th align="center" style="padding:8px 10px; border:1px solid #ccc;">Total</th>
                    <th align="center" style="padding:8px 10px; border:1px solid #ccc;">Passed</th>
                    <th align="center" style="padding:8px 10px; border:1px solid #ccc;">Failed</th>
                    <th align="center" style="padding:8px 10px; border:1px solid #ccc;">Skipped</th>
                  </tr>
                  {module_rows}
                </table>
              </td>
            </tr>

            <tr>
              <td style="padding:14px;">
                {unique_errors_section}
              </td>
            </tr>

            <tr>
              <td style="padding:14px;">
                {skipped_tests_section}
              </td>
            </tr>

          </table>

        </td>
      </tr>
    </table>

    </body>
    </html>
    """

    return html

# Add these lines to the above HTML if we need to insert the list of failed tests in the email anytime
# <tr>
#   <td style = "padding:14px;">
#       {failures_section}
#   </td >
# </tr >


# -------------------- SEND EMAIL --------------------
def send_email(to, subject, html, smtp, port, sender):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    # Display name + email
    msg["From"] = f"ASQE-TITAN-REPO <{sender}>"
    msg["To"] = ",".join(to)
    msg.attach(MIMEText(html, "html"))
    with smtplib.SMTP(smtp, port) as server:
        server.sendmail(sender, to, msg.as_string())


# -------------------- MAIN --------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-results-path", required=True)
    parser.add_argument("--pipeline-name", default="Test Run")
    parser.add_argument("--build-url", default="")
    parser.add_argument("--baseline-results-path", default="")
    parser.add_argument("--smtp-server", default="smtp3.hp.com")
    parser.add_argument("--smtp-port", type=int, default=25)
    parser.add_argument("--sender", default="asqe-titan-noreply@hp.com")
    parser.add_argument("--recipients", help="Comma-separated email addresses to send the report to. If provided, overrides the DEFAULT_RECIPIENTS distribution list." , default=None,)
    args = parser.parse_args()

    suites, totals, module_totals = parse_test_results(args.test_results_path)
    if totals["total"] == 0:
        print("No test results found.")
        return

    baseline = parse_baseline(args.baseline_results_path)
    date_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    html = build_html(
        suites,
        totals,
        module_totals,
        args.pipeline_name,
        args.build_url,
        date_time,
        baseline,
    )
    # Build subject line with status prefix and timestamp, e.g.:
    # [FAILED] My Pipeline: 10/12 Passed (2026-03-23 10:15 UTC)
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    status_label = "[FAILED]" if totals["failed"] > 0 else "[PASSED]"
    pass_rate = (totals["passed"] / totals["total"] * 100) if totals["total"] else 0.0

    subject = (
        f"{status_label} {args.pipeline_name} - "
        f"{totals['passed']}/{totals['total']} Passed ({pass_rate:.1f}%) - {date}"
    )

    # Determine recipients (precedence: --recipients > JSON config).
    if args.recipients:
        recipients = [email.strip() for email in args.recipients.split(",") if email.strip()]
    else:
        recipients = DEFAULT_RECIPIENTS

    send_email(recipients, subject, html, args.smtp_server, args.smtp_port, args.sender)


if __name__ == "__main__":
    main()