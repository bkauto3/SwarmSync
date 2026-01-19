"""
Tests for Product Generation System

Tests cover:
- SaaS application generation
- Content website generation
- E-commerce store generation
- Product validation (security, quality)
- Integration with GenesisMetaAgent
"""

import asyncio
import os
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path

# Skip all tests if Anthropic SDK not available
pytest.importorskip("anthropic", reason="Anthropic SDK required for product generation tests")

from infrastructure.products.product_generator import (
    ProductGenerator,
    ProductRequirements,
    BusinessType,
    GeneratedProduct
)
from infrastructure.products.product_validator import (
    ProductValidator,
    ValidationResult,
    ValidationIssue,
    Severity,
    SecurityIssue
)


# ====================  FIXTURES ====================

@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client for testing without API calls."""
    mock_response = Mock()
    mock_response.content = [Mock(text="""```filename: package.json
{
  "name": "test-app",
  "version": "1.0.0",
  "dependencies": {
    "next": "14.3.0",
    "react": "18.0.0"
  }
}
```

```filename: app/page.tsx
export default function Home() {
  return <div>Hello World</div>
}
```

```filename: app/layout.tsx
export default function RootLayout({ children }) {
  return <html><body>{children}</body></html>
}
```""")]

    mock_client = Mock()
    mock_client.messages.create = Mock(return_value=mock_response)

    return mock_client


@pytest.fixture
def sample_saas_requirements():
    """Sample requirements for SaaS application."""
    return ProductRequirements(
        business_type=BusinessType.SAAS,
        name="TaskFlow Pro",
        description="Project management tool for remote teams",
        features=[
            "User authentication",
            "Task creation and management",
            "Team collaboration",
            "Real-time updates",
            "Dashboard analytics"
        ],
        target_audience="Remote teams and freelancers",
        monetization_model="Subscription ($9/month, $49/month, $99/month)"
    )


@pytest.fixture
def sample_content_requirements():
    """Sample requirements for content website."""
    return ProductRequirements(
        business_type=BusinessType.CONTENT,
        name="TechBlog Daily",
        description="Technology news and tutorials",
        features=[
            "Blog posts with MDX",
            "Author profiles",
            "Categories and tags",
            "Search functionality",
            "RSS feed"
        ],
        target_audience="Developers and tech enthusiasts",
        monetization_model="Advertising and sponsored posts"
    )


@pytest.fixture
def sample_ecommerce_requirements():
    """Sample requirements for e-commerce store."""
    return ProductRequirements(
        business_type=BusinessType.ECOMMERCE,
        name="Artisan Market",
        description="Handmade crafts and artisan products",
        features=[
            "Product catalog",
            "Shopping cart",
            "Stripe checkout",
            "Order management",
            "Admin dashboard"
        ],
        target_audience="Craft enthusiasts and gift shoppers",
        monetization_model="Product sales with 10% platform fee"
    )


@pytest.fixture
def sample_generated_files():
    """Sample generated files for validation testing."""
    return {
        "package.json": '{"name": "test", "dependencies": {}}',
        "app/page.tsx": """
export default function Home() {
  return <div>Hello</div>
}
""",
        "app/api/data/route.ts": """
import { NextResponse } from 'next/server'

export async function GET(request: Request) {
  try {
    const data = await fetchData()
    return NextResponse.json(data)
  } catch (error) {
    return NextResponse.json({ error: 'Failed' }, { status: 500 })
  }
}
""",
        ".env.example": """
