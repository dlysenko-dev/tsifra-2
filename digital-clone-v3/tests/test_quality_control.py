"""
test_quality_control.py — Демонстрация работы Quality Control Engine.

Запуск:
    cd /mnt/agents/output/digital-clone-v3 && python test_quality_control.py
"""

from __future__ import annotations

import asyncio
import logging
import sys
import os

# Добавляем корень проекта в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.quality_control import ContentQualityChecker, QualityCheckPipeline
from core.tov_profile import ToVProfile

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("demo")


# ── Тестовый контент: хороший Telegram-пост ──────────────────────────────

GOOD_TELEGRAM_POST = """Прикинь — 87% разработчиков никогда не проверяют контент перед публикацией.

И потом удивляются, почему их посты собирают 3 лайка и один коммент от бабушки.

Я вот тоже так было — писал пост, жмякал "опубликовать", а потом через 2 минуты замечал опечатку в первом же предложении.

Фишка в том, что проверка контента — это не про перфекционизм. Это про уважение к читателю.

Так что вот 3 простых правила:
1. Прочитай вслух перед публикацией
2. Проверь первое предложение отдельно — оно должно цеплять
3. Убедись, что есть CTA (призыв к действию)

Короче, сделал систему автоматической проверки качества. Смотри — вот отчёт прямо под этим постом.

Пиши в комментариях — как ты проверяешь свои посты перед публикацией?"""


# ── Тестовый контент: плохой пост (с нарушениями) ──────────────────────

BAD_TELEGRAM_POST = """уважаемый клиент, в соответствии с вышеизложенным, хотелось бы отметить, что данное предложение является уникальным.

Наша компания предлагает инновационные решения на основе передовых технологий. Высококввалифицированные специалисты реализуют комплексный подход к каждому проекту.

СИНЕРГИЯ ПАРАДИГМЫ ВЕКТОРА ЭКОСИСТЕМЫ!!! Это революционный прорывной масштабный проект!!!!

Кликай сюда!!! Buy now!!! Limited time only!!! Earn $$$!!!

Ждем вашего ответа в кратчайшие сроки."""


# ── Тестовый контент: Shorts-скрипт ─────────────────────────────────────

SHORTS_SCRIPT = """[пауза]

Знаешь, почему твой код работает только по четвергам?

[пауза]

87% багов возникают из-за гонки данных. А ты даже не знаешь, что это такое.

[пауза]

Вот три признака, что у тебя race condition:
1. Баг появляется только при высокой нагрузке
2. Результат меняется от запуска к запуску
3. Добавление print() "чинит" баг

[пауза]

Фишка в том, что print() не чинит — он просто замедляет выполнение.

[пауза]

Настоящее решение — атомарные операции и mutex. Или вообще отказ от shared state.

[пауза]

Подпишись — завтра разберём на живом коде. Комментируй, если сталкивался!"""


# ── Мок-LLM Router (для демонстрации без реального LLM) ─────────────────

class MockLLMRouter:
    """Мок для демонстрации — имитирует ответ LLM."""

    async def complete(self, prompt: str) -> str:
        await asyncio.sleep(0.1)  # имитируем задержку
        return """{
  "scores": {
    "hook": 8,
    "value": 9,
    "structure": 8,
    "cta": 7,
    "branding": 9,
    "engagement": 8
  },
  "verdict": "PASS",
  "fixes": [],
  "summary": "Отличный пост: сильный хук, высокая информационная ценность, хороший CTA."
}"""


# ── Демонстрация ─────────────────────────────────────────────────────────

async def demo():
    print("=" * 60)
    print("  Quality Control Engine — Demo")
    print("  Digital Clone v3")
    print("=" * 60)
    print()

    # Инициализация с мок-роутером
    checker = ContentQualityChecker(llm_router=MockLLMRouter())

    print(f"📋 Поддерживаемые типы контента: {checker.supported_content_types()}")
    print()

    # ── Демо 1: Хороший пост ──────────────────────────────────────────
    print("─" * 60)
    print("  🟢 ДЕМО 1: Хороший Telegram-пост")
    print("─" * 60)
    print()

    report1 = await checker.check(GOOD_TELEGRAM_POST, content_type="telegram_post")
    print(report1.to_human_readable())
    print()

    # ── Демо 2: Плохой пост ───────────────────────────────────────────
    print("─" * 60)
    print("  🔴 ДЕМО 2: Плохой пост (корпоративщина, капс, спам)")
    print("─" * 60)
    print()

    report2 = await checker.check(BAD_TELEGRAM_POST, content_type="telegram_post")
    print(report2.to_human_readable())
    print()

    # ── Демо 3: Shorts-скрипт ─────────────────────────────────────────
    print("─" * 60)
    print("  🎬 ДЕМО 3: Shorts-скрипт")
    print("─" * 60)
    print()

    report3 = await checker.check(SHORTS_SCRIPT, content_type="shorts_script")
    print(report3.to_human_readable())
    print()

    # ── Демо 4: Быстрая проверка ──────────────────────────────────────
    print("─" * 60)
    print("  ⚡ ДЕМО 4: Быстрая проверка (quick_check)")
    print("─" * 60)
    print()

    quick = await checker.quick_check(GOOD_TELEGRAM_POST)
    print(f"  Результат быстрой проверки:")
    for key, value in quick.items():
        emoji = "✅" if value in (True, "True") else ("❌" if value in (False, "False") else "📊")
        print(f"    {emoji} {key}: {value}")
    print()

    # ── Демо 5: ToV Profile ───────────────────────────────────────────
    print("─" * 60)
    print("  🎭 ДЕМО 5: ToV Profile — проверка стиля Данила")
    print("─" * 60)
    print()

    tov = ToVProfile()
    tov_result = tov.check_text(GOOD_TELEGRAM_POST)
    print(f"  ToV Score: {tov_result['score']:.0f}/100")
    print(f"  Passed: {tov_result['passed']}")
    print(f"  Канцеляризмов найдено: {len(tov_result['taboo_violations'])}")
    print(f"  Характерных фраз: {tov_result['signature_phrase_count']}")
    print(f"  Средняя длина предложения: {tov_result['sentence_stats']['avg_length']}")
    print(f"  Лицо обращения: {tov_result['person']['dominant']} (2-е: {tov_result['person']['second_ratio']:.0%})")
    print(f"  Рекомендации: {tov_result['suggestions'] or 'Нет'}")
    print()

    # ── Сводка ──────────────────────────────────────────────────────────
    print("=" * 60)
    print("  📊 СВОДКА")
    print("=" * 60)
    print()

    summaries = [
        ("Хороший пост", report1),
        ("Плохой пост", report2),
        ("Shorts-скрипт", report3),
    ]

    for name, report in summaries:
        emoji = "✅" if report.auto_approved else ("⚠️" if report.passed else "❌")
        print(f"  {emoji} {name:20s} | Score: {report.quality_score:3d}/100 | "
              f"Passed: {'YES ' if report.passed else 'NO  '} | "
              f"Auto-approve: {'YES' if report.auto_approved else 'NO '}")

    print()
    print("=" * 60)
    print("  ✅ Демонстрация завершена")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(demo())
