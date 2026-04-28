"""
Script to fetch test case IDs from a TestRail test run.

This script queries the TestRail API to retrieve all test cases associated with
a specific test run ID. It outputs the case IDs in a JSON format that can be
consumed by downstream pipeline steps for test filtering.

Usage:
    python get-testrail-tests.py --run-id <run_id>

Environment Variables:
    TESTRAIL_URL: TestRail instance URL
    TESTRAIL_USER_NAME: TestRail username
    TESTRAIL_API_KEY: TestRail API key

Output:
    JSON object with format:
    {
        "run_id": 12345,
        "case_ids": ["C12345", "C12346", ...],
        "count": 2
    }

Exit Codes:
    0: Success
    1: Error (missing env vars, invalid run ID, API error, empty run)
"""

import argparse
import json
import logging
import os
import sys

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
    """
    Validate that all required environment variables are set.
    
    Returns:
        tuple: (testrail_url, username, api_key)
        
    Raises:
        ValueError: If any required environment variable is missing
    """
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


def fetch_testrail_tests(run_id):
    """
    Fetch test case IDs from a TestRail run.
    
    Args:
        run_id (int): TestRail run ID
        
    Returns:
        dict: Dictionary with run_id, case_ids list, and count
        
    Raises:
        ValueError: If run_id is invalid or run is empty
        Exception: If API call fails
    """
    logger.info(f"Fetching test cases from TestRail run ID: {run_id}")
    
    # Validate environment variables
    try:
        testrail_url, username, api_key = validate_environment()
    except ValueError as e:
        logger.error(f"Environment validation failed: {e}")
        raise
    
    # Initialize TestRail API client
    try:
        testrail_api = TestRailAPI(
            url=testrail_url,
            username=username,
            api_key=api_key
        )
        logger.info(f"Connected to TestRail instance: {testrail_url}")
    except Exception as e:
        logger.error(f"Failed to initialize TestRail API client: {e}")
        raise
    
    # Fetch tests from the run
    try:
        tests = testrail_api.get_tests(run_id)
        logger.info(f"Retrieved {len(tests)} tests from run {run_id}")
    except Exception as e:
        logger.error(f"Failed to fetch tests from TestRail run {run_id}: {e}")
        raise
    
    # Validate that we got tests back
    if not tests:
        error_msg = f"TestRail run {run_id} is empty or does not exist"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    # Extract case IDs from the tests
    case_ids = []
    for test in tests:
        case_id = test.get('case_id')
        if case_id:
            # Format as "C12345" to match pytest marker format
            case_ids.append(f"C{case_id}")
        else:
            logger.warning(f"Test {test.get('id')} has no case_id, skipping")
    
    if not case_ids:
        error_msg = f"No valid case IDs found in TestRail run {run_id}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    logger.info(f"Extracted {len(case_ids)} case IDs: {case_ids[:10]}{'...' if len(case_ids) > 10 else ''}")
    
    return {
        'run_id': run_id,
        'case_ids': case_ids,
        'count': len(case_ids)
    }


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description='Fetch test case IDs from a TestRail test run'
    )
    parser.add_argument(
        '--run-id',
        type=int,
        required=True,
        help='TestRail run ID'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='testrail-cases.json',
        help='Output JSON file path (default: testrail-cases.json)'
    )
    
    args = parser.parse_args()
    
    try:
        # Fetch the test case IDs
        result = fetch_testrail_tests(args.run_id)
        
        # Write to output file
        output_path = args.output
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2)
        
        logger.info(f"Output written to: {output_path}")
        
        # Also print to stdout for visibility
        print(json.dumps(result, indent=2))
        
        logger.info("Successfully fetched TestRail test cases")
        return 0
        
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
