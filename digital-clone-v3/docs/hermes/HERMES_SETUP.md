# Настройка Hermes Agent с Kimi API

## Что сделано

Hermes Agent теперь работает с твоим Kimi subscription ключом (`sk-kimi-...`) через официальный endpoint `api.kimi.com/coding/v1`.

## Проблемы, которые решены

1. **Provider name**: Hermes использует `kimi-coding` (не `kimi` и не `custom`)
2. **Env vars**: Hermes ожидает `KIMI_API_KEY`, а не `OPENAI_API_KEY`
3. **Config location**: Hermes читает конфиг из `~/.hermes/config.yaml` (не из `AppData/Local/hermes/`)
4. **API mode**: Hermes автоматически детектил `anthropic_messages` для `api.kimi.com`, но Kimi Coding API — это OpenAI-compatible endpoint. Пришлось явно указать `api_mode: chat_completions`

## Файлы конфигурации

### `~/.hermes/.env`

```bash
# Hermes native Kimi provider
KIMI_API_KEY=sk-kimi-...
KIMI_BASE_URL=https://api.kimi.com/coding/v1
KIMI_MODEL=kimi-for-coding

# Fallback для custom endpoint
OPENAI_API_KEY=sk-kimi-...
OPENAI_BASE_URL=https://api.kimi.com/coding/v1

DEFAULT_PROVIDER=kimi
HERMES_MODEL=kimi-for-coding
```

### `~/.hermes/config.yaml`

```yaml
model:
  default: kimi-for-coding
  provider: kimi-coding
  api_mode: chat_completions
```

## Как проверить, что работает

```bash
# Проверка здоровья
hermes doctor

# Одиночный запрос (oneshot)
hermes -z "Скажи Привет"

# Интерактивный чат
hermes chat
```

## Интеграция с Digital Clone v3

Мост для интеграции создан: `digital-clone-v3/core/hermes_bridge.py`

Он определяет интерфейс, через который DCv3 будет общаться с Hermes:
- `send_message(platform, text)` — отправка сообщений
- `query_memory(query)` — поиск в памяти
- `schedule_task(cron_expr, task_data)` — планирование задач
- `register_skill(...)` — регистрация навыков

## Следующие шаги

1. Реализовать вызовы Hermes через `subprocess` или Python API в `hermes_bridge.py`
2. Настроить навыки (skills) для DCv3 в `~/.hermes/skills/`
3. При желании — настроить Telegram/Discord бота через Hermes
