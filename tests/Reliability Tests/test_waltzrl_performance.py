"""
WaltzRL Performance Measurement Script
Measures actual performance against targets:
- Conversation Agent: <150ms
- Safety Wrapper: <200ms
"""

import time
from infrastructure.safety.waltzrl_feedback_agent import (
    WaltzRLFeedbackAgent,
    FeedbackResult,
    SafetyIssue,
    SafetyCategory
)
from infrastructure.safety.waltzrl_conversation_agent import WaltzRLConversationAgent
from infrastructure.safety.waltzrl_wrapper import WaltzRLSafetyWrapper


def measure_conversation_agent_performance():
    """Measure conversation agent performance"""
    print("=" * 80)
    print("CONVERSATION AGENT PERFORMANCE TEST")
    print("=" * 80)

    agent = WaltzRLConversationAgent()

    feedback = FeedbackResult(
        safety_score=0.6,
        helpfulness_score=0.5,
        issues_found=[
            SafetyIssue(
                category=SafetyCategory.HARMFUL_CONTENT,
                severity=0.7,
                description="Test issue",
                evidence="test",
                suggestion="Fix it"
            )
        ],
        suggestions=["Fix it"],
        should_block=False
    )

    # Run 10 iterations
    times = []
    for i in range(10):
        start = time.time()
        response = agent.improve_response(
            original_response="This is a test response with test content to analyze",
            feedback=feedback
        )
        elapsed_ms = (time.time() - start) * 1000
        times.append(elapsed_ms)

    avg_time = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)
    p95_time = sorted(times)[int(len(times) * 0.95)]

    print(f"Average: {avg_time:.2f}ms")
    print(f"Min: {min_time:.2f}ms")
    print(f"Max: {max_time:.2f}ms")
    print(f"P95: {p95_time:.2f}ms")
    print(f"Target: <150ms")
    print(f"Status: {'✓ PASS' if avg_time < 150 else '✗ FAIL'}")
    print()

    return avg_time


def measure_wrapper_performance():
    """Measure safety wrapper performance"""
    print("=" * 80)
    print("SAFETY WRAPPER PERFORMANCE TEST")
    print("=" * 80)

    wrapper = WaltzRLSafetyWrapper(feedback_only_mode=False)

    # Run 10 iterations
    times = []
    for i in range(10):
        start = time.time()
        result = wrapper.wrap_agent_response(
            agent_name="test-agent",
            query="Write Python code",
            response="Here's a Python function to help you with that task"
        )
        elapsed_ms = (time.time() - start) * 1000
        times.append(elapsed_ms)

    avg_time = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)
    p95_time = sorted(times)[int(len(times) * 0.95)]

    print(f"Average: {avg_time:.2f}ms")
    print(f"Min: {min_time:.2f}ms")
    print(f"Max: {max_time:.2f}ms")
    print(f"P95: {p95_time:.2f}ms")
    print(f"Target: <200ms")
    print(f"Status: {'✓ PASS' if avg_time < 200 else '✗ FAIL'}")
    print()

    return avg_time


if __name__ == "__main__":
    print("\nWaltzRL PERFORMANCE MEASUREMENT")
    print("Date: 2025-10-22")
    print()

    conversation_avg = measure_conversation_agent_performance()
    wrapper_avg = measure_wrapper_performance()

    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Conversation Agent: {conversation_avg:.2f}ms (target: <150ms) {'✓' if conversation_avg < 150 else '✗'}")
    print(f"Safety Wrapper: {wrapper_avg:.2f}ms (target: <200ms) {'✓' if wrapper_avg < 200 else '✗'}")
    print()

    if conversation_avg < 150 and wrapper_avg < 200:
        print("✓ ALL PERFORMANCE TARGETS MET")
    else:
        print("✗ SOME PERFORMANCE TARGETS MISSED")
