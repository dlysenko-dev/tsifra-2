"""
Autonomous Event Loop v3 — проактивный цикл агента Digital Clone.

Архитектура:
- TaskScheduler   : cron-like планировщик на чистом Python
- QualityChecker  : LLM-based проверка качества контента
- PipelineExecutor: поэтапное выполнение pipeline (генерация → проверка → публикация → лог)
- AutonomousLoop  : главный event loop, проверяет расписание каждую минуту

Уровни автономности:
- Level 1 (MANUAL):    только генерирует, НЕ публикует без подтверждения
- Level 2 (ASSISTED):  публикует если quality_score > threshold
- Level 3 (AUTONOMOUS): полная автономия

Сценарии:
- content_generation : посты для Telegram/соцсетей
- trend_monitoring   : мониторинг трендов
- video_generation   : YouTube Shorts
- client_response    : ответы клиентам
- intel_report       : ежедневные отчёты
- learning_loop      : анализ метрик
"""

from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums & Data classes
# ---------------------------------------------------------------------------


class ScheduleType(Enum):
    """Тип расписания задачи."""

    CRON = "cron"           # cron-строка (min hour dom mon dow)
    INTERVAL = "interval"   # каждые N минут
    FIXED_TIME = "fixed"    # в конкретное время (HH:MM)


class PipelineStage(Enum):
    """Стандартные этапы pipeline."""

    GENERATE_CONTENT = "generate_content"
    GENERATE_SCRIPT = "generate_script"
    GENERATE_VIDEO = "generate_video"
    QUALITY_CHECK = "quality_check"
    PUBLISH = "publish"
    PUBLISH_VIDEO = "publish_video"
    LOG = "log"
    RESEARCH_TRENDS = "research_trends"
    ANALYZE = "analyze"
    REPORT = "report"


@dataclass
class ScheduledTask:
    """Задача из расписания (загружается из JSON-конфига)."""

    id: str
    name: str
    description: str
    schedule_type: ScheduleType
    schedule_value: str
    pipeline: List[str]
    autonomy_level: int = 1
    enabled: bool = True
    last_run: Optional[float] = None
    next_run: Optional[float] = None
    run_count: int = 0
    error_count: int = 0
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "schedule": {"type": self.schedule_type.value, "value": self.schedule_value},
            "pipeline": self.pipeline,
            "autonomy_level": self.autonomy_level,
            "enabled": self.enabled,
            "last_run": self.last_run,
            "next_run": self.next_run,
            "run_count": self.run_count,
            "error_count": self.error_count,
            "context": self.context,
        }


@dataclass
class PipelineResult:
    """Результат выполнения pipeline для одной задачи."""

    task_id: str
    success: bool = False
    stages_completed: List[str] = field(default_factory=list)
    stages_failed: List[str] = field(default_factory=list)
    content: Optional[str] = None
    quality_score: float = 0.0
    published: bool = False
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "success": self.success,
            "stages_completed": self.stages_completed,
            "stages_failed": self.stages_failed,
            "content_preview": (self.content[:200] + "...") if self.content and len(self.content) > 200 else self.content,
            "quality_score": round(self.quality_score, 2),
            "published": self.published,
            "error": self.error,
            "metadata": self.metadata,
            "duration_sec": round(self.completed_at - self.started_at, 2) if self.completed_at else None,
        }


# ---------------------------------------------------------------------------
# TaskScheduler — cron-like планировщик на чистом Python
# ---------------------------------------------------------------------------


