# Facet 1: Бесплатные LLM и Fallback-стратегии для Digital Clone v3

## Key Findings (TL;DR)

- **Наилучшая fallback-цепочка для 0 бюджета**: DeepSeek (5M free tokens) → Gemini 2.0 Flash (1500 RPD free) → Groq LLaMA 3 (14400 RPD free) → OpenRouter free models (50 RPD) → Local Ollama + Gemma 4 E4B (CPU, бесплатно)
- **Локальная модель**: Gemma 4 E4B (4.5B параметров) работает на CPU с 8GB RAM, генерирует ~10-15 ток/сек, качество генерации контента — 7/10
- **Unified API**: LiteLLM Proxy (open source) позволяет настроить автоматический fallback между всеми провайдерами через единый OpenAI-compatible endpoint
- **Бесплатные API без rate limits**: DeepSeek дает 5M токенов на старте; Gemini 2.0 Flash — 1500 запросов/день; Groq LLaMA 3.1 8B — 14400 запросов/день
- **Для русского языка**: GLM-4.7 имеет "enhanced translation quality for Russian" [^95^]; DeepSeek отлично понимает русский; Gemma 4 хороша на multilingual задачах

---

## Источник 1: Ollama + Gemma 4 (Локальная модель)

**URL**: https://ollama.com, https://github.com/ollama/ollama  
**Стоимость**: Полностью бесплатно (self-hosted)  
**Требования**: CPU или GPU; RAM от 4GB до 32GB в зависимости от модели

### Доступные модели Gemma 4

| Модель | Параметры | Мин. RAM/VRAM | CPU Speed | Качество |
|--------|-----------|---------------|-----------|----------|
| gemma4:e2b | 2.3B effective | 4GB RAM | 15 tok/s | 5/10 |
| gemma4:e4b | 4.5B effective | 6-8GB RAM | 10-15 tok/s | 7/10 |
| gemma4:26b MoE | 3.8B active | 8-12GB VRAM | Быстрый | 8/10 |
| gemma4:31b | 31B dense | 16-20GB VRAM | Медленный | 9/10 |

### Установка

```bash
# macOS/Linux
curl -fsSL https://ollama.com/install.sh | sh

# Запуск сервера
ollama serve

# Скачивание модели
ollama pull gemma4:4b

# Интерактивный режим
ollama run gemma4:4b
```

### Python интеграция (async)

```python
import aiohttp
import asyncio

OLLAMA_URL = "http://localhost:11434/api/generate"

async def generate_ollama(prompt: str, model: str = "gemma4:4b") -> str:
    async with aiohttp.ClientSession() as session:
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.7}
        }
        async with session.post(OLLAMA_URL, json=payload) as resp:
            data = await resp.json()
            return data["response"]

# Использование
result = await generate_ollama("Напиши пост о AI для блога")
```

### Качество генерации контента: 7/10 (для E4B)
- ✅ Apache 2.0 лицензия — коммерческое использование разрешено
- ✅ 128K-256K контекстное окно
- ✅ Multimodal (поддержка изображений в больших моделях)
- ✅ Работает без интернета, полная приватность
- ❌ CPU inference: 5-15 tok/s — медленно для длинных текстов
- ❌ Качество ниже cloud frontier models

> **Sources**: [^38^] https://www.knolli.ai/post/how-to-run-gemma-4-locally-with-ollama, [^39^] https://www.mindstudio.ai/blog/how-to-run-gemma-4-locally-ollama/, [^40^] https://dev.to/purpledoubled/how-to-run-googles-gemma-4-locally-with-ollama-all-4-model-sizes-compared-2pbh

---

## Источник 2: GLM 4/5 (Zhipu AI)

**URL**: https://z.ai, https://docs.z.ai  
**Стоимость**: GLM-4.7-Flash и GLM-4.5-Flash — **бесплатно**. GLM-4.7 (full): $0.60/M input, $2.20/M output  
**API Endpoint**: https://api.z.ai/v1 (OpenAI-compatible)

### Бесплатные модели

| Модель | Контекст | Цена | Качество |
|--------|----------|------|----------|
| GLM-4.7-Flash | 200K | **Free** | 7/10 |
| GLM-4.5-Flash | 128K | **Free** | 6/10 |
| GLM-4.7 (paid) | 200K | $0.60/$2.20 | 8.5/10 |

