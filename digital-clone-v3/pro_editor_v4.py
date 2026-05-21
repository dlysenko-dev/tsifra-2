#!/usr/bin/env python3
"""
Professional Video Editor v4
- Fast cuts with varied duration
- Dynamic zooms (in/out/pulse/quick)
- Flash + glitch transitions
- Animated text (scale, pop, slide) with Montserrat Bold
- SFX on every cut (whoosh, hit, pop)
- Color grade per segment
- End CTA card
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
TEMP_DIR = PROJECT_ROOT / "temp" / "pro_v4"
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

# ── SFX ─────────────────────────────────────────────────────────────────────

def get_sfx(name: str) -> Optional[Path]:
    p = SFX_DIR / f"{name}.mp3"
    return p if p.exists() else None

def mix_sfx(base_audio: Path, cuts: List[float], temp: Path) -> Path:
    """Mix whoosh/hit SFX at each cut time."""
    whoosh = get_sfx("whoosh")
    hit = get_sfx("hit_low")
    pop = get_sfx("pop_high")
    
    if not whoosh and not hit:
        return base_audio
    
    # Build amix command with delays
    inputs = [f"[0:a]"]
    filters = []
    stream_idx = 1
    
    for t in cuts:
        if whoosh and random.random() < 0.7:
            inputs.append(f"[{stream_idx}:a]")
            filters.append(f"[{stream_idx}:a]adelay={int(t*1000)}|{int(t*1000)},volume=0.4[wh{stream_idx}]")
            stream_idx += 1
    
    # Simple version: just overlay whoosh at cuts using amix
    # For simplicity, create a combined SFX track
    sfx_total = temp / "sfx_mix.mp3"
    
    # Create silent base
    base_dur = get_dur(base_audio)
    silent = temp / "silent.wav"
    run([FFMPEG, "-y", "-f", "lavfi", "-i", f"anullsrc=r=48000:cl=stereo", "-t", str(base_dur), str(silent)])
    
    # Mix SFX into silent at cut times
    if cuts and whoosh:
        # Use adelay + amix
        amix_inputs = "[0:a]"
        filter_parts = []
        for i, t in enumerate(cuts[:10]):  # max 10 SFX to avoid complexity
            sfx = random.choice([whoosh, hit, pop, whoosh])
            if sfx:
                amix_inputs += f"[{i+1}:a]"
                filter_parts.append(f"[{i+1}:a]adelay={int(t*1000)}|{int(t*1000)},volume=0.35[s{i}]")
        
        if len(filter_parts) > 0:
            mix_str = ";".join(filter_parts)
            mix_str += f";[0:a]" + "".join(f"[s{i}]" for i in range(len(filter_parts))) + f"amix=inputs={len(filter_parts)+1}:duration=first[aout]"
            
            cmd = [FFMPEG, "-y", "-i", str(silent)]
            for _ in range(len(filter_parts)):
                cmd.extend(["-i", str(sfx)])
            cmd.extend(["-filter_complex", mix_str, "-map", "[aout]", "-c:a", "aac", "-b:a", "192k", str(sfx_total)])
            run(cmd)
            
            if sfx_total.exists():
                # Mix with base audio
                final_audio = temp / "audio_mixed.mp4"
                run([FFMPEG, "-y", "-i", str(base_audio), "-i", str(sfx_total),
                     "-filter_complex", "[0:a][1:a]amix=inputs=2:duration=first[aout]",
                     "-map", "[aout]", "-c:a", "aac", "-b:a", "192k", str(final_audio)])
                if final_audio.exists():
                    return final_audio
    
    return base_audio

# ── Clip prep with PIL zoom + color ────────────────────────────────────────

def prepare_clip(src: Path, start: float, seg_dur: float, zoom_type: str, temp: Path) -> Path:
    frames_dir = temp / f"f{random.randint(10000,99999)}"
    frames_dir.mkdir(parents=True, exist_ok=True)
    
    # Extract frames overscaled for zoom room
    run([FFMPEG, "-y", "-ss", str(start), "-t", str(seg_dur), "-i", str(src),
         "-vf", "scale=1200:2133:flags=lanczos,crop=1080:1920:(iw-1080)/2:(ih-1920)/2",
         "-r", str(FPS), "-pix_fmt", "rgb24", str(frames_dir / "%04d.png")])
    
    frame_files = sorted(frames_dir.glob("*.png"))
    n = len(frame_files)
    
    out_dir = temp / f"z{random.randint(10000,99999)}"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    for i, fp in enumerate(frame_files):
        t = i / n if n > 1 else 0
        img = Image.open(fp)
        iw, ih = img.size
        
        if zoom_type == "in":
            z = 1.0 + 0.18 * t
        elif zoom_type == "out":
            z = 1.18 - 0.18 * t
        elif zoom_type == "pulse":
            z = 1.0 + 0.1 * math.sin(t * math.pi * 2)
        elif zoom_type == "quick":
            z = 1.0 + 0.25 * math.sin(t * math.pi) if t < 0.5 else 1.25 - 0.25 * ((t-0.5)*2)
        else:
            z = 1.0
        
        cw, ch = int(iw / z), int(ih / z)
        cx, cy = (iw - cw) // 2, (ih - ch) // 2
        if z > 1.0:
            img = img.crop((cx, cy, cx + cw, cy + ch)).resize((iw, ih), Image.LANCZOS)
        
        # Fast color grade via PIL point ops
        # Increase contrast slightly
        from PIL import ImageEnhance
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.12)
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(1.08)
        
        img.save(out_dir / f"{i:04d}.png")
    
    out = temp / f"s{random.randint(10000,99999)}.mp4"
    run([FFMPEG, "-y", "-framerate", str(FPS), "-i", str(out_dir / "%04d.png"),
         "-vf", "eq=contrast=1.05:brightness=0.01:saturation=1.05",
         "-c:v", "libx264", "-crf", "26", "-pix_fmt", "yuv420p", "-an", str(out)])
    
    shutil.rmtree(frames_dir, ignore_errors=True)
    shutil.rmtree(out_dir, ignore_errors=True)
    return out

# ── Text animation ─────────────────────────────────────────────────────────

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
    mw = W - 80
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
            sc = 0.25 + 0.75*(1-math.exp(-6*t))
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
        
        fs = max(32, int(120*sc))
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
            y = int(H*0.72 - (H*0.18)*(1-math.exp(-6*t)) - th/2)
        
        # Thick stroke for readability
        sw = max(4, int(fs*0.09))
        for dx in range(-sw, sw+1):
            for dy in range(-sw, sw+1):
                if dx*dx+dy*dy <= sw*sw+1:
                    draw.text((x+dx,y+dy), txt, font=fnt, fill=(0,0,0,alpha))
        
        # Fill
        draw.text((x,y), txt, font=fnt, fill=(255,255,255,alpha))
        
        # Drop shadow
        shadow = Image.new("RGBA", (W,H), (0,0,0,0))
        sd = ImageDraw.Draw(shadow)
        off = max(3, sw//2)
        sd.text((x+off, y+off), txt, font=fnt, fill=(0,0,0,int(alpha*0.4)))
        img = Image.alpha_composite(shadow, img)
        
        img.save(d / f"{i:04d}.png")
    
    return d

# ── End CTA card ───────────────────────────────────────────────────────────

def make_cta_card(duration: float, temp: Path) -> Path:
    d = temp / "cta_frames"
    d.mkdir(parents=True, exist_ok=True)
    n = int(duration * FPS)
    font_path = font()
    fnt = ImageFont.truetype(str(font_path), 90)
    fnt2 = ImageFont.truetype(str(font_path), 50)
    
    for i in range(n):
        t = i / n
        img = Image.new("RGB", (W, H), (15, 15, 15))
        draw = ImageDraw.Draw(img)
        
        # Fade in text
        alpha = int(255 * min(1.0, t * 2))
        
        txt1 = "FOLLOW"
        bb = draw.textbbox((0,0), txt1, font=fnt)
        tw, th = bb[2]-bb[0], bb[3]-bb[1]
        x, y = (W-tw)//2, H//3 - th//2
        for dx in range(-5, 6):
            for dy in range(-5, 6):
                if dx*dx+dy*dy <= 26:
                    draw.text((x+dx, y+dy), txt1, font=fnt, fill=(0,0,0))
        draw.text((x,y), txt1, font=fnt, fill=(255,255,255))
        
        txt2 = "FOR MORE"
        bb2 = draw.textbbox((0,0), txt2, font=fnt2)
        tw2, th2 = bb2[2]-bb2[0], bb2[3]-bb2[1]
        x2, y2 = (W-tw2)//2, H//2 + 50
        draw.text((x2, y2), txt2, font=fnt2, fill=(200,200,200))
        
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
    for dd in temp.glob("f*"):
        shutil.rmtree(dd, ignore_errors=True)
    for dd in temp.glob("t*"):
        shutil.rmtree(dd, ignore_errors=True)
    
    # Build segments with varied duration
    seg_durations = [0.9, 1.1, 1.4, 0.8, 1.6, 1.2, 0.9, 1.3]
    zooms = ["in", "out", "pulse", "quick", "in", "none", "in", "out"]
    
    segs = []
    total = 0
    i = 0
    while total < target_dur and i < len(seg_durations):
        c = clips[i % len(clips)]
        d = get_dur(c)
        sd = seg_durations[i % len(seg_durations)]
        start = random.uniform(0.2, max(0.3, d - sd - 0.3))
        segs.append((c, start, sd, zooms[i % len(zooms)]))
        total += sd
        i += 1
    
    print(f"[INFO] {len(segs)} segments, ~{total:.1f}s")
    
    seg_files = []
    for i, (c, st, sd, zt) in enumerate(segs):
        print(f"  seg {i+1}: zoom={zt} dur={sd:.1f}s")
        p = prepare_clip(c, st, sd, zt, temp)
        seg_files.append(p)
    
    # Transitions
    flash = temp / "flash_w.mp4"
    bflash = temp / "flash_b.mp4"
    run([FFMPEG, "-y", "-f", "lavfi", "-i", f"color=c=white:s={W}x{H}:d=0.04",
         "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", str(flash)])
    run([FFMPEG, "-y", "-f", "lavfi", "-i", f"color=c=black:s={W}x{H}:d=0.05",
         "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", str(bflash)])
    
    # Concat with transitions + track cut times for SFX
    concat_txt = temp / "c.txt"
    cut_times = []
    current_time = 0.0
    with open(concat_txt, "w") as f:
        for i, p in enumerate(seg_files):
            f.write(f"file '{p.name}'\n")
            seg_dur = get_dur(p)
            current_time += seg_dur
            if i < len(seg_files) - 1:
                r = random.random()
                if r < 0.3:
                    f.write(f"file '{flash.name}'\n")
                    current_time += 0.04
                    cut_times.append(current_time)
                elif r < 0.2:
                    f.write(f"file '{bflash.name}'\n")
                    current_time += 0.05
                    cut_times.append(current_time)
                else:
                    cut_times.append(current_time)
    
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
    
    # Add CTA end card
    if cta:
        cta_vid = make_cta_card(2.0, temp)
        # Concat CTA to current
        cta_txt = temp / "cta_concat.txt"
        with open(cta_txt, "w") as f:
            f.write(f"file '{current.name}'\n")
            f.write(f"file '{cta_vid.name}'\n")
        cta_out = temp / "with_cta.mp4"
        run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(cta_txt),
             "-c:v", "libx264", "-crf", "23", "-pix_fmt", "yuv420p", str(cta_out)])
        if cta_out.exists():
            current = cta_out
    
    # Music + SFX
    final_audio = current
    if music and music.exists():
        # Mix SFX
        sfx_mix = mix_sfx(current, cut_times, temp)
        if sfx_mix != current:
            final_audio = sfx_mix
        
        dur = get_dur(final_audio)
        mv = temp / "final_music.mp4"
        run([FFMPEG, "-y", "-i", str(final_audio), "-i", str(music),
             "-filter_complex",
             f"[1:a]volume=0.25,afade=t=in:ss=0:d=1,afade=t=out:st={max(0,dur-3)}:d=3[am];[0:a][am]amix=inputs=2:duration=first[aout]",
             "-map", "0:v", "-map", "[aout]",
             "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", str(mv)])
        if mv.exists():
            final_audio = mv
    
    run([FFMPEG, "-y", "-i", str(final_audio),
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
        (1.6, 1.0, "PROFESSIONAL", "pop"),
        (3.8, 1.4, "EDITING", "slide_up"),
        (6.2, 1.2, "NOT A SLIDESHOW", "pop"),
    ]
    music = ASSETS_DIR / "music_epic.mp3"
    render(OUTPUT_DIR / "pro_v4_final.mp4", clips, target_dur=11.0,
           texts=texts, music=music if music.exists() else None, cta=True)