NEXT_PUBLIC_API_URL=https://api.example.com
DATABASE_URL=postgresql://localhost:5432/db
"""
    }


# ==================== PRODUCT GENERATOR TESTS ====================

class TestProductGenerator:
    """Tests for ProductGenerator class."""

    def test_init_without_api_key(self):
        """Test initialization without API key logs warning."""
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': ''}, clear=False):
            with patch('infrastructure.product_generator.logger') as mock_logger:
                generator = ProductGenerator(anthropic_api_key=None)
                assert generator.client is None
                mock_logger.warning.assert_called_once()

    def test_init_with_api_key(self):
        """Test initialization with API key creates client."""
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'}):
            generator = ProductGenerator()
            assert generator.client is not None
            assert generator.api_key == 'test-key'

    def test_generation_model_configuration(self):
        """Test correct models are configured."""
        generator = ProductGenerator(anthropic_api_key='test-key')
        assert generator.generation_model == "claude-sonnet-4-20250514"
        assert generator.validation_model == "claude-haiku-4-20250514"

    @pytest.mark.asyncio
    async def test_generate_saas_basic(self, sample_saas_requirements, mock_anthropic_client):
        """Test basic SaaS generation workflow."""
        generator = ProductGenerator(anthropic_api_key='test-key')
        generator.client = mock_anthropic_client

        product = await generator.generate_saas_application(
            requirements=sample_saas_requirements,
            use_cache=False
        )

        assert isinstance(product, GeneratedProduct)
        assert product.product_type == BusinessType.SAAS
        assert len(product.files) > 0
        assert "package.json" in product.files
        assert "Supabase" in product.tech_stack

    @pytest.mark.asyncio
    async def test_generate_content_basic(self, sample_content_requirements, mock_anthropic_client):
        """Test basic content website generation workflow."""
        generator = ProductGenerator(anthropic_api_key='test-key')
        generator.client = mock_anthropic_client

        product = await generator.generate_content_website(
            requirements=sample_content_requirements,
            use_cache=False
        )

        assert isinstance(product, GeneratedProduct)
        assert product.product_type == BusinessType.CONTENT
        assert len(product.files) > 0
        assert "MDX" in product.tech_stack

    @pytest.mark.asyncio
    async def test_generate_ecommerce_basic(self, sample_ecommerce_requirements, mock_anthropic_client):
        """Test basic e-commerce generation workflow."""
        generator = ProductGenerator(anthropic_api_key='test-key')
        generator.client = mock_anthropic_client

        product = await generator.generate_ecommerce_store(
            requirements=sample_ecommerce_requirements,
            use_cache=False
        )

        assert isinstance(product, GeneratedProduct)
        assert product.product_type == BusinessType.ECOMMERCE
        assert len(product.files) > 0
        assert "Stripe" in product.tech_stack
        assert "Prisma" in product.tech_stack

    @pytest.mark.asyncio
    async def test_generate_product_routing(self, sample_saas_requirements, mock_anthropic_client):
        """Test product generation routes to correct generator."""
        generator = ProductGenerator(anthropic_api_key='test-key')
        generator.client = mock_anthropic_client

        product = await generator.generate_product(
            requirements=sample_saas_requirements,
            use_cache=False
        )

        assert product.product_type == BusinessType.SAAS
        assert product.generation_time_seconds > 0

    @pytest.mark.asyncio
    async def test_template_caching(self, sample_saas_requirements, mock_anthropic_client):
        """Test template caching reduces API calls."""
        generator = ProductGenerator(anthropic_api_key='test-key')
        generator.client = mock_anthropic_client

        # First call - should hit API
        await generator.generate_saas_application(sample_saas_requirements, use_cache=False)
        call_count_1 = mock_anthropic_client.messages.create.call_count

        # Second call with cache - should use cache
        await generator.generate_saas_application(sample_saas_requirements, use_cache=True)
        call_count_2 = mock_anthropic_client.messages.create.call_count

        # Should have cached template
        assert BusinessType.SAAS in generator._template_cache

    def test_prompt_builder_saas(self, sample_saas_requirements):
        """Test SaaS prompt contains all required elements."""
        generator = ProductGenerator(anthropic_api_key='test-key')
        prompt = generator._build_saas_prompt(sample_saas_requirements)

        assert "TaskFlow Pro" in prompt
        assert "Supabase" in prompt
        assert "authentication" in prompt.lower()
        assert "Next.js 14" in prompt

    def test_file_parsing(self):
        """Test parsing generated code into files."""
        generator = ProductGenerator(anthropic_api_key='test-key')

        generated_code = """```filename: package.json
{"name": "test"}
```

