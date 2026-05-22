# Исследование: Hermes Agent (Nous Research)

> **Видео-источник:** https://youtu.be/Gx2joHxUhgg  
> **Правильное название:** Hermes Agent by Nous Research  
> **Дата исследования:** 2026-05-22  
> **GitHub:** https://github.com/NousResearch/hermes-agent  
> **Документация:** https://hermes-agent.nousresearch.com/docs/

---

## 1. Что такое Hermes Agent

Hermes Agent — это **open-source AI-агент с встроенным циклом самообучения** (self-improving learning loop), разработанный компанией Nous Research (MIT license). Это не просто "обертка над чатом" и не копилот кода — это полноценная автономная система, которая **становится умнее с каждым использованием**.

### Ключевой дифференциатор
Единственный агент на рынке с **замкнутым циклом обучения**:
- Создает скиллы из опыта (autonomous skill creation)
- Улучшает скиллы во время использования (skill self-improvement)
- Периодически "подталкивает" себя к сохранению знаний (periodic nudges)
- Ищет по своим прошлым сессиям через FTS5 (cross-session recall)
- Строит углубленную модель пользователя через Honcho dialectic user modeling

---

## 2. Архитектура и возможности

### 2.1 Memory & Learning (Память и обучение)

| Компонент | Описание | Потенциал для нашего проекта |
|-----------|----------|------------------------------|
| **Agent-curated memory** | Агент сам решает, что стоит запомнить | Улучшение персонализации Digital Clone |
| **Autonomous skill creation** | После сложных задач создает reusable skill | Можно автоматизировать создание video-pipeline skills |
| **Skill self-improvement** | Скиллы становятся лучше при повторном использовании | Постепенное улучшение качества видео-контента |
| **FTS5 recall** | Полнотекстовый поиск по всем сессиям | Замена/дополнение текущей векторной памяти |
| **Honcho dialectic** | Моделирование пользователя через диалектику | Глубокое понимание предпочтений клиентов |

### 2.2 Messaging & Gateway (15+ платформ)

Hermes имеет **единый gateway-процесс**, который обслуживает все платформы:
- Telegram, Discord, Slack, WhatsApp, Signal
- Matrix, Mattermost, Email, SMS
- DingTalk, Feishu, WeCom, BlueBubbles
- Home Assistant

**Особенности:**
- Voice memo transcription
- Cross-platform conversation continuity (диалог продолжается между платформами)
- Gateway dashboard на `127.0.0.1:9118/kanban`

### 2.3 Skills System (agentskills.io)

Скиллы — это **portable, shareable, community-contributed** модули:
- Совместимы со стандартом agentskills.io
- Procedural memory — агент создает и переиспользует автономно
- Есть Skills Hub (hermeshub / agentskills.io)
- Сообщество создает скиллы для разных задач

**Примеры community skills:**
- `paper-to-skill` — читает научные статьи и генерирует Triton kernels
- `hermes-skill-factory` — наблюдает за workflow и автоматически создает скиллы
- `Repo-to-Shorts` — сканирует GitHub-репозитории и делает видео

### 2.4 MCP Integration

Hermes поддерживает **MCP (Model Context Protocol)**:
- Подключение любого MCP-сервера для расширения возможностей
- Фильтрация инструментов
- Безопасное расширение
- Растущая MCP-экосистема

### 2.5 Cron & Scheduling

Встроенная система cron:
- Планирование задач на любом языке
- Доставка результатов на любую платформу
- "Set it and forget it" автоматизация

### 2.6 Terminal Backends (7+ вариантов запуска)

| Backend | Особенности |
|---------|------------|
| **Local** | Локальный запуск |
| **Docker** | Контейнеризация |
| **SSH** | Удаленный доступ |
| **Daytona** | Serverless persistence |
| **Singularity** | HPC-окружения |
| **Modal** | Serverless, hibernates when idle |
| **Vercel Sandbox** | Облачное выполнение |

**Критически важно для нас:** Hermes может работать на **$5 VPS** или **serverless** с гибернацией — идеально для cost-effective развертывания.

### 2.7 Multi-Agent Orchestration (Kanban)

