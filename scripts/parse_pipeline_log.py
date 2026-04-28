#!/usr/bin/env python3
"""
Pipeline Log Beautifier
Transforms Azure DevOps pipeline logs into human-readable summaries
Organized by test suite with categorized skip reasons
"""

import re
from collections import defaultdict
from pathlib import Path
import sys


def parse_pipeline_log(log_file):
    """Parse Azure DevOps pipeline log and extract key information"""
    
    with open(log_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Initialize data structures
    data = {
        'filter_applied': None,
        'test_stats': {},
        'agent_info': {},
        'matched_combinations': [],
        'skipped_combinations': [],
        'executable_tests': [],
        'non_executable_tests': [],
        'excluded_tests': []
    }
    
    # Extract filter information
    filter_match = re.search(r'Applying additional marker filter: (.+)', content)
    if filter_match:
        data['filter_applied'] = filter_match.group(1).strip()
    
    # Extract excluded tests
    excluded_pattern = r'Excluding test: ([\w_]+) \(has \'(\w+)\' marker\)'
    for match in re.finditer(excluded_pattern, content):
        data['excluded_tests'].append({
            'name': match.group(1).strip(),
            'reason': f"has '{match.group(2)}' marker"
        })
    
    # Extract test statistics
    test_stats_patterns = {
        'total_tests': r'Found (\d+) test cases',
        'filtered_tests': r'Filtered test cases: (\d+)',
        'excluded_tests_count': r'excluded: (\d+)',
        'total_agents': r'Found (\d+) agents in pool',
        'valid_combinations': r'Valid combinations \(will execute\): (\d+)',
        'skipped_combinations': r'Skipped combinations \(no agent\): (\d+)',
        'executable_tests': r'Will execute: (\d+)',
        'non_executable_tests': r'Will NOT execute: (\d+)'
    }
    
    for key, pattern in test_stats_patterns.items():
        match = re.search(pattern, content)
        if match:
            data['test_stats'][key] = int(match.group(1))
    
    # Extract agent information
    agent_pattern = r'Agent: (\w+)\s+\|\s+Platform: ([^\|]*)\|\s+Devices: ([^\|]+)\|\s+Status: (\w+)'
    for match in re.finditer(agent_pattern, content):
        agent_name = match.group(1).strip()
        platform = match.group(2).strip()
        devices = match.group(3).strip()
        status = match.group(4).strip()
        
        data['agent_info'][agent_name] = {
            'platform': platform,
            'devices': devices,
            'status': status
        }
    
    # Extract matched combinations
    matched_section = re.search(
        r'\[VALID COMBINATIONS\].*?-{80}(.*?)\[SKIPPED COMBINATIONS\]',
        content,
        re.DOTALL
    )
    if matched_section:
        match_pattern = r'Platform: (\w+)\s+\|\s+Device: ([^\n]+)\n\s+-> Agent: (\w+)'
        for match in re.finditer(match_pattern, matched_section.group(1)):
            data['matched_combinations'].append({
                'platform': match.group(1).strip(),
                'device': match.group(2).strip().replace('<none>', 'None'),
                'agent': match.group(3).strip()
            })
    
    # Extract skipped combinations with details
    skipped_section = re.search(
        r'\[SKIPPED COMBINATIONS\](.*?)ACTION REQUIRED',
        content,
        re.DOTALL
    )
    if skipped_section:
        skip_blocks = re.finditer(
            r'Platform: ([\w]+)\s+\|\s+Device: ([\w]+)\s+REASON: No enabled agent found',
            skipped_section.group(1)
        )
        for match in skip_blocks:
            platform = match.group(1).strip()
            device = match.group(2).strip()
            data['skipped_combinations'].append({
                'platform': platform,
                'device': device
            })
    
    # Extract executable tests
    exec_tests_section = re.search(
        r'\[TESTS THAT WILL EXECUTE\](.*?)\[TESTS THAT WILL NOT EXECUTE\]',
        content,
        re.DOTALL
    )
    if exec_tests_section:
        test_pattern = r'(\w+)::(test_\w+)\s+File: ([^\n]+)\s+Platforms: ([^\|]+)\|'
        for match in re.finditer(test_pattern, exec_tests_section.group(1)):
            data['executable_tests'].append({
                'suite': match.group(1).strip(),
                'name': match.group(2).strip(),
                'file': match.group(3).strip(),
                'platforms': match.group(4).strip()
            })
    
    # Extract non-executable tests with full details
    non_exec_section = re.search(
        r'\[TESTS THAT WILL NOT EXECUTE\](.*?)TEST EXECUTION SUMMARY',
        content,
        re.DOTALL
    )
    if non_exec_section:
        test_pattern = r'(\w+)::(test_\w+)\s+File: ([^\n]+)\s+Platforms: ([^\|]+)\|\s+Devices: ([^\n]+)\s+REASON:'
        for match in re.finditer(test_pattern, non_exec_section.group(1)):
            suite = match.group(1).strip()
            test_name = match.group(2).strip()
            file_path = match.group(3).strip()
            platforms = match.group(4).strip()
            devices = match.group(5).strip()
            
            data['non_executable_tests'].append({
                'suite': suite,
                'name': test_name,
                'file': file_path,
                'platforms': platforms,
                'devices': devices
            })
    
    return data


def categorize_skip_reason(test, agent_info):
    """Determine the specific reason a test was skipped"""
    devices = test['devices'].strip()
    platforms = [p.strip() for p in test['platforms'].split(',')]
    
    # Check if it's a device issue or platform issue
    platform_exists = any(
        any(agent['platform'].lower() == p.lower() for agent in agent_info.values())
        for p in platforms
    )
    
    if not platform_exists:
        return 'missing_platform', f"No agents exist for platform(s): {test['platforms']}"
    
    if devices and devices != '<none>':
        return 'missing_device', f"Platform exists but missing '{devices}' device capability"
    
    return 'other', "No compatible agent available"


def print_beautified_report(data):
    """Print a beautified report from parsed data"""
    
    print("=" * 100)
    print("PIPELINE EXECUTION REPORT".center(100))
    print("=" * 100)
    print()
    
    # Execution Overview
    print("EXECUTION OVERVIEW")
    print("-" * 100)
    stats = data['test_stats']
    
    if data['filter_applied']:
        print(f"  Pipeline Filter Applied        : \"{data['filter_applied']}\"")
    print(f"  Tests Found                    : {stats.get('total_tests', 'N/A')}")
    print(f"  Tests Excluded by Filter       : {stats.get('excluded_tests_count', 'N/A')} (all have '{data['filter_applied'].replace('not ', '')}' marker)")
    print(f"  Tests After Filtering          : {stats.get('filtered_tests', 'N/A')}")
    print()
    
    exec_count = stats.get('executable_tests', 0)
    filtered_count = stats.get('filtered_tests', 1)
    exec_rate = (exec_count / filtered_count * 100) if filtered_count > 0 else 0
    
    print(f"  Tests That WILL Execute        : {exec_count}  [PASS] ({exec_rate:.1f}%)")
    print(f"  Tests That WON'T Execute       : {stats.get('non_executable_tests', 'N/A')} [FAIL] ({100-exec_rate:.1f}%)")
    print()
    
    # Agent & Device Availability
    print("AGENT & DEVICE AVAILABILITY")
    print("-" * 100)
    online_count = sum(1 for a in data['agent_info'].values() if a['status'] == 'online')
    offline_count = sum(1 for a in data['agent_info'].values() if a['status'] == 'offline')
    offline_agents = [name for name, info in data['agent_info'].items() if info['status'] == 'offline']
    
    print(f"  Total Agents in Pool           : {stats.get('total_agents', 'N/A')}")
    print(f"  Online & Enabled               : {online_count} agents")
    if offline_agents:
        print(f"  Offline                        : {offline_count} agents ({', '.join(offline_agents)})")
    print()
    print(f"  Platform×Device Combos Needed  : {stats.get('skipped_combinations', 0) + stats.get('valid_combinations', 0)}")
    print(f"  Matched (Available)            : {stats.get('valid_combinations', 0)}  [PASS]")
    print(f"  Skipped (No Agent/Device)      : {stats.get('skipped_combinations', 0)} [WARNING]")
    print()
    
    # Tests that won't execute - organized by suite
    print("=" * 100)
    print("TESTS THAT WON'T EXECUTE - ORGANIZED BY TEST SUITE & SKIP REASON")
    print("=" * 100)
    print()
    
    # Group tests by suite
    tests_by_suite = defaultdict(list)
    for test in data['non_executable_tests']:
        tests_by_suite[test['suite']].append(test)
    
    # Process each suite
    for suite_name in sorted(tests_by_suite.keys()):
        tests = tests_by_suite[suite_name]
        
        # Get file name from first test
        file_name = tests[0]['file'].split('\\')[-1] if tests else ''
        
        print("+" + "-" * 98 + "+")
        print(f"| Test Suite: {suite_name:<84} |")
        print(f"| File: {file_name:<90} |")
        print(f"| Tests in Suite: {len(tests)} tests{' ' * (71 - len(str(len(tests))))} |")
        print("+" + "-" * 98 + "+")
        print()
        
        # Categorize tests within suite
        categorized = defaultdict(list)
        for test in tests:
            category, reason = categorize_skip_reason(test, data['agent_info'])
            categorized[category].append((test, reason))
        
        # Print by category
        for category in ['missing_device', 'missing_platform', 'other']:
            if category not in categorized:
                continue
            
            tests_in_category = categorized[category]
            
            if category == 'missing_device':
                # Group by device type
                device_groups = defaultdict(list)
                for test, reason in tests_in_category:
                    device = test['devices'].strip()
                    device_groups[device].append((test, reason))
                
                for device, device_tests in device_groups.items():
                    if len(device_tests) == len(tests):
                        print(f"  SKIP REASON: Missing Device Capability - All {len(tests)} tests require '{device}' device")
                    else:
                        print(f"  SKIP REASON: Missing Device Capability ({len(device_tests)} tests)")
                    print("  " + "-" * 96)
                    
                    for test, reason in device_tests:
                        print(f"    [X] {test['name']}")
                    
                    # Show details for first test
                    first_test = device_tests[0][0]
                    print()
                    print(f"    Required: {first_test['platforms']} platform WITH '{device}' device")
                    print(f"    Problem:  Agents exist but lack '{device}' device capability")
                    print()
            
            elif category == 'missing_platform':
                print(f"  SKIP REASON: Missing Platform or Platform/Device Combo ({len(tests_in_category)} tests)")
                print("  " + "-" * 96)
                for test, reason in tests_in_category:
                    print(f"    [X] {test['name']}")
                    print(f"       Required: {test['platforms']} platform WITH '{test['devices']}' device")
                    print(f"       Problem:  {reason}")
                print()
            
            else:  # other
                print(f"  SKIP REASON: Other ({len(tests_in_category)} tests)")
                print("  " + "-" * 96)
                for test, reason in tests_in_category:
                    print(f"    [X] {test['name']}")
                print()
        
        print()
    
    # Skip Reason Summary
    print("=" * 100)
    print("SKIP REASON SUMMARY")
    print("=" * 100)
    print()
    
    excluded_count = len(data['excluded_tests'])
    if excluded_count > 0:
        print(f"  {excluded_count} tests [X] Excluded by Filter: \"{data['filter_applied']}\"")
        print(f"     -> All these tests have the '{data['filter_applied'].replace('not ', '')}' marker")
        print()
    
    # Count by category
    missing_device_count = 0
    missing_platform_count = 0
    
    for test in data['non_executable_tests']:
        category, _ = categorize_skip_reason(test, data['agent_info'])
        if category == 'missing_device':
            missing_device_count += 1
        elif category == 'missing_platform':
            missing_platform_count += 1
    
    if missing_device_count > 0:
        print(f"  {missing_device_count} tests [X] Missing Device Capability")
        print(f"     -> Platforms exist but agents lack required device (trio, roo, moonracer)")
        print(f"     -> SOLUTION: Add device capabilities to existing agents")
        print()
    
    if missing_platform_count > 0:
        print(f"  {missing_platform_count} tests [X] Missing Platform or Platform/Device Combo")
        print(f"     -> No agents exist for required platform")
        print(f"     -> SOLUTION: Add agents for missing platforms or fix platform names")
        print()
    
    exec_count = stats.get('executable_tests', 0)
    if exec_count > 0:
        print(f"  {exec_count} tests [PASS] Will Execute")
        print(f"     -> Platform and device requirements fully satisfied")
        print()
    
    # Recommended Actions
    print("=" * 100)
    print("RECOMMENDED ACTIONS TO INCREASE TEST COVERAGE")
    print("=" * 100)
    print()
    
    if missing_device_count > 0:
        print(f"  1. ADD DEVICE CAPABILITIES (Would enable {missing_device_count} tests):")
        print("     " + "-" * 93)
        
        # Analyze which devices are needed
        device_needs = defaultdict(set)
        for test in data['non_executable_tests']:
            category, _ = categorize_skip_reason(test, data['agent_info'])
            if category == 'missing_device':
                device = test['devices'].strip()
                platforms = [p.strip() for p in test['platforms'].split(',')]
                for platform in platforms:
                    # Find agents with this platform
                    for agent_name, agent_info in data['agent_info'].items():
                        if agent_info['platform'].lower() == platform.lower() and agent_info['status'] == 'online':
                            device_needs[device].add(agent_name)
        
        for device, agents in sorted(device_needs.items()):
            agent_list = ', '.join(sorted(agents)[:8])  # Limit display
            if len(agents) > 8:
                agent_list += f", ... and {len(agents) - 8} more"
            print(f"     Add '{device}' to:    {agent_list}")
        print()
    
    if missing_platform_count > 0:
        print(f"  2. FIX PLATFORM NAMING OR ADD MISSING PLATFORMS (Would enable {missing_platform_count} tests):")
        print("     " + "-" * 93)
        
        # Find missing platforms
        missing_platforms = set()
        for test in data['non_executable_tests']:
            category, _ = categorize_skip_reason(test, data['agent_info'])
            if category == 'missing_platform':
                platforms = [p.strip() for p in test['platforms'].split(',')]
                for platform in platforms:
                    # Check if this platform exists
                    exists = any(
                        agent['platform'].lower() == platform.lower()
                        for agent in data['agent_info'].values()
                    )
                    if not exists:
                        missing_platforms.add(platform)
        
        for platform in sorted(missing_platforms):
            print(f"     Add agent for '{platform}' platform OR update test to use existing platform")
        print()
    
    print("=" * 100)


if __name__ == '__main__':
    log_file = sys.argv[1] if len(sys.argv) > 1 else 'Error.txt'
    
    print(f"\nParsing log file: {log_file}\n")
    data = parse_pipeline_log(log_file)
    print_beautified_report(data)
