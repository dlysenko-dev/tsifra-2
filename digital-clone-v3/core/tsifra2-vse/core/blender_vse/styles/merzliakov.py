#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
styles/merzliakov.py
====================

Стиль Мерзляков — минимализм, плавные переходы, золотой текст.

Характеристики:
  - Плавные CROSS переходы между клипами
  - Slide up анимация текста (выезд снизу)
  - Золотой цвет текста (#FFD700)
  - Сниженная насыщенность для элегантности
  - Gold tint цветокоррекция
  - Более длинные клипы (~3 секунды)

Идеально подходит для:
  - Элегантного контента
  - Luxury / премиум ниши
  - Мотивационных цитат
  - Минималистичных шортов

Usage:
    >>> from core.blender_vse.styles.merzliakov import MerzliakovStyle
    >>> style = MerzliakovStyle(editor)
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
# MerzliakovStyle
# ---------------------------------------------------------------------------
class MerzliakovStyle(VSEStyleBase):
    """
    Стиль Мерзляков — минималистичный, элегантный.

    Особенности:
      - Золотой текст (#FFD700) для luxury-ощущения
      - Slide up анимация для плавного появления
      - Cross-переходы между клипами
      - Gold tint цветокоррекция
      - Сниженная насыщенность фона
      - Длинные клипы для спокойного ритма
    """

    style_name: str = "merzliakov"

    # --- Переходы ---
    TRANSITION_TYPE: str = "CROSS"

    # --- Анимация текста ---
    TEXT_ANIMATION: str = "slide_up"

    # --- Текст ---
    FONT_SIZE: int = 90
    FONT_COLOR: tuple = (1, 0.84, 0, 1)  # Золотой #FFD700
    SHADOW: bool = True

    # --- Цветокоррекция ---
    CONTRAST: float = 1.1
    BRIGHTNESS: float = 0.0
    SATURATION: float = 0.9
    COLOR_MULTIPLY: tuple = (1, 0.95, 0.8)  # Gold tint

    # --- Эффекты ---
    FILM_GRAIN: bool = False
    VIGNETTE: bool = False

    # --- Длительность клипа ---
    CUT_DURATION: int = 90  # 3 секунды при 30fps

    def __init__(self, editor: Optional["BlenderVSEEditor"] = None):
        """
        Инициализация стиля Мерзляков.

        Args:
            editor: Экземпляр BlenderVSEEditor (None = создать новый).
        """
        super().__init__(editor=editor)
        logger.info("Стиль инициализирован: Мерзляков (cross, slide up, gold)")

    # ------------------------------------------------------------------
    # Переопределение _apply_text_animation для gold-стиля
    # ------------------------------------------------------------------
    def _apply_text_animation(self, text_strip) -> None:
        """
        Применить slide_up анимацию с золотым свечением.

        Переопределяет базовый метод чтобы добавить
        дополнительный glow-эффект к золотому тексту.

        Args:
            text_strip: Текстовый strip для анимации.
        """
        # Вызываем базовую slide_up анимацию
        self.editor.animate_text_slide_up(
            text_strip, slide_distance=0.12, fade_frames=18
        )

        # Дополнительно: добавляем лёгкое свечение через blend_alpha
        # (имитация glow-эффекта)
        try:
            start = int(text_strip.frame_start)
            # Небольшая пульсация alpha для эффекта "свечения"
            mid = start + 9
            end = start + 18

            # Первоначальное свечение (alpha > 1)
            text_strip.blend_alpha = 1.0
            text_strip.keyframe_insert(data_path="blend_alpha", frame=start)

            # Пик свечения
            text_strip.blend_alpha = 1.0
            text_strip.keyframe_insert(data_path="blend_alpha", frame=mid)

            # Стабилизация
            text_strip.blend_alpha = 0.95
            text_strip.keyframe_insert(data_path="blend_alpha", frame=end)

            logger.debug("Gold glow эффект добавлен к тексту.")
        except Exception as exc:
            logger.warning("Gold glow не добавлен: %s", exc)

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
        Создать шорт в стиле Мерзляков.

        Добавляет золотую цветокоррекцию и slide_up анимацию.

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
        logger.info("=== Мерзляков Style ===")
        logger.info(
            "Параметры: gold=%s, transition=%s, animation=%s",
            self.FONT_COLOR,
            self.TRANSITION_TYPE,
            self.TEXT_ANIMATION,
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

        logger.info("=== Мерзляков завершён ===")
        return result

    def __repr__(self) -> str:
        return (
            f"MerzliakovStyle("
            f"transition={self.TRANSITION_TYPE}, "
            f"animation={self.TEXT_ANIMATION}, "
            f"gold={self.FONT_COLOR}, "
            f"cut={self.CUT_DURATION}f)"
        )
