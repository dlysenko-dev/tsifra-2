"""
Analyze All — razbiraet TOLKO roliki masterov i etalonov.
Ne trogajet sluchajnyje tutorialy.
"""
import sys
sys.path.insert(0, ".")

import asyncio
from pathlib import Path

from core.self_learning_video import SelfLearningVideo


async def main():
    learner = SelfLearningVideo(
        output_dir="./learning",
        llm_router=None,  # Mozhno podkljuchit LLM dlja glubokogo analiza
    )

    # Sobiraem vse celjevye video
    targets = []

    # Mastera
    masters_dir = Path("learning/masters")
    if masters_dir.exists():
        for master_dir in masters_dir.iterdir():
            if master_dir.is_dir():
                for video in master_dir.glob("*.mp4"):
                    targets.append((video, master_dir.name))

    # Etalony
    etalons_dir = Path("learning/etalons")
    if etalons_dir.exists():
        for video in etalons_dir.glob("*.mp4"):
            targets.append((video, "ETALON"))

    print(f"[INFO] Najdeno {len(targets)} rolikov dlja analiza")
    if not targets:
        print("[WARN] Net rolikov. Snachala zapushi: python fetch_masters.py")
        return

    # Analiziruem kazhdyj
    print("\n" + "=" * 60)
    print("[ANALYZE] Razbor rolikov masterov")
    print("=" * 60)

    analyzed = 0
    for video_path, source in targets:
        print(f"\n[{source}] {video_path.name.encode("ascii", "ignore").decode()[:50]}")
        analysis = await learner.analyze_video(str(video_path))
        if analysis:
            analyzed += 1
            print(f"   Score: {analysis.score}")
            print(f"   Style: {analysis.style}")
            print(f"   Tempo: {analysis.tempo}")
            print(f"   Hook: {analysis.hook[:60] if analysis.hook else 'N/A'}")
            print(f"   CTA: {analysis.cta[:60] if analysis.cta else 'N/A'}")
            print(f"   Structure: {' -> '.join(s.get('type', '?') for s in analysis.structure[:4])}")

    # Itogi
    print("\n" + "=" * 60)
    print("[STAT] ITOGI ANALIZA:")
    print(f"   Razobrano: {analyzed}/{len(targets)}")
    print(f"   Vsego v baze: {learner.db.total_videos_analyzed}")
    print(f"   Patternov: {sum(len(v) for v in learner.db.patterns.values())}")
    print(f"   Luchshih hukov: {len(learner.db.best_hooks)}")
    print(f"   Luchshih CTA: {len(learner.db.best_ctas)}")
    print(f"   Cvetovyh shem: {len(learner.db.color_schemes)}")

    # Pokazhem top-5 hukov i CTA
    if learner.db.best_hooks:
        print("\n[TOP] HUKI:")
        for i, h in enumerate(learner.db.best_hooks[:5], 1):
            print(f"   {i}. {h[:70]}")

    if learner.db.best_ctas:
        print("\n[TOP] CTA:")
        for i, c in enumerate(learner.db.best_ctas[:5], 1):
            print(f"   {i}. {c[:70]}")

    if learner.db.patterns:
        print("\n[TOP] PATTERNS:")
        for style, patterns in learner.db.patterns.items():
            print(f"   {style}: {patterns[:3]}")

    # Sozdanije scenarija na osnove vsego
    print("\n" + "=" * 60)
    print("[CREATE] Scenarij na osnove znanij masterov")
    print("=" * 60)
    script = await learner.create_from_learning("AI automation")
    print(f"   Hook: {script['hook']}")
    print(f"   Structure: {script['structure']}")
    print(f"   CTA: {script['cta']}")
    print(f"   Colors: {script['colors']}")
    print(f"   SFX: {script['sfx']}")


if __name__ == "__main__":
    asyncio.run(main())
