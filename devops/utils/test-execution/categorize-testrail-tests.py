"""
Categorize TestRail test cases by suite directory.

This script fetches test cases from a TestRail run and categorizes them by which
test suite directory they belong to (pen_control, audio, smart_displays, etc.).
It does this by checking which directories contain tests with matching TestRail markers.

Usage:
    python categorize-testrail-tests.py --run-id <run_id> --base-path <path>

Environment Variables:
    TESTRAIL_URL: TestRail instance URL
    TESTRAIL_USER_NAME: TestRail username
    TESTRAIL_API_KEY: TestRail API key

Output:
    JSON object with format:
    {
        "run_id": 12345,
        "total_cases": 50,
        "suites": {
            "pen_control": {
                "count": 30,
                "case_ids": ["C12345", "C12346", ...]
            },
            "audio": {
                "count": 15,
                "case_ids": ["C12347", ...]
            },
            "smart_displays": {
                "count": 5,
                "case_ids": ["C12348", ...]
            }
        }
    }
"""

import argparse
import ast
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Set

# Add the project root to the path to import from libs
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, project_root)

from libs.testrail.testrail_api import TestRailAPI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def validate_environment():
    """Validate that all required environment variables are set."""
    testrail_url = os.environ.get('TESTRAIL_URL')
    username = os.environ.get('TESTRAIL_USER_NAME')
    api_key = os.environ.get('TESTRAIL_API_KEY')
    
    missing_vars = []
    if not testrail_url:
        missing_vars.append('TESTRAIL_URL')
    if not username:
        missing_vars.append('TESTRAIL_USER_NAME')
    if not api_key:
        missing_vars.append('TESTRAIL_API_KEY')
    
    if missing_vars:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing_vars)}"
        )
    
    return testrail_url, username, api_key


def extract_testrail_case_id(marker_value: str) -> str:
    """Extract TestRail case ID from marker value (handles C12345 or S177594:C12345)."""
    if not marker_value:
        return None
    
    match = re.search(r'(?:S\d+:)?(C\d+)', marker_value)
    if match:
        return match.group(1)
    
    return None


def find_testrail_markers_in_file(file_path: Path) -> Set[str]:
    """Find all TestRail case IDs in a Python test file."""
    case_ids = set()
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read(), filename=str(file_path))
        
        for node in ast.walk(tree):
            if not hasattr(node, 'decorator_list'):
                continue
                
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Call):
                    # Check if it's @pytest.mark.testrail()
                    if isinstance(decorator.func, ast.Attribute):
                        if (isinstance(decorator.func.value, ast.Attribute) and
                            isinstance(decorator.func.value.value, ast.Name) and
                            decorator.func.value.value.id == 'pytest' and
                            decorator.func.value.attr == 'mark' and
                            decorator.func.attr == 'testrail'):
                            
                            # Extract case ID from argument
                            for arg in decorator.args:
                                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                                    case_id = extract_testrail_case_id(arg.value)
                                    if case_id:
                                        case_ids.add(case_id)
        
    except Exception as e:
        logger.warning(f"Failed to parse {file_path}: {e}")
    
    return case_ids


def categorize_cases_by_suite(case_ids: List[str], base_path: Path) -> Dict[str, Dict]:
    """
    Categorize case IDs by which test suite directory they belong to.
    
    Args:
        case_ids: List of TestRail case IDs (e.g., ["C12345", "C12346"])
        base_path: Base path to test suites (e.g., tests/hp_app)
    
    Returns:
        Dictionary mapping suite names to their case IDs and counts
    """
    case_ids_set = set(case_ids)
    suites = {}
    
    # Find all test suite directories
    if not base_path.exists():
        logger.error(f"Base path does not exist: {base_path}")
        return suites
    
    for suite_dir in base_path.iterdir():
        if not suite_dir.is_dir() or suite_dir.name.startswith('_'):
            continue
        
        suite_name = suite_dir.name
        suite_cases = set()
        
        # Find all test files in this suite
        test_files = list(suite_dir.rglob('test_*.py'))
        
        for test_file in test_files:
            # Get all TestRail markers from this file
            file_cases = find_testrail_markers_in_file(test_file)
            
            # Check which ones match our TestRail run
            matching_cases = file_cases.intersection(case_ids_set)
            suite_cases.update(matching_cases)
        
        if suite_cases:
            suites[suite_name] = {
                'count': len(suite_cases),
                'case_ids': sorted(list(suite_cases))
            }
            logger.info(f"Suite '{suite_name}': {len(suite_cases)} test cases")
    
    return suites


def main():
    parser = argparse.ArgumentParser(
        description='Categorize TestRail test cases by suite directory'
    )
    parser.add_argument(
        '--run-id',
        type=int,
        required=True,
        help='TestRail run ID'
    )
    parser.add_argument(
        '--base-path',
        type=str,
        required=True,
        help='Base path to test suites (e.g., tests/hp_app)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='testrail-suite-categorization.json',
        help='Output JSON file path'
    )
    
    args = parser.parse_args()
    
    try:
        # Validate environment
        testrail_url, username, api_key = validate_environment()
        
        # Initialize TestRail API client
        testrail_api = TestRailAPI(
            username=username,
            api_key=api_key,
            base_url=testrail_url
        )
        logger.info(f"Connected to TestRail instance: {testrail_url}")
        
        # Fetch tests from the run
        logger.info(f"Fetching tests from TestRail run ID: {args.run_id}")
        tests = testrail_api.get_tests(args.run_id)
        logger.info(f"Retrieved {len(tests)} tests from run {args.run_id}")
        
        if not tests:
            logger.warning(f"TestRail run {args.run_id} is empty or does not exist")
            result = {
                'run_id': args.run_id,
                'total_cases': 0,
                'suites': {}
            }
        else:
            # Extract case IDs
            case_ids = []
            for test in tests:
                case_id = test.get('case_id')
                if case_id:
                    case_ids.append(f"C{case_id}")
            
            logger.info(f"Extracted {len(case_ids)} case IDs")
            
            # Categorize by suite
            base_path = Path(args.base_path)
            logger.info(f"Categorizing tests by suite in: {base_path}")
            suites = categorize_cases_by_suite(case_ids, base_path)
            
            result = {
                'run_id': args.run_id,
                'total_cases': len(case_ids),
                'suites': suites
            }
        
        # Write output
        output_path = args.output
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2)
        
        logger.info(f"Output written to: {output_path}")
        
        # Print summary
        print(json.dumps(result, indent=2))
        
        # Set ADO output variables for each suite
        for suite_name, suite_data in result['suites'].items():
            var_name = f"{suite_name}TestCount"
            var_value = suite_data['count']
            print(f"##vso[task.setvariable variable={var_name};isOutput=true]{var_value}")
            logger.info(f"Set output variable: {var_name}={var_value}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
