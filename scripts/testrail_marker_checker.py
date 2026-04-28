import re
from pathlib import Path
from collections import defaultdict

def check_testrail_markers():
    """Check if all tests in tests/hp_app have pytest.mark.testrail marker and find duplicate values."""

    test_dir = Path("tests/hp_app")
    if not test_dir.exists():
        print(f"Error: {test_dir} directory not found")
        return

    # Pattern to find testrail marker value
    testrail_pattern = re.compile(r'@pytest\.mark\.testrail\s*\(\s*["\']?(C\d+)["\']?\s*\)')
    # Pattern to find all test functions
    all_test_pattern = re.compile(r'^\s*def\s+(test_\w+)\s*\(', re.MULTILINE)

    missing_marker_tests = []
    marker_values = defaultdict(list)
    total_tests = 0

    # Iterate through all Python files in tests/hp_app
    for test_file in test_dir.rglob("test_*.py"):
        with open(test_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Find all test functions
        all_tests = all_test_pattern.findall(content)
        total_tests += len(all_tests)

        # Find all decorators and test functions
        # This pattern captures decorators (including those with leading/trailing spaces)
        for match in re.finditer(r'((?:^\s*@[^\n]+\n)*)\s*def\s+(test_\w+)\s*\(', content, re.MULTILINE):
            decorators = match.group(1)
            test_name = match.group(2)

            # Check if testrail marker exists in decorators
            testrail_match = testrail_pattern.search(decorators)

            if testrail_match:
                marker_value = testrail_match.group(1)
                marker_values[marker_value].append((test_file, test_name))
            else:
                missing_marker_tests.append((test_file, test_name))

    # Identify duplicate marker values
    duplicate_markers = {k: v for k, v in marker_values.items() if len(v) > 1}

    # Helper function to format test path
    def format_test_path(test_file, test_name):
        # Get path relative to test_dir and convert to pytest format
        path_str = str(test_file.relative_to(test_dir)).replace('\\', '/').replace('.py', '')
        return f"{path_str}::{test_name}"

    # Report results
    print(f"\n{'='*60}")
    print(f"TestRail Marker Check Results")
    print(f"{'='*60}")
    print(f"Total test files scanned: {len(list(test_dir.rglob('test_*.py')))}")
    print(f"Total test functions found: {total_tests}")
    print(f"Test functions missing @pytest.mark.testrail: {len(missing_marker_tests)}")
    print(f"Duplicate marker values found: {len(duplicate_markers)}")

    if missing_marker_tests:
        print(f"\n{'⚠️  Tests Missing Marker:':60}")
        for test_file, test_name in sorted(missing_marker_tests):
            print(f"  {format_test_path(test_file, test_name)}")

    if duplicate_markers:
        print(f"\n{'⚠️  Duplicate Marker Values:':60}")
        for marker_value in sorted(duplicate_markers.keys()):
            tests = duplicate_markers[marker_value]
            print(f"\n  {marker_value} used in {len(tests)} tests:")
            for test_file, test_name in sorted(tests):
                print(f"    {format_test_path(test_file, test_name)}")

    success = len(missing_marker_tests) == 0 and len(duplicate_markers) == 0

    if success:
        print(f"\n{'✅ All test functions have unique @pytest.mark.testrail markers!'}")
        return True
    else:
        return False

if __name__ == "__main__":
    success = check_testrail_markers()
    exit(0 if success else 1)