**Hermes Kanban** — система визуальной оркестрации нескольких агентов:
- Доски: TRIAGE / TODO / READY / IN PROGRESS / BLOCKED / DONE
- Карточки: `CODEX GOAL`, `CLAUDE CODE GOAL`, `HERMES GOAL`
- Агенты коммуницируют через **shared Kanban document** (избегают бесконечных циклов)
- Каждый профиль может использовать **свою модель**
- Unlimited boards and subscriptions
- Project update delivery в Telegram/Discord

**DeepSwarm 2.0** — инструмент для parallel worker orchestration:
- Auto-optimized parallel workers
- Tiered model delegation (V4 Pro для планирования, V4 Flash для выполнения — экономия 60-70%)
- Crash-resilient design с per-task checkpoints

### 2.8 Model Support (200+ моделей)

Hermes **не привязан к одному LLM**:
- Nous Portal (собственные модели)
- OpenRouter (200+ моделей)
- NovitaAI, NVIDIA NIM, Xiaomi MiMo
- z.ai/GLM, Kimi/Moonshot, MiniMax
- Hugging Face, OpenAI, Anthropic
- Локальные endpoints

**Переключение:** `hermes model` — без изменения кода, без vendor lock-in.

### 2.9 Security

Hermes использует **conservative security posture**:
- Container hardening
- Read-only root filesystems
- Dropped capabilities
- Namespace isolation
- Filesystem checkpoints and rollback
- Pre-execution scanner для terminal commands

### 2.10 Research-Ready Features

Для нас как для проекта, работающего с AI-видео:
- **Batch trajectory generation** — генерация траекторий для обучения
- **Trajectory compression** — сжатие для training tool-calling models
- **Atropos RL environments** — RL-среды для улучшения агентов

---

## 3. Сравнение: Hermes Agent vs Digital Clone v3

### 3.1 Архитектурное сравнение

| Компонент | Digital Clone v3 | Hermes Agent | Оценка |
|-----------|-----------------|--------------|--------|
| **Оркестратор** | Jarvis v3 (OpenManus-style) | Kanban + Goal-based | Hermes более зрелый |
| **Воркеры** | 5 фиксированных (content, video, dev, intel, sell) | Subagents + Skills | Hermes гибче |
| **MCP Layer** | ~15 инструментов | 47 built-in + любые MCP | Hermes богаче |
| **LLM Router** | Kimi → DeepSeek → Groq → Ollama → GLM | 200+ через OpenRouter + любые endpoints | Hermes шире |
| **Память** | Векторная БД | FTS5 + Honcho + Skill memory | Hermes продвинутей |
| **Messaging** | Только Telegram | 15+ платформ | Hermes значительно лучше |
| **Scheduling** | Custom cron-like Python | Встроенный cron | Hermes проще |
| **Skills** | Жестко закодированы | Autonomous skill creation | Hermes самообучается |
| **Desktop UI** | Нет | Hermes Desktop v0.6.0 | Hermes выигрывает |
| **Multi-agent** | Нет | Kanban orchestration | Hermes уникален |
| **Deployment** | Docker + local | 7 backends + serverless | Hermes гибче |
| **Video editing** | Pro editor v2-v9 (FFmpeg) | Через skills/MCP | DCv3 лучше здесь |
| **Self-learning** | Ограниченный | Полный learning loop | Hermes уникален |

### 3.2 Где Digital Clone v3 сильнее

1. **Видео-конвейер** — pro_editor_v8-v9, Blender AI workflow, FFmpeg assembly — это специализированная экспертиза, которой у Hermes нет
2. **Кастомные бизнес-модели** — 10+ готовых моделей монетизации в DCv3
3. **Quality Control** — ContentQualityChecker с LLM-based оценкой
4. **Autonomous Loop** — глубокая интеграция с PipelineExecutor
5. **TоV Profile** — tone-of-voice профилирование для контента

---

## 4. Возможности интеграции

### 4.1 Сценарий A: Hermes как "внешняя оболочка" (Wrapper)

**Суть:** Запустить Digital Clone v3 как набор skills внутри Hermes.

