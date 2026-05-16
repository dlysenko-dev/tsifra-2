"""
Content Worker v3
Создание контента: посты, шортсы, статьи, PDF.
Бизнес-модель: клиппинг (видео #6)
"""

import asyncio
import json
from typing import Dict, List, Any
from pathlib import Path


class ContentWorker:
    """
    Воркер контента. Задачи:
    - Написать пост для Telegram/соцсетей
    - Создать сценарий для видео
    - Написать статью/лонгрид
    - Создать PDF-продукт (из видео #19: $20K/month)
    - Сделать клиппинг (видео #6)

    Бизнес-модели:
    1. Клиппинг: создание шортсов на заказ (платформы: Kwork, Weblancer, FL.ru)
    2. PDF-продукты: шаблоны, гайды, чеклисты (продажа на Gumroad, Patreon)
    3. Контент-менеджмент: ведение TG/IG каналов
    """

    CLIPPING_PLATFORMS = [
        {"name": "Kwork", "url": "kwork.ru", "avg_price": "500-2000\u20bd"},
        {"name": "Weblancer", "url": "weblancer.net", "avg_price": "300-1500\u20bd"},
        {"name": "FL.ru", "url": "fl.ru", "avg_price": "500-3000\u20bd"},
        {"name": "Fiverr", "url": "fiverr.com", "avg_price": "$10-50"},
    ]

    PDF_NICHES = [
        "AI-\u0430\u0432\u0442\u043e\u043c\u0430\u0442\u0438\u0437\u0430\u0446\u0438\u044f \u0431\u0438\u0437\u043d\u0435\u0441\u0430",
        "\u041f\u0440\u043e\u043c\u043f\u0442\u044b \u0434\u043b\u044f ChatGPT/Claude",
        "\u0427\u0435\u043a\u043b\u0438\u0441\u0442\u044b \u043f\u043e \u043d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0435 \u0430\u0433\u0435\u043d\u0442\u043e\u0432",
        "\u0428\u0430\u0431\u043b\u043e\u043d\u044b \u043a\u043e\u043d\u0442\u0435\u043d\u0442-\u043f\u043b\u0430\u043d\u0430",
        "\u0413\u0430\u0439\u0434\u044b \u043f\u043e vibe coding",
    ]

    def __init__(self, llm_router=None, mcp_layer=None):
        self.llm = llm_router
        self.mcp = mcp_layer

    async def execute(self, task, thought_chain):
        """\u0413\u043b\u0430\u0432\u043d\u044b\u0439 \u0432\u0445\u043e\u0434"""
        action = task.description.lower()

        if "\u043f\u043e\u0441\u0442" in action or "telegram" in action:
            return await self.create_telegram_post(task.context)
        elif "\u0441\u0446\u0435\u043d\u0430\u0440\u0438\u0439" in action or "script" in action:
            return await self.create_video_script(task.context)
        elif "pdf" in action or "\u043f\u0440\u043e\u0434\u0443\u043a\u0442" in action:
            return await self.create_pdf_product(task.context)
        elif "\u043a\u043b\u0438\u043f\u043f\u0438\u043d\u0433" in action or "\u043a\u043b\u0438\u043f" in action or "shorts" in action:
            return await self.create_clipping_offer(task.context)
        elif "\u043b\u043e\u043d\u0433\u0440\u0438\u0434" in action or "\u0441\u0442\u0430\u0442\u044c\u044f" in action:
            return await self.create_longread(task.context)
        else:
            # \u041e\u0431\u0449\u0438\u0439 \u043a\u043e\u043d\u0442\u0435\u043d\u0442 \u0447\u0435\u0440\u0435\u0437 LLM
            return await self.llm.complete(task.description)

    async def create_telegram_post(self, context: Dict) -> Dict:
        """\u0421\u043e\u0437\u0434\u0430\u0442\u044c \u043f\u043e\u0441\u0442 \u0434\u043b\u044f Telegram"""
        topic = context.get("topic", "AI \u0430\u0432\u0442\u043e\u043c\u0430\u0442\u0438\u0437\u0430\u0446\u0438\u044f")
        style = context.get("style", "\u044d\u043a\u0441\u043f\u0435\u0440\u0442\u043d\u044b\u0439")
        length = context.get("length", "\u0441\u0440\u0435\u0434\u043d\u0438\u0439")  # \u043a\u043e\u0440\u043e\u0442\u043a\u0438\u0439/\u0441\u0440\u0435\u0434\u043d\u0438\u0439/\u0434\u043b\u0438\u043d\u043d\u044b\u0439

        prompt = f"""\u041d\u0430\u043f\u0438\u0448\u0438 \u043f\u043e\u0441\u0442 \u0434\u043b\u044f Telegram \u043d\u0430 \u0442\u0435\u043c\u0443: {topic}
        \u0421\u0442\u0438\u043b\u044c: {style}
        \u0414\u043b\u0438\u043d\u0430: {length}

        \u0422\u0440\u0435\u0431\u043e\u0432\u0430\u043d\u0438\u044f:
        - \u0426\u0435\u043f\u043b\u044f\u044e\u0449\u0435\u0435 \u043d\u0430\u0447\u0430\u043b\u043e (\u0445\u0443\u043a)
        - \u041f\u043e\u043b\u0435\u0437\u043d\u0430\u044f \u0438\u043d\u0444\u043e\u0440\u043c\u0430\u0446\u0438\u044f
        - \u041f\u0440\u0438\u0437\u044b\u0432 \u043a \u0434\u0435\u0439\u0441\u0442\u0432\u0438\u044e (\u043f\u043e\u0434\u043f\u0438\u0441\u043a\u0430, \u043a\u043e\u043c\u043c\u0435\u043d\u0442\u0430\u0440\u0438\u0439)
        - 2-3 \u044d\u043c\u043e\u0434\u0437\u0438
        - \u0425\u044d\u0448\u0442\u0435\u0433\u0438
        """

        content = await self.llm.complete(prompt, max_tokens=1500)

        return {
            "type": "telegram_post",
            "content": content,
            "topic": topic,
            "length": len(content),
            "ready_to_publish": True
        }

    async def create_video_script(self, context: Dict) -> Dict:
        """\u0421\u043e\u0437\u0434\u0430\u0442\u044c \u0441\u0446\u0435\u043d\u0430\u0440\u0438\u0439 \u0434\u043b\u044f \u0448\u043e\u0440\u0442\u0441\u0430"""
        topic = context.get("topic", "AI \u0430\u0432\u0442\u043e\u043c\u0430\u0442\u0438\u0437\u0430\u0446\u0438\u044f")
        duration = context.get("duration", 30)  # \u0441\u0435\u043a\u0443\u043d\u0434
        format_type = context.get("format", "infographic")  # infographic/talking/narrative

        prompt = f"""\u0421\u043e\u0437\u0434\u0430\u0439 \u0441\u0446\u0435\u043d\u0430\u0440\u0438\u0439 \u0434\u043b\u044f \u0448\u043e\u0440\u0442\u0441\u0430 ({duration} \u0441\u0435\u043a\u0443\u043d\u0434) \u043d\u0430 \u0442\u0435\u043c\u0443: {topic}
        \u0424\u043e\u0440\u043c\u0430\u0442: {format_type}

        \u0421\u0442\u0440\u0443\u043a\u0442\u0443\u0440\u0430:
        1. \u0425\u0423\u041a (0-3 \u0441\u0435\u043a): \u0447\u0442\u043e \u0446\u0435\u043f\u043b\u044f\u0435\u0442 \u0432\u043d\u0438\u043c\u0430\u043d\u0438\u0435
        2. \u041f\u0420\u041e\u0411\u041b\u0415\u041c\u0410 (3-10 \u0441\u0435\u043a): \u0431\u043e\u043b\u044c \u0437\u0440\u0438\u0442\u0435\u043b\u044f
        3. \u0420\u0415\u0428\u0415\u041d\u0418\u0415 (10-{duration-5} \u0441\u0435\u043a): \u043a\u0430\u043a \u0440\u0435\u0448\u0438\u0442\u044c
        4. CTA ({duration-5}-{duration} \u0441\u0435\u043a): \u043f\u0440\u0438\u0437\u044b\u0432 \u043a \u0434\u0435\u0439\u0441\u0442\u0432\u0438\u044e

        \u0414\u043b\u044f \u043a\u0430\u0436\u0434\u043e\u0433\u043e \u0431\u043b\u043e\u043a\u0430 \u0443\u043a\u0430\u0436\u0438:
        - \u0422\u0435\u043a\u0441\u0442 (\u043e\u0437\u0432\u0443\u0447\u043a\u0430)
        - \u0412\u0438\u0437\u0443\u0430\u043b (\u0447\u0442\u043e \u043d\u0430 \u044d\u043a\u0440\u0430\u043d\u0435)
        - \u0410\u043d\u0438\u043c\u0430\u0446\u0438\u044f (\u043a\u0430\u043a \u043f\u043e\u044f\u0432\u043b\u044f\u0435\u0442\u0441\u044f)
        """

        script = await self.llm.complete(prompt, max_tokens=2000)

        return {
            "type": "video_script",
            "topic": topic,
            "duration": duration,
            "format": format_type,
            "script": script,
            "scenes": self._parse_scenes(script)
        }

    async def create_pdf_product(self, context: Dict) -> Dict:
        """\u0421\u043e\u0437\u0434\u0430\u0442\u044c PDF-\u043f\u0440\u043e\u0434\u0443\u043a\u0442 ($20K/month model \u2014 \u0432\u0438\u0434\u0435\u043e #19)"""
        niche = context.get("niche", "AI-\u0430\u0432\u0442\u043e\u043c\u0430\u0442\u0438\u0437\u0430\u0446\u0438\u044f")
        product_type = context.get("type", "\u0433\u0430\u0439\u0434")  # \u0433\u0430\u0439\u0434/\u0447\u0435\u043a\u043b\u0438\u0441\u0442/\u0448\u0430\u0431\u043b\u043e\u043d
        pages = context.get("pages", 10)

        prompt = f"""\u0421\u043e\u0437\u0434\u0430\u0439 \u0441\u0442\u0440\u0443\u043a\u0442\u0443\u0440\u0443 PDF-\u043f\u0440\u043e\u0434\u0443\u043a\u0442\u0430:
        \u0422\u0435\u043c\u0430: {niche}
        \u0422\u0438\u043f: {product_type}
        \u0421\u0442\u0440\u0430\u043d\u0438\u0446: {pages}

        \u0411\u0438\u0437\u043d\u0435\u0441-\u043c\u043e\u0434\u0435\u043b\u044c (\u0438\u0437 \u0432\u0438\u0434\u0435\u043e): \u043f\u0440\u043e\u0434\u0430\u0451\u043c \u043d\u0430 Gumroad/Patreon \u043f\u043e $5-20

        \u0414\u0430\u0439:
        1. \u041d\u0430\u0437\u0432\u0430\u043d\u0438\u0435 \u043f\u0440\u043e\u0434\u0443\u043a\u0442\u0430 (\u0446\u0435\u043f\u043b\u044f\u044e\u0449\u0435\u0435)
        2. \u041e\u043f\u0438\u0441\u0430\u043d\u0438\u0435 \u0434\u043b\u044f \u043f\u0440\u043e\u0434\u0430\u0436\u043d\u043e\u0439 \u0441\u0442\u0440\u0430\u043d\u0438\u0446\u044b
        3. \u041e\u0433\u043b\u0430\u0432\u043b\u0435\u043d\u0438\u0435 (\u0441\u0442\u0440\u0443\u043a\u0442\u0443\u0440\u0430 PDF)
        4. \u0426\u0435\u043d\u0430 ($)
        5. \u041f\u043b\u0430\u0442\u0444\u043e\u0440\u043c\u044b \u0434\u043b\u044f \u043f\u0440\u043e\u0434\u0430\u0436\u0438
        """

        result = await self.llm.complete(prompt, max_tokens=2000)

        return {
            "type": "pdf_product",
            "niche": niche,
            "product_type": product_type,
            "structure": result,
            "monetization": {
                "price_range": "$5-20",
                "platforms": ["Gumroad", "Patreon", "Telegram"],
                "potential": "$500-5000/\u043c\u0435\u0441\u044f\u0446"  # \u0438\u0437 \u0432\u0438\u0434\u0435\u043e #19
            }
        }

    async def create_clipping_offer(self, context: Dict) -> Dict:
        """\u0421\u043e\u0437\u0434\u0430\u0442\u044c \u043f\u0440\u0435\u0434\u043b\u043e\u0436\u0435\u043d\u0438\u0435 \u043d\u0430 \u043a\u043b\u0438\u043f\u043f\u0438\u043d\u0433 (\u0432\u0438\u0434\u0435\u043e #6)"""
        platform = context.get("platform", "all")

        offer = {
            "type": "clipping_service",
            "service": "\u0421\u043e\u0437\u0434\u0430\u043d\u0438\u0435 Shorts/Reels/TikTok",
            "description": "\u0410\u0432\u0442\u043e\u043c\u0430\u0442\u0438\u0447\u0435\u0441\u043a\u043e\u0435 \u0441\u043e\u0437\u0434\u0430\u043d\u0438\u0435 \u0432\u0438\u0440\u0443\u0441\u043d\u044b\u0445 \u0448\u043e\u0440\u0442\u0441\u043e\u0432 \u0438\u0437 \u0432\u0430\u0448\u0435\u0433\u043e \u043a\u043e\u043d\u0442\u0435\u043d\u0442\u0430",
            "platforms": self.CLIPPING_PLATFORMS,
            "pricing": {
                "per_video": "300-1000\u20bd",
                "pack_10": "2500-8000\u20bd",
                "monthly": "15000-50000\u20bd/\u043c\u0435\u0441\u044f\u0446"
            },
            "delivery": "24-48 \u0447\u0430\u0441\u043e\u0432",
            "includes": [
                "\u041d\u0430\u043f\u0438\u0441\u0430\u043d\u0438\u0435 \u0441\u0446\u0435\u043d\u0430\u0440\u0438\u044f",
                "\u0413\u0435\u043d\u0435\u0440\u0430\u0446\u0438\u044f \u0432\u0438\u0434\u0435\u043e (Web-to-Video)",
                "\u041e\u0437\u0432\u0443\u0447\u043a\u0430 (TTS)",
                "\u0421\u0443\u0431\u0442\u0438\u0442\u0440\u044b",
                "\u041c\u0443\u0437\u044b\u043a\u0430",
                "\u041f\u0443\u0431\u043b\u0438\u043a\u0430\u0446\u0438\u044f \u0432 \u0441\u043e\u0446\u0441\u0435\u0442\u0438"
            ]
        }

        return offer

    async def create_longread(self, context: Dict) -> Dict:
        """\u0421\u043e\u0437\u0434\u0430\u0442\u044c \u043b\u043e\u043d\u0433\u0440\u0438\u0434/\u0441\u0442\u0430\u0442\u044c\u044e"""
        topic = context.get("topic", "")
        word_count = context.get("words", 2000)

        prompt = f"""\u041d\u0430\u043f\u0438\u0448\u0438 \u043b\u043e\u043d\u0433\u0440\u0438\u0434 ({word_count} \u0441\u043b\u043e\u0432) \u043d\u0430 \u0442\u0435\u043c\u0443: {topic}

        \u0421\u0442\u0440\u0443\u043a\u0442\u0443\u0440\u0430:
        - \u0417\u0430\u0433\u043e\u043b\u043e\u0432\u043e\u043a (\u0446\u0435\u043f\u043b\u044f\u044e\u0449\u0438\u0439)
        - \u0412\u0432\u0435\u0434\u0435\u043d\u0438\u0435 (\u043b\u0438\u0447\u043d\u0430\u044f \u0438\u0441\u0442\u043e\u0440\u0438\u044f/\u043f\u0440\u043e\u0431\u043b\u0435\u043c\u0430)
        - 3-5 \u043e\u0441\u043d\u043e\u0432\u043d\u044b\u0445 \u0431\u043b\u043e\u043a\u043e\u0432 \u0441 \u043f\u043e\u0434\u0437\u0430\u0433\u043e\u043b\u043e\u0432\u043a\u0430\u043c\u0438
        - \u041f\u0440\u0438\u043c\u0435\u0440\u044b \u0438 \u043a\u0435\u0439\u0441\u044b
        - \u0417\u0430\u043a\u043b\u044e\u0447\u0435\u043d\u0438\u0435 \u0441 CTA
        - \u0425\u044d\u0448\u0442\u0435\u0433\u0438
        """

        content = await self.llm.complete(prompt, max_tokens=3000)

        return {
            "type": "longread",
            "topic": topic,
            "word_count": len(content.split()),
            "content": content
        }

    def _parse_scenes(self, script: str) -> List[Dict]:
        """\u041f\u0430\u0440\u0441\u0438\u043d\u0433 \u0441\u0446\u0435\u043d\u0430\u0440\u0438\u044f \u043d\u0430 \u0441\u0446\u0435\u043d\u044b"""
        # \u041f\u0440\u043e\u0441\u0442\u043e\u0439 \u043f\u0430\u0440\u0441\u0438\u043d\u0433 \u2014 \u043c\u043e\u0436\u043d\u043e \u0443\u043b\u0443\u0447\u0448\u0438\u0442\u044c
        scenes = []
        lines = script.split('\n')
        current_scene = {}

        for line in lines:
            if line.strip().startswith(('1.', '2.', '3.', '4.', '###')):
                if current_scene:
                    scenes.append(current_scene)
                current_scene = {"title": line.strip(), "content": []}
            elif current_scene:
                current_scene["content"].append(line)

        if current_scene:
            scenes.append(current_scene)

        return scenes
