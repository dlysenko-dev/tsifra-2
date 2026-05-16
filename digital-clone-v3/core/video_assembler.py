"""
Video Assembler — skleivajet assety v rolik cherez ffmpeg.
Stil: Arsenij Merzljakov — 3 sceny, kontrast, effekty.

Pipeline (Merzljakov-style):
  1. Scena 1 (Problema)  — temnyje cveta, haos, bystryje katy
  2. Scena 2 (Reshenije) — svetlyje cveta, porjadok, medlenno
  3. Scena 3 (Rezultat)  — jarkije cveta, cifry, CTA
  4. Effekty: film grain, glow, chromatic aberration
  5. Zvuk: SFX na kazhdyj cut + fonovaja muzyka
  6. Burned captions (krupnyj tekst nakladennyj na video)
"""
from __future__ import annotations

import asyncio
import json
import math
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class VideoAssembler:
    """
    Montazher. Skleivajet assety v istoriju.

    Stil Merzljakova:
      - 3 akta: haos → porjadok → rezultat
      - Rezkye perehody (hard cuts, ne crossfade)
      - Zvukovyje akcenty na kazhdom perehode
      - Tekst v kadre (burned-in captions)
      - Cvetokorrektsija dlja kazhdoj sceny
    """

    # Cvetokorrektsija: nazvanije → ffmpeg curves/zscale
    COLOR_GRADES = {
        "dark": {
            "brightness": -0.15,
            "contrast": 1.2,
            "saturation": 0.7,
            "gamma": 1.3,
            "color": "cool",  # sinij otrjivochnyj
        },
        "bright": {
            "brightness": 0.1,
            "contrast": 1.1,
            "saturation": 1.1,
            "gamma": 1.0,
            "color": "warm",  # teplyj
        },
        "vivid": {
            "brightness": 0.05,
            "contrast": 1.3,
            "saturation": 1.4,
            "gamma": 0.95,
            "color": "neon",  # nasyshchennyj
        },
        "monochrome": {
            "brightness": 0.0,
            "contrast": 1.2,
            "saturation": 0.0,
            "gamma": 1.1,
            "color": "bw",
        },
        "sepia": {
            "brightness": 0.0,
            "contrast": 1.1,
            "saturation": 0.3,
            "gamma": 1.0,
            "color": "sepia",
        },
    }

    def __init__(self, output_dir: str = "./output/videos") -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.has_ffmpeg = shutil.which("ffmpeg") is not None
        self.temp_dir = Path(tempfile.gettempdir()) / "video_assembler"
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    # ── Main pipeline ───────────────────────────────────────────────────────

    async def assemble_story(
        self,
        scenes: List[Dict[str, Any]],
        captions: Optional[List[Dict[str, Any]]] = None,
        sound_effects: Optional[List[str]] = None,
        music: Optional[str] = None,
        output_name: str = "final.mp4",
        target_size: Tuple[int, int] = (1080, 1920),  # 9:16 Shorts
        fps: int = 30,
    ) -> str:
        """
        Skleivajet rolik iz scen.

        Args:
            scenes: [{"file": "path.mp4", "duration": 5, "color_grade": "dark",
                      "speed": 1.0, "zoom": "in"}, ...]
            captions: [{"text": "95%", "start": 0, "duration": 3,
                        "style": "glitch", "position": "center"}, ...]
            sound_effects: ["whoosh.mp3", "ping.mp3", ...]
            music: "background.mp3"
            output_name: "final.mp4"
            target_size: (w, h) — razreshenije vыhodnogo rolikа
            fps: kadrov v sekundu

        Returns:
            Put k gotovomu MP4.
        """
        if not self.has_ffmpeg:
            return "[ERROR] ffmpeg ne najden"

        work_dir = self.temp_dir / f"asm_{output_name.replace('.mp4','')}"
        work_dir.mkdir(parents=True, exist_ok=True)

        # 1. Podgotovit kazhduju scenu (masshtab, cvet, skorost)
        scene_clips: List[str] = []
        for i, scene in enumerate(scenes):
            clip = await self._prepare_scene(
                scene, work_dir, i, target_size, fps
            )
            if clip:
                scene_clips.append(clip)

        if not scene_clips:
            return "[ERROR] Net validnyh scen dlja sborki"

        # 2. Soedinit sceny (concat)
        concat_path = await self._concat_scenes(scene_clips, work_dir, fps)
        if not concat_path:
            return "[ERROR] Oshibka concat scen"

        current = concat_path

        # 3. Dobavit nadpisi (burned captions)
        if captions:
            captioned = await self._burn_captions(current, captions, work_dir, target_size)
            if captioned:
                current = captioned

        # 4. Zvukovaja dorozhka: SFX + muzyka
        final_audio = await self._mix_audio(
            current, sound_effects or [], music, work_dir
        )
        if final_audio:
            current = final_audio

        # 5. Effekty (grain, glow, chromatic)
        effects = scenes[0].get("effects", []) if scenes else []
        for effect in effects:
            effected = self.add_effect(current, effect, work_dir)
            if effected:
                current = effected

        # 6. Finalnyj eksport v output
        output_path = self.output_dir / output_name
        shutil.copy2(current, output_path)

        # Cleanup temp (ne vsegda, no ostavim dlja debuga)
        # shutil.rmtree(work_dir, ignore_errors=True)

        return str(output_path)

    # ── Scene preparation ───────────────────────────────────────────────────

    async def _prepare_scene(
        self,
        scene: Dict[str, Any],
        work_dir: Path,
        index: int,
        target_size: Tuple[int, int],
        fps: int,
    ) -> Optional[str]:
        """Podgotavlivajet odnu scenu: masshtab, cvetokorrektsija, skorost."""
        file_path = scene.get("file", "")
        duration = scene.get("duration", 5.0)
        color_grade = scene.get("color_grade", "bright")
        speed = scene.get("speed", 1.0)
        zoom = scene.get("zoom", "none")  # none | in | out | pulse

        if not file_path or not Path(file_path).exists():
            # Fallback: color card
            from core.asset_downloader import AssetDownloader
            ad = AssetDownloader(output_dir=str(work_dir))
            color = {"dark": "black", "bright": "white", "vivid": "red"}.get(color_grade, "gray")
            file_path = await ad.create_color_card(
                color, target_size[0], target_size[1], duration,
                output_name=f"scene_{index}_fallback"
            )
            if not file_path:
                return None

        out_path = work_dir / f"scene_{index:02d}_prepared.mp4"

        # FFmpeg filtr: cvet + skorost + zoom
        vf_parts = [f"fps={fps},format=yuv420p"]

        # Cvetokorrektsija
        grade = self.COLOR_GRADES.get(color_grade, self.COLOR_GRADES["bright"])
        lutvf = self._build_color_filter(grade)
        if lutvf:
            vf_parts.append(lutvf)

        # Zoom effekt (priblizhenije/udalenije)
        if zoom == "in":
            vf_parts.append("zoompan=z='min(zoom+0.0015,1.5)':d=125:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'")
        elif zoom == "out":
            vf_parts.append("zoompan=z='max(1.5-zoom*0.0015,1.0)':d=125:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'")
        elif zoom == "pulse":
            vf_parts.append("zoompan=z='1+0.1*sin(in*0.05)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'")

        # Skorost (setpts)
        atempo = ""
        if speed != 1.0 and speed > 0.1:
            atempo = f",atempo={speed}"
            # Dlja video: setpts=PTS/{speed}
            vf_parts.append(f"setpts=PTS/{speed}")

        # Masshtab do celjevogo razreshenija
        vf_parts.append(f"scale={target_size[0]}:{target_size[1]}:force_original_aspect_ratio=decrease,pad={target_size[0]}:{target_size[1]}:(ow-iw)/2:(oh-ih)/2")

        vf = ",".join(vf_parts)

        # Esli originalnoe video koroche nuzhnoj dlitelnosti — loop
        input_opts = ["-stream_loop", "-1"] if duration > 10 else []

        cmd = [
            "ffmpeg", "-y",
            *input_opts,
            "-i", str(file_path),
            "-vf", vf,
            "-af", f"afade=t=out:st={max(0,duration-0.5)}:d=0.5{atempo}" if atempo else f"afade=t=out:st={max(0,duration-0.5)}:d=0.5",
            "-t", str(duration),
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            "-pix_fmt", "yuv420p",
            str(out_path),
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)

        return str(out_path) if out_path.exists() else None

    # ── Concat ──────────────────────────────────────────────────────────────

    async def _concat_scenes(
        self,
        clips: List[str],
        work_dir: Path,
        fps: int,
    ) -> Optional[str]:
        """Soedinjaet sceny cherez concat demuxer."""
        concat_file = work_dir / "concat_list.txt"
        with open(concat_file, "w", encoding="utf-8") as f:
            for clip in clips:
                f.write(f"file '{Path(clip).as_posix()}'\n")

        out_path = work_dir / "concatenated.mp4"

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", str(concat_file),
            "-c", "copy",
            str(out_path),
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.wait_for(proc.communicate(), timeout=60)

        # Esli copy ne srabotal — pererenderim
        if not out_path.exists():
            cmd = [
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0",
                "-i", str(concat_file),
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-c:a", "aac", "-b:a", "128k",
                "-pix_fmt", "yuv420p",
                str(out_path),
            ]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await asyncio.wait_for(proc.communicate(), timeout=120)

        return str(out_path) if out_path.exists() else None

    # ── Captions ────────────────────────────────────────────────────────────

    async def _burn_captions(
        self,
        video_path: str,
        captions: List[Dict[str, Any]],
        work_dir: Path,
        target_size: Tuple[int, int],
    ) -> Optional[str]:
        """Nakladyvajet tekst na video (burned-in captions)."""
        # Sozdajem SRT fajl
        srt_path = work_dir / "captions.srt"
        srt_lines = []
        for i, cap in enumerate(captions, 1):
            start = cap.get("start", 0)
            duration = cap.get("duration", 3)
            end = start + duration
            text = cap.get("text", "")
            srt_lines.append(f"{i}")
            srt_lines.append(f"{self._sec_to_srt(start)} --> {self._sec_to_srt(end)}")
            srt_lines.append(text)
            srt_lines.append("")
        srt_path.write_text("\n".join(srt_lines), encoding="utf-8")

        out_path = work_dir / "captioned.mp4"

        # Stil teksta
        style = captions[0].get("style", "bold") if captions else "bold"
        fontcolor = {"glitch": "#ff0044", "neon": "#00ff88", "bold": "#ffffff"}.get(style, "#ffffff")
        bordercolor = "#000000"

        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vf", (
                f"subtitles={str(srt_path).replace('\\','/')}:force_style='"
                f"FontName=Arial,FontSize=72,PrimaryColour=&H00{fontcolor.lstrip('#')},"
                f"OutlineColour=&H00{bordercolor.lstrip('#')},Outline=4,"
                f"Alignment=2,MarginV=200'"
            ),
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "copy",
            str(out_path),
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.wait_for(proc.communicate(), timeout=120)

        return str(out_path) if out_path.exists() else None

    # ── Audio mixing ────────────────────────────────────────────────────────

    async def _mix_audio(
        self,
        video_path: str,
        sound_effects: List[str],
        music: Optional[str],
        work_dir: Path,
    ) -> Optional[str]:
        """Miksujet SFX + muzyku + video."""
        # Proverim chto est chto miksovat
        valid_sfx = [s for s in sound_effects if Path(s).exists()]
        has_music = music and Path(music).exists()

        if not valid_sfx and not has_music:
            return video_path  # Nichego delat ne nado

        out_path = work_dir / "mixed_audio.mp4"

        # Prostoj podhod: dobavit muzyku kak otdelnyj trek, SFX — vremenno propuskaem
        # (slozhnyj miksing s timeline trebujet filter_complex)
        if has_music and not valid_sfx:
            # Zamena audio na fonovuju muzyku
            cmd = [
                "ffmpeg", "-y",
                "-i", video_path,
                "-i", music,
                "-c:v", "copy",
                "-c:a", "aac", "-b:a", "128k",
                "-shortest",
                "-map", "0:v:0", "-map", "1:a:0",
                str(out_path),
            ]
        elif valid_sfx:
            # Konkatenirujem SFX v odin fajl i nakladyvajem
            sfx_concat = work_dir / "sfx_concat.txt"
            with open(sfx_concat, "w", encoding="utf-8") as f:
                for sfx in valid_sfx:
                    f.write(f"file '{Path(sfx).as_posix()}'\n")

            sfx_mixed = work_dir / "sfx_mixed.mp3"
            proc1 = await asyncio.create_subprocess_exec(
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", str(sfx_concat),
                "-c:a", "libmp3lame", "-q:a", "4",
                str(sfx_mixed),
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            await asyncio.wait_for(proc1.communicate(), timeout=60)

            if has_music:
                # Miksujem SFX + muzyka
                cmd = [
                    "ffmpeg", "-y",
                    "-i", video_path,
                    "-i", str(sfx_mixed),
                    "-i", music,
                    "-filter_complex", "[1:a][2:a]amix=inputs=2:duration=longest:weights='0.8 0.3'[aout]",
                    "-map", "0:v:0", "-map", "[aout]",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
                    "-shortest",
                    str(out_path),
                ]
            else:
                cmd = [
                    "ffmpeg", "-y",
                    "-i", video_path,
                    "-i", str(sfx_mixed),
                    "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "128k",
                    "-shortest",
                    "-map", "0:v:0", "-map", "1:a:0",
                    str(out_path),
                ]
        else:
            return video_path

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.wait_for(proc.communicate(), timeout=120)

        return str(out_path) if out_path.exists() else video_path

    # ── Effects ─────────────────────────────────────────────────────────────

    def add_effect(
        self,
        video_path: str,
        effect: str,
        work_dir: Path,
    ) -> Optional[str]:
        """Dobavljaet effekt k video."""
        if effect == "film_grain":
            return self._add_grain(video_path, work_dir)
        elif effect == "glow":
            return self._add_glow(video_path, work_dir)
        elif effect == "chromatic":
            return self._add_chromatic(video_path, work_dir)
        elif effect == "vignette":
            return self._add_vignette(video_path, work_dir)
        return None

    def _add_grain(self, video_path: str, work_dir: Path) -> Optional[str]:
        """Plenochyjnaja zernistost."""
        out = work_dir / "grain.mp4"
        vf = "noise=alls=20:allf=t+u,format=yuv420p"
        cmd = ["ffmpeg", "-y", "-i", video_path, "-vf", vf, "-c:a", "copy", str(out)]
        self._run_ffmpeg_sync(cmd)
        return str(out) if out.exists() else None

    def _add_glow(self, video_path: str, work_dir: Path) -> Optional[str]:
        """Majachij svet (blur + screen blend)."""
        out = work_dir / "glow.mp4"
        vf = "split[a][b];[b]boxblur=5:5[b2];[a][b2]blend=all_mode=screen,format=yuv420p"
        cmd = ["ffmpeg", "-y", "-i", video_path, "-vf", vf, "-c:a", "copy", str(out)]
        self._run_ffmpeg_sync(cmd)
        return str(out) if out.exists() else None

    def _add_chromatic(self, video_path: str, work_dir: Path) -> Optional[str]:
        """RGB split (chromatic aberration)."""
        out = work_dir / "chromatic.mp4"
        vf = "chromashift=cbh=-2:cbv=0:crh=2:crv=0,format=yuv420p"
        cmd = ["ffmpeg", "-y", "-i", video_path, "-vf", vf, "-c:a", "copy", str(out)]
        self._run_ffmpeg_sync(cmd)
        return str(out) if out.exists() else None

    def _add_vignette(self, video_path: str, work_dir: Path) -> Optional[str]:
        """Vinjetka (temnyje kraja)."""
        out = work_dir / "vignette.mp4"
        vf = "vignette=PI/4,format=yuv420p"
        cmd = ["ffmpeg", "-y", "-i", video_path, "-vf", vf, "-c:a", "copy", str(out)]
        self._run_ffmpeg_sync(cmd)
        return str(out) if out.exists() else None

    # ── Helpers ─────────────────────────────────────────────────────────────

    @staticmethod
    def _build_color_filter(grade: Dict[str, Any]) -> str:
        """Stroit ffmpeg vf dlja cvetokorrektsii."""
        parts = []

        brightness = grade.get("brightness", 0)
        contrast = grade.get("contrast", 1.0)
        saturation = grade.get("saturation", 1.0)
        gamma = grade.get("gamma", 1.0)

        # eq filter
        eq_params = []
        if brightness != 0:
            eq_params.append(f"brightness={brightness}")
        if contrast != 1.0:
            eq_params.append(f"contrast={contrast}")
        if saturation != 1.0:
            eq_params.append(f"saturation={saturation}")
        if gamma != 1.0:
            eq_params.append(f"gamma={gamma}")

        if eq_params:
            parts.append(f"eq={':'.join(eq_params)}")

        # Color cast
        color = grade.get("color", "")
        if color == "cool":
            parts.append("colorbalance=rs=0.05:gs=0.0:bs=0.1")
        elif color == "warm":
            parts.append("colorbalance=rs=0.1:gs=0.05:bs=-0.05")
        elif color == "neon":
            parts.append("colorbalance=rs=-0.05:gs=0.1:bs=0.1")
        elif color == "sepia":
            parts.append("colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131")

        return ",".join(parts) if parts else ""

    @staticmethod
    def _run_ffmpeg_sync(cmd: List[str]) -> None:
        import subprocess
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)

    @staticmethod
    def _sec_to_srt(seconds: float) -> str:
        """00:00:00,000 format."""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds % 1) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
