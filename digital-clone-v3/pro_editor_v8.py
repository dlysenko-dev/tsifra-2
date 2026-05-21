#!/usr/bin/env python3
"""
Professional Video Editor v8
Incorporates findings from YoEdit0r + Merzliakov frame analysis:
- Film grain overlay
- Scanlines overlay
- Sepia / B&W vintage grade
- Phone mockup frame
- Kinetic text (PIL sequence)
- RGB split / chromatic aberration on transitions
- Black hard cuts
- Elegant title cards
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
OVERLAY_DIR = ASSETS_DIR / "overlays"
TEMP_DIR = PROJECT_ROOT / "temp" / "pro_v8"
FFMPEG = "ffmpeg"
FFPROBE = "ffprobe"

W, H = 1080, 1920
FPS = 30

def run(cmd, capture=True, cwd=None):
    result = subprocess.run(cmd, capture_output=capture, text=True, cwd=cwd)
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

# ── Overlay assets ─────────────────────────────────────────────────────────

def ensure_overlays():
    """Generate grain, scanlines, phone mockup if missing."""
    OVERLAY_DIR.mkdir(parents=True, exist_ok=True)
    
    # Phone mockup
    phone = OVERLAY_DIR / "phone_mockup.png"
    if not phone.exists():
        img = Image.new("RGBA", (W, H), (0,0,0,0))
        draw = ImageDraw.Draw(img)
        mx, my, mw, mh, rr = 140, 200, 800, 1520, 60
        draw.rounded_rectangle([mx, my, mx+mw, my+mh], radius=rr, fill=(20,20,20,255), outline=(60,60,60,255), width=8)
        draw.rounded_rectangle([mx+20, my+20, mx+mw-20, my+mh-20], radius=rr-10, fill=(0,0,0,0))
        draw.rounded_rectangle([mx+mw//2-80, my+10, mx+mw//2+80, my+35], radius=15, fill=(20,20,20,255))
        img.save(phone)
    
    # Scanlines
    scan = OVERLAY_DIR / "scanlines.png"
    if not scan.exists():
        run([FFMPEG, "-y", "-f", "lavfi", "-i", f"color=c=black:s={W}x{H}",
             "-vf", "geq=lum='if(mod(Y,4),0,255)':cb=128:cr=128,format=rgba",
             "-vframes", "1", str(scan)])
    
    # Grain video (2s loop)
    grain = OVERLAY_DIR / "grain.mp4"
    if not grain.exists():
        run([FFMPEG, "-y", "-f", "lavfi", "-i", "anoisesrc=a=0.5:c=pink:duration=2",
             "-f", "lavfi", "-i", f"color=c=black:s={W}x{H}:duration=2",
             "-shortest", "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", str(grain)])
    
    return phone, scan, grain

# ── Segment prep ───────────────────────────────────────────────────────────

def prepare_segment(src: Path, start: float, seg_dur: float, zoom_type: str, temp: Path,
                    style: str = "normal") -> Path:
    out = temp / f"s{random.randint(10000,99999)}.mp4"
    
    z = 1.0
    if zoom_type == "in":
        z = random.uniform(1.1, 1.3)
    elif zoom_type == "out":
        z = random.uniform(1.0, 1.15)
    elif zoom_type == "pulse":
        z = random.uniform(1.05, 1.2)
    elif zoom_type == "quick":
        z = random.uniform(1.15, 1.4)
    
    max_off_x = int((1080 * z - 1080) / 2)
    max_off_y = int((1920 * z - 1920) / 2)
    off_x = random.randint(-max(1,max_off_x), max(1,max_off_x))
    off_y = random.randint(-max(1,max_off_y), max(1,max_off_y))
    
    # Base filter
    vf = (f"crop=min(iw\\,ih*9/16):min(ih\\,iw*16/9):(iw-min(iw\\,ih*9/16))/2:(ih-min(ih\\,iw*16/9))/2,"
          f"scale={int(1080*z)}:{int(1920*z)}:flags=lanczos,"
          f"crop=1080:1920:{max(0, (int(1080*z)-1080)//2 + off_x)}:{max(0, (int(1920*z)-1920)//2 + off_y)},"
          f"eq=contrast=1.12:brightness=0.01:saturation=1.08")
    
    # Style grades
    if style == "sepia":
        vf += ",colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131"
    elif style == "bw":
        vf += ",hue=s=0"
    elif style == "vintage":
        vf += ",colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131,eq=contrast=1.05:brightness=0.02"
    
    run([FFMPEG, "-y", "-ss", str(start), "-t", str(seg_dur), "-i", str(src),
         "-vf", vf, "-r", str(FPS), "-an",
         "-c:v", "libx264", "-crf", "24", "-pix_fmt", "yuv420p", str(out)])
    
    if not out.exists() or out.stat().st_size < 1024:
        run([FFMPEG, "-y", "-ss", str(start), "-t", str(seg_dur), "-i", str(src),
             "-vf", "scale=1080:1920:flags=lanczos", "-an",
             "-c:v", "libx264", "-crf", "24", "-pix_fmt", "yuv420p", str(out)])
    return out

# ── Transitions ────────────────────────────────────────────────────────────

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

def make_rgb_split(temp: Path) -> Path:
    out = temp / f"rgb{random.randint(1000,9999)}.mp4"
    run([FFMPEG, "-y", "-f", "lavfi", "-i", f"color=c=gray:s={W}x{H}:d=0.1",
         "-vf", "geq=r='r(X-6,Y)':g='g(X,Y)':b='b(X+6,Y)',noise=alls=15:allf=t+u",
         "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", str(out)])
    return out

# ── Kinetic text frames ────────────────────────────────────────────────────

def make_kinetic_text(text: str, duration: float, temp: Path) -> Path:
    """Letter-by-letter scale-in with motion blur feel."""
    font_path = font()
    base = ImageFont.truetype(str(font_path), 140)
    
    d = temp / f"kt{abs(hash(text))%100000:05d}"
    d.mkdir(parents=True, exist_ok=True)
    for f in d.glob("*.png"):
        f.unlink()
    
    n = max(1, int(duration * FPS))
    W, H = 1080, 1920
    
    # Measure total text
    td = ImageDraw.Draw(Image.new("RGBA", (1,1)))
    bb = td.textbbox((0,0), text, font=base)
    tw, th = bb[2]-bb[0], bb[3]-bb[1]
    start_x = (W - tw) // 2
    y = (H - th) // 2
    
    # Per-letter positions
    letters = []
    cx = start_x
    for ch in text:
        bb = td.textbbox((0,0), ch, font=base)
        cw = bb[2]-bb[0]
        letters.append((ch, cx, cw))
        cx += cw
    
    for i in range(n):
        t = i / n if n > 1 else 1.0
        img = Image.new("RGBA", (W,H), (0,0,0,0))
        draw = ImageDraw.Draw(img)
        
        # Reveal letters progressively
        reveal = t * len(letters)
        
        for idx, (ch, x, cw) in enumerate(letters):
            progress = reveal - idx
            if progress <= 0:
                continue
            if progress >= 1:
                sc = 1.0
                alpha = 255
                y_off = 0
            else:
                # Scale in + slide up
                sc = 0.3 + 0.7 * progress
                alpha = int(255 * progress)
                y_off = int(30 * (1 - progress))
            
            fs = max(28, int(140 * sc))
            try:
                fnt = ImageFont.truetype(str(font_path), fs)
            except:
                fnt = base
            
            # Re-measure for scaled font
            bb = draw.textbbox((0,0), ch, font=fnt)
            cw_s = bb[2]-bb[0]
            ch_s = bb[3]-bb[1]
            lx = x + (cw - cw_s) // 2
            ly = y + y_off + (th - ch_s) // 2
            
            # Stroke
            sw = max(4, int(fs*0.08))
            for dx in range(-sw, sw+1):
                for dy in range(-sw, sw+1):
                    if dx*dx+dy*dy <= sw*sw+1:
                        draw.text((lx+dx, ly+dy), ch, font=fnt, fill=(0,0,0,alpha))
            
            # Fill with color based on style
            color = (255, 255, 255, alpha)
            draw.text((lx, ly), ch, font=fnt, fill=color)
        
        img.save(d / f"{i:04d}.png")
    
    return d

# ── Elegant title card ─────────────────────────────────────────────────────

def make_title_card(text: str, duration: float, temp: Path) -> Path:
    d = temp / f"tc{abs(hash(text))%100000:05d}"
    d.mkdir(parents=True, exist_ok=True)
    n = int(duration * FPS)
    
    # Try to use a serif font
    serif = Path("C:/Windows/Fonts/times.ttf")
    if not serif.exists():
        serif = font()
    fnt = ImageFont.truetype(str(serif), 100)
    fnt2 = ImageFont.truetype(str(font()), 40)
    
    for i in range(n):
        t = i / n
        img = Image.new("RGB", (W, H), (240, 240, 240))
        draw = ImageDraw.Draw(img)
        
        # Light rays gradient effect (simulated with polygon)
        alpha_ray = int(40 * min(1.0, t * 2))
        for angle in range(0, 360, 30):
            rad = math.radians(angle)
            x2 = W//2 + int(1500 * math.cos(rad))
            y2 = H//2 + int(1500 * math.sin(rad))
            draw.line([(W//2, H//2), (x2, y2)], fill=(255,255,255), width=80)
        
        # Title
        bb = draw.textbbox((0,0), text, font=fnt)
        tw, th = bb[2]-bb[0], bb[3]-bb[1]
        x, y = (W-tw)//2, H//3 - th//2
        
        # Fade in
        alpha = int(255 * min(1.0, t * 2))
        # We can't do alpha on RGB, so just draw
        for dx in range(-4, 5):
            for dy in range(-4, 5):
                if dx*dx+dy*dy <= 17:
                    draw.text((x+dx, y+dy), text, font=fnt, fill=(180,180,180))
        draw.text((x, y), text, font=fnt, fill=(30, 30, 60))
        
        # Subtitle
        sub = "After Effect tutorial"
        bb2 = draw.textbbox((0,0), sub, font=fnt2)
        draw.text(((W-(bb2[2]-bb2[0]))//2, H//2+80), sub, font=fnt2, fill=(100,100,120))
        
        img.save(d / f"{i:04d}.png")
    
    out = temp / f"title_{random.randint(1000,9999)}.mp4"
    run([FFMPEG, "-y", "-framerate", str(FPS), "-i", str(d / "%04d.png"),
         "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p", "-an", str(out)])
    return out

# ── Main render ─────────────────────────────────────────────────────────────

def render(output_path: Path, clips: List[Path], target_dur: float = 12.0,
           texts: Optional[List[Tuple[float,float,str,str]]] = None,
           kinetic_texts: Optional[List[Tuple[float,float,str]]] = None,
           title: Optional[str] = None,
           music: Optional[Path] = None, cta: bool = True,
           grain: bool = True, scanlines: bool = True, phone: bool = False,
           style: str = "normal"):
    
    temp = TEMP_DIR / "safe"
    temp.mkdir(parents=True, exist_ok=True)
    for f in temp.glob("*.mp4"):
        f.unlink()
    
    phone_png, scan_png, grain_vid = ensure_overlays()
    
    zooms = ["in", "out", "pulse", "quick", "in", "none", "in"]
    segs = []
    total = 0
    i = 0
    
    while total < target_dur and i < 20:
        c = clips[i % len(clips)]
        d = get_dur(c)
        sd = random.choice([0.7, 0.9, 1.1, 1.4, 1.6, 0.8])
        if total + sd > target_dur:
            sd = target_dur - total
        if sd < 0.3:
            break
        start = random.uniform(0.2, max(0.3, d - sd - 0.3))
        segs.append((c, start, sd, zooms[i % len(zooms)]))
        total += sd
        i += 1
    
    print(f"[INFO] {len(segs)} segments, ~{total:.1f}s, style={style}")
    
    seg_files = []
    for i, (c, st, sd, zt) in enumerate(segs):
        print(f"  seg {i+1}: zoom={zt} dur={sd:.1f}s")
        p = prepare_segment(c, st, sd, zt, temp, style=style)
        seg_files.append(p)
    
    # Transitions
    flash_w = make_flash(temp, "white", 0.04)
    flash_b = make_flash(temp, "black", 0.05)
    glitch = make_glitch(temp)
    rgb_s = make_rgb_split(temp)
    
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
                    f.write(f"file '{flash_w.name}'\n")
                    ct += 0.04
                elif r < 0.15:
                    f.write(f"file '{glitch.name}'\n")
                    ct += 0.08
                elif r < 0.1:
                    f.write(f"file '{rgb_s.name}'\n")
                    ct += 0.1
                elif r < 0.1:
                    f.write(f"file '{flash_b.name}'\n")
                    ct += 0.05
                cut_times.append(ct)
    
    concat_vid = temp / "concat.mp4"
    run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_txt),
         "-c:v", "libx264", "-crf", "23", "-pix_fmt", "yuv420p", str(concat_vid)])
    
    current = concat_vid
    
    # Add grain + scanlines
    if grain or scanlines:
        # Copy overlays to temp for relative paths
        local_grain = temp / "grain.mp4"
        local_scan = temp / "scanlines.png"
        if grain and not local_grain.exists():
            shutil.copy(str(grain_vid), str(local_grain))
        if scanlines and not local_scan.exists():
            shutil.copy(str(scan_png), str(local_scan))
        
        fx_out = temp / "fx.mp4"
        parts = []
        mid = "[0:v]"
        
        if grain:
            parts.append("movie=grain.mp4:loop=0,setpts=N/FRAME_RATE/TB[grain]")
            parts.append(f"{mid}[grain]blend=all_mode='overlay':all_opacity=0.12[vg]")
            mid = "[vg]"
        
        if scanlines:
            parts.append("movie=scanlines.png[scan]")
            parts.append(f"{mid}[scan]blend=all_mode='screen':all_opacity=0.08[v]")
            mid = "[v]"
        
        filter_complex = ";".join(parts)
        
        cmd = [FFMPEG, "-y", "-i", str(current), "-filter_complex", filter_complex,
               "-map", mid, "-map", "0:a?",
               "-c:v", "libx264", "-crf", "22", "-pix_fmt", "yuv420p", str(fx_out.name)]
        run(cmd, cwd=str(temp))
        if fx_out.exists():
            current = fx_out
    
    # Phone mockup overlay
    if phone:
        phone_out = temp / "phone.mp4"
        run([FFMPEG, "-y", "-i", str(current), "-i", str(phone_png),
             "-filter_complex", "[1:v]format=rgba[ph];[0:v][ph]overlay=0:0[v]",
             "-map", "[v]", "-map", "0:a?",
             "-c:v", "libx264", "-crf", "22", "-pix_fmt", "yuv420p", str(phone_out)])
        if phone_out.exists():
            current = phone_out
    
    # Static text overlays (drawtext)
    if texts:
        text_vf_parts = []
        for start, dur, txt, _ in texts:
            safe_text = txt.replace(":", "\\:").replace("'", "\\'")
            fs = 110 if len(txt) < 10 else 90 if len(txt) < 15 else 70
            end = start + dur
            text_vf_parts.append(
                f"drawtext=fontfile=font.ttf:text='{safe_text}':fontcolor=white:"
                f"fontsize={fs}:borderw=6:bordercolor=black:x=(w-text_w)/2:y=(h-text_h)/2:"
                f"enable='between(t\\,{start}\\,{end})'"
            )
        text_vf = ",".join(text_vf_parts)
        text_out = temp / "with_text.mp4"
        run([FFMPEG, "-y", "-i", str(current), "-vf", text_vf,
             "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p",
             "-c:a", "copy", str(text_out)])
        if text_out.exists():
            current = text_out
    
    # Kinetic text overlays
    if kinetic_texts:
        for idx, (start, dur, txt) in enumerate(kinetic_texts):
            d = make_kinetic_text(txt, dur, temp)
            tv = temp / f"ktv{idx}.mp4"
            run([FFMPEG, "-y", "-framerate", str(FPS), "-i", str(d / "%04d.png"),
                 "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", str(tv)])
            
            outv = temp / f"kov{idx}.mp4"
            run([FFMPEG, "-y", "-i", str(current), "-i", str(tv),
                 "-filter_complex",
                 f"[1:v]colorkey=color=black:similarity=0.02:blend=0[txt];[0:v][txt]overlay=0:0:enable='between(t\\,{start}\\,{start+dur})'[v]",
                 "-map", "[v]", "-map", "0:a?",
                 "-c:v", "libx264", "-crf", "22", "-pix_fmt", "yuv420p",
                 str(outv)])
            if outv.exists():
                current = outv
    
    # Title card
    if title:
        tc_vid = make_title_card(title, 3.0, temp)
        tc_txt = temp / "tc_c.txt"
        with open(tc_txt, "w") as f:
            f.write(f"file '{tc_vid.name}'\n")
            f.write(f"file '{current.name}'\n")
        tc_out = temp / "with_title.mp4"
        run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(tc_txt),
             "-c:v", "libx264", "-crf", "22", "-pix_fmt", "yuv420p", str(tc_out)])
        if tc_out.exists():
            current = tc_out
    
    # CTA
    if cta:
        cta_vid = temp / f"cta{random.randint(1000,9999)}.mp4"
        run([FFMPEG, "-y", "-f", "lavfi", "-i", f"color=c=black:s={W}x{H}:d=2.0",
             "-vf", f"drawtext=fontfile=font.ttf:text='FOLLOW':fontcolor=white:fontsize=120:borderw=8:bordercolor=black:x=(w-text_w)/2:y=(h-text_h)/2-100,drawtext=fontfile=font.ttf:text='FOR MORE':fontcolor=gray:fontsize=60:borderw=4:bordercolor=black:x=(w-text_w)/2:y=(h-text_h)/2+80",
             "-c:v", "libx264", "-crf", "23", "-pix_fmt", "yuv420p", "-an", str(cta_vid)])
        cta_txt = temp / "cta_c.txt"
        with open(cta_txt, "w") as f:
            f.write(f"file '{current.name}'\n")
            f.write(f"file '{cta_vid.name}'\n")
        cta_out = temp / "with_cta.mp4"
        run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(cta_txt),
             "-c:v", "libx264", "-crf", "22", "-pix_fmt", "yuv420p", str(cta_out)])
        if cta_out.exists():
            current = cta_out
    
    # Audio: silent + SFX + music
    dur = get_dur(current)
    silent = temp / "silent.wav"
    run([FFMPEG, "-y", "-f", "lavfi", "-i", f"anullsrc=r=48000:cl=stereo", "-t", str(dur), str(silent)])
    
    sfx_files = [SFX_DIR / "whoosh.mp3", SFX_DIR / "hit_low.mp3", SFX_DIR / "pop_high.mp3"]
    sfx_files = [s for s in sfx_files if s.exists()]
    
    if cut_times and sfx_files:
        sfx_filter_parts = []
        for i, t in enumerate(cut_times[:8]):
            delay = int(t * 1000)
            sfx_filter_parts.append(f"[{i+1}:a]adelay={delay}|{delay},volume=0.35[s{i}]")
        if sfx_filter_parts:
            sfx_filter = ";".join(sfx_filter_parts)
            sfx_filter += f";[0:a]" + "".join(f"[s{i}]" for i in range(len(sfx_filter_parts))) + f"amix=inputs={len(sfx_filter_parts)+1}:duration=first[sfxout]"
            sfx_out = temp / "sfx_mix.wav"
            cmd = [FFMPEG, "-y", "-i", str(silent)]
            for _ in range(len(sfx_filter_parts)):
                cmd.extend(["-i", str(random.choice(sfx_files))])
            cmd.extend(["-filter_complex", sfx_filter, "-map", "[sfxout]", str(sfx_out)])
            run(cmd)
            sfx_track = sfx_out if sfx_out.exists() else silent
        else:
            sfx_track = silent
    else:
        sfx_track = silent
    
    with_music = temp / "wm.mp4"
    if music and music.exists():
        run([FFMPEG, "-y", "-i", str(current), "-i", str(sfx_track), "-i", str(music),
             "-filter_complex",
             f"[2:a]volume=0.28,afade=t=in:ss=0:d=1,afade=t=out:st={max(0,dur-3)}:d=3[am];[1:a][am]amix=inputs=2:duration=first[aout]",
             "-map", "0:v", "-map", "[aout]",
             "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", str(with_music)])
    else:
        run([FFMPEG, "-y", "-i", str(current), "-i", str(sfx_track),
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
    
    # Example: Merzliakov style (vintage, grain, scanlines)
    render(OUTPUT_DIR / "pro_v8_merzliakov.mp4", clips, target_dur=10.0,
           texts=[(0.5, 1.0, "TRENDY", "static"), (2.5, 1.2, "EDITING", "static")],
           kinetic_texts=[(4.5, 1.5, "CAPCUT")],
           title=None,
           music=ASSETS_DIR / "music_epic.mp3",
           cta=True, grain=True, scanlines=True, phone=False, style="vintage")
    
    # Example: YoEdit0r style (minimal, clean, elegant title)
    render(OUTPUT_DIR / "pro_v8_yoedit0r.mp4", clips, target_dur=10.0,
           texts=[(1.0, 1.0, "MINIMAL", "static"), (3.0, 1.0, "STYLE", "static")],
           kinetic_texts=[],
           title="MINIMAL EDIT",
           music=ASSETS_DIR / "music_epic.mp3",
           cta=True, grain=False, scanlines=False, phone=False, style="normal")
