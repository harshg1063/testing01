#!/usr/bin/env python3
"""
Parse Test Markers - Extract pytest markers from test files for intelligent agent routing.

This tool uses AST (Abstract Syntax Tree) parsing to extract @pytest.mark.platform() and
@pytest.mark.connected_device() markers from test files. It handles marker inheritance
where method-level markers override class-level markers, validates that all tests have
at least one marker, and generates a cartesian product of platform×device combinations.

Usage:
    python parse-test-markers.py --suite-path <path> [--output <json_file>]

Example:
    python parse-test-markers.py --suite-path tests/hp_app/pen_control
"""

import argparse
import ast
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


class MarkerInfo:
    """Holds marker information for a test."""
    def __init__(self):
        self.platforms: List[str] = []
        self.devices: List[str] = []


class MarkerParser(ast.NodeVisitor):
    """AST visitor to extract pytest markers from test files."""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.current_class = None
        self.class_markers = {}
        self.class_exclusion = {}
        self.test_requirements = []
        self.test_cases = []  # Track all test cases with their markers
        self.skipped_test_cases = []  # Track tests excluded via @pytest.mark.skip/skipif
        self.errors = []
    
    def visit_ClassDef(self, node: ast.ClassDef):
        """Visit class definition to extract class-level markers."""
        if node.name.startswith('Test'):
            self.current_class = node.name
            self.class_markers[node.name] = self._extract_markers(node)
            self.class_exclusion[node.name] = self._get_exclusion_reason(node)
        
        # Continue visiting child nodes
        self.generic_visit(node)
        self.current_class = None
    
    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Visit function definition to extract test method markers."""
        if node.name.startswith('test_'):
            class_exclusion_reason = self.class_exclusion.get(self.current_class) if self.current_class else None
            method_exclusion_reason = self._get_exclusion_reason(node)

            if class_exclusion_reason or method_exclusion_reason:
                effective_reason = class_exclusion_reason if class_exclusion_reason else method_exclusion_reason
                self.skipped_test_cases.append({
                    'file': str(self.file_path),
                    'class': self.current_class,
                    'method': node.name,
                    'line': node.lineno,
                    'skip_source': 'class' if class_exclusion_reason else 'method',
                    'skip_reason': effective_reason
                })
                return

            # Get method-level markers
            method_markers = self._extract_markers(node)
            
            # Get class-level markers (if in a class)
            class_markers = MarkerInfo()
            if self.current_class:
                class_markers = self.class_markers.get(self.current_class, MarkerInfo())
            
            # Method markers override class markers
            final_markers = MarkerInfo()
            final_markers.platforms = method_markers.platforms if method_markers.platforms else class_markers.platforms
            final_markers.devices = method_markers.devices if method_markers.devices else class_markers.devices
            
            # Extract TestRail case ID from method or class decorators
            testrail_case_id = self._extract_testrail_case_id(node)
            if not testrail_case_id and self.current_class:
                # Check class-level testrail marker
                class_node = None
                # We need to find the class node - stored during visit_ClassDef
                # For now, just extract from method
                pass
            
            # Track test case information
            test_case = {
                'file': str(self.file_path),
                'class': self.current_class,
                'method': node.name,
                'line': node.lineno,
                'platforms': final_markers.platforms,
                'devices': final_markers.devices,
                'testrail_case_id': testrail_case_id
            }
            self.test_cases.append(test_case)
            
            # Validate at least one marker exists
            if not final_markers.platforms and not final_markers.devices:
                error_msg = self._format_missing_marker_error(node.name)
                self.errors.append(error_msg)
            else:
                # Add to requirements
                self._add_requirement(final_markers)

    def _is_marker_decorator(self, decorator, marker_name: str) -> bool:
        """Check decorator shapes for pytest marker usage, with and without call syntax."""
        # Handles: @pytest.mark.<name>(...)
        if isinstance(decorator, ast.Call) and self._is_marker_call(decorator, marker_name):
            return True

        # Handles: @pytest.mark.<name>
        if isinstance(decorator, ast.Attribute):
            if (isinstance(decorator.value, ast.Attribute) and
                isinstance(decorator.value.value, ast.Name) and
                decorator.value.value.id == 'pytest' and
                decorator.value.attr == 'mark' and
                decorator.attr == marker_name):
                return True

        return False

    def _is_xfail_run_false(self, decorator) -> bool:
        """Return True when decorator is @pytest.mark.xfail with run=False."""
        if not isinstance(decorator, ast.Call):
            return False

        if not self._is_marker_call(decorator, 'xfail'):
            return False

        for keyword in decorator.keywords:
            if keyword.arg == 'run':
                return isinstance(keyword.value, ast.Constant) and keyword.value.value is False

        return False

    def _get_exclusion_reason(self, node) -> Optional[str]:
        """Return exclusion reason for non-runnable tests, if any."""
        if not hasattr(node, 'decorator_list'):
            return None

        for decorator in node.decorator_list:
            if self._is_marker_decorator(decorator, 'skip'):
                return 'skip'
            if self._is_marker_decorator(decorator, 'skipif'):
                return 'skipif'
            if self._is_xfail_run_false(decorator):
                return 'xfail(run=False)'

        return None
    
    def _extract_markers(self, node) -> MarkerInfo:
        """Extract pytest.mark.platform and pytest.mark.connected_device markers from a node."""
        markers = MarkerInfo()
        
        if not hasattr(node, 'decorator_list'):
            return markers
        
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call):
                # Handle @pytest.mark.platform("value1", "value2")
                if self._is_marker_call(decorator, 'platform'):
                    markers.platforms = self._extract_marker_args(decorator)
                
                # Handle @pytest.mark.connected_device("value1", "value2")
                elif self._is_marker_call(decorator, 'connected_device'):
                    markers.devices = self._extract_marker_args(decorator)
        
        return markers
    
    def _is_marker_call(self, decorator: ast.Call, marker_name: str) -> bool:
        """Check if decorator is a pytest.mark.<marker_name> call."""
        if isinstance(decorator.func, ast.Attribute):
            if (isinstance(decorator.func.value, ast.Attribute) and
                isinstance(decorator.func.value.value, ast.Name) and
                decorator.func.value.value.id == 'pytest' and
                decorator.func.value.attr == 'mark' and
                decorator.func.attr == marker_name):
                return True
        return False
    
    def _extract_marker_args(self, decorator: ast.Call) -> List[str]:
        """Extract string arguments from marker decorator."""
        args = []
        for arg in decorator.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                args.append(arg.value)
        return args
    
    def _extract_testrail_case_id(self, node) -> Optional[str]:
        """Extract TestRail case ID from @pytest.mark.testrail() decorator."""
        if not hasattr(node, 'decorator_list'):
            return None
        
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call):
                # Check if it's @pytest.mark.testrail()
                if isinstance(decorator.func, ast.Attribute):
                    if (isinstance(decorator.func.value, ast.Attribute) and
                        isinstance(decorator.func.value.value, ast.Name) and
                        decorator.func.value.value.id == 'pytest' and
                        decorator.func.value.attr == 'mark' and
                        decorator.func.attr == 'testrail'):
                        
                        # Extract the case ID from the marker argument
                        for arg in decorator.args:
                            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                                return extract_testrail_case_id(arg.value)
        return None
    
    def _format_missing_marker_error(self, method_name: str) -> str:
        """Format a detailed error message for missing markers."""
        class_info = f" in class '{self.current_class}'" if self.current_class else ""
        return (
            f"ERROR: Missing required marker in {self.file_path}\n"
            f"  Location: Method '{method_name}'{class_info}\n"
            f"  Required: At least one of @pytest.mark.platform() or @pytest.mark.connected_device()\n"
            f"  Remediation: Add appropriate marker decorator to the test method or its class"
        )
    
    def _add_requirement(self, markers: MarkerInfo):
        """Add a test requirement (platform×device combination)."""
        requirement = {
            'platforms': markers.platforms,
            'devices': markers.devices
        }
        
        # Only add unique requirements
        if requirement not in self.test_requirements:
            self.test_requirements.append(requirement)


def extract_testrail_case_id(marker_value: str) -> Optional[str]:
    """
    Extract TestRail case ID from marker value.
    
    Handles formats:
    - "C12345" -> "C12345"
    - "S177594:C12345" -> "C12345"
    
    Args:
        marker_value: String value from @pytest.mark.testrail()
    
    Returns:
        Case ID in "C12345" format, or None if invalid
    """
    if not marker_value:
        return None
    
    # Match "C" followed by digits, optionally prefixed by "S<digits>:"
    match = re.search(r'(?:S\d+:)?(C\d+)', marker_value)
    if match:
        return match.group(1)
    
    return None


def has_testrail_marker_in_allowed_set(node, allowed_case_ids: Set[str]) -> bool:
    """
    Check if node has a testrail marker matching the allowed case IDs.
    
    Args:
        node: AST node (ClassDef or FunctionDef)
        allowed_case_ids: Set of allowed case IDs (e.g., {"C12345", "C12346"})
    
    Returns:
        True if node has matching testrail marker, False otherwise
    """
    if not hasattr(node, 'decorator_list'):
        return False
    
    for decorator in node.decorator_list:
        if isinstance(decorator, ast.Call):
            # Check if it's @pytest.mark.testrail()
            if isinstance(decorator.func, ast.Attribute):
                if (isinstance(decorator.func.value, ast.Attribute) and
                    isinstance(decorator.func.value.value, ast.Name) and
                    decorator.func.value.value.id == 'pytest' and
                    decorator.func.value.attr == 'mark' and
                    decorator.func.attr == 'testrail'):
                    
                    # Extract the case ID from the marker argument
                    for arg in decorator.args:
                        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                            case_id = extract_testrail_case_id(arg.value)
                            if case_id and case_id in allowed_case_ids:
                                return True
    
    return False


def check_test_has_testrail_marker(file_path: str, class_name: Optional[str], 
                                   method_name: str, allowed_case_ids: Set[str]) -> bool:
    """
    Re-parse file to check if a specific test has a TestRail marker in the allowed set.
    
    This function performs AST parsing to check both class-level and method-level
    testrail markers, with method-level taking precedence.
    
    Args:
        file_path: Path to the test file
        class_name: Class name (None if test is at module level)
        method_name: Test method name
        allowed_case_ids: Set of allowed case IDs from TestRail run
    
    Returns:
        True if test has a matching testrail marker, False otherwise
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read(), filename=file_path)
        
        # If no class, look for function at module level
        if class_name is None:
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == method_name:
                    return has_testrail_marker_in_allowed_set(node, allowed_case_ids)
            return False
        
        # Find the class and method
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                # Check class-level marker first
                class_has_marker = has_testrail_marker_in_allowed_set(node, allowed_case_ids)
                
                # Check method-level marker (overrides class level)
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == method_name:
                        method_has_marker = has_testrail_marker_in_allowed_set(item, allowed_case_ids)
                        # Method marker takes precedence
                        return method_has_marker if hasattr(item, 'decorator_list') and item.decorator_list else class_has_marker
                
                # Method found but no method-level marker, use class marker
                return class_has_marker
        
        return False
        
    except Exception as e:
        print(f"Warning: Failed to re-parse {file_path} for TestRail markers: {e}")
        return False


