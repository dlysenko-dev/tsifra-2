"""
Skills Engine — ядро системы скиллов.

Архитектура:
    SkillRegistry   → хранит все skills по имени
    SkillRouter     → выбирает skill по intent / описанию задачи
    SkillExecutor   → запускает skill с валидацией параметров

Совместимость:
    - agentskills.io (future)
    - Hermes Agent skills (future integration)
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class SkillDefinition:
    """Описание одного skill'а."""

    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    handler: Optional[Callable[..., Any]] = None
    category: str = "general"
    version: str = "1.0.0"


class SkillRegistry:
    """Реестр всех доступных skills."""

    def __init__(self) -> None:
        self.skills: Dict[str, SkillDefinition] = {}
        self._register_builtin_skills()

    def register(
        self,
        name: str,
        description: str,
        handler: Optional[Callable[..., Any]] = None,
        parameters: Optional[Dict[str, Any]] = None,
        category: str = "general",
        version: str = "1.0.0",
    ) -> None:
        """Зарегистрировать skill в реестре."""
        self.skills[name] = SkillDefinition(
            name=name,
            description=description,
            handler=handler,
            parameters=parameters or {},
            category=category,
            version=version,
        )

    def get(self, name: str) -> Optional[SkillDefinition]:
        """Получить skill по имени."""
        return self.skills.get(name)

    def list_skills(self, category: Optional[str] = None) -> List[str]:
        """Список имён skills. Опционально фильтр по категории."""
        if category:
            return [s.name for s in self.skills.values() if s.category == category]
        return list(self.skills.keys())

    def _register_builtin_skills(self) -> None:
        """Регистрация встроенных skills."""
        # Content skills
        self.register(
            name="create_post",
            description="Создать пост для соцсетей (Telegram, Instagram, etc.)",
            parameters={
                "topic": {"type": "string", "required": True},
                "style": {"type": "string", "required": False, "default": "expert"},
                "length": {"type": "string", "required": False, "default": "medium"},
                "platform": {"type": "string", "required": False, "default": "telegram"},
            },
            category="content",
        )
        self.register(
            name="create_script",
            description="Создать сценарий для видео (шортс, ролик)",
            parameters={
                "topic": {"type": "string", "required": True},
                "duration": {"type": "integer", "required": False, "default": 30},
                "style": {"type": "string", "required": False, "default": "educational"},
            },
            category="content",
        )

        # Video skills
        self.register(
            name="generate_shorts",
            description="Сгенерировать шортс (видео до 60 сек)",
            parameters={
                "topic": {"type": "string", "required": True},
                "style": {"type": "string", "required": False, "default": "hybrid"},
                "duration": {"type": "integer", "required": False, "default": 15},
            },
            category="video",
        )

        # Intel skills
        self.register(
            name="research_competitors",
            description="Провести анализ конкурентов в нише",
            parameters={
                "niche": {"type": "string", "required": True},
                "depth": {"type": "string", "required": False, "default": "medium"},
            },
            category="intel",
        )
        self.register(
            name="monitor_trends",
            description="Мониторинг трендов по ключевым словам",
            parameters={
                "keywords": {"type": "array", "required": True},
                "sources": {"type": "array", "required": False, "default": ["rss", "hackernews"]},
            },
            category="intel",
        )

        # Dev skills
        self.register(
            name="generate_code",
            description="Сгенерировать код на указанном языке",
            parameters={
                "description": {"type": "string", "required": True},
                "language": {"type": "string", "required": False, "default": "python"},
            },
            category="dev",
        )

        # Sell skills
        self.register(
            name="create_proposal",
            description="Создать коммерческое предложение",
            parameters={
                "client_name": {"type": "string", "required": True},
                "service": {"type": "string", "required": True},
                "budget": {"type": "string", "required": False, "default": "flexible"},
            },
            category="sell",
        )


