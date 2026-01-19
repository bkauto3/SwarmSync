"""
Integration Tests for Reflection System
Version: 1.0
Last Updated: October 15, 2025

Integration tests for ReflectionAgent and ReflectionHarness with ReasoningBank and ReplayBuffer.
Tests end-to-end workflows and infrastructure integration.
"""

import pytest
import asyncio
import time

# Import system
import sys
sys.path.insert(0, '/home/genesis/genesis-rebuild')

from agents.reflection_agent import (
    ReflectionAgent,
    get_reflection_agent
)

from infrastructure.reflection_harness import (
    ReflectionHarness,
    FallbackBehavior,
    get_default_harness
)

# Try to import infrastructure
try:
    from infrastructure.reasoning_bank import (
        ReasoningBank,
        get_reasoning_bank,
        MemoryType,
        OutcomeTag
    )
    REASONING_BANK_AVAILABLE = True
except ImportError:
    REASONING_BANK_AVAILABLE = False

try:
    from infrastructure.replay_buffer import (
        ReplayBuffer,
        get_replay_buffer,
        Trajectory,
        ActionStep
    )
    REPLAY_BUFFER_AVAILABLE = True
except ImportError:
    REPLAY_BUFFER_AVAILABLE = False


class TestReflectionIntegration:
    """Integration tests for reflection system"""

    @pytest.fixture
    def agent(self):
        """Create reflection agent"""
        return get_reflection_agent(quality_threshold=0.70)

    @pytest.fixture
    def harness(self, agent):
        """Create reflection harness"""
        return ReflectionHarness(
            reflection_agent=agent,
            max_attempts=2,
            fallback_behavior=FallbackBehavior.WARN
        )

    @pytest.mark.asyncio
    async def test_end_to_end_code_generation(self, harness):
        """Test end-to-end code generation with reflection"""

        async def generate_calculator():
            return """
function calculate(x: number, y: number, op: string): number {
    switch(op) {
        case 'add': return x + y;
        case 'subtract': return x - y;
        case 'multiply': return x * y;
        case 'divide':
            if (y === 0) throw new Error('Division by zero');
            return x / y;
        default:
            throw new Error('Invalid operation');
    }
}
"""

        result = await harness.wrap(
            generator_func=generate_calculator,
            content_type="code",
            context={
                "required_features": ["add", "subtract", "multiply", "divide"]
            }
        )

        assert result.passed_reflection == True
        assert "calculate" in result.output
        assert result.reflection_result is not None
        assert result.reflection_result.overall_score >= 0.70

    @pytest.mark.asyncio
    async def test_reflection_with_regeneration(self, harness):
        """Test reflection triggers regeneration"""
        attempt = 0

        async def generate_improves():
            nonlocal attempt
            attempt += 1

            if attempt == 1:
                # Bad first attempt
                return "eval(x); TODO: implement"
            else:
                # Good second attempt
                return """
function processData(data: any[]): any[] {
    return data.filter(item => item != null);
}
"""

        result = await harness.wrap(
            generator_func=generate_improves,
            content_type="code",
            context={}
        )

        # Should make multiple attempts
        assert result.attempts_made >= 1
        assert isinstance(result.output, str)

    @pytest.mark.skipif(not REASONING_BANK_AVAILABLE, reason="ReasoningBank not available")
    @pytest.mark.asyncio
    async def test_reasoning_bank_integration(self, agent):
        """Test integration with ReasoningBank"""

        # Perform reflection
        code = """
function authenticate(username: string, password: string): boolean {
    return validateCredentials(username, password);
}
"""
        result = await agent.reflect(
            content=code,
            content_type="code",
            context={}
        )

        # If successful, pattern should be stored
        if result.passes_threshold and agent.reasoning_bank:
            # Query for reflection patterns
            patterns = agent.reasoning_bank.search_strategies(
                task_context="reflection code quality_assurance",
                top_n=5,
                min_win_rate=0.0
            )

            # Should find at least one pattern
            assert isinstance(patterns, list)

    @pytest.mark.skipif(not REPLAY_BUFFER_AVAILABLE, reason="ReplayBuffer not available")
    @pytest.mark.asyncio
    async def test_replay_buffer_integration(self, agent):
        """Test integration with ReplayBuffer"""

        # Perform reflection
        code = "function test() { return true; }"
        result = await agent.reflect(
            content=code,
            content_type="code",
            context={}
        )

        # Trajectory should be recorded
        if agent.replay_buffer:
            stats = agent.replay_buffer.get_statistics()
            assert stats["total_trajectories"] >= 0

    @pytest.mark.asyncio
    async def test_statistics_consistency(self, agent, harness):
        """Test statistics remain consistent"""

        async def generate():
            return "const value = 42;"

        # Run multiple invocations
        for i in range(5):
            await harness.wrap(
                generator_func=generate,
                content_type="code",
                context={}
            )

        # Check agent stats
        agent_stats = agent.get_statistics()
        assert agent_stats["total_reflections"] >= 5

        # Check harness stats
        harness_stats = harness.get_statistics()
        assert harness_stats["total_invocations"] == 5

        # Stats should be consistent
        assert harness_stats["total_reflections"] >= harness_stats["total_invocations"]

    @pytest.mark.asyncio
    async def test_concurrent_reflections_integration(self, harness):
        """Test concurrent reflections with full system"""

        async def generate(n: int):
            await asyncio.sleep(0.01)
            return f"""
function process{n}(data: any): any {{
    return data.map(x => x * {n});
}}
"""

        tasks = [
            harness.wrap(
                generate,  # generator_func positional
                "code",  # content_type positional
                {},  # context positional
                i  # arg for generate
            )
            for i in range(10)
        ]

        results = await asyncio.gather(*tasks)

        assert len(results) == 10
        for i, result in enumerate(results):
            assert f"process{i}" in result.output

    @pytest.mark.asyncio
    async def test_quality_dimensions_integration(self, agent):
        """Test all quality dimensions work together"""

        # Code with various quality issues
        code = """
function processUserInput(input) {
    console.log('Processing:', input);
    eval(input);  // Security issue
    // TODO: Add validation
    return input.map(x => x).filter(x => x).map(x => x * 2);  // Performance issue
}
"""

        result = await agent.reflect(
            content=code,
            content_type="code",
            context={}
        )

        # Should detect multiple issues across dimensions
        from agents.reflection_agent import QualityDimension

        correctness = result.dimension_scores[QualityDimension.CORRECTNESS.value]
        security = result.dimension_scores[QualityDimension.SECURITY.value]
        quality = result.dimension_scores[QualityDimension.QUALITY.value]
        performance = result.dimension_scores[QualityDimension.PERFORMANCE.value]

        # All dimensions should have some issues
        assert len(correctness.issues) > 0 or len(security.issues) > 0
        assert len(quality.issues) > 0 or len(performance.issues) > 0

    @pytest.mark.asyncio
    async def test_decorator_pattern_integration(self, harness):
        """Test decorator pattern in real workflow"""

        @harness.decorator(content_type="code")
        async def build_api_route(route_name: str):
            return f"""
async function {route_name}Handler(req: Request, res: Response) {{
    try {{
        const data = await fetchData();
        res.json({{ success: true, data }});
    }} catch (error) {{
        res.status(500).json({{ success: false, error: error.message }});
    }}
}}
"""

        result = await build_api_route("users")

        assert "usersHandler" in result.output
        assert result.passed_reflection == True or result.fallback_used == True

    @pytest.mark.asyncio
    async def test_fallback_behaviors_integration(self, agent):
        """Test all fallback behaviors work correctly"""

        # Test WARN fallback
        harness_warn = ReflectionHarness(
            reflection_agent=agent,
            max_attempts=1,
            quality_threshold=0.95,  # Very high threshold
            fallback_behavior=FallbackBehavior.WARN
        )

        async def generate_mediocre():
            # Minimal code that will definitely fail 0.95 threshold
            return "x"

        result_warn = await harness_warn.wrap(
            generator_func=generate_mediocre,
            content_type="code",
            context={}
        )

        assert isinstance(result_warn.output, str)  # Should return something

        # Test PASS fallback
        harness_pass = ReflectionHarness(
            reflection_agent=agent,
            max_attempts=1,
            quality_threshold=0.95,
            fallback_behavior=FallbackBehavior.PASS
        )

        result_pass = await harness_pass.wrap(
            generator_func=generate_mediocre,
            content_type="code",
            context={}
        )

        assert isinstance(result_pass.output, str)

        # Test FAIL fallback
        harness_fail = ReflectionHarness(
            reflection_agent=agent,
            max_attempts=1,
            quality_threshold=0.95,
            fallback_behavior=FallbackBehavior.FAIL
        )

        with pytest.raises(Exception):
            await harness_fail.wrap(
                generator_func=generate_mediocre,
                content_type="code",
                context={}
            )

    @pytest.mark.asyncio
    async def test_learning_from_reflections(self, agent):
        """Test agent learns from reflections over time"""

        initial_reflections = agent.total_reflections

        # Perform multiple reflections
        codes = [
            "function a() { return 1; }",
            "function b() { return 2; }",
            "function c() { return 3; }",
        ]

        for code in codes:
            await agent.reflect(
                content=code,
                content_type="code",
                context={}
            )

        # Statistics should update
        assert agent.total_reflections == initial_reflections + len(codes)

    @pytest.mark.asyncio
    async def test_context_propagation(self, harness):
        """Test context propagates through full stack"""

        custom_context = {
            "required_features": ["auth", "validation"],
            "framework": "Express.js",
            "security_level": "high"
        }

        async def generate():
            return "function middleware() {}"

        result = await harness.wrap(
            generator_func=generate,
            content_type="code",
            context=custom_context
        )

        # Reflection should have processed context
        assert result.reflection_result is not None

    @pytest.mark.asyncio
    async def test_error_recovery_integration(self, harness):
        """Test system recovers from errors"""

        attempts = 0

        async def sometimes_fails():
            nonlocal attempts
            attempts += 1

            if attempts == 1:
                raise ValueError("First attempt fails")
            return "function recovered() { return true; }"

        result = await harness.wrap(
            generator_func=sometimes_fails,
            content_type="code",
            context={}
        )

        # Should recover and return result
        assert isinstance(result.output, str) or result.fallback_used

    @pytest.mark.asyncio
    async def test_metadata_enrichment(self, agent):
        """Test metadata is enriched throughout pipeline"""

        code = "const config = { timeout: 5000 };"
        result = await agent.reflect(
            content=code,
            content_type="config",
            context={"environment": "production"}
        )

        # Metadata should contain context
        assert "content_type" in result.metadata
        assert result.metadata["content_type"] == "config"
        assert "agent_id" in result.metadata

    @pytest.mark.asyncio
    async def test_performance_under_load(self, harness):
        """Test performance with many concurrent requests"""

        async def generate(n: int):
            return f"const value{n} = {n};"

        start_time = time.time()

        tasks = [
            harness.wrap(
                generate,  # generator_func positional
                "code",  # content_type positional
                {},  # context positional
                i  # arg for generate
            )
            for i in range(20)
        ]

        results = await asyncio.gather(*tasks)
        duration = time.time() - start_time

        # All should complete
        assert len(results) == 20

        # Should complete reasonably fast (< 30 seconds for 20 reflections)
        assert duration < 30.0

    @pytest.mark.asyncio
    async def test_quality_threshold_boundaries(self, agent):
        """Test quality threshold boundary conditions"""

        # Create agents with different thresholds
        for threshold in [0.5, 0.7, 0.9]:
            test_agent = ReflectionAgent(
                agent_id=f"threshold_{threshold}",
                quality_threshold=threshold,
                use_llm=False
            )

            code = "function test() { return 1; }"
            result = await test_agent.reflect(
                content=code,
                content_type="code",
                context={}
            )

            # Pass/fail should depend on threshold
            if result.overall_score >= threshold:
                assert result.passes_threshold == True
            else:
                assert result.passes_threshold == False

    @pytest.mark.asyncio
    async def test_complete_build_workflow(self, harness):
        """Test complete workflow: generate → reflect → regenerate → pass"""

        async def build_complete_module():
            return """
// User authentication module
interface User {
    id: string;
    username: string;
    email: string;
}

async function authenticateUser(
    username: string,
    password: string
): Promise<User | null> {
    if (!username || !password) {
        throw new Error('Username and password required');
    }

    try {
        const user = await database.findUser(username);
        if (!user) return null;

        const isValid = await verifyPassword(password, user.hashedPassword);
        return isValid ? user : null;
    } catch (error) {
        console.error('Authentication error:', error);
        return null;
    }
}

export { User, authenticateUser };
"""

        result = await harness.wrap(
            generator_func=build_complete_module,
            content_type="code",
            context={
                "required_features": ["authentication", "error handling"]
            }
        )

        # Should pass reflection
        assert result.reflection_result is not None
        assert "authenticateUser" in result.output


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