```filename: app/page.tsx
export default function Page() {}
```"""

        files = generator._parse_generated_files(generated_code)

        assert len(files) == 2
        assert "package.json" in files
        assert "app/page.tsx" in files
        assert '{"name": "test"}' in files["package.json"]

    def test_gitignore_generation(self):
        """Test .gitignore file generation."""
        generator = ProductGenerator(anthropic_api_key='test-key')
        gitignore = generator._generate_gitignore()

        assert "node_modules" in gitignore
        assert ".env" in gitignore
        assert ".next/" in gitignore

    def test_environment_variables_saas(self, sample_saas_requirements):
        """Test SaaS environment variable generation."""
        generator = ProductGenerator(anthropic_api_key='test-key')
        env_vars = generator._generate_saas_env_vars(sample_saas_requirements)

        assert "NEXT_PUBLIC_SUPABASE_URL" in env_vars
        assert "NEXT_PUBLIC_SUPABASE_ANON_KEY" in env_vars

    def test_prisma_schema_generation(self, sample_ecommerce_requirements):
        """Test Prisma schema generation for e-commerce."""
        generator = ProductGenerator(anthropic_api_key='test-key')
        schema_files = generator._generate_prisma_schema(sample_ecommerce_requirements)

        assert "prisma/schema.prisma" in schema_files
        schema = schema_files["prisma/schema.prisma"]
        assert "model Product" in schema
        assert "model Order" in schema
        assert "model User" in schema


# ==================== PRODUCT VALIDATOR TESTS ====================

class TestProductValidator:
    """Tests for ProductValidator class."""

    def test_init_without_llm(self):
        """Test initialization without LLM validation."""
        validator = ProductValidator(use_llm_validation=False)
        assert validator.client is None

    def test_security_patterns_initialized(self):
        """Test security patterns are properly initialized."""
        validator = ProductValidator()
        assert SecurityIssue.SQL_INJECTION in validator.security_patterns
        assert SecurityIssue.XSS in validator.security_patterns
        assert len(validator.security_patterns[SecurityIssue.SQL_INJECTION]) > 0

    @pytest.mark.asyncio
    async def test_validate_product_basic(self, sample_generated_files):
        """Test basic product validation."""
        validator = ProductValidator()

        result = await validator.validate_product(
            files=sample_generated_files,
            required_features=["API routes", "error handling"],
            business_type="saas"
        )

        assert isinstance(result, ValidationResult)
        assert 0 <= result.quality_score <= 100
        assert isinstance(result.security_issues, list)
        assert isinstance(result.quality_issues, list)

    @pytest.mark.asyncio
    async def test_security_detection_sql_injection(self):
        """Test SQL injection detection."""
        validator = ProductValidator()

        files = {
            "api/query.ts": """
export async function query(userInput: string) {
  return execute(`SELECT * FROM users WHERE id = ${userInput}`)
}
"""
        }

        result = await validator.validate_product(
            files=files,
            required_features=[],
            business_type="saas"
        )

        sql_issues = [i for i in result.security_issues if i.type == SecurityIssue.SQL_INJECTION.value]
        assert len(sql_issues) > 0

    @pytest.mark.asyncio
    async def test_security_detection_xss(self):
        """Test XSS detection."""
        validator = ProductValidator()

        files = {
            "component.tsx": """
export function Component({ html }) {
  return <div dangerouslySetInnerHTML={{__html: html}} />
}
"""
        }

        result = await validator.validate_product(
            files=files,
            required_features=[],
            business_type="saas"
        )

        xss_issues = [i for i in result.security_issues if i.type == SecurityIssue.XSS.value]
        assert len(xss_issues) > 0

    @pytest.mark.asyncio
    async def test_quality_detection_typescript_any(self):
        """Test TypeScript 'any' type detection."""
        validator = ProductValidator()

        files = {
            "utils.ts": """
export function process(data: any) {
  return data.value
}
"""
        }

        result = await validator.validate_product(
            files=files,
            required_features=[],
            business_type="saas"
        )

        any_issues = [i for i in result.quality_issues if i.type == "typescript_any"]
        assert len(any_issues) > 0

    @pytest.mark.asyncio
    async def test_missing_error_handling_detection(self):
        """Test detection of missing error handling in API routes."""
        validator = ProductValidator()

        files = {
            "app/api/data/route.ts": """
