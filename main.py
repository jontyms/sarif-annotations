#!/usr/bin/env python3
"""
Simple CLI interface for testing the SARIF to GitHub Annotations converter.
"""

import argparse
import os
import sys
from pathlib import Path

# Add the current directory to the path so we can import the converter
sys.path.insert(0, os.path.dirname(__file__))

from sarif_converter import SarifConverter


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Convert SARIF 2.1.0 files to GitHub annotations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py example.sarif
  python main.py results.sarif --level error --max 5
  python main.py scan.sarif --filter "rule1,rule2" --exclude "noisy-rule"
        """,
    )

    parser.add_argument(
        "sarif_file", nargs="?", help="Path to the SARIF file to convert"
    )

    parser.add_argument(
        "--level",
        "--annotation-level",
        default="warning",
        choices=["error", "warning", "notice"],
        help="Default annotation level (default: warning)",
    )

    parser.add_argument(
        "--max",
        "--max-annotations",
        type=int,
        default=10,
        help="Maximum number of annotations to create (default: 10)",
    )

    parser.add_argument(
        "--filter",
        "--filter-rules",
        help="Comma-separated list of rule IDs to include (empty = all rules)",
    )

    parser.add_argument(
        "--exclude",
        "--exclude-rules",
        help="Comma-separated list of rule IDs to exclude",
    )

    parser.add_argument(
        "--working-dir",
        "--working-directory",
        default=".",
        help="Working directory for relative file paths (default: current directory)",
    )

    parser.add_argument(
        "--test",
        action="store_true",
        help="Run the test suite instead of converting SARIF",
    )

    parser.add_argument(
        "--version",
        action="version",
        version="sarif-annotations 1.0.0",
    )

    args = parser.parse_args()

    # Handle test mode
    if args.test:
        try:
            from test_converter import run_all_tests

            run_all_tests()
            return
        except ImportError:
            print("❌ Test module not found. Make sure test_converter.py exists.")
            sys.exit(1)

    # Validate SARIF file exists (unless in test mode)
    if not args.sarif_file:
        print("❌ SARIF file is required unless using --test mode")
        sys.exit(1)

    if not Path(args.sarif_file).exists():
        print(f"❌ SARIF file not found: {args.sarif_file}")
        sys.exit(1)

    # Parse filter and exclude rules
    filter_rules = []
    exclude_rules = []

    if args.filter:
        filter_rules = [rule.strip() for rule in args.filter.split(",") if rule.strip()]

    if args.exclude:
        exclude_rules = [
            rule.strip() for rule in args.exclude.split(",") if rule.strip()
        ]

    # Create converter and run
    try:
        converter = SarifConverter(
            sarif_file=args.sarif_file,
            annotation_level=args.level,
            max_annotations=args.max,
            filter_rules=filter_rules,
            exclude_rules=exclude_rules,
            working_directory=args.working_dir,
        )

        converter.convert()

        # Print summary
        print(f"\n📊 Summary:")
        print(f"  • Annotations created: {converter.annotations_created}")
        print(f"  • Results processed: {converter.results_processed}")
        print(f"  • Errors found: {converter.errors_found}")
        print(f"  • Warnings found: {converter.warnings_found}")

    except KeyboardInterrupt:
        print("\n⚠️  Conversion interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error during conversion: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
