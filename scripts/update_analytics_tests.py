"""
This script updates analytics test files to ensure they have the correct pytest markers.

It performs the following operations on each test file:
1. Ensures that 'import pytest' is present at the top of the file.
2. Removes any existing @pytest.mark.analytics decorators to prevent duplicates.
3. Adds class-level markers (@pytest.mark.analytics and @pytest.mark.platform("TBD")) above each test class.
4. For each test function, it adds a @pytest.mark.testrail("C12345") marker based on the function name (e.g., test_example_C12345)
5. For each test function, it removes the _C12345 suffix from the function name.

Usage:

Process entire analytics directory (no subfolders):
    python update_analytics_tests.py

Process specific subfolder (no subfolders inside it):
    python update_analytics_tests.py pcdevice_analytics

Process specific folder INCLUDING its subfolders:
    python update_analytics_tests.py pcdevice_analytics --recursive

Process full analytics directory INCLUDING all subfolders:
    python update_analytics_tests.py --recursive
"""

import re
import sys
from pathlib import Path

BASE_ANALYTICS_DIR = (
    Path(__file__).parent.parent / "tests" / "hp_app" / "analytics"
)


def ensure_pytest_import(content):
    if "import pytest" not in content:
        return "import pytest\n\n" + content
    return content


def remove_existing_analytics_markers(content):
    """
    Remove any existing @pytest.mark.analytics decorators
    """
    pattern = re.compile(r"^\s*@pytest\.mark\.analytics\s*\n", re.MULTILINE)
    return pattern.sub("", content)


def add_class_markers(content):
    """
    Add class-level markers above each test class.
    """
    class_pattern = re.compile(r"^class\s+\w+\s*[\(:]", re.MULTILINE)

    def replace_class(match):
        markers = (
            "@pytest.mark.analytics\n"
            "@pytest.mark.platform(\"TBD\")\n"
        )
        return markers + match.group(0)

    return class_pattern.sub(replace_class, content)


def process_test_functions(content):
    """
    Add @pytest.mark.testrail("C12345") above tests
    and remove _C12345 from function name.

    Ensures there is an empty line before the marker.
    Handles async tests and fixtures.
    """
    pattern = re.compile(
        r"^(\s*)(async\s+def|def)\s+(test_\w+)_C(\d+)\s*\((.*?)\):",
        re.MULTILINE,
    )

    def replace_test(match):
        indent = match.group(1)
        def_type = match.group(2)
        base_name = match.group(3)
        case_id = match.group(4)
        params = match.group(5)

        marker = f'{indent}@pytest.mark.testrail("C{case_id}")\n'
        new_def = f"{indent}{def_type} {base_name}({params}):"

        return f"\n{marker}{new_def}"

    return pattern.sub(replace_test, content)


def process_file(file_path):
    print(f"  → Processing file: {file_path}")
    content = file_path.read_text()

    content = remove_existing_analytics_markers(content)
    content = ensure_pytest_import(content)
    content = add_class_markers(content)
    content = process_test_functions(content)

    file_path.write_text(content)


def main():
    print("=" * 60)
    print("Starting analytics test update script")
    print(f"Base analytics directory: {BASE_ANALYTICS_DIR}")

    args = sys.argv[1:]

    recursive = False
    sub_path_arg = None

    for arg in args:
        if arg == "--recursive":
            recursive = True
        else:
            sub_path_arg = arg

    if sub_path_arg:
        target_path = BASE_ANALYTICS_DIR / sub_path_arg
        print(f"Sub-path argument provided: {sub_path_arg}")
    else:
        target_path = BASE_ANALYTICS_DIR
        print("No sub-path provided. Using full analytics directory.")

    print(f"Recursive mode: {'ON' if recursive else 'OFF'}")
    print(f"Looking for test files in: {target_path}")
    print("=" * 60)

    if not target_path.exists():
        print(f"❌ Path does not exist: {target_path}")
        sys.exit(1)

    if recursive:
        test_files = list(target_path.rglob("test_*.py"))
    else:
        test_files = list(target_path.glob("test_*.py"))

    if not test_files:
        print("⚠️  No test files found matching pattern test_*.py")
        return

    print(f"Found {len(test_files)} test file(s).\n")

    for file_path in test_files:
        process_file(file_path)

    print("\n" + "=" * 60)
    print(f"Completed. Updated {len(test_files)} file(s).")
    print("=" * 60)


if __name__ == "__main__":
    main()
