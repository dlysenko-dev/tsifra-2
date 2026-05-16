"""
Create Viral Video — sozdaet rolik v stile masterov na osnovanii bazy znanij.
"""
import asyncio
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, ".")

from core.self_learning_video import SelfLearningVideo
from core.llm_router import LLMRouter
from core.video_creator import VideoCreator


async def main():
    print("[INIT] Zagruzka LLM i bazy znanij...")
    llm = LLMRouter()
    learner = SelfLearningVideo(llm_router=llm)

    # Poluchaem scenarij iz bazy znanij
    print("\n[SCRIPT] Poluchenije scenarija iz bazy znanij...")
    script = await learner.create_from_learning("AI avtomatizacija biznesa")

    print("\n[SCRIPT] SCENARIJ:")
    print(f"  Huk: {script.get('hook', 'N/A')}")
    print(f"  Struktura: {script.get('structure', 'N/A')}")
    print(f"  CTA: {script.get('cta', 'N/A')}")
    print(f"  Tempo: {script.get('tempo', 'N/A')}")
    print(f"  Cveta: {script.get('colors', 'N/A')}")
    print(f"  SFX: {script.get('sfx', 'N/A')}")

    # Sozdaem rolik
    print("\n[CREATE] Sozdanije rolikа...")

    vc = VideoCreator(llm_router=llm, project_root=".")
    result = None
    method = None

    # Metod 1: Asset Engine (Merzljakov style)
    print("\n[TRY] Metod 1: Asset Engine (stil Merzljakova)")
    try:
        result = await vc.create_video_asset_engine(
            topic="AI avtomatizacija biznesa",
            duration=15.0,
        )
        if result and not result.startswith("[ERROR]"):
            method = "Asset Engine"
            print(f"  [OK] Asset Engine: {result}")
    except Exception as e:
        print(f"  [WARN] Asset Engine: {e}")

    # Metod 2: Remotion
    if not method:
        print("\n[TRY] Metod 2: Remotion")
        try:
            # Ispolzuem internal metod
            result = await vc._render_remotion(
                type("Seg", (), {"script_code": "FinalComposition", "duration": 15.0})(),
                Path("./temp/remotion_output"),
                0,
            )
            if result and Path(result).exists():
                method = "Remotion"
                print(f"  [OK] Remotion: {result}")
        except Exception as e:
            print(f"  [WARN] Remotion: {e}")

    # Metod 3: Blender AI Workflow
    if not method:
        print("\n[TRY] Metod 3: Blender AI Workflow")
        try:
            from core.blender_ai_workflow import BlenderAIWorkflow
            workflow = BlenderAIWorkflow()
            out_dir = "output/blender_ai"
            os.makedirs(out_dir, exist_ok=True)
            result = await workflow.generate_scene(
                description="AI automation for business, minimalist dark scene with golden neon accents, 3D geometric shapes floating, dark blue background with gold highlights, cinematic camera movement",
                output_dir=out_dir,
            )
            if result and Path(result).exists():
                method = "Blender AI"
                print(f"  [OK] Blender: {result}")
        except Exception as e:
            print(f"  [WARN] Blender: {e}")

    # Proverka rezultata
    if not result or not Path(result).exists():
        print("\n[FAIL] Vse metody ne srabotali")
        return

    print(f"\n{'='*60}")
    print(f"[DONE] ROLIK GOTOV! (metod: {method})")
    print(f"  Put: {result}")

    # Razmer
    size_bytes = Path(result).stat().st_size
    size_mb = size_bytes / (1024 * 1024)
    print(f"  Razmer: {size_mb:.1f} MB ({size_bytes} bajt)")

    # Dlitelnost cherez ffprobe
    try:
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(result)],
            capture_output=True, text=True, timeout=10,
        )
        duration = float(probe.stdout.strip())
        print(f"  Dlitelnost: {duration:.1f} sek")
    except Exception:
        pass

    # Razreshenije
    try:
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height",
             "-of", "csv=s=x:p=0", str(result)],
            capture_output=True, text=True, timeout=10,
        )
        wh = probe.stdout.strip()
        print(f"  Razreshenije: {wh}")
    except Exception:
        pass

    abs_path = os.path.abspath(result)
    print(f"\n[OPEN] Otkryt: {abs_path}")


if __name__ == "__main__":
    asyncio.run(main())
