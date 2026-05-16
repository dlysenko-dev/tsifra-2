"""
Nocnaja ucoba agenta  skachivanije i razbor viralnyh rolikov.
"""
import sys
sys.path.insert(0, ".")

import asyncio
from core.self_learning_video import SelfLearningVideo


async def main():
    # Bez LLM (hevristika), no s yt-dlp
    learner = SelfLearningVideo(
        output_dir="./learning",
        llm_router=None,  # Mozhno podkljucit LLMRouter
    )

    # Nocnaja sessija obucenija
    stats = await learner.night_study_session(sessions=3)

    # Sozdanije scenarija na osnove znanij
    print("\n" + "=" * 60)
    script = await learner.create_from_learning("AI avtomatizacija")
    print("=" * 60)

    print(f"\n[DB] Baza znanij: {learner.db_file}")
    print(f"[VID] Video: {learner.videos_dir}")
    print(f"[SFX] SFX: {learner.sfx_dir}")

    return stats


if __name__ == "__main__":
    result = asyncio.run(main())
    print(f"\n[OK] Gotovo. Razobrano: {result['analyzed']}/{result['downloaded']}")