```
Hermes Agent (оркестратор)
├── Skill: video_generation (обертка над pro_editor_v9.py)
├── Skill: content_creation (обертка над content_worker.py)
├── Skill: market_intel (обертка над intel_worker.py)
├── Skill: dev_automation (обертка над dev_worker.py)
└── Skill: sell_funnel (обертка над sell_worker.py)
```

**Преимущества:**
- Получаем 15+ платформ мгновенно
- Hermes управляет памятью и learning loop
- Кросс-платформенная синхронизация диалогов
- Serverless deployment через Modal/Daytona

**Риски:**
- Нужно адаптировать API DCv3 под интерфейс skills
- Видео-конвейер может работать медленнее через абстракцию

### 4.2 Сценарий B: Hermes MCP Server для DCv3

**Суть:** Запустить Hermes как MCP-сервер, к которому обращается DCv3.

```
Digital Clone v3 (Jarvis Orchestrator)
├── MCP: hermes_memory (FTS5 + Honcho)
├── MCP: hermes_skills (skill marketplace)
├── MCP: hermes_messaging (Telegram/Discord/Slack gateway)
├── MCP: hermes_cron (scheduling)
└── MCP: hermes_browser (Lightpanda/computer-use)
```

**Преимущества:**
- DCv3 остается основной системой
- Постепенная миграция компонентов
- Минимальные изменения архитектуры
- Получаем лучшие части Hermes без полного перехода

**Риски:**
- Нужно поддерживать два проекта
- MCP-протокол может добавить latency

### 4.3 Сценарий C: Kanban Multi-Agent Orchestration

**Суть:** Использовать Hermes Kanban для управления несколькими экземплярами DCv3.

```
Hermes Kanban Board
├── Column: TRIAGE
│   └── Card: "Сгенерировать 5 шортсов про AI"
├── Column: IN PROGRESS
│   ├── Card: "Шортс #1" → Agent: dc3-video-worker-1
│   ├── Card: "Шортс #2" → Agent: dc3-video-worker-2
│   └── Card: "Анализ трендов" → Agent: dc3-intel-worker
├── Column: DONE
│   └── Card: "Шортс #3" → Agent: dc3-video-worker-3
```

**Преимущества:**
- Визуальное управление параллельными задачами
- Агенты не мешают друг другу (shared Kanban doc вместо чата)
- Автоматическое распределение нагрузки
- Масштабирование: добавляем worker'ов по мере необходимости

### 4.4 Сценарий D: Полная миграция на Hermes

**Суть:** Переписать DCv3 как набор skills и MCP-серверов для Hermes.

**Что переносим:**
- Video pipeline → `skill-dcv3-video` (Python + FFmpeg)
- Content worker → `skill-dcv3-content` (prompts + ToV)
- Intel worker → `skill-dcv3-intel` (parsers + analysis)
- Dev worker → `skill-dcv3-dev` (code generation)
- Sell worker → `skill-dcv3-sell` (funnels + CRM)

**Что заменяем Hermes'ом:**
- Telegram bot → Hermes gateway
- LLM Router → Hermes model command
- Memory → Hermes FTS5 + Honcho
- Cron → Hermes built-in cron
- MCP Layer → Hermes 47 tools + custom MCP

**Риски:**
- Большой объем работы (2-3 месяца)
- Возможные регрессии в видео-качестве
- Зависимость от roadmap Nous Research

---

## 5. Конкретные точки интеграции

### 5.1 Immediate wins (быстрые победы)

| Интеграция | Сложность | ROI | Действие |
|------------|-----------|-----|----------|
| **Telegram Gateway** | Low | High | Заменить custom bot на Hermes gateway — получаем Discord/Slack/WhatsApp бесплатно |
| **Memory Enhancement** | Low | Medium | Интегрировать Hermes FTS5 recall в DCv3 через MCP |
| **Skill Marketplace** | Low | High | Использовать agentskills.io для готовых skills |
| **Cron Scheduling** | Low | Medium | Заменить custom scheduler на Hermes cron |
| **Desktop UI** | Low | High | Hermes Desktop v0.6.0 для non-CLI пользователей |

### 5.2 Medium-term (1-2 месяца)

