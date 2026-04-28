"""
Lookup Test Targets - Azure DevOps Agent Query Tool

Finds all agents matching platform/device criteria with comma-separated list support.
Designed for test execution pipelines to identify target agents.

Usage:
    python lookup-test-targets-by-platform-and-device.py --platform <platforms> --device <devices>

Examples:
    # Single platform and device
    python lookup-test-targets-by-platform-and-device.py --platform MasadaN --device roo

    # Multiple platforms (OR logic)
    python lookup-test-targets-by-platform-and-device.py --platform "MasadaN,CashmereXI,Machu13x"

    # Multiple devices (OR logic)
    python lookup-test-targets-by-platform-and-device.py --device "roo,trio"

    # Combined filters (platform1 OR platform2) AND (device1 OR device2)
    python lookup-test-targets-by-platform-and-device.py --platform "MasadaN,CashmereXI" --device "roo,trio"

    # JSON output for pipeline integration
    python lookup-test-targets-by-platform-and-device.py --platform MasadaN --device roo --json
"""

import os
import sys
import base64
import json
import argparse
import requests
from typing import Dict, List, Any, Optional

class TestTargetLookup:
    """Handle Azure DevOps agent queries for test target identification."""

    def __init__(self, organization: str, pool_name: str, api_version: str = "6.0"):
        """
        Initialize test target lookup.

        Args:
            organization: Azure DevOps organization name
            pool_name: Agent pool name
            api_version: Azure DevOps API version
        """
        self.organization = organization
        self.pool_name = pool_name
        self.api_version = api_version
        self.headers = self._get_auth_headers()
        self.pool_id = None

    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers from environment variable."""
        pat = os.environ.get('AZUREDEVOPSPAT')

        if not pat:
            print("ERROR: AZUREDEVOPSPAT environment variable not set", file=sys.stderr)
            print("Set the environment variable with your Azure DevOps Personal Access Token", file=sys.stderr)
            sys.exit(1)

        encoded_pat = base64.b64encode(f":{pat}".encode('ascii')).decode('ascii')

        return {
            'Authorization': f'Basic {encoded_pat}',
            'Content-Type': 'application/json'
        }

    def _get_pool_id(self) -> int:
        """Get pool ID from pool name."""
        if self.pool_id:
            return self.pool_id

        pools_url = f"https://dev.azure.com/{self.organization}/_apis/distributedtask/pools?api-version={self.api_version}"

        try:
            response = requests.get(pools_url, headers=self.headers, timeout=30)
            response.raise_for_status()
            pools = response.json().get('value', [])

            pool = next((p for p in pools if p.get('name') == self.pool_name), None)

            if not pool:
                available = ', '.join([p.get('name', '') for p in pools])
                print(f"ERROR: Pool '{self.pool_name}' not found", file=sys.stderr)
                print(f"Available pools: {available}", file=sys.stderr)
                sys.exit(1)

            self.pool_id = pool.get('id')
            return self.pool_id

        except requests.exceptions.RequestException as e:
            print(f"ERROR: Failed to query pools: {e}", file=sys.stderr)
            sys.exit(1)

    def _get_all_agents(self) -> List[Dict[str, Any]]:
        """
        Get all agents from the pool with their capabilities.

        Returns:
            List of processed agent dictionaries
        """
        pool_id = self._get_pool_id()
        agents_url = (f"https://dev.azure.com/{self.organization}/_apis/distributedtask/pools/"
                      f"{pool_id}/agents?includeCapabilities=true&api-version={self.api_version}")

        try:
            response = requests.get(agents_url, headers=self.headers, timeout=30)
            response.raise_for_status()
            agents = response.json().get('value', [])

            return [self._process_agent(agent) for agent in agents]

        except requests.exceptions.RequestException as e:
            print(f"ERROR: Failed to query agents: {e}", file=sys.stderr)
            sys.exit(1)

    def _process_agent(self, agent: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process agent data to extract platform and device capabilities.

        Args:
            agent: Raw agent dictionary from API

        Returns:
            Processed agent dictionary
        """
        system_caps = agent.get('systemCapabilities', {})
        user_caps = agent.get('userCapabilities', {})

        # Extract platform (preserve original casing)
        platform = system_caps.get('Platform') or user_caps.get('Platform')

        # Extract devices (boolean capabilities set to 'true')
        # Exclude interactiveSession as it's not a real device
        devices = []
        all_caps = {**system_caps, **user_caps}

        for cap_name, cap_value in all_caps.items():
            if cap_name != 'Platform' and str(cap_value).lower() == 'true':
                device_name = cap_name.lower()
                # Skip interactiveSession (not a physical device)
                if device_name != 'interactivesession':
                    devices.append(device_name)

        return {
            'name': agent.get('name'),
            'id': agent.get('id'),
            'platform': platform,
            'platform_lower': platform.lower() if platform else None,
            'devices': sorted(devices),
            'status': agent.get('status'),
            'enabled': agent.get('enabled'),
            'version': agent.get('version'),
        }

    def find_test_targets(
            self,
            platforms: Optional[str] = None,
            devices: Optional[str] = None,
            include_offline: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Find all agents matching the specified platform(s) and/or device(s).

        Args:
            platforms: Comma-separated platform names to match (case-insensitive, optional)
            devices: Comma-separated device names to match (case-insensitive, optional)
            include_offline: Include offline/disabled agents in results

        Returns:
            List of matching agent dictionaries
        """
        # Get all agents
        all_agents = self._get_all_agents()
        matching = all_agents

        # Parse comma-separated lists
        platform_list = [p.strip().lower() for p in platforms.split(',') if p.strip()] if platforms else []
        device_list = [d.strip().lower() for d in devices.split(',') if d.strip()] if devices else []

        # Filter by platforms if specified (OR logic - match ANY platform)
        if platform_list:
            matching = [
                agent for agent in matching
                if agent['platform_lower'] in platform_list
            ]

        # Filter by devices if specified (OR logic - match ANY device)
        if device_list:
            matching = [
                agent for agent in matching
                if any(device in agent['devices'] for device in device_list)
            ]

        # Filter by status if needed
        if not include_offline:
            matching = [
                agent for agent in matching
                if agent['status'] == 'online' and agent['enabled']
            ]

        return matching

def format_results_table(agents: List[Dict[str, Any]]) -> str:
    """Format agent results as a readable table."""
    if not agents:
        return "No matching agents found."

    lines = []
    lines.append("=" * 100)
    lines.append(f"{'Agent Name':<35} {'Platform':<20} {'Devices':<30} {'Status':<10}")
    lines.append("-" * 100)

    for agent in agents:
        device_str = ', '.join(agent['devices']) if agent['devices'] else '<none>'
        platform_str = agent['platform'] or '<none>'

        lines.append(f"{agent['name']:<35} {platform_str:<20} {device_str:<30} {agent['status']:<10}")

    lines.append("=" * 100)

    return '\n'.join(lines)

def format_results_summary(
        agents: List[Dict[str, Any]],
        platform: Optional[str] = None,
        device: Optional[str] = None
) -> str:
    """Format summary of matching agents."""
    lines = []
    lines.append("")
    lines.append("=" * 100)

    # Build filter description
    filters = []
    if platform:
        filters.append(f"platform '{platform}'")
    if device:
        filters.append(f"device '{device}'")
    filter_str = " and ".join(filters) if filters else "all criteria"

    lines.append(f"SUMMARY: Found {len(agents)} test target(s) matching {filter_str}")
    lines.append("=" * 100)

    if not agents:
        return '\n'.join(lines)

    lines.append("")

    # Group by platform×device combination
    combos: Dict[tuple, List[str]] = {}
    for agent in agents:
        plat = agent['platform'] or '<no platform>'
        devs = tuple(agent['devices']) if agent['devices'] else ('<no devices>',)
        key = (plat, devs)

        if key not in combos:
            combos[key] = []
        combos[key].append(agent['name'])

    lines.append("Platform × Device Combinations:")
    for (plat, devs), agent_names in sorted(combos.items()):
        device_str = ', '.join(devs) if devs != ('<no devices>',) else '<no devices>'
        lines.append(f"  {plat} × [{device_str}]")
        for name in sorted(agent_names):
            lines.append(f"    - {name}")
        lines.append("")

    return '\n'.join(lines)

def show_available_platforms(lookup: TestTargetLookup):
    """Show all available platforms in the pool."""
    agents = lookup._get_all_agents()
    platforms = set(agent['platform'] for agent in agents if agent['platform'])

    print("\nAvailable platforms:")
    for platform in sorted(platforms):
        count = sum(1 for a in agents if a['platform'] == platform)
        print(f"  - {platform} ({count} agent(s))")

def show_available_devices(lookup: TestTargetLookup):
    """Show all available devices in the pool."""
    agents = lookup._get_all_agents()
    all_devices = set()
    for agent in agents:
        all_devices.update(agent['devices'])

    print("\nAvailable devices:")
    for device in sorted(all_devices):
        count = sum(1 for a in agents if device in a['devices'])
        platforms = set(a['platform'] for a in agents if device in a['devices'] and a['platform'])
        platform_str = ', '.join(sorted(platforms)[:3])
        if len(platforms) > 3:
            platform_str += f', +{len(platforms) - 3} more'
        print(f"  - {device} ({count} agent(s) across: {platform_str})")

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description='Find Azure DevOps agents matching platform and/or device criteria for test execution',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single filters
  python lookup-test-targets-by-platform-and-device.py --platform MasadaN --device roo

  # Multiple platforms (OR logic)
  python lookup-test-targets-by-platform-and-device.py --platform "MasadaN,CashmereXI,Machu13x"

  # Multiple devices (OR logic)
  python lookup-test-targets-by-platform-and-device.py --device "roo,trio"

  # Combined: (platform1 OR platform2) AND (device1 OR device2)
  python lookup-test-targets-by-platform-and-device.py --platform "MasadaN,CashmereXI" --device "roo,trio"

  # JSON output for pipelines
  python lookup-test-targets-by-platform-and-device.py --platform CashmereXI --device trio --json

  # List available options
  python lookup-test-targets-by-platform-and-device.py --list-platforms
  python lookup-test-targets-by-platform-and-device.py --list-devices
        """
    )

    parser.add_argument('--platform', type=str, default='', help='Platform name(s) to match - comma-separated for multiple (case-insensitive)')
    parser.add_argument('--device', type=str, default='', help='Device name(s) to match - comma-separated for multiple (case-insensitive)')
    parser.add_argument('--organization', default='hpcodeway', help='Azure DevOps organization (default: hpcodeway)')
    parser.add_argument('--pool-name', default='ASQE-QAMA-General', help='Agent pool name (default: ASQE-QAMA-General)')
    parser.add_argument('--json', action='store_true', help='Output results as JSON')
    parser.add_argument('--json-output-file', type=str, default='', help='Save JSON output to file (for pipeline integration)')
    parser.add_argument('--show-offline', action='store_true', help='Include offline/disabled agents')
    parser.add_argument('--list-platforms', action='store_true', help='List all available platforms')
    parser.add_argument('--list-devices', action='store_true', help='List all available devices')
    parser.add_argument('--api-version', default='6.0', help='Azure DevOps API version (default: 6.0)')

    args = parser.parse_args()

    # Initialize lookup
    lookup = TestTargetLookup(args.organization, args.pool_name, args.api_version)

    # Handle list operations
    if args.list_platforms:
        show_available_platforms(lookup)
        return

    if args.list_devices:
        show_available_devices(lookup)
        return

    # At least one filter is required for searching
    if not args.platform and not args.device:
        parser.error('At least one of --platform or --device is required (or use --list-platforms / --list-devices)')

    # Normalize empty strings to None
    platform = args.platform if args.platform else None
    device = args.device if args.device else None

    # Build query description
    query_parts = []
    if platform:
        query_parts.append(f"platform '{platform}'")
    if device:
        query_parts.append(f"device '{device}'")
    query_str = " and ".join(query_parts)

    # Find matching agents
    print(f"Searching for test targets with {query_str}...", file=sys.stderr)
    agents = lookup.find_test_targets(platform, device, args.show_offline)

    if not agents:
        print(f"\nNo test targets found matching {query_str}", file=sys.stderr)
        print("\nUse --list-platforms or --list-devices to see available options", file=sys.stderr)
        sys.exit(1)

    # Output results
    if args.json:
        # JSON output for pipeline integration
        output = {
            'platform': platform or '',
            'device': device or '',
            'count': len(agents),
            'test_targets': [
                {
                    'name': a['name'],
                    'id': a['id'],
                    'platform': a['platform'],
                    'devices': a['devices'],
                    'status': a['status'],
                    'enabled': a['enabled']
                }
                for a in agents
            ]
        }

        json_str = json.dumps(output, indent=2)

        # Print to stdout
        print(json_str)

        # Save to file if specified
        if args.json_output_file:
            with open(args.json_output_file, 'w') as f:
                f.write(json_str)
            print(f"\nJSON output saved to: {args.json_output_file}", file=sys.stderr)
    else:
        # Human-readable output
        print(f"\n{'=' * 100}", file=sys.stderr)
        print(f"Found {len(agents)} test target(s) matching {query_str}", file=sys.stderr)
        print('=' * 100, file=sys.stderr)
        print(file=sys.stderr)

        # Show detailed table
        print(format_results_table(agents))

        # Show summary
        print(format_results_summary(agents, platform, device))

if __name__ == '__main__':
    main()