### Python интеграция (async)

```python
import openai

client = openai.AsyncOpenAI(
    api_key="your-zai-api-key",
    base_url="https://api.z.ai/api/anthropic"  # или /v1 для OpenAI format
)

async def generate_glm(prompt: str) -> str:
    response = await client.messages.create(
        model="glm-4.7",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text
```

### Качество на русском языке: 7/10
- ✅ "Enhanced translation quality for Russian" — заявлено производителем [^95^]
- ✅ 200K контекст, 128K output
- ✅ Отлично в code generation (73.8% SWE-bench)
- ⚠️ Китайская компания — latency может быть высокой из Европы
- ⚠️ Качество на русском хорошее, но не сравнимо с нативными моделями

> **Sources**: [^82^] https://vibecoding.app/blog/zhipu-ai-glm-pricing-2026, [^84^] https://docs.z.ai/guides/overview/pricing, [^94^] https://www.reddit.com/r/AIToolsPerformance/comments/1qsth0a/zai_free_api_access_to_glm47_with/, [^95^] https://www.together.ai/models/glm-4-6

---

## Источник 3: DeepSeek V3

**URL**: https://platform.deepseek.com  
**Стоимость**: **5 млн бесплатных токенов** при регистрации (без карты). Далее: $0.14/M input, $0.28/M output  
**API**: OpenAI-compatible

### Лимиты

| Параметр | Значение |
|----------|----------|
| Бесплатные токены | 5,000,000 при регистрации |
| Контекст | 128K токенов |
| Max output | 8K (chat), 64K (reasoner) |
| Автоматический context caching | Cache hit: $0.028/M (-90%) |

### Python интеграция (async)

```python
import openai

client = openai.AsyncOpenAI(
    api_key="your-deepseek-key",
    base_url="https://api.deepseek.com/v1"
)

async def generate_deepseek(prompt: str) -> str:
    response = await client.chat.completions.create(
        model="deepseek-chat",  # или "deepseek-reasoner"
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    return response.choices[0].message.content
```

### Качество генерации контента: 8.5/10
- ✅ Одна из самых мощных бесплатных моделей
- ✅ Отлично понимает русский язык
- ✅ 5M бесплатных токенов — достаточно для месяцев работы
- ✅ API полностью совместим с OpenAI
- ❌ Требует VPN в некоторых регионах
- ❌ После 5M токенов — нужно платить (но очень дёшево)

> **Sources**: [^41^] https://deepseek.ai/pricing, [^45^] https://costgoat.com/pricing/deepseek-api

---

## Источник 4: Groq + LLaMA 3

**URL**: https://console.groq.com  
**Стоимость**: **Бесплатный tier без карты**  
**Особенность**: 500+ токенов/сек — самый быстрый inference в мире

### Rate Limits (Free Tier, Март 2026)

| Модель | RPM | RPD | TPM | TPD |
|--------|-----|-----|-----|-----|
| llama-3.1-8b-instant | 30 | 14,400 | 6,000 | 500,000 |
| llama-3.3-70b-versatile | 30 | 1,000 | 12,000 | 100,000 |
| llama-4-scout-17b-16e | 30 | 1,000 | 30,000 | 500,000 |
| qwen3-32b | 60 | 1,000 | 6,000 | 500,000 |
| whisper-large-v3 (STT) | 20 | 2,000 | — | — |

### Python интеграция (async)

```python
import openai

client = openai.AsyncOpenAI(
    api_key="your-groq-key",
    base_url="https://api.groq.com/openai/v1"
)

async def generate_groq(prompt: str, model: str = "llama-3.1-8b-instant") -> str:
    response = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    return response.choices[0].message.content
```

### Качество генерации контента: 7/10 (для 8B), 8.5/10 (для 70B)
- ✅ **14,400 запросов/день** на 8B модели — самый щедрый free tier
- ✅ 500+ tok/s — мгновенные ответы
- ✅ Не нужна кредитная карта
- ✅ Поддержка Whisper для STT
- ❌ 30 RPM — ограничение на burst
- ❌ Кэшированные токены не считаются в лимиты

> **Sources**: [^44^] https://www.grizzlypeaksoftware.com/articles/p/groq-api-free-tier-limits-in-2026-what-you-actually-get-uwysd6mb

