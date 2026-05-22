"""
Business Models — готовые модели монетизации Digital Clone v3.

10+ бизнес-моделей с оценками потенциала дохода.
Модуль используется main.py для отображения доступных направлений.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

_BUSINESS_MODELS: List[Dict[str, Any]] = [
    {
        "id": "ai_agency",
        "name": "AI-агентство",
        "description": "Автоматизация бизнес-процессов для клиентов",
        "revenue_potential": "$3K-15K/мес",
        "skills_required": ["coding", "content", "dev"],
        "difficulty": "medium",
        "startup_cost": "low",
    },
    {
        "id": "content_factory",
        "name": "Контент-фабрика",
        "description": "Массовое создание контента (посты, видео, статьи)",
        "revenue_potential": "$1K-5K/мес",
        "skills_required": ["content", "video"],
        "difficulty": "low",
        "startup_cost": "minimal",
    },
    {
        "id": "saas_product",
        "name": "SaaS-продукт",
        "description": "Подписочный AI-сервис для нишевой аудитории",
        "revenue_potential": "$5K-50K/мес",
        "skills_required": ["coding", "dev", "sell"],
        "difficulty": "high",
        "startup_cost": "medium",
    },
    {
        "id": "info_products",
        "name": "Info-продукты",
        "description": "Курсы, гайды, чеклисты, шаблоны",
        "revenue_potential": "$500-3K/мес",
        "skills_required": ["content"],
        "difficulty": "low",
        "startup_cost": "minimal",
    },
    {
        "id": "freelance",
        "name": "Фриланс",
        "description": "Проектная разработка и контент на заказ",
        "revenue_potential": "$2K-10K/мес",
        "skills_required": ["coding", "content", "video"],
        "difficulty": "medium",
        "startup_cost": "minimal",
    },
    {
        "id": "affiliate",
        "name": "Аффилиат",
        "description": "Партнёрские программы AI-инструментов",
        "revenue_potential": "$200-2K/мес",
        "skills_required": ["content", "sell"],
        "difficulty": "low",
        "startup_cost": "minimal",
    },
    {
        "id": "consulting",
        "name": "Консалтинг",
        "description": "AI-консультации для бизнеса",
        "revenue_potential": "$100-500/час",
        "skills_required": ["intel", "sell"],
        "difficulty": "medium",
        "startup_cost": "low",
    },
    {
        "id": "api_access",
        "name": "API-доступ",
        "description": "Продажа API к своему Digital Clone",
        "revenue_potential": "$500-5K/мес",
        "skills_required": ["coding", "dev"],
        "difficulty": "high",
        "startup_cost": "medium",
    },
    {
        "id": "white_label",
        "name": "White-label",
        "description": "Лицензирование системы под чужим брендом",
        "revenue_potential": "$2K-20K/мес",
        "skills_required": ["coding", "dev", "sell"],
        "difficulty": "high",
        "startup_cost": "medium",
    },
    {
        "id": "auto_funnels",
        "name": "Автоматические воронки",
        "description": "Автоворонки продаж и email-цепочки",
        "revenue_potential": "$1K-10K/мес",
        "skills_required": ["sell", "content"],
        "difficulty": "medium",
        "startup_cost": "low",
    },
]

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def list_business_models() -> List[Dict[str, Any]]:
    """Список всех доступных бизнес-моделей.

    Returns:
        Список словарей с id, name, description, revenue_potential и т.д.
    """
    return _BUSINESS_MODELS.copy()


def recommend_model(skills: Optional[List[str]] = None, budget: str = "low") -> Dict[str, Any]:
    """Рекомендовать бизнес-модель на основе навыков и бюджета.

    Args:
        skills: Список навыков (coding, content, video, dev, intel, sell).
        budget: Уровень бюджета (minimal, low, medium, high).

    Returns:
        Словарь с рекомендованной моделью или fallback.
    """
    skills = skills or []
    budget = budget.lower()

    # Фильтрация по бюджету
    budget_order = {"minimal": 0, "low": 1, "medium": 2, "high": 3}
    target_level = budget_order.get(budget, 1)

    candidates = []
    for model in _BUSINESS_MODELS:
        model_level = budget_order.get(model.get("startup_cost", "low"), 1)
        if model_level <= target_level:
            # Score по совпадению skills
            model_skills = set(model.get("skills_required", []))
            user_skills = set(skills)
            match_count = len(model_skills & user_skills)
            total_required = len(model_skills)
            score = match_count / total_required if total_required else 0.0
            candidates.append((score, model))

    if not candidates:
        # Fallback: первая модель с minimal cost
        for model in _BUSINESS_MODELS:
            if model.get("startup_cost") == "minimal":
                return {"recommended": model, "score": 0.0, "reason": "fallback_minimal_cost"}
        return {"recommended": _BUSINESS_MODELS[0], "score": 0.0, "reason": "fallback_first"}

    # Сортируем по score (убывание), потом по потенциалу дохода
    candidates.sort(key=lambda x: (x[0], x[1]["revenue_potential"]), reverse=True)
    best_score, best_model = candidates[0]

    return {
        "recommended": best_model,
        "score": round(best_score, 2),
        "reason": "best_skill_match",
        "alternatives": [c[1]["name"] for c in candidates[1:3]],
    }


def get_model_by_id(model_id: str) -> Optional[Dict[str, Any]]:
    """Получить бизнес-модель по ID."""
    for model in _BUSINESS_MODELS:
        if model["id"] == model_id:
            return model.copy()
    return None
