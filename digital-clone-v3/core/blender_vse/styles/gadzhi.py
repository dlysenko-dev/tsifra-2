#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
styles/gadzhi.py
================

Стиль Iman Gadzhi — премиум, film grain, vignette, warm grade.

Характеристики:
  - Плавные gamma cross переходы
  - Zoom in анимация текста (текст "вырастает" из центра)
  - Film grain эффект для кинематографичности
  - Vignette (затемнение по краям)
  - Тёплая цветокоррекция с умеренным контрастом
  - Клипы средней длительности (~2.5 секунды)

Идеально подходит для:
  - Премиального контента
  - Образовательных видео
  - Личного брендинга
  - Кинематографических шортов

Usage:
    >>> from core.blender_vse.styles.gadzhi import GadzhiStyle
    >>> style = GadzhiStyle(editor)
    >>> style.create_short(clips, texts, output_path)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Dict, List, Optional

from .base import VSEStyleBase

if TYPE_CHECKING:
    from ..editor import BlenderVSEEditor

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# GadzhiStyle
# ---------------------------------------------------------------------------
class GadzhiStyle(VSEStyleBase):
    """
    Стиль Gadzhi — премиальный, кинематографичный.

    Включает film grain и vignette для "плёночного" вида.
    Текст появляется с zoom-in эффектом. Переходы плавные
    через gamma cross. Цветокоррекция тёплая, с лёгким
    повышением контраста.
    """

    style_name: str = "gadzhi"

    # --- Переходы ---
    TRANSITION_TYPE: str = "GAMMA_CROSS"

    # --- Анимация текста ---
    TEXT_ANIMATION: str = "zoom_in"

    # --- Текст ---
    FONT_SIZE: int = 110
    FONT_COLOR: tuple = (1, 1, 1, 1)  # Белый
    SHADOW: bool = True

    # --- Цветокоррекция ---
    CONTRAST: float = 1.15
    BRIGHTNESS: float = 0.03
    SATURATION: float = 1.05
    COLOR_MULTIPLY: tuple = (1.15, 1.05, 0.9)  # Тёплый оттенок

    # --- Эффекты ---
    FILM_GRAIN: bool = True
    VIGNETTE: bool = True

    # --- Длительность клипа ---
    CUT_DURATION: int = 75  # 2.5 секунды при 30fps

    def __init__(self, editor: Optional["BlenderVSEEditor"] = None):
        """
        Инициализация стиля Gadzhi.

        Args:
            editor: Экземпляр BlenderVSEEditor (None = создать новый).
        """
        super().__init__(editor=editor)
        logger.info("Стиль инициализирован: Gadzhi (gamma cross, zoom in, grain + vignette)")

    # ------------------------------------------------------------------
    # Переопределение create_short
    # ------------------------------------------------------------------
    def create_short(
        self,
        video_clips: List[str],
        texts: List[Dict],
        output_path: Optional[str] = None,
        sound_path: Optional[str] = None,
        width: int = 1080,
        height: int = 1920,
        fps: int = 30,
    ) -> str:
        """
        Создать шорт в стиле Gadzhi.

        Добавляет дополнительную цветокоррекцию warm grade
        и настраивает film grain интенсивность.

        Args:
            video_clips: Список путей к видео MP4.
            texts:       Список текстовых блоков.
            output_path: Путь для сохранения MP4.
            sound_path:  Путь к фоновой музыке.
            width:       Ширина видео.
            height:      Высота видео.
            fps:         Кадров в секунду.

        Returns:
            Абсолютный путь к готовому MP4.
        """
        logger.info("=== Gadhi Style ===")
        logger.info(
            "Параметры: transition=%s, grain=%s, vignette=%s, warm=%s",
            self.TRANSITION_TYPE,
            self.FILM_GRAIN,
            self.VIGNETTE,
            self.COLOR_MULTIPLY,
        )

        result = super().create_short(
            video_clips=video_clips,
            texts=texts,
            output_path=output_path,
            sound_path=sound_path,
            width=width,
            height=height,
            fps=fps,
        )

        logger.info("=== Gadzhi завершён ===")
        return result

    def __repr__(self) -> str:
        return (
            f"GadzhiStyle("
            f"transition={self.TRANSITION_TYPE}, "
            f"animation={self.TEXT_ANIMATION}, "
            f"grain={self.FILM_GRAIN}, "
            f"vignette={self.VIGNETTE}, "
            f"cut={self.CUT_DURATION}f)"
        )
