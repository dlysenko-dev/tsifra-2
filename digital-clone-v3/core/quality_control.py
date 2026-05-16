"""
quality_control.py — Quality Control Engine для Digital Clone v3.

Система контроля качества контента ПЕРЕД публикацией.
Проверяет: базовые параметры, хук, CTA, токсичность, ToV Данила,
прогноз вовлечённости, и финальный LLM-ревью.

Usage:
    checker = ContentQualityChecker(llm_router=router)
    report = await checker.check(content, content_type="telegram_post")
    if report.auto_approved:
        await publish(content)
    elif report.passed:
        await send_for_human_review(content, report)
    else:
        await rewrite(content, report.suggestions)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import statistics
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, Dict, List, Optional, Tuple

from .tov_profile import ToVProfile

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logger = logging.getLogger("quality_control")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Глобальные чек-листы по типу контента (переопределяются из JSON)
DEFAULT_CHECKLISTS: Dict[str, Dict[str, Any]] = {
    "telegram_post": {
        "min_length": 100,
        "max_length": 4000,
        "requires_hook": True,
        "requires_cta": True,
        "max_hashtags": 5,
        "requires_structure": True,   # хук → суть → CTA
    },
    "shorts_script": {
        "min_length": 200,
        "max_length": 2000,
        "requires_hook_3sec": True,
        "requires_pauses": True,      # [пауза] метки
        "max_words": 180,
        "words_per_minute": 150,
        "target_duration_sec": 60,
    },
    "blog_post": {
        "min_length": 500,
        "max_length": 10000,
        "requires_structure": True,
        "min_headers": 2,
    },
    "video_description": {
        "min_length": 100,
        "max_length": 5000,
        "requires_structure": False,
        "requires_hook": False,
        "requires_cta": True,
        "max_hashtags": 15,
    },
}

# CTA паттерны (регулярные выражения для разных языков)
CTA_PATTERNS: List[str] = [
    # Русские
    r"подпишись",
    r"подписывайся",
    r"ставь лайк",
    r"комментируй",
    r"комментариях",
    r"напиши в комментариях",
    r"делись мнением",
    r"поделись с друзьями",
    r"переходи по ссылке",
    r"загляни",
    r"сохрани",
    r"жми",
    r"кликай",
    r"заходи",
    r"оставь комментарий",
    r"читай далее",
    r"узнай больше",
    r"пиши в личку",
    r"пиши мне",
    r"поехали",
    r"погнали",
    r"давай",
    r"гойда",
    # English
    r"subscribe",
    r"follow",
    r"like this",
    r"comment below",
    r"share this",
    r"check out",
    r"click the link",
    r"swipe up",
    r"tap the link",
    r"join us",
    r"don.t miss",
    r"grab it",
    # Emoji
    r"👉",
    r"👆",
    r"🔥",
    r"⚡",
    r"❤️",
    r"👇",
    r"💬",
    r"🔗",
    r"📌",
    r"✅",
    r"❗",
    r"❓",
    r"🚀",
    r"💡",
    r"📢",
]

# Паттерны хука
HOOK_PATTERNS: List[str] = [
    r"\d+",                           # цифры
    r"\?",                            # вопросительный знак
    r"почему\b",
    r"как\b",
    r"что если\b",
    r"знаешь\b",
    r"представь\b",
    r"вот это\b",
    r"охренеть",
    r"жесть",
    r"капец",
    r"шок",
    r"безумие",
    r"взрыв",
    r"топ\s+\d+",
    r"\d+\s+(способ|факт|причина|ошибка|лайфхак)",
    r"никто не",
    r"все еще",
    r"перестань",
    r"хватит",
    r"не делай",
    r"забудь",
    r"секрет",
    r"правда о",
    r"вся правда",
    r"разоблачение",
]

# Паттерны структуры (Markdown заголовки)
STRUCTURE_HEADER_PATTERN = re.compile(r"^#{1,3}\s+", re.MULTILINE)

# Паттерны пауз для скриптов
PAUSE_PATTERN = re.compile(r"\[пауза\]|\[pause\]|\[\d+сек?\]|\(\d+сек?\)", re.IGNORECASE)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_thresholds(path: str) -> Dict[str, Any]:
    """Загрузить пороговые значения из JSON-файла."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.info("Загружены пороговые значения из %s", path)
        return data
    except FileNotFoundError:
        logger.warning("Файл порогов не найден: %s. Использую дефолты.", path)
        return {"global": {"auto_approve_threshold": 85, "pass_threshold": 60}}
    except json.JSONDecodeError as exc:
        logger.error("Ошибка парсинга JSON %s: %s", path, exc)
        return {"global": {"auto_approve_threshold": 85, "pass_threshold": 60}}


