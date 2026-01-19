"""
Comprehensive Test Suite for Enhanced Security Agent v4.0
Tests all functionality including learning infrastructure integration

Test Coverage:
1. Agent initialization and setup
2. Parallel security checks (asyncio)
3. ReasoningBank integration (pattern queries and storage)
4. Replay Buffer integration (trajectory recording)
5. Reflection Harness integration (quality validation)
6. Security scoring and grading
7. Comprehensive audit workflow
8. Error handling and edge cases
9. Metrics tracking
"""

import pytest
import asyncio
import json
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch, MagicMock

# Import agent under test
import sys
sys.path.insert(0, '/home/genesis/genesis-rebuild')

from agents.security_agent import (
    EnhancedSecurityAgent,
    get_security_agent,
    SecurityScanAttempt,
    VulnerabilityPattern
)
from infrastructure.reasoning_bank import StrategyNugget, OutcomeTag
from infrastructure.replay_buffer import Trajectory, ActionStep, OutcomeTag as ReplayOutcomeTag


class TestSecurityAgentInitialization:
    """Test agent initialization and setup"""

    @pytest.mark.asyncio
    async def test_agent_creation(self):
        """Test basic agent creation"""
        agent = EnhancedSecurityAgent(business_id="test_business_001")

        assert agent.business_id == "test_business_001"
        assert agent.agent_id == "security_test_business_001"
        assert agent.agent is None  # Not initialized yet
        assert agent.metrics['total_scans'] == 0
        assert agent.metrics['successful_scans'] == 0

    @pytest.mark.asyncio
    async def test_agent_initialization_mock(self):
        """Test agent initialization with mocked Azure"""
        agent = EnhancedSecurityAgent(business_id="test_business_002")

        # Mock Azure components
        with patch('agents.security_agent.AzureCliCredential') as mock_cred, \
             patch('agents.security_agent.AzureAIAgentClient') as mock_client, \
             patch('agents.security_agent.ChatAgent') as mock_agent:

            mock_cred.return_value = Mock()
            mock_client.return_value = Mock()
            mock_agent.return_value = Mock()

            await agent.initialize()

            # Verify initialization
            assert agent.agent is not None
            assert agent.reasoning_bank is not None
            assert agent.replay_buffer is not None

    def test_security_checks_constant(self):
        """Test that security checks are properly defined"""
        assert len(EnhancedSecurityAgent.SECURITY_CHECKS) == 8
        assert "dependencies" in EnhancedSecurityAgent.SECURITY_CHECKS
        assert "ssl_configuration" in EnhancedSecurityAgent.SECURITY_CHECKS
        assert "security_headers" in EnhancedSecurityAgent.SECURITY_CHECKS