class TaskScheduler:
    """Хранит расписание задач и определяет какие нужно запустить сейчас.

    Поддерживает три типа расписания:
    - cron      : минута час день_месяца месяц день_недели (как crontab)
    - interval  : каждые N минут
    - fixed_time: в конкретное время HH:MM

    Attributes:
        tasks: Словарь зарегистрированных задач по ID.
    """

    def __init__(self) -> None:
        self.tasks: Dict[str, ScheduledTask] = {}

    # -- task management ---------------------------------------------------

    def register(self, task: ScheduledTask) -> None:
        """Зарегистрировать задачу в планировщике."""
        self.tasks[task.id] = task
        task.next_run = self._compute_next_run(task)

    def unregister(self, task_id: str) -> None:
        """Удалить задачу из планировщика."""
        self.tasks.pop(task_id, None)

    def load_from_config(self, config_path: str) -> int:
        """Загрузить расписание из JSON-файла.

        Returns:
            Количество загруженных задач.
        """
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Schedule config not found: {config_path}")

        with open(path, "r", encoding="utf-8") as f:
            config = json.load(f)

        count = 0
        for task_data in config.get("tasks", []):
            if not task_data.get("enabled", True):
                continue

            schedule = task_data.get("schedule", {})
            task = ScheduledTask(
                id=task_data["id"],
                name=task_data.get("name", task_data["id"]),
                description=task_data.get("description", ""),
                schedule_type=ScheduleType(schedule.get("type", "interval")),
                schedule_value=schedule.get("value", "60"),
                pipeline=task_data.get("pipeline", []),
                autonomy_level=task_data.get("autonomy_level", 1),
                enabled=task_data.get("enabled", True),
                context=task_data.get("context", {}),
            )
            self.register(task)
            count += 1

        return count

    # -- scheduling logic --------------------------------------------------

    def get_tasks_to_run(self) -> List[ScheduledTask]:
        """Вернуть список задач, которые нужно запустить прямо сейчас.

        Проверяет next_run для каждой задачи. После выборки обновляет
        last_run и пересчитывает next_run.
        """
        now = time.time()
        ready: List[ScheduledTask] = []

        for task in self.tasks.values():
            if not task.enabled:
                continue
            if task.next_run is None:
                task.next_run = self._compute_next_run(task)
            if task.next_run <= now:
                ready.append(task)

        return ready

    def mark_executed(self, task: ScheduledTask) -> None:
        """Отметить задачу как выполненную и пересчитать next_run."""
        task.last_run = time.time()
        task.run_count += 1
        task.next_run = self._compute_next_run(task)

    def _compute_next_run(self, task: ScheduledTask) -> float:
        """Вычислить следующее время запуска задачи (unix timestamp)."""
        now = datetime.now()

        if task.schedule_type == ScheduleType.INTERVAL:
            minutes = int(task.schedule_value)
            # Если задача ни разу не запускалась — запускаем через N минут
            # Иначе — от last_run + interval
            base = task.last_run or time.time()
            return base + minutes * 60

        elif task.schedule_type == ScheduleType.FIXED_TIME:
            # Формат: "HH:MM"
            try:
                hour, minute = map(int, task.schedule_value.split(":"))
                target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                if target <= now:
                    target += timedelta(days=1)
                return target.timestamp()
            except ValueError:
                # Fallback: через 1 час
                return time.time() + 3600

        elif task.schedule_type == ScheduleType.CRON:
            return self._parse_cron_next(task.schedule_value, now)

        return time.time() + 3600  # fallback: через час

    def _parse_cron_next(self, cron_expr: str, now: datetime) -> float:
        """Парсинг cron-строки и вычисление следующего запуска.

        Поддерживает 5-полей: min hour dom mon dow
        Звёздочка (*) = любое значение.
        Простые числа и * поддерживаются. Шаги (*/N) — базовая поддержка.
        """
        parts = cron_expr.strip().split()
        if len(parts) != 5:
            # Некорректный cron — fallback
            return now.timestamp() + 3600

        minute_field, hour_field, dom_field, mon_field, dow_field = parts

        # Ищем ближайшее подходящее время, начиная со следующей минуты
        candidate = now + timedelta(minutes=1)
        candidate = candidate.replace(second=0, microsecond=0)

        # Ограничим поиск — не более 366 дней вперёд
        for _ in range(366 * 24 * 60):
            if self._cron_match_minute(candidate, minute_field):
                if self._cron_match_hour(candidate, hour_field):
                    if self._cron_match_dom(candidate, dom_field):
                        if self._cron_match_month(candidate, mon_field):
                            if self._cron_match_dow(candidate, dow_field):
                                return candidate.timestamp()
            candidate += timedelta(minutes=1)

        # Fallback
        return now.timestamp() + 3600

    # -- cron field matchers -----------------------------------------------

    def _cron_match_minute(self, dt: datetime, field: str) -> bool:
        if field == "*":
            return True
        if field.startswith("*/"):
            step = int(field[2:])
            return dt.minute % step == 0
        return dt.minute == int(field)

    def _cron_match_hour(self, dt: datetime, field: str) -> bool:
        if field == "*":
            return True
        if field.startswith("*/"):
            step = int(field[2:])
            return dt.hour % step == 0
        return dt.hour == int(field)

    def _cron_match_dom(self, dt: datetime, field: str) -> bool:
        if field == "*":
            return True
        if field.startswith("*/"):
            step = int(field[2:])
            return dt.day % step == 0
        try:
            return dt.day == int(field)
        except ValueError:
            return True

    def _cron_match_month(self, dt: datetime, field: str) -> bool:
        if field == "*":
            return True
        try:
            return dt.month == int(field)
        except ValueError:
            return True

    def _cron_match_dow(self, dt: datetime, field: str) -> bool:
        if field == "*":
            return True
        # Python: Monday=0, cron: Sunday=0, Monday=1
        cron_dow = (dt.weekday() + 1) % 7
        try:
            return cron_dow == int(field)
        except ValueError:
            return True

    # -- diagnostics -------------------------------------------------------

    def get_overview(self) -> Dict[str, Any]:
        """Обзор всех зарегистрированных задач."""
        now = time.time()
        return {
            "total_tasks": len(self.tasks),
            "enabled": sum(1 for t in self.tasks.values() if t.enabled),
            "tasks": [
                {
                    "id": t.id,
                    "name": t.name,
                    "enabled": t.enabled,
                    "next_run_in_sec": int(t.next_run - now) if t.next_run else None,
                    "next_run_human": datetime.fromtimestamp(t.next_run).strftime("%Y-%m-%d %H:%M") if t.next_run else None,
                    "run_count": t.run_count,
                    "error_count": t.error_count,
                }
                for t in sorted(self.tasks.values(), key=lambda x: x.next_run or 0)
            ],
        }


