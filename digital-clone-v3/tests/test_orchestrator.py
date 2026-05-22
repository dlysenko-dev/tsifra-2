"""
Tests for JarvisOrchestrator (core/jarvis_v3.py)
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

from core.jarvis_v3 import (
    JarvisOrchestrator,
    IntentType,
    TaskStatus,
    AutonomyLevel,
)


class TestJarvisOrchestrator:
    """Test suite for the main orchestrator."""

    @pytest.fixture
    def orchestrator(self):
        return JarvisOrchestrator()

    @pytest.fixture
    def orchestrator_with_router(self):
        orch = JarvisOrchestrator()
        router = AsyncMock()
        router.complete = AsyncMock(return_value="content")
        orch.bind_llm_router(router)
        return orch

    def test_init(self, orchestrator):
        assert orchestrator.autonomy == AutonomyLevel.MANUAL
        assert orchestrator.tasks == {}
        assert orchestrator.workers == {}

    def test_register_worker(self, orchestrator):
        worker = MagicMock()
        orchestrator.register_worker("test", worker)
        assert "test" in orchestrator.workers

    def test_set_autonomy(self, orchestrator):
        orchestrator.set_autonomy(AutonomyLevel.AUTONOMOUS)
        assert orchestrator.autonomy == AutonomyLevel.AUTONOMOUS

    def test_needs_human_approval_manual(self, orchestrator):
        assert orchestrator._needs_human_approval(IntentType.CONTENT) is True
        assert orchestrator._needs_human_approval(IntentType.VIDEO) is True

    def test_needs_human_approval_autonomous(self, orchestrator):
        orchestrator.set_autonomy(AutonomyLevel.AUTONOMOUS)
        assert orchestrator._needs_human_approval(IntentType.CONTENT) is False
        assert orchestrator._needs_human_approval(IntentType.SELL) is True

    def test_fallback_intent_classify(self, orchestrator):
        assert orchestrator._fallback_intent_classify("сделай пост") == IntentType.CONTENT
        assert orchestrator._fallback_intent_classify("сгенерируй видео") == IntentType.VIDEO
        assert orchestrator._fallback_intent_classify("привет") == IntentType.CHAT

    @pytest.mark.asyncio
    async def test_process_chat_without_router(self, orchestrator):
        result = await orchestrator.process("привет")
        assert result["intent"] == "chat"
        assert result["status"] == "done"

    @pytest.mark.asyncio
    async def test_classify_intent_with_router(self, orchestrator_with_router):
        orch = orchestrator_with_router
        orch.llm_router.complete = AsyncMock(return_value="content")
        intent = await orch._classify_intent("создай пост про AI")
        assert intent == IntentType.CONTENT

    @pytest.mark.asyncio
    async def test_plan_task_fallback(self, orchestrator):
        from core.jarvis_v3 import Task
        task = Task(id="test_1", intent=IntentType.CONTENT, description="test")
        plan = await orchestrator._plan_task(task)
        assert len(plan) == 1
        assert plan[0].thought == "Выполнить задачу: test"

    def test_get_stats_empty(self, orchestrator):
        stats = orchestrator.get_stats()
        assert stats["total_tasks"] == 0
        assert stats["avg_duration_sec"] == 0.0
