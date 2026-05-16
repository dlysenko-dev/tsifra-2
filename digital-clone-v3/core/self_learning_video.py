"""
Self-Learning Video System  agent uchitsja delat roliki.

Pipeline:
1. Poisk rolikov na YouTube (po kluchevym slovam)
2. Skachivanije rolikov (yt-dlp)
3. Razbor struktury (sceny, huki, perehody, SFX, memy)
4. Izvlechenije patternov (chto rabotajet, pochemu)
5. Sohranenije v bazu znanij
6. Popytka replikacii
7. Poluchenije obratnoj svjazi
8. Iterativnoje uluchshenije
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class VideoAnalysis:
    """Razbor odnogo rolika."""
    video_id: str
    title: str
    channel: str
    url: str
    style: str  # minimal, vlog, motion_graphics, storytelling, tutorial
    duration: int  # sekundy
    hook: str  # pervyje 3 sekundy
    structure: List[Dict]  # [{scene_number, start, end, type, description}]
    tempo: str  # slow/medium/fast/crazy
    transitions: List[str]  # [cut, fade, slide, zoom, whip_pan]
    sound_effects: List[str]  # [whoosh, ping, boom, glitch]
    music_mood: str  # calm/tension/epic/sad/funny
    burned_captions: bool
    caption_style: str  # big/medium/small/animated/static
    color_palette: List[str]  # [dark_blue, warm_orange, cold_white]
    has_meme: bool
    meme_description: str
    cta: str  # prizyv k dejstviju
    estimated_retention: str  # high/medium/low
    why_it_works: str  # analiz pochemu zashlo
    score: int = 0  # ocenka agentom (0-100)


@dataclass
class LearningDatabase:
    """Baza znanij agenta."""
    analyses: List[Dict] = field(default_factory=list)
    patterns: Dict[str, List[str]] = field(default_factory=dict)  # {style: [pattern1, pattern2]}
    sfx_library: List[str] = field(default_factory=list)  # puti k SFX fajlam
    color_schemes: Dict[str, List[str]] = field(default_factory=dict)  # {mood: [colors]}
    best_hooks: List[str] = field(default_factory=list)
    best_ctas: List[str] = field(default_factory=list)
    meme_templates: List[str] = field(default_factory=list)
    total_videos_analyzed: int = 0
    last_updated: str = ""


class SelfLearningVideo:
    """Agent uchitsja delat roliki."""

    def __init__(
        self,
        output_dir: str = "./learning",
        llm_router=None,
        browser_tool=None,
    ) -> None:
        self.output_dir = Path(output_dir)
        self.llm = llm_router
        self.browser = browser_tool
        self.db_file = self.output_dir / "video_knowledge.json"
        self.videos_dir = self.output_dir / "downloaded_videos"
        self.sfx_dir = self.output_dir / "sfx"
        self.ref_dir = self.output_dir / "references"
        self.ffprobe = shutil.which("ffprobe")

        for d in [self.videos_dir, self.sfx_dir, self.ref_dir]:
            d.mkdir(parents=True, exist_ok=True)

        self.db = self._load_database()
        self.yt_dlp_cmd = self._find_yt_dlp()

    def _find_yt_dlp(self) -> Optional[List[str]]:
        """Nahodit yt-dlp (exe ili python -m)."""
        if shutil.which("yt-dlp"):
            return ["yt-dlp"]
        scripts = Path(sys.executable).parent / "Scripts" / "yt-dlp.exe"
        if scripts.exists():
            return [str(scripts)]
        try:
            import yt_dlp
            return [sys.executable, "-m", "yt_dlp"]
        except ImportError:
            pass
        return None

    # =======================================================
    # ShAG 1: Poisk i skachivanije rolikov
    # =======================================================

    async def fetch_learning_videos(
        self,
        queries: Optional[List[str]] = None,
        max_per_query: int = 5,
    ) -> List[str]:
        """Ishet i skachivajet obuchajushchije roliki s YouTube."""
        if queries is None:
            queries = [
                "viral shorts editing techniques 2026",
                "YouTube shorts storytelling structure",
                "motion graphics viral shorts",
                "best short form video hooks",
                "shorts sound design SFX",
                "video editing meme inserts",
                "burned captions best practices",
                "minimalist video editing style",
                "shorts color grading viral",
                "YouTube shorts retention analysis",
            ]

        downloaded: List[str] = []
        for query in queries:
            print(f"  [SEARCH] Ischu: {query}")
            try:
                result = subprocess.run(
                    self.yt_dlp_cmd + ["--get-id", "--get-title",
                     f"ytsearch{max_per_query}:{query}"],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    encoding="utf-8",
                    errors="replace",
                )
                lines = [l.strip() for l in result.stdout.strip().split("\n") if l.strip()]
                # yt-dlp vyvodit title i id cherez stroku
                # Prichoditsja razbivat po param
                for i in range(0, len(lines), 2):
                    if i + 1 < len(lines):
                        title = lines[i]
                        video_id = lines[i + 1]
                        # Proverka chto video_id pohozh na id (11 simvolov)
                        if len(video_id) == 11 and all(c.isalnum() or c in "-_" for c in video_id):
                            video_path = await self._download_video(video_id, title)
                            if video_path:
                                downloaded.append(video_path)
                        else:
                            # Mozhet byt naoborot: snachala id, potom title
                            video_id, title = title, video_id
                            if len(video_id) == 11:
                                video_path = await self._download_video(video_id, title)
                                if video_path:
                                    downloaded.append(video_path)
            except Exception as e:
                print(f"  [WARN] Oshibka poiska: {e}")

        return downloaded

    async def _download_video(
        self, video_id: str, title: str
    ) -> Optional[str]:
        """Skachivajet video cherez yt-dlp."""
        safe_title = "".join(c for c in title if c.isalnum() or c in " _-")[:50]
        output_path = self.videos_dir / f"{safe_title}_{video_id}.mp4"

        if output_path.exists():
            return str(output_path)

        if not self.yt_dlp_cmd:
            print("  [WARN] yt-dlp ne najden. Ustanovi: pip install yt-dlp")
            return None

        try:
            proc = await asyncio.create_subprocess_exec(
                *self.yt_dlp_cmd,
                "-f", "best[height<=720][ext=mp4]/best[height<=720]/best",
                "--merge-output-format", "mp4",
                "-o", str(output_path),
                f"https://youtube.com/shorts/{video_id}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=120
            )
            if output_path.exists():
                size_mb = output_path.stat().st_size / (1024 * 1024)
                print(f"     [OK] Skachano: {safe_title[:40]} ({size_mb:.1f} MB)")
                return str(output_path)
            else:
                err = stderr.decode("utf-8", errors="replace")[:200]
                print(f"     [FAIL] Ne skachalos: {err}")
        except asyncio.TimeoutError:
            print(f"     [FAIL] Timeout pri skachivanii {video_id}")
        except Exception as e:
            print(f"     [FAIL] Oshibka: {e}")

        return None

    # =======================================================
    # ShAG 2: Razbor struktury rolika
    # =======================================================

    async def analyze_video(self, video_path: str) -> Optional[VideoAnalysis]:
        """Razbiraet rolik na strukturu."""
        path = Path(video_path)
        print(f"  [VID] Analiziruju: {path.name.encode("ascii", "ignore").decode()}")

        # Info cherez ffprobe
        info = self._get_video_info(video_path)
        duration = info.get("duration", 15)
        try:
            duration = float(duration)
        except (ValueError, TypeError):
            duration = 15.0

        # Razbivka na sceny (prostaja: 3 ravnyje chasti dlja Shorts)
        scenes = self._detect_scenes(duration)

        # Analiz cherez LLM
        analysis = None
        if self.llm:
            try:
                prompt = f"""Projanaliziruj etot YouTube Shorts i verni JSON:

Nazvanije: {path.name.encode("ascii", "ignore").decode()}
Dlitelnost: {duration:.1f} sekund
Razreshenije: {info.get('width', '?')}x{info.get('height', '?')}

Otvet strogo v formate JSON (bez markdown):
{{
  "title": "nazvanije",
  "channel": "kanal",
  "style": "minimal|vlog|motion_graphics|storytelling|tutorial",
  "hook": "chto proishodit v pervyje 3 sekundy",
  "structure": [
    {{"scene_number": 1, "start": 0, "end": 5, "type": "hook", "description": "..."}},
    {{"scene_number": 2, "start": 5, "end": 10, "type": "problem", "description": "..."}},
    {{"scene_number": 3, "start": 10, "end": 15, "type": "cta", "description": "..."}}
  ],
  "tempo": "slow|medium|fast|crazy",
  "transitions": ["cut", "zoom", "fade"],
  "sound_effects": ["whoosh", "ping", "boom"],
  "music_mood": "calm|tension|epic|sad|funny",
  "burned_captions": true,
  "caption_style": "big|medium|animated|static",
  "color_palette": ["#1a1a2e", "#ff0044"],
  "has_meme": false,
  "meme_description": "",
  "cta": "tekst prizyva k dejstviju",
  "estimated_retention": "high|medium|low",
  "why_it_works": "pochemu etot rolik mog zajti",
  "score": 85
}}
"""
                result = await self.llm.complete(
                    prompt, max_tokens=2000, temperature=0.3
                )
                analysis = self._parse_analysis(result, video_path, info)
            except Exception as e:
                print(f"     [WARN] LLM analiz ne srabotal: {e}")

        # Esli LLM ne dostupen  hevristicheskij analiz
        if analysis is None:
            analysis = self._heuristic_analysis(video_path, info)

        if analysis:
            self.db.analyses.append(asdict(analysis))
            self._update_patterns(analysis)
            self.db.total_videos_analyzed += 1
            self.db.last_updated = datetime.now().isoformat()
            self._save_database()
            print(f"     [OK] Score: {analysis.score}, Style: {analysis.style}, Tempo: {analysis.tempo}")

        return analysis

    def _detect_scenes(self, duration: float) -> List[Dict]:
        """Prostaja razbivka na 3 sceny dlja Shorts."""
        part = duration / 3
        return [
            {"scene_number": 1, "start": 0, "end": part, "type": "hook", "description": "Pervyje 3 sekundy  hvatalka"},
            {"scene_number": 2, "start": part, "end": part * 2, "type": "content", "description": "Osnovnoe soderzhanije"},
            {"scene_number": 3, "start": part * 2, "end": duration, "type": "cta", "description": "Prizyv k dejstviju"},
        ]

    # =======================================================
    # ShAG 3: Izvlechenije patternov
    # =======================================================

    def _update_patterns(self, analysis: VideoAnalysis) -> None:
        """Obnovljaet bazu patternov na osnove analiza."""
        style = analysis.style

        # Pattern struktury
        if analysis.structure:
            types = [s.get("type", "unknown") for s in analysis.structure]
            structure_pattern = " -> ".join(types)
        else:
            structure_pattern = "hook -> problem -> solution -> cta"

        if style not in self.db.patterns:
            self.db.patterns[style] = []
        if structure_pattern not in self.db.patterns[style]:
            self.db.patterns[style].append(structure_pattern)

        # Luchshije huki (sortirovka po score)
        if analysis.hook and analysis.hook not in self.db.best_hooks:
            self.db.best_hooks.append(analysis.hook)
            self.db.best_hooks.sort(key=lambda h: len(h), reverse=True)
            self.db.best_hooks = self.db.best_hooks[:50]  # limit

        # Luchshije CTA
        if analysis.cta and analysis.cta not in self.db.best_ctas:
            self.db.best_ctas.append(analysis.cta)
            self.db.best_ctas = self.db.best_ctas[:50]

        # Cvetovye shemy
        mood = analysis.music_mood
        if mood not in self.db.color_schemes:
            self.db.color_schemes[mood] = []
        for color in analysis.color_palette:
            clean = color.strip().lower()
            if clean and clean not in self.db.color_schemes[mood]:
                self.db.color_schemes[mood].append(clean)

        # SFX
        for sfx in analysis.sound_effects:
            clean = sfx.strip().lower()
            if clean and clean not in self.db.sfx_library:
                self.db.sfx_library.append(clean)

    # =======================================================
    # ShAG 4: Skacivanije SFX biblioteki
    # =======================================================

    async def build_sfx_library(self) -> List[str]:
        """Skacivajet/generirujet SFX."""
        sfx_categories = {
            "transition": ["whoosh", "swoosh", "swipe", "whip"],
            "impact": ["boom", "hit", "punch", "slam"],
            "notification": ["ping", "pop", "click", "ding"],
            "ambient": ["calm", "tension", "epic"],
            "glitch": ["glitch", "static", "digital"],
        }

        created: List[str] = []
        for category, sounds in sfx_categories.items():
            cat_dir = self.sfx_dir / category
            cat_dir.mkdir(exist_ok=True)

            for sound in sounds:
                output = cat_dir / f"{sound}.mp3"
                if not output.exists():
                    self._generate_sfx_placeholder(str(output), category)
                if output.exists():
                    created.append(str(output))

        print(f"     [OK] SFX v biblioteke: {len(created)}")
        return created

    def _generate_sfx_placeholder(self, output_path: str, category: str) -> None:
        """Generirujet prostoj SFX cherez ffmpeg."""
        if not shutil.which("ffmpeg"):
            return

        generators = {
            "transition": (
                "sine=frequency=800:duration=0.3",
                "afade=t=out:st=0.1:d=0.2,volume=0.5"
            ),
            "impact": (
                "sine=frequency=150:duration=0.25",
                "afade=t=out:st=0.05:d=0.2,volume=2.0,lowpass=f=400"
            ),
            "notification": (
                "sine=frequency=1200:duration=0.15",
                "afade=t=out:st=0.05:d=0.1,volume=0.4"
            ),
            "ambient": (
                "anoisesrc=a=0.03:color=pink:duration=5",
                "lowpass=f=600,volume=0.15"
            ),
            "glitch": (
                "sine=frequency=100:duration=0.1",
                "vibrato=f=50:d=0.5,volume=0.3"
            ),
        }
        gen, filt = generators.get(category, generators["transition"])

        subprocess.run(
            ["ffmpeg", "-y", "-f", "lavfi", "-i", gen,
             "-af", filt, "-ar", "44100", "-ac", "2",
             output_path],
            capture_output=True,
            timeout=10,
        )

    # =======================================================
    # ShAG 5: Nocnaja ucoba
    # =======================================================

    async def night_study_session(self, sessions: int = 5) -> Dict[str, Any]:
        """Nocnaja sessija obucenija."""
        print("\n" + "=" * 60)
        print("[NIGHT] NOCNAJA UCOBA NACHINAJETSJA")
        print("=" * 60)

        start_time = datetime.now()

        # 1. Skachivanije
        print("\n[DL] ShAG 1: Poisk i skachivanije rolikov")
        videos = await self.fetch_learning_videos(max_per_query=sessions)
        print(f"   Vsego skacano: {len(videos)}")

        # 2. Razbor
        print("\n[VID] ShAG 2: Razbor struktury")
        analyzed = 0
        for video_path in videos:
            analysis = await self.analyze_video(video_path)
            if analysis:
                analyzed += 1

        # 3. SFX
        print("\n[SFX] ShAG 3: SFX biblioteka")
        sfx_count = len(await self.build_sfx_library())

        # 4. Itogi
        elapsed = (datetime.now() - start_time).total_seconds()
        print("\n" + "=" * 60)
        print("[STAT] ITOGI UCOBY:")
        print(f"   Vremja: {elapsed:.0f}s")
        print(f"   Razobrano rolikov: {analyzed}/{len(videos)}")
        print(f"   Vsego v baze: {self.db.total_videos_analyzed}")
        print(f"   Patternov: {sum(len(v) for v in self.db.patterns.values())}")
        print(f"   SFX v biblioteke: {sfx_count}")
        print(f"   Luchshih hukov: {len(self.db.best_hooks)}")
        print(f"   Luchshih CTA: {len(self.db.best_ctas)}")
        print(f"   Cvetovyh shem: {len(self.db.color_schemes)}")
        print("=" * 60)

        return {
            "downloaded": len(videos),
            "analyzed": analyzed,
            "total_in_db": self.db.total_videos_analyzed,
            "sfx_count": sfx_count,
            "elapsed_seconds": elapsed,
        }

    # =======================================================
    # ShAG 6: Sozdanije rolika na osnove znanij
    # =======================================================

    async def create_from_learning(self, topic: str) -> Dict[str, Any]:
        """Sozdajet rolik na osnove nakoplennyh znanij."""
        print(f"\n[VID] Sozdaju rolik na temu: {topic}")

        # Vybor luchshih patternov
        best_hooks = self.db.best_hooks[:10] if self.db.best_hooks else [
            "95% ljudej ne znajut etogo",
            "Eto izmenit vsjo",
            "Ostanovis i posmotri",
            "Samaja bolshaja oshibka",
        ]

        best_structures: List[str] = []
        for style_patterns in self.db.patterns.values():
            best_structures.extend(style_patterns[:3])
        if not best_structures:
            best_structures = ["hook -> problem -> solution -> cta"]

        best_ctas = self.db.best_ctas[:10] if self.db.best_ctas else [
            "Podpishis",
            "Ssylka v opisanii",
            "Kommentiruj",
            "Sohrani",
        ]

        # Podbor cvetov po nastroeniju
        default_colors = ["#1a1a2e", "#ff0044", "#00d4ff", "#ffffff"]
        colors = self.db.color_schemes.get("tension", [])
        if not colors:
            colors = self.db.color_schemes.get("epic", [])
        if not colors:
            colors = default_colors

        # Sbornyje SFX
        sfx = self.db.sfx_library[:8] if self.db.sfx_library else [
            "whoosh", "ping", "boom", "click"
        ]

        script = {
            "topic": topic,
            "hook": best_hooks[0] if best_hooks else "Vnimajet!",
            "structure": best_structures[0] if best_structures else "hook -> problem -> solution -> cta",
            "cta": best_ctas[0] if best_ctas else "Podpishis",
            "tempo": "medium",
            "colors": colors[:5],
            "sfx": sfx[:5],
            "patterns_available": len(best_structures),
            "hooks_available": len(best_hooks),
            "ctas_available": len(best_ctas),
        }

        print(f"   Huk: {script['hook']}")
        print(f"   Struktura: {script['structure']}")
        print(f"   CTA: {script['cta']}")
        print(f"   Ceta: {script['colors']}")

        return script

    # =======================================================
    # Helpers
    # =======================================================

    def _load_database(self) -> LearningDatabase:
        """Zagruzajet bazu iz JSON."""
        if self.db_file.exists():
            try:
                data = json.loads(self.db_file.read_text(encoding="utf-8"))
                return LearningDatabase(**data)
            except Exception as e:
                print(f"[WARN] Ne udalos zagruzit bazu: {e}, sozdaem novuju")
        return LearningDatabase()

    def _save_database(self) -> None:
        """Sohranjajet bazu v JSON."""
        try:
            self.db_file.write_text(
                json.dumps(
                    {
                        "analyses": self.db.analyses,
                        "patterns": self.db.patterns,
                        "sfx_library": self.db.sfx_library,
                        "color_schemes": self.db.color_schemes,
                        "best_hooks": self.db.best_hooks,
                        "best_ctas": self.db.best_ctas,
                        "meme_templates": self.db.meme_templates,
                        "total_videos_analyzed": self.db.total_videos_analyzed,
                        "last_updated": self.db.last_updated,
                    },
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
        except Exception as e:
            print(f"[WARN] Ne udalos sohranit bazu: {e}")

    def _get_video_info(self, video_path: str) -> Dict[str, Any]:
        """Polucajet informaciju o video cherez ffprobe."""
        if not self.ffprobe:
            return {"duration": "15", "width": "1080", "height": "1920"}

        try:
            result = subprocess.run(
                [self.ffprobe, "-v", "error",
                 "-show_entries", "format=duration",
                 "-show_entries", "stream=width,height",
                 "-of", "json", video_path],
                capture_output=True,
                text=True,
                timeout=10,
            )
            data = json.loads(result.stdout)
            info: Dict[str, Any] = {}
            if "format" in data:
                info["duration"] = data["format"].get("duration", "15")
            if "streams" in data and data["streams"]:
                for stream in data["streams"]:
                    if stream.get("width"):
                        info["width"] = stream["width"]
                    if stream.get("height"):
                        info["height"] = stream["height"]
            return info
        except Exception:
            return {"duration": "15", "width": "1080", "height": "1920"}

    def _parse_analysis(
        self,
        text: str,
        video_path: str,
        info: Dict[str, Any],
    ) -> Optional[VideoAnalysis]:
        """Parsit JSON analiz iz otveta LLM."""
        try:
            # Ishem JSON v otvete
            json_match = re.search(r"\{.*\}", text, re.DOTALL)
            if not json_match:
                return None

            data = json.loads(json_match.group())
            stem = Path(video_path).stem
            video_id = stem[-11:] if len(stem) > 11 else stem

            return VideoAnalysis(
                video_id=video_id,
                title=data.get("title", stem),
                channel=data.get("channel", "Unknown"),
                url=data.get("url", ""),
                style=data.get("style", "minimal"),
                duration=int(float(data.get("duration", info.get("duration", 15)))),
                hook=data.get("hook", ""),
                structure=data.get("structure", []),
                tempo=data.get("tempo", "medium"),
                transitions=data.get("transitions", []),
                sound_effects=data.get("sound_effects", []),
                music_mood=data.get("music_mood", "calm"),
                burned_captions=data.get("burned_captions", False),
                caption_style=data.get("caption_style", ""),
                color_palette=data.get("color_palette", []),
                has_meme=data.get("has_meme", False),
                meme_description=data.get("meme_description", ""),
                cta=data.get("cta", ""),
                estimated_retention=data.get("estimated_retention", "medium"),
                why_it_works=data.get("why_it_works", ""),
                score=int(data.get("score", 70)),
            )
        except Exception as e:
            print(f"     [WARN] Parsing error: {e}")
            return None

    def _heuristic_analysis(
        self, video_path: str, info: Dict[str, Any]
    ) -> VideoAnalysis:
        """Hevristicheskij analiz bez LLM."""
        stem = Path(video_path).stem
        duration = int(float(info.get("duration", 15)))
        part = duration / 3

        return VideoAnalysis(
            video_id=stem[-11:] if len(stem) > 11 else stem,
            title=stem,
            channel="Unknown",
            url="",
            style="minimal",
            duration=duration,
            hook="Neizvestnyj huk (hevristika)",
            structure=[
                {"scene_number": 1, "start": 0, "end": part, "type": "hook", "description": "Pervyje 3 sekundy"},
                {"scene_number": 2, "start": part, "end": part * 2, "type": "content", "description": "Osnovnoe soderzhanije"},
                {"scene_number": 3, "start": part * 2, "end": duration, "type": "cta", "description": "Prizyv k dejstviju"},
            ],
            tempo="medium",
            transitions=["cut"],
            sound_effects=[],
            music_mood="calm",
            burned_captions=False,
            caption_style="",
            color_palette=[],
            has_meme=False,
            meme_description="",
            cta="Podpishis",
            estimated_retention="medium",
            why_it_works="Hevristicheskij analiz bez LLM",
            score=50,
        )
