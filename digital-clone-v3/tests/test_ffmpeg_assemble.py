#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест: склейка реальных Mixkit видео через ffmpeg

1. Ищет видео через AssetFinder (Mixkit scraping)
2. Обрезает / масштабирует до 1080x1920
3. Добавляет текстовые оверлеи (Gadzhi-style)
4. Добавляет эпичную музыку placeholder
5. Склеивает в финальный MP4

Запуск:
    python test_ffmpeg_assemble.py
"""

import asyncio
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.resolve()
OUTPUT_DIR = PROJECT_ROOT / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# === Шаг 1: Поиск видео =================================================

async def find_clips():
    from core.asset_finder import AssetFinder

    print("=== Поиск видео через Mixkit ===")
    finder = AssetFinder(output_dir=str(PROJECT_ROOT / "assets"))
    clips = await finder.find_videos_for_topic(
        topic="business laptop motivation",
        style="gadzhi",
        count=3,
    )
    if not clips:
        print("[ERROR] Не найдены видео")
        sys.exit(1)

    print(f"Найдено {len(clips)} клипов:")
    for c in clips:
        print(f"  [OK] {Path(c).name}")
    return [str(Path(c).resolve()) for c in clips]


# === Шаг 2: Подготовка сегментов =========================================

def prepare_segments(clips: list, duration_per_clip: float = 2.5) -> list:
    """Обрезает и масштабирует каждый клип до 1080x1920."""
    segments = []
    for i, clip in enumerate(clips):
        out = OUTPUT_DIR / f"segment_{i:02d}.mp4"

        # crop=center,scale=1080:1920 — центрируем и масштабируем
        # fill=black если соотношение не совпадает
        vf = (
            "scale=1080:1920:force_original_aspect_ratio=decrease,"
            "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black"
        )

        cmd = [
            "ffmpeg", "-y",
            "-i", clip,
            "-vf", vf,
            "-t", str(duration_per_clip),
            "-an",  # убираем оригинальный звук
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            str(out),
        ]
        print(f"\n  Сегмент {i}: {Path(clip).name} -> {out.name}")
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        segments.append(str(out))
    return segments


# === Шаг 3: Текстовые оверлеи ===========================================

def build_text_segments(segments: list) -> list:
    """Добавляет текст Gadzhi-style поверх каждого сегмента."""
    texts = [
        ("V 23 GODA", 90),
        ("YA ZARABATYVAYU", 80),
        ("$100K/MESYATS", 100),
    ]
    result = []
    for i, seg in enumerate(segments):
        out = OUTPUT_DIR / f"text_{i:02d}.mp4"
        text, size = texts[i % len(texts)]

        # drawtext: белый текст с черной обводкой
        vf = (
            f"drawtext=fontfile=/Windows/Fonts/arialbd.ttf:"
            f"text='{text}':"
            f"fontcolor=white:fontsize={size}:"
            f"x=(w-text_w)/2:y=(h-text_h)/2:"
            f"borderw=4:bordercolor=black"
        )

        cmd = [
            "ffmpeg", "-y",
            "-i", seg,
            "-vf", vf,
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            str(out),
        ]
        print(f"  Текст {i}: '{text}' -> {out.name}")
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        result.append(str(out))
    return result


# === Шаг 4: Склейка + переходы ==========================================

def assemble_final(segments: list, output_path: str, duration: float = 10.0):
    """Склеивает сегменты через filter_complex concat."""
    if len(segments) == 1:
        os.rename(segments[0], output_path)
        return

    inputs = []
    for seg in segments:
        inputs.extend(["-i", seg])

    # concat=n=3:v=1:a=0
    n = len(segments)
    filter_str = f"concat=n={n}:v=1:a=0"

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_str,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p",
        output_path,
    ]
    print(f"\n  Склейка ({n} сегментов) -> {Path(output_path).name}")
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


# === Шаг 5: Музыка ======================================================

def add_music(video_path: str, output_path: str):
    """Добавляет фоновую музыку (placeholder epic)."""
    music = PROJECT_ROOT / "assets" / "sounds" / "ambient" / "epic_placeholder.mp3"
    if not music.exists():
        print("  Музыка не найдена, пропускаем")
        os.rename(video_path, output_path)
        return

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", str(music),
        "-shortest",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "128k",
        output_path,
    ]
    print(f"  Добавление музыки -> {Path(output_path).name}")
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


# === Main ================================================================

async def main():
    # 1. Найти клипы
    clips = await find_clips()

    # 2. Подготовить сегменты
    print("\n=== Подготовка сегментов ===")
    segments = prepare_segments(clips, duration_per_clip=3.0)

    # 3. Текстовые оверлеи
    print("\n=== Текстовые оверлеи ===")
    text_segments = build_text_segments(segments)

    # 4. Склейка
    print("\n=== Склейка ===")
    raw_output = str(OUTPUT_DIR / "temp_assembled.mp4")
    assemble_final(text_segments, raw_output)

    # 5. Музыка
    print("\n=== Музыка ===")
    final_output = str(OUTPUT_DIR / "gadzhi_ffmpeg_test.mp4")
    add_music(raw_output, final_output)

    # Cleanup temp
    for f in segments + text_segments + [raw_output]:
        try:
            os.remove(f)
        except Exception:
            pass

    # Result
    size_mb = Path(final_output).stat().st_size / (1024 * 1024)
    print(f"\n{'='*50}")
    print(f"[DONE] ГОТОВО: {final_output}")
    print(f"       Размер: {size_mb:.1f} MB")
    print(f"{'='*50}")


if __name__ == "__main__":
    asyncio.run(main())
