"""
Real Tools for Digital Clone v3 — MCP Layer Integration
=========================================================
Реальные инструменты, которые вызывают внешние Python-скрипты
через subprocess. Интегрируются с MCPLayer через регистрацию
MCPTool объектов.

Инструменты:
1. tg_publish_post   — публикация поста через tg_publish.py
2. shorts_generate   — генерация шортса через shorts_pipeline.py
3. content_publish   — полный pipeline: generate + publish
4. video_publish_full — полный pipeline: generate video + publish
5. tg_send_video     — отправка видео в Telegram

Паттерн:
- Каждый метод = async handler для MCPTool
- Поиск скриптов в нескольких возможных локациях
- Subprocess с таймаутом, env-переменными, обработкой ошибок
- Возврат человекочитаемого результата (OK + данные или ERROR)
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import subprocess
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

logger = logging.getLogger("real_tools")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Где искать внешние скрипты (относительно project_root)
SEARCH_PATHS_TG_PUBLISH = [
    "tg_publish.py",
    "tools/tg_publish.py",
    "../digclone/tg_publish.py",
    "../tg_publish.py",
    "scripts/tg_publish.py",
]

SEARCH_PATHS_SHORTS_PIPELINE = [
    "shorts_pipeline.py",
    "tools/shorts_pipeline.py",
    "../digclone/shorts_pipeline.py",
    "../shorts_pipeline.py",
    "scripts/shorts_pipeline.py",
]

# Timeouts (seconds)
TIMEOUT_PUBLISH = 30
TIMEOUT_VIDEO_GEN = 300
TIMEOUT_TELEGRAM_API = 60

# Telegram
DEFAULT_CHANNEL = "@agent_exe23"


# ---------------------------------------------------------------------------
# RealTools class
# ---------------------------------------------------------------------------


class RealTools:
    """Реальные инструменты, которые вызывают внешние скрипты.

    Интегрируется с MCPLayer через register_with_mcp() который создаёт
    MCPTool объекты и регистрирует их в реестре инструментов.

    Args:
        llm_router: Опциональный LLM Router для генерации контента.
        project_root: Корневая директория проекта. Если None —
                      вычисляется относительно этого файла.
    """

    def __init__(
        self,
        llm_router: Optional[Any] = None,
        project_root: Optional[str] = None,
    ) -> None:
        self.llm = llm_router
        self.project_root = Path(project_root or self._default_project_root())
        self._script_cache: Dict[str, Optional[Path]] = {}  # Кэш найденных скриптов
        # Video Creator (Motion Canvas + Blender hybrid)
        try:
            from core.video_creator import VideoCreator
            self._video_creator = VideoCreator(llm_router=llm_router, project_root=str(self.project_root))
            logger.info("VideoCreator initialized")
        except ImportError as e:
            self._video_creator = None
            logger.warning("VideoCreator not available: %s", e)

        logger.info(
            "RealTools initialized (project_root=%s, llm=%s)",
            self.project_root,
            "yes" if llm_router else "no",
        )

    # -- helpers ---------------------------------------------------------------

    @staticmethod
    def _default_project_root() -> str:
        """Вычислить project_root по умолчанию (родитель директории core/)."""
        return str(Path(__file__).parent.parent)

    def _find_script(self, search_paths: List[str]) -> Optional[Path]:
        """Найти скрипт по списку возможных путей (с кэшированием).

        Args:
            search_paths: Список относительных путей для проверки.

        Returns:
            Path к найденному файлу или None.
        """
        cache_key = "|".join(search_paths)
        if cache_key in self._script_cache:
            return self._script_cache[cache_key]

        for rel_path in search_paths:
            candidate = self.project_root / rel_path
            if candidate.exists() and candidate.is_file():
                logger.info("Found script: %s", candidate)
                self._script_cache[cache_key] = candidate
                return candidate

        # Также проверяем в PATH
        for rel_path in search_paths:
            name = Path(rel_path).name
            for path_dir in os.environ.get("PATH", "").split(os.pathsep):
                candidate = Path(path_dir) / name
                if candidate.exists() and candidate.is_file():
                    logger.info("Found script in PATH: %s", candidate)
                    self._script_cache[cache_key] = candidate
                    return candidate

        logger.warning("Script not found. Searched: %s", search_paths)
        self._script_cache[cache_key] = None
        return None

    def _load_env(self) -> Dict[str, str]:
        """Загрузить .env файл и вернуть обновлённое окружение.

        Ищет .env в project_root и поднимается на 2 уровня вверх.
        """
        env = os.environ.copy()

        # Попытка загрузить python-dotenv если доступен
        try:
            from dotenv import load_dotenv

            env_paths = [
                self.project_root / ".env",
                self.project_root.parent / ".env",
                self.project_root.parent.parent / ".env",
            ]
            for env_path in env_paths:
                if env_path.exists():
                    load_dotenv(str(env_path), override=True)
                    env = os.environ.copy()
                    logger.debug("Loaded .env from %s", env_path)
                    break
        except ImportError:
            # Fallback: ручной парсинг .env
            env_paths = [
                self.project_root / ".env",
                self.project_root.parent / ".env",
                self.project_root.parent.parent / ".env",
            ]
            for env_path in env_paths:
                if env_path.exists():
                    try:
                        with open(env_path, "r", encoding="utf-8") as f:
                            for line in f:
                                line = line.strip()
                                if not line or line.startswith("#"):
                                    continue
                                if "=" in line:
                                    key, value = line.split("=", 1)
                                    env[key.strip()] = value.strip().strip('"').strip("'")
                        logger.debug("Manually parsed .env from %s", env_path)
                    except Exception as exc:
                        logger.warning("Failed to parse .env: %s", exc)
                    break

        return env

    @staticmethod
    def _topic_hash(topic: str) -> str:
        """Создать короткий хеш из темы для использования в путях."""
        return hashlib.md5(topic.encode("utf-8")).hexdigest()[:12]

    async def _run_subprocess(
        self,
        cmd: List[str],
        env: Optional[Dict[str, str]] = None,
        timeout: int = 30,
        cwd: Optional[str] = None,
        input_data: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Запустить subprocess с правильной обработкой ошибок.

        Args:
            cmd: Команда и аргументы (список строк).
            env: Окружение для процесса.
            timeout: Таймаут в секундах.
            cwd: Рабочая директория.
            input_data: Данные для stdin.

        Returns:
            Словарь с keys: success, stdout, stderr, returncode, error.
        """
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                cwd=cwd,
            )

            stdout_b, stderr_b = await asyncio.wait_for(
                proc.communicate(input=input_data.encode("utf-8") if input_data else None),
                timeout=timeout,
            )

            stdout = stdout_b.decode("utf-8", errors="replace").strip()
            stderr = stderr_b.decode("utf-8", errors="replace").strip()

            return {
                "success": proc.returncode == 0,
                "stdout": stdout,
                "stderr": stderr,
                "returncode": proc.returncode,
                "error": None,
            }

        except asyncio.TimeoutError:
            logger.error("Subprocess timeout after %ds: %s", timeout, cmd)
            return {
                "success": False,
                "stdout": "",
                "stderr": "",
                "returncode": -1,
                "error": f"Timeout after {timeout}s",
            }
        except FileNotFoundError as exc:
            logger.error("Command not found: %s — %s", cmd[0], exc)
            return {
                "success": False,
                "stdout": "",
                "stderr": str(exc),
                "returncode": -1,
                "error": f"Command not found: {cmd[0]}",
            }
        except Exception as exc:
            logger.error("Subprocess error: %s — %s", cmd, exc)
            return {
                "success": False,
                "stdout": "",
                "stderr": str(exc),
                "returncode": -1,
                "error": f"{type(exc).__name__}: {exc}",
            }

    # ── 1. tg_publish_post ───────────────────────────────────────────────────

    async def _tg_publish_post(
        self, text: str, channel: str = DEFAULT_CHANNEL
    ) -> str:
        """РЕАЛЬНАЯ публикация поста в Telegram через tg_publish.py.

        Ищет tg_publish.py в нескольких локациях, запускает через
        subprocess с правильным окружением (TG_BOT_TOKEN, TG_CHANNEL).

        Args:
            text: Текст поста для публикации.
            channel: ID канала или username (например, @agent_exe23).

        Returns:
            Строка с результатом: "OK: message_id=123" или "ERROR: ...".
        """
        script = self._find_script(SEARCH_PATHS_TG_PUBLISH)
        if not script:
            return (
                f"[ERROR] tg_publish.py not found. Searched under {self.project_root}: "
                f"{SEARCH_PATHS_TG_PUBLISH}. Please ensure the script exists."
            )

        env = self._load_env()
        env["TG_CHANNEL"] = channel

        # Убедимся что токен установлен
        bot_token = env.get("TG_BOT_TOKEN") or env.get("TELEGRAM_BOT_TOKEN")
        if not bot_token:
            return (
                "[ERROR] TG_BOT_TOKEN / TELEGRAM_BOT_TOKEN not found in environment. "
                "Please set it in .env file."
            )
        env["TG_BOT_TOKEN"] = bot_token

        logger.info("Publishing post to %s via %s", channel, script)

        # Запускаем: python tg_publish.py "Текст поста"
        # Fallback: echo "Текст" | python tg_publish.py
        result = await self._run_subprocess(
            cmd=["python3", str(script), text],
            env=env,
            timeout=TIMEOUT_PUBLISH,
            cwd=str(script.parent),
        )

        if not result["success"]:
            # Пробуем через stdin
            logger.info("Retrying tg_publish via stdin...")
            result = await self._run_subprocess(
                cmd=["python3", str(script)],
                env=env,
                timeout=TIMEOUT_PUBLISH,
                cwd=str(script.parent),
                input_data=text,
            )

        if result["success"]:
            stdout = result["stdout"]
            # Пытаемся извлечь message_id из stdout
            message_id = None
            for line in stdout.splitlines():
                if "message_id" in line.lower() or "msg_id" in line.lower():
                    # Простой парсинг: message_id=123
                    for part in line.replace(",", " ").split():
                        if "=" in part and any(k in part for k in ("message_id", "msg_id")):
                            message_id = part.split("=")[-1]
                            break
            ok_msg = f"Post published to {channel}"
            if message_id:
                ok_msg += f" (message_id={message_id})"
            if stdout:
                ok_msg += f" | Output: {stdout[:200]}"
            logger.info("tg_publish_post OK: %s", ok_msg)
            return f"OK: {ok_msg}"

        error_msg = result["error"] or result["stderr"] or f"exit code {result['returncode']}"
        logger.error("tg_publish_post FAILED: %s", error_msg)
        return f"[ERROR] tg_publish_post failed: {error_msg}"

    # ── 2. shorts_generate ───────────────────────────────────────────────────

    async def _shorts_generate(
        self, topic: str, dry_run: bool = False
    ) -> str:
        """РЕАЛЬНАЯ генерация шортса через shorts_pipeline.py.

        Pipeline:
        1. Находит shorts_pipeline.py
        2. Запускает с --topic и опционально --dry-run
        3. Собирает результат (путь к видео из stdout)
        4. Возвращает путь к готовому видео

        Args:
            topic: Тема шортса.
            dry_run: Тестовый прогон без реальной генерации.

        Returns:
            Строка с результатом: путь к видео или описание ошибки.
        """
        script = self._find_script(SEARCH_PATHS_SHORTS_PIPELINE)
        if not script:
            return (
                f"[ERROR] shorts_pipeline.py not found. Searched under {self.project_root}: "
                f"{SEARCH_PATHS_SHORTS_PIPELINE}."
            )

        env = self._load_env()
        topic_h = self._topic_hash(topic)
        output_dir = self.project_root / "output" / "shorts" / topic_h

        env["SHORTS_OUTPUT_DIR"] = str(output_dir)
        env["PYTHONPATH"] = str(self.project_root) + os.pathsep + env.get("PYTHONPATH", "")

        cmd = ["python3", str(script), "--topic", topic]
        if dry_run:
            cmd.append("--dry-run")

        logger.info(
            "Generating shorts for topic='%s' (dry_run=%s) via %s",
            topic, dry_run, script,
        )

        result = await self._run_subprocess(
            cmd=cmd,
            env=env,
            timeout=TIMEOUT_VIDEO_GEN,
            cwd=str(script.parent),
        )

        if not result["success"]:
            error_msg = result["error"] or result["stderr"] or f"exit {result['returncode']}"
            logger.error("shorts_generate FAILED: %s", error_msg)
            return f"[ERROR] shorts_generate failed: {error_msg}"

        stdout = result["stdout"]
        logger.info("shorts_generate stdout: %s", stdout[:500])

        # Ищем путь к видео в stdout
        video_path: Optional[str] = None
        for line in stdout.splitlines():
            line_stripped = line.strip()
            # Ищем строки с .mp4, .mov, и т.д.
            for ext in (".mp4", ".mov", ".avi", ".mkv", ".webm"):
                if ext in line_stripped.lower():
                    # Извлекаем потенциальный путь
                    words = line_stripped.split()
                    for w in words:
                        if ext in w.lower():
                            video_path = w
                            break
                    if video_path:
                        break
            if video_path:
                break

        # Если не нашли в stdout — проверяем output директорию
        if not video_path and output_dir.exists():
            video_files = list(output_dir.glob("*.mp4"))
            if video_files:
                video_path = str(video_files[0])

        if video_path:
            # Проверяем что файл реально существует
            vp = Path(video_path)
            if not vp.is_absolute():
                vp = self.project_root / vp
            if vp.exists():
                logger.info("Shorts video found: %s", vp)
                return f"OK: Video generated at {vp} (topic='{topic}')"

        # dry_run или файл не создан — возвращаем stdout
        if dry_run:
            return f"OK (dry-run): {stdout[:300]}"

        return (
            f"OK: Pipeline completed. stdout: {stdout[:300]}\n"
            f"Note: Video file not detected in expected locations. "
            f"Check {output_dir}/ for output files."
        )

    # ── 3. content_publish_full ──────────────────────────────────────────────

    async def _content_publish_full(
        self, topic: str, channel: str = DEFAULT_CHANNEL
    ) -> str:
        """Полный pipeline: сгенерировать контент → опубликовать.

        Steps:
        1. Генерирует Telegram-пост на заданную тему через LLM Router.
        2. Публикует через tg_publish_post.
        3. Возвращает результат со ссылкой на пост.

        Args:
            topic: Тема для генерации поста.
            channel: Канал для публикации.

        Returns:
            Строка с результатом операции.
        """
        logger.info("content_publish_full: topic='%s', channel='%s'", topic, channel)

        # Шаг 1: Генерация поста через LLM Router
        post_text: str
        if self.llm is not None:
            prompt = (
                f"Напиши короткий Telegram-пост на тему: '{topic}'.\n"
                f"Требования:\n"
                f"- Длина: 2-4 абзаца\n"
                f"- Стиль: разговорный, увлекательный\n"
                f"- Добавь 3-5 релевантных хештегов в конце\n"
                f"- Без markdown-разметки (Telegram не поддерживает)\n"
                f"- Можно использовать **жирный** текст и _курсив_\n\n"
                f"Пост:"
            )
            try:
                generated = await self.llm.complete(prompt, max_tokens=800, temperature=0.7)
                post_text = generated.strip()
                logger.info("Post generated by LLM (%d chars)", len(post_text))
            except Exception as exc:
                logger.error("LLM generation failed: %s", exc)
                post_text = (
                    f"📌 {topic}\n\n"
                    f"Интересная тема, требующая внимания!\n\n"
                    f"Подписывайтесь на обновления — будет много полезного контента.\n\n"
                    f"#{topic.replace(' ', '').replace('-', '')} #digital #ai"
                )
        else:
            # Fallback без LLM
            post_text = (
                f"📌 {topic}\n\n"
                f"Сегодня поговорим об этой важной теме.\n"
                f"Следите за обновлениями в канале!\n\n"
                f"#{topic.replace(' ', '').replace('-', '')} #digital #ai #content"
            )
            logger.info("Post generated without LLM (fallback)")

        # Шаг 2: Публикация
        publish_result = await self._tg_publish_post(text=post_text, channel=channel)

        if publish_result.startswith("OK"):
            return (
                f"OK: Content pipeline completed.\n"
                f"  Topic: {topic}\n"
                f"  Channel: {channel}\n"
                f"  Post length: {len(post_text)} chars\n"
                f"  Publish: {publish_result}"
            )

        return (
            f"[PARTIAL ERROR] Post generated ({len(post_text)} chars) but publish failed.\n"
            f"  Publish result: {publish_result}\n"
            f"  Generated text preview: {post_text[:200]}..."
        )

    # ── 4. video_publish_full ────────────────────────────────────────────────

    async def _video_publish_full(
        self, topic: str, channel: str = DEFAULT_CHANNEL
    ) -> str:
        """Полный pipeline: сгенерировать шортс → опубликовать.

        Steps:
        1. Сгенерировать шортс через shorts_generate.
        2. Отправить в Telegram через tg_send_video.
        3. Вернуть результат.

        Args:
            topic: Тема для шортса.
            channel: Канал для публикации.

        Returns:
            Строка с результатом операции.
        """
        logger.info("video_publish_full: topic='%s', channel='%s'", topic, channel)

        # Шаг 1: Генерация шортса
        gen_result = await self._shorts_generate(topic=topic, dry_run=False)

        if gen_result.startswith("[ERROR]"):
            return f"[ERROR] Video generation failed: {gen_result}"

        # Извлекаем путь к видео из результата
        video_path: Optional[str] = None
        for marker in ("at ", "to ", ": "):
            if marker in gen_result and ".mp4" in gen_result.lower():
                # Простой парсинг
                parts = gen_result.split()
                for i, p in enumerate(parts):
                    if ".mp4" in p.lower():
                        video_path = p
                        break
                if video_path:
                    break

        if not video_path:
            return (
                f"[PARTIAL] Video generated but path not found in output.\n"
                f"  Generation result: {gen_result}\n"
                f"  Cannot proceed to publishing without video file path."
            )

        # Очистка пути от trailing punctuation
        video_path = video_path.strip(".,;:!?|\"")

        # Шаг 2: Отправка видео
        caption = f"📹 {topic}\n\nСгенерировано автоматически."
        send_result = await self._tg_send_video(
            video_path=video_path,
            chat_id=channel,
            caption=caption,
        )

        if send_result.startswith("OK"):
            return (
                f"OK: Video pipeline completed.\n"
                f"  Topic: {topic}\n"
                f"  Channel: {channel}\n"
                f"  Video: {video_path}\n"
                f"  Send: {send_result}"
            )

        return (
            f"[PARTIAL ERROR] Video generated ({video_path}) but send failed.\n"
            f"  Send result: {send_result}"
        )

    # ── 5. tg_send_video ─────────────────────────────────────────────────────

    async def _tg_send_video(
        self, video_path: str, chat_id: str, caption: str = ""
    ) -> str:
        """Отправить видео в Telegram через Bot API.

        Использует multipart/form-data запрос к Telegram Bot API.

        Args:
            video_path: Путь к видео-файлу.
            chat_id: ID чата или канала.
            caption: Подпись к видео.

        Returns:
            Строка с результатом отправки.
        """
        env = self._load_env()
        token = env.get("TELEGRAM_BOT_TOKEN") or env.get("TG_BOT_TOKEN")
        if not token:
            return (
                "[ERROR] TELEGRAM_BOT_TOKEN / TG_BOT_TOKEN not set. "
                "Please configure .env file."
            )

        vp = Path(video_path)
        if not vp.is_absolute():
            vp = self.project_root / vp
        if not vp.exists():
            return f"[ERROR] Video file not found: {vp}"

        file_size = vp.stat().st_size
        if file_size > 50 * 1024 * 1024:
            return (
                f"[ERROR] Video file too large: {file_size / (1024*1024):.1f}MB. "
                f"Telegram limit: 50MB for bots."
            )

        logger.info(
            "Sending video %s (%d bytes) to %s", vp, file_size, chat_id,
        )

        try:
            import aiohttp
        except ImportError:
            # Fallback: используем requests если aiohttp недоступен
            return await self._tg_send_video_requests(
                token=token, video_path=str(vp), chat_id=chat_id, caption=caption
            )

        url = f"https://api.telegram.org/bot{token}/sendVideo"

        try:
            async with aiohttp.ClientSession() as session:
                data = aiohttp.FormData()
                data.add_field("chat_id", str(chat_id))
                data.add_field("video", vp.open("rb"), filename=vp.name)
                if caption:
                    data.add_field("caption", caption)
                data.add_field("supports_streaming", "true")

                async with session.post(url, data=data, timeout=aiohttp.ClientTimeout(total=120)) as resp:
                    response_text = await resp.text()
                    if resp.status == 200:
                        import json
                        try:
                            data_json = json.loads(response_text)
                            if data_json.get("ok"):
                                msg_id = data_json["result"].get("message_id", "?")
                                logger.info("Video sent to %s (msg_id=%s)", chat_id, msg_id)
                                return f"OK: Video sent to {chat_id} (message_id={msg_id})"
                            return f"[TG API ERROR] {data_json.get('description', 'Unknown')}"
                        except json.JSONDecodeError:
                            return f"OK: Video sent (raw: {response_text[:100]})"
                    return f"[HTTP ERROR] Status {resp.status}: {response_text[:200]}"
        except Exception as exc:
            logger.error("tg_send_video error: %s", exc)
            return f"[ERROR] tg_send_video failed: {type(exc).__name__}: {exc}"

    async def _tg_send_video_requests(
        self, token: str, video_path: str, chat_id: str, caption: str = ""
    ) -> str:
        """Fallback отправка видео через requests (синхронный)."""
        try:
            import requests
        except ImportError:
            return "[ERROR] Neither aiohttp nor requests installed. Run: pip install aiohttp requests"

        url = f"https://api.telegram.org/bot{token}/sendVideo"
        try:
            with open(video_path, "rb") as f:
                files = {"video": f}
                payload = {"chat_id": chat_id, "supports_streaming": True}
                if caption:
                    payload["caption"] = caption

                resp = requests.post(url, data=payload, files=files, timeout=120)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("ok"):
                        msg_id = data["result"].get("message_id", "?")
                        return f"OK: Video sent to {chat_id} (message_id={msg_id})"
                    return f"[TG API ERROR] {data.get('description', 'Unknown')}"
                return f"[HTTP ERROR] Status {resp.status_code}: {resp.text[:200]}"
        except FileNotFoundError:
            return f"[ERROR] Video file not found: {video_path}"
        except Exception as exc:
            return f"[ERROR] {type(exc).__name__}: {exc}"

    # -- Video Creator (Motion Canvas + Blender) ----------------------------

    async def _video_create_remotion(self, topic: str = "AI automation", duration: float = 15.0, composition: str = "FinalComposition", **kwargs) -> str:
        """Создать ролик через Remotion (React-based video renderer).

        Pipeline:
            1. Использует Remotion композицию из video/src/Root.tsx
            2. Рендерит через @remotion/cli
            3. Возвращает готовый MP4

        Args:
            topic: Тема ролика (используется в props композиции).
            duration: Длительность в секундах (default: 15).
            composition: Название композиции из Root.tsx (MinimalVideo, AnimatedText, DataCounter, NeonText, ParticleBackground, FinalComposition).

        Returns:
            Путь к готовому MP4 или ERROR.
        """
        if self._video_creator is None:
            return "[ERROR] VideoCreator ne inicializirovan (prover zavisimosti)"

        # Проверяем Remotion
        if not getattr(self._video_creator, 'has_remotion', False):
            return (
                "[ERROR] Remotion ne ustanovlen. "
                "Ustanovi: npm install remotion @remotion/cli @remotion/renderer react react-dom typescript"
            )

        # Запускаем рендер через Remotion CLI
        project_root = self._video_creator.project_root
        remotion_cmd = None
        for candidate in [
            project_root / "node_modules" / ".bin" / "remotion.cmd",
            project_root / "node_modules" / ".bin" / "remotion",
        ]:
            if candidate.exists():
                remotion_cmd = str(candidate)
                break

        if remotion_cmd is None:
            return "[ERROR] Remotion CLI ne najden"

        output_dir = self.project_root / "output" / "videos"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"remotion_{self._topic_hash(topic)}_{composition}.mp4"

        try:
            cmd = [
                remotion_cmd, "render",
                str(project_root / "video" / "src" / "index.tsx"),
                composition,
                str(output_path),
                "--codec", "h264",
            ]
            result = await self._run_subprocess(
                cmd=cmd,
                cwd=str(project_root),
                timeout=TIMEOUT_VIDEO_GEN,
            )
            if result["success"] and output_path.exists():
                return (
                    f"[OK] Remotion rolik sozdan: {output_path}\n"
                    f"     Tema: {topic}\n"
                    f"     Komponovka: {composition}\n"
                    f"     Format: 1920x1080"
                )
            else:
                err = result["error"] or result["stderr"] or f"exit {result['returncode']}"
                return f"[ERROR] Remotion render failed: {err[:500]}"
        except Exception as exc:
            logger.error("Remotion creation failed: %s", exc, exc_info=True)
            return f"[ERROR] {type(exc).__name__}: {exc}"

    async def _video_create_asset_engine(self, topic: str = "AI automation", duration: float = 15.0, **kwargs) -> str:
        """Sozdat rolik cherez Asset Engine (stil Arsenija Merzljakova).

        Pipeline:
            1. Isket stock-assety (video/zvuk)
            2. Sobirajet 3 sceny: Problema → Reshenije → Rezultat
            3. Dobavljaet cvetokorrektsiju, zoom, nadpisi, zvukovye effekty
            4. Eksport v MP4 (1080x1920, Shorts)

        Args:
            topic: Tema rolikа.
            duration: Dlitelnost v sekundakh (default: 15).

        Returns:
            Put k gotovomu MP4 ili ERROR.
        """
        if self._video_creator is None:
            return "[ERROR] VideoCreator ne inicializirovan"
        if not getattr(self._video_creator, 'has_asset_engine', False):
            return (
                "[ERROR] Asset Engine ne dostupen. "
                "Prover: ffmpeg ustanovlen, core/asset_downloader.py zagruzhen"
            )

        duration = float(duration)
        try:
            result_path = await self._video_creator.create_video_asset_engine(
                topic=topic, duration=duration
            )
            if result_path.startswith("[ERROR]"):
                return result_path
            return (
                f"[OK] Asset Engine rolik sozdan: {result_path}\n"
                f"     Tema: {topic}\n"
                f"     Dlitelnost: {duration}s\n"
                f"     Stil: Merzljakov (3 sceny + effekty)\n"
                f"     Format: 1080x1920 (Shorts/Reels/TikTok)"
            )
        except Exception as exc:
            logger.error("Asset Engine creation failed: %s", exc, exc_info=True)
            return f"[ERROR] {type(exc).__name__}: {exc}"

    async def _video_create_hybrid(self, topic: str = "AI automation", duration: float = 15.0, style: str = "hybrid", **kwargs) -> str:
        """Создать гибридный ролик: Motion Canvas + Blender.

        Pipeline:
            1. LLM планирует сегменты (хук/MC + сцена/Blender + CTA/MC)
            2. Генерирует код для каждого сегмента
            3. Рендерит Motion Canvas (2D анимация) + Blender (3D сцена)
            4. ffmpeg склеивает + Edge-TTS озвучка

        Args:
            topic: Тема ролика (например: "AI в продажах")
            duration: Длительность в секундах (default: 15)
            style: "hybrid" | "motion_canvas" | "blender_3d" (default: hybrid)

        Returns:
            Путь к готовому MP4 или ERROR.
        """
        if self._video_creator is None:
            return "[ERROR] VideoCreator не инициализирован (проверь зависимости)"

        duration = float(duration)

        try:
            result_path = await self._video_creator.create_video(
                topic=topic, style=style, duration=duration
            )
            if result_path.startswith("ERROR"):
                return f"[ERROR] {result_path}"
            return (
                f"[OK] Ролик создан: {result_path}\n"
                f"     Тема: {topic}\n"
                f"     Длительность: {duration}s\n"
                f"     Стиль: {style}\n"
                f"     Формат: 1080x1920 (Shorts/Reels/TikTok)"
            )
        except Exception as exc:
            logger.error("Video creation failed: %s", exc, exc_info=True)
            return f"[ERROR] {type(exc).__name__}: {exc}"

    # -- MCP registration ------------------------------------------------------

    def register_with_mcp(self, mcp_layer: Any) -> None:
        """Зарегистрировать все real tools в MCP Layer.

        Создаёт MCPTool объекты для каждого инструмента и регистрирует
        их через mcp_layer.register_tool().

        Args:
            mcp_layer: Экземпляр MCPLayer.
        """
        from core.mcp_layer import MCPTool, MCPToolType

        tools: List[MCPTool] = [
            MCPTool(
                name="tg_publish_post",
                tool_type=MCPToolType.TELEGRAM,
                description="РЕАЛЬНАЯ публикация поста в Telegram через tg_publish.py. "
                            "Вызывает внешний скрипт который отправляет пост через Bot API. "
                            "Params: {text: string, channel?: string(default='@agent_exe23')}",
                parameters={
                    "text": {
                        "type": "string",
                        "required": True,
                        "description": "Текст поста для публикации",
                    },
                    "channel": {
                        "type": "string",
                        "required": False,
                        "default": DEFAULT_CHANNEL,
                        "description": "Telegram канал (@username или chat_id)",
                    },
                },
                handler=self._tg_publish_post,
                requires_approval=True,  # Публикация требует подтверждения
            ),
            MCPTool(
                name="shorts_generate",
                tool_type=MCPToolType.VIDEO_GEN,
                description="РЕАЛЬНАЯ генерация шортса через shorts_pipeline.py. "
                            "Запускает AI-генерацию изображений + ffmpeg сборку. "
                            "Params: {topic: string, dry_run?: boolean(default=False)}",
                parameters={
                    "topic": {
                        "type": "string",
                        "required": True,
                        "description": "Тема шортса",
                    },
                    "dry_run": {
                        "type": "boolean",
                        "required": False,
                        "default": False,
                        "description": "Тестовый прогон без реальной генерации",
                    },
                },
                handler=self._shorts_generate,
                requires_approval=False,
            ),
            MCPTool(
                name="content_publish_full",
                tool_type=MCPToolType.TELEGRAM,
                description="Полный pipeline: сгенерировать пост через LLM + опубликовать. "
                            "Params: {topic: string, channel?: string(default='@agent_exe23')}",
                parameters={
                    "topic": {
                        "type": "string",
                        "required": True,
                        "description": "Тема для генерации и публикации поста",
                    },
                    "channel": {
                        "type": "string",
                        "required": False,
                        "default": DEFAULT_CHANNEL,
                        "description": "Telegram канал для публикации",
                    },
                },
                handler=self._content_publish_full,
                requires_approval=True,
            ),
            MCPTool(
                name="video_publish_full",
                tool_type=MCPToolType.VIDEO_GEN,
                description="Полный pipeline: сгенерировать шортс + отправить в Telegram. "
                            "Params: {topic: string, channel?: string(default='@agent_exe23')}",
                parameters={
                    "topic": {
                        "type": "string",
                        "required": True,
                        "description": "Тема для шортса",
                    },
                    "channel": {
                        "type": "string",
                        "required": False,
                        "default": DEFAULT_CHANNEL,
                        "description": "Telegram канал для отправки видео",
                    },
                },
                handler=self._video_publish_full,
                requires_approval=True,
            ),
            MCPTool(
                name="tg_send_video",
                tool_type=MCPToolType.TELEGRAM,
                description="Отправить видео в Telegram через Bot API (multipart/form-data). "
                            "Params: {video_path: string, chat_id: string, caption?: string}",
                parameters={
                    "video_path": {
                        "type": "string",
                        "required": True,
                        "description": "Путь к видео-файлу (.mp4 и др.)",
                    },
                    "chat_id": {
                        "type": "string",
                        "required": True,
                        "description": "Telegram chat_id или @channel",
                    },
                    "caption": {
                        "type": "string",
                        "required": False,
                        "default": "",
                        "description": "Подпись к видео",
                    },
                },
                handler=self._tg_send_video,
                requires_approval=False,
            ),
            MCPTool(
                name="video_create_asset_engine",
                tool_type=MCPToolType.VIDEO_GEN,
                description="Создать ролик через Asset Engine (стиль Арсения Мерзлякова). "
                            "3 сцены: Проблема → Решение → Результат + цветокоррекция + эффекты. "
                            "Requires: ffmpeg. "
                            "Params: {topic: string, duration?: number(default=15)}",
                parameters={
                    "topic": {
                        "type": "string",
                        "required": True,
                        "description": "Тема ролика",
                    },
                    "duration": {
                        "type": "number",
                        "required": False,
                        "default": 15.0,
                        "description": "Длительность в секундах",
                    },
                },
                handler=self._video_create_asset_engine,
                requires_approval=False,
            ),
            MCPTool(
                name="video_create_hybrid",
                tool_type=MCPToolType.VIDEO_GEN,
                description="Создать гибридный ролик: Motion Canvas 2D анимация + Blender 3D сцены. "
                            "Рендерит ночью, утром готов MP4 для Shorts/Reels/TikTok. "
                            "Requires: Blender, Node.js, ffmpeg. "
                            "Params: {topic: string, duration?: number(default=15), style?: string(default='hybrid')}",
                parameters={
                    "topic": {
                        "type": "string",
                        "required": True,
                        "description": "Тема ролика (например: 'AI заменяет менеджера')",
                    },
                    "duration": {
                        "type": "number",
                        "required": False,
                        "default": 15.0,
                        "description": "Длительность в секундах (15-60)",
                    },
                    "style": {
                        "type": "string",
                        "required": False,
                        "default": "hybrid",
                        "description": "hybrid (MC+Blender) | motion_canvas (только 2D) | blender_3d (только 3D)",
                    },
                },
                handler=self._video_create_hybrid,
                requires_approval=False,
            ),
            MCPTool(
                name="video_create_remotion",
                tool_type=MCPToolType.VIDEO_GEN,
                description="Создать ролик через Remotion (React-based video renderer). "
                            "Рендерит React-компоненты в MP4 через @remotion/cli. "
                            "Requires: Node.js, Remotion (npm install). "
                            "Params: {topic: string, duration?: number(default=15), composition?: string(default='FinalComposition')}",
                parameters={
                    "topic": {
                        "type": "string",
                        "required": True,
                        "description": "Тема ролика",
                    },
                    "duration": {
                        "type": "number",
                        "required": False,
                        "default": 15.0,
                        "description": "Длительность в секундах",
                    },
                    "composition": {
                        "type": "string",
                        "required": False,
                        "default": "FinalComposition",
                        "description": "MinimalVideo | AnimatedText | DataCounter | NeonText | ParticleBackground | FinalComposition",
                    },
                },
                handler=self._video_create_remotion,
                requires_approval=False,
            ),
        ]

        for tool in tools:
            mcp_layer.register_tool(tool)
            logger.info("Registered real tool: %s", tool.name)

        logger.info(
            "All %d real tools registered with MCPLayer", len(tools)
        )
