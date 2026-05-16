"""
Dev Worker v3
Разработка: vibe coding, code review, автотесты, security scanning.
Из видео #1: Claude Security — сканирование кода на уязвимости
Из видео #18: TestSprite — MCP автотесты
"""

import asyncio
import subprocess
from typing import Dict, List, Any


class DevWorker:
    """
    Воркер разработки. Задачи:
    - Написать/исправить код (vibe coding)
    - Code review (Claude Security-style — видео #1)
    - Автотесты (TestSprite MCP — видео #18)
    - Git операции
    - Деплой

    Security (из видео #1):
    - Сканирование кода перед выполнением
    - Проверка на SQL injection, XSS, etc.
    - Валидация зависимостей
    """

    def __init__(self, llm_router=None, mcp_layer=None):
        self.llm = llm_router
        self.mcp = mcp_layer

    async def execute(self, task, thought_chain):
        """Главный вход"""
        action = task.description.lower()

        if "код" in action or "code" in action or "напиши" in action:
            return await self.write_code(task.context)
        elif "фикс" in action or "баг" in action or "bug" in action:
            return await self.fix_bug(task.context)
        elif "ревью" in action or "review" in action:
            return await self.code_review(task.context)
        elif "тест" in action or "test" in action:
            return await self.run_tests(task.context)
        elif "гит" in action or "git" in action:
            return await self.git_ops(task.context)
        else:
            return await self.write_code(task.context)

    async def write_code(self, context: Dict) -> Dict:
        """Vibe coding — написать код по описанию"""
        description = context.get("description", "")
        language = context.get("language", "python")

        # Генерация кода через LLM
        prompt = f"""Напиши {language} код:
        {description}

        Требования:
        - Чистый, production-ready код
        - Type hints
        - Docstrings
        - Обработка ошибок
        - Безопасность (не используй eval, не делай os.system с пользовательским вводом)
        """

        code = await self.llm.complete(prompt, max_tokens=2000)

        # Security scan (Claude Security-style — видео #1)
        scan_result = await self._security_scan(code)

        # Автотесты (TestSprite — видео #18)
        test_result = await self.mcp.execute("test_run", {
            "code": code,
            "language": language
        })

        return {
            "type": "code",
            "language": language,
            "code": code,
            "security_scan": scan_result,
            "tests": test_result,
            "safe_to_execute": scan_result.get("safe", False)
        }

    async def fix_bug(self, context: Dict) -> Dict:
        """Исправить баг по описанию"""
        code = context.get("code", "")
        error = context.get("error", "")

        prompt = f"""Исправь баг в коде:

        Ошибка: {error}

        Код:
        ```python
        {code}
        ```

        Дай исправленный код и объяснение что было не так.
        """

        fix = await self.llm.complete(prompt, max_tokens=2000)

        return {
            "type": "bugfix",
            "original_error": error,
            "fix": fix
        }

    async def code_review(self, context: Dict) -> Dict:
        """Code review (Claude Security-style)"""
        code = context.get("code", "")

        prompt = f"""Проведи code review:
        ```python
        {code}
        ```

        Проверь:
        1. Безопасность (SQL injection, XSS, path traversal)
        2. Качество кода (читаемость, структура)
        3. Производительность
        4. Обработка ошибок
        5. Типизация

        Дай оценку (1-10) и рекомендации.
        """

        review = await self.llm.complete(prompt, max_tokens=1500)

        return {
            "type": "code_review",
            "review": review
        }

    async def run_tests(self, context: Dict) -> Dict:
        """Запуск автотестов (TestSprite MCP)"""
        code = context.get("code", "")

        result = await self.mcp.execute("test_run", {
            "code": code,
            "language": "python"
        })

        return result

    async def git_ops(self, context: Dict) -> Dict:
        """Git операции"""
        action = context.get("action", "status")  # commit/push/pull/status
        message = context.get("message", "")

        if action == "commit":
            return await self.mcp.execute("git_commit", {"message": message})

        return {"status": "unknown action"}

    async def _security_scan(self, code: str) -> Dict:
        """Сканирование кода на уязвимости (Claude Security-style)"""
        dangerous_patterns = [
            ("eval(", "CRITICAL: eval() can execute arbitrary code"),
            ("exec(", "CRITICAL: exec() can execute arbitrary code"),
            ("os.system", "HIGH: os.system() can run shell commands"),
            ("subprocess.call", "MEDIUM: subprocess with shell=True is dangerous"),
            ("__import__", "MEDIUM: dynamic imports can be exploited"),
            ("pickle.loads", "HIGH: pickle can execute arbitrary code"),
            ("yaml.load", "MEDIUM: use yaml.safe_load instead"),
        ]

        issues = []
        for pattern, severity in dangerous_patterns:
            if pattern in code:
                issues.append({"pattern": pattern, "severity": severity})

        return {
            "safe": len(issues) == 0,
            "issues": issues,
            "scan_time": "auto"
        }