| Интеграция | Сложность | ROI | Действие |
|------------|-----------|-----|----------|
| **Kanban Orchestration** | Medium | Very High | Управлять несколькими DCv3 worker'ами через Kanban |
| **Multi-Platform Publishing** | Medium | High | Публиковать контент в Telegram + Discord + Slack одновременно |
| **Self-Improving Video Skills** | Medium | Very High | Создать video-generation skill, который улучшается с каждым роликом |
| **Parallel Processing** | Medium | High | DeepSwarm 2.0 для параллельной генерации видео |

### 5.3 Long-term (3-6 месяцев)

| Интеграция | Сложность | ROI | Действие |
|------------|-----------|-----|----------|
| **Full Migration** | High | Very High | Полный переход на Hermes как платформу |
| **Custom Model Training** | High | Very High | Использовать Atropos RL + trajectory generation для обучения модели на наших видео |
| **AI Agency Setup** | High | Very High | HermesWorld / EchoPulz стиль — несколько специализированных агентов в офисе |

---

## 6. Влияние на проект

### 6.1 Положительное влияние

1. **Экспоненциальное увеличение охвата**
   - Сейчас: только Telegram
   - С Hermes: Telegram + Discord + Slack + WhatsApp + Signal + Email
   - Потенциал: x5-10 аудитория без дополнительных затрат

2. **Снижение затрат на инфраструктуру**
   - Serverless deployment (Modal/Daytona): платишь только за время выполнения
   - Для ночной генерации видео: запускается → работает → засыпает → почти бесплатно
   - Текущий Docker-вариант требует постоянно работающего сервера

3. **Самообучающийся контент**
   - Hermes будет автоматически создавать skills для повторяющихся задач
   - "Создать шортс про AI" → после 10 выполнений скилл становится оптимальным
   - Снижение prompt engineering ручной работы

4. **Доступ к community ecosystem**
   - 101K+ GitHub stars — огромное сообщество
   - Готовые skills для разных задач
   - Быстрые bug fixes и новые фичи

5. **Research pipeline**
   - Trajectory generation для обучения собственных моделей
   - Возможность создать специализированную модель для видео-генерации

### 6.2 Риски и ограничения

1. **Видео-специфика**
   - Hermes не имеет встроенного video-editing pipeline
   - Наши pro_editor_v8-v9, Blender AI workflow — уникальные активы
   - Риск потери качества при полной миграции

2. **Зависимость от Nous Research**
   - Hermes контролируется одной компанией
   - Roadmap определяется их приоритетами
   - Но: MIT license, можно форкнуть

3. **Сложность миграции**
   - DCv3 имеет ~1000+ строк кастомной логики
   - Перенос потребует значительных ресурсов
   - Нужно сохранить backward compatibility

4. **Безопасность**
   - Hermes запускает shell-команды, Python-код
   - Нужно правильно настроить sandbox
   - Но: у Hermes более строгий security posture, чем у аналогов

### 6.3 Нейтральное (требует адаптации)

1. **Learning curve**
   - Команда должна изучить Hermes CLI (`hermes`, `hermes setup`, `hermes model`)
   - Новая парадигма skills vs традиционные модули
   - Kanban-оркестрация вместо imperative кода

2. **Пересмотр архитектуры**
   - Текущий Jarvis Orchestrator может быть избыточен
   - Нужно решить: заменить или дополнить Hermes
   - MCP Layer DCv3 может конфликтовать с Hermes MCP

---

## 7. Рекомендации

### 7.1 Краткосрочная стратегия (2-4 недели)

**Рекомендую Сценарий B (Hermes MCP Server для DCv3) + элементы Сценария A:**

1. **Установить Hermes Agent** на dev-машину
   ```bash
   curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
   hermes setup
   ```

2. **Интегрировать Hermes Gateway** для multi-platform messaging
   - Запустить `hermes gateway` параллельно с текущим Telegram ботом
   - Настроить Telegram + Discord
   - Постепенно переключать трафик

3. **Использовать Hermes Memory** как дополнительный слой
   - Интегрировать FTS5 recall для поиска по истории
   - Сохранить текущую векторную БД как primary

4. **Эксперимент с Skills**
   - Создать skill для повторяющейся задачи (например, "ежедневный пост")
   - Посмотреть, как Hermes его улучшает

### 7.2 Среднесрочная стратегия (1-3 месяца)

