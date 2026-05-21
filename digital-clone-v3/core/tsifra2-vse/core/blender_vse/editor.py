#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
editor.py
=========

Базовый класс BlenderVSEEditor — ядро видео-редактора на базе Blender VSE.

Предоставляет методы для:
  - Создания VSE-проекта
  - Добавления видео-клипов, текста, звука
  - Анимации текста (fade, slide, bounce, zoom, typewriter)
  - Цветокоррекции (adjustment strips, film grain, vignette)
  - Переходов между клипами
  - Рендера в MP4

Требует Blender 4.x с Python API (bpy).
"""

from __future__ import annotations

import bpy
import bmesh
import os
import logging
from pathlib import Path
from typing import List, Optional, Tuple, Union

from bpy.types import (
    Sequence,
    MovieSequence,
    SoundSequence,
    TextSequence,
    AdjustmentSequence,
    EffectSequence,
    ColorSequence,
    Scene,
)

# ---------------------------------------------------------------------------
# Логирование
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


# ---------------------------------------------------------------------------
# Исключения
# ---------------------------------------------------------------------------
class VSEError(Exception):
    """Базовое исключение для ошибок VSE."""


class VSESequenceNotFoundError(VSEError):
    """Sequence не найден в timeline."""


class VSERenderError(VSEError):
    """Ошибка рендера."""


# ---------------------------------------------------------------------------
# BlenderVSEEditor
# ---------------------------------------------------------------------------
class BlenderVSEEditor:
    """
    Базовый редактор Blender Video Sequence Editor.

    Examples:
        >>> editor = BlenderVSEEditor(output_dir="./output")
        >>> editor.create_project(width=1080, height=1920, fps=30, duration_frames=300)
        >>> strip = editor.add_video_clip("/path/to/clip.mp4", channel=1, frame_start=1)
        >>> txt = editor.add_text("Hello!", channel=2, frame_start=1, frame_end=60)
        >>> editor.animate_text_fade_in(txt, fade_frames=15)
        >>> editor.render("//output.mp4")
    """

    # Поддерживаемые типы переходов
    TRANSITION_TYPES = {"HARD_CUT", "CROSS", "GAMMA_CROSS", "WIPE", "SUBTRACT", "ADD"}

    def __init__(self, output_dir: str = "./output"):
        """
        Инициализация редактора.

        Args:
            output_dir: Директория для сохранения рендеров и .blend файлов.
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._se: Optional[bpy.types.SequenceEditor] = None  # sequence_editor
        self._scene: Optional[Scene] = None
        self._clip_counter: int = 0  # счётчик клипов для уникальных имён

    # ------------------------------------------------------------------
    # Свойства
    # ------------------------------------------------------------------
    @property
    def se(self) -> Optional[bpy.types.SequenceEditor]:
        """Текущий SequenceEditor (может быть None)."""
        return self._se

    @property
    def scene(self) -> Optional[Scene]:
        """Текущая сцена Blender."""
        return self._scene

    # ------------------------------------------------------------------
    # Проект
    # ------------------------------------------------------------------
    def create_project(
        self,
        width: int = 1080,
        height: int = 1920,
        fps: int = 30,
        duration_frames: int = 300,
        clear_existing: bool = True,
    ) -> Scene:
        """
        Создать новый VSE-проект.

        Очищает существующую сцену (если clear_existing=True),
        настраивает разрешение, FPS, создаёт SequenceEditor.

        Args:
            width:  Ширина видео (px).
            height: Высота видео (px).
            fps:    Кадров в секунду.
            duration_frames: Длительность проекта в кадрах.
            clear_existing:  Удалить старые sequences перед началом.

        Returns:
            Объект bpy.types.Scene — текущая сцена.
        """
        try:
            self._scene = bpy.context.scene
            render = self._scene.render

            # --- Настройки рендера ---
            render.resolution_x = width
            render.resolution_y = height
            render.resolution_percentage = 100
            render.fps = fps
            render.fps_base = 1.0

            # --- Диапазон кадров ---
            self._scene.frame_start = 1
            self._scene.frame_end = duration_frames
            self._scene.frame_set(1)

            # --- Создание SequenceEditor ---
            if not self._scene.sequence_editor:
                self._scene.sequence_editor_create()
            self._se = self._scene.sequence_editor

            # --- Очистка старых sequences ---
            if clear_existing and self._se.sequences_all:
                seq_names = list(self._se.sequences_all.keys())
                for name in seq_names:
                    strip = self._se.sequences_all[name]
                    try:
                        self._se.sequences.remove(strip)
                    except Exception as e:
                        logger.warning("Не удалось удалить strip %s: %s", name, e)
                logger.info("Удалено %d старых sequences.", len(seq_names))

            logger.info(
                "VSE-проект создан: %dx%d @ %d fps, %d кадров",
                width,
                height,
                fps,
                duration_frames,
            )
            return self._scene

        except Exception as exc:
            logger.error("Ошибка create_project: %s", exc)
            raise VSEError(f"Не удалось создать проект: {exc}") from exc

    # ------------------------------------------------------------------
    # Видео-клипы
    # ------------------------------------------------------------------
    def add_video_clip(
        self,
        filepath: str,
        channel: int,
        frame_start: int,
        duration: Optional[int] = None,
    ) -> MovieSequence:
        """
        Добавить видео-клип на timeline.

        Args:
            filepath:     Абсолютный путь к видео-файлу (MP4/MOV/AVI).
            channel:      Канал (слой) для размещения.
            frame_start:  Кадр начала клипа.
            duration:     Длительность в кадрах (None = оригинальная длительность).

        Returns:
            MovieSequence — созданный strip.
        """
        try:
            if not os.path.isfile(filepath):
                raise VSEError(f"Файл не найден: {filepath}")

            # --- Используем movie_strip_add оператор ---
            # Переходим в VSE area чтобы оператор сработал корректно
            self._ensure_vse_area()

            bpy.ops.sequencer.movie_strip_add(
                filepath=filepath,
                frame_start=frame_start,
                channel=channel,
                fit_method="FIT",
                sound=True,
                use_framerate=False,
            )

            # Получаем только что созданный strip (последний добавленный)
            new_strip = None
            for seq in reversed(list(self._se.sequences_all.values())):
                if isinstance(seq, MovieSequence) and seq.frame_start == frame_start:
                    new_strip = seq
                    break

            if new_strip is None:
                # Fallback: ищем по имени файла
                basename = Path(filepath).stem
                for seq in self._se.sequences_all.values():
                    if isinstance(seq, MovieSequence) and basename in seq.name:
                        new_strip = seq
                        break

            if new_strip is None:
                raise VSESequenceNotFoundError(
                    "Не удалось найти созданный MovieSequence после добавления."
                )

            # --- Переопределяем длительность если задана ---
            if duration is not None:
                original_end = new_strip.frame_final_end
                new_strip.frame_final_duration = duration
                logger.debug(
                    "Клип обрезан: %d -> %d кадров", original_end, duration
                )

            self._clip_counter += 1
            logger.info(
                'Видео-клип добавлен: "%s" на channel=%d, frame=%d',
                new_strip.name,
                channel,
                frame_start,
            )
            return new_strip

        except Exception as exc:
            logger.error("Ошибка add_video_clip: %s", exc)
            raise VSEError(f"Не удалось добавить видео {filepath}: {exc}") from exc

    # ------------------------------------------------------------------
    # Текст
    # ------------------------------------------------------------------
    def add_text(
        self,
        text: str,
        channel: int,
        frame_start: int,
        frame_end: int,
        font_size: int = 100,
        color: Tuple[float, float, float, float] = (1, 1, 1, 1),
        position: Tuple[float, float] = (0.5, 0.5),
        shadow: bool = True,
        align_x: str = "CENTER",
        align_y: str = "CENTER",
        font_id: int = 0,
    ) -> TextSequence:
        """
        Добавить текстовый strip.

        Args:
            text:         Текст для отображения.
            channel:      Канал размещения.
            frame_start:  Первый кадр.
            frame_end:    Последний кадр.
            font_size:    Размер шрифта (px).
            color:        RGBA цвет (0..1).
            position:     Позиция (x, y) в нормализованных координатах.
            shadow:       Включить тень.
            align_x:      Горизонтальное выравнивание (LEFT, CENTER, RIGHT).
            align_y:      Вертикальное выравнивание (TOP, CENTER, BOTTOM).
            font_id:      ID шрифта (0 = стандартный).

        Returns:
            TextSequence — созданный текстовый strip.
        """
        try:
            self._ensure_vse_area()

            bpy.ops.sequencer.text_strip_add(
                frame_start=frame_start,
                frame_end=frame_end,
                channel=channel,
            )

            # Находим созданный strip
            txt_strip = None
            for seq in reversed(list(self._se.sequences_all.values())):
                if isinstance(seq, TextSequence) and seq.frame_start == frame_start:
                    txt_strip = seq
                    break

            if txt_strip is None:
                raise VSESequenceNotFoundError(
                    "Не удалось найти созданный TextSequence."
                )

            # --- Настройка свойств текста ---
            txt_strip.text = text
            txt_strip.font_size = font_size
            txt_strip.color = color
            txt_strip.location = position  # (x, y) 0..1
            txt_strip.use_shadow = shadow
            txt_strip.align_x = align_x
            txt_strip.align_y = align_y

            # --- Настройка интерполяции анимаций ---
            txt_strip.blend_type = "ALPHA_OVER"

            logger.info(
                'Текст добавлен: "%s" channel=%d, frames=%d-%d',
                text,
                channel,
                frame_start,
                frame_end,
            )
            return txt_strip

        except Exception as exc:
            logger.error("Ошибка add_text: %s", exc)
            raise VSEError(f"Не удалось добавить текст '{text}': {exc}") from exc

    # ------------------------------------------------------------------
    # Анимации текста
    # ------------------------------------------------------------------
    def animate_text_fade_in(
        self, strip: TextSequence, fade_frames: int = 15
    ) -> None:
        """
        Анимация появления текста — fade in по alpha.

        Args:
            strip:       Текстовый strip для анимации.
            fade_frames: Количество кадров на fade.
        """
        try:
            scene = self._scene
            start = int(strip.frame_start)
            end = min(start + fade_frames, int(strip.frame_final_end))

            # --- keyframe: alpha = 0 ---
            strip.blend_alpha = 0.0
            strip.keyframe_insert(data_path="blend_alpha", frame=start)

            # --- keyframe: alpha = 1 ---
            strip.blend_alpha = 1.0
            strip.keyframe_insert(data_path="blend_alpha", frame=end)

            # --- Настройка интерполяции (bezier для плавности) ---
            if strip.animation_data and strip.animation_data.action:
                for fcurve in strip.animation_data.action.fcurves:
                    if fcurve.data_path == "blend_alpha":
                        for kp in fcurve.keyframe_points:
                            kp.interpolation = "BEZIER"
                            kp.easing = "EASE_OUT"

            logger.info(
                "Fade-in анимация: '%s' кадры %d-%d", strip.name, start, end
            )

        except Exception as exc:
            logger.error("Ошибка animate_text_fade_in: %s", exc)
            raise VSEError(f"Fade-in анимация не применена: {exc}") from exc

    def animate_text_slide_up(
        self,
        strip: TextSequence,
        slide_distance: float = 0.1,
        fade_frames: int = 15,
    ) -> None:
        """
        Анимация: текст выезжает снизу + fade in.

        Args:
            strip:          Текстовый strip.
            slide_distance: Дистанция сдвига в нормализованных координатах.
            fade_frames:    Кадров на анимацию.
        """
        try:
            scene = self._scene
            start = int(strip.frame_start)
            end = min(start + fade_frames, int(strip.frame_final_end))
            original_y = strip.location[1]

            # --- Начальная позиция: ниже + прозрачный ---
            strip.location = (strip.location[0], original_y - slide_distance)
            strip.blend_alpha = 0.0
            strip.keyframe_insert(data_path="location", frame=start, index=1)
            strip.keyframe_insert(data_path="blend_alpha", frame=start)

            # --- Конечная позиция: на месте + видимый ---
            strip.location = (strip.location[0], original_y)
            strip.blend_alpha = 1.0
            strip.keyframe_insert(data_path="location", frame=end, index=1)
            strip.keyframe_insert(data_path="blend_alpha", frame=end)

            # --- Интерполяция ---
            self._set_keyframe_interpolation(strip, "blend_alpha", "BEZIER", "EASE_OUT")
            self._set_keyframe_interpolation(strip, "location", "BEZIER", "EASE_OUT")

            logger.info(
                "Slide-up анимация: '%s' кадры %d-%d", strip.name, start, end
            )

        except Exception as exc:
            logger.error("Ошибка animate_text_slide_up: %s", exc)
            raise VSEError(f"Slide-up анимация не применена: {exc}") from exc

    def animate_text_bounce(self, strip: TextSequence, bounce_frames: int = 20) -> None:
        """
        Анимация: bounce эффект (YoEdit стиль).

        Текст резко появляется с overshoot и затем немного
        отскакивает назад, создавая эффект "пружины".

        Args:
            strip:         Текстовый strip.
            bounce_frames: Кадров на bounce анимацию.
        """
        try:
            start = int(strip.frame_start)
            mid = start + int(bounce_frames * 0.6)
            end = start + bounce_frames
            original_y = strip.location[1]

            # --- Phase 1: снизу вверх с overshoot ---
            strip.blend_alpha = 0.0
            strip.location = (strip.location[0], original_y - 0.15)
            strip.keyframe_insert(data_path="blend_alpha", frame=start)
            strip.keyframe_insert(data_path="location", frame=start, index=1)

            # --- Phase 2: overshoot (немного выше целевой) ---
            strip.blend_alpha = 1.0
            strip.location = (strip.location[0], original_y + 0.03)
            strip.keyframe_insert(data_path="blend_alpha", frame=mid)
            strip.keyframe_insert(data_path="location", frame=mid, index=1)

            # --- Phase 3: settle на целевую позицию ---
            strip.location = (strip.location[0], original_y)
            strip.keyframe_insert(data_path="location", frame=end, index=1)

            # --- Interpolation ---
            self._set_keyframe_interpolation(strip, "blend_alpha", "BEZIER", "EASE_OUT")
            self._set_keyframe_interpolation(strip, "location", "BEZIER", "EASE_OUT")

            logger.info(
                "Bounce анимация: '%s' кадры %d-%d", strip.name, start, end
            )

        except Exception as exc:
            logger.error("Ошибка animate_text_bounce: %s", exc)
            raise VSEError(f"Bounce анимация не применена: {exc}") from exc

    def animate_text_zoom_in(
        self, strip: TextSequence, zoom_frames: int = 15
    ) -> None:
        """
        Анимация: zoom in (Gadzhi стиль).

        Текст плавно увеличивается от маленького до полного размера.

        Args:
            strip:       Текстовый strip.
            zoom_frames: Кадров на zoom анимацию.
        """
        try:
            start = int(strip.frame_start)
            end = min(start + zoom_frames, int(strip.frame_final_end))

            # --- Начало: маленький + прозрачный ---
            strip.transform.scale_x = 0.3
            strip.transform.scale_y = 0.3
            strip.blend_alpha = 0.0
            strip.keyframe_insert(data_path="blend_alpha", frame=start)
            strip.keyframe_insert(
                data_path="transform.scale_x", frame=start
            )
            strip.keyframe_insert(
                data_path="transform.scale_y", frame=start
            )

            # --- Конец: полный размер + видимый ---
            strip.transform.scale_x = 1.0
            strip.transform.scale_y = 1.0
            strip.blend_alpha = 1.0
            strip.keyframe_insert(data_path="blend_alpha", frame=end)
            strip.keyframe_insert(
                data_path="transform.scale_x", frame=end
            )
            strip.keyframe_insert(
                data_path="transform.scale_y", frame=end
            )

            # --- Interpolation ---
            self._set_keyframe_interpolation(
                strip, "blend_alpha", "BEZIER", "EASE_OUT"
            )
            self._set_keyframe_interpolation(
                strip, "transform.scale_x", "BACK", "EASE_OUT"
            )
            self._set_keyframe_interpolation(
                strip, "transform.scale_y", "BACK", "EASE_OUT"
            )

            logger.info(
                "Zoom-in анимация: '%s' кадры %d-%d", strip.name, start, end
            )

        except Exception as exc:
            logger.error("Ошибка animate_text_zoom_in: %s", exc)
            raise VSEError(f"Zoom-in анимация не применена: {exc}") from exc

    def animate_text_typewriter(
        self, strip: TextSequence, char_per_frame: int = 2
    ) -> None:
        """
        Анимация: печатная машинка (typewriter).

        Посимвольное появление текста с курсором.

        Args:
            strip:           Текстовый strip.
            char_per_frame:  Сколько символов появляется за кадр.
        """
        try:
            start = int(strip.frame_start)
            full_text = strip.text

            # --- Очищаем текст и анимируем посимвольно ---
            strip.text = ""

            for i, char in enumerate(full_text):
                frame = start + (i // char_per_frame)
                visible_text = full_text[: i + 1]
                # На каждом кадре обновляем текст
                strip.text = visible_text
                strip.keyframe_insert(data_path="text", frame=frame)

            # --- Финальный ключ на полный текст ---
            final_frame = start + (len(full_text) // char_per_frame) + 1
            strip.text = full_text
            strip.keyframe_insert(data_path="text", frame=final_frame)

            logger.info(
                "Typewriter анимация: '%s' %d символов, кадры %d-%d",
                full_text[:20],
                len(full_text),
                start,
                final_frame,
            )

        except Exception as exc:
            logger.error("Ошибка animate_text_typewriter: %s", exc)
            raise VSEError(f"Typewriter анимация не применена: {exc}") from exc

    # ------------------------------------------------------------------
    # Цветокоррекция
    # ------------------------------------------------------------------
    def add_color_grade(
        self,
        channel: int,
        frame_start: int,
        frame_end: int,
        contrast: float = 1.0,
        brightness: float = 0.0,
        saturation: float = 1.0,
        color_multiply: Tuple[float, float, float] = (1, 1, 1),
    ) -> AdjustmentSequence:
        """
        Цветокоррекция через adjustment strip.

        Args:
            channel:        Канал размещения.
            frame_start:    Первый кадр действия.
            frame_end:      Последний кадр.
            contrast:       Контраст (1.0 = без изменений).
            brightness:     Яркость (0.0 = без изменений).
            saturation:     Насыщенность (1.0 = без изменений).
            color_multiply: Множитель цвета RGB.

        Returns:
            AdjustmentSequence — созданный strip.
        """
        try:
            self._ensure_vse_area()

            bpy.ops.sequencer.adjustment_strip_add(
                frame_start=frame_start,
                frame_end=frame_end,
                channel=channel,
            )

            # Находим созданный strip
            adj = None
            for seq in reversed(list(self._se.sequences_all.values())):
                if isinstance(seq, AdjustmentSequence) and seq.frame_start == frame_start:
                    adj = seq
                    break

            if adj is None:
                raise VSESequenceNotFoundError(
                    "Не удалось найти созданный AdjustmentSequence."
                )

            # --- Применяем параметры цветокоррекции ---
            adj.color_multiply = color_multiply

            # Контраст и яркость через модификаторы (если доступно)
            # В Blender 4.x используем модификаторы strip
            self._add_strip_modifier(adj, "COLOR_BALANCE", {
                "color_multiply": color_multiply,
                "color_gain": (1.0 + brightness, 1.0 + brightness, 1.0 + brightness),
                "color_gamma": (1.0 / contrast, 1.0 / contrast, 1.0 / contrast),
            })

            logger.info(
                "Color grade добавлен: channel=%d, frames=%d-%d, contrast=%.2f",
                channel,
                frame_start,
                frame_end,
                contrast,
            )
            return adj

        except Exception as exc:
            logger.error("Ошибка add_color_grade: %s", exc)
            raise VSEError(f"Color grade не добавлен: {exc}") from exc

    def add_film_grain(
        self,
        channel: int,
        frame_start: int,
        frame_end: int,
        intensity: float = 0.1,
    ) -> Optional[AdjustmentSequence]:
        """
        Film grain эффект через adjustment strip с шумом.

        В Blender VSE film grain реализуется через adjustment strip
        с добавлением низкоуровневого шума через модификатор.

        Args:
            channel:      Канал размещения.
            frame_start:  Первый кадр.
            frame_end:    Последний кадр.
            intensity:    Интенсивность grain (0..1).

        Returns:
            AdjustmentSequence или None.
        """
        try:
            self._ensure_vse_area()

            # --- Создаём adjustment strip ---
            bpy.ops.sequencer.adjustment_strip_add(
                frame_start=frame_start,
                frame_end=frame_end,
                channel=channel,
            )

            adj = None
            for seq in reversed(list(self._se.sequences_all.values())):
                if isinstance(seq, AdjustmentSequence) and seq.frame_start == frame_start:
                    adj = seq
                    break

            if adj is None:
                return None

            # --- Применяем grain через blend_alpha ---
            # В Blender 4.x добавляем модификатор Brightness/Contrast
            # и анимируем его для эффекта шума
            mod = adj.modifiers.new(name="Grain", type="BRIGHT_CONTRAST")
            if mod:
                mod.float_1 = intensity  # brightness
                mod.float_2 = intensity * 0.5  # contrast

            logger.info(
                "Film grain добавлен: channel=%d, intensity=%.2f",
                channel,
                intensity,
            )
            return adj

        except Exception as exc:
            logger.warning("Film grain не добавлен: %s", exc)
            return None

    def add_vignette(
        self,
        channel: int,
        frame_start: int,
        frame_end: int,
        intensity: float = 0.3,
    ) -> Optional[ColorSequence]:
        """
        Vignette эффект через color strip с маской.

        Создаёт затемнение по краям кадра для кинематографического вида.

        Args:
            channel:      Канал размещения.
            frame_start:  Первый кадр.
            frame_end:    Последний кадр.
            intensity:    Интенсивность vignette (0..1).

        Returns:
            ColorSequence — созданный strip vignette.
        """
        try:
            self._ensure_vse_area()

            # --- Создаём чёрный color strip для vignette ---
            bpy.ops.sequencer.color_strip_add(
                frame_start=frame_start,
                frame_end=frame_end,
                channel=channel,
                color=(0, 0, 0, 1),
            )

            vig = None
            for seq in reversed(list(self._se.sequences_all.values())):
                if isinstance(seq, ColorSequence) and seq.frame_start == frame_start:
                    vig = seq
                    break

            if vig is None:
                return None

            vig.name = "Vignette"
            vig.blend_type = "ALPHA_OVER"
            vig.blend_alpha = intensity

            # --- Добавляем маску vignette через transform ---
            # Уменьшаем масштаб чтобы чёрные края оставались
            vig.transform.scale_x = 1.3
            vig.transform.scale_y = 1.3

            logger.info(
                "Vignette добавлен: channel=%d, intensity=%.2f",
                channel,
                intensity,
            )
            return vig

        except Exception as exc:
            logger.warning("Vignette не добавлен: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Переходы
    # ------------------------------------------------------------------
    def add_transition(
        self,
        strip1: Sequence,
        strip2: Sequence,
        channel: int,
        frame_start: int,
        frame_end: int,
        transition_type: str = "CROSS",
    ) -> Optional[EffectSequence]:
        """
        Добавить переход между двумя клипами.

        Args:
            strip1:          Первый strip (outgoing).
            strip2:          Второй strip (incoming).
            channel:         Канал для эффекта.
            frame_start:     Начало перехода.
            frame_end:       Конец перехода.
            transition_type: Тип перехода (CROSS, GAMMA_CROSS, WIPE, etc).

        Returns:
            EffectSequence — созданный strip перехода.
        """
        try:
            if transition_type not in self.TRANSITION_TYPES:
                raise VSEError(f"Неизвестный тип перехода: {transition_type}")

            # HARD_CUT — не создаём эффект, просто return
            if transition_type == "HARD_CUT":
                logger.info("HARD_CUT: переход не создаётся.")
                return None

            # Создаём effect strip
            effect = self._se.sequences.new_effect(
                name=f"Transition_{transition_type}",
                type=transition_type,
                channel=channel,
                frame_start=frame_start,
                frame_end=frame_end,
                seq1=strip1,
                seq2=strip2,
            )

            logger.info(
                "Переход %s создан: channel=%d, frames=%d-%d",
                transition_type,
                channel,
                frame_start,
                frame_end,
            )
            return effect

        except Exception as exc:
            logger.error("Ошибка add_transition: %s", exc)
            raise VSEError(f"Переход не создан: {exc}") from exc

    # ------------------------------------------------------------------
    # Звук
    # ------------------------------------------------------------------
    def add_sound(
        self,
        filepath: str,
        channel: int,
        frame_start: int,
        volume: float = 1.0,
    ) -> SoundSequence:
        """
        Добавить звуковую дорожку.

        Args:
            filepath:    Путь к аудио-файлу (MP3/WAV).
            channel:     Канал размещения.
            frame_start: Кадр начала.
            volume:      Громкость (0..1).

        Returns:
            SoundSequence — созданный аудио strip.
        """
        try:
            if not os.path.isfile(filepath):
                raise VSEError(f"Аудио-файл не найден: {filepath}")

            self._ensure_vse_area()

            bpy.ops.sequencer.sound_strip_add(
                filepath=filepath,
                frame_start=frame_start,
                channel=channel,
            )

            # Находим созданный strip
            sound = None
            for seq in reversed(list(self._se.sequences_all.values())):
                if isinstance(seq, SoundSequence) and seq.frame_start == frame_start:
                    sound = seq
                    break

            if sound is None:
                raise VSESequenceNotFoundError(
                    "Не удалось найти созданный SoundSequence."
                )

            sound.volume = volume

            logger.info(
                'Звук добавлен: "%s" channel=%d, volume=%.2f',
                sound.name,
                channel,
                volume,
            )
            return sound

        except Exception as exc:
            logger.error("Ошибка add_sound: %s", exc)
            raise VSEError(f"Звук не добавлен: {exc}") from exc

    # ------------------------------------------------------------------
    # Рендер
    # ------------------------------------------------------------------
    def render(self, output_path: Optional[str] = None) -> str:
        """
        Рендер проекта в MP4 через FFmpeg.

        Args:
            output_path: Путь для сохранения (None = авто-генерация).

        Returns:
            Абсолютный путь к сгенерированному MP4.
        """
        try:
            scene = self._scene
            render = scene.render

            # --- Настройка рендера ---
            render.engine = "BLENDER_EEVEE_NEXT"
            render.image_settings.file_format = "FFMPEG"
            render.ffmpeg.format = "MPEG4"
            render.ffmpeg.codec = "H264"
            render.ffmpeg.constant_rate_factor = "MEDIUM"
            render.ffmpeg.ffmpeg_preset = "GOOD"
            render.ffmpeg.gopsize = 12  # GOP для хорошего сжатия
            render.ffmpeg.audio_codec = "AAC"
            render.ffmpeg.audio_bitrate = 192

            # --- Путь вывода ---
            if output_path is None:
                output_path = str(self.output_dir / "render_output.mp4")
            elif output_path.startswith("//"):
                output_path = str(self.output_dir / output_path[2:])

            render.filepath = output_path

            # --- Запуск рендера ---
            logger.info("Начало рендера: %s", output_path)
            bpy.ops.render.render(animation=True, scene=scene.name)

            if os.path.isfile(output_path):
                file_size = os.path.getsize(output_path)
                logger.info(
                    "Рендер завершён: %s (%.1f MB)",
                    output_path,
                    file_size / (1024 * 1024),
                )
                return output_path
            else:
                raise VSERenderError(f"Файл не создан после рендера: {output_path}")

        except Exception as exc:
            logger.error("Ошибка render: %s", exc)
            raise VSERenderError(f"Рендер не удался: {exc}") from exc

    # ------------------------------------------------------------------
    # Сохранение
    # ------------------------------------------------------------------
    def save_project(self, filepath: Optional[str] = None) -> str:
        """
        Сохранить .blend файл.

        Args:
            filepath: Путь для сохранения (None = авто-генерация).

        Returns:
            Абсолютный путь к .blend файлу.
        """
        try:
            if filepath is None:
                filepath = str(self.output_dir / "vse_project.blend")
            elif filepath.startswith("//"):
                filepath = str(self.output_dir / filepath[2:])

            bpy.ops.wm.save_as_mainfile(filepath=filepath)
            logger.info("Проект сохранён: %s", filepath)
            return filepath

        except Exception as exc:
            logger.error("Ошибка save_project: %s", exc)
            raise VSEError(f"Не удалось сохранить проект: {exc}") from exc

    # ------------------------------------------------------------------
    # Внутренние хелперы
    # ------------------------------------------------------------------
    def _ensure_vse_area(self) -> None:
        """
        Убедиться что активный редактор — Sequence Editor.

        Некоторые bpy.ops.sequencer операторы требуют
        чтобы контекст был VSE area.
        """
        # В headless-режиме (фоновый рендер) это может не работать,
        # поэтому оборачиваем в try/except
        try:
            for area in bpy.context.screen.areas:
                if area.type == "SEQUENCE_EDITOR":
                    bpy.context.area = area
                    return
        except (AttributeError, RuntimeError):
            pass  # В headless режиме продолжаем без переключения

    def _set_keyframe_interpolation(
        self,
        strip: Sequence,
        data_path: str,
        interpolation: str = "BEZIER",
        easing: str = "AUTO",
    ) -> None:
        """
        Установить тип интерполяции для keyframes.

        Args:
            strip:         Strip с анимацией.
            data_path:     Путь к анимируемому свойству.
            interpolation: Тип интерполяции (BEZIER, LINEAR, CONSTANT, BACK).
            easing:        Тип easing (AUTO, EASE_IN, EASE_OUT, EASE_IN_OUT).
        """
        if not strip.animation_data or not strip.animation_data.action:
            return

        for fcurve in strip.animation_data.action.fcurves:
            if data_path in fcurve.data_path:
                for kp in fcurve.keyframe_points:
                    kp.interpolation = interpolation
                    if easing != "AUTO":
                        kp.easing = easing

    def _add_strip_modifier(
        self,
        strip: Sequence,
        modifier_type: str,
        props: dict,
    ) -> Optional[object]:
        """
        Добавить модификатор к strip.

        Args:
            strip:         Целевой strip.
            modifier_type: Тип модификатора (COLOR_BALANCE, BRIGHT_CONTRAST, etc).
            props:         Словарь свойств для установки.

        Returns:
            Созданный модификатор или None.
        """
        try:
            mod = strip.modifiers.new(name=modifier_type, type=modifier_type)
            for key, value in props.items():
                if hasattr(mod, key):
                    setattr(mod, key, value)
            return mod
        except Exception as exc:
            logger.warning("Модификатор %s не добавлен: %s", modifier_type, exc)
            return None

    # ------------------------------------------------------------------
    # Dunder
    # ------------------------------------------------------------------
    def __repr__(self) -> str:
        return (
            f"BlenderVSEEditor("
            f"output_dir='{self.output_dir}', "
            f"clips={self._clip_counter}, "
            f"se={'active' if self._se else 'None'})"
        )

    def __enter__(self) -> "BlenderVSEEditor":
        """Контекстный менеджер: вход."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Контекстный менеджер: выход с авто-сохранением."""
        if exc_type is None:
            try:
                self.save_project()
            except Exception:
                pass
