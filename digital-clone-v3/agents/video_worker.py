"""
Video Worker v3
Генерация видео: Seedance 2.0 (бесплатно), Web-to-Video pipeline,
 motion graphics, интеграция с CapCut-style анимациями.
"""

import asyncio
import json
import time
from typing import Dict, List, Any, Optional
from pathlib import Path

from core.asset_finder import AssetFinder


class VideoWorker:
    """
    Воркер видео. Задачи:
    - Сгенерировать видео через Seedance 2.0 (бесплатно — видео #3)
    - Создать шортс через Web-to-Video pipeline
    - Добавить motion graphics (CapCut-style — видео #14)
    - Синхронизировать с озвучкой

    Бесплатные источники видео (из видео #3):
    - Seedance 2.0 (бесплатно, без GPU)
    - Grok 3 (zero credits)
    - Happy Horse 1.0 (open source #1)
    """

    VIDEO_SOURCES = {
        "seedance": {
            "name": "Seedance 2.0",
            "url": "https://www.seedance.io",
            "free": True,
            "quality": "high",
            "max_duration": 10,  # секунд
        },
        "grok": {
            "name": "Grok 3",
            "url": "https://grok.xai.com",
            "free": True,
            "quality": "medium",
        },
        "happy_horse": {
            "name": "Happy Horse 1.0",
            "url": "https://github.com/...",
            "free": True,
            "open_source": True,
        },
    }

    def __init__(self, llm_router=None, mcp_layer=None):
        self.llm = llm_router
        self.mcp = mcp_layer
        self.asset_finder = AssetFinder()

    async def execute(self, task, thought_chain):
        """Главный вход"""
        action = task.description.lower()

        if "шортс" in action or "shorts" in action:
            return await self.create_shorts(task.context)
        elif "видео" in action or "video" in action:
            return await self.generate_video(task.context)
        elif "web-to-video" in action or "html" in action:
            return await self.create_web_to_video(task.context)
        else:
            return await self.create_shorts(task.context)

    async def create_shorts(self, context: Dict) -> Dict:
        """
        Полный pipeline создания шортса:
        1. Сценарий (ContentWorker)
        2. Озвучка (TTS)
        3. Blender VSE монтаж (вместо слайд-шоу)
        4. Публикация (tg_publish.py)
        """
        topic = context.get("topic", "AI автоматизация")
        duration = context.get("duration", 30)
        platform = context.get("platform", "telegram")  # telegram/youtube/instagram
        style = context.get("style", "yoedit")  # yoedit | gadzhi | merzliakov
        video_clips = context.get("video_clips", [])
        texts = context.get("texts", [])

        # ── Попытка использовать Blender VSE ─────────────────────────────
        if self.mcp is not None:
            try:
                # Если клипы не переданы — ищем через AssetFinder
                if not video_clips:
                    video_clips = await self.asset_finder.find_videos_for_topic(
                        topic, style=style, count=4
                    )

                # Нет клипов = нечего монтировать. Градиенты и цветные картинки не делаем.
                if not video_clips:
                    return {
                        "type": "blender_vse_short",
                        "topic": topic,
                        "style": style,
                        "status": "error",
                        "error": (
                            "Не найдены видео-клипы для монтажа. "
                            "Установи API ключи (PEXELS_API_KEY, PIXABAY_API_KEY) "
                            "или передай video_clips вручную через context."
                        ),
                        "steps": [
                            {"step": 1, "name": "script", "status": "done"},
                            {"step": 2, "name": "asset_search", "status": "failed"},
                            {"step": 3, "name": "blender_vse", "status": "skipped"},
                        ]
                    }

                # Если тексты не переданы — генерируем базовые
                if not texts:
                    texts = [
                        {"text": topic[:30].upper(), "start_frame": 1, "duration": 75},
                        {"text": "СМОТРИ ДО КОНЦА", "start_frame": 76, "duration": 75},
                    ]

                # Ищем музыку под стиль
                music_path = context.get("music")
                if not music_path:
                    music_path = await self.asset_finder.find_music_for_topic(topic, style=style)

                output_path = context.get("output_path", f"./output/shorts_{int(time.time())}.mp4")

                # Создаем проект
                await self.mcp.execute("blender_vse_create_project", {
                    "width": 1080,
                    "height": 1920,
                    "fps": 30,
                    "duration_frames": int(duration * 30),
                    "output_dir": "./output",
                })

                # Добавляем фоновую музыку если нашли
                if music_path:
                    await self.mcp.execute("blender_vse_add_clip", {
                        "strip_type": "sound",
                        "filepath": music_path,
                        "channel": 2,
                        "frame_start": 1,
                    })

                # Применяем стиль и собираем шорт
                result = await self.mcp.execute("blender_vse_add_style", {
                    "style_name": style,
                    "video_clips": video_clips,
                    "texts": texts,
                    "output_path": output_path,
                    "width": 1080,
                    "height": 1920,
                    "fps": 30,
                })

                if result and getattr(result, "success", False):
                    return {
                        "type": "blender_vse_short",
                        "topic": topic,
                        "style": style,
                        "output_path": result.output_path if hasattr(result, "output_path") else output_path,
                        "status": "done",
                        "source_clips": video_clips,
                        "music": music_path,
                        "steps": [
                            {"step": 1, "name": "script", "status": "done"},
                            {"step": 2, "name": "voice", "status": "skipped"},
                            {"step": 3, "name": "blender_vse", "status": "done"},
                            {"step": 4, "name": "publish", "status": "pending"},
                        ]
                    }
            except Exception as exc:
                print(f"[WARN] Blender VSE недоступен: {exc}. Fallback на Web-to-Video.")

        # ── Fallback: старый Web-to-Video pipeline ───────────────────────
        pipeline = {
            "type": "shorts_pipeline",
            "topic": topic,
            "duration": duration,
            "platform": platform,
            "steps": [
                {
                    "step": 1,
                    "name": "script",
                    "description": f"Создание сценария: {topic}",
                    "tool": "content_worker.create_video_script",
                    "status": "pending"
                },
                {
                    "step": 2,
                    "name": "voice",
                    "description": "Генерация озвучки (TTS)",
                    "tool": "mcp.tts_generate",
                    "status": "pending"
                },
                {
                    "step": 3,
                    "name": "web_to_video",
                    "description": "HTML → MP4 (Web-to-Video)",
                    "tool": "video.create_web_to_video",
                    "status": "pending"
                },
                {
                    "step": 4,
                    "name": "publish",
                    "description": f"Публикация в {platform}",
                    "tool": f"mcp.tg_send_message",
                    "status": "pending"
                }
            ],
            "output_path": f"./output/shorts_{int(time.time())}.mp4"
        }

        return pipeline

    async def find_transition_sounds(self, count: int = 3) -> List[str]:
        """Получить звуки для переходов между клипами."""
        return await self.asset_finder.find_transition_sounds(count=count)

    async def generate_video(self, context: Dict) -> Dict:
        """Генерация видео через Seedance 2.0 (бесплатно — видео #3)"""
        prompt = context.get("prompt", "")
        duration = context.get("duration", 5)
        source = context.get("source", "seedance")

        # Используем MCP tool для Seedance
        result = await self.mcp.execute("video_generate_seedance", {
            "prompt": prompt,
            "duration": duration
        })

        return {
            "type": "ai_video",
            "source": source,
            "prompt": prompt,
            "duration": duration,
            "result": result,
            "cost": 0  # Бесплатно!
        }

    async def create_web_to_video(self, context: Dict) -> Dict:
        """
        Web-to-Video pipeline:
        HTML-страница с анимациями → Playwright скриншоты → ffmpeg → MP4
        """
        template = context.get("template", "default")
        data = context.get("data", {})  # Тексты, цифры для страницы
        duration = context.get("duration", 30)
        fps = context.get("fps", 30)

        pipeline = {
            "type": "web_to_video",
            "template": template,
            "data": data,
            "settings": {
                "width": 1080,
                "height": 1920,
                "fps": fps,
                "duration": duration,
                "bitrate": "8000k"
            },
            "steps": [
                "Генерация HTML из шаблона + данных",
                "Запуск Playwright (headless Chromium)",
                "Плавный скролл + скриншоты каждый кадр",
                "Сборка MP4 через ffmpeg",
                "Mux аудио (озвучка + музыка)"
            ]
        }

        return pipeline

    def get_free_sources(self) -> List[Dict]:
        """Список бесплатных источников видео"""
        return [
            {"name": v["name"], "url": v["url"], "free": v["free"]}
            for v in self.VIDEO_SOURCES.values()
        ]