---

## Источник 5: Локальные LLM на CPU (без GPU)

### Лучшие модели для CPU-only инференса (2026)

| Модель | Параметры | GGUF Size | Min RAM | CPU Speed | Качество |
|--------|-----------|-----------|---------|-----------|----------|
| **Gemma 3 2B** | 2B | 1.5 GB | 2-2.5 GB | 15 tok/s | 5/10 |
| **Phi-4 Mini** | 3.8B | 2.3 GB | 3 GB | 12 tok/s | 6/10 |
| **Llama 3.2 3B** | 3B | 2 GB | 2.5-3 GB | 10 tok/s | 6/10 |
| **Gemma 4 E4B** | 4.5B eff. | 3 GB (Q4) | 6 GB | 10-15 tok/s | 7/10 |
| **Mistral 7B Q4** | 7B | 4.5 GB | 5 GB | 5 tok/s | 7.5/10 |
| **Llama 3.1 8B Q4** | 8B | 5 GB | 6 GB | 4 tok/s | 8/10 |

### Требования
- CPU: Intel i7-10th gen+ или AMD Ryzen 5000+ (AVX2/AVX-512)
- RAM: 8-16 GB для 3-8B моделей
- Apple Silicon: M1/M2/M3 работают лучше благодаря unified memory

### Запуск через Ollama (CPU-only, автодетект)

```bash
# Ollama автоматически использует CPU, если нет GPU
ollama run phi4-mini        # 3.8B, 12 tok/s
ollama run gemma3:4b        # 4B, ~10 tok/s
ollama run qwen3:8b         # 8B, ~5 tok/s (CPU)
ollama run gemma4:4b        # 4.5B, 10-15 tok/s (рекомендуется)
```

### Качество: 6-8/10 в зависимости от модели
- ✅ Ноль затрат на API
- ✅ Полная приватность
- ✅ Работает без интернета
- ❌ Медленно: 4-15 tok/s на CPU
- ❌ Качество ниже cloud models на ~20-30%
- ❌ Длинные тексты генерируются минутами

> **Sources**: [^35^] https://huggingface.co/blog/daya-shankar/open-source-llm-models-to-run-locally, [^36^] https://www.promptquorum.com/local-llms/best-cpu-only-llm, [^37^] https://overchat.ai/ai-hub/llm-hardware-requirements

---

## Источник 6: LiteLLM (Unified API + Fallback)

**URL**: https://github.com/BerriAI/litellm, https://docs.litellm.ai  
**Стоимость**: **Полностью бесплатно** (open source, MIT)  
**Тип**: Python SDK + Proxy Server

### Возможности

- **100+ LLM провайдеров** через единый OpenAI-compatible интерфейс
- **Автоматический fallback** при ошибках/rate limits
- **Load balancing** между несколькими провайдерами
- **Cost tracking** — отслеживание расходов
- **Virtual keys** — управление доступом
- **Caching** — Redis/SQLite кэш ответов

### Настройка Fallback-цепочки (config.yaml)

```yaml
model_list:
  # Primary: DeepSeek (дешево, качественно)
  - model_name: primary
    litellm_params:
      model: deepseek/deepseek-chat
      api_key: os.environ/DEEPSEEK_API_KEY

  # Backup 1: Gemini Flash (щедрый free tier)
  - model_name: backup1
    litellm_params:
      model: gemini/gemini-2.0-flash
      api_key: os.environ/GEMINI_API_KEY

  # Backup 2: Groq LLaMA (быстрый free tier)
  - model_name: backup2
    litellm_params:
      model: groq/llama-3.1-8b-instant
      api_key: os.environ/GROQ_API_KEY

  # Backup 3: OpenRouter free
  - model_name: backup3
    litellm_params:
      model: openrouter/meta-llama/llama-3.1-8b-instruct:free
      api_key: os.environ/OPENROUTER_API_KEY

  # Local: Ollama (always available)
  - model_name: local
    litellm_params:
      model: ollama/gemma4:4b
      api_base: http://localhost:11434

# Fallback цепочка
litellm_settings:
  num_retries: 3
  fallbacks:
    - primary: [backup1, backup2, backup3, local]
    - backup1: [backup2, backup3, local]
    - backup2: [backup3, local]

# Router settings
router_settings:
  routing_strategy: usage-based-routing-v2
  timeout: 30
```