class TestParallelSecurityChecks:
    """Test parallel execution of security checks"""

    @pytest.mark.asyncio
    async def test_check_environment_variables(self):
        """Test environment variable scanning"""
        agent = EnhancedSecurityAgent(business_id="test_business_003")
        agent.trajectory_steps = []

        result = await agent._check_environment_variables(["https://test.com"])

        assert result['status'] == 'PASS'
        assert 'vulnerabilities' in result
        assert 'checked_at' in result
        assert len(agent.trajectory_steps) == 1

    @pytest.mark.asyncio
    async def test_check_dependencies(self):
        """Test dependency scanning"""
        agent = EnhancedSecurityAgent(business_id="test_business_004")
        agent.trajectory_steps = []

        result = await agent._check_dependencies_async(["https://test.com"])

        assert result['status'] == 'FAIL'  # Simulated vulnerabilities
        assert len(result['vulnerabilities']) == 2
        assert result['vulnerabilities'][0]['severity'] == 'HIGH'
        assert result['total_dependencies'] == 156

    @pytest.mark.asyncio
    async def test_check_ssl_https(self):
        """Test SSL check with HTTPS URL"""
        agent = EnhancedSecurityAgent(business_id="test_business_005")
        agent.trajectory_steps = []

        result = await agent._check_ssl_async(["https://secure.com"])

        assert result['status'] == 'PASS'
        assert len(result['vulnerabilities']) == 0

    @pytest.mark.asyncio
    async def test_check_ssl_http(self):
        """Test SSL check with HTTP URL (should fail)"""
        agent = EnhancedSecurityAgent(business_id="test_business_006")
        agent.trajectory_steps = []

        result = await agent._check_ssl_async(["http://insecure.com"])

        assert result['status'] == 'FAIL'
        assert len(result['vulnerabilities']) == 1
        assert result['vulnerabilities'][0]['severity'] == 'CRITICAL'
        assert result['vulnerabilities'][0]['type'] == 'No HTTPS'

    @pytest.mark.asyncio
    async def test_check_security_headers(self):
        """Test security headers check"""
        agent = EnhancedSecurityAgent(business_id="test_business_007")
        agent.trajectory_steps = []

        result = await agent._check_security_headers_async(["https://test.com"])

        assert result['status'] == 'PASS'
        assert 'vulnerabilities' in result

    @pytest.mark.asyncio
    async def test_check_authentication(self):
        """Test authentication check"""
        agent = EnhancedSecurityAgent(business_id="test_business_008")
        agent.trajectory_steps = []

        result = await agent._check_authentication_async(["https://test.com"])

        assert result['status'] == 'PASS'
        assert 'recommendations' in result
        assert len(result['recommendations']) > 0

    @pytest.mark.asyncio
    async def test_check_authorization(self):
        """Test authorization check"""
        agent = EnhancedSecurityAgent(business_id="test_business_009")
        agent.trajectory_steps = []

        result = await agent._check_authorization_async(["https://test.com"])

        assert result['status'] == 'FAIL'  # Simulated authorization issues
        assert len(result['vulnerabilities']) == 1
        assert result['vulnerabilities'][0]['severity'] == 'HIGH'

    @pytest.mark.asyncio
    async def test_parallel_checks_execution(self):
        """Test that multiple checks execute in parallel"""
        agent = EnhancedSecurityAgent(business_id="test_business_010")
        agent.trajectory_steps = []

        scan_types = ["environment_variables", "dependencies", "ssl_configuration"]
        mock_patterns = []

        results = await agent._conduct_parallel_checks(
            targets=["https://test.com"],
            scan_types=scan_types,
            known_patterns=mock_patterns
        )

        # Verify all checks ran
        assert len(results) == 3
        assert 'env_vars' in results
        assert 'dependencies' in results
        assert 'ssl' in results


class TestSecurityScoring:
    """Test security score calculation and grading"""

    def test_calculate_security_score_perfect(self):
        """Test score calculation with no vulnerabilities"""
        agent = EnhancedSecurityAgent(business_id="test_business_011")

        audit_results = {
            'env_vars': {'vulnerabilities': []},
            'dependencies': {'vulnerabilities': []},
            'ssl': {'vulnerabilities': []}
        }

        score = agent._calculate_security_score(audit_results)
        assert score == 100.0

    def test_calculate_security_score_critical(self):
        """Test score calculation with CRITICAL vulnerability"""
        agent = EnhancedSecurityAgent(business_id="test_business_012")

        audit_results = {
            'ssl': {
                'vulnerabilities': [
                    {'severity': 'CRITICAL', 'description': 'No HTTPS'}
                ]
            }
        }

        score = agent._calculate_security_score(audit_results)
        assert score == 90.0  # 100 - 10 for CRITICAL

    def test_calculate_security_score_mixed(self):
        """Test score calculation with mixed severities"""
        agent = EnhancedSecurityAgent(business_id="test_business_013")

        audit_results = {
            'ssl': {
                'vulnerabilities': [
                    {'severity': 'CRITICAL', 'description': 'Issue 1'}  # -10
                ]
            },
            'dependencies': {
                'vulnerabilities': [
                    {'severity': 'HIGH', 'description': 'Issue 2'},  # -5
                    {'severity': 'MEDIUM', 'description': 'Issue 3'},  # -2
                    {'severity': 'LOW', 'description': 'Issue 4'}  # -1
                ]
            }
        }

        score = agent._calculate_security_score(audit_results)
        assert score == 82.0  # 100 - 10 - 5 - 2 - 1

    def test_get_security_grade(self):
        """Test security grade mapping"""
        agent = EnhancedSecurityAgent(business_id="test_business_014")

        assert agent._get_security_grade(98) == "A+"
        assert agent._get_security_grade(92) == "A"
        assert agent._get_security_grade(87) == "B+"
        assert agent._get_security_grade(82) == "B"
        assert agent._get_security_grade(77) == "C+"
        assert agent._get_security_grade(72) == "C"
        assert agent._get_security_grade(65) == "D"
        assert agent._get_security_grade(50) == "F"