# ---------------------------------------------------------------------------
# QualityChecker — LLM-based проверка качества
# ---------------------------------------------------------------------------


class QualityChecker:
    """Обёртка над ContentQualityChecker из quality_control.py."""

    DEFAULT_THRESHOLD = 0.7

    def __init__(self, llm_router=None):
        self.llm = llm_router
        self._full_checker = None
        self._init_full_checker()

    def _init_full_checker(self):
        """Ленивая инициализация ContentQualityChecker."""
        try:
            from core.quality_control import ContentQualityChecker
            self._full_checker = ContentQualityChecker(self.llm)
        except ImportError:
            self._full_checker = None

    async def check(self, content, content_type="telegram_post"):
        """Проверка качества через полный движок (если доступен) или fallback."""
        if self._full_checker is not None:
            try:
                report = await self._full_checker.check(content, content_type=content_type)
                # Нормализуем score 0-100 → 0.0-1.0
                return report.quality_score / 100.0 if hasattr(report, 'quality_score') else 0.5
            except Exception:
                pass  # Fallback ниже
        return await self._fallback_check(content, content_type)

    async def _fallback_check(self, content, content_type="telegram_post"):
        """Fallback проверка через LLM."""
        if self.llm is None:
            return self._heuristic_score(content)
        prompt = (
            f"Оцени качество контента типа '{content_type}' по шкале 0-100. "
            f"Учитывай: грамотность, структуру, CTA, читаемость, полезность.\n\n"
            f"Контент:\n{content[:1500]}\n\n"
            f"Ответь ТОЛЬКО числом от 0 до 100:"
        )
        try:
            response = await self.llm.complete(prompt, max_tokens=10, temperature=0.0)
            for token in response.strip().split():
                token = token.strip("%.,;:!? ")
                try:
                    return int(token) / 100.0
                except ValueError:
                    continue
            return self._heuristic_score(content)
        except Exception:
            return self._heuristic_score(content)

    def _heuristic_score(self, content):
        """Эвристическая оценка без LLM."""
        if not content:
            return 0.0
        score = 0.5
        content_lower = content.lower()
        length = len(content)
        if 200 <= length <= 2000:
            score += 0.15
        elif length > 100:
            score += 0.05
        if any(marker in content for marker in ["- ", "1.", "2.", "* ", ">"]):
            score += 0.1
        if any(marker in content for marker in ["**", "##", "__"]):
            score += 0.05
        cta_words = ["подпишись", "комментируй", "делись", "переходи", "пиши", "ссылка", "бесплатно"]
        if any(word in content_lower for word in cta_words):
            score += 0.1
        if "#" in content:
            score += 0.1
        return min(1.0, score)

    def passes_threshold(self, score, threshold=None):
        threshold = threshold or self.DEFAULT_THRESHOLD
        return score >= threshold


