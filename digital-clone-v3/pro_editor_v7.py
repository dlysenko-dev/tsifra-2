#!/usr/bin/env python3
"""
Professional Video Editor v7 — FAST ffmpeg-only pipeline
- Static zoom per segment (random crop offset, no animation)
- Text via ffmpeg drawtext with Montserrat Bold
- Flash/glitch transitions
- Music + silent audio
- No PIL per-frame processing
"""

import os, sys, subprocess, random
from pathlib import Path
from typing import List, Tuple, Optional

PROJECT_ROOT = Path(__file__).parent
OUTPUT_DIR = PROJECT_ROOT / "output"
ASSETS_DIR = PROJECT_ROOT / "assets"
VIDEO_DIR = ASSETS_DIR / "videos"
SFX_DIR = ASSETS_DIR / "sfx"
TEMP_DIR = PROJECT_ROOT / "temp" / "pro_v7"
FFMPEG = "ffmpeg"
FFPROBE = "ffprobe"

W, H = 1080, 1920
FPS = 30

def run(cmd, capture=True):
    result = subprocess.run(cmd, capture_output=capture, text=True)
    if result.returncode != 0 and capture:
        print("[ERR]", result.stderr[-300:] if len(result.stderr)>300 else result.stderr)
    return result

def get_dur(path):
    r = run([FFPROBE,"-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(path)])
    try:
        return float(r.stdout.strip())
    except:
        return 3.0

def font_path() -> Path:
    p = ASSETS_DIR / "Montserrat-Bold.ttf"
    if p.exists():
        return p
    return Path("C:/Windows/Fonts/arial.ttf")

def detect_beats(music_path: Path) -> List[float]:
    try:
        import librosa
        y, sr = librosa.load(str(music_path), sr=None)
        _, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
        return list(librosa.frames_to_time(beat_frames, sr=sr))
    except Exception as e:
        print("[WARN] Beat detection failed:", e)
        return []

# ── Segment prep (ffmpeg only) ─────────────────────────────────────────────

def prepare_segment(src: Path, start: float, seg_dur: float, zoom_type: str, temp: Path) -> Path:
    out = temp / f"s{random.randint(10000,99999)}.mp4"
    
    # Random static zoom: scale up then crop different center
    z = 1.0
    if zoom_type == "in":
        z = random.uniform(1.1, 1.3)
    elif zoom_type == "out":
        z = random.uniform(1.0, 1.15)
    elif zoom_type == "pulse":
        z = random.uniform(1.05, 1.2)
    elif zoom_type == "quick":
        z = random.uniform(1.15, 1.4)
    
    # Random pan offset within zoom bounds
    max_off_x = int((1080 * z - 1080) / 2)
    max_off_y = int((1920 * z - 1920) / 2)
    off_x = random.randint(-max(1,max_off_x), max(1,max_off_x))
    off_y = random.randint(-max(1,max_off_y), max(1,max_off_y))
    
    # Build filter: crop to 9:16, scale with zoom, crop back to 1080x1920 with offset
    # scale=1080*z:1920*z then crop=1080:1920:offset_x:offset_y
    vf = f"crop=min(iw\\,ih*9/16):min(ih\\,iw*16/9):(iw-min(iw\\,ih*9/16))/2:(ih-min(ih\\,iw*16/9))/2," \
         f"scale={int(1080*z)}:{int(1920*z)}:flags=lanczos," \
         f"crop=1080:1920:{max(0, (int(1080*z)-1080)//2 + off_x)}:{max(0, (int(1920*z)-1920)//2 + off_y)}," \
         f"eq=contrast=1.12:brightness=0.01:saturation=1.08"
    
    run([FFMPEG, "-y", "-ss", str(start), "-t", str(seg_dur), "-i", str(src),
         "-vf", vf, "-r", str(FPS), "-an",
         "-c:v", "libx264", "-crf", "24", "-pix_fmt", "yuv420p", str(out)])
    
    if not out.exists() or out.stat().st_size < 1024:
        # Fallback
        run([FFMPEG, "-y", "-ss", str(start), "-t", str(seg_dur), "-i", str(src),
             "-vf", "scale=1080:1920:flags=lanczos", "-an",
             "-c:v", "libx264", "-crf", "24", "-pix_fmt", "yuv420p", str(out)])
    return out

# ── Transition clips ───────────────────────────────────────────────────────

def make_flash(temp: Path, color="white", duration=0.05) -> Path:
    out = temp / f"f{random.randint(1000,9999)}.mp4"
    run([FFMPEG, "-y", "-f", "lavfi", "-i", f"color=c={color}:s={W}x{H}:d={duration}",
         "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", str(out)])
    return out

def make_glitch(temp: Path) -> Path:
    out = temp / f"g{random.randint(1000,9999)}.mp4"
    run([FFMPEG, "-y", "-f", "lavfi", "-i", f"color=c=black:s={W}x{H}:d=0.08",
         "-vf", "geq=r='r(X-4,Y)':g='g(X,Y)':b='b(X+4,Y)',noise=alls=25:allf=t+u",
         "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", str(out)])
    return out

# ── Text overlay via drawtext ──────────────────────────────────────────────

def build_text_filters(texts: List[Tuple[float,float,str,str]], font: Path) -> str:
    """Build a complex drawtext filter chain with multiple texts."""
    # ffmpeg drawtext doesn't support multiple texts in one filter easily
    # We'll use overlay approach with generated PNGs per text - but faster than PIL seq
    # Actually, for static text (no animation) we can use drawtext with enable
    # For animated text, we still need frames. Let's compromise: use drawtext for static text
    # and simple fade-in via enable
    
    filters = []
    for start, dur, text, style in texts:
        # Escape colons and special chars in text
        safe_text = text.replace(":", "\\:").replace("'", "\\'")
        
        # Font size based on length
        fs = 110 if len(text) < 10 else 90 if len(text) < 15 else 70
        
        # Enable expression
        end = start + dur
        enable = f"between(t\\,{start}\\,{end})"
        
        # For simple fade-in effect, we can use expr with alpha
        # drawtext doesn't animate fontsize, but we can use fade with alpha
        # We'll use a simple static text with bold stroke
        
        f = (f"drawtext=fontfile=font.ttf:"
             f"text='{safe_text}':"
             f"fontcolor=white:"
             f"fontsize={fs}:"
             f"borderw=6:bordercolor=black:"
             f"x=(w-text_w)/2:y=(h-text_h)/2:"
             f"enable='{enable}'")
        filters.append(f)
    
    return ",".join(filters)

# ── CTA card ───────────────────────────────────────────────────────────────

def make_cta(duration: float, temp: Path, font: Path) -> Path:
    out = temp / f"cta{random.randint(1000,9999)}.mp4"
    
    # Use drawtext on black background
    vf = (f"drawtext=fontfile=font.ttf:"
          f"text='FOLLOW':fontcolor=white:fontsize=120:borderw=8:bordercolor=black:"
          f"x=(w-text_w)/2:y=(h-text_h)/2-100,"
          f"drawtext=fontfile=font.ttf:"
          f"text='FOR MORE':fontcolor=gray:fontsize=60:borderw=4:bordercolor=black:"
          f"x=(w-text_w)/2:y=(h-text_h)/2+80")
    
    run([FFMPEG, "-y", "-f", "lavfi", "-i", f"color=c=black:s={W}x{H}:d={duration}",
         "-vf", vf, "-c:v", "libx264", "-crf", "23", "-pix_fmt", "yuv420p", "-an", str(out)])
    return out

# ── Main render ─────────────────────────────────────────────────────────────

def render(output_path: Path, clips: List[Path], target_dur: float = 12.0,
           texts: Optional[List[Tuple[float,float,str,str]]] = None,
           music: Optional[Path] = None, cta: bool = True):
    
    temp = TEMP_DIR / "safe"
    temp.mkdir(parents=True, exist_ok=True)
    for f in temp.glob("*.mp4"):
        f.unlink()
    
    # Ensure font is in project root for relative path access
    proj_font = PROJECT_ROOT / "font.ttf"
    if not proj_font.exists():
        import shutil as sh
        sh.copy(str(font_path()), str(proj_font))
    font = proj_font
    
    beats = detect_beats(music) if music and music.exists() else []
    print(f"[INFO] Beats: {len(beats)}")
    
    zooms = ["in", "out", "pulse", "quick", "in", "none", "in"]
    segs = []
    total = 0
    i = 0
    beat_idx = 0
    
    while total < target_dur and i < 20:
        c = clips[i % len(clips)]
        d = get_dur(c)
        
        if beats and beat_idx < len(beats)-1:
            sd = min(2.0, max(0.5, beats[beat_idx+1] - beats[beat_idx]))
            beat_idx += 1
        else:
            sd = random.choice([0.7, 0.9, 1.1, 1.4, 1.6, 0.8])
        
        if total + sd > target_dur:
            sd = target_dur - total
        if sd < 0.3:
            break
        
        start = random.uniform(0.2, max(0.3, d - sd - 0.3))
        segs.append((c, start, sd, zooms[i % len(zooms)]))
        total += sd
        i += 1
    
    print(f"[INFO] {len(segs)} segments, ~{total:.1f}s")
    
    seg_files = []
    for i, (c, st, sd, zt) in enumerate(segs):
        print(f"  seg {i+1}: zoom={zt} dur={sd:.1f}s")
        p = prepare_segment(c, st, sd, zt, temp)
        seg_files.append(p)
    
    # Transitions
    flash_w = make_flash(temp, "white", 0.04)
    flash_b = make_flash(temp, "black", 0.05)
    glitch = make_glitch(temp)
    
    concat_txt = temp / "c.txt"
    cut_times = []
    ct = 0.0
    with open(concat_txt, "w") as f:
        for i, p in enumerate(seg_files):
            f.write(f"file '{p.name}'\n")
            sd = get_dur(p)
            ct += sd
            if i < len(seg_files) - 1:
                r = random.random()
                if r < 0.25:
                    f.write(f"file '{flash_w.name}'\n")
                    ct += 0.04
                elif r < 0.15:
                    f.write(f"file '{glitch.name}'\n")
                    ct += 0.08
                elif r < 0.15:
                    f.write(f"file '{flash_b.name}'\n")
                    ct += 0.05
                cut_times.append(ct)
    
    concat_vid = temp / "concat.mp4"
    run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_txt),
         "-c:v", "libx264", "-crf", "23", "-pix_fmt", "yuv420p", str(concat_vid)])
    
    current = concat_vid
    
    # Text overlays via drawtext
    if texts:
        text_vf = build_text_filters(texts, font)
        text_out = temp / "with_text.mp4"
        run([FFMPEG, "-y", "-i", str(current), "-vf", text_vf,
             "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p",
             "-c:a", "copy", str(text_out)])
        if text_out.exists():
            current = text_out
    
    # CTA
    if cta:
        cta_vid = make_cta(2.0, temp, font)
        cta_txt = temp / "cta_c.txt"
        with open(cta_txt, "w") as f:
            f.write(f"file '{current.name}'\n")
            f.write(f"file '{cta_vid.name}'\n")
        cta_out = temp / "with_cta.mp4"
        run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(cta_txt),
             "-c:v", "libx264", "-crf", "23", "-pix_fmt", "yuv420p", str(cta_out)])
        if cta_out.exists():
            current = cta_out
    
    # Add silent audio + SFX + music
    dur = get_dur(current)
    silent = temp / "silent.wav"
    run([FFMPEG, "-y", "-f", "lavfi", "-i", f"anullsrc=r=48000:cl=stereo", "-t", str(dur), str(silent)])
    
    # Build SFX mix
    sfx_files = [SFX_DIR / "whoosh.mp3", SFX_DIR / "hit_low.mp3", SFX_DIR / "pop_high.mp3"]
    sfx_files = [s for s in sfx_files if s.exists()]
    
    if cut_times and sfx_files:
        # Create SFX track
        sfx_inputs = "[0:a]"
        sfx_filters = []
        for i, t in enumerate(cut_times[:8]):  # max 8 SFX
            sfx = random.choice(sfx_files)
            delay = int(t * 1000)
            sfx_filters.append(f"[{i+1}:a]adelay={delay}|{delay},volume=0.35[s{i}]")
        
        if sfx_filters:
            sfx_filter = ";".join(sfx_filters)
            sfx_filter += f";{sfx_inputs}" + "".join(f"[s{i}]" for i in range(len(sfx_filters))) + f"amix=inputs={len(sfx_filters)+1}:duration=first[sfxout]"
            
            sfx_out = temp / "sfx_mix.wav"
            cmd = [FFMPEG, "-y", "-i", str(silent)]
            for _ in range(len(sfx_filters)):
                cmd.extend(["-i", str(random.choice(sfx_files))])
            cmd.extend(["-filter_complex", sfx_filter, "-map", "[sfxout]", str(sfx_out)])
            run(cmd)
        else:
            sfx_out = silent
    else:
        sfx_out = silent
    
    with_music = temp / "wm.mp4"
    if music and music.exists():
        run([FFMPEG, "-y", "-i", str(current), "-i", str(sfx_out), "-i", str(music),
             "-filter_complex",
             f"[2:a]volume=0.28,afade=t=in:ss=0:d=1,afade=t=out:st={max(0,dur-3)}:d=3[am];[1:a][am]amix=inputs=2:duration=first[aout]",
             "-map", "0:v", "-map", "[aout]",
             "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", str(with_music)])
    else:
        run([FFMPEG, "-y", "-i", str(current), "-i", str(sfx_out),
             "-shortest", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", str(with_music)])
    
    final = with_music if with_music.exists() else current
    run([FFMPEG, "-y", "-i", str(final),
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
        (0.2, 1.0, "THIS IS", "scale_in"),
        (1.5, 1.0, "PROFESSIONAL", "pop"),
        (3.5, 1.3, "EDITING", "slide_up"),
        (6.0, 1.1, "NOT A SLIDESHOW", "pop"),
    ]
    music = ASSETS_DIR / "music_epic.mp3"
    render(OUTPUT_DIR / "pro_v7_final.mp4", clips, target_dur=11.0,
           texts=texts, music=music if music.exists() else None, cta=True)
