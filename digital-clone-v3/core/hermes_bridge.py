"""
Hermes Bridge — интеграция Digital Clone v3 с Hermes Agent.

Использует Hermes как:
1. LLM Engine — через oneshot mode (hermes -z) для генерации контента
2. Memory Store — чтение/запись в ~/.hermes/memories/
3. Task Scheduler — cron-задачи в ~/.hermes/cron/
4. Future: Gateway — Telegram/Discord/WhatsApp через Hermes
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


HERMES_HOME = Path.home() / ".hermes"
HERMES_BIN = Path(os.getenv("HERMES_BIN", shutil.which("hermes") or ""))


@dataclass
class HermesMessage:
    """Сообщение для отправки через Hermes Gateway."""

    platform: str
    chat_id: str
    text: str
    parse_mode: Optional[str] = None
    attachments: Optional[List[Dict[str, Any]]] = None


@dataclass
class HermesTask:
    """Задача для планирования через Hermes Cron."""

    name: str
    description: str
    cron: str
    skill: str
    params: Dict[str, Any]


class HermesBridge:
    """Мост между Digital Clone v3 и Hermes Agent.

    Usage:
        bridge = HermesBridge()
        await bridge.connect()

        # Генерация контента через Hermes LLM
        response = await bridge.send_message(
            platform="internal",
            chat_id="jarvis",
            text="Напиши пост про AI"
        )

        # Работа с памятью
        memories = await bridge.query_memory("AI автоматизация")
        await bridge.save_to_memory("Пользователь предпочитает короткие посты")
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config = config or {}
        self._connected = False
        self._hermes_home = Path(self.config.get("hermes_home", HERMES_HOME))
        self._bin = Path(self.config.get("hermes_bin", "")) or HERMES_BIN

    # -----------------------------------------------------------------------
    # Connection
    # -----------------------------------------------------------------------

    async def connect(self) -> bool:
        """Проверить, что Hermes установлен и работает."""
        if not self._bin or not self._bin.exists():
            # Попробуем найти в стандартных местах
            candidates = [
                Path.home() / "AppData" / "Local" / "hermes" / "hermes-agent" / "venv" / "Scripts" / "hermes.exe",
                Path("/usr/local/bin/hermes"),
                Path("/usr/bin/hermes"),
            ]
            for candidate in candidates:
                if candidate.exists():
                    self._bin = candidate
                    break

        if not self._bin or not self._bin.exists():
            self._connected = False
            return False

        # Проверим, что Hermes отвечает
        try:
            proc = await asyncio.create_subprocess_exec(
                str(self._bin), "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
            if b"Hermes Agent" in stdout:
                self._connected = True
                return True
        except Exception:
            pass

        self._connected = False
        return False

    def is_connected(self) -> bool:
        """Проверить статус подключения."""
        return self._connected

    # -----------------------------------------------------------------------
    # LLM / Messaging
    # -----------------------------------------------------------------------

    async def send_message(
        self, platform: str, chat_id: str, text: str, **kwargs
    ) -> Dict[str, Any]:
        """Отправить сообщение или сгенерировать контент через Hermes.

        Пока Gateway не запущен, используем Hermes как LLM engine:
        вызываем `hermes -z "prompt"` и возвращаем результат.

        Args:
            platform: "internal" | "telegram" | "discord" | ...
            chat_id: ID чата (для internal можно "jarvis")
            text: Промпт / текст сообщения

        Returns:
            {"success": bool, "text": str, "error": str}
        """
        if not self._connected:
            return {
                "success": False,
                "error": "Hermes not connected. Call await bridge.connect() first.",
                "platform": platform,
            }

        try:
            proc = await asyncio.create_subprocess_exec(
                str(self._bin), "-z", text,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)

            output = stdout.decode("utf-8", errors="replace").strip()
            errors = stderr.decode("utf-8", errors="replace").strip()

            if proc.returncode != 0:
                return {
                    "success": False,
                    "error": f"Hermes exited with code {proc.returncode}: {errors}",
                    "platform": platform,
                }

            return {
                "success": True,
                "text": output,
                "platform": platform,
                "chat_id": chat_id,
            }

        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": "Hermes oneshot timed out after 120s",
                "platform": platform,
            }
        except Exception as exc:
            return {
                "success": False,
                "error": str(exc),
                "platform": platform,
            }

    async def broadcast(self, text: str, platforms: Optional[List[str]] = None) -> Dict[str, Any]:
        """Отправить сообщение сразу на несколько платформ."""
        platforms = platforms or ["telegram"]
        results = {}
        for platform in platforms:
            results[platform] = await self.send_message(platform, "", text)
        return results

    # -----------------------------------------------------------------------
    # Memory
    # -----------------------------------------------------------------------

    async def query_memory(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Поиск по Hermes Memory (MEMORY.md + USER.md).

        Returns:
            Список записей, отсортированных по релевантности (простой keyword search).
        """
        memory_file = self._hermes_home / "memories" / "MEMORY.md"
        user_file = self._hermes_home / "memories" / "USER.md"

        results = []
        query_lower = query.lower()

        for file_path in (memory_file, user_file):
            if not file_path.exists():
                continue
            try:
                content = file_path.read_text(encoding="utf-8")
                # Разбиваем на записи (по заголовкам или пустым строкам)
                entries = [e.strip() for e in content.split("\n\n") if e.strip()]
                for entry in entries:
                    score = sum(1 for word in query_lower.split() if word in entry.lower())
                    if score > 0:
                        results.append({
                            "source": file_path.name,
                            "content": entry[:500],
                            "score": score,
                        })
            except Exception:
                continue

        # Сортируем по score и обрезаем до k
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:k]

    async def save_to_memory(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Сохранить запись в Hermes MEMORY.md.

        Returns:
            ID созданной записи.
        """
        memory_dir = self._hermes_home / "memories"
        memory_dir.mkdir(parents=True, exist_ok=True)
        memory_file = memory_dir / "MEMORY.md"

        entry_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().isoformat()
        meta_str = json.dumps(metadata, ensure_ascii=False) if metadata else "{}"

        entry = f"""
---
id: {entry_id}
time: {timestamp}
meta: {meta_str}
---
{content}
"""
        try:
            with open(memory_file, "a", encoding="utf-8") as f:
                f.write(entry + "\n\n")
            return entry_id
        except Exception as exc:
            return f"error:{exc}"

    # -----------------------------------------------------------------------
    # Scheduling
    # -----------------------------------------------------------------------

    async def schedule_task(self, task: HermesTask) -> Dict[str, Any]:
        """Запланировать задачу через Hermes Cron.

        Hermes хранит cron-задачи в ~/.hermes/cron/ как JSON файлы.
        """
        cron_dir = self._hermes_home / "cron"
        cron_dir.mkdir(parents=True, exist_ok=True)

        task_id = f"dcv3_{task.name.lower().replace(' ', '_')}_{uuid.uuid4().hex[:6]}"
        task_file = cron_dir / f"{task_id}.json"

        payload = {
            "id": task_id,
            "name": task.name,
            "description": task.description,
            "schedule": {"type": "cron", "value": task.cron},
            "skill": task.skill,
            "params": task.params,
            "created_at": datetime.now().isoformat(),
            "source": "digital-clone-v3",
        }

        try:
            task_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            return {
                "success": True,
                "task_id": task_id,
                "file": str(task_file),
            }
        except Exception as exc:
            return {
                "success": False,
                "error": str(exc),
                "task": task.name,
            }

    async def list_scheduled_tasks(self) -> List[Dict[str, Any]]:
        """Список запланированных задач из Hermes Cron."""
        cron_dir = self._hermes_home / "cron"
        if not cron_dir.exists():
            return []

        tasks = []
        for task_file in sorted(cron_dir.glob("*.json")):
            try:
                data = json.loads(task_file.read_text(encoding="utf-8"))
                data["_file"] = task_file.name
                tasks.append(data)
            except Exception:
                continue
        return tasks

    # -----------------------------------------------------------------------
    # Skills
    # -----------------------------------------------------------------------

    async def register_skill(self, name: str, handler: Any, description: str = "") -> Dict[str, Any]:
        """Зарегистрировать DCv3 skill в Hermes.

        Создаёт SKILL.md в ~/.hermes/skills/ для Hermes.
        """
        skills_dir = self._hermes_home / "skills" / name
        skills_dir.mkdir(parents=True, exist_ok=True)

        skill_md = skills_dir / "SKILL.md"
        content = f"""---
name: {name}
description: {description}
version: 1.0.0
source: digital-clone-v3
---

# {name}

{description}

## Usage

This skill is registered by Digital Clone v3.
Handler: {handler!r}
"""
        try:
            skill_md.write_text(content, encoding="utf-8")
            return {
                "success": True,
                "skill_id": name,
                "path": str(skill_md),
            }
        except Exception as exc:
            return {
                "success": False,
                "error": str(exc),
                "skill": name,
            }

    async def list_hermes_skills(self) -> List[str]:
        """Список доступных skills в Hermes."""
        skills_dir = self._hermes_home / "skills"
        if not skills_dir.exists():
            return []
        return [d.name for d in skills_dir.iterdir() if d.is_dir()]

    # -----------------------------------------------------------------------
    # Health
    # -----------------------------------------------------------------------

    async def health_check(self) -> Dict[str, Any]:
        """Проверить состояние интеграции."""
        hermes_version = "unknown"
        if self._connected and self._bin:
            try:
                proc = await asyncio.create_subprocess_exec(
                    str(self._bin), "--version",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
                hermes_version = stdout.decode("utf-8", errors="replace").strip()
            except Exception:
                pass

        return {
            "connected": self._connected,
            "hermes_home": str(self._hermes_home),
            "hermes_bin": str(self._bin),
            "hermes_version": hermes_version,
            "gateway": False,  # Gateway ещё не запущен
            "memory": (self._hermes_home / "memories" / "MEMORY.md").exists(),
            "cron": (self._hermes_home / "cron").exists(),
            "skills": len(await self.list_hermes_skills()),
            "status": "connected" if self._connected else "disconnected",
            "message": "HermesBridge is active" if self._connected else "Hermes not found",
        }
