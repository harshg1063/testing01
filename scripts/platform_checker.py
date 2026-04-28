"""
This script scans all Python files in the 'tests' directory for pytest.mark.platform
decorators, extracts platform names, and:

1. Prints a per-file summary table
2. Lists all unique platforms found in tests
3. Loads platforms_and_devices.yaml
4. Compares platforms found in tests vs platforms defined in YAML
5. Reports mismatches in both directions
"""

import ast
from pathlib import Path
import yaml

FILE_COL_WIDTH = 60
PLATFORMS_AND_DEVICES_YAML_FILE = "./tests/platforms_and_devices.yaml"


class PlatformVisitor(ast.NodeVisitor):
    def __init__(self):
        self.platforms = set()

    def visit_Call(self, node):
        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "platform"
            and isinstance(node.func.value, ast.Attribute)
            and node.func.value.attr == "mark"
            and isinstance(node.func.value.value, ast.Name)
            and node.func.value.value.id == "pytest"
        ):
            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    self.platforms.add(arg.value)

        self.generic_visit(node)


def extract_platforms_from_file(file_path: Path) -> set[str]:
    try:
        tree = ast.parse(file_path.read_text(encoding="utf-8"))
    except SyntaxError:
        return set()

    visitor = PlatformVisitor()
    visitor.visit(tree)
    return visitor.platforms


def extract_platforms_from_yaml(yaml_path: Path):
    """
    Supports YAML like:

    platform:
      - commercial:
          - platform1
          - platform2
      - consumer:
          - platform3
          - platform4
    """
    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))

    platforms = set()

    platform_section = data.get("platform", [])

    if isinstance(platform_section, list):
        for entry in platform_section:
            if isinstance(entry, dict):
                for _, items in entry.items():
                    if isinstance(items, list):
                        platforms.update(items)

    return platforms

def main():
    tests_dir = Path("tests")
    platforms_yaml_path = Path(PLATFORMS_AND_DEVICES_YAML_FILE)

    platforms_by_file: dict[str, set[str]] = {}
    all_test_platforms: set[str] = set()

    # ---- Scan test files ----
    for py_file in tests_dir.rglob("*.py"):
        platforms = extract_platforms_from_file(py_file)
        if platforms:
            platforms_by_file[py_file.name] = platforms
            all_test_platforms.update(platforms)

    # ---- Table Summary ----
    print("\nTable Summary:")
    header = (
        f"{'File':<{FILE_COL_WIDTH}} | "
        f"{'count':<5} | Platforms"
    )
    print(header)
    print("-" * len(header))

    for file_name, platforms in sorted(platforms_by_file.items()):
        platform_list = ", ".join(sorted(platforms))
        print(
            f"{file_name:<{FILE_COL_WIDTH}} | "
            f"{len(platforms):<5} | "
            f"{platform_list}"
        )

    # ---- Unique Platforms from tests ----
    print(f"\nUnique platforms in tests ({len(all_test_platforms)}):")
    for platform in sorted(all_test_platforms):
        print(f"- {platform}")

    # ---- Load YAML platforms ----
    yaml_platforms = extract_platforms_from_yaml(platforms_yaml_path)

    print(f"\nPlatforms in platforms_and_devices.yaml ({len(yaml_platforms)}):")
    for platform in sorted(yaml_platforms):
        print(f"- {platform}")

    # ---- Compare ----
    only_in_tests = all_test_platforms - yaml_platforms
    only_in_yaml = yaml_platforms - all_test_platforms

    print("\nPlatform mismatches:")

    print(f"\nPresent in tests but NOT in platforms_and_devices.yaml ({len(only_in_tests)}):")
    if only_in_tests:
        for platform in sorted(only_in_tests):
            print(f"- {platform}")
    else:
        print("✓ None")

    print(f"\nPresent in platforms_and_devices.yaml but NOT in tests ({len(only_in_yaml)}):")
    if only_in_yaml:
        for platform in sorted(only_in_yaml):
            print(f"- {platform}")
    else:
        print("✓ None")


if __name__ == "__main__":
    main()