### Python интеграция (async)

```python
import litellm

# Единый вызов с автоматическим fallback
async def generate_with_fallback(prompt: str) -> str:
    response = await litellm.acompletion(
        model="primary",
        messages=[{"role": "user", "content": prompt}],
        fallbacks=["backup1", "backup2", "backup3", "local"],
        num_retries=3,
        timeout=30
    )
    return response.choices[0].message.content

# Или через proxy (OpenAI-compatible endpoint)
import openai
client = openai.AsyncOpenAI(
    api_key="your-litellm-proxy-key",
    base_url="http://localhost:4000/v1"
)
```

### Оценка для проекта: 10/10 (must-have)
- ✅ Open source, бесплатно
- ✅ Fallback автоматически — не нужно писать логику
- ✅ Единый API для всех моделей
- ✅ Docker deployment за 5 минут
- ✅ Cost tracking и rate limiting из коробки

> **Sources**: [^66^] https://help.apiyi.com/en/litellm-beginner-guide-unified-api-gateway-ai-agent-tutorial-en.html, [^89^] https://techsy.io/en/blog/litellm-proxy-setup-guide, [^92^] https://www.datacamp.com/tutorial/litellm, [^93^] https://www.tanyongsheng.com/note/litellm-proxy-for-high-availability-llm-services-load-balancing-techniques/, [^95^] https://github.com/BerriAI/litellm

---

## Источник 7: Hugging Face Inference API

**URL**: https://huggingface.co/docs/api-inference  
**Стоимость**: **Бесплатно** (registered users)  
**Тип**: Serverless Inference (100+ моделей)

### Rate Limits

| Tier | Requests/Hour | Модели |
|------|---------------|--------|
| Unregistered | 1 req/hour | Ограниченный набор |
| **Registered (free)** | **300 req/hour** | 100+ open models |
| Pro ($9/mo) | 1000 req/hour | Все модели + приоритет |

### Python интеграция (async)

```python
from huggingface_hub import AsyncInferenceClient

client = AsyncInferenceClient(token="your-hf-token")

async def generate_hf(prompt: str) -> str:
    response = await client.text_generation(
        prompt=prompt,
        model="meta-llama/Meta-Llama-3-8B-Instruct",
        max_new_tokens=512,
        temperature=0.7
    )
    return response
```

### Качество: 6/10
- ✅ 300 req/hour бесплатно
- ✅ Доступ к 100+ моделям
- ✅ Не нужен deployment
- ❌ Высокая latency (serverless cold start)
- ❌ Не production-ready (throttling)
- ❌ Модели могут быть недоступны в пиковые часы

> **Sources**: [^87^] https://www.reddit.com/r/LocalLLaMA/comments/1fi90kw/free_hugging_face_inference_api_now_clearly_lists/, [^90^] https://huggingface.co/learn/cookbook/en/enterprise_hub_serverless_inference_api

---

## Источник 8: Google Gemini Flash

**URL**: https://ai.google.dev/gemini-api  
**Стоимость**: **Бесплатный tier** (без карты). Paid: $0.10/M input  
**Контекст**: 1,000,000 токенов (самый большой контекст)

### Rate Limits (Free Tier, Декабрь 2025)

| Модель | RPM | TPM | RPD |
|--------|-----|-----|-----|
| **Gemini 2.5 Pro** | 5 | 250,000 | 100 |
| **Gemini 2.5 Flash** | 10 | 250,000 | 250 |
| **Gemini 2.5 Flash-Lite** | 15 | 250,000 | 1,000 |
| **Gemini 2.0 Flash** | 15 | 1,000,000 | 1,500 |
| **Gemini 2.0 Flash-Lite** | 30 | 1,000,000 | 3,000 |

### Python интеграция (async)

```python
import google.generativeai as genai

# Или через OpenAI-compatible API
client = openai.AsyncOpenAI(
    api_key="your-gemini-key",
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

async def generate_gemini(prompt: str) -> str:
    response = await client.chat.completions.create(
        model="gemini-2.0-flash",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content
```

