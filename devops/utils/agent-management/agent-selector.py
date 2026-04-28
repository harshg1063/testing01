#!/usr/bin/env python3
"""
Agent Selector - Find and select the right agent for feature testing.

This tool uses the device-list-parser to find devices supporting a feature,
then matches them with available agents in the agent pool to select the
appropriate agent for testing.
"""

import argparse
import sys
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set


class AgentSelector:
    """Selector for finding the right agent based on feature requirements."""
    
    def __init__(self, agent_pool_file: str = "agent-pool.txt"):
        """
        Initialize the agent selector.
        
        Args:
            agent_pool_file: Path to the agent pool configuration file
        """
        # If relative path, make it relative to script directory
        agent_pool_path = Path(agent_pool_file)
        if not agent_pool_path.is_absolute():
            script_dir = Path(__file__).parent
            agent_pool_path = script_dir / agent_pool_file
        
        self.agent_pool_file = agent_pool_path
        self.available_agents = self._load_agent_pool()
        
    def _load_agent_pool(self) -> Set[str]:
        """Load available agents from the agent pool file."""
        if not self.agent_pool_file.exists():
            raise FileNotFoundError(f"Agent pool file not found: {self.agent_pool_file}")
        
        agents = set()
        with open(self.agent_pool_file, 'r', encoding='utf-8') as f:
            for line in f:
                agent_name = line.strip()
                if agent_name and not agent_name.startswith('#'):
                    agents.add(agent_name)
        
        return agents
    
    def _extract_device_name(self, device_full_name: str) -> str:
        """
        Extract the device base name from the full device description.
        
        Args:
            device_full_name: Full device name like "Cadet (HP OmniBook X Flip 14) / Intel / 25C1"
            
        Returns:
            Base device name like "Cadet"
        """
        # Extract everything before the first space or parenthesis
        match = re.match(r'^([^\s(]+)', device_full_name.strip())
        if match:
            return match.group(1)
        return device_full_name.strip()
    
    def _find_matching_agents(self, device_names: List[str]) -> List[Tuple[str, str]]:
        """
        Find matching agents for the given device names.
        
        Args:
            device_names: List of device names to match
            
        Returns:
            List of tuples (device_name, agent_name) for matches found
        """
        matches = []
        
        for device_full_name in device_names:
            device_base_name = self._extract_device_name(device_full_name)
            
            # Check for exact match
            if device_base_name in self.available_agents:
                matches.append((device_full_name, device_base_name))
                continue
            
            # Check for numbered variants (e.g., Cadet_2, Cadet_3)
            variant_found = False
            for agent in self.available_agents:
                if agent.startswith(f"{device_base_name}_"):
                    matches.append((device_full_name, agent))
                    variant_found = True
                    break
            
            if variant_found:
                continue
            
            # Check if any agent name is contained in the device name (case-insensitive)
            for agent in self.available_agents:
                if agent.lower() in device_base_name.lower() or device_base_name.lower() in agent.lower():
                    matches.append((device_full_name, agent))
                    break
        
        return matches
    
    def _run_device_parser(self, feature: str, file_type: str = "consumer") -> List[str]:
        """
        Run the device-list-parser to get devices supporting a feature.
        
        Args:
            feature: Feature name to search for
            file_type: Type of file to search ("consumer", "commercial", or "both")
            
        Returns:
            List of device names supporting the feature
        """
        try:
            # Path to device-list-parser.py in device-data folder
            script_dir = Path(__file__).parent
            utils_dir = script_dir.parent
            device_parser_path = utils_dir / "device-data" / "device-list-parser.py"
            
            cmd = ["python", str(device_parser_path), "--search", feature]
            
            if file_type == "consumer":
                cmd.append("--consumer")
            elif file_type == "commercial":
                cmd.append("--commercial")
            elif file_type == "both":
                cmd.append("--both")
            else:
                raise ValueError(f"Invalid file_type: {file_type}. Use 'consumer', 'commercial', or 'both'")
            
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
            
            if result.returncode != 0:
                print(f"Error running device-list-parser: {result.stderr}", file=sys.stderr)
                return []
            
            # Parse the output to extract device names
            devices = []
            lines = result.stdout.split('\n')
            
            capturing_devices = False
            for line in lines:
                line = line.strip()
                
                # Look for the start of device list
                if "Devices supporting" in line:
                    capturing_devices = True
                    continue
                
                # Look for the end of device list
                if capturing_devices and (line.startswith("Total:") or line.startswith("Devices NOT supporting")):
                    break
                
                # Extract device names from numbered list
                if capturing_devices and re.match(r'^\s*\d+\.\s+', line):
                    device_name = re.sub(r'^\s*\d+\.\s+', '', line)
                    devices.append(device_name)
            
            return devices
            
        except subprocess.SubprocessError as e:
            print(f"Error running device-list-parser: {e}", file=sys.stderr)
            return []
        except Exception as e:
            print(f"Unexpected error: {e}", file=sys.stderr)
            return []
    
    def find_agents_for_feature(self, feature: str, file_type: str = "consumer", max_agents: int = None) -> Dict:
        """
        Find agents that can test a specific feature.
        
        Args:
            feature: Feature name to search for
            file_type: Type of file to search ("consumer", "commercial", or "both")
            max_agents: Maximum number of agents to return (None = all agents)
            
        Returns:
            Dictionary with search results
        """
        # Get devices supporting the feature
        supporting_devices = self._run_device_parser(feature, file_type)
        
        if not supporting_devices:
            return {
                'feature': feature,
                'file_type': file_type,
                'supporting_devices': [],
                'available_agents': list(self.available_agents),
                'matches': [],
                'recommended_agent': None,
                'message': f"No devices found supporting feature '{feature}'"
            }
        
        # Find matching agents
        matches = self._find_matching_agents(supporting_devices)
        
        # Get all matching agents (unique list)
        all_matching_agents = list(set([agent for _, agent in matches]))
        
        # Apply max_agents limit if specified
        if max_agents is not None and max_agents > 0:
            limited_agents = all_matching_agents[:max_agents]
            limited_matches = [(device, agent) for device, agent in matches if agent in limited_agents]
        else:
            limited_agents = all_matching_agents
            limited_matches = matches
        
        # Select the best agent (first match for now, could be enhanced)
        recommended_agent = limited_agents[0] if limited_agents else None
        
        # Create Azure DevOps matrix strategy format
        agent_matrix = {}
        for agent in limited_agents:
            agent_matrix[agent] = {
                "agentName": agent
            }
        
        return {
            'feature': feature,
            'file_type': file_type,
            'supporting_devices': supporting_devices,
            'available_agents': list(self.available_agents),
            'matches': limited_matches,
            'all_matching_agents': limited_agents,
            'recommended_agent': recommended_agent,
            'total_supporting_devices': len(supporting_devices),
            'total_matches': len(limited_matches),
            'max_agents_applied': max_agents,
            'agent_matrix': agent_matrix,
            'message': self._generate_message(feature, supporting_devices, limited_matches, recommended_agent)
        }
    
    def _generate_message(self, feature: str, devices: List[str], matches: List[Tuple[str, str]], recommended: Optional[str]) -> str:
        """Generate a human-readable message about the results."""
        if not devices:
            return f"No devices found supporting feature '{feature}'"
        
        if not matches:
            return (f"Found {len(devices)} devices supporting '{feature}', "
                   f"but none match available agents in the pool: {', '.join(self.available_agents)}")
        
        if recommended:
            return (f"Found {len(devices)} devices supporting '{feature}'. "
                   f"Recommended agent: '{recommended}' ({len(matches)} total matches available)")
        
        return f"Found {len(devices)} devices and {len(matches)} agent matches, but could not determine recommendation"
    
    def list_available_agents(self) -> List[str]:
        """Get list of available agents."""
        return sorted(list(self.available_agents))
    
    def search_agents_by_device(self, device_pattern: str) -> List[Tuple[str, str]]:
        """
        Search for agents that might match a device pattern.
        
        Args:
            device_pattern: Pattern to search for in device/agent names
            
        Returns:
            List of tuples (agent_name, match_reason)
        """
        matches = []
        pattern_lower = device_pattern.lower()
        
        for agent in self.available_agents:
            agent_lower = agent.lower()
            
            if pattern_lower == agent_lower:
                matches.append((agent, "exact_match"))
            elif pattern_lower in agent_lower:
                matches.append((agent, "agent_contains_pattern"))
            elif agent_lower in pattern_lower:
                matches.append((agent, "pattern_contains_agent"))
            elif any(part in agent_lower for part in pattern_lower.split() if len(part) > 2):
                matches.append((agent, "partial_word_match"))
        
        return matches


