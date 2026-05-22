# Настройка Telegram бота через Hermes

## Что уже сделано

Hermes настроен для работы с Telegram. Конфигурация находится в `~/.hermes/config.yaml`.

## Шаг 1: Получить токен у @BotFather

1. Открой Telegram, найди контакт **@BotFather**
2. Напиши `/start`, затем `/newbot`
3. Укажи имя бота (например, `Digital Clone Jarvis`)
4. Укажи username (латиницей, с окончанием `bot`, например `digital_clone_jarvis_bot`)
5. BotFather выдаст токен: `123456789:ABCdef...`

## Шаг 2: Добавить токен в .env

Открой файл `C:\Users\mafio\.hermes\.env` и добавь строку:

```bash
TELEGRAM_BOT_TOKEN=123456789:ABCdef...
```

## Шаг 3: Запустить бота

Открой PowerShell или CMD и выполни:

```powershell
hermes gateway
```

Hermes запустит Telegram бота. Он будет отвечать на сообщения используя твой Kimi ключ.

## Как остановить бота

Нажми `Ctrl+C` в окне, где запущен `hermes gateway`.

## Команды бота

- Напиши боту любой текст — он ответит через AI
- `/reset` — сбросить диалог
- `/new` — начать новую сессию
