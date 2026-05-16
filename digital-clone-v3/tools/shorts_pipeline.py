#!/usr/bin/env python3
"""
shorts_pipeline.py — Shorts Video Generation Pipeline
======================================================
Генерирует короткие видео (shorts) на заданную тему через:
1. LLM — генерация сценария и описаний кадров
2. Image Generation API — создание изображений для каждого кадра
3. FFmpeg — сборка изображений в видео со звуковой дорожкой

Использование:
    python shorts_pipeline.py --topic "Тема шортса"
    python shorts_pipeline.py --topic "Тема шортса" --dry-run

Выход:
    output/shorts/<topic_hash>/video.mp4

Требуемые переменные окружения:
    KIMI_API_KEY или DEEPSEEK_API_KEY — для генерации сценария
    OUTPUT_DIR — базовая директория для выходных файлов (default: ./output)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import subprocess
import time
from pathlib import Path


# ---------------------------------------------------------------------------
# Конфигурация
# ---------------------------------------------------------------------------

DEFAULT_OUTPUT_DIR = "./output"
DEFAULT_DURATION = 15  # секунд
DEFAULT_RESOLUTION = "1080x1920"  # вертикальное 9:16
DEFAULT_FPS = 30


def get_config():
    """Прочитать конфигурацию из окружения."""
    output_dir = os.environ.get("OUTPUT_DIR", DEFAULT_OUTPUT_DIR)
    api_key = os.environ.get("KIMI_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")
    return {
        "output_dir": output_dir,
        "api_key": api_key,
    }


def topic_hash(topic: str) -> str:
    """Создать короткий хеш из темы."""
    return hashlib.md5(topic.encode("utf-8")).hexdigest()[:12]


# ---------------------------------------------------------------------------
# Шаг 1: Генерация сценария через LLM
# ---------------------------------------------------------------------------

def generate_script(topic: str, api_key: str | None, dry_run: bool = False) -> list[dict]:
    """Сгенерировать сценарий шортса — список сцен.

    Каждая сцена: {"text": "описание", "duration": секунды, "image_prompt": "описание кадра"}

    Returns:
        Список словарей с описанием сцен.
    """
    if dry_run:
        print("[DRY-RUN] Would generate script for topic:", topic)
        return [
            {"text": f"Вступление: {topic}", "duration": 3, "image_prompt": f"Eye-catching intro frame about {topic}"},
            {"text": f"Главная мысль: почему {topic} важно", "duration": 5, "image_prompt": f"Dynamic visual about importance of {topic}"},
            {"text": f"Финальный призыв к действию", "duration": 4, "image_prompt": f"Call-to-action screen for {topic}"},
        ]

    # Если нет API ключа — fallback шаблон
    if not api_key:
        print("[WARN] No API key found. Using template script.")
        return [
            {"text": f"Всё что нужно знать о {topic}", "duration": 3, "image_prompt": f"Bold title card: {topic}"},
            {"text": f"{topic} — это тренд, который меняет правила игры", "duration": 5, "image_prompt": f"Futuristic visualization of {topic}"},
            {"text": "Подписывайся на канал!", "duration": 4, "image_prompt": f"Subscribe call to action with {topic} branding"},
        ]

    # Пробуем вызвать LLM через HTTP API
    print("[SCRIPT] Generating script via LLM...")
    scenes = _call_llm_for_script(topic, api_key)
    if scenes:
        return scenes

    # Fallback
    return [
        {"text": f"Топ фактов о {topic}", "duration": 3, "image_prompt": f"Title card: {topic}"},
        {"text": f"Факт 1: {topic} растёт на 200% в год", "duration": 4, "image_prompt": f"Growth chart visualization for {topic}"},
        {"text": f"Факт 2: лидеры уже используют {topic}", "duration": 4, "image_prompt": f"Business leaders using {topic} technology"},
        {"text": "Подписывайся!", "duration": 4, "image_prompt": "Subscribe CTA end screen"},
    ]


def _call_llm_for_script(topic: str, api_key: str) -> list[dict] | None:
    """Вызвать LLM API для генерации сценария."""
    import urllib.request
    import urllib.error

    prompt = (
        f"Создай сценарий для короткого видео (15 секунд, вертикальное 9:16) "
        f"на тему: '{topic}'.\n\n"
        f"Формат ответа — строго JSON-массив:\n"
        f'[{{"text": "текст сцены", "duration": 3, "image_prompt": "описание кадра для генерации"}}]\n\n'
        f"Требования:\n"
        f"- 3-4 сцены, суммарно ~15 секунд\n"
        f"- Каждая сцена: текст для overlay, длительность в сек, описание кадра\n"
        f"- image_prompt на английском, детальное описание визуала\n"
        f"- Последняя сцена — призыв подписаться\n"
        f"- Только JSON, без markdown, без объяснений"
    )

    # Пробуем DeepSeek
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    payload = json.dumps({
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 800,
        "temperature": 0.7,
    }).encode("utf-8")

    urls_to_try = [
        "https://api.deepseek.com/v1/chat/completions",
        "https://api.moonshot.cn/v1/chat/completions",
    ]

    for url in urls_to_try:
        try:
            req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
            req.add_header("User-Agent", "shorts_pipeline/1.0")
            with urllib.request.urlopen(req, timeout=60) as resp:
                body = resp.read().decode("utf-8")
                data = json.loads(body)
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                # Парсим JSON из контента
                content = content.strip()
                if content.startswith("```"):
                    lines = content.splitlines()
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines and lines[-1].startswith("```"):
                        lines = lines[:-1]
                    content = "\n".join(lines).strip()
                scenes = json.loads(content)
                if isinstance(scenes, list) and len(scenes) > 0:
                    print(f"[SCRIPT] Generated {len(scenes)} scenes via LLM")
                    return scenes
        except Exception as exc:
            print(f"[WARN] LLM call failed for {url}: {exc}")
            continue

    return None


# ---------------------------------------------------------------------------
# Шаг 2: Генерация изображений
# ---------------------------------------------------------------------------

def generate_images(scenes: list[dict], output_dir: Path, dry_run: bool = False) -> list[Path]:
    """Сгенерировать изображения для каждой сцены.

    Returns:
        Список путей к сгенерированным изображениям.
    """
    images_dir = output_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    image_paths: list[Path] = []

    for i, scene in enumerate(scenes):
        prompt = scene.get("image_prompt", f"Scene {i+1}")
        img_path = images_dir / f"scene_{i:02d}.jpg"

        if dry_run:
            print(f"[DRY-RUN] Would generate image {i+1}/{len(scenes)}: {prompt[:60]}...")
            # Создаём placeholder файл
            img_path.write_text(f"# Placeholder for: {prompt}\n")
            image_paths.append(img_path)
            continue

        print(f"[IMAGE {i+1}/{len(scenes)}] Generating: {prompt[:60]}...")

        # Пробуем сгенерировать через доступные API
        success = _generate_image_api(prompt, str(img_path))

        if not success:
            # Fallback: создаём placeholder
            print(f"[WARN] Image generation failed for scene {i+1}, using placeholder")
            _create_placeholder_image(str(img_path), prompt, i + 1)

        if img_path.exists():
            image_paths.append(img_path)

    return image_paths


def _generate_image_api(prompt: str, output_path: str) -> bool:
    """Попытаться сгенерировать изображение через API.

    Returns:
        True если успешно, False если не удалось.
    """
    # Проверяем наличие generate_image из toolset
    try:
        import urllib.request
        import urllib.error

        # Пробуем pollinations.ai (бесплатный)
        encoded_prompt = urllib.parse.quote(prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1080&height=1920&seed={int(time.time())}&nologo=true"

        req = urllib.request.Request(url, headers={"User-Agent": "shorts_pipeline/1.0"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            with open(output_path, "wb") as f:
                f.write(resp.read())
        return True
    except Exception as exc:
        print(f"[WARN] Image API failed: {exc}")
        return False


def _create_placeholder_image(path: str, prompt: str, scene_num: int) -> None:
    """Создать placeholder изображение через PIL/Pillow."""
    try:
        from PIL import Image, ImageDraw, ImageFont

        img = Image.new("RGB", (1080, 1920), color=(30, 30, 50))
        draw = ImageDraw.Draw(img)

        # Рисуем рамку
        draw.rectangle([20, 20, 1060, 1900], outline=(100, 100, 200), width=4)

        # Текст
        text = f"Scene {scene_num}\n{prompt[:80]}"
        # Пробуем найти шрифт
        font = None
        for font_name in ["DejaVuSans-Bold.ttf", "Arial-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]:
            try:
                font = ImageFont.truetype(font_name, 40)
                break
            except:
                continue
        if font is None:
            font = ImageFont.load_default()

        # Центрируем текст
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (1080 - text_width) // 2
        y = (1920 - text_height) // 2
        draw.text((x, y), text, fill=(255, 255, 255), font=font)

        img.save(path, "JPEG", quality=85)
        print(f"[PLACEHOLDER] Created: {path}")
    except ImportError:
        # Если PIL нет — создаём пустой файл
        Path(path).write_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00")  # JPEG header
        print(f"[PLACEHOLDER] Minimal JPEG: {path}")
    except Exception as exc:
        print(f"[WARN] Placeholder creation failed: {exc}")
        Path(path).touch()  # Пустой файл как last resort


# ---------------------------------------------------------------------------
# Шаг 3: Сборка видео через FFmpeg
# ---------------------------------------------------------------------------

def assemble_video(
    image_paths: list[Path],
    scenes: list[dict],
    output_dir: Path,
    dry_run: bool = False,
) -> Path | None:
    """Собрать видео из изображений через FFmpeg.

    Returns:
        Путь к итоговому видео или None если не удалось.
    """
    video_path = output_dir / "video.mp4"

    if dry_run:
        print(f"[DRY-RUN] Would assemble video from {len(image_paths)} images → {video_path}")
        return video_path

    if not image_paths:
        print("[ERROR] No images to assemble")
        return None

    print(f"[VIDEO] Assembling {len(image_paths)} scenes into video...")

    # Проверяем наличие ffmpeg
    ffmpeg_cmd = None
    for cmd in ["ffmpeg", "avconv"]:
        try:
            subprocess.run([cmd, "-version"], capture_output=True, check=True, timeout=5)
            ffmpeg_cmd = cmd
            break
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue

    if not ffmpeg_cmd:
        print("[ERROR] ffmpeg not found. Install: apt install ffmpeg")
        return None

    # Создаём файл списка изображений с длительностью каждого
    concat_file = output_dir / "concat_list.txt"
    concat_lines = []
    for i, scene in enumerate(scenes):
        if i < len(image_paths):
            duration = scene.get("duration", 3)
            # Дублируем кадр на нужную длительность через fps
            concat_lines.append(f"file '{image_paths[i].absolute()}'")
            concat_lines.append(f"duration {duration}")

    # Последний кадр нужно дублировать без duration
    if image_paths:
        concat_lines.append(f"file '{image_paths[-1].absolute()}'")

    concat_file.write_text("\n".join(concat_lines) + "\n")

    # Запускаем ffmpeg
    cmd = [
        ffmpeg_cmd,
        "-y",  # перезаписывать файл
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-vf", f"fps={DEFAULT_FPS},scale={DEFAULT_RESOLUTION.replace('x', ':')}:force_original_aspect_ratio=decrease,pad={DEFAULT_RESOLUTION}:(ow-iw)/2:(oh-ih)/2",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "fast",
        "-crf", "23",
        "-movflags", "+faststart",
        str(video_path),
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0:
            file_size = video_path.stat().st_size
            print(f"[VIDEO] Created: {video_path} ({file_size / 1024 / 1024:.1f} MB)")
            return video_path
        else:
            print(f"[ERROR] ffmpeg failed (exit {result.returncode}):")
            print(result.stderr[-500:], file=sys.stderr)
            return None
    except subprocess.TimeoutExpired:
        print("[ERROR] ffmpeg timeout", file=sys.stderr)
        return None
    except Exception as exc:
        print(f"[ERROR] ffmpeg error: {exc}", file=sys.stderr)
        return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Shorts Video Generation Pipeline")
    parser.add_argument("--topic", required=True, help="Тема шортса")
    parser.add_argument("--dry-run", action="store_true", help="Тестовый прогон")
    args = parser.parse_args()

    topic = args.topic
    dry_run = args.dry_run

    print(f"{'='*60}")
    print(f"Shorts Pipeline — Topic: '{topic}'")
    print(f"Dry run: {dry_run}")
    print(f"{'='*60}")

    config = get_config()
    th = topic_hash(topic)
    output_dir = Path(config["output_dir"]) / "shorts" / th
    output_dir.mkdir(parents=True, exist_ok=True)

    # Шаг 1: Сценарий
    print("\n--- Step 1: Script Generation ---")
    scenes = generate_script(topic, config["api_key"], dry_run=dry_run)
    for i, scene in enumerate(scenes):
        print(f"  Scene {i+1}: {scene.get('text', '')[:50]}... ({scene.get('duration', '?')}s)")

    # Шаг 2: Изображения
    print("\n--- Step 2: Image Generation ---")
    image_paths = generate_images(scenes, output_dir, dry_run=dry_run)

    # Шаг 3: Видео
    print("\n--- Step 3: Video Assembly ---")
    video_path = assemble_video(image_paths, scenes, output_dir, dry_run=dry_run)

    # Результат
    print(f"\n{'='*60}")
    if video_path:
        print(f"RESULT: {video_path.absolute()}")
        print(f"message_id=shorts_pipeline_complete")
        print(f"topic_hash={th}")
        print(f"scenes={len(scenes)}")
        print(f"OK")
    else:
        print("RESULT: Video generation failed")
        print("ERROR: assembly_failed")
        sys.exit(1)
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
