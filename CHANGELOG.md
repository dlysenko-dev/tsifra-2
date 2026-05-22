# Changelog

> История изменений проекта Digital Clone v3.
> Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.0.0/).

---

## [Unreleased]

### Планируется
- **Hermes Agent Integration** — REST/gRPC API для всех воркеров, WebSocket-уведомления, масштабирование
- **IntelWorker v2** — детальный анализ конкурентов: RSS, Pinterest, YouTube, Instagram, Twitter/X, Reddit
- **Telegram Bot v2** — голосовые сообщения через faster-whisper, inline keyboards, админ-панель
- **Content Improvement Loop** — авто-сравнение контента с конкурентами, анализ метрик
- **skills/ модуль** — создание `skills/engine.py` и `skills/business_models.py` (сейчас импортируются, но отсутствуют)
- **tests/ директория** — полноценный test suite на pytest
- **prompts/ директория** — вынесение системных промптов в YAML
- **memory/ директория** — векторная память и сессионное хранилище
- **core/intent_classifier.py** — выделение классификации intent в отдельный модуль
- **core/memory.py** — векторная память (Obsidian Vault integration)
- **core/config.py** — централизованная конфигурация через pydantic-settings
- **Docker CMD fix** — изменение entry point с `core.jarvis_v3` на `main.py`
- **Video Pipeline v10** — улучшение качества шортсов, новые transitions
- **Blender VSE Integration** — стабилизация `core/blender_vse/` и `core/tsifra2-vse/`
- **Self-Learning Loop** — автоматический анализ эффективности публикаций
- **Безопасная свобода** — правила и ограничения перед полной автономией

### В работе
- Рефакторинг `main.py` — удаление broken imports (skills/)
- Актуализация документации (AGENTS.md, ARCHITECTURE.md, README.md, CONTEXT.md)
- Интеграция `pro_editor_v9.py` в VideoWorker

---

## [0.1.0] — 2025-05

### Добавлено
- **JarvisOrchestrator** (`core/jarvis_v3.py`) — OpenManus-style planner с ReAct loop
  - Intent classification: CHAT, CONTENT, VIDEO, CODE, INTEL, SELL, SYSTEM, BUSINESS
  - Task status FSM: PENDING → PLANNING → EXECUTING → VALIDATING → DONE/ERROR
  - 3 уровня автономности: MANUAL, ASSISTED, AUTONOMOUS
- **5 Workers** (`agents/`):
  - `ContentWorker` — посты, сценарии, PDF, клиппинг
  - `VideoWorker` — Seedance, Web-to-Video, шортсы, motion graphics
  - `DevWorker` — vibe coding, security scan, автотесты
  - `IntelWorker` — конкуренты, тренды, mind maps
  - `SellWorker` — клиенты, КП, монетизация
- **LLM Router** (`core/llm_router.py`) — fallback-цепочка:
  - Kimi (primary) → DeepSeek → Groq → Ollama → GLM
  - Health check и automatic retry
- **MCP Layer** (`core/mcp_layer.py`) — 15+ инструментов:
  - Browser (Playwright): navigate, screenshot, click, extract_text
  - Code Executor: Python REPL
  - File Tools: read, write, list
  - Shell Exec: sandbox с блокировкой
  - Search: web search
  - Telegram API: send_message, send_photo
  - Video Gen: Seedance 2.0
  - Image Gen: генерация изображений
  - Auto Tests: test_run, syntax_check
  - Git Tools: commit, status
- **Real Tools** (`core/real_tools.py`) — tg_publish_post, shorts_generate, content_publish_full, video_publish_full, tg_send_video, video_create_hybrid
- **Autonomous Loop** (`core/autonomous_loop.py`) — cron-like планировщик:
  - Загрузка расписания из `config/autonomous_schedule.json`
  - Pipeline: generate → quality_check → publish → log
  - 7 задач по умолчанию (утренний/вечерний пост, шортсы, тренды, отчёт, метрики)
- **Telegram Bot** (`core/telegram_bot.py`) — python-telegram-bot >= 20.0:
  - Текстовые сообщения → Jarvis
  - Команды: /start, /help, /status, /tasks, /autonomy
  - Уведомления от AutonomousLoop
- **Quality Control** (`core/quality_control.py`) — LLM-based проверка:
  - Пороги в `config/quality_thresholds.json`
  - Проверка: длина, hook, CTA, hashtags, readability, engagement, toxicity
- **Video Pipeline** — многоуровневая система генерации видео:
  - `pro_editor_v9.py` — motion graphics, kinetic text, transitions
  - `core/video_creator.py` — Motion Canvas + Blender + ffmpeg
  - `core/video_assembler.py` — assembly и синхронизация аудио
  - `core/blender_ai_workflow.py` — 3D-сцены через Blender
  - `tools/shorts_pipeline.py` — полный pipeline шортсов
- **Assets System** (`core/asset_*.py`) — cache, downloader, finder
- **Sound Library** (`core/sound_library.py`) — SFX, ambient, impact, riser
- **TOV Profile** (`core/tov_profile.py`) — Tone of Voice профили
- **Self-Learning Video** (`core/self_learning_video.py`) — анализ эталонных роликов
- **Kimi CLI Adapter** (`core/kimi_cli_adapter.py`) — интеграция с Kimi CLI
- **Docker Support** — Dockerfile + docker-compose.yml с Ollama
- **Makefile** — install, run, test, clean, docker
- **10+ Business Models** — AI-агентство, контент-фабрика, SaaS, info-продукты и др.

### Технологии
- Python 3.11
- asyncio + dataclasses
- openai >= 1.0.0 (OpenAI-compatible APIs)
- aiohttp >= 3.9.0
- python-telegram-bot >= 20.0
- moviepy >= 1.0.3 + ffmpeg
- playwright >= 1.40.0
- gTTS >= 2.4.0
- pydantic >= 2.0
- pytest >= 7.4.0
- bandit >= 1.7.0

### Известные проблемы
- `skills/` директория импортируется в `main.py`, но физически отсутствует
- `tests/`, `prompts/`, `memory/` директории не созданы
- Docker CMD указывает на `core.jarvis_v3` вместо `main.py`
- `Makefile` ссылается на `tests/`, которой нет

---

## Формат версий

Проект использует [Semantic Versioning](https://semver.org/lang/ru/):
- `MAJOR` — несовместимые изменения API
- `MINOR` — новая функциональность, обратно совместимая
- `PATCH` — исправления багов
