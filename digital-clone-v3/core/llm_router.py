"""
LLM Router v3
Маршрутизация между LLM с автоматическим fallback.

Цепочка приоритетов:
    Kimi → DeepSeek → Groq → GLM → Local (Ollama/Gemma 4)

Интегрированные находки:
- #8 (GLM 5.1): бесплатный backup-провайдер
- #20 (Gemma 4 + Ollama): бесплатный локальный агент
- #4 (Abacus AI multi-LLM): параллельная маршрутизация
- #5 (Claude баны): fallback критически важен — Claude забанил 1.5M аккаунтов
"""

from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


class LLMProvider(Enum):
    """Поддерживаемые провайдеры LLM."""

    KIMI = "kimi"           # Primary — OpenAI-compatible, 128K контекст
    DEEPSEEK = "deepseek"   # Secondary — дёшево, хорошее качество
    GROQ = "groq"           # Tertiary — очень быстрый, LLaMA 3
    OLLAMA = "ollama"       # Local fallback — бесплатно, Gemma 4
    GLM = "glm"             # Backup — бесплатно (GLM 5.1)


@dataclass
class LLMConfig:
    """Конфигурация одного провайдера LLM."""

    provider: LLMProvider
    api_key: str
    base_url: str
    model: str
    max_tokens: int = 2000
    temperature: float = 0.7
    timeout: int = 30
    priority: int = 1           # 1 = highest
    cost_per_1k_input: float = 0.0   # $/1K input tokens
    cost_per_1k_output: float = 0.0  # $/1K output tokens


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------


