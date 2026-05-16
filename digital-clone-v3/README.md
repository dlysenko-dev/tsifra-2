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
    │  MCP LAYER  │ ← 50+ инструментов
    │  (Tools)    │   search, browser, scraper,
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

## Как установить

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
# Вариант A: Напрямую
python main.py

# Вариант B: Через Makefile
make run

# Вариант C: Docker
make docker
# или
docker-compose up --build
```

---

## Структура проекта

```
digital-clone-v3/
|
|-- main.py                    # Точка входа
|-- requirements.txt           # Python-зависимости
|-- Dockerfile                 # Docker-образ
|-- docker-compose.yml         # Docker Compose (с Ollama)
|-- Makefile                   # Команды разработки
|-- .env.example               # Шаблон конфигурации
|
|-- core/                      # Ядро системы
|   |-- jarvis_v3.py           # Оркестратор (OpenManus-style)
|   |-- llm_router.py          # Multi-LLM роутер с fallback
|   |-- mcp_layer.py           # MCP протокол (50+ tools)
|   |-- intent_classifier.py   # Классификатор намерений
|   |-- memory.py              # Векторная память
|   |-- config.py              # Конфигурация
|
|-- agents/                    # AI-агенты (воркеры)
|   |-- content_worker.py      # Контент (посты, сценарии)
|   |-- video_worker.py        # Видео (шортсы, reels)
|   |-- dev_worker.py          # Разработка (код, API)
|   |-- intel_worker.py        # Аналитика (рынок, конкуренты)
|   |-- sell_worker.py         # Продажи (воронки, email)
|
|-- skills/                    # Скиллы (модули умений)
|   |-- engine.py              # Движок скиллов
|   |-- web_search.py          # Поиск в интернете
|   |-- scrape.py              # Парсинг сайтов
|   |-- generate_image.py      # Генерация изображений
|   |-- text2speech.py         # Озвучка текста
|   |-- browser.py             # Браузерная автоматизация
|   |-- business_models.py     # Бизнес-модели
|
|-- memory/                    # Память системы
|   |-- vector_store.py        # Векторная БД
|   |-- session_memory.py      # Сессионная память
|
|-- prompts/                   # Промпты
|   |-- system_prompts.yaml    # Системные промпты
|   |-- worker_prompts.yaml    # Промпты воркеров
|
|-- tests/                     # Тесты
|   |-- test_orchestrator.py
|   |-- test_llm_router.py
|   |-- test_mcp_layer.py
|
|-- data/                      # Данные (монтируется в Docker)
|-- output/                    # Выходные файлы (монтируется)
|-- skills/                    # Кастомные скиллы (монтируется)
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
# Запуск бота
python -m core.jarvis_v3 --telegram

# В Telegram:
# /start - начать
# /task <описание> - выполнить задачу
# /status - статус системы
# /memory - показать память
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

# 3. Система доступна на порту 8080
curl http://localhost:8080/health
```

### Docker сервисы

| Сервис | Порт | Описание |
|--------|------|----------|
| digital-clone | 8080 | Основной агент |
| ollama | 11434 | Локальная LLM |

### Постоянные volumes

| Volume | Монтируется в | Содержимое |
|--------|--------------|------------|
| `./data` | `/app/data` | Данные проекта |
| `./output` | `/app/output` | Сгенерированные файлы |
| `./skills` | `/app/skills` | Кастомные скиллы |
| `ollama_data` | `/root/.ollama` | Модели Ollama |

---

## MCP Tools (50+)

Система поддерживает 50+ инструментов через MCP-протокол:

| Категория | Инструменты |
|-----------|------------|
| **Search** | web_search, google_search, serper_search |
| **Browser** | browser_visit, browser_click, browser_scroll, browser_find |
| **Scrape** | scrape_page, scrape_table, extract_links |
| **Media** | generate_image, generate_video, text2speech |
| **Code** | code_analyzer, code_fixer, code_generator |
| **Data** | csv_reader, json_parser, data_visualizer |
| **File** | file_read, file_write, file_search |

---

## Разработка

### Команды Makefile

```bash
make install    # Установить зависимости
make run        # Запустить проект
make test       # Запустить тесты
make clean      # Очистить кэш
make docker     # Запустить в Docker
```

### Запуск тестов

```bash
pytest tests/ -v
```

### Форматирование кода

```bash
black core/ agents/ skills/ main.py
```

### Проверка безопасности

```bash
bandit -r core/ agents/ skills/
```

---

## Лицензия

MIT License — свободное использование для любых целей.

---

## Автор

**Digital Clone v3** — создан с помощью AI и для AI.

> *"The best way to predict the future is to automate it."*
