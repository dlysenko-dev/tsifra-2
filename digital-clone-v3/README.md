# Digital Clone v3 — Jarvis Agent

> **Multi-agent AI system** с архитектурой OpenManus-style, мульти-LLM роутингом, MCP-протоколом и автоматизацией контента. Работает 24/7: создает посты, видео, код и аналитику.

---

## Что это

**Digital Clone v3** — это ваш цифровой клон на базе AI, который:

- **Создает контент**: посты для Telegram, блоги, нейро-сценарии
- **Генерирует видео**: шортсы, reels, TikTok из текста
- **Пишет код**: парсеры, API, автоматизация, боты
- **Анализирует рынок**: конкуренты, ниши, тренды, pricing
- **Продает**: воронки, email-цепочки, landing pages

### Архитектура

```
┌─────────────────────────────────────────────────────┐
│                   JARVIS ORCHESTRATOR                │
│         (Intent Detection + Task Routing)            │
├──────────┬──────────┬──────────┬──────────┬─────────┤
│ Content  │  Video   │   Dev    │  Intel   │  Sell   │
│ Worker   │  Worker  │  Worker  │  Worker  │ Worker  │
│          │          │          │          │         │
│ Posts    │ Shorts   │  Code    │ Research │Funnels  │
│ Scripts  │ Reels    │  APIs    │ Analysis │Emails   │
│ Blogs    │ TikTok   │  Bots    │ Trends   │Landing │
└──────────┴──────────┴──────────┴──────────┴─────────┘
           │
    ┌──────┴──────┐
    │ LLM ROUTER  │ ← Kimi → DeepSeek → Groq → Ollama
    │  (Fallback) │
    └──────┬──────┘
           │
    ┌──────┴──────┐
    │  MCP LAYER  │ ← 15+ инструментов
    │  (Tools)    │   browser, search, scraper,
    └─────────────┘   generate_image, text2speech...
```

### Multi-LLM Fallback Chain

Система автоматически переключается между провайдерами:

```
Запрос → Kimi API (primary)
            ↓ fail
        DeepSeek API
            ↓ fail
          Groq API
            ↓ fail
        Ollama (local)
            ↓ fail
         GLM (free)
```

---

## Quickstart

### Шаг 1: Клонировать репозиторий

```bash
git clone <repo-url>
cd digital-clone-v3
```

### Шаг 2: Установить зависимости

```bash
# Вариант A: Через Makefile
make install

# Вариант B: Вручную
pip install -r requirements.txt
playwright install chromium
```

**Требования:**
- Python 3.11+
- FFmpeg (для видео)
- Chromium (для web-скрапинга)

### Шаг 3: Настроить API ключи

```bash
cp .env.example .env
```

Отредактируй `.env` файл:

```bash
# Обязательно: хотя бы один LLM ключ
KIMI_API_KEY=sk-your-key-here

# Опционально: для fallback
DEEPSEEK_API_KEY=sk-your-key-here
GROQ_API_KEY=gsk-your-key-here

# Для Telegram бота
TELEGRAM_BOT_TOKEN=your-bot-token

# Опционально: бесплатный GLM бэкап
GLM_API_KEY=your-glm-key
```

**Где получить ключи:**