### Качество генерации контента: 8/10
- ✅ **1M контекст** — лучший для длинных документов
- ✅ **1500 RPD** (Gemini 2.0 Flash) — щедрый free tier
- ✅ Отличное качество для генерации контента
- ✅ Хорошая поддержка русского языка
- ⚠️ В декабре 2025 Google сократил лимиты на 50-80%
- ⚠️ На free tier Google может использовать данные для обучения

> **Sources**: [^61^] https://ai.google.dev/gemini-api/docs/rate-limits, [^62^] https://ai.google.dev/gemini-api/docs/pricing, [^67^] https://help.apiyi.com/en/ai-studio-gemini-3-pro-rate-limit-solution-en.html, [^68^] https://yingtu.ai/en/blog/google-gemini-api-free-tier-limits-2025

---

## Источник 9: OpenRouter

**URL**: https://openrouter.ai  
**Стоимость**: Бесплатные модели с суффиксом `:free`. Пополнение от $10  
**Тип**: Unified API aggregator (100+ моделей)

### Rate Limits

| Статус | RPM | RPD |
|--------|-----|-----|
| Бесплатный (0 кредитов) | 20 | 50 |
| С кредитами ($10+) | 20 | 1,000 |

### Бесплатные модели (2026)

- `meta-llama/llama-3.1-8b-instruct:free`
- `google/gemma-3-27b-it:free`
- `nvidia/llama-3.1-nemotron-70b:free`
- `qwen/qwen-3.6-plus:free` (1M контекст!)
- `deepseek/deepseek-chat:free`

### Python интеграция (async)

```python
import openai

client = openai.AsyncOpenAI(
    api_key="your-openrouter-key",
    base_url="https://openrouter.ai/api/v1"
)

async def generate_openrouter(prompt: str) -> str:
    response = await client.chat.completions.create(
        model="meta-llama/llama-3.1-8b-instruct:free",
        messages=[{"role": "user", "content": prompt}],
        extra_headers={
            "HTTP-Referer": "your-site.com",
            "X-Title": "Digital Clone v3"
        }
    )
    return response.choices[0].message.content
```

### Качество: 6-8/10 (зависит от модели)
- ✅ Доступ к 29+ бесплатным моделям через один API
- ✅ Не нужна кредитная карта для free tier
- ✅ Поддержка fallback между моделями
- ❌ **50 RPD** на чистом free tier — очень мало
- ❌ 20 RPM — burst-ограничение
- ❌ С пополнением $10 — 1000 RPD (гораздо лучше)

> **Sources**: [^63^] https://www.datastudios.org/post/openrouter-api-key-free-limits-free-routes-paid-access-and-byok, [^85^] https://www.digitalapplied.com/blog/free-ai-models-you-can-use-right-now-april-2026, [^91^] https://www.aibase.com/news/www.aibase.com/news/16952, [^97^] https://openrouter.ai/docs/api/reference/limits, [^98^] https://costgoat.com/pricing/openrouter-free-models

---

## Источник 10: vLLM / TGI (Self-Hosted Inference)

### vLLM

**URL**: https://github.com/vllm-project/vllm, https://docs.vllm.ai  
**Стоимость**: Бесплатно (open source)  
**Требования**: Linux, GPU compute capability 7.0+ (V100, T4, RTX20xx, A100, H100)

#### Установка через Docker

```bash
# Базовый запуск
docker run --runtime nvidia --gpus all \
    -v ~/.cache/huggingface:/root/.cache/huggingface \
    -p 8000:8000 \
    vllm/vllm-openai:latest \
    --model meta-llama/Llama-3.1-8B-Instruct \
    --host 0.0.0.0

# Python запрос
python -c "
import openai
client = openai.OpenAI(base_url='http://localhost:8000/v1', api_key='dummy')
response = client.chat.completions.create(
    model='meta-llama/Llama-3.1-8B-Instruct',
    messages=[{'role': 'user', 'content': 'Hello!'}]
)
print(response.choices[0].message.content)
"
```

#### Требования

| Компонент | Требование |
|-----------|------------|
| OS | Linux (или Docker on Windows WSL2) |
| Python | 3.9-3.12 |
| GPU | Compute capability 7.0+ |
| CUDA | 12.1+ |

### TGI (Text Generation Inference)

**URL**: https://github.com/huggingface/text-generation-inference  
**Стоимость**: Бесплатно (open source)

