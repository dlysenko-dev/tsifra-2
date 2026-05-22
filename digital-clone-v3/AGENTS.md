# AGENTS.md — Digital Clone v3

> Инструкции для AI-агентов, работающих с кодовой базой Digital Clone v3.
> Этот файл — primary source of truth для стиля, архитектуры и правил проекта.

---

## 1. Общее описание проекта

**Digital Clone v3** — multi-agent AI система с архитектурой OpenManus-style.

- **Оркестратор**: `core/jarvis_v3.py` — распознаёт intent, планирует задачи, роутит на воркеров.
- **5 воркеров**: content, video, dev, intel, sell (`agents/`).
- **LLM Router**: `core/llm_router.py` — fallback-цепочка Kimi → DeepSeek → Groq → Ollama → GLM.
- **MCP Layer**: `core/mcp_layer.py` — 15+ инструментов (browser, file, shell, search, telegram, video gen, image gen, test, git).
- **Autonomous Loop**: `core/autonomous_loop.py` — cron-like планировщик задач.
- **Telegram Bot**: `core/telegram_bot.py` — интерфейс пользователя.
- **Video Pipeline**: `pro_editor_v9.py`, `core/video_creator.py`, `core/video_assembler.py` — генерация шортсов и reels.

Язык проекта: **Python 3.11**. Используется `asyncio`, `dataclasses`, `pydantic`-style валидация.

---

## 2. Стиль кода

### 2.1 Общие правила
- **PEP 8** — единственный accepted style guide.
- **Максимальная длина строки**: 100 символов.
- **Импорты**: группируй по stdlib → third-party → local. Сортируй внутри групп alphabetically.

### 2.2 Аннотации типов
- **Обязательны** для всех публичных функций, методов и атрибутов классов.
- Используй `from __future__ import annotations` в начале каждого модуля для postponed evaluation.
- Для коллекций используй `typing.Dict`, `typing.List`, `typing.Optional` (совместимость).

```python
from __future__ import annotations
from typing import Dict, List, Optional, Any

async def process_task(
    task_id: str,
    params: Dict[str, Any],
    timeout: Optional[int] = None,
) -> Dict[str, Any]:
    ...
```

### 2.3 Docstrings — Google-style
- Каждый модуль, класс и публичный метод обязан иметь docstring.
- Используй **Google-style** (не NumPy, не reStructuredText).

```python
class TaskPlanner:
    """Планировщик задач в стиле OpenManus.

    Разбивает входной запрос на sub-tasks, определяет порядок выполнения
    и выбирает подходящих воркеров.

    Attributes:
        llm_router: Экземпляр LLMRouter для генерации планов.
        max_depth: Максимальная глубина декомпозиции задачи.
    """

    async def plan(self, request: str, context: Dict[str, Any]) -> TaskPlan:
        """Создаёт план выполнения для входного запроса.

        Args:
            request: Текст запроса пользователя.
            context: Контекст предыдущих взаимодействий.

        Returns:
            TaskPlan с декомпозированными шагами.

        Raises:
            PlanningError: Если декомпозиция невозможна.
        """
```

### 2.4 Именование

| Сущность | Стиль | Пример |
|----------|-------|--------|
| Переменные, функции | `snake_case` | `process_task`, `max_retries` |
| Константы | `UPPER_CASE` | `MAX_TIMEOUT`, `DEFAULT_MODEL` |
| Классы | `CamelCase` | `JarvisOrchestrator`, `MCPTool` |
| Приватные методы/атрибуты | `_leading_underscore` | `_internal_cache`, `_validate()` |
| Enum members | `UPPER_CASE` | `IntentType.CONTENT`, `TaskStatus.DONE` |
| Файлы модулей | `snake_case.py` | `jarvis_v3.py`, `llm_router.py` |
| Пакеты (директории) | `snake_case` | `core/`, `agents/`, `tools/` |

---

## 3. Архитектурные паттерны

### 3.1 OpenManus-style Planner
- Запрос → `thought chain` (цепочка мышления) → `action` → `observation`.
- Каждый шаг планирования логируется в `TaskPlan.thoughts: List[ThoughtStep]`.
- Оркестратор НЕ выполняет задачи сам — только роутит на воркеров.

### 3.2 ReAct Loop
- В `core/jarvis_v3.py` реализован ReAct (Reasoning + Acting) цикл:
  1. **Reason**: LLM анализирует задачу и выбирает стратегию.
  2. **Act**: Вызов MCP-инструмента или делегирование воркеру.
  3. **Observe**: Получение результата и обновление контекста.
  4. **Repeat** до достижения цели или `max_iterations`.

### 3.3 MCP Protocol
- Каждый инструмент — это `MCPTool` dataclass с `name`, `description`, `parameters`, `handler`.
- Регистрация через `mcp_layer.register_tool(tool: MCPTool)`.
- Выполнение через `await mcp_layer.execute(tool_name, params)`.
- Real tools (tg_publish_post, shorts_generate и др.) регистрируются отдельно через `mcp.register_real_tools()`.

### 3.4 Worker Pattern
- Каждый воркер наследуется от базового паттерна (контракт: `__init__(llm_router, mcp_layer)` + `execute(task, thought_chain)`).
- Воркер самостоятельно решает, какие MCP-инструменты использовать.
- Воркер возвращает `Dict[str, Any]` с ключами `status`, `result`, `metadata`.

