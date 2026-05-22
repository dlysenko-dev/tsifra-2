# Digital Clone v3 — Контекст проекта

## Что мы строим
Автономного AI-агента "Джарвис" который работает на Oracle Cloud VPS 24/7, управляется голосом через Telegram, создаёт контент (шортсы, посты), привлекает трафик, отвечает клиентам и зарабатывает деньги.

## Философия (из стрима ИИздец)
1. Телефон + голос = PRIMARY интерфейс
2. Человек = стратег, агент = исполнитель (диалог, не код)
3. Один Джарвис оркестрирует всё (не 4 разрозненных агента)
4. Скилл = чип в голову (reusable навыки)
5. Видеть = контролировать (щупальца везде — тренды, конкуренты)
6. Трафик > разработка (главная проблема — трафик)
7. Агент знает тебя (цифровой мозг = твоя копия)

## Текущая архитектура (создано)
```
digital-clone-v3/
├── core/
│   ├── jarvis_v3.py — Оркестратор (OpenManus-style planner)
│   ├── llm_router.py — Fallback: Kimi → DeepSeek → Groq → Ollama → GLM
│   ├── mcp_layer.py — 15+ инструментов (MCP Protocol)
│   ├── autonomous_loop.py — Автономный event loop (cron-like scheduler)
│   ├── telegram_bot.py — Telegram Bot (python-telegram-bot >= 20.0)
│   ├── quality_control.py — LLM-based проверка качества
│   ├── video_creator.py — Гибридный видео-генератор (Motion Canvas + Blender)
│   ├── video_assembler.py — Сборка видео из сегментов
│   ├── blender_ai_workflow.py — Blender integration
│   ├── real_tools.py — Real tools (tg_publish_post, shorts_generate)
│   ├── asset_cache.py — Кэш ассетов
│   ├── asset_downloader.py — Загрузка ассетов
│   ├── asset_finder.py — Поиск ассетов
│   ├── bounce_animator.py — Bounce-анимации
│   ├── kinetic_text.py — Kinetic typography
│   ├── sound_library.py — Библиотека звуков
│   ├── tov_profile.py — Tone of Voice профили
│   ├── self_learning_video.py — Self-learning для видео
│   └── kimi_cli_adapter.py — Адаптер для Kimi CLI
├── agents/
│   ├── content_worker.py — Посты, сценарии, PDF, клиппинг
│   ├── video_worker.py — Seedance, Web-to-Video, шортсы, motion graphics
│   ├── dev_worker.py — Vibe coding + security scan + автотесты
│   ├── intel_worker.py — Конкуренты, тренды, mind maps (НУЖНО ДОРАБОТАТЬ)
│   └── sell_worker.py — Клиенты, КП, монетизация
├── tools/
│   ├── shorts_pipeline.py — Pipeline шортсов
│   └── tg_publish.py — Публикация в Telegram
├── config/
│   ├── autonomous_schedule.json — Cron-задачи для AutonomousLoop
│   └── quality_thresholds.json — Пороги качества контента
├── templates/
│   └── horror_snowman.py — Blender template
├── learning/
│   ├── downloaded_videos/ — Скачанные видео для анализа
│   ├── etalons/ — Эталонные ролики
│   ├── masters/ — Анализ мастеров
│   ├── references/ — Референсы
│   └── video_knowledge.json — База знаний видео
├── assets/ — Шрифты, музыка, SFX, видео, overlays
├── output/ — Сгенерированные файлы (не коммитить)
├── temp/ — Временные файлы (не коммитить)
├── pro_editor_v2.py … v9.py — Версии pro video editor
├── create_viral_video.py — Генерация вирусных видео
├── analyze_all.py — Анализ контента
├── fetch_masters.py — Парсинг мастеров
├── build_knowledge_manual.py — Сборка knowledge base
├── main.py — Точка входа
└── test_*.py — Тестовые скрипты
```

> **Важно**: `skills/` директория импортируется в `main.py`, но физически отсутствует. Требуется создание `skills/engine.py` и `skills/business_models.py`.

## Бизнес-модели (встроены)
1. Клиппинг-сервис: 50-200K₽/мес
2. PDF-продукты: $500-5K/мес
3. Подписка на контент: $1-10K/мес
4. AI-консультации: $2-10K/мес
5. Ведение соцсетей: 100-300K₽/мес
6. Реферальные программы: $500-3K/мес

## Технологии
- **LLM**: Kimi API (Primary), DeepSeek, Groq, Ollama (Local), GLM (Backup)
- **Video**: Seedance 2.0 (бесплатно), Web-to-Video (HTML → Playwright → ffmpeg), Pro Editor v9
- **Voice**: gTTS (бесплатно), faster-whisper (INT8) — для Telegram
- **Infra**: Oracle Cloud Free Tier (4 CPU + 24GB RAM), Docker
- **UI**: Telegram Bot (python-telegram-bot >= 20.0)
- **Memory**: Obsidian Vault (ошибки, сессии, persona) — в планах vector store
- **Python**: 3.11+ (asyncio, dataclasses, pydantic-style)

## Уровни автономности (встроены)
- **Level 1 (MANUAL)** — всё на проверку человека (недели 1-2)
- **Level 2 (ASSISTED)** — простое сам, сложное — спросит (недели 3-4)
- **Level 3 (AUTONOMOUS)** — полная автономия, только отчёты (месяц 2+)

Агент ВСЕГДА эскалирует когда: не уверен, клиент хочет кастомное, API упал,
нет доступа, качество низкое, потенциально опасное действие.

## Что НУЖНО сделать (текущие задачи)
1. **IntelWorker v2** — детальная проработка:
   - Конкретные источники: RSS, API соцсетей, парсинг
   - Pinterest, YouTube, Instagram, Twitter/X, Reddit, Medium
   - Нововведения с оценкой "как поможет проекту"
   - Критический анализ каждой находки
   
2. **Telegram Bot v2** — полная реализация:
   - Клиенты пишут → бот → агент → ответ
   - Уведомления о задачах
   - Голосовые сообщения (Whisper → текст)
   - Inline keyboards, админ-панель
   
3. **Content Improvement Loop**:
   - Агент сравнивает свой контент с конкурентами
   - Автоматический анализ что заходит лучше
   - Постоянное улучшение
   
4. **Безопасная свобода**:
   - Правила и ограничения перед запуском
   - Постепенное увеличение автономности

5. **Hermes Agent Integration**:
   - REST/gRPC API для всех воркеров
   - WebSocket-уведомления
   - Масштабирование на несколько инстансов

## 21 видео — что было полезного
- #3 Seedance 2.0 — бесплатные AI-видео
- #9 OpenManus — open-source агент (референс)
- #14 CapCut + Claude — motion graphics
- #19 $20K/month PDF — монетизация
- #6 Клиппинг — платформы для заказов
- #1 Claude Security — сканирование кода
- #18 TestSprite — MCP автотесты
- #20 Gemma 4 + Ollama — локальный fallback
- #21 100+ скиллов — лучшие практики
- #11 NotebookLM — mind maps

## Пользователь
Даниил Лысенко. Строит Digital Clone — AI-агент для автоматизации бизнеса. Бюджет ~5000₽/мес. Oracle Cloud Free Tier. Цель: автоматический трафик + продажи через агентов.

---

## Документация проекта
- `AGENTS.md` — инструкции для AI-агентов
- `ARCHITECTURE.md` — архитектура и data flow
- `README.md` — обзор и quickstart
- `CHANGELOG.md` — история изменений (в корне репозитория)
