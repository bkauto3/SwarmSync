"""
Security Agent Demo - Quick demonstration of enhanced security agent capabilities
Run with: python tests/test_security_agent_demo.py
"""

import asyncio
import sys
sys.path.insert(0, '/home/genesis/genesis-rebuild')

from agents.security_agent import EnhancedSecurityAgent


async def demo_security_agent():
    """Demonstrate security agent capabilities"""
    print("=" * 80)
    print("Enhanced Security Agent v4.0 - Demo")
    print("=" * 80)
    print()

    # Create agent (mocked for demo - no actual Azure connection)
    print("1. Creating Enhanced Security Agent...")
    agent = EnhancedSecurityAgent(business_id="demo_business")
    print(f"   Agent ID: {agent.agent_id}")
    print(f"   Business: {agent.business_id}")
    print()

    # Show security checks
    print("2. Security Check Types:")
    for i, check in enumerate(agent.SECURITY_CHECKS, 1):
        print(f"   {i}. {check}")
    print()

    # Demonstrate security scoring
    print("3. Security Scoring System:")
    test_scores = [98, 90, 85, 80, 75, 70, 60, 50]
    for score in test_scores:
        grade = agent._get_security_grade(score)
        print(f"   Score {score:3.0f}/100 = Grade {grade}")
    print()

    # Test individual checks (without Azure)
    print("4. Testing Security Checks (async parallel execution):")

    # Test environment variables check
    print("   a) Environment Variables Check...")
    env_result = await agent._check_environment_variables(["https://demo.com"])
    print(f"      Status: {env_result['status']}")
    print(f"      Vulnerabilities: {len(env_result['vulnerabilities'])}")

    # Test SSL check
    print("   b) SSL Configuration Check...")
    ssl_https = await agent._check_ssl_async(["https://secure.com"])
    ssl_http = await agent._check_ssl_async(["http://insecure.com"])
    print(f"      HTTPS URL: {ssl_https['status']} ({len(ssl_https['vulnerabilities'])} issues)")
    print(f"      HTTP URL:  {ssl_http['status']} ({len(ssl_http['vulnerabilities'])} issues)")

    # Test dependencies check
    print("   c) Dependencies Check...")
    dep_result = await agent._check_dependencies_async(["https://demo.com"])
    print(f"      Status: {dep_result['status']}")
    print(f"      Vulnerabilities: {len(dep_result['vulnerabilities'])}")
    for vuln in dep_result['vulnerabilities']:
        print(f"         - {vuln['severity']}: {vuln['package']} {vuln['cve_id']}")
    print()

    # Show metrics
    print("5. Agent Metrics:")
    metrics = agent.get_metrics()
    for key, value in metrics.items():
        print(f"   {key}: {value}")
    print()

    # Test security score calculation
    print("6. Security Score Calculation Demo:")
    audit_results = {
        'ssl': {
            'vulnerabilities': [
                {'severity': 'CRITICAL', 'description': 'No HTTPS'}
            ]
        },
        'dependencies': {
            'vulnerabilities': [
                {'severity': 'HIGH', 'cve_id': 'CVE-2024-1234', 'description': 'RCE'},
                {'severity': 'MEDIUM', 'description': 'Prototype pollution'}
            ]
        }
    }

    score = agent._calculate_security_score(audit_results)
    grade = agent._get_security_grade(score)
    print(f"   Example Audit Results:")
    print(f"   - 1 CRITICAL vulnerability (-10 points)")
    print(f"   - 1 HIGH vulnerability (-5 points)")
    print(f"   - 1 MEDIUM vulnerability (-2 points)")
    print(f"   Final Score: {score}/100 (Grade: {grade})")
    print()

    # Show recommendations generation
    print("7. Recommendations Generation:")
    severity_counts = {'CRITICAL': 1, 'HIGH': 1, 'MEDIUM': 1, 'LOW': 0}
    recommendations = agent._generate_recommendations(audit_results, severity_counts)
    print(f"   Generated {len(recommendations)} recommendations:")
    for i, rec in enumerate(recommendations[:5], 1):
        print(f"   {i}. {rec}")
    print(f"   ... and {len(recommendations) - 5} more")
    print()

    print("=" * 80)
    print("Demo Complete!")
    print()
    print("Key Features Demonstrated:")
    print("  - Async parallel security checks (8 types)")
    print("  - Security scoring and grading system")
    print("  - Vulnerability detection and categorization")
    print("  - Automated recommendations generation")
    print("  - Metrics tracking and reporting")
    print()
    print("Learning Infrastructure (requires initialization):")
    print("  - ReasoningBank: Pattern storage and retrieval")
    print("  - Replay Buffer: Trajectory recording for learning")
    print("  - Reflection Harness: Quality validation")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(demo_security_agent())