1. **Kanban Orchestration**
   - Запустить Hermes Kanban dashboard
   - Создать goal cards для типовых задач DCv3
   - Управлять несколькими worker'ами через доску

2. **Parallel Video Generation**
   - Интегрировать DeepSwarm 2.0
   - Генерировать 3-5 шортсов параллельно
   - Экономия времени: 60-70%

3. **Self-Improving Content Skills**
   - Создать content-creation skill
   - Позволить Hermes улучшать его на основе метрик (views, engagement)

### 7.3 Долгосрочная стратегия (3-6 месяцев)

1. **Оценить полную миграцию**
   - Если результаты положительные — перенести всю логику в skills
   - Сохранить video-pipeline как отдельный MCP-сервер
   - Запустить на Modal/Daytona для cost optimization

2. **Custom Model Training**
   - Использовать Atropos RL для fine-tuning на наших видео-траекториях
   - Создать специализированную модель для video-script generation

---

## 8. Технические детали для начала

### 8.1 Установка Hermes Agent

```bash
# Linux, macOS, WSL2
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash

# Конфигурация
hermes setup

# Выбор модели
hermes model

# Запуск CLI
hermes

# Запуск gateway (Telegram, Discord, etc.)
hermes gateway setup
hermes gateway start

# Dashboard
hermes dashboard
```

### 8.2 Интеграция с DCv3 (MCP Server)

```python
# core/hermes_mcp_bridge.py

class HermesMCPBridge:
    """Мост между DCv3 и Hermes Agent через MCP."""
    
    async def query_memory(self, query: str) -> str:
        """Поиск по Hermes FTS5 memory."""
        # Вызов Hermes через MCP
        pass
    
    async def publish_multiplatform(self, content: str, platforms: list):
        """Публикация в несколько платформ."""
        # Hermes gateway API
        pass
    
    async def schedule_task(self, cron: str, task: str):
        """Планирование через Hermes cron."""
        pass
```

### 8.3 Создание Skill для DCv3

```python
# ~/.hermes/skills/dcv3-video/skill.py

class DCv3VideoSkill:
    """Hermes Skill для video generation через DCv3 pipeline."""
    
    async def generate_shorts(self, topic: str, duration: int = 30):
        """Генерация шортса через pro_editor_v9."""
        from digital_clone_v3.pro_editor_v9 import generate_video
        return await generate_video(topic=topic, duration=duration)
```

---

## 9. Заключение

Hermes Agent — это **зрелая, быстро развивающаяся платформа** с уникальными возможностями self-improvement и multi-agent orchestration. Для нашего проекта Digital Clone v3 он представляет:

- **Краткосрочную ценность:** Multi-platform messaging, улучшенная память, готовые skills
- **Среднесрочную ценность:** Kanban orchestration, parallel processing, cost-effective deployment
- **Долгосрочную ценность:** Self-improving content pipeline, custom model training, AI agency setup

**Ключевое преимущество:** Hermes может работать как **ускоритель** нашего проекта, а не как замена. Интегрируя его компоненты (gateway, memory, cron, kanban), мы получаем enterprise-level возможности без переписывания нашего уникального video-pipeline.

**Рекомендуемый подход:** Начать с **Сценария B (MCP Server)** + ** gateway integration**, постепенно наращивая использование Hermes по мере валидации результатов.

---

## 10. Полезные ссылки

- **GitHub:** https://github.com/NousResearch/hermes-agent
- **Документация:** https://hermes-agent.nousresearch.com/docs/
- **Skills Hub:** https://agentskills.io
- **Community Discord:** https://discord.gg/NousResearch
- **Awesome Hermes:** https://github.com/0xNyk/awesome-hermes-agent
- **Hermes Ecosystem Map:** https://github.com/ksimback/hermes-ecosystem
- **Hermes Desktop:** https://github.com/advanceyue/hermes-desktop
- **DeepSwarm 2.0:** https://github.com/mr_r0b0t/deepswarm (parallel orchestration)

---

> **Примечание:** Это исследование проведено на основе открытых источников (GitHub, документация, community resources). Рекомендуется провести PoC (Proof of Concept) перед полномасштабной интеграцией.
