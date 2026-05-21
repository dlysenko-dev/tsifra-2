#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mcp_tools.py
============

MCP интеграция — регистрация инструментов Blender VSE в MCP-сервер.

Предоставляет набор инструментов для удалённого управления
Blender Video Sequence Editor через MCP (Model Context Protocol):

  - blender_vse_create_project : Создать новый VSE-проект
  - blender_vse_add_clip       : Добавить видео-клип
  - blender_vse_add_text       : Добавить текстовый оверлей
  - blender_vse_add_style      : Применить стиль (yoedit/gadzhi/merzliakov)
  - blender_vse_animate        : Анимировать текст
  - blender_vse_add_effect     : Добавить эффект (grain/vignette/grade)
  - blender_vse_render         : Рендер проекта в MP4

Usage:
    >>> from core.blender_vse.mcp_tools import register_blender_vse_tools
    >>> register_blender_vse_tools(mcp_layer)
"""

from __future__ import annotations

import logging
import os
from typing import Any, Callable, Dict, List, Optional

# Попытка импорта Blender API (bpy может быть недоступен вне Blender)
try:
    import bpy

    HAS_BPY = True
except ImportError:
    HAS_BPY = False

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# MCPTool dataclass (реализация если не импортирована из внешнего пакета)
# ---------------------------------------------------------------------------


class MCPTool:
    """
    Простая реализация MCP Tool для регистрации.

    Если используется внешний MCP-фреймворк — замените
    на соответствующий класс из фреймворка.
    """

    def __init__(
        self,
        name: str,
        description: str,
        handler: Callable[..., Any],
        parameters: Optional[Dict[str, Any]] = None,
    ):
        self.name = name
        self.description = description
        self.handler = handler
        self.parameters = parameters or {}

    def __repr__(self) -> str:
        return f"MCPTool(name='{self.name}', description='{self.description}')"


# ---------------------------------------------------------------------------
# Глобальное состояние редактора
# ---------------------------------------------------------------------------
# Храним активный экземпляр редактора между вызовами инструментов
_editor_instance = None
_current_style = None


def _get_editor(output_dir: str = "./output"):
    """
    Получить или создать экземпляр BlenderVSEEditor.

    Args:
        output_dir: Директория для выходных файлов.

    Returns:
        Экземпляр BlenderVSEEditor.
    """
    global _editor_instance
    if _editor_instance is None:
        from .editor import BlenderVSEEditor

        _editor_instance = BlenderVSEEditor(output_dir=output_dir)
    return _editor_instance


# =========================================================================
# Обработчики инструментов
# =========================================================================


def _handle_create_project(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Обработчик: blender_vse_create_project.

    Создаёт новый VSE-проект с указанными параметрами.

    Args:
        params: {
            "width": int (default: 1080),
            "height": int (default: 1920),
            "fps": int (default: 30),
            "duration_frames": int (default: 300),
            "output_dir": str (default: "./output"),
        }

    Returns:
        {"success": bool, "message": str, "project": dict}
    """
    try:
        width = params.get("width", 1080)
        height = params.get("height", 1920)
        fps = params.get("fps", 30)
        duration = params.get("duration_frames", 300)
        output_dir = params.get("output_dir", "./output")

        editor = _get_editor(output_dir)
        scene = editor.create_project(
            width=width,
            height=height,
            fps=fps,
            duration_frames=duration,
        )

        return {
            "success": True,
            "message": f"Проект создан: {width}x{height} @ {fps}fps, {duration} кадров",
            "project": {
                "width": width,
                "height": height,
                "fps": fps,
                "duration_frames": duration,
                "output_dir": output_dir,
            },
        }
    except Exception as exc:
        logger.error("Ошибка create_project: %s", exc)
        return {"success": False, "message": str(exc), "project": None}


