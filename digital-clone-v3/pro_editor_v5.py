#!/usr/bin/env python3
"""
Professional Video Editor v5
- Beat-sync cuts via librosa
- Zoom transitions between clips
- Background box for text readability
- Improved color grading
- Faster pipeline (reduce PIL ops)
"""

import os, sys, subprocess, random, math, shutil
from pathlib import Path
from typing import List, Tuple, Optional
from PIL import Image, ImageDraw, ImageFont

PROJECT_ROOT = Path(__file__).parent
OUTPUT_DIR = PROJECT_ROOT / "output"
ASSETS_DIR = PROJECT_ROOT / "assets"
VIDEO_DIR = ASSETS_DIR / "videos"
SFX_DIR = ASSETS_DIR / "sfx"
TEMP_DIR = PROJECT_ROOT / "temp" / "pro_v5"
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

def font():
    p = ASSETS_DIR / "Montserrat-Bold.ttf"
    if p.exists():
        return p
    return Path("C:/Windows/Fonts/arial.ttf")

# ── Beat Detection ─────────────────────────────────────────────────────────

def detect_beats(music_path: Path) -> List[float]:
    try:
        import librosa
        y, sr = librosa.load(str(music_path), sr=None)
        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
        beat_times = librosa.frames_to_time(beat_frames, sr=sr)
        return list(beat_times)
    except Exception as e:
        print("[WARN] Beat detection failed:", e)
        return []

# ── Clip prep (ffmpeg only, no PIL per frame) ──────────────────────────────

def prepare_clip_fast(src: Path, start: float, seg_dur: float, zoom_type: str, 
                      temp: Path, end_zoom: bool = False) -> Path:
    """Use ffmpeg zoompan for zoom; much faster than PIL per-frame."""
    out = temp / f"s{random.randint(10000,99999)}.mp4"
    d_frames = max(1, int(seg_dur * FPS))
    
    # zoompan: t = frame number (0-based), d = total frames
    # Normalized time = t/d
    if zoom_type == "in":
        z = "min(zoom+0.003,1.35)"
    elif zoom_type == "out":
        z = "max(zoom-0.003,1.0)"
    elif zoom_type == "pulse":
        z = f"1.0+0.1*sin(2*PI*t/{d_frames})"
    elif zoom_type == "quick":
        z = f"1.0+0.2*sin(PI*t/{max(1,int(d_frames/2))})" if seg_dur <= 1.0 else f"1.0+0.15*sin(2*PI*t/{d_frames})"
    else:
        z = "1.0"
    
    # If end_zoom, zoom in aggressively at end for transition
    if end_zoom:
        z = f"1.0+0.3*pow(t/{d_frames},2)"
    
    crop = f"crop=min(iw\\,ih*9/16):min(ih\\,iw*16/9):(iw-min(iw\\,ih*9/16))/2:(ih-min(ih\\,iw*16/9))/2"
    scale = "scale=1080:1920:flags=lanczos"
    zoom = f"zoompan=z='{z}':d={d_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920"
    color = "eq=contrast=1.12:brightness=0.01:saturation=1.08"
    
    vf = f"{crop},{scale},{zoom},{color}"
    
    run([FFMPEG, "-y", "-ss", str(start), "-t", str(seg_dur), "-i", str(src),
         "-vf", vf, "-r", str(FPS), "-an",
         "-c:v", "libx264", "-crf", "26", "-pix_fmt", "yuv420p", str(out)])
    
    if not out.exists() or out.stat().st_size < 1024:
        run([FFMPEG, "-y", "-ss", str(start), "-t", str(seg_dur), "-i", str(src),
             "-vf", "scale=1080:1920:flags=lanczos", "-an",
             "-c:v", "libx264", "-crf", "26", "-pix_fmt", "yuv420p", str(out)])
    return out

# ── Transition effects ─────────────────────────────────────────────────────

def make_zoom_transition(temp: Path) -> Path:
    """White flash with radial zoom blur effect."""
    out = temp / f"tr{random.randint(1000,9999)}.mp4"
    run([FFMPEG, "-y", "-f", "lavfi",
         "-i", f"color=c=white:s={W}x{H}:d=0.08",
         "-vf", "zoompan=z='1.0+2.0*t/0.08':d=3:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920",
         "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", str(out)])
    return out

