"""
Analyze by Title — glubokij analiz na osnovanii nazvanija rolikа.
Kimi CLI ne mozhet smotret video, no otlicho ponimajet nazvanija i strukturu.
"""
import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, ".")

from core.self_learning_video import SelfLearningVideo, VideoAnalysis


def kimi_analyze(title: str, duration: float, master: str) -> dict:
    """Otpravljaet nazvanije v Kimi CLI i poluchaet JSON-analiz."""
    
    prompt = f"""Po nazvaniju YouTube Shorts opredeli strukturu i verni TOLKO JSON.

Nazvanije: "{title}"
Dlitelnost: {duration:.0f} sekund
Master: {master}

Vernj strogo JSON (bez markdown, bez kommentariev):
{{
  "title": "{title}",
  "style": "tutorial|storytelling|motion_graphics|vlog|review",
  "hook": "chto govorjat v pervyje 3 sekundy (konkretnyj tekst ili ideja)",
  "structure": "hook -> problem -> solution -> cta|hook -> demo -> result -> cta|hook -> tutorial -> cta",
  "tempo": "slow|medium|fast|crazy",
  "transitions": ["cut", "zoom", "fade", "slide"],
  "sound_effects": ["whoosh", "ping", "boom", "click"],
  "music_mood": "calm|tension|epic|sad|funny",
  "burned_captions": true,
  "caption_style": "big|animated|static",
  "color_palette": ["#1a1a2e", "#ff0044"],
  "has_meme": false,
  "meme_description": "",
  "cta": "konkretnyj prizyv k dejstviju",
  "estimated_retention": "high|medium|low",
  "why_it_works": "pochemu etot format rabotajet",
  "score": 85
}}

Otvet TOLKO JSON, bez dopolnitelnogo teksta."""

    kimi_path = r"C:\Users\mafio\AppData\Roaming\Code\User\globalStorage\moonshot-ai.kimi-code\bin\kimi\kimi.exe"
    
    try:
        start = time.time()
        proc = subprocess.run(
            [kimi_path, "-c", prompt],
            capture_output=True, text=True, timeout=180,
            encoding="utf-8", errors="replace",
        )
        elapsed = time.time() - start
        
        if proc.returncode != 0:
            return {"error": f"kimi exit {proc.returncode}"}
        
        output = proc.stdout
        # Ishem JSON v otvete
        json_start = output.find("{")
        json_end = output.rfind("}")
        if json_start == -1 or json_end == -1:
            return {"error": "no JSON found"}
        
        data = json.loads(output[json_start:json_end+1])
        data["_elapsed"] = elapsed
        return data
        
    except subprocess.TimeoutExpired:
        return {"error": "timeout"}
    except Exception as e:
        return {"error": str(e)}