def _get_project_root() -> str:
    """Определить корень проекта относительно данного файла."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class CheckResult:
    """Результат одной проверки."""
    name: str
    passed: bool
    score: float           # 0-100
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    suggestions: List[str] = field(default_factory=list)
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "score": round(self.score, 1),
            "message": self.message,
            "details": self.details,
            "suggestions": self.suggestions,
            "duration_ms": round(self.duration_ms, 1),
        }


@dataclass
class QualityReport:
    """Полный отчёт проверки качества контента."""
    quality_score: int                     # 0-100
    passed: bool
    auto_approved: bool
    content_type: str
    checks: List[CheckResult]
    suggestions: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)
    llm_review: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "quality_score": self.quality_score,
            "passed": self.passed,
            "auto_approved": self.auto_approved,
            "content_type": self.content_type,
            "checks": [c.to_dict() for c in self.checks],
            "suggestions": self.suggestions,
            "metadata": self.metadata,
            "llm_review": self.llm_review,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    def to_human_readable(self) -> str:
        """Отформатированный отчёт для логов и Telegram.

        Returns:
            Многострочная строка с эмодзи и читаемым форматированием.
        """
        status_emoji = "✅" if self.auto_approved else ("⚠️" if self.passed else "❌")
        lines = [
            f"{status_emoji} Quality Report | {self.content_type}",
            f"{'─' * 40}",
            f"📊 Score: {self.quality_score}/100",
            f"🔐 Passed: {'YES' if self.passed else 'NO'}",
            f"🤖 Auto-approve: {'YES' if self.auto_approved else 'NO'}",
            f"{'─' * 40}",
        ]

        lines.append("")
        lines.append("📋 Checks:")
        for check in self.checks:
            emoji = "✅" if check.passed else "❌"
            lines.append(f"  {emoji} {check.name}: {check.score:.0f}/100")
            if check.message:
                lines.append(f"     {check.message}")
            for sug in check.suggestions[:3]:
                lines.append(f"     💡 {sug}")

        if self.llm_review:
            lines.append("")
            lines.append("🧠 LLM Review:")
            verdict = self.llm_review.get("verdict", "N/A")
            v_emoji = "✅" if verdict == "PASS" else "❌"
            lines.append(f"  {v_emoji} Verdict: {verdict}")
            scores = self.llm_review.get("scores", {})
            for k, v in scores.items():
                s_emoji = "✅" if (isinstance(v, (int, float)) and v >= 6) else "❌"
                lines.append(f"  {s_emoji} {k}: {v}")
            fixes = self.llm_review.get("fixes", [])
            if fixes:
                lines.append("  📝 Fixes:")
                for f in fixes[:5]:
                    lines.append(f"    • {f}")

        if self.suggestions:
            lines.append("")
            lines.append("💡 Suggestions:")
            for i, s in enumerate(self.suggestions[:10], 1):
                lines.append(f"  {i}. {s}")

        if self.metadata:
            lines.append("")
            lines.append("⏱ Timing:")
            for k, v in self.metadata.items():
                if "duration" in k.lower() or "time" in k.lower():
                    lines.append(f"  {k}: {v}")

        lines.append(f"{'─' * 40}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Individual Check Classes
# ---------------------------------------------------------------------------


class _BasicCheck:
    """Базовая проверка: длина, формат, пустые абзацы, Markdown."""

    name = "BasicCheck"

    async def run(self, content: str, checklist: Dict[str, Any]) -> CheckResult:
        start = time.monotonic()
        details: Dict[str, Any] = {}
        suggestions: List[str] = []
        score = 100.0
        passed = True

        # --- Длина ---
        text_length = len(content)
        char_count_no_spaces = len(content.replace(" ", "").replace("\n", ""))
        word_count = len(content.split())

        details["length_chars"] = text_length
        details["length_chars_no_spaces"] = char_count_no_spaces
        details["word_count"] = word_count

        min_len = checklist.get("min_length", 0)
        max_len = checklist.get("max_length", 999999)

        if text_length < min_len:
            passed = False
            score -= 30.0
            suggestions.append(
                f"Текст слишком короткий: {text_length} символов, минимум {min_len}"
            )
        if text_length > max_len:
            passed = False
            score -= 20.0
            suggestions.append(
                f"Текст слишком длинный: {text_length} символов, максимум {max_len}"
            )

        # --- Пустые абзацы ---
        empty_paragraphs = re.findall(r"\n\s*\n\s*\n", content)
        if empty_paragraphs:
            score -= 5.0 * len(empty_paragraphs)
            details["empty_paragraphs"] = len(empty_paragraphs)
            suggestions.append(f"Убери {len(empty_paragraphs)} лишних пустых абзацев")

        # --- Markdown форматирование ---
        has_markdown = bool(
            re.search(r"[*_`#\[\]()]", content)
        )
        details["has_markdown"] = has_markdown
        if not has_markdown and checklist.get("requires_structure", False):
            score -= 5.0
            suggestions.append("Добавь Markdown форматирование (жирный, курсив, ссылки)")

        # --- Хэштеги ---
        hashtags = re.findall(r"#\w+", content)
        details["hashtag_count"] = len(hashtags)
        details["hashtags"] = hashtags[:10]
        max_hashtags = checklist.get("max_hashtags")
        if max_hashtags is not None and len(hashtags) > max_hashtags:
            passed = False
            score -= 10.0
            suggestions.append(
                f"Слишком много хэштегов: {len(hashtags)}, максимум {max_hashtags}"
            )

        # --- Структура (заголовки) для blog_post ---
        headers = STRUCTURE_HEADER_PATTERN.findall(content)
        details["header_count"] = len(headers)
        min_headers = checklist.get("min_headers", 0)
        if min_headers > 0 and len(headers) < min_headers:
            passed = False
            score -= 15.0
            suggestions.append(
                f"Недостаточно заголовков: {len(headers)}, нужно минимум {min_headers}"
            )

        # --- Финальный скоринг ---
        score = max(0.0, score)
        message = (
            f"{word_count} слов, {text_length} символов"
            + (f", {len(hashtags)} хэштегов" if hashtags else "")
        )
        if not passed:
            message += f". {'; '.join(suggestions[:2])}"

        return CheckResult(
            name=self.name,
            passed=passed,
            score=score,
            message=message,
            details=details,
            suggestions=suggestions,
            duration_ms=(time.monotonic() - start) * 1000,
        )


class _HookCheck:
    """Проверка хука / первого предложения."""

    name = "HookCheck"

    async def run(self, content: str, checklist: Dict[str, Any]) -> CheckResult:
        start = time.monotonic()
        details: Dict[str, Any] = {}
        suggestions: List[str] = []
        score = 100.0
        passed = True

        # Для shorts: пропускаем маркеры пауз в начале
        stripped = content.strip()
        pause_skipped = 0
        while re.match(r"\[(?:пауза|pause|\d+сек?)\]|\(\d+сек?\)", stripped.strip().split("\n")[0].strip(), re.IGNORECASE):
            lines = stripped.split("\n", 1)
            if len(lines) > 1:
                stripped = lines[1]
                pause_skipped += 1
            else:
                break

        # Получаем первое предложение (после пропуска пауз)
        first_sentence_match = re.match(r"([^\.\n!?]+[\.\n!?])", stripped.strip())
        if first_sentence_match:
            first_sentence = first_sentence_match.group(1).strip()
        else:
            first_sentence = stripped.strip().split("\n")[0][:200]

        details["first_sentence"] = first_sentence
        details["pause_markers_skipped"] = pause_skipped
        first_words = first_sentence.split()
        details["first_sentence_word_count"] = len(first_words)

        # --- Хук должен быть коротким ---
        requires_hook_3sec = checklist.get("requires_hook_3sec", False)
        max_words = 8 if requires_hook_3sec else 15
        if len(first_words) > max_words:
            score -= 10.0
            suggestions.append(
                f"Первое предложение длинное ({len(first_words)} слов). "
                f"Сократи до {max_words}"
            )

        # --- Хук должен содержать "захват" ---
        has_hook_element = False
        matched_patterns: List[str] = []
        lower_first = first_sentence.lower()

        for pattern in HOOK_PATTERNS:
            if re.search(pattern, lower_first):
                has_hook_element = True
                matched_patterns.append(pattern)

        details["hook_patterns_matched"] = matched_patterns
        details["has_hook_element"] = has_hook_element

        if not has_hook_element:
            score -= 20.0
            suggestions.append(
                "Хук слабый. Добавь: цифру, вопрос, шок-факт или 'представь'"
            )

        # --- Для shorts — хук в первые 3 секунды = первые 8 слов ---
        if requires_hook_3sec:
            hook_words = content.strip().split()[:8]
            hook_text = " ".join(hook_words).lower()
            has_3sec_hook = any(
                re.search(p, hook_text) for p in HOOK_PATTERNS
            )
            details["has_3sec_hook"] = has_3sec_hook
            if not has_3sec_hook:
                score -= 25.0
                passed = False
                suggestions.append(
                    "Нет сильного хука в первые 3 секунды (первые 8 слов)"
                )

        # --- Требуется хук? ---
        requires_hook = checklist.get("requires_hook", True)
        if requires_hook and not has_hook_element:
            passed = False

        score = max(0.0, score)
        message = f"Первое предложение: \"{first_sentence[:80]}...\""
        if not passed:
            message += f". Слабый хук"

        return CheckResult(
            name=self.name,
            passed=passed,
            score=score,
            message=message,
            details=details,
            suggestions=suggestions,
            duration_ms=(time.monotonic() - start) * 1000,
        )


class _CtaCheck:
    """Проверка наличия призыва к действию (CTA)."""

    name = "CtaCheck"

    async def run(self, content: str, checklist: Dict[str, Any]) -> CheckResult:
        start = time.monotonic()
        details: Dict[str, Any] = {}
        suggestions: List[str] = []
        score = 100.0
        passed = True

        requires_cta = checklist.get("requires_cta", True)
        if not requires_cta:
            return CheckResult(
                name=self.name,
                passed=True,
                score=100.0,
                message="CTA не требуется для данного типа контента",
                details={"required": False},
                suggestions=[],
                duration_ms=(time.monotonic() - start) * 1000,
            )

        # Поиск CTA паттернов
        found_ctas: List[str] = []
        lower_content = content.lower()
        for pattern in CTA_PATTERNS:
            if re.search(pattern, lower_content):
                found_ctas.append(pattern)

        details["found_ctas"] = found_ctas
        details["cta_count"] = len(found_ctas)

        has_cta = len(found_ctas) > 0
        details["has_cta"] = has_cta

        # Проверка позиции CTA (лучше в конце)
        last_30_percent = content[int(len(content) * 0.7):]
        cta_in_end = any(
            re.search(p, last_30_percent.lower()) for p in CTA_PATTERNS
        )
        details["cta_in_end"] = cta_in_end

        if not has_cta:
            passed = False
            score -= 30.0
            suggestions.append(
                "Нет призыва к действия (CTA). Добавь: 'подпишись', "
                "'комментируй', 'ставь лайк', 'пиши в комментариях'"
            )
        elif not cta_in_end:
            score -= 10.0
            suggestions.append(
                "CTA лучше разместить в конце контента"
            )

        # Для shorts — CTA должен быть чётким и коротким
        if checklist.get("target_duration_sec"):
            if has_cta and len(found_ctas) > 2:
                score -= 5.0
                suggestions.append(
                    "В шортс CTA должен быть один и чёткий"
                )

        score = max(0.0, score)
        message = f"{'CTA найден' if has_cta else 'CTA НЕ найден'} ({len(found_ctas)} шт.)"
        if cta_in_end:
            message += ", CTA в конце ✓"

        return CheckResult(
            name=self.name,
            passed=passed,
            score=score,
            message=message,
            details=details,
            suggestions=suggestions,
            duration_ms=(time.monotonic() - start) * 1000,
        )


class _ToxicityCheck:
    """Проверка на токсичность: мат, капс-спам, повторы, спам-ссылки."""

    name = "ToxicityCheck"

    def __init__(self, tov: Optional[ToVProfile] = None) -> None:
        self.tov = tov or ToVProfile()

    async def run(self, content: str, checklist: Dict[str, Any]) -> CheckResult:
        start = time.monotonic()
        details: Dict[str, Any] = {}
        suggestions: List[str] = []
        score = 100.0
        passed = True

        # --- Проверка через ToV (мат, капс) ---
        toxicity = self.tov.check_toxicity(content)
        details.update(toxicity)

        if toxicity["has_hard_toxicity"]:
            passed = False
            score -= 40.0
            suggestions.append(
                f"Найден грубый мат: {', '.join(toxicity['toxic_matches'][:5])}"
            )

        if toxicity["caps_ratio"] > self.tov.max_caps_ratio:
            passed = False
            score -= 15.0
            suggestions.append(
                f"Слишком много КАПСА: {toxicity['caps_ratio']:.1%} "
                f"(макс {self.tov.max_caps_ratio:.0%})"
            )

        # --- Повторяющиеся символы (спам) ---
        spam_patterns = [
            r"(.)\1{5,}",              # "ааааааа" — повтор 6+
            r"[!?]{4,}",               # "!!!!" — 4+ знаков препинания
            r"\.{6,}",                 # "......" — 6+ точек
        ]
        spam_matches: List[str] = []
        for pat in spam_patterns:
            spam_matches.extend(re.findall(pat, content))
        details["spam_matches"] = spam_matches
        if spam_matches:
            score -= 10.0
            suggestions.append("Убери повторяющиеся символы (спам)")

        # --- Проверка ссылок ---
        urls = re.findall(r"https?://\S+", content)
        details["url_count"] = len(urls)
        details["urls"] = urls[:10]
        if len(urls) > 5:
            score -= 10.0
            suggestions.append(f"Слишком много ссылок: {len(urls)} (макс 5)")

        # --- Spam фразы ---
        spam_phrases = checklist.get(
            "spam_link_patterns",
            [
                "click here!!!",
                "buy now!!!",
                "limited time only!!!",
                "act now!!!",
                "earn $$$",
            ],
        )
        found_spam_phrases: List[str] = []
        lower_content = content.lower()
        for phrase in spam_phrases:
            if phrase.lower() in lower_content:
                found_spam_phrases.append(phrase)
        details["spam_phrases_found"] = found_spam_phrases
        if found_spam_phrases:
            passed = False
            score -= 20.0
            suggestions.append(f"Спам-фразы: {', '.join(found_spam_phrases)}")

        score = max(0.0, score)
        message = (
            f"Капс: {toxicity['caps_ratio']:.1%}, "
            f"мат: {'YES' if toxicity['has_hard_toxicity'] else 'NO'}, "
            f"спам паттернов: {len(spam_matches)}"
        )

        return CheckResult(
            name=self.name,
            passed=passed,
            score=score,
            message=message,
            details=details,
            suggestions=suggestions,
            duration_ms=(time.monotonic() - start) * 1000,
        )


class _BrandingCheck:
    """Проверка соответствия Tone of Voice Данила."""

    name = "BrandingCheck"

    def __init__(self, tov: Optional[ToVProfile] = None) -> None:
        self.tov = tov or ToVProfile()

    async def run(self, content: str, checklist: Dict[str, Any]) -> CheckResult:
        start = time.monotonic()
        details: Dict[str, Any] = {}
        suggestions: List[str] = []

        # Полная проверка через ToVProfile
        tov_result = self.tov.check_text(content)
        details.update(tov_result)

        score = tov_result["score"]
        passed = tov_result["passed"]
        suggestions.extend(tov_result["suggestions"])

        # Дополнительные проверки подписных фраз (бонус)
        sig_count = tov_result.get("signature_phrase_count", 0)
        details["signature_phrase_count"] = sig_count

        # Проверка длины предложений (разговорный стиль = короткие)
        sentence_stats = tov_result.get("sentence_stats", {})
        avg_len = sentence_stats.get("avg_length", 0)
        if avg_len > 20:
            score -= 5.0
            suggestions.append(f"Среднее предложение {avg_len} слов — сократи до 15-20")

        # Проверка на канцеляризмы
        taboo_count = len(tov_result.get("taboo_violations", []))
        details["taboo_count"] = taboo_count
        if taboo_count > 0:
            passed = False

        score = max(0.0, min(100.0, score))
        message = (
            f"ToV score: {score:.0f}/100, "
            f"табу: {taboo_count}, "
            f"характерных фраз: {sig_count}"
        )

        return CheckResult(
            name=self.name,
            passed=passed,
            score=score,
            message=message,
            details=details,
            suggestions=suggestions,
            duration_ms=(time.monotonic() - start) * 1000,
        )


class _StructureCheck:
    """Проверка структуры контента (хук → суть → CTA)."""

    name = "StructureCheck"

    async def run(self, content: str, checklist: Dict[str, Any]) -> CheckResult:
        start = time.monotonic()
        details: Dict[str, Any] = {}
        suggestions: List[str] = []
        score = 100.0
        passed = True

        # Анализ структуры по третям
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        details["paragraph_count"] = len(paragraphs)

        if not paragraphs:
            passed = False
            score = 0.0
            suggestions.append("Контент пустой или без структуры")
            return CheckResult(
                name=self.name,
                passed=False,
                score=0.0,
                message="Нет абзацев",
                details=details,
                suggestions=suggestions,
                duration_ms=(time.monotonic() - start) * 1000,
            )

        # Проверка: начало = хук, середина = суть, конец = CTA
        first_third = "\n".join(paragraphs[:max(1, len(paragraphs) // 3)])
        last_third = "\n".join(paragraphs[2 * len(paragraphs) // 3:])

        # Хук в начале?
        has_hook_start = any(
            re.search(p, first_third.lower()) for p in HOOK_PATTERNS
        )
        details["has_hook_in_first_third"] = has_hook_start

        # CTA в конце?
        has_cta_end = any(
            re.search(p, last_third.lower()) for p in CTA_PATTERNS
        )
        details["has_cta_in_last_third"] = has_cta_end

        if not has_hook_start:
            score -= 15.0
            suggestions.append("Структура: начни с хука")

        if not has_cta_end:
            score -= 15.0
            suggestions.append("Структура: заверши CTA")

        # Для shorts — проверка пауз
        requires_pauses = checklist.get("requires_pauses", False)
        if requires_pauses:
            pauses = PAUSE_PATTERN.findall(content)
            details["pause_count"] = len(pauses)
            if not pauses:
                score -= 20.0
                suggestions.append(
                    "Добавь маркеры пауз [пауза] или (2сек) для драматургии"
                )
            elif len(pauses) < 2:
                score -= 5.0
                suggestions.append("Добавь ещё пауз для лучшей драматургии")

        # Проверка длины скрипта shorts
        max_words = checklist.get("max_words")
        if max_words:
            words = content.split()
            details["script_word_count"] = len(words)
            if len(words) > max_words:
                passed = False
                score -= 25.0
                suggestions.append(
                    f"Скрипт слишком длинный: {len(words)} слов, "
                    f"максимум {max_words} (~{checklist.get('target_duration_sec', 60)} сек)"
                )

        score = max(0.0, score)
        if not has_hook_start or not has_cta_end:
            passed = False

        message = (
            f"{len(paragraphs)} абзацев, "
            f"хук в начале: {'YES' if has_hook_start else 'NO'}, "
            f"CTA в конце: {'YES' if has_cta_end else 'NO'}"
        )

        return CheckResult(
            name=self.name,
            passed=passed,
            score=score,
            message=message,
            details=details,
            suggestions=suggestions,
            duration_ms=(time.monotonic() - start) * 1000,
        )


class _EngagementPredictor:
    """Прогноз вовлечённости на основе эвристик."""

    name = "EngagementPredictor"

    # Веса для расчёта engagement score
    WEIGHTS: Dict[str, float] = {
        "hook_strength": 0.25,
        "readability": 0.20,
        "cta_strength": 0.20,
        "emotional_triggers": 0.15,
        "uniqueness": 0.10,
        "length_optimality": 0.10,
    }

    # Эмоциональные триггеры
    EMOTIONAL_TRIGGERS: List[str] = [
        r"\b(шок|капец|жесть|охренеть|обалдеть|пипец|невероятно|фантастика)\b",
        r"\b(секрет|тайна|правда|ложь|обман)\b",
        r"\b(никто не|все еще|перестань|хватит|забудь)\b",
        r"\b(почему|как|что если|знаешь ли ты)\b",
        r"\d+\s+(способ|факт|причина|ошибка|лайфхак|совет|правило)",
        r"!{1,2}",                           # восклицания (не спам)
    ]

    async def run(self, content: str, checklist: Dict[str, Any]) -> CheckResult:
        start = time.monotonic()
        details: Dict[str, Any] = {}
        suggestions: List[str] = []

        # --- 1. Hook Strength ---
        first_sentence = content[:200].lower()
        hook_matches = sum(
            1 for p in HOOK_PATTERNS if re.search(p, first_sentence)
        )
        hook_score = min(10.0, 4.0 + hook_matches * 2.0)
        details["hook_score"] = round(hook_score, 1)
        if hook_score < 6:
            suggestions.append("Усиль хук — добавь цифру, вопрос или интригу")

        # --- 2. Readability ---
        sentences = re.split(r"[.!?\n]+", content)
        sentences = [s.strip() for s in sentences if s.strip()]
        if sentences:
            sent_lengths = [len(s.split()) for s in sentences]
            avg_len = statistics.mean(sent_lengths) if sent_lengths else 0
            # Оптимум: 10-15 слов на предложение
            readability_score = 10.0 - abs(avg_len - 12.5) * 0.5
            readability_score = max(0.0, min(10.0, readability_score))
        else:
            readability_score = 0.0
        details["avg_sentence_length"] = round(avg_len, 1)
        details["readability_score"] = round(readability_score, 1)
        if readability_score < 5:
            suggestions.append(
                f"Читаемость низкая (среднее предложение {avg_len:.0f} слов). "
                f"Сократи до 10-15"
            )

        # --- 3. CTA Strength ---
        cta_matches = sum(
            1 for p in CTA_PATTERNS if re.search(p, content.lower())
        )
        cta_score = min(10.0, 3.0 + cta_matches * 1.5)
        details["cta_score"] = round(cta_score, 1)
        if cta_score < 5:
            suggestions.append("Добавь более чёткий призыв к действию")

        # --- 4. Emotional Triggers ---
        emotional_matches = sum(
            1 for p in self.EMOTIONAL_TRIGGERS if re.search(p, content.lower())
        )
        emotional_score = min(10.0, 3.0 + emotional_matches * 1.5)
        details["emotional_triggers_count"] = emotional_matches
        details["emotional_score"] = round(emotional_score, 1)
        if emotional_score < 5:
            suggestions.append(
                "Добавь эмоциональных триггеров (вопросы, цифры, интригу)"
            )

        # --- 5. Uniqueness (по эвристикам) ---
        # Проверка на копипасту: повторяющиеся фразы
        words = content.lower().split()
        trigrams = [f"{words[i]} {words[i+1]} {words[i+2]}" for i in range(len(words) - 3)]
        unique_trigrams = len(set(trigrams))
        total_trigrams = len(trigrams) if trigrams else 1
        uniqueness_ratio = unique_trigrams / total_trigrams
        uniqueness_score = min(10.0, uniqueness_ratio * 12.0)
        details["uniqueness_ratio"] = round(uniqueness_ratio, 2)
        details["uniqueness_score"] = round(uniqueness_score, 1)
        if uniqueness_score < 5:
            suggestions.append("Текст кажется шаблонным — добавь уникальных формулировок")

        # --- 6. Length Optimality ---
        word_count = len(words)
        if checklist.get("target_duration_sec"):
            # Для shorts: 150 слов/мин
            optimal = (checklist["target_duration_sec"] / 60) * checklist.get("words_per_minute", 150)
            length_score = 10.0 - abs(word_count - optimal) / optimal * 10.0
        elif checklist.get("max_length"):
            optimal = (checklist.get("min_length", 100) + checklist["max_length"]) / 2
            length_score = 10.0 - abs(word_count - optimal) / optimal * 5.0
        else:
            length_score = 7.0  # default
        length_score = max(0.0, min(10.0, length_score))
        details["word_count"] = word_count
        details["length_score"] = round(length_score, 1)

        # --- Final Score ---
        total_score = (
            hook_score * self.WEIGHTS["hook_strength"]
            + readability_score * self.WEIGHTS["readability"]
            + cta_score * self.WEIGHTS["cta_strength"]
            + emotional_score * self.WEIGHTS["emotional_triggers"]
            + uniqueness_score * self.WEIGHTS["uniqueness"]
            + length_score * self.WEIGHTS["length_optimality"]
        )
        final_score = total_score * 10  # convert 0-10 to 0-100

        details["component_scores"] = {
            "hook_strength": round(hook_score, 1),
            "readability": round(readability_score, 1),
            "cta_strength": round(cta_score, 1),
            "emotional_triggers": round(emotional_score, 1),
            "uniqueness": round(uniqueness_score, 1),
            "length_optimality": round(length_score, 1),
        }

        min_engagement = checklist.get("min_engagement_score", 5.0)
        passed = (total_score >= min_engagement)

        score = max(0.0, min(100.0, final_score))
        message = f"Engagement: {total_score:.1f}/10 (min {min_engagement})"

        return CheckResult(
            name=self.name,
            passed=passed,
            score=score,
            message=message,
            details=details,
            suggestions=suggestions,
            duration_ms=(time.monotonic() - start) * 1000,
        )


class _LLMReview:
    """LLM-эксперт: финальная оценка контента."""

    name = "LLMReview"

    SYSTEM_PROMPT = (
        "Ты — редактор с 10-летним опытом и эксперт по контент-маркетингу. "
        "Твоя задача — объективно оценить контент по критериям. "
        "Будь строгим, но справедливым. Отвечай ТОЛЬКО в формате JSON."
    )

    REVIEW_TEMPLATE = """Ты — редактор с 10-летним опытом. Проверь этот {content_type}:

---
{content}
---

Оцени по каждому критерию от 1 до 10:
1. hook — цепляет ли начало, есть ли сильный хук
2. value — информационная ценность (факты, инсайты, польза)
3. structure — структура и читаемость
4. cta — качество призыва к действию
5. branding — соответствие стилю Данила Лысенко (разговорный, экспертный, без воды, без корпоративщины)
6. engagement — потенциал вовлечённости (лайки, комменты, репосты)

Если любая оценка < 6 — напиши конкретно что исправить.

Ответ ТОЛЬКО в формате JSON:
{{
  "scores": {{
    "hook": 0,
    "value": 0,
    "structure": 0,
    "cta": 0,
    "branding": 0,
    "engagement": 0
  }},
  "verdict": "PASS или FAIL",
  "fixes": ["конкретное исправление 1", "исправление 2"],
  "summary": "краткое заключение 1-2 предложения"
}}"""

    def __init__(
        self,
        llm_router: Optional[Any] = None,
        timeout: float = 30.0,
    ) -> None:
        self.llm_router = llm_router
        self.timeout = timeout

    async def run(self, content: str, checklist: Dict[str, Any]) -> CheckResult:
        start = time.monotonic()
        details: Dict[str, Any] = {}
        suggestions: List[str] = []

        # Если LLM Router не доступен — возвращаем placeholder
        if self.llm_router is None:
            return CheckResult(
                name=self.name,
                passed=True,
                score=70.0,
                message="LLM Review: LLM Router не настроен, пропускаю",
                details={"skipped": True, "reason": "llm_router is None"},
                suggestions=["Настрой LLM Router для полной проверки"],
                duration_ms=(time.monotonic() - start) * 1000,
            )

        # Формируем промпт
        content_type = checklist.get("_content_type", "content")
        prompt = self.REVIEW_TEMPLATE.format(
            content_type=content_type,
            content=content[:4000],  # обрезаем для контекста
        )

        try:
            # Вызываем LLM с таймаутом
            response = await asyncio.wait_for(
                self.llm_router.complete(prompt),
                timeout=self.timeout,
            )

            # Парсим JSON из ответа
            llm_result = self._parse_llm_response(response)
            details["llm_raw_response"] = response[:500]
            details.update(llm_result)

            scores = llm_result.get("scores", {})
            verdict = llm_result.get("verdict", "PASS")
            fixes = llm_result.get("fixes", [])

            # Считаем средний скор
            if scores and all(isinstance(v, (int, float)) for v in scores.values()):
                avg_score = sum(scores.values()) / len(scores)
                score = avg_score * 10  # 0-10 → 0-100
            else:
                avg_score = 5.0
                score = 50.0

            passed = (verdict.upper() == "PASS")
            suggestions.extend(fixes)

            details["avg_llm_score"] = round(avg_score, 1)

        except asyncio.TimeoutError:
            logger.warning("LLM Review: timeout после %.0f сек", self.timeout)
            score = 60.0
            passed = True  # мягкая политика при таймауте
            suggestions.append("LLM Review: таймаут — проверь вручную")
            details["error"] = "timeout"

        except Exception as exc:
            logger.error("LLM Review: ошибка: %s", exc)
            score = 50.0
            passed = False
            suggestions.append(f"LLM Review: ошибка — {str(exc)[:100]}")
            details["error"] = str(exc)

        score = max(0.0, min(100.0, score))
        message = (
            f"LLM verdict: {details.get('verdict', 'N/A')}, "
            f"avg: {details.get('avg_llm_score', 'N/A')}/10"
        )

        return CheckResult(
            name=self.name,
            passed=passed,
            score=score,
            message=message,
            details=details,
            suggestions=suggestions,
            duration_ms=(time.monotonic() - start) * 1000,
        )

    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Извлечь JSON из ответа LLM."""
        # Пытаемся найти JSON в ответе
        json_match = re.search(r"\{.*\}", response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        # Fallback: парсим текстово
        return self._fallback_parse(response)

    def _fallback_parse(self, response: str) -> Dict[str, Any]:
        """Ручной парсинг если JSON не удался."""
        result: Dict[str, Any] = {
            "scores": {},
            "verdict": "UNKNOWN",
            "fixes": [],
            "summary": response[:200],
        }

        # Ищем числа рядом с ключевыми словами
        for key in ["hook", "value", "structure", "cta", "branding", "engagement"]:
            patterns = [
                rf"{key}[:\s]+(\d+)",
                rf"{key}.*?(\d+)[\/\\]10",
                rf"{key}.*?=\s*(\d+)",
            ]
            for pat in patterns:
                match = re.search(pat, response, re.IGNORECASE)
                if match:
                    try:
                        result["scores"][key] = int(match.group(1))
                        break
                    except ValueError:
                        pass

        # Ищем вердикт
        if "FAIL" in response.upper():
            result["verdict"] = "FAIL"
        elif "PASS" in response.upper():
            result["verdict"] = "PASS"

        return result


# ---------------------------------------------------------------------------
# QualityCheckPipeline
# ---------------------------------------------------------------------------


class QualityCheckPipeline:
    """Полный pipeline проверки контента.

    Запускает все проверки последовательно и собирает единый отчёт.

    Usage:
        pipeline = QualityCheckPipeline(llm_router=router)
        report = await pipeline.check(content, content_type="telegram_post")
    """

    def __init__(
        self,
        llm_router: Optional[Any] = None,
        tov: Optional[ToVProfile] = None,
        thresholds_path: Optional[str] = None,
    ) -> None:
        self.llm_router = llm_router
        self.tov = tov or ToVProfile()

        # Загружаем пороговые значения
        if thresholds_path is None:
            thresholds_path = os.path.join(
                _get_project_root(), "config", "quality_thresholds.json"
            )
        self.thresholds = _load_thresholds(thresholds_path)
        self.global_thresholds = self.thresholds.get("global", {})

        # Собираем чек-листы (мердж дефолтов + JSON)
        self.checklists: Dict[str, Dict[str, Any]] = {}
        for ctype, default in DEFAULT_CHECKLISTS.items():
            json_config = self.thresholds.get(ctype, {})
            merged = {**default, **json_config}
            self.checklists[ctype] = merged

        # Инициализируем проверки
        self._init_checks()

    def _init_checks(self) -> None:
        """Создать экземпляры всех проверок."""
        self.checks: List[Any] = [
            _BasicCheck(),
            _HookCheck(),
            _CtaCheck(),
            _ToxicityCheck(tov=self.tov),
            _BrandingCheck(tov=self.tov),
            _StructureCheck(),
            _EngagementPredictor(),
        ]

        # LLM Review добавляется только если есть router
        self.llm_review_check = _LLMReview(
            llm_router=self.llm_router,
            timeout=self.global_thresholds.get("llm_timeout_sec", 30.0),
        )

    def _get_checklist(self, content_type: str) -> Dict[str, Any]:
        """Получить чек-лист для типа контента."""
        checklist = self.checklists.get(content_type, self.checklists.get("telegram_post", {}))
        checklist = dict(checklist)  # копия
        checklist["_content_type"] = content_type
        # Мержим глобальные спам-паттерны
        checklist.setdefault(
            "spam_link_patterns",
            self.global_thresholds.get("spam_link_patterns", []),
        )
        return checklist

    async def check(self, content: str, content_type: str = "telegram_post") -> QualityReport:
        """Запустить полный pipeline проверки.

        Args:
            content: Текст контента для проверки.
            content_type: Тип контента (telegram_post, shorts_script, blog_post, video_description).

        Returns:
            QualityReport с полными результатами.
        """
        pipeline_start = time.monotonic()
        logger.info("QualityCheckPipeline: начало проверки %s (тип: %s)", content_type, content_type)

        if not content or not content.strip():
            logger.warning("Пустой контент")
            return self._empty_report(content_type)

        checklist = self._get_checklist(content_type)
        results: List[CheckResult] = []
        all_suggestions: List[str] = []

        # --- Шаги 1-7: базовые проверки ---
        for check in self.checks:
            try:
                result = await check.run(content, checklist)
                results.append(result)
                all_suggestions.extend(result.suggestions)
                logger.debug("  %s: %.0f/100 %s", result.name, result.score, "PASS" if result.passed else "FAIL")
            except Exception as exc:
                logger.error("Ошибка в проверке %s: %s", check.name, exc)
                results.append(CheckResult(
                    name=check.name,
                    passed=False,
                    score=0.0,
                    message=f"Ошибка проверки: {exc}",
                    details={"error": str(exc)},
                    suggestions=["Проверьте конфигурацию quality_control"],
                ))

        # --- Шаг 8: LLM Review ---
        try:
            llm_result = await self.llm_review_check.run(content, checklist)
            results.append(llm_result)
            all_suggestions.extend(llm_result.suggestions)
        except Exception as exc:
            logger.error("Ошибка LLM Review: %s", exc)
            results.append(CheckResult(
                name="LLMReview",
                passed=False,
                score=0.0,
                message=f"LLM Review ошибка: {exc}",
                details={"error": str(exc)},
            ))

        # --- Сборка отчёта ---
        total_duration_ms = (time.monotonic() - pipeline_start) * 1000

        # Общий score — среднее всех проверок
        scores = [r.score for r in results]
        quality_score = int(round(statistics.mean(scores))) if scores else 0

        # Флаги
        pass_threshold = self.global_thresholds.get("pass_threshold", 60)
        auto_approve_threshold = self.global_thresholds.get("auto_approve_threshold", 85)

        all_passed = all(r.passed for r in results)
        passed = quality_score >= pass_threshold and all_passed
        auto_approved = quality_score >= auto_approve_threshold and all_passed

        # LLM review данные
        llm_review_data = None
        for r in results:
            if r.name == "LLMReview" and r.details:
                llm_review_data = {
                    "scores": r.details.get("scores", {}),
                    "verdict": r.details.get("verdict", "UNKNOWN"),
                    "fixes": r.details.get("fixes", []),
                    "summary": r.details.get("summary", ""),
                }
                break

        # Дедупликация suggestions
        unique_suggestions = list(dict.fromkeys(all_suggestions))

        report = QualityReport(
            quality_score=quality_score,
            passed=passed,
            auto_approved=auto_approved,
            content_type=content_type,
            checks=results,
            suggestions=unique_suggestions,
            metadata={
                "pipeline_duration_ms": round(total_duration_ms, 1),
                "checks_count": len(results),
                "pass_threshold": pass_threshold,
                "auto_approve_threshold": auto_approve_threshold,
                "content_length": len(content),
                "word_count": len(content.split()),
            },
            llm_review=llm_review_data,
        )

        logger.info(
            "QualityCheckPipeline: завершено. Score: %d, passed: %s, auto_approved: %s",
            report.quality_score, report.passed, report.auto_approved,
        )
        return report

    def _empty_report(self, content_type: str) -> QualityReport:
        """Отчёт для пустого контента."""
        return QualityReport(
            quality_score=0,
            passed=False,
            auto_approved=False,
            content_type=content_type,
            checks=[],
            suggestions=["Контент пустой — нечего проверять"],
            metadata={"error": "empty_content"},
        )


# ---------------------------------------------------------------------------
# ContentQualityChecker — основной класс (facade)
# ---------------------------------------------------------------------------


class ContentQualityChecker:
    """Фасад для системы контроля качества контента.

    Проверяет контент ПЕРЕД публикацией:
    - Базовые: длина, формат, наличие хука, CTA
    - Языковые: орфография, грамматика, токсичность
    - Брендинг: соответствие ToV Данила
    - Юридические: нет запрещённого контента
    - Энгейджмент: прогноз вовлечённости
    - LLM Review: экспертная оценка

    Возвращает:
        quality_score: 0-100
        passed: True/False (прошёл ли минимальный порог)
        report: подробный отчёт с замечаниями
        auto_approved: можно ли публиковать без человека

    Usage:
        checker = ContentQualityChecker(llm_router=router)
        report = await checker.check(content, content_type="telegram_post")

        if report.auto_approved:
            await publish(content)
        elif report.passed:
            # Хороший контент, но нужен взгляд человека
            await notify_human(content, report)
        else:
            # Переписать
            rewritten = await rewrite(content, report.suggestions)
            report2 = await checker.check(rewritten)
    """

    def __init__(
        self,
        llm_router: Optional[Any] = None,
        tov: Optional[ToVProfile] = None,
        thresholds_path: Optional[str] = None,
    ) -> None:
        self.pipeline = QualityCheckPipeline(
            llm_router=llm_router,
            tov=tov,
            thresholds_path=thresholds_path,
        )
        logger.info("ContentQualityChecker инициализирован")

    async def check(self, content: str, content_type: str = "telegram_post") -> QualityReport:
        """Проверить контент.

        Args:
            content: Текст контента.
            content_type: Тип контента (telegram_post, shorts_script, blog_post, video_description).

        Returns:
            QualityReport с полными результатами проверки.
        """
        return await self.pipeline.check(content, content_type)

    async def quick_check(self, content: str) -> Dict[str, Any]:
        """Быстрая проверка без LLM Review.

        Проверяет только базовые параметры — быстро, без вызова LLM.

        Returns:
            Dict с ключевыми метриками.
        """
        start = time.monotonic()
        word_count = len(content.split())
        char_count = len(content)

        # Проверка через ToV (быстрая, без LLM)
        tov = self.pipeline.tov
        toxicity = tov.check_toxicity(content)
        taboo = tov.check_taboo(content)

        # Проверка хука
        first_sentence = content[:200].lower()
        has_hook = any(re.search(p, first_sentence) for p in HOOK_PATTERNS)

        # Проверка CTA
        has_cta = any(re.search(p, content.lower()) for p in CTA_PATTERNS)

        result = {
            "word_count": word_count,
            "char_count": char_count,
            "has_hook": has_hook,
            "has_cta": has_cta,
            "has_toxicity": toxicity["has_hard_toxicity"],
            "caps_ratio": toxicity["caps_ratio"],
            "taboo_count": len(taboo),
            "is_valid": (
                word_count >= 10
                and not toxicity["has_hard_toxicity"]
                and len(taboo) == 0
            ),
            "duration_ms": round((time.monotonic() - start) * 1000, 1),
        }
        return result

    def get_checklist(self, content_type: str) -> Dict[str, Any]:
        """Получить чек-лист для типа контента."""
        return self.pipeline._get_checklist(content_type)

    def supported_content_types(self) -> List[str]:
        """Список поддерживаемых типов контента."""
        return list(self.pipeline.checklists.keys())