def main():
    """Main entry point for the command-line interface."""
    parser = argparse.ArgumentParser(
        description="Find and select the right agent for feature testing.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --feature "Audio Control"
  %(prog)s --feature "HP Sure Click" --commercial
  %(prog)s --feature "Audio Levels" --both
  %(prog)s --list-agents
  %(prog)s --search-device "Cadet"
  %(prog)s --feature "Bluetooth" --json
        """
    )
    
    parser.add_argument(
        "--feature", "-f",
        help="Feature name to search for compatible agents"
    )
    
    parser.add_argument(
        "--file-type", "-t",
        choices=["consumer", "commercial", "both"],
        default="consumer",
        help="Type of device database to search (default: consumer)"
    )
    
    parser.add_argument(
        "--agent-pool",
        default="agent-pool.txt",
        help="Path to agent pool configuration file (default: agent-pool.txt)"
    )
    
    parser.add_argument(
        "--max-agents",
        type=int,
        help="Maximum number of agents to return (default: all agents)"
    )
    
    parser.add_argument(
        "--list-agents", "-la",
        action="store_true",
        help="List all available agents in the pool"
    )
    
    parser.add_argument(
        "--search-device", "-sd",
        help="Search for agents matching a device pattern"
    )
    
    parser.add_argument(
        "--json", "-j",
        action="store_true",
        help="Output results in JSON format"
    )
    
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Only output the recommended agent name (for scripting)"
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    action_count = sum([
        bool(args.feature),
        args.list_agents,
        bool(args.search_device)
    ])
    
    if action_count == 0:
        parser.error("Please specify an action: --feature, --list-agents, or --search-device")
    
    if action_count > 1:
        parser.error("Please specify only one action at a time")
    
    try:
        selector = AgentSelector(args.agent_pool)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    
    try:
        if args.list_agents:
            agents = selector.list_available_agents()
            if args.json:
                import json
                print(json.dumps({"available_agents": agents}, indent=2))
            else:
                print(f"\nAvailable agents in pool ({len(agents)} total):")
                for i, agent in enumerate(agents, 1):
                    print(f"  {i}. {agent}")
        
        elif args.search_device:
            matches = selector.search_agents_by_device(args.search_device)
            if args.json:
                import json
                result = {
                    "search_pattern": args.search_device,
                    "matches": [{"agent": agent, "match_type": match_type} for agent, match_type in matches]
                }
                print(json.dumps(result, indent=2))
            elif args.quiet:
                if matches:
                    print(matches[0][0])  # Print first match only
            else:
                if matches:
                    print(f"\nAgents matching '{args.search_device}':")
                    for agent, match_type in matches:
                        print(f"  - {agent} ({match_type.replace('_', ' ')})")
                else:
                    print(f"No agents found matching '{args.search_device}'")
        
        elif args.feature:
            result = selector.find_agents_for_feature(args.feature, args.file_type, args.max_agents)
            
            if args.json:
                import json
                print(json.dumps(result, indent=2))
            elif args.quiet:
                if result['recommended_agent']:
                    print(result['recommended_agent'])
                else:
                    sys.exit(1)
            else:
                print(f"\n{'='*70}")
                print(f"Agent Selection for Feature: '{args.feature}'")
                print(f"{'='*70}")
                print(f"Database: {args.file_type.title()}")
                print()
                
                print(result['message'])
                print()
                
                if result['matches']:
                    print(f"Available matches ({len(result['matches'])} total):")
                    for i, (device, agent) in enumerate(result['matches'][:10], 1):  # Show first 10
                        device_short = selector._extract_device_name(device)
                        print(f"  {i}. {agent} -> {device_short} ({device})")
                    
                    if len(result['matches']) > 10:
                        print(f"  ... and {len(result['matches']) - 10} more matches")
                    
                    print()
                    if result['recommended_agent']:
                        print(f"🎯 RECOMMENDED AGENT: {result['recommended_agent']}")
                    print()
                
                if result['supporting_devices']:
                    device_count = len(result['supporting_devices'])
                    if device_count <= 5:
                        print(f"Supporting devices ({device_count} total):")
                        for device in result['supporting_devices']:
                            device_short = selector._extract_device_name(device)
                            print(f"  - {device_short}")
                    else:
                        print(f"Supporting devices ({device_count} total - showing first 5):")
                        for device in result['supporting_devices'][:5]:
                            device_short = selector._extract_device_name(device)
                            print(f"  - {device_short}")
                        print(f"  ... and {device_count - 5} more")
                    print()
                
                available = selector.list_available_agents()
                print(f"Agent pool ({len(available)} agents): {', '.join(available)}")
    
    except KeyboardInterrupt:
        print("\nOperation cancelled by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        if args.json:
            import json
            print(json.dumps({"error": str(e)}, indent=2), file=sys.stderr)
        else:
            print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()