#!/usr/bin/env python3
"""
Professional Video Editor v2
Replicates YoEdit0r / Merzliakov / Gadzhi style editing.
"""

import os, sys, subprocess, random, math, json, tempfile, textwrap, shutil
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Tuple, Optional
from PIL import Image, ImageDraw, ImageFont

# ── Config ──────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent
OUTPUT_DIR = PROJECT_ROOT / "output"
ASSETS_DIR = PROJECT_ROOT / "assets"
VIDEO_DIR = ASSETS_DIR / "videos"
TEMP_DIR = PROJECT_ROOT / "temp" / "pro_v2"
FFMPEG = "ffmpeg"
FFPROBE = "ffprobe"

TARGET_W, TARGET_H = 1080, 1920
FPS = 30
CRF = 20

# ── Utilities ───────────────────────────────────────────────────────────────

def run(cmd: list, capture=True):
    print("[RUN]", " ".join(str(c) for c in cmd)[:200], "..." if len(str(cmd)) > 200 else "")
    result = subprocess.run(cmd, capture_output=capture, text=True)
    if result.returncode != 0 and capture:
        print("[ERR]", result.stderr[-600:] if len(result.stderr) > 600 else result.stderr)
    return result

def get_duration(path: Path) -> float:
    r = run([FFPROBE, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)])
    try:
        return float(r.stdout.strip())
    except:
        return 5.0

def ensure_font() -> Path:
    font_path = ASSETS_DIR / "Montserrat-Bold.ttf"
    if font_path.exists():
        return font_path
    for name in ["impact", "Impact", "arial", "Arial"]:
        p = Path(f"C:/Windows/Fonts/{name}.ttf")
        if p.exists():
            return p
    # Try download
    url = "https://github.com/JulietaUla/Montserrat/raw/master/fonts/ttf/Montserrat-Bold.ttf"
    try:
        import urllib.request
        urllib.request.urlretrieve(url, str(font_path))
        if font_path.exists():
            return font_path
    except Exception as e:
        print("[WARN] Font download failed:", e)
    return Path("C:/Windows/Fonts/arial.ttf")

# ── Text Frame Generator (PIL) ─────────────────────────────────────────────

