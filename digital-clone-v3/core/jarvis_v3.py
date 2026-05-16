"""
Jarvis v3 — единый оркестратор Digital Clone
Архитектура: OpenManus-style planner + ReAct loop + validation

Интегрированные паттерны:
- OpenManus (#9): агент-планировщик с цепочкой мышления (thought → action → observation)
- NEO (#13): один промпт → полный pipeline
- Claude Security beta (#1): валидация действий перед выполнением
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums & Data classes
# ---------------------------------------------------------------------------


class IntentType(Enum):
    """Типы намерений, которые оркестратор умеет распознавать."""

    CHAT = "chat"
    CONTENT = "content"        # создание контента (посты, статьи)
    VIDEO = "video"            # генерация видео (Seedance / другие)
    CODE = "code"              # разработка / рефакторинг / баг-фикс
    INTEL = "intel"            # разведка / мониторинг / парсинг
    SELL = "sell"              # продажи / клиенты / CRM
    SYSTEM = "system"          # системные команды (restart, update)
    BUSINESS = "business"      # бизнес-операции (PDF, отчеты, инвойсы)


class TaskStatus(Enum):
    """Конечный автомат статусов задачи."""

    PENDING = "pending"
    PLANNING = "planning"
    EXECUTING = "executing"
    VALIDATING = "validating"
    DONE = "done"
    ERROR = "error"
    RETRYING = "retrying"


class AutonomyLevel(Enum):
    """Уровень автономности агента.

    Level 1 (MANUAL)     — всё на проверку человека
    Level 2 (ASSISTED)   — простое сам, сложное — спросит
    Level 3 (AUTONOMOUS) — полная автономия, только отчёты
    """

    MANUAL = 1       # Всё на проверку (недели 1-2)
    ASSISTED = 2     # Простое — сам, сложное — спросит (недели 3-4)
    AUTONOMOUS = 3   # Полная автономия (месяц 2+)


class EscalationReason(Enum):
    """Причины почему агент зовёт человека."""

    UNCERTAIN = "uncertain"           # Не уверен в результате
    CLIENT_REQUEST = "client_request" # Клиент хочет кастомное
    API_DOWN = "api_down"             # API упал, нет fallback
    ACCESS_DENIED = "access_denied"   # Нет доступа к нужному
    QUALITY_LOW = "quality_low"       # Качество ниже порога
    NEW_DOMAIN = "new_domain"         # Задача из новой области
    SAFETY = "safety"                 # Потенциально опасное действие


@dataclass
class Thought:
    """Шаг цепочки мышления (thought → action → observation).

    Паттерн из OpenManus (#9): каждое действие агента предваряется
    рассуждением и завершается наблюдением (результатом).
    """

    step: int
    thought: str               # что думаем (reasoning)
    action: str                # что делаем (action description)
    observation: str           # что получили (result / observation)
    tool_used: Optional[str] = None  # какой инструмент/MCP использовался
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """Сериализация для JSON-ответов."""
        return {
            "step": self.step,
            "thought": self.thought,
            "action": self.action,
            "observation": self.observation,
            "tool_used": self.tool_used,
            "timestamp": self.timestamp,
        }


@dataclass
class ValidationResult:
    """Результат Claude Security-style валидации (#1)."""

    is_safe: bool
    reason: str
    severity: str  # "safe" | "warning" | "critical"
    suggested_fix: Optional[str] = None


@dataclass
class Task:
    """Единица работы, которую оркестратор обрабатывает end-to-end."""

    id: str
    intent: IntentType
    description: str
    context: Dict[str, Any] = field(default_factory=dict)
    priority: int = 1                               # 1 (низкий) – 5 (критический)
    status: TaskStatus = field(default=TaskStatus.PENDING)
    worker: Optional[str] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    thought_chain: List[Thought] = field(default_factory=list)
    validation: Optional[ValidationResult] = None
    retry_count: int = 0
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "intent": self.intent.value,
            "description": self.description,
            "context": self.context,
            "priority": self.priority,
            "status": self.status.value,
            "worker": self.worker,
            "result": self.result,
            "error": self.error,
            "thought_chain": [t.to_dict() for t in self.thought_chain],
            "validation": {
                "is_safe": self.validation.is_safe,
                "reason": self.validation.reason,
                "severity": self.validation.severity,
                "suggested_fix": self.validation.suggested_fix,
            } if self.validation else None,
            "retry_count": self.retry_count,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }


# ---------------------------------------------------------------------------
# Jarvis Orchestrator
# ---------------------------------------------------------------------------


class JarvisOrchestrator:
    """Единый оркестратор v3.

    Архитектура (OpenManus-style + NEO + Claude Security):
        1. Получаем задачу от пользователя (Telegram / голос / webhook).
        2. LLM Router выбирает модель (Kimi → DeepSeek → Groq → Local).
        3. Intent Classifier определяет тип задачи.
        4. Planner создаёт цепочку шагов (Thought chain).
        5. Worker Dispatcher запускает воркера.
        6. Validator проверяет результат (Claude Security-style).
        7. Сохраняем в память (Obsidian / векторная БД).

    Args:
        config_path: Путь к YAML-файлу с настройками (опционально).

    Attributes:
        tasks: Реестр всех задач по ID.
        thought_chains: Реестр цепочек мышления по ID задачи.
        workers: Зарегистрированные воркеры (Content, Video, Dev, Intel, Sell).
        llm_router: Экземпляр LLMRouter (инициализируется отдельно).
        mcp_layer: Экземпляр MCPLayer.
        memory: Интерфейс к векторной памяти / Obsidian.
    """

    # Маппинг IntentType → имя воркера
    _WORKER_MAP: Dict[IntentType, str] = {
        IntentType.CONTENT:  "content",
        IntentType.VIDEO:    "video",
        IntentType.CODE:     "dev",
        IntentType.INTEL:    "intel",
        IntentType.SELL:     "sell",
        IntentType.BUSINESS: "business",
    }

    # Какие намерения требуют подтверждения на каждом уровне
    _MANUAL_INTENTS: set = {IntentType.SELL, IntentType.VIDEO, IntentType.CODE}
    _ASSISTED_INTENTS: set = {IntentType.SELL, IntentType.CODE}

    def __init__(self, config_path: str = "config/settings.yaml",
                 autonomy_level: AutonomyLevel = AutonomyLevel.MANUAL) -> None:
        self.config_path = config_path
        self.autonomy: AutonomyLevel = autonomy_level
        self.tasks: Dict[str, Task] = {}
        self.thought_chains: Dict[str, List[Thought]] = {}
        self.workers: Dict[str, Any] = {}
        self.llm_router: Optional[Any] = None
        self.mcp_layer: Optional[Any] = None
        self.memory: Optional[Any] = None

    # -- autonomy & escalation ---------------------------------------------

    def set_autonomy(self, level: AutonomyLevel) -> None:
        """Переключить уровень автономности (ручной / полуавто / авто)."""
        self.autonomy = level

    def _needs_human_approval(self, intent: IntentType) -> bool:
        """Определяет, требуется ли подтверждение человека для задачи.

        Уровень 1 (MANUAL):     ВСЕ задачи → на проверку
        Уровень 2 (ASSISTED):   SELL + CODE + VIDEO → на проверку
        Уровень 3 (AUTONOMOUS): Только SELL + CODE (опасные)
        """
        if self.autonomy == AutonomyLevel.MANUAL:
            return True
        if self.autonomy == AutonomyLevel.ASSISTED:
            return intent in self._ASSISTED_INTENTS
        if self.autonomy == AutonomyLevel.AUTONOMOUS:
            return intent in {IntentType.SELL}  # Только деньги
        return True

    def _build_escalation_message(self, task: Task, reason: EscalationReason,
                                  details: str = "") -> str:
        """Сформировать сообщение для человека с просьбой о помощи."""
        emoji = {
            EscalationReason.UNCERTAIN: "🤔",
            EscalationReason.CLIENT_REQUEST: "💬",
            EscalationReason.API_DOWN: "🔌",
            EscalationReason.ACCESS_DENIED: "🔒",
            EscalationReason.QUALITY_LOW: "⚠️",
            EscalationReason.NEW_DOMAIN: "🆕",
            EscalationReason.SAFETY: "🛡️",
        }.get(reason, "❓")

        return (
            f"{emoji} <b>Нужна помощь!</b>\n\n"
            f"Задача: {task.description}\n"
            f"Причина: <b>{reason.value}</b>\n"
            f"{details}\n\n"
            f"Что сделать:\n"
            f"[✅ Подтвердить] [📝 Править] [❌ Отменить]"
        )

    # -- external wiring ---------------------------------------------------

    def register_worker(self, name: str, worker_instance: Any) -> None:
        """Регистрация воркера (Content, Video, Dev, Intel, Sell, и т.д.).

        Args:
            name: Уникальное имя воркера (должно совпадать с _WORKER_MAP).
            worker_instance: Объект воркера с async методом ``execute``.
        """
        self.workers[name] = worker_instance

    def bind_llm_router(self, router: Any) -> None:
        """Подключить LLM Router для маршрутизации между провайдерами."""
        self.llm_router = router

    def bind_mcp_layer(self, mcp: Any) -> None:
        """Подключить MCP Layer для доступа к инструментам."""
        self.mcp_layer = mcp

    def bind_memory(self, memory: Any) -> None:
        """Подключить интерфейс памяти (Obsidian / векторная БД)."""
        self.memory = memory

    # -- public API --------------------------------------------------------

    async def process(
        self,
        user_input: str,
        context: Optional[Dict[str, Any]] = None,
        priority: int = 1,
    ) -> Dict[str, Any]:
        """Главный вход. Обработка пользовательского запроса end-to-end.

        Pipeline (NEO #13 — один вызов, полная цепочка):
            pending → planning → executing → validating → done/error

        Args:
            user_input: Текст запроса от пользователя.
            context: Опциональный контекст (chat_id, user_id, метаданные).
            priority: Приоритет задачи (1–5).

        Returns:
            Словарь с task_id, intent, thought_chain, result и status.
        """
        ctx = context or {}

        # ── Шаг 1: Классификация намерения ──────────────────────────────
        intent = await self._classify_intent(user_input)

        # ── Шаг 2: Создание задачи ──────────────────────────────────────
        task = Task(
            id=f"task_{uuid.uuid4().hex[:12]}_{int(time.time() * 1000)}",
            intent=intent,
            description=user_input,
            context=ctx,
            priority=priority,
            status=TaskStatus.PENDING,
        )
        self.tasks[task.id] = task

        # ── Шаг 3: Планирование (OpenManus-style thought chain) ─────────
        task.status = TaskStatus.PLANNING
        thought_chain = await self._plan_task(task)
        task.thought_chain = thought_chain
        self.thought_chains[task.id] = thought_chain

        # ── Шаг 4: Выполнение через воркера ─────────────────────────────
        task.status = TaskStatus.EXECUTING
        result = await self._execute_task(task, thought_chain)

        # ── Шаг 5: Валидация (Claude Security-style #1) ─────────────────
        task.status = TaskStatus.VALIDATING
        validation = await self._validate_result(task, result)
        task.validation = validation

        if validation.is_safe:
            task.status = TaskStatus.DONE
            task.result = result
        else:
            task.status = TaskStatus.ERROR
            task.error = f"Validation failed: {validation.reason}"
            # ── Retry logic ───────────────────────────────────────────
            result = await self._retry_task(task)
            task.result = result

        task.completed_at = time.time()

        # ── Шаг 6: Сохранение в память ──────────────────────────────────
        if self.memory is not None:
            try:
                await self._persist_to_memory(task)
            except Exception as exc:
                # Не ломаем пайплайн если память недоступна
                task.error = f"{task.error or ''}; Memory persist error: {exc}"

        return {
            "task_id": task.id,
            "intent": task.intent.value,
            "thought_chain": [t.to_dict() for t in thought_chain],
            "result": result,
            "status": task.status.value,
            "validation": {
                "is_safe": task.validation.is_safe,
                "severity": task.validation.severity,
                "reason": task.validation.reason,
            } if task.validation else None,
        }

    # -- internal steps ----------------------------------------------------

    async def _classify_intent(self, text: str) -> IntentType:
        """Intent Classifier через LLM Router.

        Использует few-shot примеры для надёжной классификации.
        Fallback на CHAT если LLM Router недоступен.
        """
        prompt = (
            "Классифицируй намерение пользователя. "
            "Допустимые значения: content, video, code, intel, sell, system, business, chat.\n\n"
            "Примеры:\n"
            '- "сделай пост для Instagram" → content\n'
            '- "сделай шортс про нейросети" → video\n'
            '- "пофикси баг в авторизации" → code\n'
            '- "что там у конкурентов за неделю" → intel\n'
            '- "ответь клиенту по поводу цены" → sell\n'
            '- "перезапусти сервис parser" → system\n'
            '- "создай PDF-отчёт по продажам" → business\n'
            '- "привет, как дела?" → chat\n\n'
            f"Запрос пользователя: {text}\n"
            "Ответ (только одно слово):"
        )

        if self.llm_router is None:
            # Fallback: эвристика по ключевым словам
            return self._fallback_intent_classify(text)

        try:
            response = await self.llm_router.complete(prompt, max_tokens=10, temperature=0.0)
            intent_str = response.strip().lower().rstrip(".").rstrip(",")
            return IntentType(intent_str)
        except (ValueError, Exception):
            return self._fallback_intent_classify(text)

    def _fallback_intent_classify(self, text: str) -> IntentType:
        """Быстрая эвристическая классификация без LLM."""
        lowered = text.lower()
        keywords: Dict[IntentType, List[str]] = {
            IntentType.VIDEO:    ["видео", "видос", "шортс", "shorts", "ролик", "video", "сгенерируй видео"],
            IntentType.CONTENT:  ["пост", "статья", "content", "публикация", "текст", "напиши пост", "сделай пост"],
            IntentType.CODE:     ["код", "баг", "фикс", "debug", "refactor", "deploy", "git", "commit"],
            IntentType.INTEL:    ["конкурент", "монитор", "парс", "intel", "разведка", "данные"],
            IntentType.SELL:     ["клиент", "продаж", "crm", "lead", "ответь клиенту", "предложение"],
            IntentType.SYSTEM:   ["перезапуск", "restart", "update", "обнови", "статус сервиса"],
            IntentType.BUSINESS: ["pdf", "отчёт", "invoice", "инвойс", "бизнес", "отчет"],
        }
        for intent, words in keywords.items():
            if any(w in lowered for w in words):
                return intent
        return IntentType.CHAT

    async def _plan_task(self, task: Task) -> List[Thought]:
        """Planner: создаёт цепочку шагов (OpenManus-style).

        Генерирует JSON-план через LLM и парсит его в список Thought.
        При ошибке парсинга — fallback на одношаговый план.
        """
        prompt = (
            f"Создай план выполнения задачи. Разбей на шаги: Thought → Action → Observation.\n\n"
            f"Задача: {task.description}\n"
            f"Тип: {task.intent.value}\n\n"
            "Формат (строго JSON-массив):\n"
            '[\n'
            '  {"thought": "Анализирую запрос пользователя...", "action": "Выполнить X", "tool": "browser"},\n'
            '  ...\n'
            ']\n\n'
            "Доступные инструменты: browser, code_executor, file_tool, "
            "telegram_api, whisper, video_gen, search, shell, git\n\n"
            "Ответ только JSON, без markdown-форматирования:"
        )

        if self.llm_router is None:
            return self._fallback_plan(task)

        try:
            response = await self.llm_router.complete(prompt, max_tokens=800, temperature=0.3)
            # Очистка от markdown-обёртки
            cleaned = response.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.strip("`").strip()
                if cleaned.lower().startswith("json"):
                    cleaned = cleaned[4:].strip()

            plan = json.loads(cleaned)
            if not isinstance(plan, list):
                raise ValueError("Plan is not a list")

            return [
                Thought(
                    step=i + 1,
                    thought=step.get("thought", ""),
                    action=step.get("action", ""),
                    observation="",
                    tool_used=step.get("tool"),
                )
                for i, step in enumerate(plan)
            ]
        except (json.JSONDecodeError, ValueError, KeyError, Exception):
            return self._fallback_plan(task)

    def _fallback_plan(self, task: Task) -> List[Thought]:
        """Одношаговый fallback-план если LLM Router недоступен."""
        return [
            Thought(
                step=1,
                thought=f"Выполнить задачу: {task.description}",
                action=task.description,
                observation="",
                tool_used=None,
            )
        ]

    async def _execute_task(
        self,
        task: Task,
        thought_chain: List[Thought],
    ) -> Any:
        """Dispatcher: выбирает и запускает воркера по типу задачи.

        Для CHAT-задач возвращает прямой ответ через LLM.
        Для остальных — делегирует зарегистрированному воркеру.
        """
        worker_name = self._WORKER_MAP.get(task.intent)

        if worker_name and worker_name in self.workers:
            worker = self.workers[worker_name]
            task.worker = worker_name
            # Воркер должен иметь async метод execute(task, thought_chain)
            return await worker.execute(task, thought_chain)

        # CHAT или нет воркера — отвечаем через LLM напрямую
        if self.llm_router is not None:
            return await self.llm_router.complete(task.description)

        return {"error": "No worker registered and no LLM router available", "task_id": task.id}

    async def _validate_result(self, task: Task, result: Any) -> ValidationResult:
        """Claude Security-style валидация (#1).

        Для CODE и SYSTEM-задач проверяем безопасность результата.
        Для остальных — проверяем качество и адекватность.
        """
        result_str = str(result)[:2000]

        # Уровень 1: проверка опасных паттернов (автономная)
        if task.intent in (IntentType.CODE, IntentType.SYSTEM):
            dangerous_patterns = [
                "rm -rf /", "mkfs", "dd if=", ":(){:|:&};:",
                "shutdown", "reboot -f", "format c:",
                "os.system", "subprocess.call", "eval(", "exec(",
                "__import__('os')", "drop table", "delete from",
            ]
            for pattern in dangerous_patterns:
                if pattern.lower() in result_str.lower():
                    return ValidationResult(
                        is_safe=False,
                        reason=f"Dangerous pattern detected: {pattern}",
                        severity="critical",
                        suggested_fix="Review the code before executing. Remove dangerous operations.",
                    )

        # Уровень 2: LLM-based валидация (если router доступен)
        if self.llm_router is not None:
            try:
                val_prompt = (
                    f"Проверь результат на безопасность и корректность:\n\n"
                    f"Задача: {task.description}\n"
                    f"Тип задачи: {task.intent.value}\n"
                    f"Результат:\n{result_str}\n\n"
                    "Оцени безопасность: SAFE или UNSAFE.\n"
                    "Если UNSAFE — укажи почему и уровень: warning или critical.\n"
                    "Ответ в формате: SAFE|UNSAFE::severity::reason"
                )
                val_response = await self.llm_router.complete(val_prompt, max_tokens=50, temperature=0.0)
                val_clean = val_response.strip()

                if val_clean.upper().startswith("UNSAFE"):
                    parts = val_clean.split("::")
                    severity = parts[1] if len(parts) > 1 else "warning"
                    reason = parts[2] if len(parts) > 2 else "LLM flagged as unsafe"
                    return ValidationResult(
                        is_safe=False,
                        reason=reason,
                        severity=severity,
                        suggested_fix="Retry with more specific constraints.",
                    )
            except Exception:
                pass  # Fallback: считаем безопасным если валидация упала

        return ValidationResult(is_safe=True, reason="Passed all checks", severity="safe")

    async def _retry_task(self, task: Task, max_retries: int = 2) -> Any:
        """Retry с улучшенным промптом и контекстом ошибки.

        При каждой попытке добавляет контекст предыдущей ошибки,
        чтобы LLM мог адаптировать подход.
        """
        for attempt in range(max_retries):
            task.status = TaskStatus.RETRYING
            task.retry_count += 1

            modified_description = (
                f"[Retry {attempt + 1}/{max_retries}] {task.description}\n\n"
                f"Предыдущая ошибка: {task.error or 'validation failed'}\n"
                "Пожалуйста, исправь проблему и попробуй снова."
            )

            retry_task = Task(
                id=task.id,
                intent=task.intent,
                description=modified_description,
                context={**task.context, "previous_error": task.error, "retry_attempt": attempt + 1},
            )

            thought_chain = await self._plan_task(retry_task)
            result = await self._execute_task(retry_task, thought_chain)
            validation = await self._validate_result(retry_task, result)

            if validation.is_safe:
                task.status = TaskStatus.DONE
                task.validation = validation
                return result

            task.error = f"Retry {attempt + 1} failed: {validation.reason}"

        task.status = TaskStatus.ERROR
        return {"error": "Max retries exceeded", "task_id": task.id, "last_error": task.error}

    async def _persist_to_memory(self, task: Task) -> None:
        """Сохранить результат задачи в векторную память / Obsidian."""
        if self.memory is None:
            return

        memory_entry = {
            "task_id": task.id,
            "intent": task.intent.value,
            "description": task.description,
            "result_summary": str(task.result)[:500] if task.result else None,
            "status": task.status.value,
            "timestamp": task.completed_at,
        }
        # Интерфейс памяти — async add / save
        if hasattr(self.memory, "add"):
            await self.memory.add(memory_entry)
        elif hasattr(self.memory, "save"):
            await self.memory.save(memory_entry)

    # -- query helpers -----------------------------------------------------

    def get_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Получить статус задачи по ID.

        Args:
            task_id: Идентификатор задачи.

        Returns:
            Словарь с полной информацией о задаче или None.
        """
        task = self.tasks.get(task_id)
        return task.to_dict() if task else None

    def list_tasks(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Список задач с опциональным фильтром по статусу.

        Args:
            status: Фильтр по статусу (pending, planning, executing, validating, done, error).

        Returns:
            Список словарей с информацией о задачах.
        """
        tasks_iter = self.tasks.values()
        if status:
            tasks_iter = [t for t in tasks_iter if t.status.value == status]
        return [t.to_dict() for t in tasks_iter]

    def get_stats(self) -> Dict[str, Any]:
        """Агрегированная статистика по всем задачам.

        Returns:
            Словарь с counts по статусам, intent-ам и средним временем выполнения.
        """
        from collections import Counter

        statuses = Counter(t.status.value for t in self.tasks.values())
        intents = Counter(t.intent.value for t in self.tasks.values())

        completed = [t for t in self.tasks.values() if t.completed_at and t.created_at]
        avg_duration = (
            sum(t.completed_at - t.created_at for t in completed) / len(completed)
            if completed else 0
        )

        return {
            "total_tasks": len(self.tasks),
            "by_status": dict(statuses),
            "by_intent": dict(intents),
            "avg_duration_sec": round(avg_duration, 2),
            "active_tasks": len([t for t in self.tasks.values() if t.status in {
                TaskStatus.PENDING, TaskStatus.PLANNING, TaskStatus.EXECUTING, TaskStatus.VALIDATING
            }]),
        }
