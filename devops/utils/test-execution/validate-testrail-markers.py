"""
TestRail Marker Validation Script

Purpose: Pre-execution validation of @pytest.mark.testrail() markers in test files.
Validates marker format and warns about invalid case IDs that will be skipped during result upload.

Expected Marker Formats:
- @pytest.mark.testrail("C12345") - Case ID only (suite from TESTRAIL_SUITE_ID env var)
- @pytest.mark.testrail("S177594:C12345") - Suite and case ID

Invalid Patterns:
- Missing C prefix
- Non-numeric case ID
- Invalid S:C separator
- Empty strings

Outputs:
- Exit code 0 with warnings if invalid markers found
- Prints summary of valid/invalid markers by file
"""

import ast
import argparse
import sys
import re
from pathlib import Path
from typing import Dict, List, Tuple


class TestRailMarkerValidator:
    """Validates @pytest.mark.testrail() markers in Python test files."""
    
    # Regex pattern matching testrail_misc.py
    MARKER_PATTERN = re.compile(r"(?:S(?P<suite>\d+):)?C(?P<case>\d+)")
    
    def __init__(self, suite_path: str):
        """Initialize validator with test suite path."""
        self.suite_path = Path(suite_path)
        self.valid_markers: Dict[str, List[str]] = {}
        self.invalid_markers: Dict[str, List[str]] = {}
        
    def validate_marker(self, marker_value: str) -> bool:
        """Validate a single TestRail marker value."""
        if not marker_value or not isinstance(marker_value, str):
            return False
        
        match = self.MARKER_PATTERN.fullmatch(marker_value)
        return match is not None
    
    def parse_file(self, file_path: Path) -> Tuple[List[str], List[str]]:
        """
        Parse a single Python file and extract TestRail markers.
        
        Returns:
            Tuple of (valid_markers, invalid_markers)
        """
        valid = []
        invalid = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read(), filename=str(file_path))
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    for decorator in node.decorator_list:
                        # Handle @pytest.mark.testrail("C12345")
                        if (isinstance(decorator, ast.Call) and
                            isinstance(decorator.func, ast.Attribute) and
                            decorator.func.attr == 'testrail'):
                            
                            if decorator.args:
                                arg = decorator.args[0]
                                if isinstance(arg, ast.Constant):
                                    marker_value = arg.value
                                    if self.validate_marker(marker_value):
                                        valid.append(marker_value)
                                    else:
                                        invalid.append(marker_value)
                                        
        except Exception as e:
            print(f"[ERROR] Failed to parse {file_path}: {e}", file=sys.stderr)
        
        return valid, invalid
    
    def validate_suite(self) -> int:
        """
        Validate all test files in the suite path.
        
        Returns:
            0 if all valid or only warnings, 1 if critical errors
        """
        if not self.suite_path.exists():
            print(f"[ERROR] Suite path not found: {self.suite_path}", file=sys.stderr)
            return 1
        
        # Find all test files
        test_files = list(self.suite_path.rglob("test*.py"))
        
        if not test_files:
            print(f"[WARNING] No test files found in {self.suite_path}")
            return 0
        
        print(f"Validating TestRail markers in {len(test_files)} test file(s)...")
        
        total_valid = 0
        total_invalid = 0
        
        for test_file in test_files:
            valid, invalid = self.parse_file(test_file)
            
            if valid:
                self.valid_markers[str(test_file.relative_to(self.suite_path))] = valid
                total_valid += len(valid)
            
            if invalid:
                self.invalid_markers[str(test_file.relative_to(self.suite_path))] = invalid
                total_invalid += len(invalid)
        
        # Print summary
        print(f"\nValidation Summary:")
        print(f"  Valid markers: {total_valid}")
        print(f"  Invalid markers: {total_invalid}")
        
        if total_valid > 0:
            print(f"\n[OK] Files with valid TestRail markers:")
            for file_path, markers in sorted(self.valid_markers.items()):
                print(f"  ✓ {file_path}: {len(markers)} marker(s)")
                for marker in markers[:5]:  # Show first 5
                    print(f"      - {marker}")
                if len(markers) > 5:
                    print(f"      ... and {len(markers) - 5} more")
        
        if total_invalid > 0:
            print(f"\n[WARNING] Files with invalid TestRail markers:")
            for file_path, markers in sorted(self.invalid_markers.items()):
                print(f"  ⚠ {file_path}: {len(markers)} invalid marker(s)")
                for marker in markers:
                    print(f"      - '{marker}' (expected format: 'C12345' or 'S177594:C12345')")
            print(f"\n[WARNING] Invalid markers will be skipped during TestRail result upload!")
            print(f"[WARNING] Expected format: 'C12345' or 'S177594:C12345'")
        
        # Return success with warnings (don't fail the build)
        return 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Validate TestRail markers in pytest test files'
    )
    parser.add_argument(
        '--suite-path',
        required=True,
        help='Path to test suite directory'
    )
    
    args = parser.parse_args()
    
    validator = TestRailMarkerValidator(args.suite_path)
    exit_code = validator.validate_suite()
    
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
