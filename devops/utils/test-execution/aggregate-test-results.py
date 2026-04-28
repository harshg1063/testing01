"""
Test Result Aggregation Script

Purpose: Aggregates pytest test results from multiple platform/device executions
into a single set of TestRail results with consolidated comments showing all
platform combinations.

Flow:
1. Download all test result XML files from pipeline artifacts
2. Parse JUnit XML results and group by test case ID
3. Aggregate outcomes (failed if any platform failed, passed if all passed, skipped if all skipped)
4. Build consolidated comments listing all platform × device combinations with their outcomes
5. Upload aggregated results to TestRail

Usage:
    python aggregate-test-results.py --artifact-dir <path> [--testrail-run-id <id>] [--testrail-milestone-id <id>] [--run-name <name>] [--version <version>]
"""

import argparse
import json
import logging
import os
import sys
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple
from xml.etree import ElementTree as ET

# Add repository root to path for imports
repo_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(repo_root))

from libs.testrail.testrail_api import TestRailAPI, TestStatus


class TestResult:
    """Represents a single test execution result."""
    def __init__(self, case_id: str, platform: str, device: str, status: str, 
                 duration: float, failure_msg: str = None, nodeid: str = None, teamviewer_id: str = None):
        self.case_id = case_id
        self.platform = platform
        self.device = device
        self.status = status  # 'passed', 'failed', 'skipped', 'error'
        self.duration = duration
        self.failure_msg = failure_msg
        self.nodeid = nodeid
        self.teamviewer_id = teamviewer_id


