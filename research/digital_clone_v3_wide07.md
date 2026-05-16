# Исследование: Безопасность и надёжность автономного AI-агента (Digital Clone v3)

> **Контекст**: Агент работает 24/7, публикует контент, общается с клиентами, принимает деньги. Если агент сделает что-то не так — позор и потеря репутации.
>
> **Дата исследования**: 2025-07-09
> **Поисков проведено**: 12 (60+ источников)

---

## Содержание

1. [Sandbox для AI-агентов](#1-sandbox-для-ai-агентов)
2. [Human-in-the-loop](#2-human-in-the-loop)
3. [Content Moderation](#3-content-moderation)
4. [Monitoring агентов](#4-monitoring-агентов)
5. [Alerting](#5-alerting)
6. [Recovery / Self-healing](#6-recovery--self-healing)
7. [Backup](#7-backup)
8. [API Key Rotation](#8-api-key-rotation)
9. [Audit Trail](#9-audit-trail)
10. [Rate Limiting](#10-rate-limiting)
11. [Рекомендуемый Security Checklist](#11-рекомендуемый-security-checklist)
12. [Итоговые рекомендации](#12-итоговые-рекомендации)

---

## 1. Sandbox для AI-агентов

### Почему Docker-контейнеров недостаточно

Стандартные Docker-контейнеры разделяют хост-ядро Linux. Уязвимость ядра или ошибка конфигурации может позволить "побег из контейнера" (container escape), дав злоумышленнику доступ к хосту и другим контейнерам. AI-агенты генерируют непредсказуемый код, который может эксплуатировать эти уязвимости [^246^].

### Технологии изоляции (сравнение)

| Технология | Уровень изоляции | Время загрузки | Сила безопасности | Лучше всего для |
|---|---|---|---|---|
| **Docker** ( hardened ) | Процесс (shared kernel) | 1-5 сек | Средняя | Доверенные внутренние скрипты |
| **gVisor** | Перехват syscall | Миллисекунды | Высокая | Multi-tenant SaaS, CI/CD |
| **Firecracker microVM** | Аппаратная (KVM) | ~125 мс | Очень высокая | Недоверенный код, serverless |
| **Kata Containers** | Аппаратная (VMM) | ~200 мс | Очень высокая | Regulated industries, K8s [^246^][^247^] |

### Рекомендации для Digital Clone

**Для продакшн-агента, работающего с API-ключами и деньгами:**

1. **Использовать Firecracker microVM или Kata Containers** для изоляции кода, который агент может сгенерировать или выполнить [^246^]. Аппаратная граница предотвращает целые классы атак на уровне ядра.

2. **Если microVM невозможен** — использовать **gVisor** как промежуточный вариант. Добавить в Kubernetes Pod:
   ```yaml
   runtimeClassName: gvisor
   ```
   Это включает перехват системных вызовов в userspace-ядре [^249^].

3. **Hardened Docker** (минимальный вариант):
   ```yaml
   securityContext:
     readOnlyRootFilesystem: true
     allowPrivilegeEscalation: false
     runAsNonRoot: true
   ```
   - Не-root пользователь внутри контейнера [^249^]
   - Read-only корневая файловая система
   - seccomp-профили и AppArmor
   - Ограничение capabilities [^247^]

4. **Практика defense-in-depth**: комбинировать sandboxing + monitoring + approval gates + signed artifacts [^246^].

5. **Сетевые ограничения**: Network Policy — разрешить только необходимые API (Telegram, LLM-провайдер, платёжная система). Всё остальное — `DENY` [^249^].

> **Консенсус сообщества**: Для продакшн-агентов, выполняющих недоверенный код (сгенерированный LLM), Docker-контейнеров недостаточно. Нужна аппаратная изоляция [^247^].

---

## 2. Human-in-the-loop (HITL)

### Когда нужен HITL

Задайте себе вопросы [^240^]:
- **Решение необратимо?** Финансовые транзакции, удаление данных, изменение конфигурации — требуют human approval.
- **Агент имеет write-доступ к продакшн-системам?** Модификация БД, деплой кода — требуют human gates.
- **Последствия значимы для клиентов или регуляторов?** EU AI Act, GDPR требуют документированного человеческого надзора.
- **Задача этически чувствительна?** Сценарии вне тренировочной выборки агента требуют человеческого суждения.

### Архитектурные паттерны

**1. Синхронное одобрение (для необратимых действий)**
- Система идентифицирует действие, требующее подтверждения
- Оркестратор приостанавливает выполнение и сериализует состояние
- Workflow возвращает статус с ID вызова
- Человек рассматривает через UI с полным контекстом
- Сессия возобновляется с результатом approval/rejection [^243^]

**2. Confidence-based escalation**
- Использовать пороги уверенности, risk scores, business rules
- Target escalation rate: **10-15%** случаев [^240^]
- Слишком много escalation — убивает эффективность; слишком мало — создаёт риск

**3. Разделение планирования и исполнения**
- LLM генерирует планы действий высокого уровня
- Операторы рецензируют планы на feasibility
- Нижнеуровневые агенты исполняют approved планы с ограниченной автономией [^243^]

### Лучшие практики HITL

1. **Дизайн для людей первым делом** — интуитивные дашборды, контекстные summaries, простые approval workflows. Если UI неудобный, рецензенты становятся "резиновыми штампами" [^240^].

2. **Bake governance into architecture** — audit trails, decision logs, role-based access должны быть встроены в workflow orchestration, не "прикручены сверху" [^240^].

3. **Обучение рецензентов** — train reviewers to systematically question AI outputs. Ротация рецензентов для предотвращения automation complacency [^240^].

4. **Измерение KPI**:
   - Time-to-decision
   - Error rates
   - Escalation rates
   - Reviewer workload [^240^]

5. **Прогрессивная автономность** — начинайте с HITL на всё, переходите к human-on-the-loop по мере накопления данных о надёжности [^240^].

> **Фундаментальный принцип**: HITL — это не ограничение возможностей агента. Это то, что делает безопасным давать агенту больше возможностей [^253^].

---

## 3. Content Moderation

### Проблема

Агент публикует контент. Если контент будет токсичным, оскорбительным или неприемлемым — репутационные потери.

### Инструменты и их сравнение

| Инструмент | Текст | Изображения | Видео | Стоимость | Особенности |
|---|---|---|---|---|---|
| **Perspective API** (Google) | ✅ | ❌ | ❌ | **Бесплатно** | Закрывается **31 декабря 2026** [^244^] |
| **OpenAI Moderation API** | ✅ | ✅ (partial) | ❌ | **Бесплатно** | Интегрирован с OpenAI workflows [^323^] |
| **Detoxify** (open-source) | ✅ | ❌ | ❌ | Бесплатно | pip install, локальный запуск [^241^] |
| **Azure AI Content Safety** | ✅ | ✅ | Preview | $1/1K | Severity levels, prompt shields [^323^] |
| **Amazon Rekognition** | ❌ | ✅ | ✅ | $1/1K | AWS-нативный, image/video [^323^] |
| **EvoLink Moderation** | ✅ | ✅ | ❌ | $1/1K | OpenAI-compatible endpoint [^323^] |

### Ключевые выводы

1. **Perspective API закрывается 31 декабря 2026** — нужен план миграции [^244^].

2. **Detoxify** показывает более высокую уверенность в определении toxicity (0.95 vs 0.8 у Perspective), но Perspective лучше чувствителен к атрибутам токсичного текста [^241^].

3. **OpenAI Moderation API** — лучший бесплатный выбор для text moderation, если вы уже используете OpenAI. Простой REST API, мгновенная обработка [^323^].

4. **Многоуровневая стратегия**:
   - **Уровень 1**: Локальный фильтр (Detoxify) — быстро, без задержек сети
   - **Уровень 2**: API-фильтр (OpenAI Moderation API) — дополнительная проверка
   - **Уровень 3**: Custom rules — специфичные для домена (финансовые термины, специфика бизнеса)
   - **Уровень 4**: Human review для edge cases

### Рекомендация для Digital Clone

Использовать **OpenAI Moderation API** (бесплатно, встроено в экосистему) + **Detoxify** как fallback для локальной быстрой проверки. Настроить пороги:
- `toxicity > 0.7` — блокировка публикации
- `toxicity 0.3-0.7` — отправка на human review
- `toxicity < 0.3` — публикация разрешена [^252^]

---

## 4. Monitoring агентов

### Стек: Prometheus + Grafana

**Prometheus** — сбор метрик, **Grafana** — визуализация. Это стандарт де-факто для мониторинга production-систем [^245^].

### Какие метрики собирать

| Категория | Метрики |
|---|---|
| **Здоровье агента** | Uptime, heartbeat, last activity timestamp |
| **API-вызовы** | Количество запросов к LLM, latency (p50/p95/p99), error rate |
| **Токены** | Input/output tokens per request, tokens per minute, cost per session |
| **Telegram** | Messages sent/received, rate limit hits (429), queue depth |
| **Бизнес-метрики** | Posts published, revenue processed, customer interactions |
| **Безопасность** | Failed auth attempts, policy violations, anomalous behavior [^285^] |

### Настройка Prometheus

```yaml
# prometheus.yml
global:
  scrape_interval: 15s  # для критических метрик
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'digital-clone-agent'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: /metrics
```

**Best practices** [^245^]:
- Scrape intervals: 5-15 сек для динамических метрик, 30-60 сек для менее критичных
- Избегать high-cardinality labels (user IDs) — агрегировать по endpoint/status code
- Recording rules для предвычисления частых запросов

### Health check endpoint

```python
@app.get("/health")
async def health_check():
    checks = {
        "telegram": check_telegram_connection(),
        "database": check_db_connection(),
        "llm_api": check_llm_api_access(),
        "disk_space": check_disk_space(),
    }
    if all(checks.values()):
        return {"status": "healthy", "checks": checks}
    return JSONResponse(
        status_code=503,
        content={"status": "unhealthy", "checks": checks}
    )
```

### Grafana Dashboard

Ключевые панели:
1. **Overview**: red/yellow/green статус всех компонентов
2. **Agent Activity**: сообщения, посты, взаимодействия
3. **LLM Usage**: token consumption, latency, cost tracking
4. **Error Tracking**: 429 errors, failed requests, exceptions
5. **Security Events**: policy violations, anomalous actions [^245^]

---

## 5. Alerting

### Почему это критично

Агент работает 24/7. Если он упал в 3 часа ночи — вы должны узнать об этом немедленно.

### Варианты оповещений

| Сервис | Стоимость | Задержка | Лучше всего для |
|---|---|---|---|
| **Telegram Bot** | Бесплатно | < 1 сек | Быстрые алерты для маленьких команд |
| **PagerDuty** | $21/мес (Solo) | < 5 сек | On-call rotation, escalation |
| **Email** | Бесплатно | 1-5 мин | Некритичные уведомления |
| **Slack webhook** | Бесплатно | < 1 сек | Командные каналы |

### Рекомендация: Telegram Bot для alerting

Для одного агента/небольшой команды — **Telegram Bot** — оптимальный бесплатный вариант.

**Интеграция с Prometheus Alertmanager** [^334^][^335^][^337^]:

```yaml
# alertmanager.yml
route:
  group_by: ['alertname']
  group_wait: 10s
  receiver: 'telegram'

receivers:
  - name: 'telegram'
    webhook_configs:
      - url: 'http://localhost:8080/alert'  # webhook receiver
        send_resolved: true
```

**Telegram webhook receiver** [^334^]:
- Существуют готовые решения: `alertmanager-webhook` (Python), `prometheus-telegram-alert` (Java/Spring Boot)
- Конфигурация: bot token + chat_id
- Поддержка severity levels: warning → один chat, critical → другой chat

**Какие события алертить**:
- Агент не отвечает на health check > 2 минуты
- Error rate > 5% за 5 минут
- Queue depth > 100 сообщений
- Rate limit hits > 10 за минуту
- Необъяснимый скачок token usage
- Попытка агента выполнить запрещённое действие

### Код простого Telegram алерта (Python)

```python
import asyncio
import logging
from telegram import Bot

logger = logging.getLogger(__name__)

class TelegramAlerter:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot = Bot(token=bot_token)
        self.chat_id = chat_id
    
    async def alert(self, severity: str, message: str):
        emoji = {"critical": "🔴", "warning": "🟡", "info": "🟢"}
        text = f"{emoji.get(severity, '⚪')} *{severity.upper()}*\n{message}"
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=text,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Failed to send alert: {e}")
    
    async def critical(self, message: str):
        await self.alert("critical", message)
    
    async def warning(self, message: str):
        await self.alert("warning", message)
```

---

## 6. Recovery / Self-healing

### Принцип: MAPE-K loop

Self-healing агенты вдохновлены autonomic computing [^289^]:
- **Monitor** — собирать telemetry и логи
- **Analyze** — детектировать аномалии
- **Plan** — решить корректирующее действие
- **Execute** — выполнить (перезапуск, очистка кэша, rollback)
- **Knowledge** — исторические данные и правила

### Варианты auto-restart

| Инструмент | Сложность | Auto-restart | Мониторинг | Лучше всего для |
|---|---|---|---|---|
| **systemd** | Средняя | ✅ | System logs | Production Linux-серверы |
| **Docker `--restart`** | Низкая | ✅ | Docker logs | Контейнеризованные деплои |
| **PM2** | Низкая | ✅ | Встроенный | Node.js/Python приложения |
| **Kubernetes** | Высокая | ✅ (livenessProbe) | Полный | Масштабируемые деплои |
| **Supervisor** | Низкая | ✅ | Веб-интерфейс | Простые Python-скрипты |

### Рекомендация: systemd (для production Linux)

```ini
# /etc/systemd/system/digital-clone.service
[Unit]
Description=Digital Clone AI Agent
After=network.target

[Service]
Type=simple
User=digitalclone
Group=digitalclone
WorkingDirectory=/opt/digital-clone
ExecStart=/opt/digital-clone/venv/bin/python main.py
Restart=on-failure
RestartSec=5
StartLimitInterval=60
StartLimitBurst=3

# Health check
ExecStartPost=/bin/sleep 5
ExecCondition=/usr/bin/curl -f http://localhost:8000/health

# Resource limits
MemoryLimit=512M
CPUQuota=80%

# Graceful shutdown
TimeoutStopSec=30
KillSignal=SIGTERM

[Install]
WantedBy=multi-user.target
```

**Команды управления**:
```bash
sudo systemctl enable digital-clone    # автозапуск
sudo systemctl start digital-clone     # запуск
sudo systemctl status digital-clone    # статус
sudo journalctl -u digital-clone -f    # логи
```

### Docker restart policy

```yaml
# docker-compose.yml
services:
  agent:
    image: digital-clone:latest
    restart: unless-stopped  # перезапускать всегда, кроме явного stop
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

### Health check best practices [^283^]

1. **Liveness probe** — "приложение работает?" → перезапуск если нет
2. **Readiness probe** — "приложение гово обслуживать трафик?" → не маршрутизировать трафик если нет
3. Проверять критические зависимости: БД, внешние API, дисковое пространство
4. Тестировать failure scenarios — симулировать crash, resource exhaustion

### Graceful shutdown

```python
import signal
import sys
import asyncio

async def shutdown(signal_num, loop):
    logger.info(f"Received signal {signal_num}, shutting down...")
    # Очистка: закрыть соединения, сохранить состояние
    await save_state()
    await close_connections()
    loop.stop()

def setup_signal_handlers(loop):
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, 
            lambda s=sig: asyncio.create_task(shutdown(s, loop)))
```

---

## 7. Backup

### Стратегия резервного копирования SQLite

SQLite — WAL (Write-Ahead Logging) режим позволяет делать online-backup без блокировок.

### Варианты хранилища (free tier)

| Хранилище | Бесплатный лимит | Особенности |
|---|---|---|
| **Backblaze B2** | 10 GB бесплатно | Нативное versioning, дешёвое продолжение [^336^] |
| **Google Drive API** | 15 GB (общий) | Хорошая интеграция, но сложная аутентификация |
| **Dropbox** | 2 GB | Простой API, но маленький лимит |
| **AWS S3 Glacier** | 5 GB (12 мес) | Enterprise-grade, но сложный |

### Рекомендация: rclone + systemd timer + Backblaze B2 [^336^]

**1. Установка rclone**:
```bash
curl https://rclone.org/install.sh | sudo bash
rclone config  # настроить Backblaze B2
```

**2. Backup-скрипт**:
```bash
#!/bin/bash
# /opt/digital-clone/scripts/backup.sh
set -euo pipefail

DB_PATH="/opt/digital-clone/data/agent.db"
BACKUP_DIR="/tmp/db-backup"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="agent_${DATE}.db"

# SQLite online backup (WAL-safe)
sqlite3 "${DB_PATH}" ".backup '${BACKUP_DIR}/${BACKUP_FILE}'"

# Сжатие
gzip "${BACKUP_DIR}/${BACKUP_FILE}"

# Upload в облако
rclone copy "${BACKUP_DIR}/${BACKUP_FILE}.gz" b2:agent-backups/

# Очистка старых (> 30 дней)
rclone delete b2:agent-backups/ --min-age 30d

# Очистка локальных tmp файлов
rm -f "${BACKUP_DIR}/${BACKUP_FILE}.gz"

echo "Backup completed: ${BACKUP_FILE}.gz"
```

**3. Systemd timer** (современная замена cron) [^336^]:

```ini
# /etc/systemd/system/agent-backup.service
[Unit]
Description=Digital Clone Database Backup

[Service]
Type=oneshot
User=digitalclone
ExecStart=/opt/digital-clone/scripts/backup.sh

# /etc/systemd/system/agent-backup.timer
[Unit]
Description=Run Digital Clone backup daily

[Timer]
OnCalendar=*-*-* 03:00:00  # в 3 ночи каждый день
Persistent=true            # запустить, если пропущено

[Install]
WantedBy=timers.target
```

```bash
sudo systemctl enable agent-backup.timer
sudo systemctl start agent-backup.timer
sudo systemctl list-timers  # проверить
```

**4. Telegram-уведомление о backup**:
```bash
# Добавить в backup.sh
if [ $? -eq 0 ]; then
    curl -s "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
        -d "chat_id=${CHAT_ID}" \
        -d "text=✅ Backup completed: ${BACKUP_FILE}.gz"
else
    curl -s "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
        -d "chat_id=${CHAT_ID}" \
        -d "text=🔴 Backup FAILED! Check logs immediately."
fi
```

### Backup checklist

- [ ] WAL mode enabled в SQLite (`PRAGMA journal_mode=WAL;`)
- [ ] Ежедневный backup в 3-5 ночи (минимальная нагрузка)
- [ ] Хранение 30 дней бэкапов
- [ ] Тестовое восстановление раз в месяц
- [ ] Мониторинг успешности backup через Telegram
- [ ] Отдельное хранилище (не на том же сервере)

---

## 8. API Key Rotation

### Почему это важно

API-ключи агента — критический вектор атаки. Если ключ скомпрометирован (утёк в лог, попал в Git, перехвачен по сети) — злоумышленник получает контроль над агентом [^280^][^284^].

### Best practices по управлению ключами [^280^][^284^][^286^][^290^]

**1. Никогда не хардкодить ключи**
- ❌ `API_KEY = "sk-abc123"` в коде
- ✅ Получать из environment variables или secrets manager

**2. Use a Secrets Manager**

| Инструмент | Стоимость | Особенности |
|---|---|---|
| **HashiCorp Vault** | Open-source (self-hosted) | Enterprise-grade, dynamic secrets |
| **AWS Secrets Manager** | ~$0.40/secret/мес | Интегрирован с AWS |
| **Doppler** | 5 secrets бесплатно | Удобный UI, CLI интеграция |
| **1Password Secrets Automation** | От $8/мес | Простой, надёжный |
| **Environment variables** | Бесплатно | Минимальный вариант |

**3. Принцип least privilege**
- Отдельные ключи для dev/staging/prod
- Каждый ключ — только нужные permissions
- Read-only ключи где возможно [^284^]

**4. Автоматическая ротация**

Частота ротации [^291^]:
- **High-risk keys** (платёжные API, админ-доступ): каждые 30-90 дней
- **Medium-risk keys**: каждые 90-180 дней
- **Low-risk keys**: каждые 180-365 дней

**Zero-downtime rotation** [^284^]:
1. Сгенерировать новый ключ
2. Обновить приложение (новый ключ)
3. Подождать 5-10 минут (все запросы перешли на новый)
4. Отозвать старый ключ

**5. Мониторинг использования**
- Логировать все API-вызовы (timestamp, endpoint, source IP) [^284^]
- Алерты на аномалии: spike usage, unexpected geolocations
- Интеграция с SIEM для real-time analytics [^294^]

### Emergency response: ключ скомпрометирован [^290^]

```
1. НЕМЕДЛЕННО отозвать ключ (revoke) — не ждать
2. Проверить audit logs на подозрительную активность
3. Сгенерировать новый ключ
4. Обновить все сервисы
5. Найти и устранить root cause (утечка)
```

### Рекомендация для Digital Clone

Для одного агента — использовать **Doppler** (free tier) или **1Password Secrets Automation**:
```bash
# Doppler CLI
doppler secrets upload API_KEY="new_key_here"
doppler secrets upload TELEGRAM_BOT_TOKEN="new_token"

# Агент запускается через
doppler run -- python main.py
```

Ротация: ручная каждые 90 дней с календарным напоминанием. При инциденте — мгновенная ротация.

---

## 9. Audit Trail

### Зачем нужен audit trail

> "Если ваш AI-система не может сказать, кто что изменил, почему было принято решение, или какая версия модели использовалась — она не готова к аудиту" [^292^]

**Проблема**: LLM-агент записывает то, что он *считает*, что сделал — не то, что *доказуемо* выполнил [^281^].

### Решение: Cryptographic receipts

Best practice — независимый gate пишет cryptographic receipt **перед** каждым действием:
- Агент не может влиять на audit trail
- Поддерживает deterministic replay
- Удовлетворяет ISO 42001, EU AI Act Article 12, NIST Measure 2.5 [^281^]

### Что логировать [^288^][^285^][^292^]

Каждое событие должно включать:
```json
{
  "timestamp": "2025-07-09T14:30:00Z",
  "correlation_id": "uuid-v4",
  "agent_id": "digital-clone-v3",
  "session_id": "session-uuid",
  "event_type": "tool_call",  // tool_call, llm_request, decision, action, error
  "tool_name": "telegram_send_message",
  "input": "{masked}",
  "output": "{masked}",
  "decision_rationale": "User requested price quote",
  "model_version": "gpt-4o-2024-08-06",
  "confidence_score": 0.92,
  "human_approved": true,
  "approval_user": "admin@example.com",
  "duration_ms": 450,
  "status": "success",
  "risk_score": 0.1
}
```

### Структура логов [^288^]

**Must have**:
- Timestamp (UTC)
- Agent ID / Session ID / Correlation ID
- Event type (tool_call, llm_request, decision, action, policy_violation)
- Tool name / Action taken
- Input / Output (sanitized — без секретов)
- Model version
- Duration
- Status (success / failure / blocked)
- Risk score / Confidence score

**Security events** (отдельная категория):
- Policy violation attempts
- Authentication failures
- Rate limit triggers
- Anomalous behavior patterns
- Human override decisions

### Best practices [^288^][^285^]

1. **Structured JSON logs** — не plain text. Все логи одного формата для парсинга.

2. **Sanitize sensitive data** — не логировать API keys, пароли, PII. Маскировать или токенизировать.

3. **End-to-end traceability** — correlation ID связывает все шаги workflow воедино.

4. **Immutable logs** — логи должны быть защищены от подделки. Append-only, с контрольными суммами.

5. **Retention policy**:
   - Hot storage (7 дней) — быстрый доступ для дебага
   - Warm storage (90 дней) — для incident investigation
   - Cold storage (1-3 года) — для compliance [^288^]

6. **Регулярный review** — не ждать инцидента. Еженедельный просмотр логов на аномалии.

### Реализация (Python)

```python
import logging
import json
import hashlib
from datetime import datetime, timezone
from typing import Any, Optional

class AuditLogger:
    def __init__(self, log_file: str = "audit.log"):
        self.logger = logging.getLogger("audit")
        handler = logging.FileHandler(log_file)
        handler.setFormatter(logging.Formatter('%(message)s'))
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def log_event(self, event_type: str, tool_name: str, 
                  input_data: Any, output_data: Any,
                  decision_rationale: str = "",
                  confidence: float = 0.0,
                  human_approved: bool = False,
                  duration_ms: int = 0,
                  status: str = "success"):
        
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "correlation_id": get_current_correlation_id(),
            "agent_id": "digital-clone-v3",
            "event_type": event_type,
            "tool_name": tool_name,
            "input_hash": hashlib.sha256(str(input_data).encode()).hexdigest()[:16],
            "output_hash": hashlib.sha256(str(output_data).encode()).hexdigest()[:16],
            "decision_rationale": decision_rationale,
            "confidence": confidence,
            "human_approved": human_approved,
            "duration_ms": duration_ms,
            "status": status,
        }
        
        self.logger.info(json.dumps(event, ensure_ascii=False))
    
    def log_decision(self, rationale: str, confidence: float, 
                     human_approved: bool = False):
        self.log_event(
            event_type="decision",
            tool_name="llm_reasoning",
            input_data="",
            output_data=rationale,
            decision_rationale=rationale,
            confidence=confidence,
            human_approved=human_approved,
        )
    
    def log_policy_violation(self, violation_type: str, details: str):
        self.log_event(
            event_type="policy_violation",
            tool_name="guardrail",
            input_data=details,
            output_data="BLOCKED",
            status="blocked",
        )
```

---

## 10. Rate Limiting

### Telegram Bot API limits [^282^][^295^][^287^]

| Действие | Лимит | Штраф за превышение |
|---|---|---|
| Отправка в **личный чат** | 1 msg/sec | 429 + 1-3 sec retry_after |
| Отправка в **группу** | 20 msg/min | 429 + 5-45 sec retry_after |
| **Глобальный** лимит | 30 msg/sec | Временный бан |
| File upload | 20 MB/sec | 413 |
| getUpdates (polling) | 1 req/sec | 502 |

### LLM API rate limits [^324^][^325^][^330^]

**OpenAI** [^325^]:
- RPM (requests per minute) + TPM (tokens per minute) — **два независимых лимита**
- Tier-based: чем больше потратил — тем выше лимиты
- `retry-after-ms` header в ответе

**Kimi / Moonshot AI** [^330^][^331^]:
- Лимиты зависят от cumulative recharge amount
- Concurrency, RPM, TPM, TPD (tokens per day)
- **Обязательно**: `stream = true` для надёжности
- Retry logic **не опционален** — обрабатывать overloaded, network errors

### Exponential backoff — правильная реализация [^324^][^328^]

```python
import asyncio
import random
import time
from telegram.error import RetryAfter

async def call_with_backoff(func, max_retries=5):
    """Production-grade exponential backoff with jitter."""
    for attempt in range(max_retries):
        try:
            return await func()
        except RetryAfter as e:
            # Telegram говорит точно, сколько ждать
            wait = e.retry_after + random.uniform(0, 1)
            await asyncio.sleep(wait)
        except Exception as e:
            if hasattr(e, 'status') and e.status in (429, 529):
                # 529 = provider overloaded (Anthropic/Kimi)
                base_delay = min(2 ** attempt, 30)  # cap at 30s
                jitter = random.uniform(0, base_delay * 0.3)
                wait = base_delay + jitter
                await asyncio.sleep(wait)
            else:
                raise  # Не retry-ить non-retryable errors
    raise Exception(f"Max retries ({max_retries}) exceeded")
```

### Dual-bucket rate limiter (LLM APIs) [^324^]

```python
import asyncio
import time
from dataclasses import dataclass

@dataclass
class DualBucket:
    """Token bucket с двойным контролем: RPM + TPM."""
    rpm_limit: int
    tpm_limit: int
    request_tokens: float = 0
    token_tokens: float = 0
    last_refill: float = 0
    
    async def acquire(self, estimated_tokens: int):
        while True:
            now = time.monotonic()
            elapsed = now - self.last_refill
            
            # Refill
            self.request_tokens = min(
                self.rpm_limit,
                self.request_tokens + elapsed * (self.rpm_limit / 60)
            )
            self.token_tokens = min(
                self.tpm_limit,
                self.token_tokens + elapsed * (self.tpm_limit / 60)
            )
            self.last_refill = now
            
            if (self.request_tokens >= 1 and 
                self.token_tokens >= estimated_tokens):
                self.request_tokens -= 1
                self.token_tokens -= estimated_tokens
                return
            
            await asyncio.sleep(0.1)
```

### Ключевые anti-patterns [^324^]

- ❌ Retry на 400 errors — это malformed request, retry не поможет
- ❌ Retry без jitter — все серверы retry в одну миллисекунду, recreating spike
- ❌ Shared API key across environments — dev ест prod quota
- ❌ Нет pre-flight token estimation — отправляешь 80K-token запрос без проверки

### Production checklist для rate limiting [^324^]

- [ ] Pre-flight token estimation на каждый запрос
- [ ] Dual bucket (RPM + TPM), distributed если multi-replica
- [ ] Exponential backoff с `retry-after` honored и cap 30s
- [ ] Jitter на каждый retry (минимум 1000ms uniform random)
- [ ] Model-fallback ladder (GPT-4 → GPT-4o-mini) для non-critical путей
- [ ] Separate API keys per environment
- [ ] Anomaly alerts на tokens-per-request и retries-per-success
- [ ] Time-to-quota-exhaustion dashboard

---

## 11. Рекомендуемый Security Checklist

### Источники

Этот checklist основан на:
- **OWASP Top 10 for LLM Applications** v2.0 (2025) [^313^][^318^]
- **NIST 800-53 Rev 5** — Control Mapping for AI Agents [^313^][^317^]
- **OWASP Agentic Skills Top 10** [^318^][^319^]
- **Monday.com AI Agent Security Checklist** [^311^]
- **GitHub: AI Agent Security Audit Checklist** [^314^]

---

### Phase 1: Identity & Access Control

| # | Проверка | Статус |
|---|---|---|
| 1.1 | Каждый агент имеет уникальный ID (не shared credentials) | [ ] |
| 1.2 | Каждый агент имеет назначенного human owner | [ ] |
| 1.3 | Назначен least-privilege доступ (только нужные permissions) | [ ] |
| 1.4 | Read/Write/Admin разделены — нет admin-прав без необходимости | [ ] |
| 1.5 | Регулярный review permissions (раз в месяц) | [ ] |
| 1.6 | Документирован purpose и scope каждого агента | [ ] |

### Phase 2: Sandbox & Isolation

| # | Проверка | Статус |
|---|---|---|
| 2.1 | Агент запускается в sandbox (Docker + hardened / microVM) | [ ] |
| 2.2 | Network Policy ограничивает доступ только необходимым API | [ ] |
| 2.3 | Read-only root filesystem | [ ] |
| 2.4 | Run as non-root user | [ ] |
| 2.5 | seccomp / AppArmor профили настроены | [ ] |
| 2.6 | Нет прямого доступа к production database (через API gateway) | [ ] |

### Phase 3: Human-in-the-Loop

| # | Проверка | Статус |
|---|---|---|
| 3.1 | Все state-changing actions требуют human approval | [ ] |
| 3.2 | Финансовые транзакции — синхронное одобрение | [ ] |
| 3.3 | Удаление данных — синхронное одобрение | [ ] |
| 3.4 | Confidence-based escalation настроен (target 10-15%) | [ ] |
| 3.5 | Чёткие escalation paths определены | [ ] |
| 3.6 | Human reviewer обучен и имеет guidelines | [ ] |

### Phase 4: Content Moderation

| # | Проверка | Статус |
|---|---|---|
| 4.1 | OpenAI Moderation API или Detoxify интегрирован | [ ] |
| 4.2 | Пороги настроены: >0.7 блок, 0.3-0.7 review | [ ] |
| 4.3 | Fallback на human review для edge cases | [ ] |
| 4.4 | Пост-модерация: периодический review опубликованного контента | [ ] |

### Phase 5: Monitoring & Alerting

| # | Проверка | Статус |
|---|---|---|
| 5.1 | Health check endpoint настроен (/health) | [ ] |
| 5.2 | Prometheus собирает метрики | [ ] |
| 5.3 | Grafana dashboard настроен | [ ] |
| 5.4 | Telegram alerts на critical events | [ ] |
| 5.5 | Алерты на: downtime, error rate, rate limits, token usage spikes | [ ] |

### Phase 6: Recovery & Self-healing

| # | Проверка | Статус |
|---|---|---|
| 6.1 | systemd / Docker restart policy настроен | [ ] |
| 6.2 | Graceful shutdown обработан (SIGTERM) | [ ] |
| 6.3 | Liveness + Readiness probes | [ ] |
| 6.4 | Queue для сообщений (не теряются при restart) | [ ] |

### Phase 7: Backup

| # | Проверка | Статус |
|---|---|---|
| 7.1 | Ежедневный automated backup SQLite | [ ] |
| 7.2 | WAL mode enabled | [ ] |
| 7.3 | Backup хранится отдельно от сервера | [ ] |
| 7.4 | Retention: 30 дней | [ ] |
| 7.5 | Тестовое восстановление раз в месяц | [ ] |

### Phase 8: API Key Management

| # | Проверка | Статус |
|---|---|---|
| 8.1 | API keys в secrets manager (не в коде!) | [ ] |
| 8.2 | Разные ключи для dev/staging/prod | [ ] |
| 8.3 | Ротация каждые 90 дней (календарное напоминание) | [ ] |
| 8.4 | Emergency revocation процедура документирована | [ ] |
| 8.5 | Мониторинг аномального использования | [ ] |

### Phase 9: Audit Trail

| # | Проверка | Статус |
|---|---|---|
| 9.1 | Все действия агента логируются (JSON) | [ ] |
| 9.2 | Correlation ID для traceability | [ ] |
| 9.3 | Sensitive data sanitized в логах | [ ] |
| 9.4 | Логи immutable (append-only) | [ ] |
| 9.5 | Retention policy: 90 дней hot, 1 год cold | [ ] |
| 9.6 | Security events отдельно от business events | [ ] |

### Phase 10: Rate Limiting

| # | Проверка | Статус |
|---|---|---|
| 10.1 | Exponential backoff с jitter на всех API | [ ] |
| 10.2 | Queue для Telegram messages | [ ] |
| 10.3 | Pre-flight token estimation для LLM | [ ] |
| 10.4 | Dual-bucket rate limiter (RPM + TPM) | [ ] |
| 10.5 | Separate API keys per environment | [ ] |
| 10.6 | Monitoring 429 errors | [ ] |

### Phase 11: Incident Response

| # | Проверка | Статус |
|---|---|---|
| 11.1 | Мгновенный kill switch (остановка агента за < 10 сек) | [ ] |
| 11.2 | Runbook для common incidents | [ ] |
| 11.3 | Post-mortem process документирован | [ ] |
| 11.4 | Evidence preservation (logs, snapshots) | [ ] |

---

## 12. Итоговые рекомендации

### Архитектура безопасности Digital Clone v3

```
┌─────────────────────────────────────────────────────────────────┐
│                        DIGITAL CLONE v3                          │
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │   Telegram   │◄──►│    Agent     │◄──►│   LLM API    │       │
│  │    Bot API   │    │  (Python)    │    │ (Kimi/GPT)   │       │
│  └──────────────┘    └──────┬───────┘    └──────────────┘       │
│                             │                                    │
│  ┌──────────────────────────┼──────────────────────────────┐     │
│  │        SANDBOX LAYER     │                              │     │
│  │   ┌──────────────────────┴──────────────┐               │     │
│  │   │  Docker + gVisor / Firecracker      │               │     │
│  │   │  • Non-root user                    │               │     │
│  │   │  • Read-only root FS                │               │     │
│  │   │  • Network Policy (whitelist)       │               │     │
│  │   └─────────────────────────────────────┘               │     │
│  └──────────────────────────────────────────────────────────┘     │
│                             │                                    │
│  ┌──────────────────────────┼──────────────────────────────┐     │
│  │        GUARDRAILS        │                              │     │
│  │   ┌────────────┐  ┌──────┴───────┐  ┌────────────────┐ │     │
│  │   │  Content   │  │   Human-in   │  │   Rate Limit   │ │     │
│  │   │ Moderation │  │   the Loop   │  │   (dual bucket)│ │     │
│  │   └────────────┘  └──────────────┘  └────────────────┘ │     │
│  └──────────────────────────────────────────────────────────┘     │
│                             │                                    │
│  ┌──────────────────────────┼──────────────────────────────┐     │
│  │      OBSERVABILITY       │                              │     │
│  │   ┌────────┐ ┌────────┐ │┌──────────┐  ┌─────────────┐ │     │
│  │   │Prometheus│ │Grafana │ ││ Telegram │  │  Audit Log  │ │     │
│  │   │Metrics │ │Dashboard│ ││  Alerts  │  │   (JSON)    │ │     │
│  │   └────────┘ └────────┘ │└──────────┘  └─────────────┘ │     │
│  └──────────────────────────────────────────────────────────┘     │
│                             │                                    │
│  ┌──────────────────────────┼──────────────────────────────┐     │
│  │      INFRASTRUCTURE      │                              │     │
│  │   ┌────────┐ ┌────────┐ │┌──────────┐  ┌─────────────┐ │     │
│  │   │ systemd│ │ rclone │ ││ Backblaze│  │   Doppler   │ │     │
│  │   │restart │ │ backup │ ││   B2     │  │   Secrets   │ │     │
│  │   └────────┘ └────────┘ │└──────────┘  └─────────────┘ │     │
│  └──────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
```

### Приоритеты внедрения

| Приоритет | Компонент | Время внедрения | Критичность |
|---|---|---|---|
| **P0** | Kill switch (остановка агента) | 1 час | Блокирующий |
| **P0** | HITL для финансовых операций | 1 день | Блокирующий |
| **P1** | Content moderation | 1 день | Высокий |
| **P1** | Audit logging | 1 день | Высокий |
| **P1** | Telegram alerting | 2 часа | Высокий |
| **P1** | systemd auto-restart | 1 час | Высокий |
| **P2** | Backup (rclone + B2) | 2 часа | Средний |
| **P2** | Rate limiting (dual bucket) | 4 часа | Средний |
| **P2** | Secrets manager (Doppler) | 2 часа | Средний |
| **P3** | Prometheus + Grafana | 1 день | Средний |
| **P3** | API key rotation process | 4 часа | Низкий |
| **P4** | Firecracker microVM | 1-2 дня | Желательно |

### Ключевые принципы

1. **Defense in depth** — ни один guardrail не должен быть единственной линией обороны
2. **Fail closed** — если guardrail не работает, действие блокируется по умолчанию [^281^]
3. **Trust but verify** — логируй ВСЁ, мониторь ВСЁ, review ВСЁ
4. **Kill switch всегда под рукой** — возможность остановить агента за < 10 секунд
5. **Гуманизация** — агент действует от имени человека, поэтому безопасность критичнее скорости

---

## Ссылки

| ID | Источник |
|----|----------|
| [^240^] | Elementum.ai — Human-in-the-Loop Agentic AI |
| [^241^] | PMC — Unveiling disguised toxicity: Perspective API vs Detoxify |
| [^243^] | Galileo.ai — How to Build Human-in-the-Loop Oversight for AI Agents |
| [^244^] | Lasso Moderation — Perspective API: complete guide to finding an alternative |
| [^245^] | Sparkco.ai — Integrating Grafana and Prometheus with AI for Advanced Monitoring |
| [^246^] | Northflank — How to sandbox AI agents in 2026 |
| [^247^] | Bunnyshell — Sandboxed Environments for AI Coding |
| [^249^] | EastonDev — Agent Sandbox Guide: A Complete Solution |
| [^251^] | Firecrawl — AI Agent Sandbox: How to Safely Run Autonomous Agents |
| [^252^] | ACM — A Human-centered Evaluation of a Toxicity Detection API |
| [^253^] | Agno — How to add human-in-the-loop controls to AI agents |
| [^280^] | Dev.to (GitGuardian) — API Keys Security & Secrets Management Best Practices |
| [^281^] | AgenticRail — AI Agent Audit Log Best Practices |
| [^282^] | BotNameFinder — Telegram Bot API Rate Limits Explained |
| [^283^] | Milvus — How do I implement auto-restart and health checks |
| [^284^] | PeakHour — Best Practices for API Key Management and Rotation |
| [^285^] | OWASP — AI Agent Security Cheat Sheet |
| [^286^] | Cycode — Secrets Management Best Practices |
| [^287^] | Grokipedia — Telegram Bot API Limitations |
| [^288^] | ByteBridge — Implementing Audit Logging and Retention in MCP |
| [^289^] | Medium — Self-Healing Agents in Python |
| [^290^] | Wiz.io — What is Secrets Management? Best Practices & Tools |
| [^292^] | Prefactor — 5 Best Practices for AI Agent Access Control |
| [^293^] | NHIMG — API key rotation best practices |
| [^295^] | Rollout — Telegram Bot API Essential Guide |
| [^311^] | Monday.com — AI Agent Security: Controls, Risks, and Best Practices |
| [^312^] | arXiv — ExpGuard: LLM Content Moderation in Specialized Domains |
| [^313^] | dig8ital — Mapping AI Agent Security Across OWASP, NIST |
| [^314^] | GitHub — AI Agent Security Audit Checklist |
| [^317^] | Microsoft — NIST-Based Security Governance Framework for AI Agents |
| [^318^] | OWASP — Agentic Skills Top 10 |
| [^319^] | OWASP — Skill Security Assessment Checklist |
| [^324^] | ClawPulse — LLM API Rate Limiting Best Practices |
| [^325^] | OpenAI Help Center — How can I solve 429 errors |
| [^328^] | OpenAI Cookbook — How to handle rate limits |
| [^329^] | Dev.to — The Python Developer's Guide to Background Process Management |
| [^330^] | Kimi Platform — Recharge and Rate Limiting |
| [^331^] | Kimi Platform — Best Practices for Benchmarking |
| [^334^] | GitHub — alertmanager-webhook (Telegram/Discord/PagerDuty) |
| [^335^] | Muetsch.io — Sending Prometheus Alerts to Telegram with Telepush |
| [^336^] | CodingNotions — Fully Automated Backup with Rclone and systemd Timer |
| [^337^] | GitHub — prometheus-telegram-alert |
| [^338^] | PCT Telegram — Telegram Bot API Rate Limits Best Practices (Chinese) |
| [^342^] | CodeWords — A complete guide to Telegram automations |
| [^323^] | EvoLink — Best Content Moderation APIs Compared |
| [^292^] | Prefactor — AI Agent Access Control Best Practices |
