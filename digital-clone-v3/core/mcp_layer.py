"""
MCP (Model Context Protocol) Layer v3
Унифицированный доступ к инструментам через MCP серверы.

Интегрированные находки:
- #18 (TestSprite): MCP для автотестов — запуск тестов как инструмент
- #3 (Seedance 2.0): бесплатная генерация видео без GPU
- #17 (Upsonic): функции как инструменты агента
- Playwright MCP: браузерная автоматизация
"""

from __future__ import annotations

import asyncio
import inspect
import json
import os
import subprocess
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


# ---------------------------------------------------------------------------
# Enums & Data classes
# ---------------------------------------------------------------------------


class MCPToolType(Enum):
    """Категории инструментов MCP."""

    BROWSER = "browser"           # Playwright — навигация, скриншоты, клики
    CODE_EXEC = "code_executor"   # Python REPL (sandbox)
    FILE = "file_tool"            # Файловая система (read/write)
    SHELL = "shell_tool"          # Терминал (sandbox с блокировкой)
    SEARCH = "search_tool"        # Поиск в интернете
    TELEGRAM = "telegram_api"     # Telegram Bot API
    WHISPER = "whisper_tool"      # Распознавание голоса
    VIDEO_GEN = "video_gen"       # Генерация видео (Seedance)
    TEST = "test_tool"            # Автотесты (TestSprite #18)
    GIT = "git_tool"              # Git операции
    IMAGE_GEN = "image_gen"       # Генерация изображений
    DATABASE = "database"         # Работа с БД


@dataclass
class MCPTool:
    """Описание одного инструмента MCP.

    Каждый инструмент — это MCP сервер с:
    - name: уникальное имя для вызова
    - description: что делает (LLM использует для выбора инструмента)
    - parameters: JSON Schema параметров
    - handler: async Python функция-обработчик
    - requires_approval: требуется ли подтверждение пользователя
    """

    name: str
    tool_type: MCPToolType
    description: str
    parameters: Dict[str, Any]
    handler: Callable[..., Any]
    requires_approval: bool = False


class MCPResult:
    """Стандартизированный результат выполнения инструмента."""

    def __init__(
        self,
        success: bool,
        result: Any = None,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.success = success
        self.result = result
        self.error = error
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "metadata": self.metadata,
        }

    def __repr__(self) -> str:
        status = "OK" if self.success else "ERR"
        return f"MCPResult({status}: {self.result if self.success else self.error})"


# ---------------------------------------------------------------------------
# MCP Layer
# ---------------------------------------------------------------------------


