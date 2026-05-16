"""
Kimi CLI Adapter — вызывает Kimi Code через командную строку.
Работает с подпиской Kimi Code (через kimi CLI).
Не использует HTTP API (который даёт 403).
"""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional


class KimiCLIAdapter:
    """
    Адаптер для вызова Kimi Code через CLI.
    Подписка Kimi Code работает напрямую через `kimi` команду.
    """

    def __init__(self):
        self.cli_path = self._find_kimi_cli()
        # Neutral work-dir to avoid kimi scanning the project on every call
        self._work_dir = str(Path(os.environ.get("TEMP", "/tmp")))

    def _find_kimi_cli(self) -> str:
        """Найти путь к kimi CLI."""
        # Try PATH first
        path = shutil.which("kimi")
        if path:
            return path

        # VS Code extension fallback (Windows)
        vscode_kimi = Path.home() / (
            "AppData/Roaming/Code/User/globalStorage/"
            "moonshot-ai.kimi-code/bin/kimi/kimi.exe"
        )
        if vscode_kimi.exists():
            return str(vscode_kimi)

        # Additional Windows fallbacks
        for candidate in [
            r"C:\Program Files\Kimi CLI\bin\kimi.exe",
            os.path.expanduser(r"~\AppData\Local\Kimi CLI\bin\kimi.exe"),
            os.path.expanduser(
                r"~\AppData\Roaming\Code\User\globalStorage"
                r"\moonshot-ai.kimi-code\bin\kimi\kimi.exe"
            ),
        ]:
            if shutil.which(candidate):
                return shutil.which(candidate)
            if Path(candidate).exists():
                return candidate

        raise RuntimeError(
            "kimi CLI не найден. Установи VS Code extension 'Kimi Code' "
            "или standalone CLI: https://code.kimi.com/"
        )

    async def complete(
        self,
        prompt: str,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        system: Optional[str] = None,
    ) -> str:
        """
        Отправить промпт в Kimi CLI и получить ответ.

        Args:
            prompt: Текст промпта
            max_tokens: максимум токенов (не применяется в CLI, для совместимости)
            temperature: температура (не применяется в CLI, для совместимости)
            system: системный промпт (добавляется в начало)

        Returns:
            Ответ от Kimi
        """
        full_prompt = prompt
        if system:
            full_prompt = f"{system}\n\n{prompt}"

        env = {
            **os.environ,
            "PYTHONIOENCODING": "utf-8",
            "PYTHONUTF8": "1",
        }

        try:
            result = subprocess.run(
                [
                    self.cli_path,
                    "--quiet",
                    "-p",
                    full_prompt,
                    "--work-dir",
                    self._work_dir,
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
                stdin=subprocess.DEVNULL,
                timeout=120,
            )

            if result.returncode != 0:
                error_msg = result.stderr[:500] if result.stderr else "Unknown error"
                return f"[Kimi CLI Error: {error_msg}]"

            return result.stdout.strip()

        except subprocess.TimeoutExpired:
            return "[Kimi CLI Error: timeout after 120s]"
        except Exception as e:
            return f"[Kimi CLI Error: {type(e).__name__}: {e}]"

    def is_available(self) -> bool:
        """Проверить что Kimi CLI доступен."""
        if not self.cli_path or not Path(self.cli_path).exists():
            return False
        # Quick smoke test
        try:
            env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
            result = subprocess.run(
                [self.cli_path, "info"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
                stdin=subprocess.DEVNULL,
                timeout=10,
            )
            return result.returncode == 0 and "kimi-cli version" in result.stdout
        except Exception:
            return False