def filter_test_cases_by_testrail(test_cases: List[Dict], allowed_case_ids: Set[str]) -> List[Dict]:
    """
    Filter test cases to only include those with testrail markers in the allowed set.
    
    Args:
        test_cases: List of test case dictionaries
        allowed_case_ids: Set of allowed case IDs (e.g., {"C12345", "C12346"})
    
    Returns:
        Filtered list of test cases that have matching testrail markers
    """
    filtered = []
    
    for test_case in test_cases:
        file_path = test_case['file']
        class_name = test_case['class']
        method_name = test_case['method']
        
        if check_test_has_testrail_marker(file_path, class_name, method_name, allowed_case_ids):
            filtered.append(test_case)
    
    return filtered


def parse_test_file(file_path: Path) -> Tuple[List[Dict], List[Dict], List[Dict], List[str]]:
    """
    Parse a single test file to extract marker requirements.
    
    Args:
        file_path: Path to the Python test file
    
    Returns:
        Tuple of (requirements list, test_cases list, skipped_test_cases list, errors list)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read(), filename=str(file_path))
        
        parser = MarkerParser(str(file_path))
        parser.visit(tree)
        
        return parser.test_requirements, parser.test_cases, parser.skipped_test_cases, parser.errors
    
    except SyntaxError as e:
        error = f"ERROR: Syntax error in {file_path}: {e}"
        return [], [], [], [error]
    except Exception as e:
        error = f"ERROR: Failed to parse {file_path}: {e}"
        return [], [], [], [error]


def find_test_files(suite_path: Path) -> List[Path]:
    """
    Find all test files in the suite path.
    
    Args:
        suite_path: Path to the test suite directory or file
    
    Returns:
        List of test file paths
    """
    if not suite_path.exists():
        raise FileNotFoundError(f"Suite path not found: {suite_path}")
    
    # If it's a file, return it directly
    if suite_path.is_file():
        if suite_path.name.startswith('test_') and suite_path.suffix == '.py':
            return [suite_path]
        else:
            raise ValueError(f"File must be a test file (test_*.py): {suite_path}")
    
    # If it's a directory, find all test_*.py files recursively
    test_files = list(suite_path.rglob('test_*.py'))
    
    return sorted(test_files)


def generate_matrix_requirements(all_requirements: List[Dict]) -> List[Dict]:
    """
    Generate cartesian product of platform×device combinations.
    
    Args:
        all_requirements: List of requirement dictionaries with platforms and devices
    
    Returns:
        List of unique platform×device combinations
    """
    matrix = []
    
    for req in all_requirements:
        platforms = req['platforms']
        devices = req['devices']
        
        # Handle different marker scenarios
        if platforms and devices:
            # Both markers: create platform×device cartesian product
            for platform in platforms:
                for device in devices:
                    combo = {'platform': platform, 'device': device}
                    if combo not in matrix:
                        matrix.append(combo)
        
        elif platforms and not devices:
            # Platform only: create platform entries without device
            for platform in platforms:
                combo = {'platform': platform, 'device': None}
                if combo not in matrix:
                    matrix.append(combo)
        
        elif devices and not platforms:
            # Device only: mark for expansion (will be expanded by PowerShell script)
            for device in devices:
                combo = {'platform': None, 'device': device}
                if combo not in matrix:
                    matrix.append(combo)
    
    return matrix


def main():
    parser = argparse.ArgumentParser(
        description='Parse pytest markers from test files for intelligent agent routing'
    )
    parser.add_argument(
        '--suite-path',
        required=True,
        help='Path to test suite directory or individual test file'
    )
    parser.add_argument(
        '--output',
        default='marker-requirements.json',
        help='Output JSON file path (default: marker-requirements.json)'
    )
    parser.add_argument(
        '--specific-files',
        type=str,
        default='',
        help='Comma-separated list of specific test files to parse (filenames only)'
    )
    parser.add_argument(
        '--testrail-cases',
        type=str,
        default='',
        help='Comma-separated list of TestRail case IDs to filter tests (e.g., "C12345,C12346")'
    )
    
    args = parser.parse_args()
    
    # Convert to Path object
    suite_path = Path(args.suite_path)
    
    # Find all test files
    print(f"Scanning for test files in: {suite_path}")
    try:
        test_files = find_test_files(suite_path)
        print(f"Found {len(test_files)} test files")
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Filter to specific files if provided
    if args.specific_files:
        specific_files_list = [f.strip() for f in args.specific_files.split(',')]
        test_files = [f for f in test_files if f.name in specific_files_list]
        print(f"Filtering to specific files: {specific_files_list}")
        print(f"Matched {len(test_files)} file(s): {[f.name for f in test_files]}")
    
    # Validate at least one test file was found
    if not test_files:
        print(f"ERROR: No test files found in {suite_path}", file=sys.stderr)
        if args.specific_files:
            print(f"No files matched the specific filter: {args.specific_files}", file=sys.stderr)
        print("Suite path must be a directory containing test_*.py files or a test_*.py file", file=sys.stderr)
        sys.exit(1)
    
    # Parse all test files
    all_requirements = []
    all_test_cases = []
    all_skipped_test_cases = []
    all_errors = []
    
    for test_file in test_files:
        print(f"  Parsing: {test_file.relative_to(suite_path)}")
        requirements, test_cases, skipped_test_cases, errors = parse_test_file(test_file)
        all_requirements.extend(requirements)
        all_test_cases.extend(test_cases)
        all_skipped_test_cases.extend(skipped_test_cases)
        all_errors.extend(errors)
    
    # Filter by TestRail case IDs if provided
    if args.testrail_cases:
        testrail_case_ids = {case_id.strip() for case_id in args.testrail_cases.split(',')}
        print(f"\nFiltering tests by {len(testrail_case_ids)} TestRail case IDs...")
        print(f"  Case IDs: {sorted(testrail_case_ids)}")
        
        # Filter test cases
        original_count = len(all_test_cases)
        all_test_cases = filter_test_cases_by_testrail(all_test_cases, testrail_case_ids)
        filtered_count = len(all_test_cases)
        
        print(f"  Filtered: {original_count} tests -> {filtered_count} tests")
        
        # Validate that we have tests after filtering
        if not all_test_cases:
            print("\nERROR: No tests match the provided TestRail case IDs", file=sys.stderr)
            print(f"  TestRail filter: {sorted(testrail_case_ids)}", file=sys.stderr)
            print("  This indicates none of the tests have matching @pytest.mark.testrail() markers", file=sys.stderr)
            sys.exit(1)
        
        # Regenerate requirements from filtered test cases
        all_requirements = []
        for test_case in all_test_cases:
            if test_case['platforms'] or test_case['devices']:
                requirement = {
                    'platforms': test_case['platforms'],
                    'devices': test_case['devices']
                }
                if requirement not in all_requirements:
                    all_requirements.append(requirement)
        
        print(f"  Regenerated {len(all_requirements)} unique requirements after filtering")

    if all_skipped_test_cases:
        print("\n" + "="*80)
        print("NON-RUNNABLE TESTS EXCLUDED FROM MATRIX")
        print("="*80)
        for i, skipped_test in enumerate(all_skipped_test_cases, 1):
            file_name = Path(skipped_test['file']).name
            class_name = skipped_test['class'] or '<module>'
            method_name = skipped_test['method']
            skip_source = skipped_test.get('skip_source', 'method')
            skip_reason = skipped_test.get('skip_reason', 'skip')
            print(f"{i}. {file_name}::{class_name}::{method_name} ({skip_reason} marker on {skip_source})")
        print("="*80)
        print(f"Excluded non-runnable tests: {len(all_skipped_test_cases)}")
    
    # Check if we have valid test cases
    if not all_test_cases:
        print("\n" + "="*80)
        print("##[warning]No valid test cases found")
        print("="*80)
        if args.testrail_cases:
            print(f"TestRail filter was applied but no tests matched")
        if args.specific_files:
            print(f"Specific files filter was applied but no tests matched")
        print("No tests available to run - subsequent test execution will be skipped")
        print("="*80)
        
        # Write empty output to indicate no tests found
        output_data = {
            'requirements': [],
            'test_cases': [],
            'skipped_test_cases': all_skipped_test_cases,
            'summary': {
                'total_files': len(test_files),
                'total_test_cases': 0,
                'skipped_test_cases': len(all_skipped_test_cases),
                'total_requirements': 0,
                'unique_combinations': 0
            }
        }
        
        output_path = Path(args.output)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2)
        
        print(f"\nEmpty output written to: {output_path}")
        print("##vso[task.setvariable variable=foundTests;isOutput=true]false")
        return 0
    
    # Check for validation warnings
    has_warnings = False
    if all_errors:
        print("\n" + "="*80)
        print("##[warning]VALIDATION WARNING: Missing required markers")
        print("="*80)
        for error in all_errors:
            print(f"\n{error}")
        print("\n" + "="*80)
        print(f"##[warning]Total warnings: {len(all_errors)}")
        print("="*80)
        print("\nCONTINUING with tests that have valid markers")
        print("Tests without markers will be skipped\n")
        has_warnings = True
    
    # List all tests with valid markers
    print("\n" + "="*80)
    print(f"TESTS WITH VALID MARKERS: {len(all_test_cases)}")
    print("="*80)
    for i, test_case in enumerate(all_test_cases, 1):
        file_name = Path(test_case['file']).name
        class_name = test_case['class'] or '<module>'
        method_name = test_case['method']
        platforms = ', '.join(test_case['platforms']) if test_case['platforms'] else '<ALL>'
        devices = ', '.join(test_case['devices']) if test_case['devices'] else '<NONE>'
        
        print(f"\n{i}. {file_name}::{class_name}::{method_name}")
        print(f"   Platforms: {platforms}")
        print(f"   Devices: {devices}")
    print("\n" + "="*80 + "\n")
    
    # Generate matrix requirements
    matrix = generate_matrix_requirements(all_requirements)
    print(f"Generated {len(matrix)} unique platform×device combinations")
    
    # Validate matrix is not empty
    if not matrix:
        print("\nERROR: No platform×device combinations generated", file=sys.stderr)
        print("This indicates no valid markers were found in the test files", file=sys.stderr)
        sys.exit(1)
    
    # Write output
    output_data = {
        'requirements': matrix,
        'test_cases': all_test_cases,
        'skipped_test_cases': all_skipped_test_cases,
        'summary': {
            'total_files': len(test_files),
            'total_test_cases': len(all_test_cases),
            'skipped_test_cases': len(all_skipped_test_cases),
            'total_requirements': len(all_requirements),
            'unique_combinations': len(matrix)
        }
    }
    
    output_path = Path(args.output)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"\nOutput written to: {output_path}")
    print("\nSummary:")
    for combo in matrix:
        platform = combo['platform'] or '<ALL_PLATFORMS>'
        device = combo['device'] or '<NO_DEVICE>'
        print(f"  - Platform: {platform}, Device: {device}")
    
    if has_warnings:
        print(f"\n##[warning]{len(all_errors)} test(s) missing markers (will be skipped)")
        print("Continuing with tests that have valid markers")
    else:
        print("\nAll tests have required markers")

    if all_skipped_test_cases:
        print(f"\n##[warning]{len(all_skipped_test_cases)} test(s) excluded due to @pytest.mark.skip/skipif or @pytest.mark.xfail(run=False)")
        print("These non-runnable tests are intentionally excluded from matrix generation")
    
    # Set output variable to indicate tests were found
    print("##vso[task.setvariable variable=foundTests;isOutput=true]true")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
