"""
Integration Tests for Fine-Tuned Model Integration

Tests ModelRegistry, HALO router integration, and fallback mechanisms.
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict

# Import modules to test
from infrastructure.model_registry import ModelRegistry, ModelConfig
from infrastructure.halo_router import HALORouter
from infrastructure.ab_testing import ABTestController
from infrastructure.config_loader import ConfigLoader


class TestModelRegistry:
    """Test ModelRegistry functionality"""
    
    def test_model_registry_initialization(self):
        """Test ModelRegistry can be initialized"""
        with patch.dict(os.environ, {"MISTRAL_API_KEY": "test-key"}):
            with patch('infrastructure.model_registry.Mistral'):
                registry = ModelRegistry(api_key="test-key")
                assert registry is not None
                assert registry.api_key == "test-key"
    
    def test_get_model_returns_finetuned_id(self):
        """Test get_model returns fine-tuned model ID"""
        with patch.dict(os.environ, {"MISTRAL_API_KEY": "test-key"}):
            with patch('infrastructure.model_registry.Mistral'):
                registry = ModelRegistry(api_key="test-key")
                model_id = registry.get_model("qa_agent", use_finetuned=True)
                assert "ft:open-mistral-7b" in model_id
                assert "ecc3829c" in model_id  # QA agent model ID
    
    def test_get_model_returns_fallback_id(self):
        """Test get_model returns fallback model ID when use_finetuned=False"""
        with patch.dict(os.environ, {"MISTRAL_API_KEY": "test-key"}):
            with patch('infrastructure.model_registry.Mistral'):
                registry = ModelRegistry(api_key="test-key")
                model_id = registry.get_model("qa_agent", use_finetuned=False)
                assert model_id == "open-mistral-7b"
    
    def test_get_model_unknown_agent(self):
        """Test get_model handles unknown agent gracefully"""
        with patch.dict(os.environ, {"MISTRAL_API_KEY": "test-key"}):
            with patch('infrastructure.model_registry.Mistral'):
                registry = ModelRegistry(api_key="test-key")
                model_id = registry.get_model("unknown_agent")
                assert model_id == "open-mistral-7b"  # Default fallback
    
    def test_list_agents(self):
        """Test list_agents returns all registered agents"""
        with patch.dict(os.environ, {"MISTRAL_API_KEY": "test-key"}):
            with patch('infrastructure.model_registry.Mistral'):
                registry = ModelRegistry(api_key="test-key")
                agents = registry.list_agents()
                assert len(agents) == 5
                assert "qa_agent" in agents
                assert "support_agent" in agents
                assert "legal_agent" in agents
                assert "analyst_agent" in agents
                assert "content_agent" in agents
    
    def test_chat_with_fallback(self):
        """Test chat method falls back to baseline on error"""
        with patch.dict(os.environ, {"MISTRAL_API_KEY": "test-key"}):
            mock_client = MagicMock()
            
            # First call (fine-tuned) fails, second (fallback) succeeds
            mock_response_fallback = MagicMock()
            mock_response_fallback.choices = [MagicMock()]
            mock_response_fallback.choices[0].message.content = "Fallback response"
            
            mock_client.chat.complete.side_effect = [
                Exception("Fine-tuned model failed"),
                mock_response_fallback
            ]
            
            with patch('infrastructure.model_registry.Mistral', return_value=mock_client):
                registry = ModelRegistry(api_key="test-key")
                response = registry.chat(
                    "qa_agent",
                    [{"role": "user", "content": "test"}],
                    use_finetuned=True,
                    use_fallback=True
                )
                assert response == "Fallback response"
                assert mock_client.chat.complete.call_count == 2


class TestHALORouterIntegration:
    """Test HALO router integration with ModelRegistry"""
    
    def test_halo_router_with_model_registry(self):
        """Test HALO router can be initialized with ModelRegistry"""
        with patch.dict(os.environ, {"MISTRAL_API_KEY": "test-key"}):
            with patch('infrastructure.model_registry.Mistral'):
                registry = ModelRegistry(api_key="test-key")
                router = HALORouter(model_registry=registry)
                assert router.model_registry is not None
                assert router.model_registry == registry
    
    def test_execute_with_finetuned_model(self):
        """Test execute_with_finetuned_model calls ModelRegistry correctly"""
        with patch.dict(os.environ, {"MISTRAL_API_KEY": "test-key"}):
            mock_registry = MagicMock()
            mock_registry.chat.return_value = "Test response"
            
            router = HALORouter(model_registry=mock_registry)
            response = router.execute_with_finetuned_model(
                "qa_agent",
                [{"role": "user", "content": "test"}],
                use_finetuned=True
            )
            
            assert response == "Test response"
            mock_registry.chat.assert_called_once_with(
                "qa_agent",
                [{"role": "user", "content": "test"}],
                use_finetuned=True,
                use_fallback=True
            )
    
    def test_execute_without_model_registry_raises_error(self):
        """Test execute_with_finetuned_model raises error if ModelRegistry not configured"""
        router = HALORouter(model_registry=None)
        with pytest.raises(ValueError, match="ModelRegistry not configured"):
            router.execute_with_finetuned_model(
                "qa_agent",
                [{"role": "user", "content": "test"}]
            )


class TestABTesting:
    """Test A/B testing infrastructure"""
    
    def test_ab_controller_deterministic_assignment(self):
        """Test user assignment is deterministic"""
        controller = ABTestController(rollout_percentage=10)
        
        # Same user should always get same variant
        user1_variant1 = controller.should_use_finetuned("user123")
        user1_variant2 = controller.should_use_finetuned("user123")
        
        assert user1_variant1 == user1_variant2
    
    def test_ab_controller_rollout_percentage(self):
        """Test rollout percentage controls variant assignment"""
        controller = ABTestController(rollout_percentage=50)
        
        # With 50% rollout, roughly half should get fine-tuned
        assignments = [controller.should_use_finetuned(f"user{i}") for i in range(100)]
        finetuned_count = sum(assignments)
        
        # Should be roughly 50% (allow some variance)
        assert 40 <= finetuned_count <= 60
    
    def test_ab_controller_log_request(self):
        """Test log_request updates metrics"""
        controller = ABTestController()
        
        controller.log_request(
            "user1", "qa_agent", "finetuned",
            success=True, latency_ms=100.0, cost_usd=0.001
        )
        
        metrics = controller.metrics["finetuned"]
        assert metrics.total_requests == 1
        assert metrics.successful_requests == 1
        assert metrics.avg_latency_ms == 100.0
        assert metrics.avg_cost_usd == 0.001
    
    def test_ab_controller_compare_variants(self):
        """Test compare_variants returns comparison metrics"""
        controller = ABTestController()
        
        # Log some requests
        controller.log_request("user1", "qa_agent", "baseline", True, 100.0, 0.001)
        controller.log_request("user2", "qa_agent", "finetuned", True, 120.0, 0.0015)
        
        comparison = controller.compare_variants()
        
        assert "baseline" in comparison
        assert "finetuned" in comparison
        assert "comparison" in comparison
        assert comparison["baseline"]["total_requests"] == 1
        assert comparison["finetuned"]["total_requests"] == 1


class TestConfigLoader:
    """Test configuration loader"""
    
    def test_config_loader_detects_environment(self):
        """Test environment detection"""
        with patch.dict(os.environ, {"GENESIS_ENV": "production"}):
            env = ConfigLoader.detect_environment()
            assert env == "production"
    
    def test_config_loader_defaults_to_dev(self):
        """Test defaults to dev if GENESIS_ENV not set"""
        with patch.dict(os.environ, {}, clear=True):
            env = ConfigLoader.detect_environment()
            assert env == "dev"
    
    def test_config_loader_loads_dev_config(self):
        """Test loading dev configuration"""
        config = ConfigLoader.load("dev")
        assert config["environment"] == "development"
        assert config["models"]["use_finetuned"] is False
    
    def test_config_loader_expands_env_vars(self):
        """Test environment variable expansion"""
        with patch.dict(os.environ, {"MISTRAL_API_KEY": "test-key-123"}):
            config = ConfigLoader.load("dev")
            # Should expand ${MISTRAL_API_KEY}
            assert config["api_keys"]["mistral"] == "test-key-123"
    
    def test_config_loader_get_value(self):
        """Test get method retrieves nested values"""
        value = ConfigLoader.get("models.use_finetuned", env="dev")
        assert value is False


class TestEndToEndIntegration:
    """End-to-end integration tests"""
    
    def test_full_flow_model_registry_to_halo(self):
        """Test full flow: ModelRegistry → HALO router"""
        with patch.dict(os.environ, {"MISTRAL_API_KEY": "test-key"}):
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Response"
            mock_client.chat.complete.return_value = mock_response
            
            with patch('infrastructure.model_registry.Mistral', return_value=mock_client):
                registry = ModelRegistry(api_key="test-key")
                router = HALORouter(model_registry=registry)
                
                response = router.execute_with_finetuned_model(
                    "qa_agent",
                    [{"role": "user", "content": "test"}]
                )
                
                assert response == "Response"
    
    def test_ab_testing_with_model_registry(self):
        """Test A/B testing with ModelRegistry integration"""
        controller = ABTestController(rollout_percentage=10)
        
        user_id = "user123"
        variant = controller.get_model_variant("qa_agent", user_id)
        
        # Should return "finetuned" or "baseline" based on hash
        assert variant in ["finetuned", "baseline"]
        
        # Same user should get same variant
        variant2 = controller.get_model_variant("qa_agent", user_id)
        assert variant == variant2
    
    def test_fallback_mechanism(self):
        """Test fallback mechanism works end-to-end"""
        with patch.dict(os.environ, {"MISTRAL_API_KEY": "test-key"}):
            mock_client = MagicMock()
            
            # Fine-tuned fails, fallback succeeds
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Fallback"
            
            mock_client.chat.complete.side_effect = [
                Exception("Fine-tuned failed"),
                mock_response
            ]
            
            with patch('infrastructure.model_registry.Mistral', return_value=mock_client):
                registry = ModelRegistry(api_key="test-key")
                response = registry.chat(
                    "qa_agent",
                    [{"role": "user", "content": "test"}],
                    use_finetuned=True,
                    use_fallback=True
                )
                
                assert response == "Fallback"
                assert mock_client.chat.complete.call_count == 2