class SkillRouter:
    """Маршрутизатор: выбирает skill под задачу."""

    def __init__(self, registry: SkillRegistry) -> None:
        self.registry = registry

    def route(self, task_description: str) -> Optional[str]:
        """Эвристический роутинг по ключевым словам.

        Returns:
            Имя skill'а или None, если не удалось определить.
        """
        lowered = task_description.lower()

        # Video
        if any(w in lowered for w in ["видео", "видос", "шортс", "shorts", "ролик", "video", "clip"]):
            return "generate_shorts"

        # Content
        if any(w in lowered for w in ["пост", "статья", "content", "публикация", "текст", "пост", "script", "сценарий"]):
            if "сценарий" in lowered or "script" in lowered:
                return "create_script"
            return "create_post"

        # Intel
        if any(w in lowered for w in ["конкурент", "монитор", "парс", "intel", "разведка", "данные", "тренд", "trend"]):
            if "тренд" in lowered or "trend" in lowered:
                return "monitor_trends"
            return "research_competitors"

        # Dev
        if any(w in lowered for w in ["код", "баг", "фикс", "debug", "refactor", "deploy", "git", "commit", "api", "script"]):
            return "generate_code"

        # Sell
        if any(w in lowered for w in ["клиент", "продаж", "crm", "lead", "предложение", "proposal", "воронка", "funnel"]):
            return "create_proposal"

        return None

    def route_with_llm(self, task_description: str, llm_router=None) -> Optional[str]:
        """LLM-based роутинг (если доступен LLM Router).

        Fallback на эвристический роутинг.
        """
        if llm_router is None:
            return self.route(task_description)

        prompt = (
            f"Выбери подходящий skill для задачи. Доступные skills:\n"
            f"{', '.join(self.registry.list_skills())}\n\n"
            f"Задача: {task_description}\n\n"
            f"Ответ (только имя skill'а):"
        )
        try:
            response = asyncio.get_event_loop().run_until_complete(
                llm_router.complete(prompt, max_tokens=20, temperature=0.0)
            )
            skill_name = response.strip().lower()
            if skill_name in self.registry.skills:
                return skill_name
        except Exception:
            pass

        return self.route(task_description)


class SkillExecutor:
    """Исполнитель: запускает skill с валидацией параметров."""

    def __init__(
        self,
        registry: SkillRegistry,
        llm_router=None,
        mcp_layer=None,
    ) -> None:
        self.registry = registry
        self.llm = llm_router
        self.mcp = mcp_layer

    async def execute(self, skill_name: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Выполнить skill по имени с параметрами.

        Args:
            skill_name: Имя зарегистрированного skill'а.
            params: Параметры для skill'а.

        Returns:
            Результат выполнения или ошибка.
        """
        params = params or {}
        skill = self.registry.get(skill_name)

        if not skill:
            return {
                "success": False,
                "error": f"Skill '{skill_name}' not found. Available: {self.registry.list_skills()}",
            }

        # Валидация обязательных параметров
        missing = []
        for param_name, cfg in skill.parameters.items():
            if cfg.get("required", False) and param_name not in params:
                missing.append(param_name)

        if missing:
            return {
                "success": False,
                "error": f"Missing required params for '{skill_name}': {missing}",
            }

        # Заполнение дефолтов
        for param_name, cfg in skill.parameters.items():
            if param_name not in params and "default" in cfg:
                params[param_name] = cfg["default"]

        # Выполнение
        try:
            if skill.handler:
                if asyncio.iscoroutinefunction(skill.handler):
                    result = await skill.handler(**params)
                else:
                    result = skill.handler(**params)
                return {"success": True, "result": result, "skill": skill_name}

            # Если handler не задан — fallback на LLM
            if self.llm:
                prompt = (
                    f"Выполни задачу как skill '{skill_name}': {skill.description}\n"
                    f"Параметры: {json.dumps(params, ensure_ascii=False)}\n\n"
                    f"Результат:"
                )
                result = await self.llm.complete(prompt, max_tokens=1000)
                return {"success": True, "result": result, "skill": skill_name, "mode": "llm_fallback"}

            return {
                "success": False,
                "error": f"Skill '{skill_name}' has no handler and no LLM router available",
            }

        except Exception as exc:
            return {
                "success": False,
                "error": f"{type(exc).__name__}: {exc}",
                "skill": skill_name,
            }
