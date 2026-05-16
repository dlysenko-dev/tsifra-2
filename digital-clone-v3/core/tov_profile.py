"""
tov_profile.py — Tone of Voice профиль Данила Лысенко.

Проверяет соответствие текста фирменному стилю: разговорный,
экспертный, без корпоративной воды и канцеляризмов.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Допустимые "мягкие" междометия (Данил разрешает)
_ALLOWED_SOFT_SWEARS: List[str] = ["блин", "чёрт", "черт", "ого", "огоо", "ух"]

# Полные запреты (строгий мат, оскорбления)
_HARD_TOXIC_PATTERNS: List[str] = [
    r"\b(ху[йеяиё]|пизд[аеыой]|еба[лтьн]|бля[дть]|\bсука\b|\bмудак\b|\bпидор\b|\bгандон\b)",
    r"\b(д[еи]бил|идиот|тупой\s+(?:чел|мужик|парень)|тварь)\b",
]

# Разрешённые для Данила эмфатичные капс-паттерны (белый список)
_ALLOWED_CAPS_PATTERNS: List[str] = [
    r"\bOK\b",
    r"\bVS\b",
    r"\bAI\b",
    r"\bML\b",
    r"\bAPI\b",
    r"\bGPT\b",
    r"\bLLM\b",
    r"\bMCP\b",
    r"\bJSON\b",
    r"\bHTTP\b",
    r"\bURL\b",
    r"\bPDF\b",
    r"\bS3\b",
    r"\bCSS\b",
    r"\bHTML\b",
    r"\bSQL\b",
    r"\bNoSQL\b",
    r"\bREST\b",
    r"\bSOAP\b",
    r"\bSDK\b",
    r"\bCLI\b",
    r"\bIDE\b",
    r"\bCI/CD\b",
    r"\bCDN\b",
    r"\bDNS\b",
    r"\bRAM\b",
    r"\bCPU\b",
    r"\bGPU\b",
    r"\bTPU\b",
    r"\bI/O\b",
    r"\bUI\b",
    r"\bUX\b",
    r"\bSaaS\b",
    r"\bPaaS\b",
    r"\bIaaS\b",
    r"\bFOMO\b",
    r"\bTL;DR\b",
    r"\bFAQ\b",
    r"\bSEO\b",
    r"\bCTR\b",
    r"\bROI\b",
    r"\bKPI\b",
    r"\bOKR\b",
    r"\bPM\b",
    r"\bPO\b",
    r"\bCEO\b",
    r"\bCTO\b",
    r"\bCPO\b",
    r"\bCFO\b",
    r"\bCOO\b",
    r"\bCIO\b",
    r"\bCMO\b",
    r"\bCDO\b",
    r"\bCHRO\b",
    r"\bCISO\b",
    r"\bVP\b",
    r"\bSVP\b",
    r"\bEVP\b",
    r"\bGM\b",
    r"\bVP\b",
    r"\bAWS\b",
    r"\bGCP\b",
    r"\bAzure\b",
    r"\bIBM\b",
    r"\bHP\b",
    r"\bDELL\b",
    r"\bSSD\b",
    r"\bHDD\b",
    r"\bUSB\b",
    r"\bHDMI\b",
    r"\bVGA\b",
    r"\bLCD\b",
    r"\bLED\b",
    r"\bOLED\b",
    r"\bQLED\b",
    r"\bPDF\b",
    r"\bJPEG\b",
    r"\bJPG\b",
    r"\bPNG\b",
    r"\bGIF\b",
    r"\bSVG\b",
    r"\bMP3\b",
    r"\bMP4\b",
    r"\bAVI\b",
    r"\bMOV\b",
    r"\bWMV\b",
    r"\bFLV\b",
    r"\bMKV\b",
    r"\bWEBM\b",
    r"\bOGG\b",
    r"\bWAV\b",
    r"\bFLAC\b",
    r"\bAAC\b",
    r"\bWMA\b",
    r"\bM4A\b",
    r"\bOGV\b",
    r"\bM3U8\b",
    r"\bHLS\b",
    r"\bDASH\b",
    r"\bRTMP\b",
    r"\bRTSP\b",
    r"\bRTP\b",
    r"\bSRT\b",
    r"\bVTT\b",
    r"\bTTML\b",
    r"\bWebVTT\b",
    r"\bSSA\b",
    r"\bASS\b",
    r"\bSMI\b",
    r"\bPSB\b",
    r"\bSUB\b",
    r"\bIDX\b",
]


# ---------------------------------------------------------------------------
# ToV Profile
# ---------------------------------------------------------------------------

@dataclass
class ToVProfile:
    """Tone of Voice Данила Лысенко (из стрима ИИздец).

    Стиль: разговорный, экспертный, "как с другом за кружкой чая".
    Никакой корпоративной воды, канцеляризмов и пафоса.
    """

    name: str = "Данил Лысенко"
    style: str = "разговорный, как с другом"
    description: str = (
        "Экспертный разговорный стиль. Короткие предложения. "
        "Прямое обращение к читателю. Ирония и самоирония допустимы. "
        "Никакого 'уважаемого клиента' и 'в соответствии с'."
    )

    # --- Запретные паттерны (корпоративщина, канцеляризмы) ---------------
    taboo_words: List[str] = field(default_factory=lambda: [
        # Корпоративная чушь
        "уважаемый клиент", "уважаемый пользователь",
        "в соответствии с", "в связи с", "в рамках",
        "на основании", "в целях", "в порядке",
        "просим сообщить", "просим предоставить",
        "данное предложение", "настоящим сообщаем",
        "быть может", "возможно", "как известно",
        "как правило", "как следствие",
        "обращаем ваше внимание", "просим обратить внимание",
        "в случае если", "при наличии", "при отсутствии",
        "в соответствии с вышеизложенным",
        "во исполнение", "в целях реализации",
        "на постоянной основе", "в кратчайшие сроки",
        "приносим извинения", "просим извинения",
        "ждем вашего ответа", "ждем обратной связи",
        "с уважением", "с благодарностью",
        "высококвалифицированные специалисты",
        "передовые технологии", "инновационные решения",
        "комплексный подход", "уникальное предложение",
        "ограниченное предложение", "только сегодня",
        "горячее предложение", "спешите",
        "дорогие друзья", "уважаемые подписчики",
        "наши дорогие", "в данный момент",
        "в текущий момент", "в настоящее время",
        "с целью оптимизации", "в целях повышения",
        "в рамках реализации", "в рамках проекта",
        "благодарим за понимание", "надеемся на сотрудничество",
        "оставьте заявку", "заполните форму",
        "наши менеджеры свяжутся",
        # Излишне официальные
        "здравствуйте, коллеги", "уважаемые коллеги",
        "позвольте представить", "позвольте сообщить",
        "имею честь сообщить", "доводим до вашего сведения",
        "по состоянию на", "в установленном порядке",
        "в сроки не позднее", "в установленные сроки",
        # Водянистые фразы
        "хотелось бы отметить", "следует отметить",
        "необходимо отметить", "важно отметить",
        "следует подчеркнуть", "хотелось бы подчеркнуть",
        "стоит отметить", "нельзя не отметить",
        "как известно каждому", "общеизвестно",
        "не секрет, что", "все мы знаем",
        "как говорится", "как известно",
        # Пафос
        "невероятно", "феноменально", "беспрецедентно",
        "революционно", "прорывной", "масштабный",
        "масштабнейший", "грандиозный",
        # Бессмысленные модные словечки
        "синергия", "парадигма", "вектор",
        "платформа", "экосистема", "数字化转型",
    ])

    # --- Характерные обороты Данила (плюс при проверке) ----------------
    signature_phrases: List[str] = field(default_factory=lambda: [
        "короче", "типа", "вот", "ну", "блин",
        "прикинь", "представляешь", "в общем",
        "короче говоря", "ну типа", "короч",
        "слушай", "смотри", "вообще", "если честно",
        "честно говоря", "честно скажу",
        "так что", "поэтому", "в итоге",
        "штука в том, что", "фишка в том, что",
        "суть в том, что", "дело в том, что",
    ])

    # --- Пороговые значения ---------------------------------------------
    max_caps_ratio: float = 0.05           # не более 5% капсом
    min_signature_phrases: int = 0         # 0 = не обязательны
    max_avg_sentence_length: int = 20      # средняя длина предложения
    min_avg_sentence_length: int = 4       # слишком короткие = телеграфный стиль
    max_taboo_violations: int = 0          # табу = жёсткий запрет
    preferred_person: str = "second"       # предпочтительное лицо: 2-е (ты)

    # --- Качественные характеристики ------------------------------------
    voice_dimensions: Dict[str, float] = field(default_factory=lambda: {
        "formality": 0.15,         # 0=неформальный, 1=официальный
        "expertise": 0.85,         # 0=попса, 1=глубокий эксперт
        "warmth": 0.80,            # 0=холодный, 1=теплый
        "humor": 0.40,             # 0=серьезный, 1=шутник
        "directness": 0.85,        # 0=обтекаемый, 1=прямой
        "energy": 0.75,            # 0=спокойный, 1=энергичный
    })

    # ------------------------------------------------------------------
    # Methods
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Сериализовать профиль в словарь."""
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """Сериализовать профиль в JSON-строку."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    # ---- Проверки ------------------------------------------------------

    def check_caps_ratio(self, text: str) -> Tuple[float, List[str]]:
        """Доля символов в ВЕРХНЕМ регистре (без учета аббревиатур)."""
        # Убираем разрешённые аббревиатуры
        cleaned = text
        for pattern in _ALLOWED_CAPS_PATTERNS:
            cleaned = re.sub(pattern, "", cleaned)

        letters = re.findall(r"[A-Za-zА-Яа-яЁё]", cleaned)
        if not letters:
            return 0.0, []

        caps = [ch for ch in letters if ch.isupper()]
        ratio = len(caps) / len(letters)

        violations: List[str] = []
        # Ищем подозрительные капс-последовательности (3+ буквы)
        for match in re.finditer(r"[А-ЯЁ]{3,}", text):
            word = match.group()
            if not any(re.match(p, word) for p in _ALLOWED_CAPS_PATTERNS):
                violations.append(word)
        for match in re.finditer(r"[A-Z]{3,}", text):
            word = match.group()
            if not any(re.match(p, word) for p in _ALLOWED_CAPS_PATTERNS):
                violations.append(word)

        return ratio, violations

    def check_taboo(self, text: str) -> List[Dict[str, Any]]:
        """Найти канцеляризмы и корпоративщину."""
        lower = text.lower()
        violations: List[Dict[str, Any]] = []
        for taboo in self.taboo_words:
            if taboo.lower() in lower:
                # найти позицию
                start = lower.index(taboo.lower())
                end = start + len(taboo)
                context = text[max(0, start - 20):min(len(text), end + 20)]
                violations.append({
                    "type": "taboo_phrase",
                    "phrase": taboo,
                    "context": context,
                    "severity": "high",
                    "suggestion": f"Замени на разговорный аналог",
                })
        return violations

    def check_signature_phrases(self, text: str) -> Tuple[int, List[str]]:
        """Подсчитать характерные обороты Данила."""
        lower = text.lower()
        found: List[str] = []
        for phrase in self.signature_phrases:
            if phrase.lower() in lower:
                found.append(phrase)
        return len(found), found

    def check_toxicity(self, text: str) -> Dict[str, Any]:
        """Проверить на токсичность (мат, оскорбления, капс-спам)."""
        result: Dict[str, Any] = {
            "has_hard_toxicity": False,
            "has_spam_patterns": False,
            "caps_ratio": 0.0,
            "caps_violations": [],
            "toxic_matches": [],
            "soft_swear_count": 0,
            "soft_swear_matches": [],
            "is_clean": True,
        }

        # 1. Жёсткий мат / оскорбления
        for pattern in _HARD_TOXIC_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                result["has_hard_toxicity"] = True
                result["toxic_matches"].extend(matches)

        # 2. Разрешённые "мягкие" слова
        for word in _ALLOWED_SOFT_SWEARS:
            matches = re.findall(rf"\b{word}\b", text, re.IGNORECASE)
            result["soft_swear_count"] += len(matches)
            result["soft_swear_matches"].extend(matches)

        # 3. Капс
        ratio, violations = self.check_caps_ratio(text)
        result["caps_ratio"] = ratio
        result["caps_violations"] = violations
        if ratio > self.max_caps_ratio:
            result["is_clean"] = False

        # 4. Итог
        if result["has_hard_toxicity"]:
            result["is_clean"] = False

        return result

    def check_sentence_length(self, text: str) -> Dict[str, Any]:
        """Средняя длина предложений."""
        sentences = re.split(r"[.!?\n]+", text)
        sentences = [s.strip() for s in sentences if s.strip()]
        if not sentences:
            return {"avg_length": 0, "median_length": 0, "max_length": 0, "count": 0}

        lengths = [len(s.split()) for s in sentences]
        import statistics
        return {
            "avg_length": round(statistics.mean(lengths), 1),
            "median_length": round(statistics.median(lengths), 1),
            "max_length": max(lengths),
            "count": len(lengths),
        }

    def check_person(self, text: str) -> Dict[str, Any]:
        """Проверить лицо обращения (предпочтительно 2-е — 'ты')."""
        # 1-е лицо
        first_person = len(re.findall(r"\b(я|мне|меня|мой|моя|моё|мои)\b", text.lower()))
        # 2-е лицо
        second_person = len(re.findall(r"\b(ты|тебе|тебя|твой|твоя|твоё|твои|вы|вам|вас|ваш|ваша|ваше|ваши)\b", text.lower()))
        # 3-е лицо / безличное
        third_person = len(re.findall(r"\b(он|она|оно|они|его|её|их|мы|нас|нам)\b", text.lower()))

        total = first_person + second_person + third_person
        if total == 0:
            return {
                "dominant": "neutral",
                "first_ratio": 0,
                "second_ratio": 0,
                "third_ratio": 0,
            }

        return {
            "dominant": "second" if second_person >= first_person and second_person >= third_person
            else ("first" if first_person >= third_person else "third"),
            "first_ratio": round(first_person / total, 2),
            "second_ratio": round(second_person / total, 2),
            "third_ratio": round(third_person / total, 2),
        }

    def check_text(self, text: str) -> Dict[str, Any]:
        """Полная проверка текста на соответствие ToV.

        Returns:
            Dict с полным отчётом по ToV.
        """
        taboo_violations = self.check_taboo(text)
        sig_count, sig_found = self.check_signature_phrases(text)
        toxicity = self.check_toxicity(text)
        sentence_stats = self.check_sentence_length(text)
        person = self.check_person(text)

        # Скоринг
        score = 100.0

        # Минус за табу
        for v in taboo_violations:
            if v["severity"] == "high":
                score -= 15.0
            else:
                score -= 5.0

        # Минус за капс
        if toxicity["caps_ratio"] > self.max_caps_ratio:
            score -= 10.0

        # Минус за жёсткую токсичность
        if toxicity["has_hard_toxicity"]:
            score -= 30.0

        # Минус за слишком длинные предложения
        if sentence_stats["avg_length"] > self.max_avg_sentence_length:
            score -= 5.0
        if sentence_stats["max_length"] > 40:
            score -= 5.0

        # Бонус за подписные фразы (но не штраф за отсутствие)
        score += min(sig_count * 2, 10)

        # Бонус за 2-е лицо
        if person["dominant"] == "second":
            score += 5.0

        score = max(0.0, min(100.0, score))

        passed = (
            len(taboo_violations) <= self.max_taboo_violations
            and not toxicity["has_hard_toxicity"]
            and toxicity["caps_ratio"] <= self.max_caps_ratio
        )

        return {
            "score": round(score, 1),
            "passed": passed,
            "taboo_violations": taboo_violations,
            "signature_phrases_found": sig_found,
            "signature_phrase_count": sig_count,
            "toxicity": toxicity,
            "sentence_stats": sentence_stats,
            "person": person,
            "suggestions": self._generate_suggestions(
                taboo_violations, toxicity, sentence_stats, person
            ),
        }

    # ---- Helpers -------------------------------------------------------

    def _generate_suggestions(
        self,
        taboo: List[Dict],
        toxicity: Dict[str, Any],
        sentence_stats: Dict[str, Any],
        person: Dict[str, Any],
    ) -> List[str]:
        """Сформировать рекомендации по улучшению текста."""
        suggestions: List[str] = []

        if taboo:
            phrases = [v["phrase"] for v in taboo]
            suggestions.append(
                f"Убери корпоративщину: {', '.join(phrases[:5])}"
                + ("..." if len(phrases) > 5 else "")
            )

        if toxicity["has_hard_toxicity"]:
            suggestions.append("Убери грубый мат и оскорбления")

        if toxicity["caps_ratio"] > self.max_caps_ratio:
            suggestions.append(
                f"Слишком много КАПСА ({toxicity['caps_ratio']:.1%}). "
                f"Снизь до {self.max_caps_ratio:.0%}"
            )

        if sentence_stats["avg_length"] > self.max_avg_sentence_length:
            suggestions.append(
                f"Средняя длина предложения {sentence_stats['avg_length']} слов — "
                f"сократи до {self.max_avg_sentence_length}"
            )

        if sentence_stats["max_length"] > 40:
            suggestions.append(
                f"Самое длинное предложение — {sentence_stats['max_length']} слов. "
                f"Разбей на два"
            )

        if person["dominant"] != "second":
            suggestions.append(
                f"Обращайся к читателю напрямую ('ты'). "
                f"Сейчас доминирует {person['dominant']} лицо"
            )

        return suggestions
