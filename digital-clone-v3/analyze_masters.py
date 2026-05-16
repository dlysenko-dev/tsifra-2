"""
Analyze Masters — glubokij LLM-analiz 21 rolika s kanalov masterov.
"""
import asyncio
import os
import sys

sys.path.insert(0, ".")

from core.self_learning_video import SelfLearningVideo
from core.llm_router import LLMRouter


async def main():
    print("[INIT] Zagruzka LLM i learner...")
    llm = LLMRouter()
    learner = SelfLearningVideo(llm_router=llm)

    dirs_to_analyze = [
        "learning/masters/ArseniiMerzliakov",
        "learning/masters/egorlistopadov",
        "learning/masters/YoEdit0r",
        "learning/etalons",
    ]

    total_analyzed = 0

    for directory in dirs_to_analyze:
        if not os.path.exists(directory):
            print(f"[SKIP] Papka ne najdena: {directory}")
            continue

        mp4_files = [f for f in os.listdir(directory) if f.endswith(".mp4")]
        print(f"\n{'='*60}")
        print(f"[DIR] {directory}: {len(mp4_files)} rolikov")

        for i, filename in enumerate(sorted(mp4_files), 1):
            video_path = os.path.join(directory, filename)
            safe_name = filename.encode("ascii", "ignore").decode()[:50]
            print(f"\n[{i}/{len(mp4_files)}] [VID] {safe_name}...")

            try:
                analysis = await learner.analyze_video(video_path)

                if analysis:
                    print(f"  [OK] Huk: {analysis.hook[:60] if analysis.hook else 'N/A'}")
                    print(f"  [OK] Stil: {analysis.style}")
                    print(f"  [OK] Struktura: {len(analysis.structure)} scen")
                    print(f"  [OK] Tempo: {analysis.tempo}")
                    print(f"  [OK] Perehody: {analysis.transitions}")
                    print(f"  [OK] SFX: {analysis.sound_effects}")
                    print(f"  [OK] Muzyka: {analysis.music_mood}")
                    print(f"  [OK] Cveta: {analysis.color_palette}")
                    print(f"  [OK] Memy: {analysis.has_meme}")
                    print(f"  [OK] CTA: {analysis.cta[:40] if analysis.cta else 'N/A'}")
                    print(f"  [OK] Pochemu zashlo: {analysis.why_it_works[:70] if analysis.why_it_works else 'N/A'}")
                    print(f"  [OK] Score: {analysis.score}")
                    total_analyzed += 1
                else:
                    print(f"  [FAIL] Analiz ne udalosja")

            except Exception as e:
                err = str(e).encode("ascii", "ignore").decode()[:100]
                print(f"  [FAIL] Oshibka: {err}")

    # Sohranjaem bazu
    learner._save_database()

    # Itogi
    print(f"\n{'='*60}")
    print("[STAT] ITOGI GLUBOKOGO ANALIZA:")
    print(f"  Razobrano LLM: {total_analyzed}")
    print(f"  Vsego v baze: {len(learner.db.analyses)}")
    print(f"  Patternov: {len(learner.db.patterns)}")
    print(f"  Unikalnyh hukov: {len(learner.db.best_hooks)}")
    print(f"  Unikalnyh CTA: {len(learner.db.best_ctas)}")
    print(f"  Cvetovyh shem: {len(learner.db.color_schemes)}")

    # TOP-5 hukov
    if learner.db.best_hooks:
        print(f"\n[TOP] HUKI:")
        for i, hook in enumerate(learner.db.best_hooks[:5], 1):
            safe = hook.encode("ascii", "ignore").decode()[:70]
            print(f"  {i}. {safe}")

    # TOP-5 CTA
    if learner.db.best_ctas:
        print(f"\n[TOP] CTA:")
        for i, cta in enumerate(learner.db.best_ctas[:5], 1):
            safe = cta.encode("ascii", "ignore").decode()[:70]
            print(f"  {i}. {safe}")

    # Patterny po stiljam
    if learner.db.patterns:
        print(f"\n[PAT] PATTERNY PO STILJAM:")
        for style, patterns in learner.db.patterns.items():
            print(f"  {style}: {len(patterns)} patternov")
            for p in patterns[:3]:
                safe = p.encode("ascii", "ignore").decode()[:60]
                print(f"    - {safe}")

    # Sozdanije scenarija
    print(f"\n{'='*60}")
    print("[CREATE] SOZDAJU SCENARIJ NA OSNOVE ZNANIJ...")
    script = await learner.create_from_learning("AI avtomatizacija biznesa")

    print(f"\n[SCRIPT] SCENARIJ:")
    print(f"  Huk: {script.get('hook', 'N/A')}")
    print(f"  Struktura: {script.get('structure', 'N/A')}")
    print(f"  CTA: {script.get('cta', 'N/A')}")
    print(f"  Tempo: {script.get('tempo', 'N/A')}")
    print(f"  Cveta: {script.get('colors', 'N/A')}")
    print(f"  SFX: {script.get('sfx', 'N/A')}")

    # Baza znanij
    db_path = learner.db_file
    if db_path.exists():
        size_kb = db_path.stat().st_size / 1024
        print(f"\n[DB] Baza: {db_path} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    asyncio.run(main())