class AggregatedResult:
    """Represents aggregated results for a test case across platforms."""
    def __init__(self, case_id: str, suite_id: str = None):
        self.case_id = case_id
        self.suite_id = suite_id
        self.results: List[TestResult] = []
        self.nodeid = None
    
    def add_result(self, result: TestResult):
        """Add a platform execution result."""
        self.results.append(result)
        if not self.nodeid:
            self.nodeid = result.nodeid
    
    def get_overall_status(self) -> str:
        """
        Determine overall TestRail status across all platform/device executions.

        Rules:
          - No results OR every result is error/skipped (test body never ran) → 'never_executed'
            → TestRail status left as Untested; comment still recorded for visibility.
          - Some devices ran (passed/failed), others errored (fixture/device failure)  → 'partial'
            → Retest: partial execution, needs a re-run.
          - At least one assertion failure among the results that actually ran          → 'failed'
            → Failed: genuine functional regression.
          - All results that ran passed                                                 → 'passed'
            → Passed.
        """
        if not self.results:
            return 'never_executed'

        statuses = {r.status for r in self.results}
        ran_statuses = statuses - {'error', 'skipped'}  # statuses where test body actually executed

        if not ran_statuses:
            # Test body never executed on any device — treat as never run
            return 'never_executed'

        if 'error' in statuses:
            # Some devices ran, some had fixture/setup failures — partial execution
            return 'partial'

        if 'failed' in ran_statuses:
            return 'failed'

        return 'passed'
    
    def get_total_duration(self) -> float:
        """Sum of all execution durations."""
        return sum(r.duration for r in self.results)
    
    def build_comment(self, build_url: str = None) -> str:
        """Build consolidated comment showing all platform combinations."""
        comment_parts = []

        # Add test identifier
        if self.nodeid:
            comment_parts.append(f"Test: {self.nodeid}")

        passed  = [r for r in self.results if r.status == 'passed']
        failed  = [r for r in self.results if r.status == 'failed']
        errored = [r for r in self.results if r.status == 'error']
        skipped = [r for r in self.results if r.status == 'skipped']

        total = len(self.results)
        ran   = len(passed) + len(failed)

        # ── Targeted platforms ────────────────────────────────────────────────
        comment_parts.append("\n=== Targeted Platforms ===")
        comment_parts.append(f"Total: {total} platform/device combination(s)")
        for r in self.results:
            platform_device = f"{r.platform} × {r.device}" if r.device and r.device != 'none' else r.platform
            comment_parts.append(f"  • {platform_device}")

        # ── Execution summary ─────────────────────────────────────────────────
        comment_parts.append("\n=== Execution Summary ===")
        comment_parts.append(f"Ran: {ran} | Passed: {len(passed)} | Failed: {len(failed)} | Skipped: {len(skipped)} | Error: {len(errored)}")

        if passed:
            comment_parts.append(f"\n✓ RAN AND PASSED ({len(passed)}):")
            for r in passed:
                platform_device = f"{r.platform} × {r.device}" if r.device and r.device != 'none' else r.platform
                tv_info = f" [TV: {r.teamviewer_id}]" if r.teamviewer_id else ""
                comment_parts.append(f"  • {platform_device} ({r.duration:.1f}s){tv_info}")

        if failed:
            comment_parts.append(f"\n✗ RAN AND FAILED ({len(failed)}):")
            for r in failed:
                platform_device = f"{r.platform} × {r.device}" if r.device and r.device != 'none' else r.platform
                tv_info = f" [TV: {r.teamviewer_id}]" if r.teamviewer_id else ""
                comment_parts.append(f"  • {platform_device} ({r.duration:.1f}s){tv_info}")

        if skipped:
            comment_parts.append(f"\n— SKIPPED (test marked skip, did not run) ({len(skipped)}):")
            for r in skipped:
                platform_device = f"{r.platform} × {r.device}" if r.device and r.device != 'none' else r.platform
                comment_parts.append(f"  • {platform_device}")

        if errored:
            comment_parts.append(f"\n⊗ ERROR (fixture/setup failure, test did not run) ({len(errored)}):")
            for r in errored:
                platform_device = f"{r.platform} × {r.device}" if r.device and r.device != 'none' else r.platform
                tv_info = f" [TV: {r.teamviewer_id}]" if r.teamviewer_id else ""
                comment_parts.append(f"  • {platform_device} ({r.duration:.1f}s){tv_info}")

        # ── Failure / error details ───────────────────────────────────────────
        if errored:
            comment_parts.append("\n=== Error Details (fixture/setup — test body never ran) ===")
            for r in errored:
                platform_device = f"{r.platform} × {r.device}" if r.device and r.device != 'none' else r.platform
                comment_parts.append(f"\n[{platform_device}]")
                if r.failure_msg:
                    msg = r.failure_msg
                    if len(msg) > 1000:
                        msg = msg[:1000] + "\n... (truncated)"
                    comment_parts.append(msg)
                else:
                    comment_parts.append("  (no error details captured)")

        if failed:
            comment_parts.append("\n=== Failure Details (assertion failures) ===")
            for r in failed:
                platform_device = f"{r.platform} × {r.device}" if r.device and r.device != 'none' else r.platform
                comment_parts.append(f"\n[{platform_device}]")
                if r.failure_msg:
                    msg = r.failure_msg
                    if len(msg) > 1000:
                        msg = msg[:1000] + "\n... (truncated)"
                    comment_parts.append(msg)
                else:
                    comment_parts.append("  (no failure details captured)")

        # ── Build link ────────────────────────────────────────────────────────
        if build_url:
            comment_parts.append(f"\nAzure DevOps Build: {build_url}")

        return "\n".join(comment_parts)


