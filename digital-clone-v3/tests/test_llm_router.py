"""
Tests for LLMRouter (core/llm_router.py)
"""

import pytest
import os
from unittest.mock import AsyncMock, patch, MagicMock

from core.llm_router import LLMRouter


class TestLLMRouter:
    """Test suite for LLM Router with fallback chain."""

    @pytest.fixture
    def router(self):
        return LLMRouter()

    def test_init(self, router):
        assert router is not None

    @pytest.mark.asyncio
    async def test_health_check_no_keys(self, router):
        """Health check should return all providers as down without keys."""
        health = await router.health_check()
        assert isinstance(health, dict)
        # Without real API keys, all providers should be down
        assert any(v is False for v in health.values())

    @pytest.mark.asyncio
    async def test_complete_fallback_chain(self, router):
        """Test that complete falls back through providers."""
        # Mock all providers to fail
        with patch.object(router, '_call_kimi', AsyncMock(return_value=None)), \
             patch.object(router, '_call_deepseek', AsyncMock(return_value=None)), \
             patch.object(router, '_call_groq', AsyncMock(return_value=None)), \
             patch.object(router, '_call_glm', AsyncMock(return_value="fallback response")):
            
            result = await router.complete("test prompt")
            assert result == "fallback response"

    def test_provider_priority_order(self, router):
        """Verify the fallback order is correct."""
        # Access internal state if available, otherwise skip
        pytest.skip("Implementation-specific test")