export async function GET() {
  const data = await fetchData()
  return Response.json(data)
}
"""
        }

        result = await validator.validate_product(
            files=files,
            required_features=[],
            business_type="saas"
        )

        error_issues = [i for i in result.quality_issues if i.type == "missing_error_handling"]
        assert len(error_issues) > 0

    @pytest.mark.asyncio
    async def test_feature_completeness_validation(self):
        """Test feature completeness validation."""
        validator = ProductValidator()

        files = {
            "lib/auth.ts": "export function signIn() {}",
            "lib/db.ts": "export const db = prisma",
            "app/api/route.ts": "export async function GET() {}"
        }

        result = await validator.validate_product(
            files=files,
            required_features=["authentication", "database", "api_routes"],
            business_type="saas"
        )

        assert result.feature_completeness["authentication"] is True
        assert result.feature_completeness["database"] is True
        assert result.feature_completeness["api_routes"] is True

    @pytest.mark.asyncio
    async def test_quality_score_calculation(self):
        """Test quality score calculation with various issues."""
        validator = ProductValidator()

        # Perfect code - should score high
        perfect_files = {
            "page.tsx": "export default function Page() { return <div>Hello</div> }"
        }

        result = await validator.validate_product(
            files=perfect_files,
            required_features=[],
            business_type="saas"
        )

        assert result.quality_score >= 90  # Should be very high for simple valid code

    @pytest.mark.asyncio
    async def test_strict_mode_with_critical_issues(self):
        """Test strict mode fails on critical security issues."""
        validator = ProductValidator(strict_mode=True)

        files = {
            "api.py": """