class TestResultAggregator:
    """Aggregates test results from multiple platform executions."""
    
    def __init__(self, artifact_dir: Path):
        self.artifact_dir = artifact_dir
        self.aggregated: Dict[str, AggregatedResult] = {}
        self.testrail_pattern = re.compile(r"(?:S(?P<suite>\d+):)?C(?P<case>\d+)")
        self.workspace_root = None  # Will be set if needed for automation detection
    
    def find_automation_for_case(self, case_id: str, suite_id: str = None) -> Tuple[bool, str]:
        """
        Check if automation exists for a test case.
        
        Returns:
            Tuple of (has_automation, reason_if_not)
        """
        if not self.workspace_root:
            # Try to find workspace root from artifact directory
            # Artifact dir is typically: workspace/pipeline-workspace/test-results
            current = self.artifact_dir
            for _ in range(5):  # Search up to 5 levels
                if (current / 'tests').exists():
                    self.workspace_root = current
                    break
                current = current.parent
        
        if not self.workspace_root:
            return (False, "Cannot determine workspace root to search for automation")
        
        # Search for TestRail marker in test files
        tests_dir = self.workspace_root / 'tests'
        if not tests_dir.exists():
            return (False, "Tests directory not found in workspace")
        
        # Build search pattern for this case ID
        search_patterns = []
        if suite_id:
            search_patterns.append(f'@pytest.mark.testrail("S{suite_id}:C{case_id}")')
            search_patterns.append(f"@pytest.mark.testrail('S{suite_id}:C{case_id}')")
        search_patterns.append(f'@pytest.mark.testrail("C{case_id}")')
        search_patterns.append(f"@pytest.mark.testrail('C{case_id}')")
        
        # Search all Python test files
        for test_file in tests_dir.rglob('test_*.py'):
            try:
                content = test_file.read_text(encoding='utf-8')
                for pattern in search_patterns:
                    if pattern in content:
                        # Found automation - now check why it wasn't executed
                        return self._analyze_why_not_executed(test_file, content, case_id)
            except Exception as e:
                logging.debug(f"Error reading {test_file}: {e}")
                continue
        
        return (False, f"No automation found for test case C{case_id}")
    
    def _analyze_why_not_executed(self, test_file: Path, content: str, case_id: str) -> Tuple[bool, str]:
        """
        Analyze why automation exists but wasn't executed.
        
        Returns:
            Tuple of (True, reason)
        """
        reasons = []
        
        # Extract platform and device markers from the test
        platform_match = re.search(r'@pytest\.mark\.platform\((.*?)\)', content, re.DOTALL)
        device_match = re.search(r'@pytest\.mark\.connected_device\((.*?)\)', content, re.DOTALL)
        
        if platform_match:
            # Extract platform names
            platforms_str = platform_match.group(1)
            platforms = re.findall(r'["\']([^"\']+)["\']', platforms_str)
            if platforms:
                reasons.append(f"Requires platform(s): {', '.join(platforms)}")
        
        if device_match:
            # Extract device names
            devices_str = device_match.group(1)
            devices = re.findall(r'["\']([^"\']+)["\']', devices_str)
            if devices:
                reasons.append(f"Requires device(s): {', '.join(devices)}")
        
        if reasons:
            return (True, f"Automation exists but not executed - {' | '.join(reasons)} - No matching hardware/platform available in this run")
        else:
            return (True, f"Automation exists in {test_file.name} but was not executed - Test may have been filtered out or skipped")
    
    def parse_junit_xml(self, xml_file: Path, platform: str, device: str) -> None:
        """Parse a JUnit XML file and extract test results."""
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            # Handle both <testsuites> and <testsuite> root elements
            testsuites = root.findall('.//testsuite')
            if not testsuites:
                testsuites = [root] if root.tag == 'testsuite' else []
            
            logging.debug(f"Found {len(testsuites)} test suites in {xml_file.name}")
            
            for testsuite in testsuites:
                testcases = testsuite.findall('testcase')
                logging.debug(f"Found {len(testcases)} test cases in suite")
                
                for testcase in testcases:
                    # Get test properties to find TestRail case ID
                    # Extract TestRail case ID and TeamViewer ID from properties
                    case_id = None
                    suite_id = None
                    teamviewer_id = None
                    
                    # Log testcase details for debugging
                    testcase_name = testcase.get('name', 'unknown')
                    logging.debug(f"Processing testcase: {testcase_name}")
                    
                    properties = testcase.find('properties')
                    if properties is not None:
                        logging.debug(f"Found properties element with {len(properties.findall('property'))} properties")
                        for prop in properties.findall('property'):
                            prop_name = prop.get('name')
                            prop_value = prop.get('value')
                            logging.debug(f"Property: {prop_name} = {prop_value}")
                            if prop_name == 'testrail_case_id':
                                marker_value = prop_value
                                match = self.testrail_pattern.match(marker_value)
                                if match:
                                    suite_id = match.group('suite')
                                    case_id = match.group('case')
                                    logging.debug(f"Matched TestRail case: suite={suite_id}, case={case_id}")
                                else:
                                    logging.warning(f"Failed to parse testrail_case_id value: {marker_value}")
                            elif prop_name == 'teamviewer_id':
                                teamviewer_id = prop_value
                                logging.debug(f"Found TeamViewer ID: {teamviewer_id}")
                    else:
                        logging.debug("No properties element found in testcase")
                    
                    if not case_id:
                        # Skip tests without TestRail markers
                        logging.debug(f"Skipping testcase {testcase_name} - no TestRail case ID found")
                        continue
                    
                    # Determine status
                    failure = testcase.find('failure')
                    error = testcase.find('error')
                    skipped = testcase.find('skipped')
                    
                    if error is not None:
                        # ERROR = test execution blocked (setup/teardown/collection errors)
                        status = 'error'
                        failure_msg = error.get('message', '')
                        if error.text:
                            failure_msg += f"\n{error.text}"
                    elif failure is not None:
                        # FAILURE = test assertion failed
                        status = 'failed'
                        failure_msg = failure.get('message', '')
                        if failure.text:
                            failure_msg += f"\n{failure.text}"
                    elif skipped is not None:
                        status = 'skipped'
                        failure_msg = None
                    else:
                        status = 'passed'
                        failure_msg = None
                    
                    # Get duration
                    duration = float(testcase.get('time', 0))
                    
                    # Get nodeid (classname + name)
                    classname = testcase.get('classname', '')
                    name = testcase.get('name', '')
                    nodeid = f"{classname}::{name}" if classname else name
                    
                    # Create test result
                    result = TestResult(
                        case_id=case_id,
                        platform=platform,
                        device=device,
                        status=status,
                        duration=duration,
                        failure_msg=failure_msg,
                        nodeid=testcase_name,
                        teamviewer_id=teamviewer_id
                    )
                    
                    # Add to aggregated results
                    key = case_id
                    if key not in self.aggregated:
                        self.aggregated[key] = AggregatedResult(case_id, suite_id)
                    self.aggregated[key].add_result(result)
                    
        except Exception as e:
            logging.error(f"Failed to parse {xml_file}: {e}")
    
    def load_all_results(self) -> None:
        """Load all JUnit XML files from artifact directory."""
        if not self.artifact_dir.exists():
            logging.error(f"Artifact directory not found: {self.artifact_dir}")
            return
        
        # Pattern: test-results-{platform}-{device}.xml
        xml_files = list(self.artifact_dir.glob("**/test-results-*.xml"))
        
        logging.info(f"Found {len(xml_files)} result files")
        
        for xml_file in xml_files:
            # Extract platform and device from filename
            filename = xml_file.stem  # e.g., "test-results-cashmerexi-roo"
            parts = filename.replace('test-results-', '').split('-')
            
            if len(parts) >= 2:
                platform = parts[0]
                device = '-'.join(parts[1:])  # Handle multi-part device names
            else:
                platform = parts[0] if parts else 'unknown'
                device = 'none'
            
            logging.info(f"Parsing {xml_file.name} (Platform: {platform}, Device: {device})")
            self.parse_junit_xml(xml_file, platform, device)
    
    def upload_to_testrail(
        self,
        run_id: str = None,
        milestone_id: str = None,
        run_name: str = None,
        plan_id: str = None,
        plan_name: str = None,
        version: str = None,
        skip_invalid_case_ids: bool = False,
        testrail_project_id: str = None,
        testrail_suite_id: str = None,
    ) -> None:
        """Upload aggregated results to TestRail."""
        if not self.aggregated:
            logging.warning("No test results to upload")
            return
        
        # Get build URL from environment
        build_uri = os.environ.get('SYSTEM_TEAMFOUNDATIONCOLLECTIONURI')
        team_project = os.environ.get('SYSTEM_TEAMPROJECT')
        build_id = os.environ.get('BUILD_BUILDID')
        build_url = None
        if build_uri and team_project and build_id:
            build_url = f"{build_uri}{team_project}/_build/results?buildId={build_id}"
        
        # Prepare results for TestRail API format
        results: List[dict] = []
        
        # Map aggregated outcome → TestRail status_id.
        # 'never_executed' is intentionally absent: no status_id is set so TestRail keeps
        # the case as Untested. The comment is still written for visibility.
        status_map = {
            'passed':  TestStatus.PASSED,   # All devices passed
            'failed':  TestStatus.FAILED,   # Assertion failure on at least one device
            'partial': TestStatus.RETEST,   # Some devices ran, others had fixture/device errors
        }

        for case_id, agg_result in self.aggregated.items():
            overall_status = agg_result.get_overall_status()

            tr_result = {
                'case_id': int(agg_result.case_id),
                'elapsed': f"{max(1, int(agg_result.get_total_duration()))}s",
                'comment': agg_result.build_comment(build_url)
            }

            # Set status_id only for outcomes where at least one device ran the test.
            # 'never_executed' leaves status_id absent → case stays Untested in TestRail.
            if overall_status in status_map:
                tr_result['status_id'] = status_map[overall_status]

            if version:
                tr_result['version'] = version

            results.append(tr_result)
        
        # Upload to TestRail
        logging.info(f"Uploading {len(self.aggregated)} aggregated results to TestRail")
        
        # Get TestRail credentials from environment variables
        testrail_url = os.environ.get('TESTRAIL_URL')
        testrail_user = os.environ.get('TESTRAIL_USER_NAME')
        testrail_api_key = os.environ.get('TESTRAIL_API_KEY')
        
        if not all([testrail_url, testrail_user, testrail_api_key]):
            raise ValueError("Missing TestRail credentials in environment variables: TESTRAIL_URL, TESTRAIL_USER_NAME, TESTRAIL_API_KEY")
        
        api = TestRailAPI(testrail_user, testrail_api_key, testrail_url)
        
        if run_id:
            # Upload to existing run
            run_record = api.get_run(run_id)
            test_records = api.get_tests(run_record["id"])
            
            # Update milestone if provided and different from current
            if milestone_id:
                current_milestone_id = run_record.get("milestone_id")
                milestone_id_int = int(milestone_id)
                
                if current_milestone_id != milestone_id_int:
                    logging.info(f"Updating run {run_id} milestone from {current_milestone_id} to {milestone_id_int}")
                    api.update_run(run_id, {"milestone_id": milestone_id_int})
                else:
                    logging.info(f"Run {run_id} already has milestone {milestone_id_int}")
            
            # Convert case_ids to test_ids
            case_to_test = {test["case_id"]: test["id"] for test in test_records}
            executed_case_ids = {r["case_id"] for r in results}
            
            for result in results:
                if result["case_id"] in case_to_test:
                    result["test_id"] = case_to_test[result["case_id"]]
                    del result["case_id"]
            
            # Filter out results without test_id
            results = [r for r in results if "test_id" in r]
            
            # Find missing test cases (in TestRail run but not executed)
            testrail_case_ids = set(case_to_test.keys())
            missing_case_ids = testrail_case_ids - executed_case_ids
            
            if missing_case_ids:
                logging.warning(f"Found {len(missing_case_ids)} test cases in the TestRail run that were not executed")

                not_in_automation = 0
                marked_blocked = 0
                marked_retest = 0

                for case_id in missing_case_ids:
                    test_id = case_to_test[case_id]

                    # Check whether this case exists in our automation at all.
                    # If it doesn't, leave it completely untouched (stay Untested).
                    has_automation, reason = self.find_automation_for_case(str(case_id))

                    if not has_automation:
                        # Case is not in our automation suite — do not touch it.
                        not_in_automation += 1
                        logging.debug(f"Skipping C{case_id}: not in automation ({reason})")
                        continue

                    # Case IS in automation but was not executed this run.
                    # Distinguish device/environment issues (→ Blocked) from script issues (→ Retest).
                    # find_automation_for_case returns reasons like "Requires platform(s): ..." when
                    # the test needs hardware that wasn't available in this run.
                    is_device_env_issue = any(
                        kw in reason.lower()
                        for kw in ('requires platform', 'requires device', 'no matching hardware', 'no available device')
                    )

                    if is_device_env_issue:
                        missing_status = TestStatus.BLOCKED
                        status_label = "Blocked"
                        marked_blocked += 1
                    else:
                        missing_status = TestStatus.RETEST
                        status_label = "Retest"
                        marked_retest += 1

                    comment_parts = [
                        f"⊘ Test is in automation but was not executed this run ({status_label})",
                        f"\nReason: {reason}"
                    ]
                    if build_url:
                        comment_parts.append(f"\nAzure DevOps Build: {build_url}")

                    missing_result = {
                        'test_id': test_id,
                        'status_id': missing_status,
                        'comment': "\n".join(comment_parts)
                    }
                    if version:
                        missing_result['version'] = version

                    results.append(missing_result)

                logging.info(
                    f"Missing case handling: {not_in_automation} left Untested (not in automation), "
                    f"{marked_blocked} marked Blocked (device/env issue), "
                    f"{marked_retest} marked Retest (script issue)"
                )
            
            api.add_results(run_record["id"], results)
            logging.info(f'Uploaded {len(results)} results to run {run_record["id"]} ({run_record["name"]})')
            
        else:
            # Create a new run (single-suite) and upload
            project_id = testrail_project_id or os.environ.get('TESTRAIL_PROJECT_ID')
            suite_id = testrail_suite_id or os.environ.get('TESTRAIL_SUITE_ID')
            if not project_id or not suite_id:
                raise ValueError(
                    "No TestRail run ID provided and missing suite information. "
                    "Set TESTRAIL_PROJECT_ID and TESTRAIL_SUITE_ID (or provide --testrail-run-id)."
                )

            if not run_name:
                run_name = "[Automation] Test Run"

            case_ids = sorted({int(r["case_id"]) for r in results if "case_id" in r})

            # Validate case IDs up-front to avoid HTTP 400 on add_run().
            # This commonly happens when TESTRAIL_PROJECT_ID / TESTRAIL_SUITE_ID don't match the cases in automation.
            suite_id_int = int(suite_id)
            valid_case_ids: List[int] = []
            invalid_case_ids: List[int] = []
            case_suite_map: Dict[int, int] = {}  # case_id -> suite_id

            for cid in case_ids:
                try:
                    case = api.get_case(cid)
                except Exception as e:
                    logging.debug(f"get_case({cid}) failed: {e}")
                    invalid_case_ids.append(cid)
                    continue

                actual_suite_id = case.get("suite_id")
                if actual_suite_id is not None:
                    try:
                        actual_suite_id_int = int(actual_suite_id)
                    except Exception:
                        actual_suite_id_int = None
                    if actual_suite_id_int is not None:
                        case_suite_map[cid] = actual_suite_id_int

                valid_case_ids.append(cid)

            # If cases all belong to a different single suite, auto-switch to it.
            suite_ids_found = {sid for sid in case_suite_map.values() if sid is not None}
            if suite_ids_found and suite_id_int not in suite_ids_found:
                if len(suite_ids_found) == 1:
                    detected_suite_id = next(iter(suite_ids_found))
                    logging.warning(
                        f"Configured TESTRAIL_SUITE_ID={suite_id_int} does not match cases; "
                        f"auto-detected suite_id={detected_suite_id} from case IDs."
                    )
                    suite_id_int = detected_suite_id
                    suite_id = str(detected_suite_id)
                else:
                    preview = ", ".join([f"S{sid}" for sid in sorted(list(suite_ids_found))[:10]])
                    raise ValueError(
                        "TestRail cases span multiple suites; cannot create a single-suite run.\n"
                        f"Configured: TESTRAIL_PROJECT_ID={project_id}, TESTRAIL_SUITE_ID={suite_id}\n"
                        f"Suites detected from cases: {preview}{' ...' if len(suite_ids_found) > 10 else ''}\n\n"
                        "Fix by: (1) using --testrail-run-id for an existing run, or (2) splitting execution by suite."
                    )

            wrong_suite_case_ids = [cid for cid, sid in case_suite_map.items() if sid != suite_id_int]
            if invalid_case_ids or wrong_suite_case_ids:
                msg_parts = [
                    "TestRail case ID validation failed for new-run creation.",
                    f"Configured: TESTRAIL_PROJECT_ID={project_id}, TESTRAIL_SUITE_ID={suite_id}",
                ]
                if invalid_case_ids:
                    msg_parts.append(
                        f"Unrecognized case IDs ({len(invalid_case_ids)}): {invalid_case_ids[:25]}"
                        + (" ..." if len(invalid_case_ids) > 25 else "")
                    )
                if wrong_suite_case_ids:
                    preview_pairs = [(cid, case_suite_map.get(cid)) for cid in wrong_suite_case_ids]
                    preview = ", ".join([f"C{cid}->S{sid}" for cid, sid in preview_pairs[:25]])
                    msg_parts.append(
                        f"Case IDs in a different suite ({len(wrong_suite_case_ids)}): {preview}"
                        + (" ..." if len(wrong_suite_case_ids) > 25 else "")
                    )

                full_msg = "\n".join(msg_parts)
                if not skip_invalid_case_ids:
                    raise ValueError(
                        full_msg
                        + "\n\nFix by either: (1) setting correct TESTRAIL_PROJECT_ID/TESTRAIL_SUITE_ID, "
                        + "or (2) providing --testrail-run-id for an existing run that contains these cases, "
                        + "or (3) rerun with --testrail-skip-invalid-case-ids to create a run with only valid cases."
                    )

                logging.warning(full_msg)

            valid_set = {cid for cid in valid_case_ids if case_suite_map.get(cid, suite_id_int) == suite_id_int}
            results = [r for r in results if r.get("case_id") in valid_set]
            case_ids = sorted(valid_set)

            if not case_ids:
                raise ValueError(
                    "No valid TestRail case IDs remain after validation. "
                    "Check TESTRAIL_PROJECT_ID/TESTRAIL_SUITE_ID or use --testrail-run-id."
                )

            milestone_id_int = int(milestone_id) if milestone_id else None

            run_record = None

            if plan_id or plan_name:
                selected_plan_id = int(plan_id) if plan_id else None

                if selected_plan_id is None:
                    plan_query = {"is_completed": 0}
                    if milestone_id_int is not None:
                        plan_query["milestone_id"] = milestone_id_int

                    existing_plans = api.get_plans(int(project_id), params=plan_query) or []
                    existing_plan = None
                    for p in existing_plans:
                        if p.get("name") == plan_name:
                            existing_plan = p
                            break

                    if existing_plan:
                        selected_plan_id = int(existing_plan["id"])
                        logging.info(f"Using existing TestRail plan {selected_plan_id} ({plan_name})")
                    else:
                        if not plan_name:
                            raise ValueError("testrail plan_name is required when plan_id is not provided")
                        created_plan = api.add_plan(
                            name=plan_name,
                            project_id=int(project_id),
                            milestone_id=milestone_id_int,
                        )
                        selected_plan_id = int(created_plan["id"])
                        logging.info(f"Created TestRail plan {selected_plan_id} ({plan_name})")

                plan_record = api.get_plan(selected_plan_id)
                existing_run_in_plan = None
                for entry in plan_record.get("entries", []):
                    for r in entry.get("runs", []):
                        if r.get("name") == run_name and r.get("suite_id") == int(suite_id) and not r.get("is_completed", False):
                            existing_run_in_plan = r
                            break
                    if existing_run_in_plan:
                        break

                if existing_run_in_plan:
                    run_record = existing_run_in_plan
                    logging.info(f"Using existing run in plan: {run_record['id']} ({run_record.get('name')})")
                else:
                    entry_resp = api.add_plan_entry(
                        plan_id=selected_plan_id,
                        suite_id=int(suite_id),
                        name=run_name,
                        case_ids=case_ids,
                    )
                    created_run = None
                    for r in entry_resp.get("runs", []):
                        if r.get("name") == run_name and r.get("suite_id") == int(suite_id):
                            created_run = r
                            break
                    if not created_run and entry_resp.get("runs"):
                        created_run = entry_resp.get("runs")[-1]
                    if not created_run:
                        raise ValueError(f"Failed to resolve created run from plan entry response (plan_id={selected_plan_id})")
                    run_record = created_run
                    logging.info(f"Created plan run {run_record['id']} under plan {selected_plan_id}")
            else:
                logging.info(
                    f"Creating new TestRail run: name='{run_name}', project_id={project_id}, suite_id={suite_id}, cases={len(case_ids)}"
                )
                try:
                    run_record = api.add_run(
                        name=run_name,
                        project_id=int(project_id),
                        suite_id=int(suite_id),
                        case_ids=case_ids,
                        milestone_id=milestone_id_int,
                    )
                except Exception as e:
                    preview = case_ids[:25]
                    raise ValueError(
                        f"Failed to create TestRail run (project_id={project_id}, suite_id={suite_id}). "
                        f"Cases preview: {preview}{' ...' if len(case_ids) > 25 else ''}. Error: {e}"
                    )

            test_records = api.get_tests(run_record["id"])
            case_to_test = {test["case_id"]: test["id"] for test in test_records}

            for result in results:
                if result["case_id"] in case_to_test:
                    result["test_id"] = case_to_test[result["case_id"]]
                    del result["case_id"]

            results = [r for r in results if "test_id" in r]
            api.add_results(run_record["id"], results)
            logging.info(f'Uploaded {len(results)} results to NEW run {run_record["id"]} ({run_record.get("name")})')