# ---------------------------------------------------------------------------
# PipelineExecutor — поэтапное выполнение pipeline
# ---------------------------------------------------------------------------


class PipelineExecutor:
    """Исполняет pipeline задачи поэтапно.

    Pipeline — список stage names, например:
        ["generate_content", "quality_check", "publish", "log"]

    Каждый stage — это async метод. Stage может вернуть результат
    или выбросить исключение — pipeline продолжается или прерывается
    в зависимости от настроек.
    """

    # Stage-ы, при ошибке в которых pipeline прерывается
    CRITICAL_STAGES = {"generate_content", "generate_script"}

    def __init__(
        self,
        jarvis: Any,
        quality_checker: QualityChecker,
    ) -> None:
        self.jarvis = jarvis
        self.quality = quality_checker
        self.llm = getattr(jarvis, "llm_router", None)
        self.mcp = getattr(jarvis, "mcp_layer", None)

    async def execute(self, task: ScheduledTask) -> PipelineResult:
        """Выполнить полный pipeline для задачи.

        Pipeline:
            generate_content → quality_check → publish → log
            generate_script  → generate_video → publish_video → log
            research_trends  → analyze → report

        Returns:
            PipelineResult с полной информацией о выполнении.
        """
        result = PipelineResult(task_id=task.id)
        accumulated_content: Optional[str] = None

        try:
            for stage_name in task.pipeline:
                try:
                    stage_result = await self._execute_stage(
                        stage_name, task, accumulated_content
                    )
                    result.stages_completed.append(stage_name)

                    # Сохраняем контент из генерации для следующих stage
                    if isinstance(stage_result, dict):
                        if "content" in stage_result and stage_result["content"]:
                            accumulated_content = stage_result["content"]
                        elif "script" in stage_result and stage_result["script"]:
                            accumulated_content = stage_result["script"]

                        if stage_name == PipelineStage.QUALITY_CHECK.value:
                            result.quality_score = stage_result.get("quality_score", 0.0)

                        if stage_name in (PipelineStage.PUBLISH.value, PipelineStage.PUBLISH_VIDEO.value):
                            result.published = stage_result.get("published", False)

                    elif isinstance(stage_result, str):
                        accumulated_content = stage_result

                except Exception as exc:
                    result.stages_failed.append(stage_name)
                    if stage_name in self.CRITICAL_STAGES:
                        result.success = False
                        result.error = f"Critical stage '{stage_name}' failed: {exc}"
                        break
                    # Некритичные stage — логируем ошибку и продолжаем
                    print(f"[PipelineExecutor] Non-critical stage '{stage_name}' failed: {exc}")
                    continue

            # Pipeline завершился без критических ошибок
            if not result.error:
                result.success = True
                result.content = accumulated_content

        except Exception as exc:
            result.success = False
            result.error = f"Pipeline execution failed: {exc}"

        finally:
            result.completed_at = time.time()

        return result

    async def _execute_stage(
        self,
        stage_name: str,
        task: ScheduledTask,
        content: Optional[str],
    ) -> Dict[str, Any]:
        """Выполнить один stage pipeline."""
        handler = getattr(self, f"_stage_{stage_name}", None)
        if handler is None:
            # Если нет специализированного обработчика — fallback
            return await self._stage_default(stage_name, task, content)
        return await handler(task, content)

    # -- stage handlers ----------------------------------------------------

    async def _stage_generate_content(self, task: ScheduledTask, content: Optional[str]) -> Dict[str, Any]:
        """Генерация контента (пост) через ContentWorker."""
        topic = task.context.get("topic", task.description or "AI автоматизация")
        style = task.context.get("style", "экспертный")
        length = task.context.get("length", "средний")

        # Через Jarvis оркестратор
        user_input = f"Напиши пост про {topic}. Стиль: {style}. Длина: {length}."
        jarvis_result = await self.jarvis.process(user_input, context={"autonomous": True})

        result_content = jarvis_result.get("result", "")
        if isinstance(result_content, dict):
            text = result_content.get("content", str(result_content))
        else:
            text = str(result_content)

        return {
            "content": text,
            "type": "telegram_post",
            "topic": topic,
            "jarvis_task_id": jarvis_result.get("task_id"),
        }

    async def _stage_generate_script(self, task: ScheduledTask, content: Optional[str]) -> Dict[str, Any]:
        """Генерация сценария для видео."""
        topic = task.context.get("topic", task.description or "AI автоматизация")
        duration = task.context.get("duration", 30)

        user_input = f"Создай сценарий для шортса ({duration} сек) на тему: {topic}"
        jarvis_result = await self.jarvis.process(user_input, context={"autonomous": True})

        result_content = jarvis_result.get("result", "")
        script = result_content.get("script", str(result_content)) if isinstance(result_content, dict) else str(result_content)

        return {
            "script": script,
            "type": "video_script",
            "topic": topic,
            "duration": duration,
        }

    async def _stage_generate_video(self, task: ScheduledTask, content: Optional[str]) -> Dict[str, Any]:
        """Генерация видео через VideoWorker."""
        script = content or task.context.get("script", "AI автоматизация")
        topic = task.context.get("topic", "AI автоматизация")

        user_input = f"Сгенерируй шортс по сценарию: {script[:200]}"
        jarvis_result = await self.jarvis.process(user_input, context={"autonomous": True})

        return {
            "video_result": jarvis_result.get("result"),
            "type": "video_generated",
            "topic": topic,
        }

    async def _stage_quality_check(self, task: ScheduledTask, content: Optional[str]) -> Dict[str, Any]:
        """Проверка качества сгенерированного контента."""
        if not content:
            return {"quality_score": 0.0, "passed": False, "content_type": "unknown"}

        score = await self.quality.check(content, content_type="telegram_post")
        task._last_quality_score = score  # Сохраняем для проверки autonomy_level 2
        passed = self.quality.passes_threshold(score)

        return {
            "quality_score": score,
            "passed": passed,
            "threshold": self.quality.DEFAULT_THRESHOLD,
            "content_type": "telegram_post",
            "content_preview": content[:200],
        }

    async def _stage_publish(self, task: ScheduledTask, content: Optional[str]) -> Dict[str, Any]:
        """Публикация в Telegram (через MCP tool tg_send_message).

        Учитывает autonomy_level:
        - Level 1: только генерирует, НЕ публикует
        - Level 2: публикует если quality_score > threshold
        - Level 3: полная автономия
        """
        if not content:
            return {"published": False, "reason": "no_content"}

        autonomy = task.autonomy_level

        # Level 1 — не публикуем без подтверждения
        if autonomy <= 1:
            return {
                "published": False,
                "reason": " autonomy_level_1_requires_human_approval",
                "preview": content[:500],
            }

        # Level 2 — публикуем только если quality_score > threshold
        # (quality_score устанавливается в _stage_quality_check)
        if autonomy == 2:
            # quality_score хранится в task._last_quality_score
            last_score = getattr(task, '_last_quality_score', 0.0)
            if last_score < self.quality.DEFAULT_THRESHOLD:
                return {
                    "published": False,
                    "reason": f"autonomy_level_2_quality_check_failed (score={last_score:.2f} < {self.quality.DEFAULT_THRESHOLD})",
                    "preview": content[:500],
                }

        # Level 2+ — публикуем через MCP
        if self.mcp is not None:
            chat_id = task.context.get("chat_id", os.getenv("AUTONOMOUS_CHAT_ID", "@your_channel"))
            try:
                mcp_result = await self.mcp.execute("tg_publish_post", {
                    "text": content,
                    "channel": chat_id,
                })
                return {
                    "published": mcp_result.success,
                    "reason": "published_via_mcp" if mcp_result.success else str(mcp_result.error),
                    "chat_id": chat_id,
                    "mcp_result": mcp_result.to_dict(),
                }
            except Exception as exc:
                return {"published": False, "reason": f"mcp_error: {exc}"}

        return {"published": False, "reason": "mcp_layer_not_available"}

    async def _stage_publish_video(self, task: ScheduledTask, content: Optional[str]) -> Dict[str, Any]:
        """Публикация видео (YouTube Shorts / Telegram)."""
        autonomy = task.autonomy_level

        if autonomy <= 1:
            return {"published": False, "reason": "autonomy_level_1_requires_human_approval"}

        if self.mcp is not None:
            try:
                mcp_result = await self.mcp.execute("video_create_hybrid", {
                    "topic": task.context.get("topic", content or "AI automation"),
                    "duration": task.context.get("duration", 15.0),
                    "style": "hybrid",
                })
                return {
                    "published": mcp_result.success,
                    "type": "video",
                    "mcp_result": mcp_result.to_dict(),
                }
            except Exception as exc:
                return {"published": False, "reason": f"video_publish_error: {exc}"}

        return {"published": False, "reason": "mcp_layer_not_available"}

    async def _stage_research_trends(self, task: ScheduledTask, content: Optional[str]) -> Dict[str, Any]:
        """Исследование трендов через IntelWorker."""
        niche = task.context.get("niche", "AI automation")
        user_input = f"Проведи анализ трендов в нише: {niche}"
        jarvis_result = await self.jarvis.process(user_input, context={"autonomous": True})

        return {
            "research_result": jarvis_result.get("result"),
            "niche": niche,
            "jarvis_task_id": jarvis_result.get("task_id"),
        }

    async def _stage_analyze(self, task: ScheduledTask, content: Optional[str]) -> Dict[str, Any]:
        """Анализ результатов исследования."""
        # Здесь можно добавить LLM-based анализ
        return {"analysis": "completed", "stage": "analyze"}

    async def _stage_report(self, task: ScheduledTask, content: Optional[str]) -> Dict[str, Any]:
        """Формирование и отправка отчёта."""
        if self.mcp is not None:
            report_text = f"<b>Ежедневный отчёт: {task.name}</b>\n\nАнализ трендов завершён."
            try:
                chat_id = task.context.get("chat_id", os.getenv("AUTONOMOUS_CHAT_ID", "@your_channel"))
                mcp_result = await self.mcp.execute("tg_send_message", {
                    "chat_id": chat_id,
                    "text": report_text,
                    "parse_mode": "HTML",
                })
                return {"reported": mcp_result.success, "mcp_result": mcp_result.to_dict()}
            except Exception as exc:
                return {"reported": False, "error": str(exc)}

        return {"reported": False, "reason": "mcp_layer_not_available"}

    async def _stage_log(self, task: ScheduledTask, content: Optional[str]) -> Dict[str, Any]:
        """Логирование результатов в память и файл."""
        log_entry = {
            "timestamp": time.time(),
            "task_id": task.id,
            "task_name": task.name,
            "run_count": task.run_count,
            "content_preview": (content[:300] + "...") if content and len(str(content)) > 300 else content,
        }

        # Пишем в файл лога
        try:
            log_dir = Path("logs/autonomous")
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / f"{datetime.now():%Y-%m-%d}.jsonl"
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception as exc:
            print(f"[PipelineExecutor] Log write warning: {exc}")

        # Сохраняем в память Jarvis если доступна
        memory = getattr(self.jarvis, "memory", None)
        if memory is not None:
            try:
                if hasattr(memory, "add"):
                    await memory.add(log_entry)
                elif hasattr(memory, "save"):
                    await memory.save(log_entry)
            except Exception as exc:
                print(f"[PipelineExecutor] Memory persist warning: {exc}")

        return {"logged": True, "log_file": str(log_file) if 'log_file' in dir() else None}

    async def _stage_default(self, stage_name: str, task: ScheduledTask, content: Optional[str]) -> Dict[str, Any]:
        """Fallback для неизвестных stage — через Jarvis."""
        user_input = f"[Autonomous] Задача '{task.name}', этап: {stage_name}. Описание: {task.description}"
        jarvis_result = await self.jarvis.process(user_input, context={"autonomous": True})
        return {
            "stage": stage_name,
            "jarvis_result": jarvis_result.get("result"),
            "status": "completed_via_fallback",
        }


