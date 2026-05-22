"""
Skills Engine v3
================
Реестр и маршрутизация скиллов (модулей умений) агента.

Паттерн: Registry → Router → Executor
- Registry: хранит все зарегистрированные скиллы
- Router: выбирает подходящий скилл под задачу
- Executor: выполняет скилл с заданными параметрами

Интеграция с Hermes Agent:
- Skills compatible с agentskills.io
- Hermes может импортировать и выполнять наши скиллы как свои
"""

from .engine import SkillRegistry, SkillRouter, SkillExecutor
from .business_models import list_business_models, recommend_model

__all__ = [
    "SkillRegistry",
    "SkillRouter",
    "SkillExecutor",
    "list_business_models",
    "recommend_model",
]
