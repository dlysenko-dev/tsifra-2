"""
Test Self-Learning Video System bez YouTube (lokalnyj test).
"""
import sys
sys.path.insert(0, ".")

import asyncio
import shutil
import subprocess
from pathlib import Path

from core.self_learning_video import SelfLearningVideo


async def main():
    learner = SelfLearningVideo(
        output_dir="./learning",
        llm_router=None,
    )

    # Sozdaem testovoe video cherez ffmpeg (3 sceny: temnaja/svetlaja/krasnaja)
    print("[TEST] Sozdanije testovogo video...")
    test_dir = Path("./learning/test_videos")
    test_dir.mkdir(parents=True, exist_ok=True)

    if shutil.which("ffmpeg"):
        # 3 korotkih klipa po 3 sekundy
        for color, name in [("black", "hook_dark"), ("white", "solution_bright"), ("red", "cta_vivid")]:
            out = test_dir / f"{name}.mp4"
            if not out.exists():
                subprocess.run(
                    ["ffmpeg", "-y", "-f", "lavfi",
                     "-i", f"color=c={color}:s=1080x1920:d=3",
                     "-f", "lavfi", "-i", "sine=frequency=400:duration=3",
                     "-shortest", "-pix_fmt", "yuv420p", str(out)],
                    capture_output=True, timeout=15,
                )
            print(f"  [OK] {out.name}")

    # Razbor testovyh video
    print("\n[TEST] Razbor struktury...")
    test_videos = list(test_dir.glob("*.mp4"))
    for v in test_videos:
        analysis = await learner.analyze_video(str(v))
        if analysis:
            print(f"  [OK] {analysis.video_id}: score={analysis.score}, style={analysis.style}")

    # SFX biblioteka
    print("\n[TEST] SFX biblioteka...")
    sfx = await learner.build_sfx_library()
    print(f"  [OK] SFX fajlov: {len(sfx)}")

    # Sozdanije scenarija
    print("\n[TEST] Sozdanije scenarija iz bazu znanij...")
    script = await learner.create_from_learning("AI avtomatizacija biznesa")
    print(f"  [OK] Huk: {script['hook']}")
    print(f"  [OK] Struktura: {script['structure']}")
    print(f"  [OK] CTA: {script['cta']}")
    print(f"  [OK] Cveta: {script['colors']}")

    # Itogi
    print("\n" + "=" * 60)
    print("[STAT] BAZA ZNANIJ:")
    print(f"  Razobrano video: {learner.db.total_videos_analyzed}")
    print(f"  Patternov: {len(learner.db.patterns)}")
    print(f"  Luchshih hukov: {len(learner.db.best_hooks)}")
    print(f"  Luchshih CTA: {len(learner.db.best_ctas)}")
    print(f"  Cvetovyh shem: {len(learner.db.color_schemes)}")
    print(f"  SFX v baze: {len(learner.db.sfx_library)}")
    print("=" * 60)

    # Pokazhem soderzhimoe JSON bazy
    db_path = learner.db_file
    if db_path.exists():
        data = db_path.read_text(encoding="utf-8")
        size_kb = len(data) / 1024
        print(f"\n[DB] Fajl: {db_path} ({size_kb:.1f} KB)")
        # Pokazhem pervye 2000 simvolov
        print("[DB] Soderzhanije (pervye 2000 symvolov):")
        print(data[:2000])


if __name__ == "__main__":
    asyncio.run(main())