class TextAnimator:
    def __init__(self, font_path: Path, output_dir: Path):
        self.font_path = font_path
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.base_font = ImageFont.truetype(str(font_path), 120)

    def render_text_animation(self, text: str, duration: float, style: str = "scale_in") -> Path:
        frames_dir = self.output_dir / f"txt_{abs(hash(text)) % 100000:05d}"
        frames_dir.mkdir(parents=True, exist_ok=True)
        
        # Clean old frames
        for f in frames_dir.glob("*.png"):
            f.unlink()
        
        total_frames = max(1, int(duration * FPS))
        W, H = TARGET_W, TARGET_H
        
        # Word wrap
        max_width = W - 120
        words = text.split()
        lines = []
        current = ""
        test_draw = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
        for w in words:
            test = current + " " + w if current else w
            bbox = test_draw.textbbox((0, 0), test, font=self.base_font)
            if bbox[2] - bbox[0] > max_width and current:
                lines.append(current)
                current = w
            else:
                current = test
        if current:
            lines.append(current)
        text_to_draw = "\n".join(lines)
        
        for i in range(total_frames):
            t = i / total_frames if total_frames > 1 else 1.0
            img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            
            if style == "scale_in":
                scale = 0.2 + 0.8 * (1 - math.exp(-5 * t))
                alpha = int(255 * min(1.0, t * 2))
            elif style == "pop":
                if t < 0.3:
                    scale = 0.2 + 2.5 * t
                elif t < 0.5:
                    scale = 0.95 + 0.2 * math.sin((t - 0.3) * math.pi / 0.2)
                else:
                    scale = 1.0
                alpha = 255
            elif style == "slide_up":
                scale = 1.0
                alpha = int(255 * min(1.0, t * 3))
            else:
                scale = 1.0
                alpha = 255
            
            font_size = max(24, int(120 * scale))
            try:
                font = ImageFont.truetype(str(self.font_path), font_size)
            except:
                font = self.base_font
            
            draw = ImageDraw.Draw(img)
            bbox = draw.textbbox((0, 0), text_to_draw, font=font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            x = (W - tw) // 2
            y = (H - th) // 2
            
            if style == "slide_up":
                y = int(H * 0.75 - (H * 0.15) * (1 - math.exp(-5 * t)) - th / 2)
            
            # Stroke
            stroke_w = max(3, int(font_size * 0.07))
            for dx in range(-stroke_w, stroke_w + 1):
                for dy in range(-stroke_w, stroke_w + 1):
                    if dx * dx + dy * dy <= stroke_w * stroke_w + 1:
                        draw.text((x + dx, y + dy), text_to_draw, font=font, fill=(0, 0, 0, alpha))
            
            # Fill
            draw.text((x, y), text_to_draw, font=font, fill=(255, 255, 255, alpha))
            
            # Shadow
            shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            sd = ImageDraw.Draw(shadow)
            off = max(2, stroke_w // 2)
            sd.text((x + off, y + off), text_to_draw, font=font, fill=(0, 0, 0, int(alpha * 0.35)))
            img = Image.alpha_composite(shadow, img)
            
            img.save(frames_dir / f"{i:04d}.png")
        
        return frames_dir

# ── Video Effects Engine ────────────────────────────────────────────────────

@dataclass
class Segment:
    video_path: Path
    start: float = 0.0
    duration: float = 2.0
    zoom_type: str = "in"
    speed: float = 1.0
    glitch: bool = False

class EffectEngine:
    def __init__(self, temp_dir: Path):
        self.temp_dir = temp_dir
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.counter = 0
        # Use ASCII-only temp dir for ffmpeg concat
        self.safe_dir = self.temp_dir / "safe"
        self.safe_dir.mkdir(parents=True, exist_ok=True)
    
    def _tmp(self, suffix: str) -> Path:
        self.counter += 1
        # Use safe ASCII path
        return self.safe_dir / f"s{self.counter:04d}{suffix}"
    
    def prepare_clip(self, seg: Segment) -> Path:
        out = self._tmp(".mp4")
        
        # zoompan d must be integer frames
        d_frames = max(1, int(seg.duration * FPS))
        
        if seg.zoom_type == "in":
            zoom_expr = "min(zoom+0.0025,1.35)"
        elif seg.zoom_type == "out":
            zoom_expr = "max(zoom-0.0025,1.0)"
        elif seg.zoom_type == "pulse":
            zoom_expr = "1.0+0.12*sin(2*PI*t/2)"
        else:
            zoom_expr = "1.0"
        
        # Build filter: crop -> scale -> zoompan -> color
        crop = f"crop=min(iw\\,ih*9/16):min(ih\\,iw*16/9):(iw-min(iw\\,ih*9/16))/2:(ih-min(ih\\,iw*16/9))/2"
        scale = "scale=1080:1920:flags=lanczos"
        color = "eq=contrast=1.15:brightness=0.02:saturation=1.15"
        curves = "curves=r='0/0 0.5/0.55 1/1':g='0/0 0.5/0.52 1/1':b='0/0 0.5/0.48 1/1'"
        
        filters = [crop, scale]
        if seg.zoom_type != "none":
            filters.append(
                f"zoompan=z='{zoom_expr}':d={d_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920"
            )
        filters.extend([color, curves])
        if seg.glitch:
            filters.append("geq=r='r(X-3,Y)':g='g(X,Y)':b='b(X+3,Y)',noise=alls=10:allf=t+u")
        
        vf = ",".join(filters)
        
        cmd = [
            FFMPEG, "-y",
            "-ss", str(seg.start),
            "-t", str(seg.duration),
            "-i", str(seg.video_path),
            "-vf", vf,
            "-r", str(FPS),
            "-an",
            "-c:v", "libx264", "-crf", str(CRF), "-pix_fmt", "yuv420p",
            str(out)
        ]
        
        if seg.speed != 1.0:
            # Can't use -vf twice; append to filter_complex later or use setpts in vf
            # For simplicity, skip speed change for now or do second pass
            pass
        
        r = run(cmd)
        if r.returncode != 0 or not out.exists() or out.stat().st_size < 1024:
            print("[FALLBACK] Basic scale only")
            run([FFMPEG, "-y", "-ss", str(seg.start), "-t", str(seg.duration),
                 "-i", str(seg.video_path),
                 "-vf", "scale=1080:1920:flags=lanczos",
                 "-an", "-c:v", "libx264", "-crf", str(CRF), "-pix_fmt", "yuv420p",
                 str(out)])
        return out
    
    def create_flash(self, color_name="white") -> Path:
        out = self._tmp(f"_{color_name}.mp4")
        run([FFMPEG, "-y", "-f", "lavfi",
             "-i", f"color=c={color_name}:s={TARGET_W}x{TARGET_H}:d=0.05",
             "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
             str(out)])
        return out

# ── Main Pipeline ───────────────────────────────────────────────────────────

class ProEditor:
    def __init__(self):
        self.temp_dir = TEMP_DIR
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.fx = EffectEngine(self.temp_dir)
        font_path = ensure_font()
        self.text_anim = TextAnimator(font_path, self.temp_dir / "text_frames")
        self.segments: List[Segment] = []
    
    def add_segments_from_clips(self, clips: List[Path], target_duration: float = 15.0):
        seg_dur = 1.5
        num = max(4, int(target_duration / seg_dur))
        zooms = ["in", "out", "pulse", "in", "none", "in"]
        for i in range(num):
            clip = clips[i % len(clips)]
            dur = get_duration(clip)
            start = random.uniform(0.2, max(0.3, dur - seg_dur - 0.3))
            self.segments.append(Segment(
                video_path=clip,
                start=start,
                duration=seg_dur,
                zoom_type=random.choice(zooms),
                speed=1.0,
                glitch=random.random() < 0.1
            ))
    
    def render(self, output_path: Path,
               texts: Optional[List[Tuple[float, float, str, str]]] = None,
               music_path: Optional[Path] = None):
        print(f"[INFO] Rendering {len(self.segments)} segments")
        
        # Prepare clips
        prepared = []
        for i, seg in enumerate(self.segments):
            print(f"[SEG {i+1}/{len(self.segments)}] zoom={seg.zoom_type} glitch={seg.glitch}")
            p = self.fx.prepare_clip(seg)
            prepared.append(p)
        
        # Concat with flashes
        safe_dir = self.fx.safe_dir
        concat_txt = safe_dir / "concat.txt"
        flash = self.fx.create_flash("white")
        bflash = self.fx.create_flash("black")
        
        with open(concat_txt, "w", encoding="utf-8") as f:
            for i, p in enumerate(prepared):
                f.write(f"file '{p.name}'\n")
                if i < len(prepared) - 1:
                    r = random.random()
                    if r < 0.25:
                        f.write(f"file '{flash.name}'\n")
                    elif r < 0.15:
                        f.write(f"file '{bflash.name}'\n")
        
        concat_vid = safe_dir / "concat.mp4"
        run([FFMPEG, "-y", "-f", "concat", "-safe", "0",
             "-i", str(concat_txt),
             "-c:v", "libx264", "-crf", str(CRF), "-pix_fmt", "yuv420p",
             str(concat_vid)])
        
        if not concat_vid.exists():
            print("[ERR] Concat failed")
            return None
        
        # Text overlays
        final_vid = concat_vid
        if texts:
            text_inputs = []
            for idx, (start, dur, txt, style) in enumerate(texts):
                d = self.text_anim.render_text_animation(txt, dur, style)
                tvid = safe_dir / f"t{idx}.mp4"
                run([FFMPEG, "-y", "-framerate", str(FPS),
                     "-i", f"{d}/%04d.png",
                     "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
                     str(tvid)])
                text_inputs.append((start, dur, tvid))
            
            # Overlay each text video
            current = concat_vid
            for idx, (start, dur, tvid) in enumerate(text_inputs):
                outv = safe_dir / f"ovl{idx}.mp4"
                run([FFMPEG, "-y",
                     "-i", str(current), "-i", str(tvid),
                     "-filter_complex",
                     f"[1:v]format=rgba[txt]; [0:v][txt]overlay=0:0:enable='between(t\\,{start}\\,{start+dur})'[v]",
                     "-map", "[v]", "-map", "0:a?",
                     "-c:v", "libx264", "-crf", str(CRF), "-pix_fmt", "yuv420p",
                     str(outv)])
                if outv.exists():
                    current = outv
            final_vid = current
        
        # Music
        if music_path and music_path.exists():
            mus_out = safe_dir / "music.mp4"
            dur = get_duration(final_vid)
            run([FFMPEG, "-y",
                 "-i", str(final_vid), "-i", str(music_path),
                 "-filter_complex",
                 f"[1:a]volume=0.3,afade=t=in:ss=0:d=1,afade=t=out:st={max(0,dur-3)}:d=3[am]; [0:a][am]amix=inputs=2:duration=first[aout]",
                 "-map", "0:v", "-map", "[aout]",
                 "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                 str(mus_out)])
            if mus_out.exists():
                final_vid = mus_out
        
        # Final copy
        run([FFMPEG, "-y", "-i", str(final_vid),
             "-c:v", "libx264", "-crf", str(CRF), "-pix_fmt", "yuv420p",
             "-c:a", "aac", "-b:a", "192k",
             str(output_path)])
        
        sz = output_path.stat().st_size / 1024 / 1024 if output_path.exists() else 0
        print(f"[DONE] {output_path} ({sz:.1f} MB)")
        return output_path

# ── Demo ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    editor = ProEditor()
    clips = list(VIDEO_DIR.glob("mixkit_*.mp4"))
    if not clips:
        clips = list(VIDEO_DIR.glob("*.mp4"))
    if not clips:
        print("[ERR] No clips in", VIDEO_DIR)
        sys.exit(1)
    
    print(f"[INFO] {len(clips)} clips available")
    editor.add_segments_from_clips(clips, target_duration=12.0)
    
    texts = [
        (0.3, 1.2, "THIS IS", "scale_in"),
        (2.0, 1.2, "PROFESSIONAL", "pop"),
        (4.5, 1.8, "EDITING", "slide_up"),
        (7.5, 1.5, "NOT A SLIDESHOW", "pop"),
    ]
    
    music = ASSETS_DIR / "music_epic.mp3"
    out = OUTPUT_DIR / "pro_v2_final.mp4"
    editor.render(out, texts=texts, music_path=music if music.exists() else None)
