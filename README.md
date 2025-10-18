# SARIF to GitHub Annotations

[![GitHub](https://img.shields.io/github/license/jontyms/sarif-annotations)](LICENSE)
[![GitHub release](https://img.shields.io/github/v/release/jontyms/sarif-annotations)](https://github.com/jontyms/sarif-annotations/releases)

A GitHub Action that converts SARIF 2.1.0 files to GitHub annotations, making static analysis results visible directly in your pull requests and workflow runs.

## Features

- ✅ **Full SARIF 2.1.0 Support**: Processes all standard SARIF elements including rules, results, and locations
- 🎯 **Smart Annotations**: Creates GitHub annotations with proper file locations, line numbers, and severity levels
- 🔧 **Flexible Filtering**: Include or exclude specific rules based on your needs
- 📊 **Detailed Reporting**: Provides summaries and outputs for further automation
- ⚡ **Fast Processing**: Efficiently handles large SARIF files with configurable limits
- 🛡️ **Error Handling**: Robust error handling with helpful diagnostic messages

## Usage

### Basic Usage

```yaml
name: Static Analysis
on: [push, pull_request]

jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      # Run your static analysis tool (example with ESLint)
      - name: Run ESLint
        run: npx eslint . --format @microsoft/eslint-formatter-sarif --output-file eslint-results.sarif
        continue-on-error: true

      # Convert SARIF to annotations
      - name: Annotate with SARIF results
        uses: jontyms/sarif-annotations@v1
        with:
          sarif-file: 'eslint-results.sarif'
```

### Advanced Usage

```yaml
- name: Annotate with SARIF results
  uses: jontyms/sarif-annotations@v1
  with:
    sarif-file: 'analysis-results.sarif'
    annotation-level: 'warning'
    max-annotations: 10
    filter-rules: 'rule1,rule2,rule3'  # Only include these rules
    exclude-rules: 'noisy-rule,deprecated-rule'  # Exclude these rules
    working-directory: './src'
  id: sarif-annotations

- name: Check results
  run: |
    echo "Created ${{ steps.sarif-annotations.outputs.annotations-created }} annotations"
    echo "Found ${{ steps.sarif-annotations.outputs.errors-found }} errors"
    echo "Found ${{ steps.sarif-annotations.outputs.warnings-found }} warnings"
```

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `sarif-file` | Path to the SARIF file to convert | ✅ Yes | - |
| `annotation-level` | Default annotation level (`error`, `warning`, `notice`) | No | `warning` |
| `max-annotations` | Maximum number of annotations to create (GitHub limit is 10 per step) | No | `10` |
| `filter-rules` | Comma-separated list of rule IDs to include (empty = all rules) | No | `''` |
| `exclude-rules` | Comma-separated list of rule IDs to exclude | No | `''` |
| `working-directory` | Working directory for relative file paths | No | `'.'` |

## Outputs

| Output | Description |
|--------|-------------|
| `annotations-created` | Number of annotations created |
| `results-processed` | Total number of SARIF results processed |
| `errors-found` | Number of error-level results found |
| `warnings-found` | Number of warning-level results found |

## Supported Tools

This action works with any tool that generates SARIF 2.1.0 files. Popular tools include:

### Security Analysis
- **CodeQL** - GitHub's semantic code analysis
- **Semgrep** - Static analysis for finding bugs and security issues
- **Bandit** - Python security linter
- **Brakeman** - Ruby on Rails security scanner
- **gosec** - Go security checker

### Code Quality
- **ESLint** - JavaScript/TypeScript linting (with `@microsoft/eslint-formatter-sarif`)
- **Pylint** - Python code analysis (with `pylint-sarif`)
- **SonarQube** - Code quality and security analysis
- **Checkmarx** - Static application security testing

### Infrastructure as Code
- **ansible-lint** - Ansible playbook linting
- **terraform-compliance** - Terraform policy enforcement
- **cfn-lint** - CloudFormation template validation

## Examples

### ESLint with SARIF

```yaml
- name: Run ESLint
  run: |
    npm install @microsoft/eslint-formatter-sarif
    npx eslint . --format @microsoft/eslint-formatter-sarif --output-file eslint.sarif
  continue-on-error: true

- name: Annotate ESLint results
  uses: jontyms/sarif-annotations@v1
  with:
    sarif-file: 'eslint.sarif'
```

### Semgrep Security Analysis

```yaml
- name: Run Semgrep
  run: |
    pip install semgrep
    semgrep --config=auto --sarif --output=semgrep.sarif .
  continue-on-error: true

- name: Annotate Semgrep results
  uses: jontyms/sarif-annotations@v1
  with:
    sarif-file: 'semgrep.sarif'
    annotation-level: 'error'
    exclude-rules: 'low-severity-rule'
```

### Multiple SARIF Files

```yaml
- name: Process multiple SARIF files
  run: |
    for sarif_file in *.sarif; do
      echo "Processing $sarif_file"
      # Use a unique step ID for each file
      step_id=$(basename "$sarif_file" .sarif)
    done
  shell: bash

# Process each file in separate steps
- name: Annotate security results
  uses: jontyms/sarif-annotations@v1
  with:
    sarif-file: 'security.sarif'
    annotation-level: 'error'

- name: Annotate quality results
  uses: jontyms/sarif-annotations@v1
  with:
    sarif-file: 'quality.sarif'
    annotation-level: 'warning'
```

## GitHub Annotation Limits

GitHub has some limitations on annotations:

- **10 annotations per step**: This action respects this limit with the `max-annotations` input
- **50 annotations per job**: Plan your workflow accordingly
- **Annotation visibility**: Annotations appear in the Files Changed tab of pull requests

To work around these limits:

1. **Use multiple steps** for different SARIF files or rule categories
2. **Filter rules** to focus on the most important issues
3. **Prioritize by severity** - process errors first, then warnings

## Troubleshooting

### Common Issues

**"SARIF file not found"**
```yaml
# Make sure the path is correct and the file exists
- name: Check SARIF file
  run: ls -la *.sarif
```

**"No annotations created"**
- Check that your SARIF file contains results
- Verify your `filter-rules` and `exclude-rules` settings
- Check that rule IDs match exactly (case-sensitive)

**"Invalid JSON in SARIF file"**
- Ensure your analysis tool generated valid JSON
- Check for truncated or corrupted files

### Debug Mode

Enable debug logging to see detailed processing information:

```yaml
- name: Annotate with debug
  uses: jontyms/sarif-annotations@v1
  with:
    sarif-file: 'results.sarif'
  env:
    ACTIONS_STEP_DEBUG: true
```

## SARIF 2.1.0 Specification

This action follows the [SARIF 2.1.0 specification](https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html). Key elements processed:

- **Rules**: Tool-specific analysis rules with metadata
- **Results**: Individual findings with messages and locations
- **Locations**: File paths, line numbers, and column ranges
- **Severity Levels**: Error, warning, note, and info classifications

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup

```bash
git clone https://github.com/jontyms/sarif-annotations.git
cd sarif-annotations
python -m pip install -r requirements.txt
```

### Testing

```bash
# Test with the example SARIF file
python sarif_converter.py
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Related Projects

- [SARIF Specification](https://sarifweb.azurewebsites.net/)
- [Microsoft SARIF SDK](https://github.com/microsoft/sarif-sdk)
- [SARIF Viewers](https://sarifweb.azurewebsites.net/Viewers)

---

**Note**: Replace `jontyms/sarif-annotations` with your actual GitHub repository path when using this action.