import subprocess
subprocess.call(user_input, shell=True)
"""
        }

        result = await validator.validate_product(
            files=files,
            required_features=[],
            business_type="saas"
        )

        assert result.passed is False  # Should fail in strict mode

    def test_severity_mapping(self):
        """Test severity levels are correctly mapped."""
        validator = ProductValidator()

        assert validator._get_security_severity(SecurityIssue.SQL_INJECTION) == Severity.CRITICAL
        assert validator._get_security_severity(SecurityIssue.INSECURE_COOKIE) == Severity.MEDIUM

    def test_recommendations_generation(self):
        """Test actionable recommendations are generated."""
        validator = ProductValidator()

        security_issues = [
            ValidationIssue(
                type="sql_injection",
                severity=Severity.CRITICAL,
                message="SQL injection",
                file="api.ts"
            )
        ]

        recommendations = validator._generate_recommendations(
            security_issues=security_issues,
            quality_issues=[],
            feature_completeness={}
        )

        assert len(recommendations) > 0
        assert any("CRITICAL" in rec for rec in recommendations)


# ==================== INTEGRATION TESTS ====================

class TestProductGenerationIntegration:
    """Integration tests for product generation with GenesisMetaAgent."""

    @pytest.mark.asyncio
    async def test_end_to_end_saas_generation(self, sample_saas_requirements, mock_anthropic_client):
        """Test complete SaaS generation and validation flow."""
        generator = ProductGenerator(anthropic_api_key='test-key')
        validator = ProductValidator()
        generator.client = mock_anthropic_client

        # Generate
        product = await generator.generate_product(sample_saas_requirements)

        # Validate
        result = await validator.validate_product(
            files=product.files,
            required_features=sample_saas_requirements.features,
            business_type=sample_saas_requirements.business_type.value
        )

        assert product.generation_time_seconds > 0
        assert result.quality_score > 0
        assert len(product.files) >= 3  # At least package.json, page, layout

    @pytest.mark.asyncio
    async def test_fallback_to_static_on_error(self):
        """Test graceful fallback when generation fails."""
        generator = ProductGenerator(anthropic_api_key='test-key')

        # Force error by using invalid client
        generator.client = None

        try:
            # Should raise RuntimeError
            with pytest.raises(RuntimeError):
                await generator._call_claude_for_generation(
                    prompt="test",
                    business_type=BusinessType.SAAS,
                    use_cache=False
                )
        except RuntimeError as exc:
            assert "Anthropic client not initialized" in str(exc)

    @pytest.mark.asyncio
    async def test_multiple_business_types(self, mock_anthropic_client):
        """Test generating different business types."""
        generator = ProductGenerator(anthropic_api_key='test-key')
        generator.client = mock_anthropic_client

        types = [
            (BusinessType.SAAS, "SaaS App"),
            (BusinessType.CONTENT, "Blog Site"),
            (BusinessType.ECOMMERCE, "Online Store")
        ]

        for btype, name in types:
            reqs = ProductRequirements(
                business_type=btype,
                name=name,
                description=f"Test {name}",
                features=["Feature 1", "Feature 2"],
                target_audience="Users",
                monetization_model="Free"
            )

            product = await generator.generate_product(reqs)
            assert product.product_type == btype
            assert len(product.files) > 0


# ==================== EDGE CASE TESTS ====================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_features_list(self):
        """Test handling empty features list."""
        generator = ProductGenerator(anthropic_api_key='test-key')

        reqs = ProductRequirements(
            business_type=BusinessType.SAAS,
            name="Test",
            description="Test app",
            features=[],  # Empty
            target_audience="Users",
            monetization_model="Free"
        )

        prompt = generator._build_saas_prompt(reqs)
        assert "Required Features:" in prompt  # Should still build valid prompt

    @pytest.mark.asyncio
    async def test_validator_with_empty_files(self):
        """Test validator handles empty file dict."""
        validator = ProductValidator()

        result = await validator.validate_product(
            files={},
            required_features=[],
            business_type="saas"
        )

        assert result.quality_score >= 0
        assert len(result.security_issues) == 0

    def test_invalid_file_parsing(self):
        """Test parser handles malformed code blocks."""
        generator = ProductGenerator(anthropic_api_key='test-key')

        malformed = """No code blocks here"""

        files = generator._parse_generated_files(malformed)
        assert len(files) == 0  # Should return empty dict, not crash

    @pytest.mark.asyncio
    async def test_concurrent_generations(self, sample_saas_requirements, mock_anthropic_client):
        """Test concurrent product generations don't interfere."""
        generator = ProductGenerator(anthropic_api_key='test-key')
        generator.client = mock_anthropic_client

        tasks = [
            generator.generate_product(sample_saas_requirements)
            for _ in range(3)
        ]

        products = await asyncio.gather(*tasks)

        assert len(products) == 3
        for product in products:
            assert isinstance(product, GeneratedProduct)

    @pytest.mark.asyncio
    async def test_rate_limiting(self, sample_saas_requirements, mock_anthropic_client):
        """Test rate limiting enforces max generations per hour."""
        generator = ProductGenerator(anthropic_api_key='test-key')
        generator.client = mock_anthropic_client
        generator._max_generations_per_hour = 3  # Set low limit for testing

        # First 3 should succeed
        await generator.generate_saas_application(sample_saas_requirements)
        await generator.generate_saas_application(sample_saas_requirements)
        await generator.generate_saas_application(sample_saas_requirements)

        # 4th should raise ValueError
        with pytest.raises(ValueError, match="Rate limit exceeded"):
            await generator.generate_saas_application(sample_saas_requirements)

    @pytest.mark.asyncio
    async def test_fuzzy_feature_matching(self):
        """Test fuzzy feature matching detects features with partial keywords."""
        validator = ProductValidator()

        files = {
            "app/page.tsx": """
export default function HomePage() {
    // User management functionality
    return <div>Welcome</div>
}
"""
        }

        result = await validator.validate_product(
            files=files,
            required_features=["User authentication and management"],
            business_type="saas"
        )

        # Should match "User" keyword from "User authentication and management"
        assert result.feature_completeness["User authentication and management"] is True

    @pytest.mark.asyncio
    async def test_empty_critical_file_detection(self):
        """Test detection of empty critical files."""
        validator = ProductValidator()

        files = {
            "package.json": "",  # Empty critical file
            "app/page.tsx": "export default function Page() { return <div>OK</div> }"
        }

        result = await validator.validate_product(
            files=files,
            required_features=[],
            business_type="saas"
        )

        # Should have warning about empty critical file
        assert any("package.json" in warning and "empty" in warning.lower()
                  for warning in result.performance_warnings)