def make_glitch_transition(temp: Path) -> Path:
    out = temp / f"tr{random.randint(1000,9999)}.mp4"
    run([FFMPEG, "-y", "-f", "lavfi",
         "-i", f"color=c=black:s={W}x{H}:d=0.1",
         "-vf", "geq=r='r(X-5,Y)':g='g(X,Y)':b='b(X+5,Y)',noise=alls=30:allf=t+u",
         "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", str(out)])
    return out

# ── Text with background box ───────────────────────────────────────────────

def make_text_frames(text: str, duration: float, style: str, temp: Path) -> Path:
    font_path = font()
    base = ImageFont.truetype(str(font_path), 120)
    
    d = temp / f"t{abs(hash(text))%100000:05d}"
    d.mkdir(parents=True, exist_ok=True)
    for f in d.glob("*.png"):
        f.unlink()
    
    n = max(1, int(duration * FPS))
    W, H = 1080, 1920
    
    # Word wrap
    td = ImageDraw.Draw(Image.new("RGBA", (1,1)))
    words = text.split()
    lines = []
    cur = ""
    mw = W - 100
    for w in words:
        test = cur + " " + w if cur else w
        bb = td.textbbox((0,0), test, font=base)
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
            sc = 0.3 + 0.7*(1-math.exp(-6*t))
            alpha = int(255*min(1.0, t*3))
        elif style == "pop":
            if t < 0.25:
                sc = 0.3 + 3.0*t
            elif t < 0.45:
                sc = 1.05 - 0.15*math.sin((t-0.25)*math.pi/0.2)
            else:
                sc = 1.0
            alpha = 255
        elif style == "slide_up":
            sc = 1.0
            alpha = int(255*min(1.0, t*3.5))
        else:
            sc = 1.0
            alpha = 255
        
        fs = max(36, int(120*sc))
        try:
            fnt = ImageFont.truetype(str(font_path), fs)
        except:
            fnt = base
        
        draw = ImageDraw.Draw(img)
        bb = draw.textbbox((0,0), txt, font=fnt)
        tw, th = bb[2]-bb[0], bb[3]-bb[1]
        x = (W-tw)//2
        y = (H-th)//2
        
        if style == "slide_up":
            y = int(H*0.7 - (H*0.15)*(1-math.exp(-6*t)) - th/2)
        
        # Background box for readability
        pad_x, pad_y = int(fs*0.4), int(fs*0.25)
        box_alpha = int(180 * (alpha/255))
        box_coords = [x - pad_x, y - pad_y, x + tw + pad_x, y + th + pad_y]
        # Rounded rect approximation
        draw.rectangle(box_coords, fill=(0, 0, 0, box_alpha))
        
        # Stroke
        sw = max(4, int(fs*0.08))
        for dx in range(-sw, sw+1):
            for dy in range(-sw, sw+1):
                if dx*dx+dy*dy <= sw*sw+1:
                    draw.text((x+dx,y+dy), txt, font=fnt, fill=(0,0,0,alpha))
        
        draw.text((x,y), txt, font=fnt, fill=(255,255,255,alpha))
        
        img.save(d / f"{i:04d}.png")
    
    return d

# ── CTA card ───────────────────────────────────────────────────────────────