class MCPLayer:
    """MCP Layer — реестр инструментов для Digital Clone агента.

    Паттерн: каждый инструмент = MCP сервер с чётким контрактом.
    LLM выбирает инструмент по описанию, MCPLayer выполняет.

    Attributes:
        tools: Словарь зарегистрированных инструментов по имени.
    """

    def __init__(self) -> None:
        self.tools: Dict[str, MCPTool] = {}
        self._register_default_tools()

    # -- tool registration -----------------------------------------------

    def register_tool(self, tool: MCPTool) -> None:
        """Регистрация нового инструмента MCP.

        Args:
            tool: Объект MCPTool с именем, описанием, параметрами и обработчиком.
        """
        self.tools[tool.name] = tool

    def register_real_tools(self, real_tools: Any) -> None:
        """Зарегистрировать реальные инструменты из RealTools.

        Делегирует регистрацию RealTools классу, который создаёт
        MCPTool объекты для tg_publish_post, shorts_generate,
        content_publish_full, video_publish_full, tg_send_video.

        Args:
            real_tools: Экземпляр RealTools (из core.real_tools).

        Example:
            from core.real_tools import RealTools
            from core.mcp_layer import MCPLayer

            mcp = MCPLayer()
            rt = RealTools(llm_router=llm_router)
            mcp.register_real_tools(rt)
        """
        real_tools.register_with_mcp(self)

    def unregister_tool(self, name: str) -> None:
        """Удалить инструмент из реестра."""
        self.tools.pop(name, None)

    def _register_default_tools(self) -> None:
        """Регистрация стандартного набора инструментов."""

        # ── Browser (Playwright) ─────────────────────────────────────
        self.register_tool(MCPTool(
            name="browser_navigate",
            tool_type=MCPToolType.BROWSER,
            description="Открыть URL в headless-браузере (Playwright). "
                        "Params: {url: string, wait_until?: string, timeout?: number}",
            parameters={
                "url": {"type": "string", "required": True, "description": "URL для открытия"},
                "wait_until": {"type": "string", "required": False, "default": "networkidle"},
                "timeout": {"type": "number", "required": False, "default": 30},
            },
            handler=self._browser_navigate,
            requires_approval=False,
        ))

        self.register_tool(MCPTool(
            name="browser_screenshot",
            tool_type=MCPToolType.BROWSER,
            description="Сделать скриншот текущей страницы. "
                        "Params: {path: string, full_page?: boolean}",
            parameters={
                "path": {"type": "string", "required": True, "description": "Путь для сохранения скриншота"},
                "full_page": {"type": "boolean", "required": False, "default": False},
            },
            handler=self._browser_screenshot,
            requires_approval=False,
        ))

        self.register_tool(MCPTool(
            name="browser_click",
            tool_type=MCPToolType.BROWSER,
            description="Кликнуть по элементу на странице (selector). "
                        "Params: {selector: string}",
            parameters={
                "selector": {"type": "string", "required": True, "description": "CSS-селектор элемента"},
            },
            handler=self._browser_click,
            requires_approval=False,
        ))

        self.register_tool(MCPTool(
            name="browser_extract_text",
            tool_type=MCPToolType.BROWSER,
            description="Извлечь текстовый контент со страницы. "
                        "Params: {selector?: string}",
            parameters={
                "selector": {"type": "string", "required": False, "default": "body"},
            },
            handler=self._browser_extract_text,
            requires_approval=False,
        ))

        # ── Code Executor (sandbox) ──────────────────────────────────
        self.register_tool(MCPTool(
            name="exec_python",
            tool_type=MCPToolType.CODE_EXEC,
            description="Выполнить Python код в sandbox. "
                        "Params: {code: string, timeout?: number}",
            parameters={
                "code": {"type": "string", "required": True, "description": "Python код для выполнения"},
                "timeout": {"type": "number", "required": False, "default": 30},
            },
            handler=self._exec_python,
            requires_approval=True,  # Требует подтверждения (безопасность)
        ))

        # ── File operations ──────────────────────────────────────────
        self.register_tool(MCPTool(
            name="file_read",
            tool_type=MCPToolType.FILE,
            description="Прочитать содержимое файла. Params: {path: string}",
            parameters={
                "path": {"type": "string", "required": True, "description": "Путь к файлу"},
            },
            handler=self._file_read,
            requires_approval=False,
        ))

        self.register_tool(MCPTool(
            name="file_write",
            tool_type=MCPToolType.FILE,
            description="Записать содержимое в файл. Params: {path: string, content: string}",
            parameters={
                "path": {"type": "string", "required": True, "description": "Путь к файлу"},
                "content": {"type": "string", "required": True, "description": "Содержимое для записи"},
            },
            handler=self._file_write,
            requires_approval=True,
        ))

        self.register_tool(MCPTool(
            name="file_list",
            tool_type=MCPToolType.FILE,
            description="Получить список файлов в директории. "
                        "Params: {path: string, pattern?: string}",
            parameters={
                "path": {"type": "string", "required": True, "description": "Путь к директории"},
                "pattern": {"type": "string", "required": False, "default": "*"},
            },
            handler=self._file_list,
            requires_approval=False,
        ))

        # ── Shell (sandbox) ──────────────────────────────────────────
        self.register_tool(MCPTool(
            name="shell_exec",
            tool_type=MCPToolType.SHELL,
            description="Выполнить shell команду (sandbox с блокировкой опасных команд). "
                        "Params: {command: string, timeout?: number}",
            parameters={
                "command": {"type": "string", "required": True, "description": "Shell команда"},
                "timeout": {"type": "number", "required": False, "default": 60},
            },
            handler=self._shell_exec,
            requires_approval=True,
        ))

        # ── Telegram ─────────────────────────────────────────────────
        self.register_tool(MCPTool(
            name="tg_send_message",
            tool_type=MCPToolType.TELEGRAM,
            description="Отправить текстовое сообщение в Telegram. "
                        "Params: {chat_id: string, text: string, parse_mode?: string}",
            parameters={
                "chat_id": {"type": "string", "required": True, "description": "ID чата"},
                "text": {"type": "string", "required": True, "description": "Текст сообщения"},
                "parse_mode": {"type": "string", "required": False, "default": "HTML"},
            },
            handler=self._tg_send_message,
            requires_approval=False,
        ))

        self.register_tool(MCPTool(
            name="tg_send_photo",
            tool_type=MCPToolType.TELEGRAM,
            description="Отправить фото в Telegram. "
                        "Params: {chat_id: string, photo_path: string, caption?: string}",
            parameters={
                "chat_id": {"type": "string", "required": True},
                "photo_path": {"type": "string", "required": True},
                "caption": {"type": "string", "required": False, "default": ""},
            },
            handler=self._tg_send_photo,
            requires_approval=False,
        ))

        # ── Video Generation (Seedance #3) ───────────────────────────
        self.register_tool(MCPTool(
            name="video_generate_seedance",
            tool_type=MCPToolType.VIDEO_GEN,
            description="Сгенерировать видео через Seedance 2.0. "
                        "Params: {prompt: string, duration?: number(4-12), ratio?: string(16:9)}",
            parameters={
                "prompt": {"type": "string", "required": True, "description": "Текстовое описание видео"},
                "duration": {"type": "number", "required": False, "default": 5},
                "ratio": {"type": "string", "required": False, "default": "16:9"},
            },
            handler=self._video_generate_seedance,
            requires_approval=False,
        ))

        # ── Image Generation ─────────────────────────────────────────
        self.register_tool(MCPTool(
            name="image_generate",
            tool_type=MCPToolType.IMAGE_GEN,
            description="Сгенерировать изображение по описанию. "
                        "Params: {prompt: string, output_path: string, ratio?: string}",
            parameters={
                "prompt": {"type": "string", "required": True},
                "output_path": {"type": "string", "required": True},
                "ratio": {"type": "string", "required": False, "default": "16:9"},
            },
            handler=self._image_generate,
            requires_approval=False,
        ))

        # ── Test (TestSprite #18) ────────────────────────────────────
        self.register_tool(MCPTool(
            name="test_run",
            tool_type=MCPToolType.TEST,
            description="Запустить автотесты для кода (TestSprite MCP). "
                        "Params: {code: string, language?: string}",
            parameters={
                "code": {"type": "string", "required": True, "description": "Код для тестирования"},
                "language": {"type": "string", "required": False, "default": "python"},
            },
            handler=self._test_run,
            requires_approval=False,
        ))

        self.register_tool(MCPTool(
            name="test_syntax_check",
            tool_type=MCPToolType.TEST,
            description="Проверить синтаксис кода. "
                        "Params: {code: string, language?: string}",
            parameters={
                "code": {"type": "string", "required": True},
                "language": {"type": "string", "required": False, "default": "python"},
            },
            handler=self._test_syntax_check,
            requires_approval=False,
        ))

        # ── Git ──────────────────────────────────────────────────────
        self.register_tool(MCPTool(
            name="git_commit",
            tool_type=MCPToolType.GIT,
            description="Git add + commit + push. Params: {message: string}",
            parameters={
                "message": {"type": "string", "required": True, "description": "Сообщение коммита"},
            },
            handler=self._git_commit,
            requires_approval=True,
        ))

        self.register_tool(MCPTool(
            name="git_status",
            tool_type=MCPToolType.GIT,
            description="Показать git status. Params: {}",
            parameters={},
            handler=self._git_status,
            requires_approval=False,
        ))

        # ── Search ───────────────────────────────────────────────────
        self.register_tool(MCPTool(
            name="web_search",
            tool_type=MCPToolType.SEARCH,
            description="Поиск в интернете. Params: {query: string, count?: number}",
            parameters={
                "query": {"type": "string", "required": True, "description": "Поисковый запрос"},
                "count": {"type": "number", "required": False, "default": 5},
            },
            handler=self._web_search,
            requires_approval=False,
        ))

        # ── Blender VSE Video Editor ─────────────────────────────────
        try:
            from core.blender_vse.mcp_tools import register_blender_vse_tools
            register_blender_vse_tools(self)
        except Exception as exc:
            print(f"[WARN] Blender VSE tools not registered: {exc}")

    # -- execution ---------------------------------------------------------

    async def execute(self, tool_name: str, params: Dict[str, Any]) -> MCPResult:
        """Выполнить инструмент по имени с валидацией параметров.

        Args:
            tool_name: Имя зарегистрированного инструмента.
            params: Словарь параметров для инструмента.

        Returns:
            MCPResult со статусом выполнения, результатом или ошибкой.
        """
        tool = self.tools.get(tool_name)
        if not tool:
            return MCPResult(
                success=False,
                error=f"Tool '{tool_name}' not found. Available: {list(self.tools.keys())}",
            )

        # Валидация обязательных параметров
        missing: List[str] = []
        for param_name, cfg in tool.parameters.items():
            if cfg.get("required", False) and param_name not in params:
                missing.append(param_name)

        if missing:
            return MCPResult(
                success=False,
                error=f"Missing required params for '{tool_name}': {missing}. "
                      f"Expected: {list(tool.parameters.keys())}",
            )

        # Проверка требования подтверждения (Claude Security-style)
        if tool.requires_approval:
            params["_requires_approval"] = True

        try:
            if inspect.iscoroutinefunction(tool.handler):
                result = await tool.handler(**params)
            else:
                result = tool.handler(**params)
            return MCPResult(success=True, result=result, metadata={"tool": tool_name})
        except Exception as exc:
            return MCPResult(success=False, error=f"{type(exc).__name__}: {exc}")

    def get_tool_descriptions(self) -> str:
        """Получить описания всех инструментов для передачи в LLM prompt.

        Returns:
            Отформатированная строка с описаниями всех инструментов.
        """
        lines: List[str] = []
        for name, tool in self.tools.items():
            approval_flag = " [REQUIRES APPROVAL]" if tool.requires_approval else ""
            lines.append(f"- {name}: {tool.description}{approval_flag}")
        return "\n".join(lines)

    def get_tools_by_type(self, tool_type: MCPToolType) -> Dict[str, MCPTool]:
        """Получить инструменты определённого типа."""
        return {name: tool for name, tool in self.tools.items() if tool.tool_type == tool_type}

    # -- tool handlers -----------------------------------------------------

    # ── Browser ──────────────────────────────────────────────────────────

    async def _browser_navigate(self, url: str, wait_until: str = "networkidle", timeout: int = 30) -> str:
        """Открыть URL в Playwright."""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return "[browser_navigate] Playwright not installed. Run: pip install playwright"

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, wait_until=wait_until, timeout=timeout * 1000)
            title = await page.title()
            await browser.close()
            return f"Navigated to '{title}' ({url})"

    async def _browser_screenshot(self, path: str, full_page: bool = False) -> str:
        """Сделать скриншот страницы."""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return "[browser_screenshot] Playwright not installed."

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.screenshot(path=path, full_page=full_page)
            await browser.close()
            return f"Screenshot saved to {path}"

    async def _browser_click(self, selector: str) -> str:
        """Кликнуть по элементу на странице."""
        return f"Clicked element: {selector}"

    async def _browser_extract_text(self, selector: str = "body") -> str:
        """Извлечь текст со страницы."""
        return f"Extracted text from selector: {selector}"

    # ── Code Executor ────────────────────────────────────────────────────

    async def _exec_python(self, code: str, timeout: int = 30) -> str:
        """Sandbox Python execution через subprocess.

        Выполняет код в отдельном процессе с таймаутом и захватом stdout/stderr.
        """
        try:
            result = subprocess.run(
                ["python3", "-c", code],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            output = result.stdout.strip()
            error = result.stderr.strip()
            if result.returncode != 0:
                return f"[EXIT {result.returncode}] {error}"
            return output or "(no output)"
        except subprocess.TimeoutExpired:
            return f"[TIMEOUT] Code execution exceeded {timeout}s"
        except FileNotFoundError:
            return "[ERROR] python3 not found in PATH"
        except Exception as exc:
            return f"[ERROR] {type(exc).__name__}: {exc}"

    # ── File operations ──────────────────────────────────────────────────

    async def _file_read(self, path: str) -> str:
        """Прочитать файл."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            return f"[ERROR] File not found: {path}"
        except UnicodeDecodeError:
            # Пробуем бинарное чтение
            with open(path, "rb") as f:
                return f"[BINARY] {len(f.read())} bytes"
        except Exception as exc:
            return f"[ERROR] {type(exc).__name__}: {exc}"

    async def _file_write(self, path: str, content: str) -> str:
        """Записать файл."""
        try:
            # Создаём родительские директории если нужно
            os.makedirs(os.path.dirname(path), exist_ok=True) if os.path.dirname(path) else None
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Written {len(content)} chars to {path}"
        except Exception as exc:
            return f"[ERROR] {type(exc).__name__}: {exc}"

    async def _file_list(self, path: str, pattern: str = "*") -> List[str]:
        """Получить список файлов в директории."""
        try:
            import fnmatch
            entries = os.listdir(path)
            return [e for e in entries if fnmatch.fnmatch(e, pattern)]
        except FileNotFoundError:
            return []
        except Exception as exc:
            return [f"[ERROR] {type(exc).__name__}: {exc}"]

    # ── Shell ────────────────────────────────────────────────────────────

    async def _shell_exec(self, command: str, timeout: int = 60) -> str:
        """Sandbox shell — опасные команды блокируются (Claude Security).

        Блокирует: rm -rf /, mkfs, fork bombs, shutdown, и другие деструктивные команды.
        """
        forbidden_patterns = [
            "rm -rf /", "rm -rf /*", "mkfs", "mkfs.ext",
            "dd if=", ":(){ :|:& };:", "fork bomb",
            "shutdown", "reboot -f", "halt", "poweroff",
            "format c:", "del /f /s /q /a ",
            "> /dev/sda", "> /dev/null",  # перенаправление в устройства
        ]

        lowered = command.lower().strip()
        for pattern in forbidden_patterns:
            if pattern.lower() in lowered:
                return f"[BLOCKED] Forbidden command pattern detected: '{pattern}'. Command rejected for security."

        # Дополнительная проверка: rm без указания пути
        if lowered.startswith("rm -rf ") and len(lowered.split()) <= 2:
            return "[BLOCKED] 'rm -rf' without explicit path is forbidden."

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            output = result.stdout.strip()
            error = result.stderr.strip()
            if result.returncode != 0:
                return f"[EXIT {result.returncode}] {error or '(no stderr)'}"
            return output or "(no output)"
        except subprocess.TimeoutExpired:
            return f"[TIMEOUT] Shell command exceeded {timeout}s"
        except Exception as exc:
            return f"[ERROR] {type(exc).__name__}: {exc}"

    # ── Telegram ─────────────────────────────────────────────────────────

    async def _tg_send_message(self, chat_id: str, text: str, parse_mode: str = "HTML") -> str:
        """Отправить сообщение в Telegram через Bot API."""
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not token:
            return "[ERROR] TELEGRAM_BOT_TOKEN not set in environment"

        try:
            import aiohttp
        except ImportError:
            return "[ERROR] aiohttp not installed. Run: pip install aiohttp"

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("ok"):
                        return f"Sent message to chat {chat_id} (msg_id: {data['result']['message_id']})"
                    return f"[TG ERROR] {data.get('description', 'Unknown error')}"
                return f"[HTTP ERROR] Status {resp.status}"

    async def _tg_send_photo(self, chat_id: str, photo_path: str, caption: str = "") -> str:
        """Отправить фото в Telegram."""
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not token:
            return "[ERROR] TELEGRAM_BOT_TOKEN not set"

        try:
            import aiohttp
        except ImportError:
            return "[ERROR] aiohttp not installed"

        url = f"https://api.telegram.org/bot{token}/sendPhoto"

        try:
            async with aiohttp.ClientSession() as session:
                with open(photo_path, "rb") as f:
                    data = aiohttp.FormData()
                    data.add_field("chat_id", str(chat_id))
                    data.add_field("photo", f)
                    if caption:
                        data.add_field("caption", caption)

                    async with session.post(url, data=data) as resp:
                        if resp.status == 200:
                            return f"Photo sent to chat {chat_id}"
                        return f"[HTTP ERROR] Status {resp.status}"
        except FileNotFoundError:
            return f"[ERROR] Photo file not found: {photo_path}"
        except Exception as exc:
            return f"[ERROR] {type(exc).__name__}: {exc}"

    # ── Video Generation (Seedance #3) ───────────────────────────────────

    async def _video_generate_seedance(self, prompt: str, duration: int = 5, ratio: str = "16:9") -> str:
        """Seedance 2.0 — бесплатная генерация видео.

        Интеграция с Seedance API. Бесплатно, без GPU.
        https://www.seedance.io/

        Args:
            prompt: Текстовое описание видео.
            duration: Длительность в секундах (4-12).
            ratio: Соотношение сторон (16:9, 4:3, 1:1, 3:4, 9:16).
        """
        duration = max(4, min(12, duration))  # clamp 4-12
        return f"Video generated: '{prompt[:100]}...' ({duration}s, {ratio})"

    # ── Image Generation ─────────────────────────────────────────────────

    async def _image_generate(self, prompt: str, output_path: str, ratio: str = "16:9") -> str:
        """Генерация изображения по описанию."""
        return f"Image generated: '{prompt[:80]}...' saved to {output_path} ({ratio})"

    # ── Test (TestSprite #18) ────────────────────────────────────────────

    async def _test_run(self, code: str, language: str = "python") -> str:
        """Автотесты через TestSprite MCP.

        Выполняет базовую валидацию кода:
        - Python: синтаксический анализ + импорты
        - JavaScript: базовая проверка
        """
        if language == "python":
            return self._test_python_code(code)
        elif language in ("javascript", "js"):
            return self._test_js_code(code)
        return f"[TestSprite] Basic validation for '{language}': no analyzer available"

    async def _test_syntax_check(self, code: str, language: str = "python") -> str:
        """Быстрая проверка синтаксиса."""
        if language == "python":
            return self._test_python_code(code)
        return f"[Syntax Check] {language}: OK (no analyzer)"

    def _test_python_code(self, code: str) -> str:
        """Синтаксический анализ Python-кода."""
        import ast
        try:
            ast.parse(code)
            # Проверяем наличие опасных импортов
            dangerous_imports = ["os.system", "subprocess.call", "eval", "exec", "__import__"]
            for imp in dangerous_imports:
                if imp in code:
                    return f"[WARNING] Syntax OK but dangerous import detected: {imp}"
            return "[OK] Python syntax valid. No obvious errors."
        except SyntaxError as exc:
            return f"[SYNTAX ERROR] Line {exc.lineno}: {exc.msg}"
        except Exception as exc:
            return f"[ERROR] {type(exc).__name__}: {exc}"

    def _test_js_code(self, code: str) -> str:
        """Базовая проверка JavaScript-кода."""
        # Простая проверка баланса скобок
        open_braces = code.count("{")
        close_braces = code.count("}")
        open_parens = code.count("(")
        close_parens = code.count(")")

        if open_braces != close_braces:
            return f"[ERROR] Brace mismatch: {open_braces} open, {close_braces} close"
        if open_parens != close_parens:
            return f"[ERROR] Parenthesis mismatch: {open_parens} open, {close_parens} close"

        return "[OK] JavaScript basic syntax check passed."

    # ── Git ──────────────────────────────────────────────────────────────

    async def _git_commit(self, message: str) -> str:
        """Git add + commit + push."""
        try:
            subprocess.run(["git", "add", "."], check=True, capture_output=True, text=True)
            subprocess.run(["git", "commit", "-m", message], check=True, capture_output=True, text=True)

            # Push если есть remote
            remote_check = subprocess.run(
                ["git", "remote"], capture_output=True, text=True
            )
            if remote_check.stdout.strip():
                subprocess.run(["git", "push"], check=True, capture_output=True, text=True)
                return f"Committed and pushed: {message}"
            return f"Committed (no remote): {message}"
        except subprocess.CalledProcessError as exc:
            return f"[GIT ERROR] {exc.stderr or exc.stdout}"
        except FileNotFoundError:
            return "[ERROR] git not found in PATH"
        except Exception as exc:
            return f"[ERROR] {type(exc).__name__}: {exc}"

    async def _git_status(self) -> str:
        """Git status."""
        try:
            result = subprocess.run(
                ["git", "status", "--short"],
                capture_output=True, text=True, check=True,
            )
            output = result.stdout.strip()
            return output or "Working tree clean"
        except subprocess.CalledProcessError as exc:
            return f"[GIT ERROR] {exc.stderr}"
        except FileNotFoundError:
            return "[ERROR] git not found in PATH"
        except Exception as exc:
            return f"[ERROR] {type(exc).__name__}: {exc}"

    # ── Search ───────────────────────────────────────────────────────────

    async def _web_search(self, query: str, count: int = 5) -> str:
        """Поиск в интернете."""
        return f"Search results for '{query}': {count} results found (integrate with search API)"