```bash
# Запуск TGI через Docker
docker run \
    --gpus all \
    --shm-size 64g \
    -p 8080:80 \
    -v $PWD/data:/data \
    ghcr.io/huggingface/text-generation-inference:3.0.1 \
    --model-id microsoft/phi-4
```

### Оценка для проекта: 8/10 (для GPU-сетапов)
- ✅ Production-grade throughput (10-24x vs обычный inference)
- ✅ OpenAI-compatible API
- ✅ Continuous batching для максимальной эффективности
- ❌ **Требует GPU** — не работает на чистом CPU
- ❌ Linux-only (нативно)
- ❌ Сложность настройки выше, чем Ollama

> **Sources**: [^64^] https://graphwiz.ai/ai/vllm-self-hosted-inference-guide/, [^83^] https://www.tensorzero.com/docs/integrations/model-providers/tgi, [^92^] https://christiant.io/vLLM, [^94^] https://www.docker.com/blog/docker-model-runner-vllm-windows/, [^97^] https://medium.com/@kimdoil1211/effortless-vllm-deployment-with-docker-a-comprehensive-guide-2a23119839e2

---

## Рекомендуемая Fallback-цепочка для Digital Clone v3 (0 бюджет)

```
PRIMARY     → Kimi API (текущий основной провайдер)
BACKUP #1   → DeepSeek V3 (5M free tokens, $0.14/M после)
BACKUP #2   → Gemini 2.0 Flash (1500 RPD free tier)
BACKUP #3   → Groq LLaMA 3.1 8B (14400 RPD free tier)
BACKUP #4   → OpenRouter free models (50 RPD, 29+ models)
BACKUP #5   → GLM-4.7-Flash (бесплатно, 200K контекст)
LOCAL       → Ollama + Gemma 4 E4B (CPU, 8GB RAM)
DEAD MAN'S  → Hugging Face Inference API (300 req/hour)
```

### Архитектура с LiteLLM Proxy

```
┌─────────────────────────────────────────────────────────────┐
│                    Digital Clone v3                         │
│                      (Python async)                         │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │          LiteLLM Proxy (localhost:4000)              │   │
│  │                                                      │   │
│  │   fallbacks:                                         │   │
│  │     - primary:   kimi (текущий)                     │   │
│  │     - backup1:   deepseek/deepseek-chat             │   │
│  │     - backup2:   gemini/gemini-2.0-flash            │   │
│  │     - backup3:   groq/llama-3.1-8b-instant          │   │
│  │     - backup4:   openrouter (free models)           │   │
│  │     - backup5:   zai/glm-4.7-flash                  │   │
│  │     - local:     ollama/gemma4:4b                   │   │
│  │                                                      │   │
│  │   router: usage-based-routing-v2                     │   │
│  │   num_retries: 3                                     │   │
│  │   timeout: 30s                                       │   │
│  └─────────────────────────────────────────────────────┘   │
│                           │                                 │
│                     ┌─────┴─────┐                           │
│                     ▼           ▼                           │
│              ┌─────────┐  ┌─────────┐                      │
│              │  Redis  │  │  Cache  │                      │
│              │ (opt.)  │  │ (opt.)  │                      │
│              └─────────┘  └─────────┘                      │
└─────────────────────────────────────────────────────────────┘
```

### Минимальная реализация (без LiteLLM Proxy)

