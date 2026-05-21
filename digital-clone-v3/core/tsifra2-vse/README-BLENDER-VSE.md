# Blender VSE Video Editor — Монтаж шортсов в Blender

## Что это

Полноценный видео-редактор на базе **Blender Video Sequence Editor (VSE)**.

**Ключевое отличие от предыдущей версии:**
- Было: ffmpeg drawtext на цветных фонах (слайд-шоу)
- Стало: Blender VSE с timeline, keyframe-анимацией, цветокоррекцией, переходами

## Архитектура

```
core/blender_vse/
  __init__.py              # Публичное API
  editor.py                # BlenderVSEEditor (1063 строки)
  mcp_tools.py             # MCP интеграция (837 строк)
  styles/
    __init__.py            # Регистрация стилей
    base.py                # VSEStyleBase — базовый pipeline
    yoedit.py              # YoEdit стиль
    gadzhi.py              # Iman Gadzhi стиль
    merzliakov.py          # Arsenii Merzliakov стиль
```

## 3 стиля монтажа

| Стиль | Переход | Анимация текста | Цветокоррекция | Эффекты |
|-------|---------|-----------------|----------------|---------|
| **YoEdit** | HARD_CUT (резкий) | bounce (пружина) | contrast 1.2, sat 1.3, warm | — |
| **Gadzhi** | GAMMA_CROSS (плавный) | zoom_in | contrast 1.15, warm | film grain + vignette |
| **Merzliakov** | CROSS (плавный) | slide_up | gold tint (#FFD700) | — |

## 5 типов анимации текста

- **fade_in** — плавное появление через alpha
- **slide_up** — выезд снизу + fade
- **bounce** — 3 фазы: подъём/overshoot/settle (YoEdit)
- **zoom_in** — увеличение scale 0.3→1.0 (Gadzhi)
- **typewriter** — посимвольное появление

## Как использовать

### Вариант 1: Прямой Python

```python
from core.blender_vse.styles import get_style

# Выбрать стиль
style = get_style("gadzhi")  # yoedit | gadzhi | merzliakov

# Создать шорт
video_path = style.create_short(
    video_clips=["clip1.mp4", "clip2.mp4", "clip3.mp4"],
    texts=[
        {"text": "ХУК: Этот трюк", "start_frame": 1, "duration": 75},
        {"text": "сделает тебя", "start_frame": 76, "duration": 75},
        {"text": "миллионером", "start_frame": 151, "duration": 75},
    ],
    output_path="./output/short.mp4",
    width=1080,
    height=1920,
    fps=30,
)
print(f"Готово: {video_path}")
```

### Вариант 2: Через MCP (Model Context Protocol)

```python
from core.mcp_layer import MCPLayer
from core.blender_vse.mcp_tools import register_blender_vse_tools

# Регистрация инструментов
mcp = MCPLayer()
register_blender_vse_tools(mcp)

# Использование через MCP
result = await mcp.execute("blender_vse_create_project", {
    "width": 1080, "height": 1920, "fps": 30
})

result = await mcp.execute("blender_vse_add_clip", {
    "filepath": "/path/to/clip.mp4", "channel": 1, "frame_start": 1
})

result = await mcp.execute("blender_vse_add_text", {
    "text": "HELLO", "channel": 3, "frame_start": 1, "frame_end": 60
})

result = await mcp.execute("blender_vse_animate", {
    "strip_name": "Text", "animation_type": "bounce"
})

result = await mcp.execute("blender_vse_render", {
    "output_path": "./output.mp4"
})
```

## Требования

- **Blender 4.x** (с Python API)
- Видео-клипы (B-roll) для монтажа
- Для MCP: запущенный MCP-сервер

## Как это работает

1. **create_project()** — создаёт VSE проект в Blender
2. **add_video_clip()** — добавляет movie strip на timeline
3. **add_text()** — добавляет text strip с позиционированием
4. **animate_text_*()** — добавляет keyframe анимации
5. **add_color_grade()** — adjustment strip с цветокоррекцией
6. **add_transition()** — CROSS / GAMMA_CROSS / WIPE между клипами
7. **render()** — рендер в MP4 через ffmpeg (H.264)

## Blender VSE API

Код использует нативный Blender Python API:

```python
# Создание sequence editor
bpy.context.scene.sequence_editor_create()

# Добавление видео
bpy.ops.sequencer.movie_strip_add(filepath="clip.mp4", frame_start=1, channel=1)

# Добавление текста
bpy.ops.sequencer.text_strip_add(frame_start=1, frame_end=60, channel=3)

# Анимация через keyframes
text_strip.blend_alpha = 0
text_strip.keyframe_insert("blend_alpha", frame=1)
text_strip.blend_alpha = 1
text_strip.keyframe_insert("blend_alpha", frame=15)

# Цветокоррекция
bpy.ops.sequencer.adjustment_strip_add(frame_start=1, frame_end=300, channel=7)

# Рендер
bpy.context.scene.render.image_settings.file_format = 'FFMPEG'
bpy.ops.render.render(animation=True)
```

## Технические детали

- **2925 строк** Python кода
- **15 методов** в BlenderVSEEditor
- **8 MCP инструментов**
- **3 стиля** с разными параметрами
- **5 типов анимации** текста
- **4 типа переходов** между клипами
- Разрешение: 1080x1920 (9:16), 30fps
- Выход: MP4 (H.264)
