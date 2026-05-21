#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
styles/base.py
==============

Базовый класс VSEStyleBase — шаблон для всех VSE-стилей.

Каждый подкласс определяет набор параметров (переходы, анимации,
цветокоррекция) и реализует метод create_short() для сборки
видео из клипов и текста.

Архитектура стилей:
    1. Определить параметры (класс-переменные)
    2. Переопределить create_short() или использовать базовый
    3. Вызвать editor-методы для сборки timeline
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    from ..editor import BlenderVSEEditor

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# VSEStyleBase
# ---------------------------------------------------------------------------
class VSEStyleBase:
    """
    Базовый класс для всех VSE-стилей.

    Предоставляет:
      - Параметры стиля (переопределяются в подклассах)
      - Метод create_short() — сборка шорта из клипов и текста
      - Хелперы для размещения элементов на timeline

    Параметры стиля:
      TRANSITION_TYPE : Тип перехода (HARD_CUT | CROSS | GAMMA_CROSS | WIPE)
      TEXT_ANIMATION  : Тип анимации текста (fade | slide_up | bounce | zoom_in | typewriter)
      FONT_SIZE       : Размер шрифта
      FONT_COLOR      : RGBA цвет текста
      SHADOW          : Использовать тень
      CONTRAST        : Контраст
      BRIGHTNESS      : Яркость
      SATURATION      : Насыщенность
      COLOR_MULTIPLY  : RGB множитель цвета
      FILM_GRAIN      : Включить film grain
      VIGNETTE        : Включить vignette
      CUT_DURATION    : Длительность одного cut в кадрах
    """

    style_name: str = "base"

    # --- Параметры стиля (переопределяются в подклассах) ---
    TRANSITION_TYPE: str = "HARD_CUT"  # HARD_CUT | CROSS | GAMMA_CROSS | WIPE
    TEXT_ANIMATION: str = "fade_slide"  # fade | slide_up | bounce | zoom_in | typewriter
    FONT_SIZE: int = 100
    FONT_COLOR: Tuple[float, float, float, float] = (1, 1, 1, 1)  # белый
    SHADOW: bool = True
    CONTRAST: float = 1.0
    BRIGHTNESS: float = 0.0
    SATURATION: float = 1.0
    COLOR_MULTIPLY: Tuple[float, float, float] = (1, 1, 1)
    FILM_GRAIN: bool = False
    VIGNETTE: bool = False
    CUT_DURATION: int = 75  # кадров (2.5s при 30fps)

    # --- Каналы на timeline ---
    CHANNEL_VIDEO: int = 1
    CHANNEL_TEXT: int = 3
    CHANNEL_TRANSITION: int = 5
    CHANNEL_COLORGRADE: int = 7
    CHANNEL_EFFECTS: int = 9
    CHANNEL_SOUND: int = 11

    def __init__(self, editor: Optional["BlenderVSEEditor"] = None):
        """
        Инициализация стиля.

        Args:
            editor: Экземпляр BlenderVSEEditor. Если None — создаётся новый.
        """
        if editor is None:
            # Отложенный импорт чтобы избежать циклической зависимости
            from ..editor import BlenderVSEEditor

            editor = BlenderVSEEditor()
        self.editor: "BlenderVSEEditor" = editor

    # ------------------------------------------------------------------
    # Основной метод: сборка шорта
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
        Создать шорт из видео-клипов и текста.

        Метод выполняет полный pipeline:
          1. Создание проекта
          2. Размещение видео-клипов на timeline с переходами
          3. Добавление текстовых оверлеев с анимацией
          4. Цветокоррекция (contrast, brightness, saturation)
          5. Эффекты (film grain, vignette)
          6. Звуковая дорожка
          7. Рендер в MP4

        Args:
            video_clips: Список путей к видео MP4.
            texts:       Список текстовых блоков.
                         Каждый блок: {
                             "text": str,
                             "start_frame": int,
                             "duration": int,
                             "channel": int (optional),
                             "font_size": int (optional),
                             "color": tuple (optional),
                             "position": tuple (optional),
                         }
            output_path: Путь для сохранения MP4 (None = auto).
            sound_path:  Путь к фоновой музыке (None = без музыки).
            width:       Ширина видео.
            height:      Высота видео.
            fps:         Кадров в секунду.

        Returns:
            Абсолютный путь к готовому MP4.
        """
        try:
            logger.info("=== Создание шорта в стиле '%s' ===", self.style_name)
            logger.info("Клипов: %d, Текстовых блоков: %d", len(video_clips), len(texts))

            # --- Шаг 1: Рассчитать общую длительность ---
            total_duration = self._calculate_duration(video_clips, texts)
            logger.info("Общая длительность: %d кадров (%.1f сек)", total_duration, total_duration / fps)

            # --- Шаг 2: Создать проект ---
            self.editor.create_project(
                width=width,
                height=height,
                fps=fps,
                duration_frames=total_duration,
            )

            # --- Шаг 3: Разместить видео-клипы ---
            video_strips = self._arrange_video_clips(video_clips, fps)

            # --- Шаг 4: Добавить переходы между клипами ---
            self._add_transitions_between_clips(video_strips)

            # --- Шаг 5: Добавить текстовые оверлеи ---
            self._add_text_overlays(texts, fps)

            # --- Шаг 6: Цветокоррекция ---
            self._apply_color_grading(total_duration)

            # --- Шаг 7: Эффекты (grain, vignette) ---
            self._apply_effects(total_duration)

            # --- Шаг 8: Звуковая дорожка ---
            if sound_path and os.path.isfile(sound_path):
                self.editor.add_sound(
                    filepath=sound_path,
                    channel=self.CHANNEL_SOUND,
                    frame_start=1,
                    volume=0.3,
                )
                logger.info("Фоновая музыка добавлена: %s", sound_path)

            # --- Шаг 9: Рендер ---
            result_path = self.editor.render(output_path)
            logger.info("=== Шорт завершён: %s ===", result_path)
            return result_path

        except Exception as exc:
            logger.error("Ошибка create_short: %s", exc)
            raise

    # ------------------------------------------------------------------
    # Внутренние хелперы
    # ------------------------------------------------------------------
    def _calculate_duration(
        self, video_clips: List[str], texts: List[Dict]
    ) -> int:
        """
        Рассчитать общую длительность проекта.

        Берёт максимум из:
          - Суммарной длительности видео-клипов
          - Последнего кадра текста

        Args:
            video_clips: Список путей к видео.
            texts:       Список текстовых блоков.

        Returns:
            Общая длительность в кадрах.
        """
        # Длительность от видео: каждый клип = CUT_DURATION
        video_duration = len(video_clips) * self.CUT_DURATION

        # Длительность от текста
        text_duration = 0
        for txt in texts:
            start = txt.get("start_frame", 1)
            duration = txt.get("duration", self.CUT_DURATION)
            text_duration = max(text_duration, start + duration)

        # Берём максимум + небольшой запас
        total = max(video_duration, text_duration) + 5
        return max(total, 30)  # Минимум 30 кадров

    def _arrange_video_clips(
        self, video_clips: List[str], fps: int
    ) -> List:
        """
        Разместить видео-клипы на timeline последовательно.

        Args:
            video_clips: Список путей к видео.
            fps:         Кадров в секунду.

        Returns:
            Список созданных video strips.
        """
        strips = []
        current_frame = 1

        for i, clip_path in enumerate(video_clips):
            if not os.path.isfile(clip_path):
                logger.warning("Видео пропущено (не найдено): %s", clip_path)
                continue

            try:
                strip = self.editor.add_video_clip(
                    filepath=clip_path,
                    channel=self.CHANNEL_VIDEO,
                    frame_start=current_frame,
                    duration=self.CUT_DURATION,
                )
                strips.append(strip)
                current_frame += self.CUT_DURATION
                logger.info(
                    "Клип %d/%d размещён: frame=%d",
                    i + 1,
                    len(video_clips),
                    strip.frame_start,
                )
            except Exception as exc:
                logger.error("Ошибка размещения клипа %s: %s", clip_path, exc)

        return strips

    def _add_transitions_between_clips(self, video_strips: List) -> None:
        """
        Добавить переходы между последовательными клипами.

        Args:
            video_strips: Список video strips.
        """
        if self.TRANSITION_TYPE == "HARD_CUT" or len(video_strips) < 2:
            return  # Hard cut — без переходов

        transition_duration = min(8, self.CUT_DURATION // 4)  # 8 кадров или 1/4 клипа

        for i in range(len(video_strips) - 1):
            strip1 = video_strips[i]
            strip2 = video_strips[i + 1]

            # Переход в конце первого клипа
            trans_start = int(strip1.frame_final_end) - transition_duration
            trans_end = int(strip1.frame_final_end) + transition_duration // 2

            try:
                self.editor.add_transition(
                    strip1=strip1,
                    strip2=strip2,
                    channel=self.CHANNEL_TRANSITION,
                    frame_start=trans_start,
                    frame_end=trans_end,
                    transition_type=self.TRANSITION_TYPE,
                )
                logger.info(
                    "Переход %s между клипами %d-%d",
                    self.TRANSITION_TYPE,
                    i,
                    i + 1,
                )
            except Exception as exc:
                logger.warning("Переход не создан: %s", exc)

    def _add_text_overlays(self, texts: List[Dict], fps: int) -> None:
        """
        Добавить текстовые оверлеи с анимацией.

        Args:
            texts: Список текстовых блоков.
            fps:   Кадров в секунду.
        """
        for i, txt_data in enumerate(texts):
            try:
                text = txt_data["text"]
                start_frame = txt_data.get("start_frame", 1)
                duration = txt_data.get("duration", self.CUT_DURATION)
                end_frame = start_frame + duration

                # Позиция текста (по умолчанию — центр)
                position = txt_data.get("position", (0.5, 0.5))

                # Дополнительные параметры
                font_size = txt_data.get("font_size", self.FONT_SIZE)
                color = txt_data.get("color", self.FONT_COLOR)
                shadow = txt_data.get("shadow", self.SHADOW)
                channel = txt_data.get("channel", self.CHANNEL_TEXT)

                # Создаём текстовый strip
                text_strip = self.editor.add_text(
                    text=text,
                    channel=channel + i,  # Разные каналы для каждого текста
                    frame_start=start_frame,
                    frame_end=end_frame,
                    font_size=font_size,
                    color=color,
                    position=position,
                    shadow=shadow,
                )

                # Применяем анимацию в зависимости от стиля
                self._apply_text_animation(text_strip)

                logger.info(
                    'Текст %d добавлен: "%s" frames=%d-%d',
                    i + 1,
                    text,
                    start_frame,
                    end_frame,
                )

            except Exception as exc:
                logger.error("Ошибка добавления текста %d: %s", i, exc)

    def _apply_text_animation(self, text_strip) -> None:
        """
        Применить анимацию к текстовому strip в соответствии со стилем.

        Args:
            text_strip: Текстовый strip для анимации.
        """
        animation = self.TEXT_ANIMATION.lower()

        if animation == "fade" or animation == "fade_slide":
            self.editor.animate_text_fade_in(text_strip, fade_frames=15)

        elif animation == "slide_up":
            self.editor.animate_text_slide_up(
                text_strip, slide_distance=0.1, fade_frames=15
            )

        elif animation == "bounce":
            self.editor.animate_text_bounce(text_strip, bounce_frames=20)

        elif animation == "zoom_in":
            self.editor.animate_text_zoom_in(text_strip, zoom_frames=15)

        elif animation == "typewriter":
            self.editor.animate_text_typewriter(text_strip, char_per_frame=2)

        else:
            logger.warning("Неизвестная анимация: %s, используется fade.", animation)
            self.editor.animate_text_fade_in(text_strip, fade_frames=15)

    def _apply_color_grading(self, total_duration: int) -> None:
        """
        Применить цветокоррекцию ко всему проекту.

        Args:
            total_duration: Общая длительность проекта в кадрах.
        """
        try:
            self.editor.add_color_grade(
                channel=self.CHANNEL_COLORGRADE,
                frame_start=1,
                frame_end=total_duration,
                contrast=self.CONTRAST,
                brightness=self.BRIGHTNESS,
                saturation=self.SATURATION,
                color_multiply=self.COLOR_MULTIPLY,
            )
            logger.info(
                "Color grade: contrast=%.2f, brightness=%.2f, saturation=%.2f",
                self.CONTRAST,
                self.BRIGHTNESS,
                self.SATURATION,
            )
        except Exception as exc:
            logger.warning("Color grade не применён: %s", exc)

    def _apply_effects(self, total_duration: int) -> None:
        """
        Применить эффекты (film grain, vignette).

        Args:
            total_duration: Общая длительность проекта в кадрах.
        """
        # --- Film Grain ---
        if self.FILM_GRAIN:
            try:
                self.editor.add_film_grain(
                    channel=self.CHANNEL_EFFECTS,
                    frame_start=1,
                    frame_end=total_duration,
                    intensity=0.08,
                )
                logger.info("Film grain применён.")
            except Exception as exc:
                logger.warning("Film grain не применён: %s", exc)

        # --- Vignette ---
        if self.VIGNETTE:
            try:
                self.editor.add_vignette(
                    channel=self.CHANNEL_EFFECTS + 1,
                    frame_start=1,
                    frame_end=total_duration,
                    intensity=0.25,
                )
                logger.info("Vignette применён.")
            except Exception as exc:
                logger.warning("Vignette не применён: %s", exc)

    # ------------------------------------------------------------------
    # Dunder
    # ------------------------------------------------------------------
    def __repr__(self) -> str:
        return (
            f"VSEStyleBase("
            f"style='{self.style_name}', "
            f"transition={self.TRANSITION_TYPE}, "
            f"animation={self.TEXT_ANIMATION}, "
            f"cut_duration={self.CUT_DURATION})"
        )
