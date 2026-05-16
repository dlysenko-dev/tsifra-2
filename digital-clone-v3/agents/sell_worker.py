"""
Sell Worker v3
Продажи: ответы клиентам, воронки, предложения, монетизация.
Бизнес-модели из видео: клиппинг (#6), PDF-продукты (#19), бесплатные LLM (#8)
"""

import asyncio
import json
from typing import Dict, List, Any
from datetime import datetime


class SellWorker:
    """
    Воркер продаж. Задачи:
    - Ответить клиенту
    - Создать коммерческое предложение
    - Управление воронкой
    - Монетизация контента

    Бизнес-модели:
    1. Клиппинг-сервис (видео #6)
    2. PDF-продукты (видео #19: $20K/month)
    3. Подписка на контент
    4. Консультации
    """

    PRICING = {
        "clipping_per_video": "500-2000₽",
        "clipping_monthly": "15000-50000₽",
        "pdf_guide": "$5-15",
        "pdf_template": "$10-30",
        "consultation_hour": "$50-100",
        "content_management_monthly": "30000-100000₽",
    }

    def __init__(self, llm_router=None, mcp_layer=None):
        self.llm = llm_router
        self.mcp = mcp_layer

    async def execute(self, task, thought_chain):
        """Главный вход"""
        action = task.description.lower()

        if "клиент" in action or "ответ" in action or "lead" in action:
            return await self.respond_to_client(task.context)
        elif "предложение" in action or "offer" in action or "кп" in action:
            return await self.create_offer(task.context)
        elif "воронка" in action or "funnel" in action:
            return await self.manage_funnel(task.context)
        elif "монетизация" in action or "money" in action:
            return await self.monetization_strategy(task.context)
        else:
            return await self.respond_to_client(task.context)

    async def respond_to_client(self, context: Dict) -> Dict:
        """Ответ клиенту (через Telegram/email)"""
        client_message = context.get("message", "")
        channel = context.get("channel", "telegram")
        tone = context.get("tone", "professional")  # professional/friendly/expert

        prompt = f"""Напиши ответ клиенту.

        Сообщение клиента: {client_message}
        Тон: {tone}
        Канал: {channel}

        Правила:
        - Отвечай на языке клиента (русский/английский)
        - Будь {tone}
        - Если клиент спрашивает про услуги — дай краткое описание + цену
        - Если клиент хочет купить — направь на оплату
        - Если не знаешь ответ — скажи что уточнишь

        Наши услуги:
        - Создание Shorts/Reels/TikTok: 500-2000₽/видео
        - Ведение соцсетей: от 30000₽/месяц
        - AI-автоматизация: индивидуально
        """

        response = await self.llm.complete(prompt, max_tokens=800)

        return {
            "type": "client_response",
            "original_message": client_message,
            "response": response,
            "channel": channel,
            "ready_to_send": True
        }

    async def create_offer(self, context: Dict) -> Dict:
        """Создать коммерческое предложение"""
        service = context.get("service", "контент")
        client_type = context.get("client_type", "small")  # small/medium/enterprise
        budget = context.get("budget", "")

        offer_templates = {
            "clipping": {
                "title": "Пакет 'Shorts Machine'",
                "description": "Автоматическое создание вирусных шортсов",
                "packages": [
                    {"name": "Старт", "price": "15000₽/мес", "includes": "10 видео"},
                    {"name": "Про", "price": "30000₽/мес", "includes": "25 видео + аналитика"},
                    {"name": "Бизнес", "price": "50000₽/мес", "includes": "50 видео + стратегия"},
                ]
            },
            "content": {
                "title": "Ведение каналов",
                "description": "Полное ведение Telegram/Instagram/YouTube",
                "packages": [
                    {"name": "Базовый", "price": "30000₽/мес"},
                    {"name": "Продвинутый", "price": "60000₽/мес"},
                    {"name": "Премиум", "price": "100000₽/мес"},
                ]
            }
        }

        template = offer_templates.get(service, offer_templates["content"])

        prompt = f"""Создай коммерческое предложение:

        Услуга: {template['title']}
        Описание: {template['description']}
        Клиент: {client_type}
        Бюджет: {budget}

        Дай:
        1. Привлекательное название
        2. Описание ценности
        3. 3 варианта пакетов с ценами
        4. Что входит в каждый пакет
        5. Примеры работ (описание)
        6. Призыв к действию
        """

        offer = await self.llm.complete(prompt, max_tokens=1500)

        return {
            "type": "commercial_offer",
            "service": service,
            "offer": offer,
            "pricing": self.PRICING,
            "generated_at": datetime.now().isoformat()
        }

    async def monetization_strategy(self, context: Dict) -> Dict:
        """Стратегия монетизации (из видео #19 и #6)"""
        niche = context.get("niche", "AI контент")
        audience = context.get("audience_size", "1000")

        strategies = [
            {
                "name": "PDF-продукты (видео #19)",
                "description": "Создание и продажа гайдов, чеклистов, шаблонов",
                "revenue_potential": "$500-5000/месяц",
                "platforms": ["Gumroad", "Patreon", "Telegram"],
                "effort": "Средне",
                "time_to_first_dollar": "1-2 недели"
            },
            {
                "name": "Клиппинг-сервис (видео #6)",
                "description": "Создание шортсов на заказ",
                "revenue_potential": "50000-200000₽/месяц",
                "platforms": ["Kwork", "FL.ru", "Fiverr"],
                "effort": "Высоко",
                "time_to_first_dollar": "Немедленно"
            },
            {
                "name": "Подписка на контент",
                "description": "Эксклюзивный контент за подписку",
                "revenue_potential": "$1000-10000/месяц",
                "platforms": ["Patreon", "Boosty", "Telegram"],
                "effort": "Средне",
                "time_to_first_dollar": "1 месяц"
            },
            {
                "name": "Консультации",
                "description": "Персональные консультации по AI",
                "revenue_potential": "$2000-10000/месяц",
                "platforms": ["Telegram", "Calendly"],
                "effort": "Низко",
                "time_to_first_dollar": "Немедленно"
            }
        ]

        prompt = f"""Создай стратегию монетизации для ниши: {niche}
        Аудитория: {audience} подписчиков

        Доступные модели: {json.dumps(strategies, ensure_ascii=False, indent=2)}

        Дай рекомендации:
        1. Какая модель подходит лучше всего (и почему)
        2. Порядок запуска (что сначала, что потом)
        3. План первого месяца
        4. Целевые метрики
        """

        strategy = await self.llm.complete(prompt, max_tokens=1500)

        return {
            "type": "monetization_strategy",
            "niche": niche,
            "strategies": strategies,
            "recommendation": strategy
        }

    async def manage_funnel(self, context: Dict) -> Dict:
        """Управление воронкой продаж"""
        stage = context.get("stage", "all")

        funnel = {
            "stages": [
                {"name": "Awareness", "description": "Привлечение внимания", "conversion": "100%"},
                {"name": "Interest", "description": "Проявление интереса", "conversion": "30%"},
                {"name": "Consideration", "description": "Сравнение вариантов", "conversion": "15%"},
                {"name": "Conversion", "description": "Покупка", "conversion": "5%"},
                {"name": "Retention", "description": "Возврат клиента", "conversion": "20%"},
            ],
            "metrics": {
                "leads_per_month": 100,
                "conversion_rate": "5%",
                "avg_check": "15000₽",
                "ltv": "45000₽"
            }
        }

        return funnel