class TestReasoningBankIntegration:
    """Test ReasoningBank pattern querying and storage"""

    @pytest.mark.asyncio
    async def test_query_vulnerability_patterns(self):
        """Test querying vulnerability patterns from ReasoningBank"""
        agent = EnhancedSecurityAgent(business_id="test_business_015")
        agent.trajectory_steps = []

        # Mock ReasoningBank
        mock_reasoning_bank = Mock()
        mock_reasoning_bank.search_strategies = Mock(return_value=[
            Mock(
                pattern_id="pattern_001",
                description="SQL injection detection",
                context="security scan dependencies",
                win_rate=0.85
            )
        ])
        agent.reasoning_bank = mock_reasoning_bank

        patterns = await agent._query_vulnerability_patterns(["dependencies"])

        assert len(patterns) == 1
        assert len(agent.trajectory_steps) == 1
        mock_reasoning_bank.search_strategies.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_anti_patterns(self):
        """Test querying anti-patterns from Replay Buffer"""
        agent = EnhancedSecurityAgent(business_id="test_business_016")

        # Mock Replay Buffer
        mock_replay_buffer = Mock()
        mock_replay_buffer.query_anti_patterns = Mock(return_value=[
            {
                'strategy_id': 'anti_001',
                'failure_rationale': 'Missed XSS vulnerability',
                'error_category': 'detection_failure'
            }
        ])
        agent.replay_buffer = mock_replay_buffer

        anti_patterns = await agent._query_anti_patterns(["security_headers"])

        assert len(anti_patterns) == 1
        assert anti_patterns[0]['error_category'] == 'detection_failure'

    @pytest.mark.asyncio
    async def test_store_new_patterns(self):
        """Test storing new vulnerability patterns in ReasoningBank"""
        agent = EnhancedSecurityAgent(business_id="test_business_017")
        agent.current_scan = SecurityScanAttempt(
            scan_id="scan_123",
            business_id="test_business_017"
        )

        # Mock ReasoningBank
        mock_reasoning_bank = Mock()
        mock_reasoning_bank.store_strategy = Mock(return_value="strategy_001")
        agent.reasoning_bank = mock_reasoning_bank

        audit_results = {
            'ssl': {
                'vulnerabilities': [
                    {
                        'severity': 'CRITICAL',
                        'type': 'No HTTPS',
                        'description': 'Site not using HTTPS'
                    }
                ]
            }
        }

        await agent._store_new_patterns(audit_results)

        # Verify pattern was stored
        mock_reasoning_bank.store_strategy.assert_called_once()
        assert agent.metrics['patterns_learned'] == 1


class TestReplayBufferIntegration:
    """Test Replay Buffer trajectory recording"""

    @pytest.mark.asyncio
    async def test_record_successful_trajectory(self):
        """Test recording successful scan trajectory"""
        agent = EnhancedSecurityAgent(business_id="test_business_018")
        agent.current_scan = SecurityScanAttempt(
            scan_id="scan_456",
            business_id="test_business_018",
            scan_targets=["https://test.com"],
            vulnerabilities_found=2,
            critical_issues=0,
            security_score=95.0,
            start_time=1000.0,
            end_time=1010.0
        )
        agent.trajectory_steps = [
            ActionStep(
                timestamp=datetime.now().isoformat(),
                tool_name="check_ssl",
                tool_args={"targets": ["https://test.com"]},
                tool_result="PASS",
                agent_reasoning="Verifying SSL configuration"
            )
        ]

        # Mock Replay Buffer
        mock_replay_buffer = Mock()
        mock_replay_buffer.store_trajectory = Mock(return_value="traj_001")
        agent.replay_buffer = mock_replay_buffer

        await agent._record_scan_trajectory(
            outcome=ReplayOutcomeTag.SUCCESS,
            report={"security_score": 95.0}
        )

        # Verify trajectory was recorded
        mock_replay_buffer.store_trajectory.assert_called_once()
        call_args = mock_replay_buffer.store_trajectory.call_args[0][0]
        assert call_args.final_outcome == ReplayOutcomeTag.SUCCESS.value
        assert call_args.reward > 0.7  # Success reward

    @pytest.mark.asyncio
    async def test_record_failed_trajectory(self):
        """Test recording failed scan trajectory"""
        agent = EnhancedSecurityAgent(business_id="test_business_019")
        agent.current_scan = SecurityScanAttempt(
            scan_id="scan_789",
            business_id="test_business_019",
            scan_targets=["https://test.com"],
            error_message="Connection timeout",
            start_time=1000.0,
            end_time=1005.0
        )
        agent.trajectory_steps = []

        # Mock Replay Buffer
        mock_replay_buffer = Mock()
        mock_replay_buffer.store_trajectory = Mock(return_value="traj_002")
        agent.replay_buffer = mock_replay_buffer

        await agent._record_scan_trajectory(
            outcome=ReplayOutcomeTag.FAILURE,
            report={"error": "Connection timeout"}
        )

        # Verify trajectory was recorded with failure
        mock_replay_buffer.store_trajectory.assert_called_once()
        call_args = mock_replay_buffer.store_trajectory.call_args[0][0]
        assert call_args.final_outcome == ReplayOutcomeTag.FAILURE.value
        assert call_args.reward == 0.0  # Failure reward
        assert call_args.failure_rationale == "Connection timeout"

    def test_record_step(self):
        """Test recording individual trajectory steps"""
        agent = EnhancedSecurityAgent(business_id="test_business_020")
        agent.trajectory_steps = []

        agent._record_step(
            tool_name="check_dependencies",
            tool_args={"targets": ["https://test.com"]},
            tool_result="Found 2 vulnerabilities",
            reasoning="Scanning dependencies for CVEs"
        )

        assert len(agent.trajectory_steps) == 1
        step = agent.trajectory_steps[0]
        assert step.tool_name == "check_dependencies"
        assert step.agent_reasoning == "Scanning dependencies for CVEs"