def make_cta(duration: float, temp: Path) -> Path:
    d = temp / "cta"
    d.mkdir(parents=True, exist_ok=True)
    n = int(duration * FPS)
    fnt = ImageFont.truetype(str(font()), 100)
    fnt2 = ImageFont.truetype(str(font()), 48)
    
    for i in range(n):
        t = i/n
        img = Image.new("RGB", (W,H), (12,12,12))
        draw = ImageDraw.Draw(img)
        
        txt1 = "FOLLOW"
        bb = draw.textbbox((0,0), txt1, font=fnt)
        tw, th = bb[2]-bb[0], bb[3]-bb[1]
        x, y = (W-tw)//2, H//3 - th//2
        for dx in range(-6, 7):
            for dy in range(-6, 7):
                if dx*dx+dy*dy <= 37:
                    draw.text((x+dx,y+dy), txt1, font=fnt, fill=(0,0,0))
        draw.text((x,y), txt1, font=fnt, fill=(255,255,255))
        
        txt2 = "FOR MORE"
        bb2 = draw.textbbox((0,0), txt2, font=fnt2)
        draw.text(((W-(bb2[2]-bb2[0]))//2, H//2+60), txt2, font=fnt2, fill=(180,180,180))
        
        img.save(d / f"{i:04d}.png")
    
    out = temp / "cta.mp4"
    run([FFMPEG, "-y", "-framerate", str(FPS), "-i", str(d / "%04d.png"),
         "-c:v", "libx264", "-crf", "23", "-pix_fmt", "yuv420p", "-an", str(out)])
    return out

# ── Main render ─────────────────────────────────────────────────────────────

def render(output_path: Path, clips: List[Path], target_dur: float = 12.0,
           texts: Optional[List[Tuple[float,float,str,str]]] = None,
           music: Optional[Path] = None, cta: bool = True):
    
    temp = TEMP_DIR / "safe"
    temp.mkdir(parents=True, exist_ok=True)
    for f in temp.glob("*.mp4"):
        f.unlink()
    
    # Detect beats from music
    beats = []
    if music and music.exists():
        beats = detect_beats(music)
        print(f"[INFO] Detected {len(beats)} beats")
    
    # Build segments
    # Use beat times to determine cut points if available
    zooms = ["in", "out", "pulse", "quick", "in", "none", "in"]
    
    segs = []
    total = 0
    i = 0
    beat_idx = 0
    
    while total < target_dur and i < 20:
        c = clips[i % len(clips)]
        d = get_dur(c)
        
        # Duration: use beat interval or random 0.7-1.8
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
        end_zoom = (i < 20)  # zoom at end for transition feel
        segs.append((c, start, sd, zooms[i % len(zooms)], end_zoom))
        total += sd
        i += 1
    
    print(f"[INFO] {len(segs)} segments, ~{total:.1f}s")
    
    seg_files = []
    for i, (c, st, sd, zt, ez) in enumerate(segs):
        print(f"  seg {i+1}: zoom={zt} dur={sd:.1f}s end_zoom={ez}")
        p = prepare_clip_fast(c, st, sd, zt, temp, ez)
        seg_files.append(p)
    
    # Transitions
    flash = make_zoom_transition(temp)
    glitch = make_glitch_transition(temp)
    bflash = temp / "bf.mp4"
    run([FFMPEG, "-y", "-f", "lavfi", "-i", f"color=c=black:s={W}x{H}:d=0.04",
         "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", str(bflash)])
    
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
                if r < 0.2:
                    f.write(f"file '{flash.name}'\n")
                    ct += 0.08
                elif r < 0.15:
                    f.write(f"file '{glitch.name}'\n")
                    ct += 0.1
                elif r < 0.15:
                    f.write(f"file '{bflash.name}'\n")
                    ct += 0.04
                cut_times.append(ct)
    
    concat_vid = temp / "concat.mp4"
    run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_txt),
         "-c:v", "libx264", "-crf", "23", "-pix_fmt", "yuv420p", str(concat_vid)])
    
    current = concat_vid
    
    # Text overlays
    if texts:
        for idx, (start, dur, txt, style) in enumerate(texts):
            d = make_text_frames(txt, dur, style, temp)
            tv = temp / f"tv{idx}.mp4"
            run([FFMPEG, "-y", "-framerate", str(FPS), "-i", str(d / "%04d.png"),
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
    
    # CTA
    if cta:
        cta_vid = make_cta(2.0, temp)
        cta_txt = temp / "cta_c.txt"
        with open(cta_txt, "w") as f:
            f.write(f"file '{current.name}'\n")
            f.write(f"file '{cta_vid.name}'\n")
        cta_out = temp / "with_cta.mp4"
        run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(cta_txt),
             "-c:v", "libx264", "-crf", "23", "-pix_fmt", "yuv420p", str(cta_out)])
        if cta_out.exists():
            current = cta_out
    
    # Add silent audio track then music
    silent = temp / "silent.wav"
    dur = get_dur(current)
    run([FFMPEG, "-y", "-f", "lavfi", "-i", f"anullsrc=r=48000:cl=stereo", "-t", str(dur), str(silent)])
    
    with_music = temp / "wm.mp4"
    if music and music.exists():
        run([FFMPEG, "-y", "-i", str(current), "-i", str(silent), "-i", str(music),
             "-filter_complex",
             f"[2:a]volume=0.28,afade=t=in:ss=0:d=1,afade=t=out:st={max(0,dur-3)}:d=3[am];[1:a][am]amix=inputs=2:duration=first[aout]",
             "-map", "0:v", "-map", "[aout]",
             "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", str(with_music)])
    else:
        run([FFMPEG, "-y", "-i", str(current), "-i", str(silent),
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
    render(OUTPUT_DIR / "pro_v5_final.mp4", clips, target_dur=11.0,
           texts=texts, music=music if music.exists() else None, cta=True)