# ---------------------------------------------------------------------------
# AutonomousLoop — главный цикл
# ---------------------------------------------------------------------------


class AutonomousLoop:
    """Проактивный цикл агента. Работает по расписанию (cron-like).

    Сценарии:
    - content_generation: генерировать и публиковать посты
    - trend_monitoring: мониторить тренды
    - video_generation: создавать шортсы
    - client_response: отвечать клиентам
    - intel_report: ежедневные отчёты
    - learning_loop: анализировать метрики

    Args:
        jarvis: Экземпляр JarvisOrchestrator.
        check_interval: Интервал проверки расписания в секундах (по умолчанию 60).

    Attributes:
        scheduler: TaskScheduler с загруженными задачами.
        executor: PipelineExecutor для выполнения pipeline.
        running: Флаг работы цикла.
        stats: Статистика выполнения.
    """

    def __init__(
        self,
        jarvis: Any,
        check_interval: int = 60,
    ) -> None:
        self.jarvis = jarvis
        self.check_interval = check_interval
        self.scheduler = TaskScheduler()
        self.quality = QualityChecker(getattr(jarvis, "llm_router", None))
        self.executor = PipelineExecutor(jarvis, self.quality)
        self.running = False
        self.stats: Dict[str, Any] = {
            "loops": 0,
            "tasks_triggered": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "started_at": None,
        }
        self._results_log: List[Dict[str, Any]] = []
        self.telegram_bot: Optional[Any] = None  # JarvisTelegramBot instance

    # -- lifecycle -----------------------------------------------------------

    async def load_schedule(self, config_path: str) -> int:
        """Загрузить расписание из JSON-файла.

        Returns:
            Количество загруженных задач.
        """
        count = self.scheduler.load_from_config(config_path)
        print(f"[AutonomousLoop] Loaded {count} scheduled tasks from {config_path}")
        for task in self.scheduler.tasks.values():
            next_human = datetime.fromtimestamp(task.next_run).strftime("%H:%M") if task.next_run else "?"
            print(f"  - {task.name}: next run at {next_human}")
        return count

    async def start(self) -> None:
        """Запустить автономный цикл."""
        self.running = True
        self.stats["started_at"] = time.time()
        print("[AutonomousLoop] Started")

    async def stop(self) -> None:
        """Остановить автономный цикл."""
        self.running = False
        print("[AutonomousLoop] Stopped")

    # -- main event loop ----------------------------------------------------

    async def run(self) -> None:
        """Главный цикл — проверяет расписание каждую минуту.

        Запускает pipeline для каждой задачи, у которой наступило время.
        Каждый pipeline выполняется в отдельной asyncio задаче.
        """
        if not self.running:
            await self.start()

        print(f"[AutonomousLoop] Event loop running (check every {self.check_interval}s)")

        while self.running:
            self.stats["loops"] += 1
            loop_start = time.time()

            try:
                tasks_to_run = self.scheduler.get_tasks_to_run()

                if tasks_to_run:
                    print(f"[AutonomousLoop] {len(tasks_to_run)} task(s) ready to run")

                    for task in tasks_to_run:
                        self.stats["tasks_triggered"] += 1
                        task.error_count += 1  # инкремент на случай падения — сбросим при успехе
                        asyncio.create_task(self._execute_pipeline(task))

            except Exception as exc:
                print(f"[AutonomousLoop] Scheduler check error: {exc}")

            # Ждём до следующей проверки (ровно check_interval, даже если были задачи)
            elapsed = time.time() - loop_start
            sleep_time = max(0, self.check_interval - elapsed)
            await asyncio.sleep(sleep_time)

    # -- pipeline execution --------------------------------------------------

    async def _execute_pipeline(self, task: ScheduledTask) -> None:
        """Выполнить pipeline для одной задачи с обработкой ошибок."""
        print(f"[AutonomousLoop] Executing task: {task.name} (pipeline: {task.pipeline})")

        try:
            result = await self.executor.execute(task)

            if result.success:
                self.stats["tasks_completed"] += 1
                task.error_count = max(0, task.error_count - 1)  # сброс ошибки
                print(f"  OK: {task.name} | stages: {result.stages_completed}")
                if result.quality_score > 0:
                    print(f"  Quality score: {result.quality_score:.2f}")
                if result.published:
                    print(f"  Published: True")
                # Уведомление админов об успехе
                await self._notify_admins(
                    f"<b>✅ Zadacha vypolnena:</b> {task.name}\n"
                    f"Etapov: {len(result.stages_completed)}\n"
                    f"Quality: {result.quality_score:.2f}\n"
                    f"Published: {'YES' if result.published else 'NO'}"
                )
            else:
                self.stats["tasks_failed"] += 1
                print(f"  FAIL: {task.name} | error: {result.error}")
                # Уведомление админов об ошибке
                await self._notify_admins(
                    f"<b>❌ Zadacha provalena:</b> {task.name}\n"
                    f"Oshibka: {result.error or 'Unknown'}"
                )

            # Сохраняем результат
            self._results_log.append(result.to_dict())

        except Exception as exc:
            self.stats["tasks_failed"] += 1
            print(f"[AutonomousLoop] Pipeline exception for '{task.name}': {exc}")

        finally:
            # Обновляем расписание (пересчитываем next_run)
            self.scheduler.mark_executed(task)
            next_human = datetime.fromtimestamp(task.next_run).strftime("%Y-%m-%d %H:%M") if task.next_run else "?"
            print(f"  Next run: {next_human}")

    # -- query helpers ------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Агрегированная статистика автономного цикла.

        Returns:
            Словарь с counts, uptime, scheduler overview.
        """
        uptime = 0.0
        if self.stats["started_at"]:
            uptime = time.time() - self.stats["started_at"]

        return {
            **self.stats,
            "uptime_sec": round(uptime, 2),
            "running": self.running,
            "scheduler": self.scheduler.get_overview(),
            "recent_results": self._results_log[-10:],
        }

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Получить статус задачи по ID."""
        task = self.scheduler.tasks.get(task_id)
        if not task:
            return None
        return task.to_dict()

    def list_tasks(self) -> List[Dict[str, Any]]:
        """Список всех задач в планировщике."""
        return [t.to_dict() for t in self.scheduler.tasks.values()]

    async def trigger_task_now(self, task_id: str) -> Optional[PipelineResult]:
        """Принудительно запустить задачу по ID (для ручного триггера)."""
        task = self.scheduler.tasks.get(task_id)
        if not task:
            return None

        print(f"[AutonomousLoop] Manual trigger for task: {task.name}")
        result = await self.executor.execute(task)
        self.scheduler.mark_executed(task)
        return result

    async def _notify_admins(self, text: str) -> None:
        """Отправить уведомление админам через Telegram Bot."""
        if self.telegram_bot is not None:
            try:
                await self.telegram_bot.broadcast_to_admins(text)
            except Exception as exc:
                print(f"[AutonomousLoop] Notify error: {exc}")