async def main():
    learner = SelfLearningVideo(llm_router=None)
    
    dirs_to_analyze = [
        ("learning/masters/ArseniiMerzliakov", "ArseniiMerzliakov"),
        ("learning/masters/egorlistopadov", "egorlistopadov"),
        ("learning/masters/YoEdit0r", "YoEdit0r"),
        ("learning/etalons", "ETALON"),
    ]
    
    total = 0
    success = 0
    
    for directory, master_name in dirs_to_analyze:
        if not os.path.exists(directory):
            continue
        
        mp4_files = sorted([f for f in os.listdir(directory) if f.endswith(".mp4")])
        print(f"\n{'='*60}")
        print(f"[DIR] {master_name}: {len(mp4_files)} rolikov")
        
        for i, filename in enumerate(mp4_files, 1):
            video_path = os.path.join(directory, filename)
            safe_name = filename.encode("ascii", "ignore").decode()[:50]
            
            # Poluchaem dlitelnost
            try:
                import subprocess as sp
                r = sp.run(
                    ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                     "-of", "csv=p=0", video_path],
                    capture_output=True, text=True, timeout=10,
                )
                duration = float(r.stdout.strip() or 15)
            except:
                duration = 15.0
            
            print(f"\n[{i}/{len(mp4_files)}] [VID] {safe_name} ({duration:.0f}s)")
            
            # Izlekaem nazvanije bez ID
            title = filename.rsplit("_", 1)[0].replace("_", " ")
            if title.startswith("etalon_"):
                title = title[7:]  # Ubrat "etalon_"
            
            # Analiz cherez Kimi CLI
            result = kimi_analyze(title, duration, master_name)
            
            if "error" in result:
                print(f"  [WARN] Kimi: {result['error']}")
                continue
            
            print(f"  [OK] Time: {result.get('_elapsed', 0):.1f}s")
            print(f"  [OK] Hook: {result.get('hook', 'N/A')[:60]}")
            print(f"  [OK] Style: {result.get('style', 'N/A')}")
            print(f"  [OK] Structure: {result.get('structure', 'N/A')[:50]}")
            print(f"  [OK] Score: {result.get('score', 50)}")
            
            # Sozdaem VideoAnalysis i dobavljaem v bazu
            try:
                analysis = VideoAnalysis(
                    video_id=filename.rsplit("_", 1)[-1].replace(".mp4", ""),
                    title=result.get("title", title),
                    channel=master_name,
                    url="",
                    style=result.get("style", "minimal"),
                    duration=int(duration),
                    hook=result.get("hook", ""),
                    structure=[],  # Uproshhenno
                    tempo=result.get("tempo", "medium"),
                    transitions=result.get("transitions", []),
                    sound_effects=result.get("sound_effects", []),
                    music_mood=result.get("music_mood", "calm"),
                    burned_captions=result.get("burned_captions", False),
                    caption_style=result.get("caption_style", ""),
                    color_palette=result.get("color_palette", []),
                    has_meme=result.get("has_meme", False),
                    meme_description=result.get("meme_description", ""),
                    cta=result.get("cta", ""),
                    estimated_retention=result.get("estimated_retention", "medium"),
                    why_it_works=result.get("why_it_works", ""),
                    score=int(result.get("score", 70)),
                )
                learner.db.analyses.append({
                    "video_id": analysis.video_id,
                    "title": analysis.title,
                    "channel": analysis.channel,
                    "style": analysis.style,
                    "duration": analysis.duration,
                    "hook": analysis.hook,
                    "tempo": analysis.tempo,
                    "transitions": analysis.transitions,
                    "sound_effects": analysis.sound_effects,
                    "music_mood": analysis.music_mood,
                    "burned_captions": analysis.burned_captions,
                    "color_palette": analysis.color_palette,
                    "has_meme": analysis.has_meme,
                    "cta": analysis.cta,
                    "why_it_works": analysis.why_it_works,
                    "score": analysis.score,
                })
                
                # Obnovljaem patterny
                if analysis.hook and analysis.hook not in learner.db.best_hooks:
                    learner.db.best_hooks.append(analysis.hook)
                if analysis.cta and analysis.cta not in learner.db.best_ctas:
                    learner.db.best_ctas.append(analysis.cta)
                if analysis.style not in learner.db.patterns:
                    learner.db.patterns[analysis.style] = []
                struct = result.get("structure", "")
                if struct and struct not in learner.db.patterns[analysis.style]:
                    learner.db.patterns[analysis.style].append(struct)
                mood = analysis.music_mood
                if mood not in learner.db.color_schemes:
                    learner.db.color_schemes[mood] = []
                for c in analysis.color_palette:
                    if c not in learner.db.color_schemes[mood]:
                        learner.db.color_schemes[mood].append(c)
                
                learner.db.total_videos_analyzed += 1
                success += 1
            except Exception as e:
                print(f"  [WARN] Parse error: {e}")
            
            total += 1
            
            # Sohranjajem bazu posle kazhdogo rolikа
            learner._save_database()
    
    # Itogi
    print(f"\n{'='*60}")
    print("[STAT] ITOGI GLUBOKOGO ANALIZA (Kimi CLI po nazvanijam):")
    print(f"  Vsego: {total}")
    print(f"  Uspehov: {success}")
    print(f"  V baze: {learner.db.total_videos_analyzed}")
    print(f"  Patternov: {len(learner.db.patterns)}")
    print(f"  Unikalnyh hukov: {len(learner.db.best_hooks)}")
    print(f"  Unikalnyh CTA: {len(learner.db.best_ctas)}")
    
    if learner.db.best_hooks:
        print("\n[TOP] HUKI:")
        for i, h in enumerate(learner.db.best_hooks[:5], 1):
            print(f"  {i}. {h.encode('ascii', 'ignore').decode()[:70]}")
    
    if learner.db.best_ctas:
        print("\n[TOP] CTA:")
        for i, c in enumerate(learner.db.best_ctas[:5], 1):
            print(f"  {i}. {c.encode('ascii', 'ignore').decode()[:70]}")
    
    if learner.db.patterns:
        print("\n[PAT] PATTERNY:")
        for style, patterns in learner.db.patterns.items():
            print(f"  {style}: {patterns[:3]}")
    
    # Scenarij
    print(f"\n{'='*60}")
    print("[CREATE] Scenarij...")
    script = await learner.create_from_learning("AI avtomatizacija biznesa")
    print(f"  Huk: {script.get('hook', 'N/A')}")
    print(f"  Struktura: {script.get('structure', 'N/A')}")
    print(f"  CTA: {script.get('cta', 'N/A')}")
    print(f"  Tempo: {script.get('tempo', 'N/A')}")
    print(f"  Cveta: {script.get('colors', 'N/A')}")


if __name__ == "__main__":
    asyncio.run(main())