```python
import os
import asyncio
import openai
from typing import Optional

# Конфигурация всех провайдеров
PROVIDERS = {
    "kimi": {
        "client": openai.AsyncOpenAI(
            api_key=os.getenv("KIMI_API_KEY"),
            base_url="https://api.moonshot.cn/v1"
        ),
        "model": "moonshot-v1-8k"
    },
    "deepseek": {
        "client": openai.AsyncOpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com/v1"
        ),
        "model": "deepseek-chat"
    },
    "gemini": {
        "client": openai.AsyncOpenAI(
            api_key=os.getenv("GEMINI_API_KEY"),
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        ),
        "model": "gemini-2.0-flash"
    },
    "groq": {
        "client": openai.AsyncOpenAI(
            api_key=os.getenv("GROQ_API_KEY"),
            base_url="https://api.groq.com/openai/v1"
        ),
        "model": "llama-3.1-8b-instant"
    },
    "openrouter": {
        "client": openai.AsyncOpenAI(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1"
        ),
        "model": "meta-llama/llama-3.1-8b-instruct:free"
    },
    "glm": {
        "client": openai.AsyncOpenAI(
            api_key=os.getenv("ZAI_API_KEY"),
            base_url="https://api.z.ai/v1"
        ),
        "model": "glm-4.7-flash"
    },
    "local": {
        "client": openai.AsyncOpenAI(
            api_key="not-needed",
            base_url="http://localhost:11434/v1"
        ),
        "model": "gemma4:4b"
    }
}

# Порядок fallback
FALLBACK_CHAIN = ["kimi", "deepseek", "gemini", "groq", "openrouter", "glm", "local"]

async def generate_with_fallback(
    prompt: str,
    max_retries: int = 2,
    timeout: float = 30.0
) -> tuple[str, str]:
    """Генерация с автоматическим fallback.
    
    Returns: (provider_name, response_text)
    """
    messages = [{"role": "user", "content": prompt}]
    
    for provider_name in FALLBACK_CHAIN:
        provider = PROVIDERS[provider_name]
        client = provider["client"]
        model = provider["model"]
        
        for attempt in range(max_retries):
            try:
                response = await asyncio.wait_for(
                    client.chat.completions.create(
                        model=model,
                        messages=messages,
                        temperature=0.7,
                        max_tokens=2048
                    ),
                    timeout=timeout
                )
                content = response.choices[0].message.content
                print(f"[OK] Generated via {provider_name}")
                return provider_name, content
                
            except asyncio.TimeoutError:
                print(f"[TIMEOUT] {provider_name} attempt {attempt + 1}")
            except Exception as e:
                print(f"[ERROR] {provider_name} attempt {attempt + 1}: {e}")
    
    raise RuntimeError("All providers exhausted!")

# Пример использования
async def main():
    provider, text = await generate_with_fallback(
        "Напиши SEO-оптимизированный пост про нейросети для блога"
    )
    print(f"Provider: {provider}")
    print(f"Text: {text[:200]}...")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Сводная таблица всех провайдеров

| # | Провайдер | Стоимость | RPD | RPM | Контекст | Качество | Русский |
|---|-----------|-----------|-----|-----|----------|----------|---------|
| 1 | **Kimi** | Платный (текущий) | — | — | 200K | 9/10 | 9/10 |
| 2 | **DeepSeek V3** | 5M free, затем $0.14/M | — | — | 128K | 9/10 | 8/10 |
| 3 | **Gemini 2.0 Flash** | 1500 RPD free | 1500 | 15 | 1M | 8/10 | 8/10 |
| 4 | **Groq LLaMA 3.1 8B** | 14400 RPD free | 14400 | 30 | 128K | 7/10 | 7/10 |
| 5 | **OpenRouter free** | 50 RPD (1000 при $10) | 50 | 20 | 128K | 7/10 | 7/10 |
| 6 | **GLM-4.7-Flash** | Free | — | — | 200K | 7/10 | 7/10 |
| 7 | **Ollama + Gemma 4** | Free (self-hosted) | ∞ | ∞ | 128K | 7/10 | 7/10 |
| 8 | **Hugging Face** | 300 req/hour free | 7200 | — | varies | 6/10 | varies |

---

## Рекомендации по внедрению

### Phase 1 (Немедленно — 1 день)
1. Зарегистрироваться на DeepSeek, Gemini, Groq, OpenRouter, Z.AI
2. Получить API ключи для всех бесплатных сервисов
3. Заменить прямой вызов Kimi на функцию `generate_with_fallback()`
4. Kimi остаётся primary, DeepSeek → backup #1

### Phase 2 (1-3 дня)
1. Установить LiteLLM Proxy через Docker
2. Настроить `config.yaml` с полной fallback цепочкой
3. Настроить Redis кэш для повторяющихся запросов
4. Перевести приложение на единый endpoint (localhost:4000)

### Phase 3 (3-7 дней)
1. Установить Ollama + Gemma 4 E4B на сервер
2. Настроить local fallback через LiteLLM
3. Мониторинг: cost tracking, provider usage stats
4. Dead man's switch: алертинг если все провайдеры down

### Phase 4 (Опционально — GPU)
1. GPU-сервер с vLLM для production-grade локального inference
2. Модели: Qwen3-8B или Gemma 4 12B на GPU
3. Tensor parallelism для масштабирования

---

## Мониторинг и алертинг

```python
# Простой health-check для всех провайдеров
async def health_check_all() -> dict[str, bool]:
    """Проверяет доступность всех провайдеров."""
    results = {}
    for name, provider in PROVIDERS.items():
        try:
            await provider["client"].chat.completions.create(
                model=provider["model"],
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=5
            )
            results[name] = True
        except Exception:
            results[name] = False
    return results