class TestReflectionHarnessIntegration:
    """Test Reflection Harness quality validation"""

    @pytest.mark.asyncio
    async def test_validate_report_quality_pass(self):
        """Test report validation that passes reflection"""
        agent = EnhancedSecurityAgent(business_id="test_business_021")

        # Mock Reflection Harness
        mock_harness = AsyncMock()
        mock_reflection_result = Mock()
        mock_reflection_result.overall_score = 0.85
        mock_harness_result = Mock()
        mock_harness_result.passed_reflection = True
        mock_harness_result.reflection_result = mock_reflection_result
        mock_harness_result.attempts_made = 1
        mock_harness_result.fallback_used = False
        mock_harness.wrap = AsyncMock(return_value=mock_harness_result)
        agent.reflection_harness = mock_harness

        report = {
            "scan_id": "scan_123",
            "security_score": 90.0,
            "vulnerabilities": []
        }

        validated_report = await agent._validate_report_quality(report)

        assert 'reflection_metadata' in validated_report
        assert validated_report['reflection_metadata']['passed'] is True
        assert validated_report['reflection_metadata']['quality_score'] == 0.85

    @pytest.mark.asyncio
    async def test_validate_report_quality_fail(self):
        """Test report validation that fails reflection"""
        agent = EnhancedSecurityAgent(business_id="test_business_022")

        # Mock Reflection Harness
        mock_harness = AsyncMock()
        mock_reflection_result = Mock()
        mock_reflection_result.overall_score = 0.60
        mock_harness_result = Mock()
        mock_harness_result.passed_reflection = False
        mock_harness_result.reflection_result = mock_reflection_result
        mock_harness_result.attempts_made = 2
        mock_harness_result.fallback_used = True
        mock_harness.wrap = AsyncMock(return_value=mock_harness_result)
        agent.reflection_harness = mock_harness

        report = {
            "scan_id": "scan_456",
            "security_score": 75.0
        }

        validated_report = await agent._validate_report_quality(report)

        assert validated_report['reflection_metadata']['passed'] is False
        assert validated_report['reflection_metadata']['fallback_used'] is True


