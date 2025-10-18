#!/usr/bin/env python3
"""
Test script for SARIF to GitHub Annotations converter.
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open
import io

# Add the current directory to the path so we can import the converter
sys.path.insert(0, os.path.dirname(__file__))

from sarif_converter import SarifConverter


def create_test_sarif(results=None, rules=None):
    """Create a test SARIF file with the given results and rules."""
    if rules is None:
        rules = [
            {
                "id": "test-rule-1",
                "name": "Test Rule 1",
                "shortDescription": {"text": "A test rule for validation"},
                "defaultConfiguration": {"level": "warning"},
            },
            {
                "id": "test-rule-2",
                "name": "Test Rule 2",
                "shortDescription": {"text": "Another test rule"},
                "defaultConfiguration": {"level": "error"},
            },
        ]

    if results is None:
        results = [
            {
                "ruleId": "test-rule-1",
                "level": "warning",
                "message": {"text": "This is a test warning"},
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {"uri": "src/test.py"},
                            "region": {
                                "startLine": 10,
                                "startColumn": 5,
                                "endLine": 10,
                                "endColumn": 15,
                            },
                        }
                    }
                ],
            },
            {
                "ruleId": "test-rule-2",
                "level": "error",
                "message": {"text": "This is a test error"},
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {"uri": "src/main.py"},
                            "region": {"startLine": 25, "startColumn": 1},
                        }
                    }
                ],
            },
        ]

    sarif = {
        "$schema": "https://schemastore.azurewebsites.net/schemas/json/sarif-2.1.0-rtm.5.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {"name": "test-tool", "version": "1.0.0", "rules": rules}
                },
                "results": results,
            }
        ],
    }

    return sarif


def test_basic_conversion():
    """Test basic SARIF to annotation conversion."""
    print("Testing basic conversion...")

    # Create test SARIF
    sarif_data = create_test_sarif()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".sarif", delete=False) as f:
        json.dump(sarif_data, f)
        sarif_file = f.name

    try:
        # Capture stdout to check annotations
        captured_output = io.StringIO()

        with patch("sys.stdout", captured_output):
            converter = SarifConverter(sarif_file)
            converter.convert()

        output = captured_output.getvalue()

        # Check that annotations were created
        assert "::warning" in output, "Should contain warning annotation"
        assert "::error" in output, "Should contain error annotation"
        assert "src/test.py" in output, "Should contain file path"
        assert "line=10" in output, "Should contain line number"
        assert "This is a test warning" in output, "Should contain warning message"

        # Check counters
        assert converter.annotations_created == 2, (
            f"Expected 2 annotations, got {converter.annotations_created}"
        )
        assert converter.results_processed == 2, (
            f"Expected 2 results processed, got {converter.results_processed}"
        )
        assert converter.errors_found == 1, (
            f"Expected 1 error, got {converter.errors_found}"
        )
        assert converter.warnings_found == 1, (
            f"Expected 1 warning, got {converter.warnings_found}"
        )

        print("✅ Basic conversion test passed")

    finally:
        os.unlink(sarif_file)


def test_rule_filtering():
    """Test rule filtering functionality."""
    print("Testing rule filtering...")

    sarif_data = create_test_sarif()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".sarif", delete=False) as f:
        json.dump(sarif_data, f)
        sarif_file = f.name

    try:
        captured_output = io.StringIO()

        with patch("sys.stdout", captured_output):
            # Filter to only include test-rule-1
            converter = SarifConverter(sarif_file, filter_rules=["test-rule-1"])
            converter.convert()

        output = captured_output.getvalue()

        # Should only have one annotation (the warning)
        assert converter.annotations_created == 1, (
            f"Expected 1 annotation, got {converter.annotations_created}"
        )
        assert converter.results_processed == 2, (
            f"Expected 2 results processed, got {converter.results_processed}"
        )
        assert "test-rule-1" in output, "Should contain filtered rule"
        assert "This is a test warning" in output, "Should contain warning message"

        print("✅ Rule filtering test passed")

    finally:
        os.unlink(sarif_file)


def test_rule_exclusion():
    """Test rule exclusion functionality."""
    print("Testing rule exclusion...")

    sarif_data = create_test_sarif()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".sarif", delete=False) as f:
        json.dump(sarif_data, f)
        sarif_file = f.name

    try:
        captured_output = io.StringIO()

        with patch("sys.stdout", captured_output):
            # Exclude test-rule-2
            converter = SarifConverter(sarif_file, exclude_rules=["test-rule-2"])
            converter.convert()

        output = captured_output.getvalue()

        # Should only have one annotation (the warning, not the error)
        assert converter.annotations_created == 1, (
            f"Expected 1 annotation, got {converter.annotations_created}"
        )
        assert "This is a test warning" in output, "Should contain warning message"
        assert "This is a test error" not in output, (
            "Should not contain excluded rule message"
        )

        print("✅ Rule exclusion test passed")

    finally:
        os.unlink(sarif_file)


def test_max_annotations_limit():
    """Test max annotations limit."""
    print("Testing max annotations limit...")

    # Create SARIF with many results
    results = []
    for i in range(20):
        results.append(
            {
                "ruleId": "test-rule-1",
                "level": "warning",
                "message": {"text": f"Warning #{i + 1}"},
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {"uri": f"file{i}.py"},
                            "region": {"startLine": i + 1, "startColumn": 1},
                        }
                    }
                ],
            }
        )

    sarif_data = create_test_sarif(results=results)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".sarif", delete=False) as f:
        json.dump(sarif_data, f)
        sarif_file = f.name

    try:
        captured_output = io.StringIO()

        with patch("sys.stdout", captured_output):
            # Limit to 5 annotations
            converter = SarifConverter(sarif_file, max_annotations=5)
            converter.convert()

        output = captured_output.getvalue()

        # Should only create 5 annotations despite having 20 results
        assert converter.annotations_created == 5, (
            f"Expected 5 annotations, got {converter.annotations_created}"
        )
        assert converter.results_processed == 20, (
            f"Expected 20 results processed, got {converter.results_processed}"
        )
        assert "Reached maximum annotations limit (5)" in output, (
            "Should show limit message"
        )

        print("✅ Max annotations limit test passed")

    finally:
        os.unlink(sarif_file)


def test_no_location_results():
    """Test handling of results without location information."""
    print("Testing results without locations...")

    results = [
        {
            "ruleId": "test-rule-1",
            "level": "warning",
            "message": {"text": "Global warning without location"},
            # No locations array
        }
    ]

    sarif_data = create_test_sarif(results=results)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".sarif", delete=False) as f:
        json.dump(sarif_data, f)
        sarif_file = f.name

    try:
        captured_output = io.StringIO()

        with patch("sys.stdout", captured_output):
            converter = SarifConverter(sarif_file)
            converter.convert()

        output = captured_output.getvalue()

        # Should create annotation without file location
        assert converter.annotations_created == 1, (
            f"Expected 1 annotation, got {converter.annotations_created}"
        )
        assert "Global warning without location" in output, "Should contain message"
        assert "::warning" in output, "Should create warning annotation"

        print("✅ No location results test passed")

    finally:
        os.unlink(sarif_file)


def test_file_path_normalization():
    """Test file path normalization."""
    print("Testing file path normalization...")

    results = [
        {
            "ruleId": "test-rule-1",
            "level": "warning",
            "message": {"text": "File URI test"},
            "locations": [
                {
                    "physicalLocation": {
                        "artifactLocation": {"uri": "file:///absolute/path/to/file.py"},
                        "region": {"startLine": 1, "startColumn": 1},
                    }
                }
            ],
        },
        {
            "ruleId": "test-rule-1",
            "level": "warning",
            "message": {"text": "Relative path test"},
            "locations": [
                {
                    "physicalLocation": {
                        "artifactLocation": {"uri": "relative/path/file.py"},
                        "region": {"startLine": 1, "startColumn": 1},
                    }
                }
            ],
        },
    ]

    sarif_data = create_test_sarif(results=results)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".sarif", delete=False) as f:
        json.dump(sarif_data, f)
        sarif_file = f.name

    try:
        captured_output = io.StringIO()

        with patch("sys.stdout", captured_output):
            converter = SarifConverter(sarif_file)
            converter.convert()

        output = captured_output.getvalue()

        # Check that file URI was processed
        assert (
            "/absolute/path/to/file.py" in output
            or "absolute/path/to/file.py" in output
        ), "Should contain normalized file path"
        assert "relative/path/file.py" in output, "Should contain relative path"

        print("✅ File path normalization test passed")

    finally:
        os.unlink(sarif_file)


def test_invalid_sarif_file():
    """Test handling of invalid SARIF files."""
    print("Testing invalid SARIF file handling...")

    # Test with non-existent file
    try:
        with patch("sys.exit") as mock_exit:
            converter = SarifConverter("non-existent-file.sarif")
            converter.load_sarif()
            mock_exit.assert_called_with(1)
        print("✅ Non-existent file handling test passed")
    except SystemExit:
        print("✅ Non-existent file handling test passed")

    # Test with invalid JSON
    with tempfile.NamedTemporaryFile(mode="w", suffix=".sarif", delete=False) as f:
        f.write("{ invalid json }")
        invalid_sarif_file = f.name

    try:
        with patch("sys.exit") as mock_exit:
            converter = SarifConverter(invalid_sarif_file)
            converter.load_sarif()
            mock_exit.assert_called_with(1)
        print("✅ Invalid JSON handling test passed")
    except SystemExit:
        print("✅ Invalid JSON handling test passed")
    finally:
        os.unlink(invalid_sarif_file)


def test_severity_level_detection():
    """Test severity level detection from SARIF."""
    print("Testing severity level detection...")

    results = [
        {
            "ruleId": "test-rule-1",
            "level": "error",
            "message": {"text": "Explicit error level"},
        },
        {
            "ruleId": "test-rule-2",
            "level": "note",
            "message": {"text": "Note level (should become notice)"},
        },
        {
            "ruleId": "test-rule-1",
            "message": {"text": "No explicit level (should use rule default)"},
        },
    ]

    sarif_data = create_test_sarif(results=results)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".sarif", delete=False) as f:
        json.dump(sarif_data, f)
        sarif_file = f.name

    try:
        captured_output = io.StringIO()

        with patch("sys.stdout", captured_output):
            converter = SarifConverter(sarif_file)
            converter.convert()

        output = captured_output.getvalue()

        # Check different severity levels
        assert "::error" in output, "Should contain error annotation"
        assert "::notice" in output, (
            "Should contain notice annotation (converted from note)"
        )
        assert "::warning" in output, (
            "Should contain warning annotation (from rule default)"
        )

        print("✅ Severity level detection test passed")

    finally:
        os.unlink(sarif_file)


def run_all_tests():
    """Run all tests."""
    print("🧪 Running SARIF Converter Tests\n")

    tests = [
        test_basic_conversion,
        test_rule_filtering,
        test_rule_exclusion,
        test_max_annotations_limit,
        test_no_location_results,
        test_file_path_normalization,
        test_invalid_sarif_file,
        test_severity_level_detection,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ {test.__name__} failed: {e}")
            failed += 1
        print()

    print(f"🏁 Test Results: {passed} passed, {failed} failed")

    if failed > 0:
        sys.exit(1)
    else:
        print("🎉 All tests passed!")


if __name__ == "__main__":
    run_all_tests()
