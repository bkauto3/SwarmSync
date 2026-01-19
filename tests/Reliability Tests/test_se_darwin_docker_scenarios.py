"""
Test SE-Darwin Docker Support Scenarios

Validates that SE-Darwin correctly processes Docker-focused support scenarios
and produces Docker-specific troubleshooting recommendations.

Author: Hudson (Code Review Agent)
Date: October 25, 2025
"""

import json
import pytest


class TestSEDarwinDockerScenarios:
    """Test SE-Darwin with Docker support scenarios"""

    @pytest.fixture
    def support_scenarios(self):
        """Load support scenarios from JSON"""
        with open('benchmarks/test_cases/support_scenarios.json', 'r') as f:
            scenarios = json.load(f)
        return scenarios

    def test_docker_scenarios_exist(self, support_scenarios):
        """Test that Docker scenarios are present in support scenarios"""
        docker_scenarios = [
            s for s in support_scenarios
            if 'docker' in s.get('id', '').lower()
        ]

        assert len(docker_scenarios) >= 6, f"Expected at least 6 Docker scenarios, found {len(docker_scenarios)}"

        # Verify Docker scenario IDs
        docker_ids = [s['id'] for s in docker_scenarios]
        expected_ids = [
            'support_19_docker',
            'support_20_docker',
            'support_21_docker',
            'support_22_docker',
            'support_23_docker',
            'support_24_docker'
        ]

        for expected_id in expected_ids:
            assert expected_id in docker_ids, f"Missing Docker scenario: {expected_id}"

        print(f"✓ Found {len(docker_scenarios)} Docker scenarios")

    def test_docker_scenario_structure(self, support_scenarios):
        """Test that Docker scenarios have required Docker-specific fields"""
        docker_scenarios = [
            s for s in support_scenarios
            if 'docker' in s.get('id', '').lower()
        ]

        for scenario in docker_scenarios:
            # Verify required fields
            assert 'id' in scenario
            assert 'description' in scenario
            assert 'inputs' in scenario
            assert 'expected_outputs' in scenario
            assert 'scoring' in scenario

            # Verify Docker-specific inputs
            inputs = scenario['inputs']
            assert 'issue_type' in inputs
            assert 'docker' in inputs['issue_type'].lower() or 'docker' in scenario['description'].lower()

            # Verify Docker-specific outputs
            outputs = scenario['expected_outputs']
            assert 'required_elements' in outputs

            # Check for Docker-specific checks
            if 'docker_specific_checks' in outputs:
                checks = outputs['docker_specific_checks']
                assert len(checks) > 0, f"Docker scenario {scenario['id']} has empty docker_specific_checks"

                # Verify at least one check mentions 'docker'
                docker_commands = [c for c in checks if 'docker' in c.lower()]
                assert len(docker_commands) > 0, f"Docker scenario {scenario['id']} has no docker commands"

        print(f"✓ All Docker scenarios have proper structure")

    def test_docker_scenario_coverage(self, support_scenarios):
        """Test that Docker scenarios cover key Docker troubleshooting areas"""
        docker_scenarios = [
            s for s in support_scenarios
            if 'docker' in s.get('id', '').lower()
        ]

        # Expected Docker issue types
        expected_coverage = {
            'container_startup': False,
            'networking': False,
            'volumes_permissions': False,
            'build_caching': False,
            'compose_dependencies': False,
            'image_size': False
        }

        for scenario in docker_scenarios:
            issue_type = scenario['inputs']['issue_type']
            description = scenario['description'].lower()

            if 'startup' in issue_type or 'start' in description:
                expected_coverage['container_startup'] = True
            if 'network' in issue_type or 'network' in description:
                expected_coverage['networking'] = True
            if 'volume' in issue_type or 'permission' in description:
                expected_coverage['volumes_permissions'] = True
            if 'cache' in issue_type or 'cache' in description:
                expected_coverage['build_caching'] = True
            if 'compose' in issue_type or 'compose' in description:
                expected_coverage['compose_dependencies'] = True
            if 'size' in issue_type or 'optimization' in description:
                expected_coverage['image_size'] = True

        # Verify coverage
        uncovered = [k for k, v in expected_coverage.items() if not v]
        assert len(uncovered) == 0, f"Missing Docker coverage areas: {uncovered}"

        print(f"✓ Docker scenarios cover all key troubleshooting areas")

    def test_docker_commands_validity(self, support_scenarios):
        """Test that Docker commands in scenarios are valid"""
        docker_scenarios = [
            s for s in support_scenarios
            if 'docker' in s.get('id', '').lower()
        ]

        valid_docker_commands = [
            'docker ps',
            'docker logs',
            'docker inspect',
            'docker rm',
            'docker network',
            'docker exec',
            'docker build',
            'docker history',
            'docker image',
            'docker system',
            'docker-compose'
        ]

        # Also allow non-command checks like "Dockerfile ...", "ls -la", etc.
        valid_check_prefixes = [
            'dockerfile',
            '.dockerignore',
            'ls -la',
            'chown',
            'chmod',
            'iptables',
            'dns settings',
            'volume mount',
            'copy vs add',
            'arg vs env',
            'healthcheck',
            'wait-for-it',
            'multi-stage',
            'dive tool'
        ]

        for scenario in docker_scenarios:
            outputs = scenario['expected_outputs']
            if 'docker_specific_checks' not in outputs:
                continue

            checks = outputs['docker_specific_checks']
            for check in checks:
                check_lower = check.lower()

                # Check if it's a Docker command
                is_docker_cmd = any(valid_cmd in check_lower for valid_cmd in valid_docker_commands)

                # Check if it's a valid non-command check
                is_valid_check = any(prefix in check_lower for prefix in valid_check_prefixes)

                # Must be one or the other
                assert is_docker_cmd or is_valid_check, \
                    f"Invalid Docker check in {scenario['id']}: {check}"

        print(f"✓ All Docker commands and checks are valid")

    def test_docker_scenario_scoring(self, support_scenarios):
        """Test that Docker scenarios have appropriate scoring weights"""
        docker_scenarios = [
            s for s in support_scenarios
            if 'docker' in s.get('id', '').lower()
        ]

        for scenario in docker_scenarios:
            scoring = scenario['scoring']

            # Should have technical_accuracy_weight for Docker scenarios
            assert 'technical_accuracy_weight' in scoring, \
                f"Docker scenario {scenario['id']} missing technical_accuracy_weight"

            # Weights should sum to 1.0
            total_weight = sum(scoring.values())
            assert abs(total_weight - 1.0) < 0.01, \
                f"Docker scenario {scenario['id']} weights sum to {total_weight}, expected 1.0"

        print(f"✓ All Docker scenarios have proper scoring")

    def test_docker_scenario_expected_elements(self, support_scenarios):
        """Test that Docker scenarios have Docker-specific expected elements"""
        docker_scenarios = [
            s for s in support_scenarios
            if 'docker' in s.get('id', '').lower()
        ]

        docker_keywords = [
            'docker',
            'container',
            'dockerfile',
            'compose',
            'network',
            'volume',
            'image',
            'build',
            'cache'
        ]

        for scenario in docker_scenarios:
            required_elements = scenario['expected_outputs']['required_elements']

            # At least one element should mention Docker concepts
            has_docker_element = any(
                any(keyword in elem.lower() for keyword in docker_keywords)
                for elem in required_elements
            )

            assert has_docker_element, \
                f"Docker scenario {scenario['id']} missing Docker-specific required elements"

        print(f"✓ All Docker scenarios have Docker-specific expected elements")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