| Провайдер | URL | Цена | Скорость |
|-----------|-----|------|----------|
| Kimi | [platform.moonshot.cn](https://platform.moonshot.cn) | $ | Fast |
| DeepSeek | [platform.deepseek.com](https://platform.deepseek.com) | $ | Fast |
| Groq | [console.groq.com](https://console.groq.com) | Free tier | Ultra-fast |
| GLM | [open.bigmodel.cn](https://open.bigmodel.cn) | Free tier | Medium |
| Ollama | [ollama.com](https://ollama.com) | Free (local) | Depends on GPU |

### Шаг 4: Запустить

```bash
# Точка входа — main.py
python main.py
```

При успешном запуске вы увидите:

```
============================================================
  Digital Clone v3 — Jarvis Agent
  Architecture: OpenManus-style + Multi-LLM + MCP
============================================================

[1/7] Initializing LLM Router...
[2/7] Initializing MCP Layer...
[3/7] Initializing Skills Engine...
[4/7] Registering Workers...
[5/7] Loading Business Models...
[6/7] Starting Autonomous Loop...
[7/7] Starting Telegram Bot...

============================================================
  System Ready!
============================================================
```

> **Примечание**: `skills/`, `memory/`, `tests/`, `prompts/` — модули созданы и готовы к использованию.

### Шаг 5: Взаимодействие

- **Telegram**: напишите боту любое сообщение — Jarvis ответит.
- **CLI**: после запуска `main.py` система автоматически выполняет демо-задачи.
- **Autonomous**: планировщик начинает выполнять задачи из `config/autonomous_schedule.json`.

---

## Структура проекта

```
digital-clone-v3/
│
├── main.py                    # Точка входа
├── requirements.txt           # Python-зависимости
├── Dockerfile                 # Docker-образ
├── docker-compose.yml         # Docker Compose (с Ollama)
├── Makefile                   # Команды разработки
├── .env.example               # Шаблон конфигурации
│
├── core/                      # Ядро системы
│   ├── jarvis_v3.py           # Оркестратор (OpenManus-style)
│   ├── llm_router.py          # Multi-LLM роутер с fallback
│   ├── mcp_layer.py           # MCP протокол (15+ tools)
│   ├── autonomous_loop.py     # Автономный event loop
│   ├── telegram_bot.py        # Telegram Bot
│   ├── quality_control.py     # Проверка качества контента
│   ├── video_creator.py       # Гибридный видео-генератор
│   ├── video_assembler.py     # Сборка видео из сегментов
│   ├── blender_ai_workflow.py # Blender integration
│   ├── real_tools.py          # Real tools (tg_publish, shorts_generate)
│   ├── asset_cache.py         # Кэш ассетов
│   ├── asset_downloader.py    # Загрузка ассетов
│   ├── asset_finder.py        # Поиск ассетов
│   ├── bounce_animator.py     # Bounce-анимации
│   ├── kinetic_text.py        # Kinetic typography
│   ├── sound_library.py       # Библиотека звуков
│   ├── tov_profile.py         # Профиль Tone of Voice
│   ├── self_learning_video.py # Self-learning для видео
│   └── kimi_cli_adapter.py    # Адаптер для Kimi CLI
│
├── agents/                    # AI-агенты (воркеры)
│   ├── content_worker.py      # Контент (посты, сценарии)
│   ├── video_worker.py        # Видео (шортсы, reels)
│   ├── dev_worker.py          # Разработка (код, API)
│   ├── intel_worker.py        # Аналитика (рынок, конкуренты)
│   └── sell_worker.py         # Продажи (воронки, email)
│
├── tools/                     # Утилиты публикации
│   ├── shorts_pipeline.py     # Pipeline шортсов
│   └── tg_publish.py          # Публикация в Telegram
│
├── config/                    # Конфигурация
│   ├── autonomous_schedule.json  # Cron-задачи
│   └── quality_thresholds.json   # Пороги качества
│
├── skills/                    # Скиллы (модули умений)
│   ├── engine.py              # Движок скиллов
│   └── business_models.py     # Бизнес-модели
│
├── memory/                    # Память системы
│   └── vector_store.py        # Векторное хранилище
│
├── prompts/                   # Промпты
│   └── system_prompts.yaml    # Системные промпты
│
├── tests/                     # Тесты
│   ├── test_orchestrator.py
│   ├── test_llm_router.py
│   ├── test_mcp_layer.py
│   └── ...
│
├── templates/                 # Шаблоны
│   └── horror_snowman.py      # Blender template
│
├── learning/                  # Данные self-learning
│   ├── downloaded_videos/     # Скачанные видео
│   ├── etalons/               # Эталонные ролики
│   ├── masters/               # Анализ мастеров
│   ├── references/            # Референсы
│   └── video_knowledge.json   # База знаний видео
│
├── assets/                    # Статические ассеты
│   ├── fonts/                 # Шрифты (Montserrat, Impact)
│   ├── music_epic.mp3         # Музыка
│   ├── sfx/                   # Sound effects
│   ├── videos/                # B-rolls, cards
│   └── overlays/              # Overlays (grain, scanlines)
│
├── output/                    # Выходные файлы (не коммитить)
├── temp/                      # Временные файлы (не коммитить)
│
├── pro_editor_v2.py … v9.py   # Версии pro video editor
├── create_viral_video.py      # Генерация вирусных видео
├── analyze_all.py             # Анализ контента
├── fetch_masters.py           # Парсинг мастеров
├── build_knowledge_manual.py  # Сборка knowledge base
│
└── test_*.py                  # Тестовые скрипты
```

---

## Примеры использования

### Пример 1: Создание поста для Telegram

```bash
$ python main.py

Task: Создай пост про AI автоматизацию для Telegram
→ Intent: CONTENT_CREATE
→ Status: completed
→ Preview: "5 инструментов AI-автоматизации для Telegram, которые сэкономят вам 20 часов в неделю..."
```

### Пример 2: Генерация видео-шортса

```bash
Task: Сделай шортс про MCP протокол
→ Intent: VIDEO_CREATE
→ Status: completed
→ Preview: Video saved to output/shorts/mcp_protocol_20250101.mp4
```

### Пример 3: Анализ конкурентов

```bash
Task: Проведи анализ конкурентов в нише AI агентов
→ Intent: INTEL_RESEARCH
→ Status: completed
→ Preview: {"competitors": [...], "market_size": "$12B", "trends": [...]}
```

### Пример 4: Написание кода

```bash
Task: Напиши код для парсера JSON на Python
→ Intent: DEV_CODE
→ Status: completed
→ Preview: import json\n\ndef parse_json(data):\n    try:\n        return json.loads(data)...
```

### Пример 5: Telegram бот

```bash
# Запуск бота (входит в main.py)
python main.py

# В Telegram:
# /start — начать
# /status — статус системы
# /tasks — список задач
# /autonomy — уровень автономности
```

---

## Бизнес-модели

Система включает 10+ готовых бизнес-моделей для монетизации:

| # | Модель | Описание | Потенциал дохода |
|---|--------|----------|-----------------|
| 1 | **AI-агентство** | Автоматизация бизнеса для клиентов | $3K-15K/мес |
| 2 | **Контент-фабрика** | Массовое создание контента | $1K-5K/мес |
| 3 | **SaaS-продукт** | Подписочный AI-сервис | $5K-50K/мес |
| 4 | **Info-продукты** | Курсы, гайды, чек-листы | $500-3K/мес |
| 5 | **Фриланс** | Проектная разработка | $2K-10K/мес |
| 6 | **Аффилиат** | Партнерские программы AI-инструментов | $200-2K/мес |
| 7 | **Консалтинг** | AI-консультации для бизнеса | $100-500/час |
| 8 | **API-доступ** | Продажа API к вашему клону | $500-5K/мес |
| 9 | **White-label** | Лицензирование системы | $2K-20K/мес |
| 10 | **Автоматические воронки** | Автоворонки продаж | $1K-10K/мес |

### Выбор модели

> **Примечание**: `skills/business_models.py` импортируется в `main.py`, но модуль `skills/` отсутствует. Функциональность business models требует создания этого модуля.

```python
from skills.business_models import recommend_model

# Получить рекомендацию на основе навыков
model = recommend_model(skills=["coding", "content"], budget="low")
print(f"Рекомендуемая модель: {model['name']}")
```

---

## Docker-развертывание

### Быстрый старт через Docker

```bash
# 1. Скопируй .env
mv .env.example .env
# Отредактируй API ключи

# 2. Запусти
docker-compose up --build

# 3. Система доступна
# Telegram Bot — через polling
# Ollama — http://localhost:11434
```

### Docker сервисы

| Сервис | Порт | Описание |
|--------|------|----------|
| digital-clone | — | Основной агент (Telegram polling) |
| ollama | 11434 | Локальная LLM |

### Постоянные volumes

| Volume | Монтируется в | Содержимое |
|--------|--------------|------------|
| `./output` | `/app/output` | Сгенерированные файлы |
| `ollama_data` | `/root/.ollama` | Модели Ollama |

> **Примечание**: Docker `CMD` указывает на `python -m core.jarvis_v3`, но entry point проекта — `main.py`. Для корректного запуска обновите `CMD` в Dockerfile.

---

## MCP Tools (15+)

Система поддерживает 15+ инструментов через MCP-протокол:

| Категория | Инструменты |
|-----------|------------|
| **Browser** | browser_navigate, browser_screenshot, browser_click, browser_extract_text |
| **Search** | search_web |
| **File** | file_read, file_write, file_list |
| **Shell** | shell_exec |
| **Telegram** | tg_send_message, tg_send_photo |
| **Media** | video_generate_seedance, image_generate |
| **Code** | exec_python, test_run, test_syntax_check |
| **Git** | git_commit, git_status |

**Real Tools** (регистрируются через `core/real_tools.py`):
- `tg_publish_post` — публикация в Telegram
- `shorts_generate` — генерация шортсов
- `content_publish_full` — полный pipeline контента
- `video_publish_full` — полный pipeline видео
- `tg_send_video` — отправка видео
- `video_create_hybrid` — гибридное создание видео

---

## Hermes Agent Integration (в планах)

**Hermes** — планируемый агент-интегратор для:
- Унифицированного API доступа ко всем воркерам через REST/gRPC
- WebSocket-уведомлений о статусе задач
- Масштабирования на несколько инстансов Jarvis
- Централизованного логирования и мониторинга

**Статус**: 🔮 Concept phase. Требования и API — в разработке.

---

## Known Issues

| # | Проблема | Обходное решение | Статус |
|---|----------|-----------------|--------|
| 1 | ~~`skills/` директория импортируется в `main.py`, но не существует~~ | ✅ Исправлено: созданы skills/, memory/, tests/, prompts/ | ✅ Fixed |
| 2 | ~~`tests/`, `prompts/`, `memory/` директории отсутствуют~~ | ✅ Исправлено: все директории созданы | ✅ Fixed |
| 3 | Docker `CMD` указывает на `core.jarvis_v3`, а не `main.py` | Обновить `CMD` в Dockerfile | 🟡 Несоответствие |
| 4 | ~~`Makefile` содержит `pytest tests/`, но директории `tests/` нет~~ | ✅ Исправлено: тесты перенесены в tests/ | ✅ Fixed |
| 5 | `core/intent_classifier.py`, `core/memory.py`, `core/config.py` — описаны в старых документах, но не существуют | Функциональность встроена в `jarvis_v3.py` | ✅ Ожидаемо |
| 6 | `pro_editor_v2.py … v8.py` — legacy-версии, актуальная `pro_editor_v9.py` | Использовать `pro_editor_v9.py` | ✅ Ожидаемо |
| 7 | `core/blender_vse/` и `core/tsifra2-vse/` — экспериментальные Blender интеграции | Использовать с осторожностью | 🟡 Эксперимент |

---

## Разработка

### Команды Makefile

```bash
make install    # Установить зависимости
make run        # Запустить проект (python main.py)
make test       # Запустить тесты (pytest tests/)
make clean      # Очистить кэш
make docker     # Запустить в Docker
```

### Запуск тестов

```bash
# Индивидуальные тестовые скрипты
python test_llm.py
python test_video.py
python test_telegram_bot.py
python test_intel_worker.py
python test_quality_control.py
```

### Форматирование кода

```bash
black core/ agents/ tools/ main.py
```

### Проверка безопасности

```bash
bandit -r core/ agents/ tools/
```

---

## Документация

| Файл | Описание |
|------|----------|
| `AGENTS.md` | Инструкции для AI-агентов (стиль, паттерны, правила) |
| `ARCHITECTURE.md` | Архитектура системы, диаграммы, data flow |
| `CONTEXT.md` | Контекст проекта, философия, бизнес-цели |
| `README.md` | Этот файл — обзор и quickstart |
| `CHANGELOG.md` | История изменений (в корне репозитория) |

---

## Лицензия

MIT License — свободное использование для любых целей.

---

## Автор

**Digital Clone v3** — создан с помощью AI и для AI.

> *"The best way to predict the future is to automate it."*
