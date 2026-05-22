# Полная интеграция: Target Architecture + Поэтапная реализация

> **Принцип:** Проектируем целиком → Строим поэтапно → Каждый этап — работающая система

---

## 1. Target Architecture (целевая архитектура)

### 1.1 Общая картина

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           HERMES AGENT PLATFORM                              │
│  (Nous Research — orchestrator, memory, messaging, cron, skills engine)     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │  Gateway    │  │   Kanban    │  │   Memory    │  │   Cron Scheduler    │ │
│  │  (15+ plat) │  │  (Boards)   │  │ (FTS5+Honcho│  │  (Goals/Skills)     │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘ │
│         │                │                │                   │            │
│         └────────────────┴────────────────┴───────────────────┘            │
│                                    │                                        │
│                           ┌────────┴────────┐                               │
│                           │  Hermes Core    │                               │
│                           │  (Agent Loop)   │                               │
│                           └────────┬────────┘                               │
│                                    │                                        │
│  ┌─────────────────────────────────┼─────────────────────────────────────┐ │
│  │         DCv3 SKILL ECOSYSTEM    │                                     │ │
│  │  (наши кастомные skills + MCP)  │                                     │ │
│  │                                 ▼                                     │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │ │
│  │  │dcv3-video   │  │dcv3-content │  │dcv3-intel   │  │dcv3-sell    │  │ │
│  │  │skill        │  │skill        │  │skill        │  │skill        │  │ │
│  │  │             │  │             │  │             │  │             │  │ │
│  │  │pro_editor_v9│  │ToV profile  │  │fetch_masters│  │funnel engine│  │ │
│  │  │blender_ai   │  │auto_prompt  │  │analyze_comp │  │crm_bridge   │  │ │
│  │  │ffmpeg_asm   │  │quality_check│  │trend_mon    │  │email_chain  │  │ │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  │ │
│  │         │                │                │                │         │ │
│  │         └────────────────┴────────────────┴────────────────┘         │ │
│  │                                    │                                  │ │
│  │                           ┌────────┴────────┐                        │ │
│  │                           │  DCv3 MCP Core  │                        │ │
│  │                           │  (legacy bridge)│                        │ │
│  │                           └─────────────────┘                        │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
            ┌───────────┐   ┌───────────┐   ┌───────────┐
            │  Telegram │   │  Discord  │   │  YouTube  │
            │   Bot     │   │   Bot     │   │  Channel  │
            └───────────┘   └───────────┘   └───────────┘
```

### 1.2 Компоненты Target Architecture

#### Layer 1: Hermes Platform (внешний оркестратор)
- **Gateway**: Все входящие сообщения со всех платформ
- **Kanban**: Визуальное управление задачами и агентами
- **Memory**: FTS5 + Honcho для долгосрочной памяти
- **Cron**: Планирование автономных задач
- **Skills Engine**: Загрузка, выполнение, самообучение скиллов
- **Agent Loop**: Основной цикл обработки

#### Layer 2: DCv3 Skill Ecosystem (наши активы)
Каждый воркер DCv3 становится **Hermes Skill**:

| Skill Name | Что содержит | Интерфейс |
|------------|-------------|-----------|
| `dcv3-video` | pro_editor_v9, blender_ai, ffmpeg_assembler, sound_library | `generate_shorts()`, `generate_reel()`, `edit_video()` |
| `dcv3-content` | ToV profile, quality_control, auto_prompts, content_worker | `create_post()`, `create_script()`, `check_quality()` |
| `dcv3-intel` | fetch_masters, analyze_masters, intel_worker | `research_competitors()`, `monitor_trends()`, `generate_report()` |
| `dcv3-dev` | dev_worker, code templates, git automation | `generate_code()`, `fix_bug()`, `deploy_service()` |
| `dcv3-sell` | sell_worker, funnel engine, email chains | `create_funnel()`, `answer_client()`, `send_campaign()` |

#### Layer 3: DCv3 MCP Core (legacy bridge)
Минимальный слой совместимости, чтобы старый код работал без изменений:
- `llm_router` → проксирует в Hermes model selector
- `mcp_layer` → проксирует в Hermes tools
- `memory` → проксирует в Hermes FTS5
- `telegram_bot` → проксирует в Hermes gateway

### 1.3 Поток данных (Data Flow)

```
[User on Discord] 
      ↓
[Hermes Gateway] — распознает платформу, сохраняет контекст
      ↓
[Hermes Agent Loop] — intent classification через LLM
      ↓
[Hermes Kanban] — создает Goal Card (например, "Создать шортс про MCP")
      ↓
[Skill Router] — определяет, какой skill нужен (dcv3-video)
      ↓
[dcv3-video skill] — вызывает pro_editor_v9.generate_shorts()
      ↓
[Video Pipeline] — FFmpeg + Blender + Assets → MP4 файл
      ↓
[Hermes Gateway] — отправляет результат обратно в Discord + Telegram
      ↓
[Hermes Memory] — сохраняет результат, обновляет skill (self-improvement)
      ↓
[Hermes Cron] — если задача повторяющаяся, планирует следующую
```

### 1.4 State Management

| Что | Где хранится | Формат |
|-----|-------------|--------|
| User preferences | Hermes Honcho | Dialectic user model |
| Conversation history | Hermes FTS5 | Full-text indexed |
| Video projects | DCv3 local storage + Hermes Memory | JSON + refs |
| Skills metadata | `~/.hermes/skills/dcv3-*/` | Python modules + README |
| Quality metrics | DCv3 analytics DB | Time-series |
| Content templates | DCv3 templates/ + Hermes skill memory | YAML + learned variants |

---

## 2. Почему не "всё и сразу"

### 2.1 Риски "big bang" миграции

| Риск | Вероятность | Последствие |
|------|------------|-------------|
| Video pipeline сломается | Высокая | Потеря уникального актива, дни починки |
| Hermes окажется нестабильным | Средняя | Вся система лежит, нет fallback |
| API Hermes изменится | Средняя | Переписывание интеграции |
| Performance regression | Высокая | Видео генерируется в 2-3x дольше |
| Data loss (memory migration) | Низкая, но критичная | Потеря обученных профилей |

### 2.2 Аргументы за поэтапность

**1. Каждый этап — работающая система**
- Нет состояния "полумиграции"
- Можно остановиться на любом этапе и система работает
- Бизнес не страдает

**2. Обратная связь между этапами**
- После этапа 1 узнаем реальные latency Gateway
- После этапа 2 поймем, как Kanban работает с нашими задачами
- Это позволяет скорректировать target architecture

**3. Параллельная разработка**
- Пока один разработчик интегрирует Gateway
- Другой может начинать оборачивать video pipeline в skill
- Нет блокировок

**4. Риск-менеджмент**
- Если Hermes закроется/заглохнет — мы потеряем только последний этап
- Основная система всегда цела

---

## 3. Поэтапная реализация Target Architecture

### ЭТАП 0: Foundation (неделя 1) — Подготовка

**Цель:** Подготовить инфраструктуру для интеграции, ничего не сломав.

```
Digital Clone v3 (как есть)
├── [NEW] hermes/              # Новая директория в проекте
│   ├── docker-compose.yml     # Hermes Agent в отдельном контейнере
│   ├── config/
│   │   └── gateway.yaml       # Конфиг Gateway (Telegram только)
│   └── skills/
│       └── __init__.py
├── core/
│   └── [NEW] hermes_bridge.py # Минимальный мост DCv3 ↔ Hermes
└── (всё остальное без изменений)
```

**Задачи:**
1. Запустить Hermes Agent в Docker-контейнере (isolated)
2. Настроить Hermes Gateway только для **нового** Telegram бота (test bot)
3. Создать `hermes_bridge.py` с методами:
   - `send_message(platform, text)`
   - `get_memory(query)` — stub
   - `schedule_task(cron, task)` — stub
4. Провести нагрузочное тестирование: Hermes Gateway vs текущий бот

**Критерий готовности:**
- Hermes Gateway работает параллельно с текущей системой
- Можно отправить тестовое сообщение через `hermes_bridge.py`
- Нулевое влияние на production

---

### ЭТАП 1: Multi-Platform Gateway (недели 2-3)

**Цель:** Заменить messaging layer DCv3 на Hermes Gateway.

```
Hermes Gateway
├── Telegram (primary)      ← текущий бот мигрирует сюда
├── Discord (new)           ← новая платформа
└── Slack (new)             ← новая платформа
      │
      ▼
[Hermes Bridge] → [Jarvis Orchestrator] → [Workers] → [Output]
```

**Задачи:**
1. Перенести логику текущего Telegram бота в Hermes Gateway
2. Настроить Discord и Slack bots через Gateway
3. Реализовать `hermes_bridge.py` полностью для messaging
4. **Fallback:** если Gateway падает — автоматически переключаться на старый бот

**Критерий готовности:**
- Пользователи могут писать боту в Telegram/Discord/Slack
- Ответы идут через Hermes Gateway
- Старый бот отключен, но готов к fallback

**Бизнес-ценность:** x3 платформы без написания кода для Discord/Slack

---

### ЭТАП 2: Memory Integration (недели 4-5)

**Цель:** Интегрировать Hermes Memory (FTS5 + Honcho) как primary memory.

```
[User Query]
      ↓
[Hermes Gateway]
      ↓
[Hermes Memory] — поиск по истории, user model
      ↓
[Jarvis Orchestrator] + context из Memory
      ↓
[Workers]
      ↓
[Result] → [Hermes Memory] — сохранение
```

**Задачи:**
1. Создать `dcv3_memory_skill` — обертка над текущей векторной БД
2. Интегрировать Hermes FTS5 для поиска по conversation history
3. Настроить Honcho dialectic modeling для key users
4. Мигрировать исторические данные (экспорт/импорт)

**Критерий готовности:**
- Бот помнит предыдущие диалоги через Hermes Memory
- Поиск по истории работает через `/search <query>`
- User preferences автоматически обновляются

**Бизнес-ценность:** Персонализация без ручного prompt engineering

---

### ЭТАП 3: Cron & Autonomous Loop (недели 6-7)

**Цель:** Заменить custom autonomous_loop.py на Hermes Cron.

```
[Hermes Cron]
├── Goal: "Daily Telegram Post"      → cron: 0 9 * * *
├── Goal: "Trend Monitoring"         → cron: 0 */6 * * *
├── Goal: "Weekly Report"            → cron: 0 10 * * 1
└── Goal: "Video Generation"         → cron: 0 14 * * *
      │
      ▼
[Hermes Kanban] — создает карточки задач
      ↓
[DCv3 Workers через Skills]
```

**Задачи:**
1. Перенести задачи из `config/autonomous_schedule.json` в Hermes Cron
2. Создать `dcv3-scheduler` skill
3. Интегрировать PipelineExecutor с Hermes Goal system
4. Настроить уведомления в Telegram/Discord о выполнении

**Критерий готовности:**
- Автономные задачи работают через Hermes Cron
- Можно добавлять/менять расписание через CLI/API
- Quality thresholds сохранены

**Бизнес-ценность:** Надежнее scheduling, проще управление

---

### ЭТАП 4: Skills Migration — Content & Intel (недели 8-10)

**Цель:** Обернуть content_worker и intel_worker в Hermes Skills.

```
~/.hermes/skills/
├── dcv3-content/
│   ├── skill.py              # Основной интерфейс
│   ├── tov_profile.yaml      # Tone of Voice
│   ├── prompts/              # Системные промпты
│   └── quality_thresholds/   # Пороги качества
│
└── dcv3-intel/
    ├── skill.py
    ├── sources.json          # Источники данных
    └── templates/            # Шаблоны отчетов
```

**Задачи:**
1. Создать `dcv3-content` skill с методами:
   - `create_post(topic, style, platform)`
   - `create_script(topic, duration)`
   - `check_quality(content, type)`
2. Создать `dcv3-intel` skill с методами:
   - `research_competitors(niche)`
   - `monitor_trends(keywords)`
   - `generate_report(type)`
3. Интегрировать quality_control.py в skill
4. Настроить self-improvement: скиллы учатся на метриках

**Критерий готовности:**
- `hermes skill run dcv3-content "Создай пост про AI"` работает
- Quality score сохраняется и отображается
- Скиллы улучшаются после каждого использования

**Бизнес-ценность:** Content & intel начинают самообучаться

---

### ЭТАП 5: Skills Migration — Video (недели 11-13)

**Цель:** Обернуть video pipeline в Hermes Skill (самый критичный!).

```
~/.hermes/skills/dcv3-video/
├── skill.py                  # Hermes Skill interface
├── pipeline/
│   ├── pro_editor_v9.py      # ← текущий файл, минимальные изменения
│   ├── blender_ai.py         # Blender VSE workflow
│   ├── ffmpeg_assembler.py   # FFmpeg assembly
│   └── sound_library.py      # Аудио-активы
├── templates/                # Шаблоны видео
├── assets/                   # Кэш ассетов
└── config.yaml               # Настройки pipeline
```

**Задачи:**
1. Создать `dcv3-video` skill без изменения `pro_editor_v9.py` логики
2. Skill-интерфейс:
   - `generate_shorts(topic, style, duration)`
   - `generate_reel(topic, style)`
   - `edit_video(source, edits)`
3. Интегрировать asset_downloader, asset_cache
4. Добавить self-improvement на основе:
   - View count (если публикуется)
   - Quality score
   - Render time optimization

**Критерий готовности:**
- Видео генерируется через `hermes skill run dcv3-video`
- Качество видео не ниже текущего
- Render time не дольше текущего

**Бизнес-ценность:** Video pipeline становится portable + self-improving

---

### ЭТАП 6: Kanban Orchestration (недели 14-16)

**Цель:** Включить визуальное управление задачами через Kanban.

```
Hermes Kanban Dashboard (127.0.0.1:9118/kanban)
┌─────────────────────────────────────────────────────────────┐
│ Board: "DCv3 Content Factory"                               │
├──────────┬──────────┬──────────────┬──────────┬─────────────┤
│  TRIAGE  │  TODO    │ IN PROGRESS  │ BLOCKED  │    DONE     │
├──────────┼──────────┼──────────────┼──────────┼─────────────┤
│ Post #1  │ Script#2 │ Video #5     │ Render#3 │ Post #42    │
│ Post #2  │          │ (dcv3-video) │ (ffmpeg) │ ✓ Published │
│          │          │              │          │             │
└──────────┴──────────┴──────────────┴──────────┴─────────────┘
```

**Задачи:**
1. Настроить Hermes Kanban boards:
   - "Content Pipeline"
   - "Video Production"
   - "Intel & Research"
2. Интегрировать goal creation из Telegram/Discord команд
3. Настроить parallel execution через DeepSwarm 2.0
4. Добавить notifications в мессенджеры при смене статуса

**Критерий готовности:**
- Можно создать задачу в Telegram, она появляется на Kanban
- Агенты автоматически берут задачи из TODO
- Можно отслеживать прогресс в реальном времени

**Бизнес-ценность:** Визуальный контроль, параллельная работа, масштабирование

---

### ЭТАП 7: Dev & Sell + Polishing (недели 17-18)

**Цель:** Завершить миграцию оставшихся воркеров и финальная полировка.

**Задачи:**
1. `dcv3-dev` skill: code generation, deployment, git automation
2. `dcv3-sell` skill: funnels, email campaigns, client responses
3. Интеграция `hermes claw migrate` — если нужно мигрировать с OpenClaw (не наш случай, но полезно знать)
4. Performance optimization
5. Security audit (container hardening, command scanner)

**Критерий готовности:**
- Все 5 воркеров работают как Hermes Skills
- Система проходит нагрузочное тестирование
- Документация обновлена

---

### ЭТАП 8: Serverless Deployment (недели 19-20)

**Цель:** Оптимизировать инфраструктуру через serverless.

```
[User Request]
      ↓
[Modal/Daytona] — контейнер просыпается
      ↓
[Hermes Agent] — обработка
      ↓
[DCv3 Skills] — выполнение
      ↓
[Result] → [User]
      ↓
[Container hibernates] — $0
```

**Задачи:**
1. Настроить Hermes на Modal или Daytona backend
2. Оптимизировать cold start time (критично для user experience)
3. Настроить auto-scaling для parallel video generation
4. Мониторинг: cost tracking, performance metrics

**Критерий готовности:**
- Система работает на $5-20/месяц вместо $50-100
- Cold start < 10 секунд
- Auto-scaling работает под нагрузкой

---

## 4. Матрица зависимостей этапов

```
Этап 0 (Foundation)
    │
    ├──→ Этап 1 (Gateway) ──┐
    │                        │
    ├──→ Этап 2 (Memory) ────┤
    │                        │
    └──→ Этап 3 (Cron) ──────┤
                             │
        Этап 4 (Content) ←───┤
        Этап 5 (Video)   ←───┤ (могут идти параллельно)
        Этап 6 (Intel)   ←───┤
                             │
        Этап 7 (Kanban)  ←───┘
                             │
        Этап 8 (Dev/Sell) ←──┘
                             │
        Этап 9 (Serverless) ←┘
```

**Ключевое правило:** Этапы 4-6 (Skills Migration) могут выполняться **параллельно** разными разработчиками, потому что они изолированы друг от друга.

---

## 5. Точки невозврата (Point of No Return)

| Этап | Точка невозврата | Что делать, если откатываемся |
|------|------------------|------------------------------|
| 1 (Gateway) | Переключение production Telegram бота | Старый бот всегда готов, fallback за 5 минут |
| 2 (Memory) | Удаление старой векторной БД | Держать backup 30 дней, dual-write mode |
| 3 (Cron) | Отключение autonomous_loop.py | Старый loop остается как модуль, можно вернуть |
| 5 (Video) | Изменение pro_editor_v9.py | **НЕ трогаем оригинал**, skill вызывает его как есть |
| 7 (Kanban) | Полное переключение на goal-based | Fallback на command-based через `/legacy` команду |

**Золотое правило:** Никогда не изменяем оригинальные файлы DCv3 до этапа 8. Все интеграции — через обертки (wrappers) и прокси.

---

## 6. Технический стек каждого этапа

### Этап 0-1
```yaml
hermes:
  image: nousresearch/hermes-agent:latest
  ports:
    - "9118:9118"  # Dashboard
  volumes:
    - ./hermes/skills:/root/.hermes/skills
    - ./hermes/config:/root/.hermes/config
  environment:
    - HERMES_MODEL=openrouter:kimi/k2.6
    - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
    - DISCORD_BOT_TOKEN=${DISCORD_BOT_TOKEN}
```

### Этап 2-3
```python
# core/hermes_memory_bridge.py
import hermes_client  # hypothetical

class HermesMemoryBridge:
    def __init__(self):
        self.hermes = hermes_client.connect("localhost:9118")
        self.vector_db = load_vector_db()  # legacy
    
    async def search(self, query: str, k: int = 5):
        # Dual search: FTS5 + Vector
        fts_results = await self.hermes.memory.fts_search(query, k)
        vec_results = await self.vector_db.search(query, k)
        return merge_results(fts_results, vec_results)
```

### Этап 4-5 (Skill Template)
```python
# ~/.hermes/skills/dcv3-video/skill.py
from hermes.skill import Skill, skill_method

class DCv3VideoSkill(Skill):
    name = "dcv3-video"
    description = "Professional video generation pipeline"
    
    def __init__(self):
        # Импортируем текущий код БЕЗ изменений
        import sys
        sys.path.insert(0, "/app/digital-clone-v3")
        from pro_editor_v9 import generate_video
        self._generate = generate_video
    
    @skill_method
    async def generate_shorts(self, topic: str, duration: int = 30):
        """Generate a short video."""
        result = await self._generate(
            topic=topic, 
            duration=duration,
            style="shorts"
        )
        # Self-improvement: save metrics
        await self.learn_from_result(result)
        return result
```

---

## 7. Оценка ресурсов

### Время (при 1 разработчике)

| Этап | Недели | Сложность |
|------|--------|-----------|
| 0 | 1 | Low |
| 1 | 2 | Medium |
| 2 | 2 | Medium |
| 3 | 2 | Medium |
| 4 | 3 | High |
| 5 | 3 | **Very High** |
| 6 | 3 | High |
| 7 | 2 | Medium |
| 8 | 2 | Medium |
| **Итого** | **20 недель** | |

### Время (при 2 разработчиках, параллельно)

```
Разработчик A: Этапы 0→1→2→3→7→8 (инфраструктура, gateway, cron, polishing)
Разработчик B: Этапы 0→4→5→6 (skills: content, video, intel)

Результат: 12-14 недель вместо 20
```

### Стоимость

| Период | Инфраструктура | Разработка | Итого |
|--------|---------------|------------|-------|
| Текущий | ~$50-100/мес | — | $50-100/мес |
| Этапы 0-7 | ~$50-100/мес | 20 недель × rate | $50-100/мес + dev cost |
| Этап 8+ | ~$5-20/мес (serverless) | — | **$5-20/мес** |

---

## 8. Риски и митигация

| Риск | Вероятность | Влияние | Митигация |
|------|------------|---------|-----------|
| Hermes прекращает развиваться | Низкая | Высокое | MIT license, можно форкнуть; код DCv3 остается отдельным |
| Video pipeline regression | Средняя | Критичное | Не трогаем pro_editor_v9.py, только обертка |
| Performance degradation | Средняя | Высокое | Бенчмарки перед и после каждого этапа |
| Memory migration data loss | Низкая | Критичное | Dual-write + backup на 30 дней |
| LLM costs вырастают | Средняя | Среднее | Model routing (дешевые модели для простых задач) |
| Hermes API breaking changes | Средняя | Высокое | Pin version, read changelog перед update |

---

## 9. Критерии успеха интеграции

### Технические KPI

| Метрика | Бейслайн (сейчас) | Цель (после) |
|---------|-------------------|--------------|
| Поддерживаемые платформы | 1 (Telegram) | 3+ (Telegram, Discord, Slack) |
| Время деплоя | 30 мин (Docker) | 5 мин (serverless) |
| Инфраструктурные затраты | $50-100/мес | $5-20/мес |
| Время добавления новой фичи | 2-3 дня | 2-3 часа (skill creation) |
| Поиск по истории | Векторный (медленно) | FTS5 (мгновенно) |
| Параллельные видео | 1 | 3-5 |

### Бизнес KPI

| Метрика | Бейслайн | Цель |
|---------|----------|------|
| Охват аудитории | Telegram only | Telegram + Discord + Slack |
| Quality score (content) | 0.75 | 0.85 (self-improvement) |
| Time-to-content | 2 часа | 30 минут (parallelization) |
| Ручное вмешательство | 80% задач | 20% задач (autonomy) |

---

## 10. Заключение

**Мы проектируем целиком — строим поэтапно.**

Target Architecture описывает конечное состояние, где:
- Hermes управляет оркестрацией, памятью, messaging, cron
- DCv3 существует как набор специализированных skills (video, content, intel, dev, sell)
- Каждый skill самообучается и улучшается со временем
- Система работает на serverless инфраструктуре

Но реализация идет **20-недельными этапами**, где каждый этап — это работающая система с возможностью отката.

**Это не "починить потом" — это "строить мосты, не сжигая старые".**

---

## Appendix A: Команды для старта

```bash
# Этап 0: Foundation
mkdir -p hermes/skills hermes/config
wget https://raw.githubusercontent.com/NousResearch/hermes-agent/main/docker-compose.yml -O hermes/docker-compose.yml

# Этап 1: Gateway
cp .env hermes/.env
docker-compose -f hermes/docker-compose.yml up -d
hermes gateway setup
hermes gateway start

# Этап 4: First skill
hermes skill create dcv3-content --template python
# Копируем content_worker.py в hermes/skills/dcv3-content/
hermes skill install dcv3-content
hermes skill run dcv3-content "Создай пост про AI"
```

## Appendix B: Fallback Plan

Если на любом этапе что-то идет не так:

```bash
# Мгновенный откат к старой системе
hermes gateway stop
docker-compose -f hermes/docker-compose.yml down

# Запускаем старую систему
python main.py

# Время восстановления: < 2 минуты
```
