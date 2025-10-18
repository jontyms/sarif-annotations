#!/usr/bin/env python3
"""
SARIF to GitHub Annotations Converter

Converts SARIF 2.1.0 files to GitHub annotations for better code review visibility.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any


class SarifConverter:
    """Converts SARIF results to GitHub annotations."""

    def __init__(
        self,
        sarif_file: str,
        annotation_level: str = "warning",
        max_annotations: int = 10,
        filter_rules: List[str] = None,
        exclude_rules: List[str] = None,
        working_directory: str = ".",
    ):
        self.sarif_file = sarif_file
        self.annotation_level = annotation_level
        self.max_annotations = max_annotations
        self.filter_rules = filter_rules or []
        self.exclude_rules = exclude_rules or []
        self.working_directory = Path(working_directory).resolve()

        # Counters for output
        self.annotations_created = 0
        self.results_processed = 0
        self.errors_found = 0
        self.warnings_found = 0

    def load_sarif(self) -> Dict[str, Any]:
        """Load and validate SARIF file."""
        try:
            with open(self.sarif_file, "r", encoding="utf-8") as f:
                sarif_data = json.load(f)

            if sarif_data.get("version") != "2.1.0":
                print(
                    f"::warning::SARIF version is {sarif_data.get('version')}, expected 2.1.0"
                )

            return sarif_data
        except FileNotFoundError:
            print(f"::error::SARIF file not found: {self.sarif_file}")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"::error::Invalid JSON in SARIF file: {e}")
            sys.exit(1)

    def get_rule_info(self, rule_id: str, rules: List[Dict]) -> Tuple[str, str]:
        """Get rule information from the SARIF rules section."""
        for rule in rules:
            if rule.get("id") == rule_id:
                name = rule.get("name", rule_id)
                description = ""
                if "shortDescription" in rule:
                    description = rule["shortDescription"].get("text", "")
                elif "help" in rule:
                    description = rule["help"].get("text", "")
                return name, description
        return rule_id, ""

    def get_severity_level(
        self, result: Dict[str, Any], rule_config: Dict = None
    ) -> str:
        """Determine the severity level for a result."""
        # Check result level first
        if "level" in result:
            level = result["level"]
            if level in ["error", "warning", "note", "info"]:
                return (
                    "error"
                    if level == "error"
                    else "warning"
                    if level == "warning"
                    else "notice"
                )

        # Check rule configuration
        if rule_config and "defaultConfiguration" in rule_config:
            level = rule_config["defaultConfiguration"].get("level", "")
            if level in ["error", "warning", "note", "info"]:
                return (
                    "error"
                    if level == "error"
                    else "warning"
                    if level == "warning"
                    else "notice"
                )

        # Default to configured annotation level
        return self.annotation_level

    def normalize_file_path(self, file_path: str) -> str:
        """Normalize file path to be relative to working directory."""
        if not file_path:
            return ".github"  # Default GitHub annotation path

        # Handle URI format
        if file_path.startswith("file://"):
            file_path = file_path[7:]

        path = Path(file_path)

        # If absolute path, try to make it relative to working directory
        if path.is_absolute():
            try:
                path = path.relative_to(self.working_directory)
            except ValueError:
                # Path is not under working directory, use as-is
                pass

        return str(path)

    def should_include_rule(self, rule_id: str) -> bool:
        """Check if rule should be included based on filters."""
        if self.exclude_rules and rule_id in self.exclude_rules:
            return False

        if self.filter_rules:
            return rule_id in self.filter_rules

        return True

    def create_annotation(
        self,
        level: str,
        message: str,
        file_path: str = None,
        line: int = None,
        end_line: int = None,
        col: int = None,
        end_col: int = None,
        title: str = None,
    ) -> str:
        """Create a GitHub annotation command."""
        params = []

        if file_path:
            params.append(f"file={file_path}")
        if line is not None:
            params.append(f"line={line}")
        if end_line is not None and end_line != line:
            params.append(f"endLine={end_line}")
        if col is not None:
            params.append(f"col={col}")
        if end_col is not None and end_col != col:
            params.append(f"endColumn={end_col}")
        if title:
            params.append(f"title={title}")

        param_str = ",".join(params)
        if param_str:
            return f"::{level} {param_str}::{message}"
        else:
            return f"::{level}::{message}"

    def process_location(
        self, location: Dict[str, Any]
    ) -> Tuple[str, int, int, int, int]:
        """Extract location information from SARIF location object."""
        file_path = ".github"
        line = 1
        end_line = 1
        col = 1
        end_col = 1

        if "physicalLocation" in location:
            phys_loc = location["physicalLocation"]

            # Get file path
            if "artifactLocation" in phys_loc:
                artifact = phys_loc["artifactLocation"]
                if "uri" in artifact:
                    file_path = self.normalize_file_path(artifact["uri"])

            # Get region information
            if "region" in phys_loc:
                region = phys_loc["region"]
                line = region.get("startLine", 1)
                end_line = region.get("endLine", line)
                col = region.get("startColumn", 1)
                end_col = region.get("endColumn", col)

        return file_path, line, end_line, col, end_col

    def convert(self) -> None:
        """Convert SARIF to GitHub annotations."""
        print("::group::Converting SARIF to GitHub annotations")

        sarif_data = self.load_sarif()

        if "runs" not in sarif_data:
            print("::error::No runs found in SARIF file")
            sys.exit(1)

        for run in sarif_data["runs"]:
            # Get rules information
            rules = []
            if "tool" in run and "driver" in run["tool"]:
                rules = run["tool"]["driver"].get("rules", [])

            # Process results
            if "results" not in run:
                continue

            for result in run["results"]:
                self.results_processed += 1

                if self.annotations_created >= self.max_annotations:
                    # Continue processing to count all results, but don't create more annotations
                    continue

                rule_id = result.get("ruleId", "unknown")

                # Check if rule should be included
                if not self.should_include_rule(rule_id):
                    continue

                # Get rule information
                rule_name, rule_description = self.get_rule_info(rule_id, rules)

                # Get message
                message = ""
                if "message" in result:
                    if "text" in result["message"]:
                        message = result["message"]["text"]
                    elif "markdown" in result["message"]:
                        message = result["message"]["markdown"]

                if not message:
                    message = f"Rule violation: {rule_id}"

                # Determine severity
                rule_config = next((r for r in rules if r.get("id") == rule_id), None)
                severity = self.get_severity_level(result, rule_config)

                # Count by severity
                if severity == "error":
                    self.errors_found += 1
                elif severity == "warning":
                    self.warnings_found += 1

                # Get locations
                locations = result.get("locations", [])
                if not locations:
                    # Create annotation without location
                    title = (
                        f"{rule_name} ({rule_id})" if rule_name != rule_id else rule_id
                    )
                    annotation = self.create_annotation(
                        level=severity, message=message, title=title
                    )
                    print(annotation)
                    self.annotations_created += 1
                else:
                    # Create annotation for each location
                    for location in locations:
                        if self.annotations_created >= self.max_annotations:
                            # Skip creating annotation but continue processing
                            continue

                        file_path, line, end_line, col, end_col = self.process_location(
                            location
                        )
                        title = (
                            f"{rule_name} ({rule_id})"
                            if rule_name != rule_id
                            else rule_id
                        )

                        annotation = self.create_annotation(
                            level=severity,
                            message=message,
                            file_path=file_path,
                            line=line,
                            end_line=end_line,
                            col=col,
                            end_col=end_col,
                            title=title,
                        )
                        print(annotation)
                        self.annotations_created += 1

        # Show limit message after processing all results
        if (
            self.results_processed > self.max_annotations
            and self.annotations_created >= self.max_annotations
        ):
            print(
                f"::notice::Reached maximum annotations limit ({self.max_annotations})"
            )

        print("::endgroup::")

        # Set outputs
        self.set_output("annotations-created", str(self.annotations_created))
        self.set_output("results-processed", str(self.results_processed))
        self.set_output("errors-found", str(self.errors_found))
        self.set_output("warnings-found", str(self.warnings_found))

        # Summary
        print(
            f"::notice::Processed {self.results_processed} results, created {self.annotations_created} annotations"
        )
        if self.errors_found > 0:
            print(
                f"::notice::Found {self.errors_found} errors and {self.warnings_found} warnings"
            )

    @staticmethod
    def set_output(name: str, value: str) -> None:
        """Set GitHub Action output."""
        github_output = os.getenv("GITHUB_OUTPUT")
        if github_output:
            with open(github_output, "a", encoding="utf-8") as f:
                f.write(f"{name}={value}\n")


def main():
    """Main entry point."""
    # Get inputs from environment variables
    sarif_file = os.getenv("SARIF_FILE")
    if not sarif_file:
        print("::error::SARIF_FILE environment variable is required")
        sys.exit(1)

    annotation_level = os.getenv("ANNOTATION_LEVEL", "warning")
    max_annotations = int(os.getenv("MAX_ANNOTATIONS", "10"))
    working_directory = os.getenv("WORKING_DIRECTORY", ".")

    # Parse filter and exclude rules
    filter_rules = []
    exclude_rules = []

    filter_input = os.getenv("FILTER_RULES", "").strip()
    if filter_input:
        filter_rules = [
            rule.strip() for rule in filter_input.split(",") if rule.strip()
        ]

    exclude_input = os.getenv("EXCLUDE_RULES", "").strip()
    if exclude_input:
        exclude_rules = [
            rule.strip() for rule in exclude_input.split(",") if rule.strip()
        ]

    # Create converter and run
    converter = SarifConverter(
        sarif_file=sarif_file,
        annotation_level=annotation_level,
        max_annotations=max_annotations,
        filter_rules=filter_rules,
        exclude_rules=exclude_rules,
        working_directory=working_directory,
    )

    converter.convert()


if __name__ == "__main__":
    main()