---

## 4. Границы модулей

```
core/           — Ядро системы. НЕ импортирует agents/, tools/, learning/.
                Допустимые импорты: только stdlib + third-party.
                Исключение: core/real_tools.py может использовать agents/ для делегирования.

agents/         — Воркеры (бизнес-логика). Могут импортировать core/ и tools/.
                НЕ должны импортировать друг друга напрямую.

config/         — JSON-конфигурации. НЕ содержит Python-код (кроме чтения).
                Файлы: autonomous_schedule.json, quality_thresholds.json.

tools/          — Утилиты публикации и pipeline. tg_publish.py, shorts_pipeline.py.
                Могут импортировать core/.

templates/      — Шаблоны для генерации (Blender scripts, HTML templates).

learning/       — Данные для self-learning: reference_analysis, etalons, masters.
                НЕ содержит production-код.

output/         — Сгенерированные файлы. НЕ коммитится.

temp/           — Временные файлы. НЕ коммитится.

assets/         — Статические ассеты (шрифты, музыка, видео, SFX).
```

---

## 5. Как работать с кодом

### 5.1 Добавление нового MCP-инструмента

1. В `core/mcp_layer.py` добавь `async def _your_tool_name(self, ...)` как private method.
2. В `MCPLayer._register_default_tools()` зарегистрируй `MCPTool(...)` с `handler=self._your_tool_name`.
3. Обнови `MCPToolType` enum, если нужна новая категория.
4. Добавь тест в `test_mcp_layer.py` (если существует) или создай новый.
5. Обнови `AGENTS.md` — раздел с перечнем инструментов.

### 5.2 Создание нового воркера

1. Создай файл `agents/<name>_worker.py`.
2. Реализуй класс с конструктором `__init__(self, llm_router, mcp_layer)`.
3. Реализуй `async def execute(self, task, thought_chain) -> Dict[str, Any]`.
4. Зарегистрируй в `main.py` в секции `Registering Workers`.
5. Добавь соответствующий `IntentType` в `core/jarvis_v3.py`, если нужен новый intent.

### 5.3 Изменение конфигурации

- `config/autonomous_schedule.json` — cron-задачи для AutonomousLoop.
- `config/quality_thresholds.json` — пороги качества для QualityChecker.
- `.env` — API-ключи и секреты. **НИКОГДА не коммить `.env`.**

---

## 6. Конвенции коммитов (Conventional Commits)

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Типы:**

| Тип | Когда использовать |
|-----|-------------------|
| `feat:` | Новая функциональность |
| `fix:` | Исправление бага |
| `docs:` | Изменения только в документации |
| `refactor:` | Рефакторинг без изменения поведения |
| `test:` | Добавление/исправление тестов |
| `chore:` | Обновление зависимостей, CI, конфигов |
| `perf:` | Оптимизация производительности |

**Примеры:**
```
feat(mcp): добавить инструмент google_search
fix(video): исправить расчёт duration для шортсов
docs: обновить AGENTS.md — добавить раздел про security
refactor(jarvis): вынести intent classification в отдельный метод
test(router): добавить тест fallback на Groq
```

---

## 7. Безопасность

### 7.1 Критические правила
- **НИКОГДА не коммить `.env`** — он содержит API-ключи. Используй `.env.example` как шаблон.
- **НИКОГДА не коммить `output/` и `temp/`** — они уже в `.gitignore`.
- **НИКОГДА не логируй API-ключи** — даже partially (первые 10 символов допустимы только для debug).
- **Проверяй импорты перед коммитом** — убедись, что все импортируемые модули существуют в репозитории.

### 7.2 Shell execution
- MCP-инструмент `_shell_exec` использует sandbox с блокировкой опасных команд.
- Перед добавлением нового shell-команды проверь её на idempotency.
- Не позволяй LLM формировать shell-команды напрямую — всегда используй whitelist.

### 7.3 Code execution
- `_exec_python` запускает код в restricted environment.
- Не импортируй `os`, `subprocess`, `sys` внутри exec_python без валидации.

---

## 8. Технический стек

| Компонент | Технология | Версия |
|-----------|-----------|--------|
| Python | CPython | 3.11+ |
| Async | asyncio | stdlib |
| LLM Client | openai (OpenAI-compatible) | >=1.0.0 |
| HTTP | aiohttp | >=3.9.0 |
| Telegram | python-telegram-bot | >=20.0 |
| Video | moviepy, ffmpeg | >=1.0.3 |
| Web | playwright | >=1.40.0 |
| TTS | gTTS | >=2.4.0 |
| Data | pydantic, pyyaml | >=2.0, >=6.0 |
| Testing | pytest | >=7.4.0 |
| Security | bandit | >=1.7.0 |

---

## 9. Известные проблемы и ограничения

- `skills/` директория импортируется в `main.py`, но **не существует** в репозитории. Это баг — требуется создание модуля или удаление импортов.
- `tests/`, `prompts/`, `memory/` директории указаны в README, но **не существуют**.
- `core/intent_classifier.py`, `core/memory.py`, `core/config.py` — указаны в README, но **не существуют** (функциональность встроена в `jarvis_v3.py`).
- Docker `CMD` указывает на `python -m core.jarvis_v3`, но entry point проекта — `main.py`.
- `Makefile` содержит `pytest tests/ -v`, но директории `tests/` нет.
