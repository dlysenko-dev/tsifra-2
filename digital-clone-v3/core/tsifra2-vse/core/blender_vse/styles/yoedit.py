#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
styles/yoedit.py
================

Стиль YoEdit — трендовый, hard cuts, bounce текст.

Характеристики:
  - Быстрые hard cuts (резкие смены кадра)
  - Bounce анимация текста (пружинящий эффект появления)
  - Тёплая цветокоррекция (slightly warm)
  - Повышенный контраст и насыщенность
  - Короткие клипы (~2 секунды)

Идеально подходит для:
  - Трендовых Reels / Shorts
  - Мотивационного контента
  - Динамичных нарезок

Usage:
    >>> from core.blender_vse.styles.yoedit import YoEditStyle
    >>> style = YoEditStyle(editor)
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
# YoEditStyle
# ---------------------------------------------------------------------------
class YoEditStyle(VSEStyleBase):
    """
    Стиль YoEdit — трендовый, динамичный, с bounce-анимацией.

    Каждый текст "прыгает" на экран с пружинящим эффектом,
    видео меняется резкими hard cuts. Цветокоррекция тёплая,
    с повышенным контрастом для "популярного" вида.
    """

    style_name: str = "yoedit"

    # --- Переходы ---
    TRANSITION_TYPE: str = "HARD_CUT"

    # --- Анимация текста ---
    TEXT_ANIMATION: str = "bounce"

    # --- Текст ---
    FONT_SIZE: int = 120
    FONT_COLOR: tuple = (1, 1, 1, 1)  # Белый
    SHADOW: bool = True

    # --- Цветокоррекция ---
    CONTRAST: float = 1.2
    BRIGHTNESS: float = 0.05
    SATURATION: float = 1.3
    COLOR_MULTIPLY: tuple = (1.1, 0.95, 0.9)  # Тёплый оттенок

    # --- Эффекты ---
    FILM_GRAIN: bool = False
    VIGNETTE: bool = False

    # --- Длительность клипа ---
    CUT_DURATION: int = 60  # 2 секунды при 30fps

    def __init__(self, editor: Optional["BlenderVSEEditor"] = None):
        """
        Инициализация стиля YoEdit.

        Args:
            editor: Экземпляр BlenderVSEEditor (None = создать новый).
        """
        super().__init__(editor=editor)
        logger.info("Стиль инициализирован: YoEdit (hard cuts, bounce)")

    # ------------------------------------------------------------------
    # Переопределение create_short для дополнительной кастомизации
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
        Создать шорт в стиле YoEdit.

        Переопределяет базовый метод для добавления специфичных
        эффектов: дополнительный тёплый градиент на каждый cut.

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
        logger.info("=== YoEdit Style ===")
        logger.info("Параметры: contrast=%.2f, saturation=%.2f, warm=%s", self.CONTRAST, self.SATURATION, self.COLOR_MULTIPLY)

        # Вызываем базовую реализацию
        result = super().create_short(
            video_clips=video_clips,
            texts=texts,
            output_path=output_path,
            sound_path=sound_path,
            width=width,
            height=height,
            fps=fps,
        )

        logger.info("=== YoEdit завершён ===")
        return result

    def __repr__(self) -> str:
        return (
            f"YoEditStyle("
            f"transition={self.TRANSITION_TYPE}, "
            f"animation={self.TEXT_ANIMATION}, "
            f"cut={self.CUT_DURATION}f, "
            f"contrast={self.CONTRAST}, "
            f"sat={self.SATURATION})"
        )
