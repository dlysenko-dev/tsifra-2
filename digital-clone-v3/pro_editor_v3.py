#!/usr/bin/env python3
"""
Professional Video Editor v3 — FAST version
Uses pre-extracted frames + PIL text + ffmpeg assembly for speed.
"""

import os, sys, subprocess, random, math, shutil
from pathlib import Path
from dataclasses import dataclass
from typing import List, Tuple, Optional
from PIL import Image, ImageDraw, ImageFont

PROJECT_ROOT = Path(__file__).parent
OUTPUT_DIR = PROJECT_ROOT / "output"
ASSETS_DIR = PROJECT_ROOT / "assets"
VIDEO_DIR = ASSETS_DIR / "videos"
TEMP_DIR = PROJECT_ROOT / "temp" / "pro_v3"
FFMPEG = "ffmpeg"
FFPROBE = "ffprobe"

W, H = 1080, 1920
FPS = 30

def run(cmd, capture=True):
    result = subprocess.run(cmd, capture_output=capture, text=True)
    if result.returncode != 0 and capture:
        print("[ERR]", result.stderr[-400:] if len(result.stderr) > 400 else result.stderr)
    return result

def get_dur(path):
    r = run([FFPROBE,"-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(path)])
    try:
        return float(r.stdout.strip())
    except:
        return 3.0

def font():
    for p in [ASSETS_DIR/"Montserrat-Bold.ttf", Path("C:/Windows/Fonts/impact.ttf"), Path("C:/Windows/Fonts/arial.ttf")]:
        if p.exists():
            return p
    return Path("C:/Windows/Fonts/arial.ttf")

# ── Fast clip prep: extract frames, apply zoom via crop, re-encode ──────────

def prepare_clip_fast(src: Path, start: float, seg_dur: float, zoom_type: str, temp: Path) -> Path:
    """Extract frames, apply animated crop for zoom, encode segment."""
    frames_dir = temp / f"f{random.randint(1000,9999)}"
    frames_dir.mkdir(parents=True, exist_ok=True)
    
    # Extract frames at 1080x1920 (crop+scale in one step)
    total_frames = int(seg_dur * FPS)
    
    # For zoom effect, we crop from a larger virtual canvas
    # zoom in = start with wider crop, end with tighter crop
    # zoom out = reverse
    # We do this by adjusting crop dimensions per frame
    
    # Extract original frames first (cropped to 9:16, scaled up slightly for zoom room)
    overscale = "scale=1200:2133:flags=lanczos"  # 10% oversize for zoom room
    crop = "crop=1080:1920:(iw-1080)/2:(ih-1920)/2"
    
    run([FFMPEG, "-y", "-ss", str(start), "-t", str(seg_dur), "-i", str(src),
         "-vf", f"{overscale},{crop}",
         "-r", str(FPS), "-pix_fmt", "rgb24",
         str(frames_dir / "%04d.png")])
    
    # Apply animated zoom by cropping extracted frames
    zoom_dir = temp / f"z{random.randint(1000,9999)}"
    zoom_dir.mkdir(parents=True, exist_ok=True)
    
    frame_files = sorted(frames_dir.glob("*.png"))
    n = len(frame_files)
    
    for i, fpath in enumerate(frame_files):
        t = i / n if n > 1 else 0
        img = Image.open(fpath)
        iw, ih = img.size  # Should be 1080x1920
        
        if zoom_type == "in":
            z = 1.0 + 0.15 * t  # 1.0 -> 1.15
        elif zoom_type == "out":
            z = 1.15 - 0.15 * t
        elif zoom_type == "pulse":
            z = 1.0 + 0.08 * math.sin(t * math.pi * 2)
        else:
            z = 1.0
        
        # Crop from center with zoom
        cw, ch = int(iw / z), int(ih / z)
        cx, cy = (iw - cw) // 2, (ih - ch) // 2
        
        if z > 1.0:
            img = img.crop((cx, cy, cx + cw, cy + ch)).resize((iw, ih), Image.LANCZOS)
        
        # Color grade (fast PIL)
        # Simple contrast + saturation using point transforms
        # We'll skip complex curves for speed and do eq in ffmpeg final pass
        img.save(zoom_dir / f"{i:04d}.png")
    
    # Encode segment
    out = temp / f"s{random.randint(1000,9999)}.mp4"
    run([FFMPEG, "-y", "-framerate", str(FPS), "-i", str(zoom_dir / "%04d.png"),
         "-vf", "eq=contrast=1.15:saturation=1.1",
         "-c:v", "libx264", "-crf", "26", "-pix_fmt", "yuv420p", "-an",
         str(out)])
    
    # Cleanup frames
    shutil.rmtree(frames_dir, ignore_errors=True)
    shutil.rmtree(zoom_dir, ignore_errors=True)
    
    return out

# ── Text overlay as PNG sequence ────────────────────────────────────────────

def make_text_frames(text: str, duration: float, style: str, temp: Path) -> Path:
    font_path = font()
    base = ImageFont.truetype(str(font_path), 120)
    
    frames_dir = temp / f"t{abs(hash(text))%100000:05d}"
    frames_dir.mkdir(parents=True, exist_ok=True)
    for f in frames_dir.glob("*.png"):
        f.unlink()
    
    n = max(1, int(duration * FPS))
    W, H = 1080, 1920
    
    # Word wrap
    test_draw = ImageDraw.Draw(Image.new("RGBA", (1,1)))
    words = text.split()
    lines = []
    cur = ""
    mw = W - 100
    for w in words:
        test = cur + " " + w if cur else w
        bb = test_draw.textbbox((0,0), test, font=base)
        if bb[2]-bb[0] > mw and cur:
            lines.append(cur)
            cur = w
        else:
            cur = test
    if cur:
        lines.append(cur)
    txt = "\n".join(lines)
    
    for i in range(n):
        t = i/n if n>1 else 1.0
        img = Image.new("RGBA", (W,H), (0,0,0,0))
        
        if style == "scale_in":
            sc = 0.3 + 0.7*(1-math.exp(-5*t))
            alpha = int(255*min(1.0, t*2.5))
        elif style == "pop":
            sc = 1.0 + 0.15*math.sin(t*math.pi*3) if t<0.4 else 1.0
            alpha = 255
        else:
            sc = 1.0
            alpha = int(255*min(1.0, t*3))
        
        fs = max(28, int(120*sc))
        try:
            fnt = ImageFont.truetype(str(font_path), fs)
        except:
            fnt = base
        
        draw = ImageDraw.Draw(img)
        bb = draw.textbbox((0,0), txt, font=fnt)
        tw, th = bb[2]-bb[0], bb[3]-bb[1]
        x = (W-tw)//2
        y = (H-th)//2
        
        sw = max(3, int(fs*0.07))
        for dx in range(-sw, sw+1):
            for dy in range(-sw, sw+1):
                if dx*dx+dy*dy <= sw*sw+1:
                    draw.text((x+dx,y+dy), txt, font=fnt, fill=(0,0,0,alpha))
        draw.text((x,y), txt, font=fnt, fill=(255,255,255,alpha))
        
        img.save(frames_dir / f"{i:04d}.png")
    
    return frames_dir

# ── Main render ─────────────────────────────────────────────────────────────

def render(output_path: Path, clips: List[Path], target_dur: float = 10.0,
           texts: Optional[List[Tuple[float,float,str,str]]] = None,
           music: Optional[Path] = None):
    
    temp = TEMP_DIR / "safe"
    temp.mkdir(parents=True, exist_ok=True)
    # Clean old
    for f in temp.glob("*.mp4"):
        f.unlink()
    for d in temp.glob("f*"):
        shutil.rmtree(d, ignore_errors=True)
    for d in temp.glob("t*"):
        shutil.rmtree(d, ignore_errors=True)
    
    seg_dur = 1.3
    n_segs = max(4, int(target_dur / seg_dur))
    zooms = ["in","out","pulse","in","none","in"]
    
    segs = []
    for i in range(n_segs):
        c = clips[i % len(clips)]
        duration = get_dur(c)
        start = random.uniform(0.2, max(0.3, duration-seg_dur-0.3))
        segs.append((c, start, seg_dur, random.choice(zooms)))
    
    print(f"[INFO] Preparing {len(segs)} segments...")
    seg_files = []
    for i, (c, st, sd, zt) in enumerate(segs):
        print(f"  seg {i+1}/{len(segs)} zoom={zt}")
        p = prepare_clip_fast(c, st, sd, zt, temp)
        seg_files.append(p)
    
    # Flash transitions
    flash = temp / "flash_w.mp4"
    bflash = temp / "flash_b.mp4"
    run([FFMPEG, "-y", "-f", "lavfi", "-i", f"color=c=white:s={W}x{H}:d=0.05",
         "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", str(flash)])
    run([FFMPEG, "-y", "-f", "lavfi", "-i", f"color=c=black:s={W}x{H}:d=0.06",
         "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", str(bflash)])
    
    # Concat
    concat_txt = temp / "c.txt"
    with open(concat_txt, "w") as f:
        for i, p in enumerate(seg_files):
            f.write(f"file '{p.name}'\n")
            if i < len(seg_files)-1:
                r = random.random()
                if r < 0.25:
                    f.write(f"file '{flash.name}'\n")
                elif r < 0.15:
                    f.write(f"file '{bflash.name}'\n")
    
    concat_vid = temp / "concat.mp4"
    run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_txt),
         "-c:v", "libx264", "-crf", "23", "-pix_fmt", "yuv420p", str(concat_vid)])
    
    current = concat_vid
    
    # Text overlays
    if texts:
        for idx, (start, dur, txt, style) in enumerate(texts):
            d = make_text_frames(txt, dur, style, temp)
            tv = temp / f"tv{idx}.mp4"
            run([FFMPEG, "-y", "-framerate", str(FPS), "-i", f"{d}/%04d.png",
                 "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", str(tv)])
            
            outv = temp / f"ov{idx}.mp4"
            run([FFMPEG, "-y", "-i", str(current), "-i", str(tv),
                 "-filter_complex",
                 f"[1:v]colorkey=color=black:similarity=0.02:blend=0[txt];[0:v][txt]overlay=0:0:enable='between(t\\,{start}\\,{start+dur})'[v]",
                 "-map", "[v]", "-map", "0:a?",
                 "-c:v", "libx264", "-crf", "23", "-pix_fmt", "yuv420p",
                 str(outv)])
            if outv.exists():
                current = outv
    
    # Music
    if music and music.exists():
        duration = get_dur(current)
        mv = temp / "final_music.mp4"
        run([FFMPEG, "-y", "-i", str(current), "-i", str(music),
             "-filter_complex",
             f"[1:a]volume=0.3,afade=t=in:ss=0:d=1,afade=t=out:st={max(0,duration-2.5)}:d=2.5[am];[0:a][am]amix=inputs=2:duration=first[aout]",
             "-map", "0:v", "-map", "[aout]",
             "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", str(mv)])
        if mv.exists():
            current = mv
    
    # Final
    run([FFMPEG, "-y", "-i", str(current),
         "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "192k",
         str(output_path)])
    
    sz = output_path.stat().st_size/1024/1024 if output_path.exists() else 0
    print(f"[DONE] {output_path} ({sz:.1f} MB)")
    return output_path

# ── Run ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    clips = list(VIDEO_DIR.glob("mixkit_*.mp4"))
    if not clips:
        clips = list(VIDEO_DIR.glob("*.mp4"))
    if not clips:
        print("[ERR] No clips")
        sys.exit(1)
    
    print(f"[INFO] {len(clips)} clips")
    texts = [
        (0.3, 1.0, "THIS IS", "scale_in"),
        (1.8, 1.0, "PROFESSIONAL", "pop"),
        (4.0, 1.5, "EDITING", "scale_in"),
        (6.5, 1.2, "NOT A SLIDESHOW", "pop"),
    ]
    music = ASSETS_DIR / "music_epic.mp3"
    render(OUTPUT_DIR / "pro_v3_final.mp4", clips, target_dur=10.0,
           texts=texts, music=music if music.exists() else None)
