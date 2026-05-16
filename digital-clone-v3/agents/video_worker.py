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
        3. Web-to-Video (HTML → MP4)
        4. Публикация (tg_publish.py)
        """
        topic = context.get("topic", "AI автоматизация")
        duration = context.get("duration", 30)
        platform = context.get("platform", "telegram")  # telegram/youtube/instagram

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
                    "tool": f"mcp.tg_send_message",  # или yt_publish
                    "status": "pending"
                }
            ],
            "output_path": f"./output/shorts_{int(time.time())}.mp4"
        }

        return pipeline

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