def _handle_add_clip(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Обработчик: blender_vse_add_clip.

    Добавляет видео-клип на timeline.

    Args:
        params: {
            "filepath": str (required),
            "channel": int (default: 1),
            "frame_start": int (default: 1),
            "duration": int (optional),
        }

    Returns:
        {"success": bool, "message": str, "strip": dict}
    """
    try:
        filepath = params["filepath"]
        channel = params.get("channel", 1)
        frame_start = params.get("frame_start", 1)
        duration = params.get("duration", None)

        if not os.path.isfile(filepath):
            return {
                "success": False,
                "message": f"Файл не найден: {filepath}",
                "strip": None,
            }

        editor = _get_editor()
        strip = editor.add_video_clip(
            filepath=filepath,
            channel=channel,
            frame_start=frame_start,
            duration=duration,
        )

        return {
            "success": True,
            "message": f"Клип добавлен: {strip.name}",
            "strip": {
                "name": strip.name,
                "channel": strip.channel,
                "frame_start": strip.frame_start,
                "frame_end": strip.frame_final_end,
            },
        }
    except Exception as exc:
        logger.error("Ошибка add_clip: %s", exc)
        return {"success": False, "message": str(exc), "strip": None}


def _handle_add_text(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Обработчик: blender_vse_add_text.

    Добавляет текстовый оверлей с анимацией.

    Args:
        params: {
            "text": str (required),
            "channel": int (default: 3),
            "frame_start": int (default: 1),
            "duration": int (default: 75),
            "font_size": int (default: 100),
            "color": list [r, g, b, a] (default: [1, 1, 1, 1]),
            "position": list [x, y] (default: [0.5, 0.5]),
            "animation": str (default: "fade"),
        }

    Returns:
        {"success": bool, "message": str, "strip": dict}
    """
    try:
        text = params["text"]
        channel = params.get("channel", 3)
        frame_start = params.get("frame_start", 1)
        duration = params.get("duration", 75)
        frame_end = frame_start + duration
        font_size = params.get("font_size", 100)
        color = tuple(params.get("color", [1, 1, 1, 1]))
        position = tuple(params.get("position", [0.5, 0.5]))
        animation = params.get("animation", "fade")

        editor = _get_editor()
        strip = editor.add_text(
            text=text,
            channel=channel,
            frame_start=frame_start,
            frame_end=frame_end,
            font_size=font_size,
            color=color,
            position=position,
            shadow=True,
        )

        # Применяем анимацию
        animation = animation.lower()
        if animation == "fade":
            editor.animate_text_fade_in(strip, fade_frames=15)
        elif animation == "slide_up":
            editor.animate_text_slide_up(strip, slide_distance=0.1, fade_frames=15)
        elif animation == "bounce":
            editor.animate_text_bounce(strip, bounce_frames=20)
        elif animation == "zoom_in":
            editor.animate_text_zoom_in(strip, zoom_frames=15)
        elif animation == "typewriter":
            editor.animate_text_typewriter(strip, char_per_frame=2)
        else:
            editor.animate_text_fade_in(strip, fade_frames=15)

        return {
            "success": True,
            "message": f"Текст добавлен: '{text[:30]}...' с анимацией {animation}",
            "strip": {
                "name": strip.name,
                "text": text,
                "channel": strip.channel,
                "frame_start": strip.frame_start,
                "frame_end": frame_end,
                "animation": animation,
            },
        }
    except Exception as exc:
        logger.error("Ошибка add_text: %s", exc)
        return {"success": False, "message": str(exc), "strip": None}


def _handle_add_style(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Обработчик: blender_vse_add_style.

    Применяет стиль к текущему проекту и собирает шорт.

    Args:
        params: {
            "style_name": str (required, "yoedit" | "gadzhi" | "merzliakov"),
            "video_clips": list[str] (required),
            "texts": list[dict] (required),
            "output_path": str (optional),
            "sound_path": str (optional),
            "width": int (default: 1080),
            "height": int (default: 1920),
            "fps": int (default: 30),
        }

    Returns:
        {"success": bool, "message": str, "output_path": str}
    """
    global _current_style

    try:
        style_name = params["style_name"].lower().strip()
        video_clips = params.get("video_clips", [])
        texts = params.get("texts", [])
        output_path = params.get("output_path", None)
        sound_path = params.get("sound_path", None)
        width = params.get("width", 1080)
        height = params.get("height", 1920)
        fps = params.get("fps", 30)

        from .styles import get_style

        editor = _get_editor()
        style = get_style(style_name, editor=editor)
        _current_style = style

        result = style.create_short(
            video_clips=video_clips,
            texts=texts,
            output_path=output_path,
            sound_path=sound_path,
            width=width,
            height=height,
            fps=fps,
        )

        return {
            "success": True,
            "message": f"Шорт в стиле '{style_name}' создан: {result}",
            "output_path": result,
            "style": style_name,
        }
    except Exception as exc:
        logger.error("Ошибка add_style: %s", exc)
        return {"success": False, "message": str(exc), "output_path": None}


def _handle_animate(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Обработчик: blender_vse_animate.

    Анимирует существующий текстовый strip.

    Args:
        params: {
            "strip_name": str (required),
            "animation": str (required, "fade" | "slide_up" | "bounce" | "zoom_in" | "typewriter"),
        }

    Returns:
        {"success": bool, "message": str}
    """
    try:
        strip_name = params["strip_name"]
        animation = params.get("animation", "fade").lower()

        editor = _get_editor()
        se = editor.se

        if se is None or strip_name not in se.sequences_all:
            return {
                "success": False,
                "message": f"Strip '{strip_name}' не найден в timeline.",
            }

        strip = se.sequences_all[strip_name]

        if animation == "fade":
            editor.animate_text_fade_in(strip, fade_frames=15)
        elif animation == "slide_up":
            editor.animate_text_slide_up(strip, slide_distance=0.1, fade_frames=15)
        elif animation == "bounce":
            editor.animate_text_bounce(strip, bounce_frames=20)
        elif animation == "zoom_in":
            editor.animate_text_zoom_in(strip, zoom_frames=15)
        elif animation == "typewriter":
            editor.animate_text_typewriter(strip, char_per_frame=2)
        else:
            return {
                "success": False,
                "message": f"Неизвестная анимация: {animation}",
            }

        return {
            "success": True,
            "message": f"Анимация {animation} применена к '{strip_name}'",
        }
    except Exception as exc:
        logger.error("Ошибка animate: %s", exc)
        return {"success": False, "message": str(exc)}


def _handle_add_effect(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Обработчик: blender_vse_add_effect.

    Добавляет эффект к проекту.

    Args:
        params: {
            "effect_type": str (required, "grain" | "vignette" | "grade"),
            "channel": int (default: 7),
            "frame_start": int (default: 1),
            "frame_end": int (default: 300),
            "intensity": float (default: 0.1),
        }

    Returns:
        {"success": bool, "message": str}
    """
    try:
        effect_type = params["effect_type"].lower()
        channel = params.get("channel", 7)
        frame_start = params.get("frame_start", 1)
        frame_end = params.get("frame_end", 300)
        intensity = params.get("intensity", 0.1)

        editor = _get_editor()

        if effect_type == "grain":
            editor.add_film_grain(
                channel=channel,
                frame_start=frame_start,
                frame_end=frame_end,
                intensity=intensity,
            )
            msg = f"Film grain добавлен: intensity={intensity}"

        elif effect_type == "vignette":
            editor.add_vignette(
                channel=channel,
                frame_start=frame_start,
                frame_end=frame_end,
                intensity=intensity,
            )
            msg = f"Vignette добавлен: intensity={intensity}"

        elif effect_type == "grade":
            contrast = params.get("contrast", 1.0)
            brightness = params.get("brightness", 0.0)
            saturation = params.get("saturation", 1.0)
            color_multiply = tuple(params.get("color_multiply", [1, 1, 1]))
            editor.add_color_grade(
                channel=channel,
                frame_start=frame_start,
                frame_end=frame_end,
                contrast=contrast,
                brightness=brightness,
                saturation=saturation,
                color_multiply=color_multiply,
            )
            msg = f"Color grade добавлен: contrast={contrast}, brightness={brightness}"

        else:
            return {
                "success": False,
                "message": f"Неизвестный эффект: {effect_type}",
            }

        return {"success": True, "message": msg}

    except Exception as exc:
        logger.error("Ошибка add_effect: %s", exc)
        return {"success": False, "message": str(exc)}


def _handle_render(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Обработчик: blender_vse_render.

    Рендерит проект в MP4.

    Args:
        params: {
            "output_path": str (optional),
            "save_project": bool (default: True),
        }

    Returns:
        {"success": bool, "message": str, "output_path": str}
    """
    try:
        output_path = params.get("output_path", None)
        save_project = params.get("save_project", True)

        editor = _get_editor()

        # Сохраняем .blend если нужно
        if save_project:
            blend_path = editor.save_project()
            logger.info("Проект сохранён перед рендером: %s", blend_path)

        # Рендер
        result = editor.render(output_path)

        return {
            "success": True,
            "message": f"Рендер завершён: {result}",
            "output_path": result,
        }
    except Exception as exc:
        logger.error("Ошибка render: %s", exc)
        return {"success": False, "message": str(exc), "output_path": None}


def _handle_get_info(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Обработчик: blender_vse_get_info.

    Возвращает информацию о текущем проекте.

    Args:
        params: {} (пустой)

    Returns:
        {"success": bool, "project": dict}
    """
    try:
        editor = _get_editor()
        se = editor.se

        strips_info = []
        if se and se.sequences_all:
            for name, strip in se.sequences_all.items():
                strips_info.append(
                    {
                        "name": name,
                        "type": strip.type,
                        "channel": getattr(strip, "channel", None),
                        "frame_start": getattr(strip, "frame_start", None),
                        "frame_end": getattr(strip, "frame_final_end", None),
                    }
                )

        return {
            "success": True,
            "project": {
                "editor": repr(editor),
                "current_style": getattr(_current_style, "style_name", None),
                "strips_count": len(strips_info),
                "strips": strips_info,
            },
        }
    except Exception as exc:
        logger.error("Ошибка get_info: %s", exc)
        return {"success": False, "project": None}


# =========================================================================
# Регистрация инструментов
# =========================================================================


# Описания параметров для каждого инструмента
_TOOL_PARAMS = {
    "blender_vse_create_project": {
        "type": "object",
        "properties": {
            "width": {"type": "integer", "default": 1080, "description": "Ширина видео"},
            "height": {"type": "integer", "default": 1920, "description": "Высота видео"},
            "fps": {"type": "integer", "default": 30, "description": "Кадров в секунду"},
            "duration_frames": {"type": "integer", "default": 300, "description": "Длительность в кадрах"},
            "output_dir": {"type": "string", "default": "./output", "description": "Директория вывода"},
        },
    },
    "blender_vse_add_clip": {
        "type": "object",
        "properties": {
            "filepath": {"type": "string", "required": True, "description": "Путь к видео-файлу"},
            "channel": {"type": "integer", "default": 1, "description": "Канал"},
            "frame_start": {"type": "integer", "default": 1, "description": "Начальный кадр"},
            "duration": {"type": "integer", "description": "Длительность в кадрах (опционально)"},
        },
        "required": ["filepath"],
    },
    "blender_vse_add_text": {
        "type": "object",
        "properties": {
            "text": {"type": "string", "required": True, "description": "Текст"},
            "channel": {"type": "integer", "default": 3, "description": "Канал"},
            "frame_start": {"type": "integer", "default": 1, "description": "Начальный кадр"},
            "duration": {"type": "integer", "default": 75, "description": "Длительность"},
            "font_size": {"type": "integer", "default": 100, "description": "Размер шрифта"},
            "color": {"type": "array", "default": [1, 1, 1, 1], "description": "RGBA цвет"},
            "position": {"type": "array", "default": [0.5, 0.5], "description": "Позиция [x, y]"},
            "animation": {"type": "string", "default": "fade", "description": "Тип анимации"},
        },
        "required": ["text"],
    },
    "blender_vse_add_style": {
        "type": "object",
        "properties": {
            "style_name": {"type": "string", "required": True, "description": "yoedit | gadzhi | merzliakov"},
            "video_clips": {"type": "array", "required": True, "description": "Список путей к видео"},
            "texts": {"type": "array", "required": True, "description": "Список текстовых блоков"},
            "output_path": {"type": "string", "description": "Путь для MP4"},
            "sound_path": {"type": "string", "description": "Путь к музыке"},
            "width": {"type": "integer", "default": 1080},
            "height": {"type": "integer", "default": 1920},
            "fps": {"type": "integer", "default": 30},
        },
        "required": ["style_name", "video_clips", "texts"],
    },
    "blender_vse_animate": {
        "type": "object",
        "properties": {
            "strip_name": {"type": "string", "required": True, "description": "Имя strip"},
            "animation": {"type": "string", "required": True, "description": "fade | slide_up | bounce | zoom_in | typewriter"},
        },
        "required": ["strip_name", "animation"],
    },
    "blender_vse_add_effect": {
        "type": "object",
        "properties": {
            "effect_type": {"type": "string", "required": True, "description": "grain | vignette | grade"},
            "channel": {"type": "integer", "default": 7},
            "frame_start": {"type": "integer", "default": 1},
            "frame_end": {"type": "integer", "default": 300},
            "intensity": {"type": "number", "default": 0.1},
            "contrast": {"type": "number", "default": 1.0},
            "brightness": {"type": "number", "default": 0.0},
            "saturation": {"type": "number", "default": 1.0},
            "color_multiply": {"type": "array", "default": [1, 1, 1]},
        },
        "required": ["effect_type"],
    },
    "blender_vse_render": {
        "type": "object",
        "properties": {
            "output_path": {"type": "string", "description": "Путь для MP4"},
            "save_project": {"type": "boolean", "default": True, "description": "Сохранить .blend"},
        },
    },
    "blender_vse_get_info": {
        "type": "object",
        "properties": {},
    },
}


def register_blender_vse_tools(mcp_layer) -> List[str]:
    """
    Зарегистрировать Blender VSE инструменты в MCP-сервере.

    Регистрирует 8 инструментов:
      1. blender_vse_create_project — Создать проект
      2. blender_vse_add_clip       — Добавить видео-клип
      3. blender_vse_add_text       — Добавить текст
      4. blender_vse_add_style      — Применить стиль
      5. blender_vse_animate        — Анимировать текст
      6. blender_vse_add_effect     — Добавить эффект
      7. blender_vse_render         — Рендер MP4
      8. blender_vse_get_info       — Информация о проекте

    Args:
        mcp_layer: Объект MCP-сервера с методом register_tool().
                   Должен реализовывать интерфейс:
                   mcp_layer.register_tool(MCPTool(...))

    Returns:
        Список имён зарегистрированных инструментов.

    Example:
        >>> from core.blender_vse.mcp_tools import register_blender_vse_tools
        >>> names = register_blender_vse_tools(mcp_server)
        >>> print(names)
        ['blender_vse_create_project', 'blender_vse_add_clip', ...]
    """
    tools = [
        MCPTool(
            name="blender_vse_create_project",
            description="Создать новый VSE-проект в Blender. "
                        "Параметры: width, height, fps, duration_frames, output_dir",
            handler=_handle_create_project,
            parameters=_TOOL_PARAMS["blender_vse_create_project"],
        ),
        MCPTool(
            name="blender_vse_add_clip",
            description="Добавить видео-клип в timeline. "
                        "Параметры: filepath (обязательный), channel, frame_start, duration",
            handler=_handle_add_clip,
            parameters=_TOOL_PARAMS["blender_vse_add_clip"],
        ),
        MCPTool(
            name="blender_vse_add_text",
            description="Добавить текстовый оверлей с анимацией. "
                        "Параметры: text (обязательный), channel, frame_start, duration, "
                        "font_size, color, position, animation",
            handler=_handle_add_text,
            parameters=_TOOL_PARAMS["blender_vse_add_text"],
        ),
        MCPTool(
            name="blender_vse_add_style",
            description="Применить стиль (yoedit/gadzhi/merzliakov) и собрать шорт. "
                        "Параметры: style_name, video_clips, texts, output_path, sound_path",
            handler=_handle_add_style,
            parameters=_TOOL_PARAMS["blender_vse_add_style"],
        ),
        MCPTool(
            name="blender_vse_animate",
            description="Анимировать текстовый strip. "
                        "Параметры: strip_name (обязательный), animation (обязательный)",
            handler=_handle_animate,
            parameters=_TOOL_PARAMS["blender_vse_animate"],
        ),
        MCPTool(
            name="blender_vse_add_effect",
            description="Добавить эффект (grain/vignette/grade). "
                        "Параметры: effect_type (обязательный), channel, frame_start, frame_end, intensity",
            handler=_handle_add_effect,
            parameters=_TOOL_PARAMS["blender_vse_add_effect"],
        ),
        MCPTool(
            name="blender_vse_render",
            description="Рендер проекта в MP4. "
                        "Параметры: output_path, save_project",
            handler=_handle_render,
            parameters=_TOOL_PARAMS["blender_vse_render"],
        ),
        MCPTool(
            name="blender_vse_get_info",
            description="Получить информацию о текущем проекте (strips, стиль, etc).",
            handler=_handle_get_info,
            parameters=_TOOL_PARAMS["blender_vse_get_info"],
        ),
    ]

    registered = []
    for tool in tools:
        try:
            mcp_layer.register_tool(tool)
            registered.append(tool.name)
            logger.info("Зарегистрирован инструмент: %s", tool.name)
        except Exception as exc:
            logger.error("Ошибка регистрации %s: %s", tool.name, exc)

    logger.info("Всего зарегистрировано: %d/%d инструментов", len(registered), len(tools))
    return registered


# ---------------------------------------------------------------------------
# Альтернативная регистрация (для прямого вызова без MCP-сервера)
# ---------------------------------------------------------------------------

_TOOL_HANDLERS = {
    "blender_vse_create_project": _handle_create_project,
    "blender_vse_add_clip": _handle_add_clip,
    "blender_vse_add_text": _handle_add_text,
    "blender_vse_add_style": _handle_add_style,
    "blender_vse_animate": _handle_animate,
    "blender_vse_add_effect": _handle_add_effect,
    "blender_vse_render": _handle_render,
    "blender_vse_get_info": _handle_get_info,
}


def call_tool(tool_name: str, params: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Вызвать инструмент по имени напрямую (без MCP-сервера).

    Args:
        tool_name: Имя инструмента (например, "blender_vse_create_project").
        params:    Параметры вызова (dict).

    Returns:
        Результат вызова инструмента (dict).

    Example:
        >>> result = call_tool("blender_vse_create_project", {"width": 1080, "height": 1920})
        >>> print(result["message"])
    """
    params = params or {}

    if tool_name not in _TOOL_HANDLERS:
        return {
            "success": False,
            "message": f"Инструмент '{tool_name}' не найден. "
                       f"Доступные: {list(_TOOL_HANDLERS.keys())}",
        }

    handler = _TOOL_HANDLERS[tool_name]
    return handler(params)


def list_tools() -> List[Dict[str, str]]:
    """
    Получить список всех доступных инструментов.

    Returns:
        Список словарей с name и description.
    """
    return [
        {"name": name, "description": tool.description}
        for name, tool in {
            "blender_vse_create_project": MCPTool(
                name="blender_vse_create_project",
                description="Создать новый VSE-проект в Blender",
                handler=_handle_create_project,
            ),
            "blender_vse_add_clip": MCPTool(
                name="blender_vse_add_clip",
                description="Добавить видео-клип в timeline",
                handler=_handle_add_clip,
            ),
            "blender_vse_add_text": MCPTool(
                name="blender_vse_add_text",
                description="Добавить текстовый оверлей",
                handler=_handle_add_text,
            ),
            "blender_vse_add_style": MCPTool(
                name="blender_vse_add_style",
                description="Применить стиль (yoedit/gadzhi/merzliakov)",
                handler=_handle_add_style,
            ),
            "blender_vse_animate": MCPTool(
                name="blender_vse_animate",
                description="Анимировать текстовый strip",
                handler=_handle_animate,
            ),
            "blender_vse_add_effect": MCPTool(
                name="blender_vse_add_effect",
                description="Добавить эффект (grain/vignette/grade)",
                handler=_handle_add_effect,
            ),
            "blender_vse_render": MCPTool(
                name="blender_vse_render",
                description="Рендер проекта в MP4",
                handler=_handle_render,
            ),
            "blender_vse_get_info": MCPTool(
                name="blender_vse_get_info",
                description="Информация о текущем проекте",
                handler=_handle_get_info,
            ),
        }.items()
    ]