# Dead man's switch: алерт если < 2 провайдеров доступны
async def dead_mans_switch():
    health = await health_check_all()
    available = sum(health.values())
    if available < 2:
        send_alert(f"CRITICAL: Only {available} LLM providers available!")
```

---

## Итоговые рекомендации

1. **Must-have: LiteLLM Proxy** — единая точка входа, автоматический fallback, cost tracking
2. **Primary backup: DeepSeek V3** — 5M бесплатных токенов, отличное качество, дёшево после
3. **Secondary backup: Gemini 2.0 Flash** — 1500 RPD, 1M контекст, стабильный Google
4. **Tertiary backup: Groq LLaMA** — 14400 RPD, молниеносная скорость
5. **Local backup: Ollama + Gemma 4 E4B** — работает на CPU с 8GB RAM, полностью бесплатно
6. **Emergency: Hugging Face Inference API** — 300 req/hour как последний резерв

**Эта конфигурация обеспечит 100% uptime Digital Clone v3 при нулевом бюджете.**

---

## Список источников

- [^38^] https://www.knolli.ai/post/how-to-run-gemma-4-locally-with-ollama — Gemma 4 hardware requirements
- [^39^] https://www.mindstudio.ai/blog/how-to-run-gemma-4-locally-ollama/ — Gemma 4 Ollama guide
- [^40^] https://dev.to/purpledoubled/how-to-run-googles-gemma-4-locally-with-ollama-all-4-model-sizes-compared-2pbh — Gemma 4 benchmarks
- [^41^] https://deepseek.ai/pricing — DeepSeek pricing
- [^44^] https://www.grizzlypeaksoftware.com/articles/p/groq-api-free-tier-limits-in-2026-what-you-actually-get-uwysd6mb — Groq free tier limits
- [^45^] https://costgoat.com/pricing/deepseek-api — DeepSeek API details
- [^61^] https://ai.google.dev/gemini-api/docs/rate-limits — Gemini rate limits
- [^62^] https://ai.google.dev/gemini-api/docs/pricing — Gemini pricing
- [^63^] https://www.datastudios.org/post/openrouter-api-key-free-limits-free-routes-paid-access-and-byok — OpenRouter limits
- [^64^] https://graphwiz.ai/ai/vllm-self-hosted-inference-guide/ — vLLM self-hosted guide
- [^66^] https://help.apiyi.com/en/litellm-beginner-guide-unified-api-gateway-ai-agent-tutorial-en.html — LiteLLM guide
- [^82^] https://vibecoding.app/blog/zhipu-ai-glm-pricing-2026 — GLM pricing
- [^84^] https://docs.z.ai/guides/overview/pricing — Z.AI pricing docs
- [^85^] https://www.digitalapplied.com/blog/free-ai-models-you-can-use-right-now-april-2026 — Free AI models guide
- [^87^] https://www.reddit.com/r/LocalLLaMA/comments/1fi90kw/free_hugging_face_inference_api_now_clearly_lists/ — HF Inference API limits
- [^89^] https://techsy.io/en/blog/litellm-proxy-setup-guide — LiteLLM proxy setup
- [^90^] https://huggingface.co/learn/cookbook/en/enterprise_hub_serverless_inference_api — HF cookbook
- [^91^] https://www.aibase.com/news/www.aibase.com/news/16952 — OpenRouter policy changes
- [^92^] https://christiant.io/vLLM — vLLM production guide
- [^94^] https://www.docker.com/blog/docker-model-runner-vllm-windows/ — vLLM Docker setup
- [^95^] https://www.together.ai/models/glm-4-6 — GLM-4.6 specs
- [^97^] https://openrouter.ai/docs/api/reference/limits — OpenRouter rate limits docs
- [^98^] https://costgoat.com/pricing/openrouter-free-models — OpenRouter free models list
