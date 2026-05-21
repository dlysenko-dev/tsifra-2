#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестовый ролик в стиле Iman Gadzhi
Запуск: blender --background --python make_test_gadzhi.py
"""

import sys
import os

# Добавляем путь к проекту (где лежит core/)
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.blender_vse.styles import get_style

# === НАСТРОЙКИ ===
BROLL_DIR = os.path.join(project_root, "output", "broll")
OUTPUT_DIR = os.path.join(project_root, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Собираем клипы из папки broll
clips = sorted([
    os.path.join(BROLL_DIR, f)
    for f in os.listdir(BROLL_DIR)
    if f.endswith((".mp4", ".mov", ".avi"))
])

if len(clips) < 3:
    print(f"Нужно минимум 3 видео в {BROLL_DIR}, найдено: {len(clips)}")
    sys.exit(1)

print(f"Найдено клипов: {len(clips)}")
for c in clips:
    print(f"  - {os.path.basename(c)}")

# Тексты в стиле Gadzhi
texts = [
    {
        "text": "В 23 ГОДА",
        "start_frame": 1,
        "duration": 75,
        "font_size": 110,
        "position": (0.5, 0.45),
    },
    {
        "text": "Я ЗАРАБАТЫВАЮ",
        "start_frame": 76,
        "duration": 75,
        "font_size": 100,
        "position": (0.5, 0.5),
    },
    {
        "text": "$100K/МЕСЯЦ",
        "start_frame": 151,
        "duration": 75,
        "font_size": 120,
        "position": (0.5, 0.55),
    },
    {
        "text": "ССЫЛКА В ШАПКЕ",
        "start_frame": 226,
        "duration": 75,
        "font_size": 90,
        "position": (0.5, 0.85),
    },
]

output_path = os.path.join(OUTPUT_DIR, "gadzhi_test_short.mp4")

# Создаём в стиле Gadzhi
print("\n=== Создание Gadzhi-шортса ===")
style = get_style("gadzhi")
print(f"Стиль: {style}")

try:
    video = style.create_short(
        video_clips=clips[:4],
        texts=texts,
        output_path=output_path,
        width=1080,
        height=1920,
        fps=30,
    )
    print(f"\n=== ГОТОВО ===")
    print(f"Видео: {video}")
except Exception as exc:
    print(f"\n=== ОШИБКА ===")
    print(f"{type(exc).__name__}: {exc}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