def main():
    """Main entry point."""
    # Enable debug logging to troubleshoot XML parsing
    log_level = logging.DEBUG if os.getenv('DEBUG') else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    parser = argparse.ArgumentParser(description='Aggregate test results from multiple platforms')
    parser.add_argument('--artifact-dir', required=True, help='Directory containing test result XML files')
    parser.add_argument('--output', help='Output file for aggregated results JSON (optional)')
    parser.add_argument('--testrail-run-id', help='Existing TestRail run ID to upload to')
    parser.add_argument('--testrail-plan-id', help='Existing TestRail plan ID to upload runs under')
    parser.add_argument('--testrail-plan-name', help='TestRail plan name to create/reuse for run uploads')
    parser.add_argument('--testrail-milestone-id', help='TestRail milestone ID for new runs')
    parser.add_argument('--run-name', help='Name for created TestRail run')
    parser.add_argument('--version', help='Application version')
    parser.add_argument('--testrail-project-id', help='Override TestRail project id (defaults to TESTRAIL_PROJECT_ID env var)')
    parser.add_argument('--testrail-suite-id', help='Override TestRail suite id (defaults to TESTRAIL_SUITE_ID env var)')
    parser.add_argument(
        '--testrail-skip-invalid-case-ids',
        action='store_true',
        help='When creating a new run, skip invalid/wrong-suite case IDs instead of failing',
    )
    
    args = parser.parse_args()
    
    artifact_dir = Path(args.artifact_dir)
    
    aggregator = TestResultAggregator(artifact_dir)
    aggregator.load_all_results()
    
    logging.info(f"Aggregated {len(aggregator.aggregated)} unique test cases")
    
    # Save to JSON if output specified
    if args.output:
        output_data = {
            key: {
                'case_id': agg.case_id,
                'suite_id': agg.suite_id,
                'status': agg.get_overall_status(),
                'results': [
                    {
                        'platform': r.platform,
                        'device': r.device,
                        'status': r.status,
                        'duration': r.duration
                    }
                    for r in agg.results
                ]
            }
            for key, agg in aggregator.aggregated.items()
        }
        
        with open(args.output, 'w') as f:
            json.dump(output_data, f, indent=2)
        logging.info(f"Saved aggregated results to {args.output}")
    
    # Upload to TestRail
    aggregator.upload_to_testrail(
        run_id=args.testrail_run_id,
        plan_id=args.testrail_plan_id,
        plan_name=args.testrail_plan_name,
        milestone_id=args.testrail_milestone_id,
        run_name=args.run_name,
        version=args.version,
        skip_invalid_case_ids=args.testrail_skip_invalid_case_ids,
        testrail_project_id=args.testrail_project_id,
        testrail_suite_id=args.testrail_suite_id,
    )


if __name__ == '__main__':
    main()