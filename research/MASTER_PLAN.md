# MASTER PLAN: Digital Clone v3 — Допил до мирового уровня

> На основе 5589 строк исследований, 7 фасетов, 90+ поисков, 350+ источников

---

## ГЛАВНЫЙ ВЫВОД: Рекомендуемая архитектура

### Fallback-цепочка LLM (0$):
```
Kimi (primary) → DeepSeek (5M free tokens) → Gemini 2.0 Flash (1500 RPD) 
→ Groq LLaMA 3.1 (14400 RPD) → OpenRouter free (50 RPD) 
→ GLM-4.7-Flash (бесплатно) → Ollama + Gemma 4 E4B (CPU, локально)
→ Hugging Face Inference API (300 req/h, emergency)
```

### Фреймворк: ДОПИЛИВАТЬ СВОЁ
> Не мигрировать на LangGraph/CrewAI. 80% benefit через частичную интеграцию при 20% усилий.

### Стек (0$ бюджет):
| Компонент | Инструмент | Цена |
|-----------|-----------|------|
| LLM Primary | Kimi / DeepSeek | $0 (free tier) |
| LLM Fallback | Gemini + Groq + OpenRouter | $0 |
| LLM Local | Ollama + Gemma 4 | $0 |
| Bot Framework | aiogram 3.x | $0 |
| CRM | Notion (solo) или EspoCRM | $0 |
| Quality | LanguageTool self-hosted + textstat + VADER | $0 |
| Images | Pollinations AI + Copilot DALL-E 3 | $0 |
| TTS | Edge-TTS (322 голоса) | $0 |
| Subtitles | faster-whisper | $0 |
| Video | ffmpeg + Pillow | $0 |
| Music | YouTube Audio Library | $0 |
| Analytics | pytrends + YouTube Data API | $0 |
| Monitoring | Prometheus + Telegram alerts | $0 |
| Backup | rclone + Backblaze B2 (10GB free) | $0 |

---

## ЭТАП 1: LLM Fallback + Unified API (2-3 дня)

### Что делать:
1. Установить LiteLLM Proxy — единый API для всех LLM
2. Настроить fallback chain в `config/llm_fallback.yaml`:
   ```yaml
   model_list:
     - model_name: "primary"
       litellm_params:
         model: "kimi/kimi-latest"
         api_key: "os.environ/KIMI_API_KEY"
     - model_name: "backup-1"
       litellm_params:
         model: "deepseek/deepseek-chat"
         api_key: "os.environ/DEEPSEEK_API_KEY"
     - model_name: "backup-2"
       litellm_params:
         model: "gemini/gemini-2.0-flash"
         api_key: "os.environ/GEMINI_API_KEY"
     - model_name: "local"
       litellm_params:
         model: "ollama/gemma4:4b"
         api_base: "http://localhost:11434"
   ```
3. Переписать `LLMRouter` на использование LiteLLM
4. Установить Ollama + Gemma 4 локально (запасной вариант)

### Результат: Агент не умирает если Kimi падает

---

## ЭТАП 2: Quality Control v2 (3-4 дня)

### Что добавить в `core/quality_control.py`:

| Проверка | Библиотека | Как |
|----------|-----------|-----|
| Grammar | LanguageTool self-hosted (Docker) | HTTP API |
| Readability | textstat (Python) | `textstat.flesch_reading_ease(text)` |
| ToV Check | VADER + кастомные правила | Сентимент + запрещённые слова |
| Fact Check | Gemini с grounding (500/день) | `google_search_retrieval` tool |
| Plagiarism | Quetext free + ZeroGPT | API вызовы |
| SEO Score | SEO ContentScore (free) | Веб-скрапинг |
| LLM Review | Self-Refine pattern | Генерировать → оценить → доработать |

### Approval Workflow:
```
Generated Post → Quality Check (8 проверок) → Score ≥ 85? 
  → ДА: Auto-publish (level 3)
  → 60-85: Send to you in Telegram → ✅/❌
  → < 60: Rewrite (max 3 attempts)
```

### Результат: Контент проходит 8 проверок + твое одобрение

---

## ЭТАП 3: Traffic Engine (2-3 дня)

### Что добавить:

**Telegram Growth:**
- Cross-promotion: автопоиск каналов в TGStat + предложение обмена
- SEO название канала с ключевым словом "AI automation"
- Discussion group для engagement

**YouTube Shorts:**
- pytrends — мониторинг трендов
- Shorts SEO: хуки в первые 3 сек, burned-in captions, 15-30 сек
- Кросс-постинг в Instagram Reels, TikTok, VK

**Community:**
- Reddit (r/artificial, r/MachineLearning) — ответы с ссылками
- VC.ru — статьи и экспертные комментарии
- Quora — ответы на вопросы про AI automation

