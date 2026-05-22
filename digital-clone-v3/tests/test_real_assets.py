#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестовый рендер шортса из реальных видео (Mixkit)

1. Ищет видео через AssetFinder (Mixkit scraping, без API ключей)
2. Монтирует в Blender VSE в стиле Gadzhi
3. Рендерит MP4

Запуск:
    cd digital-clone-v3
    python test_real_assets.py
"""

import asyncio
import os
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.resolve()
OUTPUT_DIR = PROJECT_ROOT / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# --- Шаг 1: Поиск видео через AssetFinder ---------------------------

async def find_clips():
    from core.asset_finder import AssetFinder

    print("=== Поиск видео через Mixkit (без API ключей) ===")
    finder = AssetFinder(output_dir=str(PROJECT_ROOT / "assets"))

    # Ищем 4 клипа по теме бизнес/мотивация
    clips = await finder.find_videos_for_topic(
        topic="business laptop motivation",
        style="gadzhi",
        count=4,
    )

    if not clips:
        print("\n[ERROR] Не найдены видео. Mixkit может быть недоступен.")
        print("Попробуй установить PEXELS_API_KEY для fallback.")
        sys.exit(1)

    print(f"\nНайдено {len(clips)} клипов:")
    for c in clips:
        print(f"  [OK] {Path(c).name}")
    return clips


# --- Шаг 2: Генерация Blender-скрипта ------------------------------

def build_blender_script(clips: list, output_path: str) -> str:
    """Генерирует Python-скрипт для запуска внутри Blender."""
    # Абсолютные пути, иначе Blender ищет от корня диска
    abs_clips = [str(Path(c).resolve()) for c in clips]
    clips_json = repr(abs_clips)
    output_json = repr(output_path)

    return f'''
import sys
import os

# Путь к проекту внутри Blender
project_root = {repr(str(PROJECT_ROOT))}
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.blender_vse.styles import get_style

clips = {clips_json}
output_path = {output_json}

# Проверяем что файлы существуют
valid_clips = [c for c in clips if os.path.isfile(c)]
if len(valid_clips) < 3:
    print(f"[ERROR] Нужно минимум 3 видео, найдено: {{len(valid_clips)}}")
    sys.exit(1)

print(f"\\n=== Монта Gadzhi-шортса из {{len(valid_clips)}} клипов ===")
for c in valid_clips:
    print(f"  - {{os.path.basename(c)}}")

# Тексты в стиле Gadzhi
texts = [
    {{
        "text": "В 23 ГОДА",
        "start_frame": 1,
        "duration": 75,
        "font_size": 110,
        "position": (0.5, 0.45),
    }},
    {{
        "text": "Я ЗАРАБАТЫВАЮ",
        "start_frame": 76,
        "duration": 75,
        "font_size": 100,
        "position": (0.5, 0.5),
    }},
    {{
        "text": "$100K/МЕСЯЦ",
        "start_frame": 151,
        "duration": 75,
        "font_size": 120,
        "position": (0.5, 0.55),
    }},
    {{
        "text": "ССЫЛКА В ШАПКЕ",
        "start_frame": 226,
        "duration": 75,
        "font_size": 90,
        "position": (0.5, 0.85),
    }},
]

try:
    style = get_style("gadzhi")
    video = style.create_short(
        video_clips=valid_clips[:4],
        texts=texts,
        output_path=output_path,
        width=1080,
        height=1920,
        fps=30,
    )
    print(f"\\n=== ГОТОВО ===")
    print(f"Видео: {{video}}")
except Exception as exc:
    print(f"\\n=== ОШИБКА ===")
    print(f"{{type(exc).__name__}}: {{exc}}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
'''


# --- Шаг 3: Запуск Blender -----------------------------------------

def find_blender() -> str:
    """Найти Blender executable."""
    candidates = [
        r"C:\Tools\Blender\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender\blender.exe",
    ]
    for c in candidates:
        if Path(c).exists():
            return c
    # fallback на PATH
    import shutil
    exe = shutil.which("blender")
    if exe:
        return exe
    raise FileNotFoundError("Blender не найден. Установи Blender 4.x или укажи путь.")


def run_blender(script_path: str):
    blender = find_blender()
    cmd = [
        blender,
        "--background",
        "--python", script_path,
    ]
    print(f"\n=== Запуск Blender ===")
    print(f"  Blender: {blender}")
    print(f"  Script:  {script_path}")
    print(f"  Это займёт 30-60 секунд...\n")

    result = subprocess.run(cmd, capture_output=False, text=True)
    return result.returncode == 0


# --- Main ----------------------------------------------------------

async def main():
    # 1. Ищем клипы
    clips = await find_clips()

    # 2. Готовим путь для выходного файла
    output_path = str(OUTPUT_DIR / "gadzhi_real_assets.mp4")

    # 3. Генерируем временный Blender-скрипт
    script_content = build_blender_script(clips, output_path)
    with tempfile.NamedTemporaryFile(
        mode="w", suffix="_blender.py", delete=False, encoding="utf-8"
    ) as f:
        f.write(script_content)
        script_path = f.name

    try:
        # 4. Запускаем Blender
        success = run_blender(script_path)
        if success and Path(output_path).exists():
            size_mb = Path(output_path).stat().st_size / (1024 * 1024)
            print(f"\n{'='*50}")
            print(f"[DONE] ГОТОВО: {output_path}")
            print(f"       Размер: {size_mb:.1f} MB")
            print(f"{'='*50}")
        else:
            print("\n[ERROR] Рендер не удался. Смотри логи Blender выше.")
            sys.exit(1)
    finally:
        os.unlink(script_path)


if __name__ == "__main__":
    asyncio.run(main())