class TestComprehensiveAuditWorkflow:
    """Test end-to-end audit workflow"""

    @pytest.mark.asyncio
    async def test_generate_comprehensive_report(self):
        """Test comprehensive report generation"""
        agent = EnhancedSecurityAgent(business_id="test_business_023")

        audit_results = {
            'ssl': {
                'status': 'FAIL',
                'vulnerabilities': [
                    {
                        'severity': 'CRITICAL',
                        'type': 'No HTTPS',
                        'description': 'Site not using HTTPS'
                    }
                ],
                'recommendations': ['Enable HTTPS']
            },
            'dependencies': {
                'status': 'FAIL',
                'vulnerabilities': [
                    {
                        'severity': 'HIGH',
                        'cve_id': 'CVE-2024-1234',
                        'description': 'RCE vulnerability'
                    }
                ],
                'recommendations': []
            }
        }

        report = await agent._generate_comprehensive_report(
            scan_id="scan_comprehensive",
            targets=["https://test.com"],
            audit_results=audit_results,
            security_score=80.0,
            known_patterns=[]
        )

        assert report['scan_id'] == "scan_comprehensive"
        assert report['security_score'] == 80.0
        assert report['grade'] == "B"
        assert report['summary']['total_vulnerabilities'] == 2
        assert report['summary']['severity_breakdown']['CRITICAL'] == 1
        assert report['summary']['severity_breakdown']['HIGH'] == 1
        assert len(report['vulnerabilities']) == 2
        assert report['compliance']['soc2'] is True  # 80 >= 80
        assert report['compliance']['iso27001'] is False  # 80 < 85

    def test_generate_recommendations(self):
        """Test security recommendations generation"""
        agent = EnhancedSecurityAgent(business_id="test_business_024")

        audit_results = {
            'ssl': {'vulnerabilities': [], 'recommendations': ['Enable HSTS']},
            'auth': {'vulnerabilities': [], 'recommendations': ['Implement MFA']}
        }

        severity_counts = {
            'CRITICAL': 2,
            'HIGH': 1,
            'MEDIUM': 0,
            'LOW': 0
        }

        recommendations = agent._generate_recommendations(audit_results, severity_counts)

        # Check for urgent and high priority recommendations
        assert any('URGENT' in r for r in recommendations)
        assert any('High priority' in r for r in recommendations)
        assert 'Enable HSTS' in recommendations
        assert 'Implement MFA' in recommendations


class TestMetricsTracking:
    """Test metrics tracking and statistics"""

    def test_update_average_security_score(self):
        """Test security score averaging"""
        agent = EnhancedSecurityAgent(business_id="test_business_025")
        agent.metrics['total_scans'] = 0
        agent.metrics['average_security_score'] = 0.0

        # First scan
        agent.metrics['total_scans'] = 1
        agent._update_average_security_score(90.0)
        assert agent.metrics['average_security_score'] == 90.0

        # Second scan
        agent.metrics['total_scans'] = 2
        agent._update_average_security_score(80.0)
        assert agent.metrics['average_security_score'] == 85.0  # (90 + 80) / 2

        # Third scan
        agent.metrics['total_scans'] = 3
        agent._update_average_security_score(75.0)
        assert abs(agent.metrics['average_security_score'] - 81.67) < 0.01

    def test_get_metrics(self):
        """Test metrics retrieval"""
        agent = EnhancedSecurityAgent(business_id="test_business_026")
        agent.metrics = {
            'total_scans': 10,
            'successful_scans': 8,
            'vulnerabilities_found': 25,
            'vulnerabilities_fixed': 20,
            'average_security_score': 85.5,
            'patterns_learned': 5
        }

        metrics = agent.get_metrics()

        assert metrics['total_scans'] == 10
        assert metrics['successful_scans'] == 8
        assert metrics['success_rate'] == 0.8
        assert metrics['vulnerabilities_found'] == 25
        assert metrics['average_security_score'] == 85.5
        assert metrics['patterns_learned'] == 5

    def test_count_new_patterns(self):
        """Test counting new vulnerability patterns"""
        agent = EnhancedSecurityAgent(business_id="test_business_027")

        vulnerabilities = [
            {'severity': 'CRITICAL', 'description': 'Issue 1'},
            {'severity': 'HIGH', 'description': 'Issue 2'},
            {'severity': 'MEDIUM', 'description': 'Issue 3'},
            {'severity': 'LOW', 'description': 'Issue 4'}
        ]

        # Only CRITICAL and HIGH are counted as new patterns
        count = agent._count_new_patterns(vulnerabilities)
        assert count == 2