### Growth Plan (12 недель):
| Неделя | Действие | Цель |
|--------|----------|------|
| 1-2 | Контент 2x/день, cross-promo | 100 подписчиков |
| 3-4 | Shorts 3x/нед, Reddit/Quora | 300 подписчиков |
| 5-8 | Guest posts, VC.ru статьи | 600 подписчиков |
| 9-12 | Коллаборации, AMA | 1000 подписчиков |

---

## ЭТАП 4: Sales Funnel (3-4 дня)

### Бот-воронка в Telegram:
```
Подписчик → Lead Magnet (free guide) → 
  Qualification Bot (5 вопросов) → 
    CRM (Notion) → 
      Offer Generation (WeasyPrint PDF) → 
        Payment (TON crypto or Stripe) → 
          Contract (docxtpl) → 
            Delivery → 
              Review Request
```

### Lead Qualification Questions:
1. Какой у вас бизнес?
2. Какую задачу хотите автоматизировать?
3. Какой бюджет?
4. Какие сроки?
5. Как с вами связаться? (TG/phone/email)

### Результат: Автоматическая воронка от лида до оплаты

---

## ЭТАП 5: Video Pipeline v2 (4-5 дней)

### Новый shorts_pipeline.py:
```python
def run_pipeline(topic):
    # 1. Script (LLM)
    script = generate_script(topic)        # 200-300 слов
    
    # 2. Images (Pollinations AI)          # $0, без API-ключа
    images = generate_images(script, 5)    # 5 сцен
    
    # 3. TTS (Edge-TTS)                    # $0, 322 голоса
    audio = generate_tts(script, "ru-RU")  # русский голос
    
    # 4. Subtitles (faster-whisper)        # $0, локально
    srt = generate_subtitles(audio)
    
    # 5. Assembly (ffmpeg)                 # $0
    video = assemble_video(images, audio, srt, music)
    
    # 6. Thumbnail (Pillow)                # $0
    thumb = generate_thumbnail(topic)
    
    # 7. Publish (tg_publish + YouTube API)
    return publish(video, thumb, topic)
```

### Технические детали:
- **Pollinations AI**: `https://image.pollinations.ai/prompt/{text}?nologo=true` — нет API ключа, нет watermark
- **Edge-TTS**: `edge-tts --voice ru-RU-SvetlanaNeural --text "..." --write-media out.mp3`
- **faster-whisper**: `model = WhisperModel("base")` — работает на CPU, 4x быстрее OpenAI
- **ffmpeg**: Ken Burns эффект, масштабирование 9:16, субтитры с обводкой
- **Музыка**: YouTube Audio Library (Content ID-safe)

---

## ЭТАП 6: Security + Monitoring (2-3 дня)

### Что добавить:

| Компонент | Инструмент | Что делает |
|-----------|-----------|------------|
| Content Filter | OpenAI Moderation API ($0) | Проверяет токсичность |
| Sandbox | systemd + Docker | Агент не может удалить систему |
| Monitoring | Prometheus + health endpoint | Метрики: токены, latency, ошибки |
| Alerts | Telegram bot | Оповещение если агент упал |
| Recovery | systemd Restart=on-failure | Автоперезапуск |
| Backup | rclone + Backblaze B2 | Бэкап SQLite каждый час |
| Rate Limit | Exponential backoff | Не попасть в бан |
| Audit | JSON structured logs | Все действия агента записаны |

### Approval System:
```python
# Перед публикацией — send to you
def request_approval(content, quality_score):
    if quality_score >= 85 and autonomy_level >= 3:
        return auto_publish(content)      # Полная автономия
    elif quality_score >= 60:
        return send_for_approval(content) # Ты жмёшь ✅/❌
    else:
        return rewrite(content)           # Переписать
```

---

## ИТОГОВЫЙ TIMELINE

| Неделя | Этап | Что готово |
|--------|------|------------|
| 1 | LLM Fallback + Quality v2 | Агент не падает, контент проверяется |
| 2 | Traffic Engine + Shorts Pipeline | Трафик растёт, ролики генерируются |
| 3 | Sales Funnel | Воронка от лида до оплаты |
| 4 | Security + Monitoring + Polish | Production-ready, ты спишь спокойно |

---

## ЧТО НЕ ДЕЛАТЬ (убитые исследованием мифы):

1. ❌ Не мигрируй на LangGraph/CrewAI — своё лучше (score 50/60)
2. ❌ Не используй Perspective API — закрывается в декабре 2026
3. ❌ Не плать за plagiarism check — Quetext free + ZeroGPT достаточно
4. ❌ Не используй CapCut API — watermark, нет автоматизации
5. ❌ Не делай Docker-only sandbox — нужен gVisor для LLM-кода
6. ❌ Не надеясь на один LLM — fallback ОБЯЗАТЕЛЕН

---

## СЛЕДУЮЩИЙ ШАГ

Дай мне KIMI_API_KEY (или DEEPSEEK_API_KEY) — и я начну реализацию Этапа 1 (LLM Fallback). Без ключа — начну с Этапа 2 (Quality v2) и Этапа 5 (Video Pipeline), которые не требуют API.
