# AUDIT: Интеграционные проблемы Digital Clone v3

## Статус: 6 критических проблем

---

### Проблема 1 (CRITICAL): RealTools не зарегистрированы в MCP
**Где:** `main.py` (строки 78-83)
**Что:** В main.py создаётся `AutonomousLoop(jarvis)`, но НЕ вызывается `mcp.register_real_tools()`.
**Последствие:** tg_publish_post, shorts_generate, content_publish_full — все 5 real tools НЕДОСТУПНЫ через MCP.

### Проблема 2 (CRITICAL): Pipeline публикации использует не тот инструмент
**Где:** `core/autonomous_loop.py` строка 650
```python
mcp_result = await self.mcp.execute("tg_send_message", {...})  # <-- WRONG
```
**Должно быть:**
```python
mcp_result = await self.mcp.execute("tg_publish_post", {...})  # <-- RIGHT
```
tg_send_message — шлёт текст через Bot API (заглушка-лайт).
tg_publish_post — реально вызывает tg_publish.py через subprocess.

### Проблема 3 (CRITICAL): Pipeline видео использует заглушку
**Где:** `core/autonomous_loop.py` строка 679
```python
mcp_result = await self.mcp.execute("video_generate_seedance", ...)  # <-- WRONG
```
**Должно быть:**
```python
mcp_result = await self.mcp.execute("shorts_generate", ...)  # <-- RIGHT
```
video_generate_seedance — возвращает строку "Video generated: ..." (заглушка).
shorts_generate — реально вызывает shorts_pipeline.py через subprocess.

### Проблема 4 (HIGH): QualityChecker — простой, а не full QualityControl
**Где:** `core/autonomous_loop.py` строки 359-445
**Что:** AutonomousLoop использует простой `QualityChecker` (LLM score 0-1 + эвристика).
**Должен использовать:** `ContentQualityChecker` из `core/quality_control.py` с 8 проверками, ToV профилем Данила, human-readable отчётами.
**Последствие:** Контент проверяется поверхностно, ToV Данила не проверяется.

### Проблема 5 (MEDIUM): Autonomy Level 2 не проверяет quality_score перед публикацией
**Где:** `core/autonomous_loop.py` строки 638-664
**Что:** Для autonomy_level >= 2 публикует без проверки quality_score.
**Должно:** Проверять score из предыдущего quality_check stage.

### Проблема 6 (LOW): .env.example не содержит новых переменных
**Где:** `.env.example`
**Чего не хватает:** AUTONOMOUS_CHAT_ID, SHORTS_OUTPUT_DIR, TG_CHANNEL

---

## Фиксы: что нужно сделать

1. main.py — добавить `mcp.register_real_tools(real_tools)` после инициализации
2. autonomous_loop.py — заменить `tg_send_message` на `tg_publish_post`
3. autonomous_loop.py — заменить `video_generate_seedance` на `shorts_generate`
4. autonomous_loop.py — использовать ContentQualityChecker вместо QualityChecker
5. autonomous_loop.py — добавить проверку quality_score для autonomy_level 2
6. .env.example — добавить недостающие переменные
