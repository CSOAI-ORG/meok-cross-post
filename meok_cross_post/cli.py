"""CLI entry point for meok-cross-post — `meok-cross-post <path>`."""
import argparse
import json
import sys
from pathlib import Path

from meok_cross_post import score_repo


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="meok-cross-post",
        description="Score an MCP server against 6 marketplaces. One command, one score.",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Path to the MCP server repo (default: current dir)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON only (no human-readable summary)",
    )
    parser.add_argument(
        "--platform",
        choices=["smithery", "mcp_registry", "docker_hub", "glama", "mcpize", "pulse_mcp", "all"],
        default="all",
        help="Filter to a single platform (default: all)",
    )

    args = parser.parse_args()
    result = score_repo(args.path)

    if "error" in result:
        print(f"ERROR: {result['error']} (path: {result['path']})", file=sys.stderr)
        return 1

    if args.json:
        if args.platform != "all":
            result["platforms"] = [p for p in result["platforms"] if p["platform"] == args.platform]
        print(json.dumps(result, indent=2))
        return 0

    # Human-readable
    print(f"\nMEOK Cross-Post Score: {result['path']}\n")
    print(f"  README:    {result['readme_score']}/40")
    print(f"  Pyproject: {result['pyproject_score']}/30")
    print(f"  GitHub:    {result['github_score']}/30")
    print()
    print("  Platform scores:")
    for p in result["platforms"]:
        marker = "OK" if p["ready"] else "--"
        print(f"    [{marker}] {p['platform']:14} {p['score']:3}/100")
        for issue in p["issues"][:3]:
            print(f"           - {issue}")
    print()
    print(f"  Total: {result['total_score']}/{result['max_score']}  ({result['ready_count']}/6 ready)")
    if result["ready_for_production"]:
        print("  STATUS: production-ready")
    else:
        print("  STATUS: needs work to hit 500+/600")
    return 0


if __name__ == "__main__":
    sys.exit(main())
