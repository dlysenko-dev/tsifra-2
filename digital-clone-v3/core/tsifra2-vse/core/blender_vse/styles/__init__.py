#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
styles/__init__.py
==================

Регистрация всех VSE-стилей.

Каждый стиль — это предустановленный набор параметров для создания
шортов с определённой визуальной эстетикой:

  - YoEditStyle   : Трендовый, hard cuts, bounce текст
  - GadzhiStyle   : Премиум, film grain, vignette, warm grade
  - MerzliakovStyle : Минимализм, плавные переходы, золотой текст

Usage:
    >>> from core.blender_vse.styles import YoEditStyle, GadzhiStyle, MerzliakovStyle
    >>> style = YoEditStyle(editor)
    >>> style.create_short(clips, texts, output_path)
"""

from .base import VSEStyleBase
from .yoedit import YoEditStyle
from .gadzhi import GadzhiStyle
from .merzliakov import MerzliakovStyle

# Реестр стилей по имени
STYLE_REGISTRY = {
    "base": VSEStyleBase,
    "yoedit": YoEditStyle,
    "gadzhi": GadzhiStyle,
    "merzliakov": MerzliakovStyle,
}


def get_style(style_name: str, editor=None):
    """
    Получить класс стиля по имени.

    Args:
        style_name: Имя стиля (base, yoedit, gadzhi, merzliakov).
        editor:     Экземпляр BlenderVSEEditor (опционально).

    Returns:
        Экземпляр стиля.

    Raises:
        ValueError: Если стиль не найден.
    """
    style_name = style_name.lower().strip()
    if style_name not in STYLE_REGISTRY:
        available = ", ".join(STYLE_REGISTRY.keys())
        raise ValueError(f"Стиль '{style_name}' не найден. Доступные: {available}")
    return STYLE_REGISTRY[style_name](editor=editor)


__all__ = [
    "VSEStyleBase",
    "YoEditStyle",
    "GadzhiStyle",
    "MerzliakovStyle",
    "STYLE_REGISTRY",
    "get_style",
]