class LLMRouter:
    """Маршрутизатор LLM с автоматическим fallback.

    Логика работы:
        1. Пробуем Primary (Kimi)
        2. Если ошибка / таймаут → Secondary (DeepSeek)
        3. Если квота исчерпана → Tertiary (Groq)
        4. Если всё offline → Local (Ollama / Gemma 4)
        5. Backup (GLM) — если всё остальное недоступно

    Из видео #5: Claude забанил 1.5M аккаунтов — fallback критически важен.
    Из видео #20: Gemma 4 + Ollama — бесплатный локальный агент без GPU.

    Args:
        provider_chain: Порядок fallback-цепочки (можно переопределить).

    Attributes:
        configs: Словарь конфигураций по провайдеру.
        stats: Статистика запросов (requests, errors, latency).
    """

    DEFAULT_CHAIN: List[LLMProvider] = [
        LLMProvider.KIMI,
        LLMProvider.DEEPSEEK,
        LLMProvider.GROQ,
        LLMProvider.GLM,
        LLMProvider.OLLAMA,
    ]

    def __init__(self, provider_chain: Optional[List[LLMProvider]] = None) -> None:
        self.provider_chain: List[LLMProvider] = provider_chain or list(self.DEFAULT_CHAIN)
        self.configs: Dict[LLMProvider, LLMConfig] = {}
        self.stats: Dict[LLMProvider, Dict[str, Any]] = {
            p: {"requests": 0, "errors": 0, "total_latency": 0.0}
            for p in LLMProvider
        }
        self._load_configs()

    # -- config loading ----------------------------------------------------

    def _load_configs(self) -> None:
        """Загрузка конфигураций из переменных окружения."""

        # Kimi CLI (Primary) — подписка Kimi Code через командную строку
        # Работает напрямую через kimi.exe, не через HTTP API (который даёт 403)
        self._kimi_cli = None
        try:
            from core.kimi_cli_adapter import KimiCLIAdapter
            self._kimi_cli = KimiCLIAdapter()
            self.configs[LLMProvider.KIMI] = LLMConfig(
                provider=LLMProvider.KIMI,
                api_key="kimi-cli",
                base_url="kimi-cli",
                model="kimi-for-coding",
                priority=1,
            )
            print("      Kimi CLI adapter initialized")
        except Exception as e:
            print(f"      Kimi CLI not available: {e}")
            # Fallback: HTTP API через Moonshot / Kimi (если CLI недоступен)
            kimi_key = os.getenv("KIMI_API_KEY")
            if kimi_key:
                self.configs[LLMProvider.KIMI] = LLMConfig(
                    provider=LLMProvider.KIMI,
                    api_key=kimi_key,
                    base_url=os.getenv("KIMI_BASE_URL", "https://api.kimi.com/coding/v1"),
                    model=os.getenv("KIMI_MODEL", "kimi-for-coding"),
                    priority=1,
                    cost_per_1k_input=0.012,
                    cost_per_1k_output=0.012,
                )

        # DeepSeek (Secondary) — дёшево и качественно
        ds_key = os.getenv("DEEPSEEK_API_KEY")
        if ds_key:
            self.configs[LLMProvider.DEEPSEEK] = LLMConfig(
                provider=LLMProvider.DEEPSEEK,
                api_key=ds_key,
                base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
                model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
                priority=2,
                cost_per_1k_input=0.00027,
                cost_per_1k_output=0.0011,
            )

        # Groq (Tertiary) — сверхбыстрый inference
        groq_key = os.getenv("GROQ_API_KEY")
        if groq_key:
            self.configs[LLMProvider.GROQ] = LLMConfig(
                provider=LLMProvider.GROQ,
                api_key=groq_key,
                base_url=os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1"),
                model=os.getenv("GROQ_MODEL", "llama3-70b-8192"),
                priority=3,
                cost_per_1k_input=0.00059,
                cost_per_1k_output=0.00079,
            )

        # Ollama (Local) — Gemma 4, бесплатно, без GPU (#20)
        ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.configs[LLMProvider.OLLAMA] = LLMConfig(
            provider=LLMProvider.OLLAMA,
            api_key="ollama",  # Ollama не требует ключ
            base_url=f"{ollama_host}/v1",
            model=os.getenv("OLLAMA_MODEL", "gemma4:9b"),
            priority=4,
            cost_per_1k_input=0.0,
            cost_per_1k_output=0.0,
        )

        # GLM (Backup) — бесплатный, GLM 5.1 (#8)
        glm_key = os.getenv("GLM_API_KEY")
        if glm_key:
            self.configs[LLMProvider.GLM] = LLMConfig(
                provider=LLMProvider.GLM,
                api_key=glm_key,
                base_url=os.getenv("GLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4"),
                model=os.getenv("GLM_MODEL", "glm-5.1"),
                priority=5,
                cost_per_1k_input=0.0,
                cost_per_1k_output=0.0,
            )

    def add_config(self, config: LLMConfig) -> None:
        """Добавить конфигурацию провайдера вручную."""
        self.configs[config.provider] = config

    # -- public API --------------------------------------------------------

    async def complete(
        self,
        prompt: str,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        system: Optional[str] = None,
    ) -> str:
        """Отправить запрос с автоматическим fallback по цепочке провайдеров.

        Перебирает провайдеров в порядке приоритета до первого успешного
        ответа. Обновляет статистику latency и ошибок.

        Args:
            prompt: Текст пользовательского запроса.
            max_tokens: Максимальное количество токенов в ответе.
            temperature: Креативность (0.0 = детерминированный, 1.0 = креативный).
            system: Опциональный системный промпт.

        Returns:
            Текст ответа от первого успешного LLM.

        Raises:
            Exception: Если все провайдеры в цепочке недоступны.
        """
        for provider in self.provider_chain:
            if provider not in self.configs:
                continue

            # Special case: Kimi CLI adapter (subprocess, не HTTP)
            if provider == LLMProvider.KIMI and getattr(self, '_kimi_cli', None):
                try:
                    start = time.monotonic()
                    result = await self._kimi_cli.complete(
                        prompt, max_tokens=max_tokens,
                        temperature=temperature, system=system
                    )
                    if result and not result.startswith("[Kimi CLI Error"):
                        latency = time.monotonic() - start
                        self.stats[provider]["requests"] += 1
                        self.stats[provider]["total_latency"] += latency
                        return result
                    # Если CLI вернул ошибку — логируем и падаем в HTTP fallback
                    print(f"[LLM Router] kimi CLI returned: {result}")
                except Exception as exc:
                    print(f"[LLM Router] kimi CLI failed: {exc}. Trying HTTP fallback...")

            config = self.configs[provider]

            try:
                start = time.monotonic()
                result = await self._call_provider(config, prompt, max_tokens, temperature, system)
                latency = time.monotonic() - start

                # Обновляем статистику
                self.stats[provider]["requests"] += 1
                self.stats[provider]["total_latency"] += latency

                return result

            except Exception as exc:
                self.stats[provider]["errors"] += 1
                print(f"[LLM Router] {provider.value} failed: {exc}. Trying next...")
                continue

        raise Exception(
            "All LLM providers failed. Check your API keys and internet connection. "
            f"Stats: {self.get_stats()}"
        )

    async def complete_parallel(
        self,
        prompt: str,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        system: Optional[str] = None,
        providers: Optional[List[LLMProvider]] = None,
    ) -> str:
        """Параллельный запрос к нескольким провайдерам — возвращает первый ответ.

        Паттерн из #4 (Abacus AI multi-LLM): запускаем запросы параллельно
        и берём первый успешный результат.

        Args:
            providers: Список провайдеров для параллельного запроса.
                       По умолчанию — первые 3 из цепочки.

        Returns:
            Текст ответа от первого ответившего провайдера.
        """
        targets = providers or self.provider_chain[:3]
        targets = [p for p in targets if p in self.configs]

        if not targets:
            return await self.complete(prompt, max_tokens, temperature, system)

        async def _try_one(provider: LLMProvider) -> Optional[str]:
            config = self.configs[provider]
            try:
                return await self._call_provider(config, prompt, max_tokens, temperature, system)
            except Exception:
                return None

        tasks = [asyncio.create_task(_try_one(p)) for p in targets]

        for coro in asyncio.as_completed(tasks):
            result = await coro
            if result is not None:
                # Отменяем оставшиеся задачи
                for t in tasks:
                    if not t.done():
                        t.cancel()
                return result

        raise Exception("All parallel LLM requests failed.")

    # -- provider-specific callers -----------------------------------------

    async def _call_provider(
        self,
        config: LLMConfig,
        prompt: str,
        max_tokens: int,
        temperature: float,
        system: Optional[str],
    ) -> str:
        """Диспатчер вызова конкретного провайдера."""
        if config.provider == LLMProvider.OLLAMA:
            return await self._call_ollama(config, prompt, max_tokens, temperature, system)
        return await self._call_openai_compatible(config, prompt, max_tokens, temperature, system)

    async def _call_openai_compatible(
        self,
        config: LLMConfig,
        prompt: str,
        max_tokens: int,
        temperature: float,
        system: Optional[str],
    ) -> str:
        """OpenAI-compatible API: Kimi, DeepSeek, Groq, GLM.

        Пробует использовать openai SDK, fallback на aiohttp.
        """
        try:
            from openai import AsyncOpenAI
            return await self._call_with_openai_sdk(config, prompt, max_tokens, temperature, system)
        except ImportError:
            return await self._call_with_aiohttp(config, prompt, max_tokens, temperature, system)

    async def _call_with_openai_sdk(
        self,
        config: LLMConfig,
        prompt: str,
        max_tokens: int,
        temperature: float,
        system: Optional[str],
    ) -> str:
        """Вызов через AsyncOpenAI SDK."""
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=config.timeout,
        )

        messages: List[Dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = await client.chat.completions.create(
            model=config.model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        content = response.choices[0].message.content
        return content if content else ""

    async def _call_with_aiohttp(
        self,
        config: LLMConfig,
        prompt: str,
        max_tokens: int,
        temperature: float,
        system: Optional[str],
    ) -> str:
        """Вызов через aiohttp (без openai SDK)."""
        import aiohttp

        url = f"{config.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        }

        messages: List[Dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": config.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=config.timeout)
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise Exception(f"HTTP {resp.status}: {text}")

                data = await resp.json()
                return data["choices"][0]["message"]["content"] or ""

    async def _call_ollama(
        self,
        config: LLMConfig,
        prompt: str,
        max_tokens: int,
        temperature: float,
        system: Optional[str],
    ) -> str:
        """Локальный Ollama (Gemma 4) — из видео #20.

        Ollama имеет OpenAI-compatible endpoint, но делаем
        прямой вызов для надёжности.
        """
        import aiohttp

        url = f"{config.base_url}/chat/completions"

        messages: List[Dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": config.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url, json=payload, timeout=aiohttp.ClientTimeout(total=config.timeout)
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise Exception(f"Ollama error {resp.status}: {text}")

                data = await resp.json()
                return data["choices"][0]["message"]["content"] or ""

    # -- diagnostics -------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Статистика использования всех провайдеров.

        Returns:
            Словарь с requests, errors, error_rate, avg_latency для каждого провайдера
            и общей оценкой стоимости.
        """
        provider_stats = {}
        for provider, s in self.stats.items():
            requests = s["requests"]
            errors = s["errors"]
            total_latency = s["total_latency"]
            avg_latency = (total_latency / requests) if requests > 0 else 0.0

            provider_stats[provider.value] = {
                "requests": requests,
                "errors": errors,
                "error_rate": round(errors / max(requests, 1), 3),
                "avg_latency_sec": round(avg_latency, 2),
            }

        total_cost = sum(
            (c.cost_per_1k_input + c.cost_per_1k_output)
            * self.stats[p]["requests"]
            for p, c in self.configs.items()
        )

        return {
            "providers": provider_stats,
            "estimated_cost_usd": round(total_cost, 4),
            "available_providers": [p.value for p in self.configs.keys()],
            "chain_order": [p.value for p in self.provider_chain],
        }

    async def health_check(self) -> Dict[str, bool]:
        """Проверка доступности всех сконфигурированных провайдеров.

        Returns:
            Словарь {provider_name: is_available}.
        """
        import aiohttp

        results: Dict[str, bool] = {}

        for provider, config in self.configs.items():
            try:
                if provider == LLMProvider.KIMI and getattr(self, '_kimi_cli', None):
                    # Kimi CLI — проверяем через is_available()
                    results[provider.value] = self._kimi_cli.is_available()
                elif provider == LLMProvider.OLLAMA:
                    async with aiohttp.ClientSession() as s:
                        async with s.get(
                            f"{config.base_url}/models",
                            timeout=aiohttp.ClientTimeout(total=5),
                        ) as r:
                            results[provider.value] = r.status == 200
                else:
                    await self._call_provider(config, "Hi", 5, 0.0, None)
                    results[provider.value] = True
            except Exception:
                results[provider.value] = False

        return results