class TestToolImplementations:
    """Test individual tool functions"""

    def test_scan_vulnerabilities_tool(self):
        """Test scan_vulnerabilities tool"""
        agent = EnhancedSecurityAgent(business_id="test_business_028")

        result_json = agent.scan_vulnerabilities(
            target="https://test.com",
            scan_type="full"
        )

        result = json.loads(result_json)
        assert 'scan_id' in result
        assert result['target'] == "https://test.com"
        assert result['scan_type'] == "full"
        assert 'scanned_at' in result

    def test_conduct_security_audit_tool(self):
        """Test conduct_security_audit tool"""
        agent = EnhancedSecurityAgent(business_id="test_business_029")

        result_json = agent.conduct_security_audit(
            system_name="test_system",
            audit_scope=["auth", "authz", "encryption"]
        )

        result = json.loads(result_json)
        assert 'audit_id' in result
        assert result['system_name'] == "test_system"
        assert result['audit_scope'] == ["auth", "authz", "encryption"]
        assert 'overall_security_score' in result

    def test_monitor_threats_tool(self):
        """Test monitor_threats tool"""
        agent = EnhancedSecurityAgent(business_id="test_business_030")

        result_json = agent.monitor_threats(
            timeframe_hours=24,
            threat_types=["brute_force", "sql_injection"]
        )

        result = json.loads(result_json)
        assert 'monitoring_id' in result
        assert result['timeframe_hours'] == 24
        assert result['threat_types'] == ["brute_force", "sql_injection"]

    def test_check_dependencies_tool(self):
        """Test check_dependencies tool"""
        agent = EnhancedSecurityAgent(business_id="test_business_031")

        result_json = agent.check_dependencies(
            project_path="/path/to/project",
            package_manager="npm"
        )

        result = json.loads(result_json)
        assert 'check_id' in result
        assert result['project_path'] == "/path/to/project"
        assert result['package_manager'] == "npm"

    def test_check_ssl_configuration_tool(self):
        """Test check_ssl_configuration tool"""
        agent = EnhancedSecurityAgent(business_id="test_business_032")

        result_json = agent.check_ssl_configuration(domain="test.com")

        result = json.loads(result_json)
        assert 'check_id' in result
        assert result['domain'] == "test.com"
        assert 'certificate_valid' in result

    def test_check_security_headers_tool(self):
        """Test check_security_headers tool"""
        agent = EnhancedSecurityAgent(business_id="test_business_033")

        result_json = agent.check_security_headers(url="https://test.com")

        result = json.loads(result_json)
        assert 'check_id' in result
        assert result['url'] == "https://test.com"
        assert 'headers_present' in result

    def test_check_authentication_tool(self):
        """Test check_authentication tool"""
        agent = EnhancedSecurityAgent(business_id="test_business_034")

        result_json = agent.check_authentication(system="test_system")

        result = json.loads(result_json)
        assert 'check_id' in result
        assert result['system'] == "test_system"
        assert 'mfa_enabled' in result

    def test_generate_security_report_tool(self):
        """Test generate_security_report tool"""
        agent = EnhancedSecurityAgent(business_id="test_business_035")

        result_json = agent.generate_security_report(
            organization="test_org",
            report_period="Q4_2025"
        )

        result = json.loads(result_json)
        assert 'report_id' in result
        assert result['organization'] == "test_org"
        assert result['report_period'] == "Q4_2025"


class TestErrorHandling:
    """Test error handling and edge cases"""

    @pytest.mark.asyncio
    async def test_parallel_checks_with_exception(self):
        """Test parallel checks when one check raises exception"""
        agent = EnhancedSecurityAgent(business_id="test_business_036")
        agent.trajectory_steps = []

        # Mock a check that raises exception
        async def failing_check(targets):
            raise ValueError("Simulated check failure")

        # Patch one of the checks to fail
        with patch.object(agent, '_check_ssl_async', failing_check):
            results = await agent._conduct_parallel_checks(
                targets=["https://test.com"],
                scan_types=["ssl_configuration", "environment_variables"],
                known_patterns=[]
            )

            # SSL check should have error, env_vars should succeed
            assert 'ssl' in results
            assert 'error' in results['ssl']
            assert 'env_vars' in results
            assert results['env_vars']['status'] == 'PASS'

    def test_security_score_minimum_zero(self):
        """Test that security score never goes below zero"""
        agent = EnhancedSecurityAgent(business_id="test_business_037")

        # Create many CRITICAL vulnerabilities
        audit_results = {
            'check1': {
                'vulnerabilities': [
                    {'severity': 'CRITICAL'} for _ in range(20)  # -200 points
                ]
            }
        }

        score = agent._calculate_security_score(audit_results)
        assert score == 0.0  # Should be capped at 0, not negative


class TestFactoryFunction:
    """Test factory function for agent creation"""

    @pytest.mark.asyncio
    async def test_get_security_agent_factory(self):
        """Test get_security_agent factory function"""
        with patch('agents.security_agent.AzureCliCredential') as mock_cred, \
             patch('agents.security_agent.AzureAIAgentClient') as mock_client, \
             patch('agents.security_agent.ChatAgent') as mock_agent:

            mock_cred.return_value = Mock()
            mock_client.return_value = Mock()
            mock_agent.return_value = Mock()

            agent = await get_security_agent(business_id="factory_test")

            assert isinstance(agent, EnhancedSecurityAgent)
            assert agent.business_id == "factory_test"
            assert agent.agent is not None


# Run tests with pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
