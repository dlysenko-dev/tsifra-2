#!/usr/bin/env python3
"""
pro_editor_v9.py — Professional short-form video editor v9
Phone mockup + kinetic text + chromatic aberration + scanlines + grain + vignette
"""
import os
import sys
import random
import subprocess
import shutil
from pathlib import Path

# Paths
PROJECT = Path(__file__).parent.resolve()
TEMP = PROJECT / "temp" / "v9_pipeline"
TEMP.mkdir(parents=True, exist_ok=True)
SAFE_TEMP = str(TEMP).replace("\\", "/")
SAFE_FONT = "font.ttf"
if not (PROJECT / SAFE_FONT).exists():
    src_font = PROJECT / "assets" / "Montserrat-Bold.ttf"
    if src_font.exists():
        shutil.copy2(str(src_font), str(PROJECT / SAFE_FONT))

ASSETS = PROJECT / "assets"
PHONE_BLACK = str(ASSETS / "phone_frame_black.png").replace("\\", "/")
PHONE_WHITE = str(ASSETS / "phone_frame_white.png").replace("\\", "/")
SCANLINES = str(ASSETS / "scanlines.png").replace("\\", "/")
VIGNETTE = str(ASSETS / "vignette.png").replace("\\", "/")
GRAIN = str(ASSETS / "grain.mp4").replace("\\", "/")
BLUE_ARC = str(ASSETS / "blue_arc.png").replace("\\", "/")

# ── Helpers ──

def run(cmd, shell=False, timeout=300):
    if shell:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    else:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        err = (r.stderr or "")[:600]
        print(f"  [ERR] {err}")
    return r


def get_dur(p):
    r = run(f'ffprobe -v quiet -show_entries format=duration -of csv=p=0 "{p}"', shell=True)
    try:
        return float(r.stdout.strip())
    except:
        return 3.0


# ── Assets ──

def find_clips():
    vdir = ASSETS / "videos"
    clips = list(vdir.glob("mixkit_*.mp4")) if vdir.exists() else []
    if not clips:
        clips = list(vdir.glob("*.mp4")) if vdir.exists() else []
    return [str(c).replace("\\", "/") for c in clips]


def find_music():
    m = ASSETS / "music_epic.mp3"
    return str(m).replace("\\", "/") if m.exists() else None


def find_sfx():
    sdir = ASSETS / "sfx"
    if not sdir.exists():
        return []
    return [str(f).replace("\\", "/") for f in sdir.glob("*.mp3")]


# ── Segment pipeline ──

def cut_segment(video, out, ss, t):
    run([
        "ffmpeg", "-y", "-ss", str(ss), "-t", str(t), "-i", video,
        "-c:v", "libx264", "-crf", "22", "-pix_fmt", "yuv420p", "-an", out
    ])
    return out if os.path.exists(out) else None


def phone_mockup(video, out, style="merzliakov"):
    if style == "merzliakov" or style == "feast":
        frame = PHONE_BLACK
        bg = "black" if style == "merzliakov" else "0x050510"
    else:
        frame = PHONE_WHITE
        bg = "white"
    vf = (
        f"[0:v]scale=900:1600:force_original_aspect_ratio=decrease,"
        f"pad=900:1600:(ow-iw)/2:(oh-ih)/2:{bg}[vid];"
        f"[1:v][vid]overlay=90:160:format=auto[out]"
    )
    run([
        "ffmpeg", "-y", "-i", video, "-i", frame, "-filter_complex", vf,
        "-map", "[out]", "-c:v", "libx264", "-crf", "22", "-pix_fmt", "yuv420p", "-an", out
    ])
    return out if os.path.exists(out) else None


def apply_merzliakov_fx(video, out):
    dur = get_dur(video)
    # Step 1: grade + chromatic aberration (fast chromashift)
    t1 = f"{SAFE_TEMP}/fx1.mp4"
    grade = "eq=contrast=1.05:brightness=-0.02:saturation=0.45"
    ca = "chromashift=cbh=-2:crh=2"
    run([
        "ffmpeg", "-y", "-i", video, "-vf", f"{grade},{ca}",
        "-an", "-c:v", "libx264", "-crf", "22", "-pix_fmt", "yuv420p", t1
    ])
    if not os.path.exists(t1):
        return None

    # Step 2: extend grain to video length then blend
    grain_ext = f"{SAFE_TEMP}/grain_ext.mp4"
    run([
        "ffmpeg", "-y", "-stream_loop", "-1", "-i", GRAIN,
        "-t", str(dur + 0.5), "-an", "-c:v", "libx264",
        "-crf", "23", "-pix_fmt", "yuv420p", grain_ext
    ])
    t2 = f"{SAFE_TEMP}/fx2.mp4"
    if os.path.exists(grain_ext):
        run([
            "ffmpeg", "-y", "-i", t1, "-i", grain_ext,
            "-filter_complex", "[0:v][1:v]blend=all_mode='addition':all_opacity=0.12",
            "-an", "-c:v", "libx264", "-crf", "22", "-pix_fmt", "yuv420p", t2
        ])
    if not os.path.exists(t2):
        t2 = t1

    # Step 3: scanlines
    t3 = f"{SAFE_TEMP}/fx3.mp4"
    run([
        "ffmpeg", "-y", "-i", t2, "-i", SCANLINES,
        "-filter_complex", "[0:v][1:v]overlay=0:0:format=auto",
        "-an", "-c:v", "libx264", "-crf", "22", "-pix_fmt", "yuv420p", t3
    ])
    if not os.path.exists(t3):
        t3 = t2

    # Step 4: vignette
    run([
        "ffmpeg", "-y", "-i", t3, "-i", VIGNETTE,
        "-filter_complex", "[0:v][1:v]overlay=0:0:format=auto",
        "-an", "-c:v", "libx264", "-crf", "22", "-pix_fmt", "yuv420p", out
    ])
    return out if os.path.exists(out) else None


def apply_yoedit0r_fx(video, out):
    grade = "eq=contrast=1.15:brightness=0.02:saturation=1.10"
    run([
        "ffmpeg", "-y", "-i", video, "-vf", grade,
        "-an", "-c:v", "libx264", "-crf", "22", "-pix_fmt", "yuv420p", out
    ])
    return out if os.path.exists(out) else None


def apply_feast_fx(video, out):
    # Grade: slightly desaturated, high contrast
    grade = "eq=contrast=1.10:brightness=-0.02:saturation=0.85"
    t1 = f"{SAFE_TEMP}/feast1.mp4"
    run([
        "ffmpeg", "-y", "-i", video, "-vf", grade,
        "-an", "-c:v", "libx264", "-crf", "22", "-pix_fmt", "yuv420p", t1
    ])
    if not os.path.exists(t1):
        return None
    # Overlay blue arcs
    run([
        "ffmpeg", "-y", "-i", t1, "-i", BLUE_ARC,
        "-filter_complex", "[0:v][1:v]overlay=0:0:format=auto",
        "-an", "-c:v", "libx264", "-crf", "22", "-pix_fmt", "yuv420p", out
    ])
    return out if os.path.exists(out) else None


def add_bold_text(video, out, text, ts=0, te=3, fontsize=90, fontcolor="white", borderw=6):
    font = SAFE_FONT
    vf = (
        f"drawtext=fontfile={font}:text='{text}':fontcolor={fontcolor}:fontsize={fontsize}:"
        f"x=(w-text_w)/2:y=(h-text_h)/2:borderw={borderw}:bordercolor=black:"
        f"enable='between(t\\,{ts}\\,{te})'"
    )
    run([
        "ffmpeg", "-y", "-i", video, "-vf", vf,
        "-an", "-c:v", "libx264", "-crf", "22", "-pix_fmt", "yuv420p", out
    ])
    return out if os.path.exists(out) else None


def make_black_flash(out, frames=2):
    dur = max(0.07, frames / 30)
    run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c=black:s=1080x1920:d={dur}:r=30",
        "-an", "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", out
    ])
    return out if os.path.exists(out) else None


# ── Intro / Concat / Audio ──

def kinetic_intro(lines, style, out, dur=2.0):
    sys.path.insert(0, str(PROJECT / "core"))
    from kinetic_text import KineticText
    kt = KineticText(str(PROJECT / SAFE_FONT), str(TEMP), fps=30)
    try:
        if style == "merzliakov":
            return kt.generate_merzliakov_intro(lines, duration=dur, w=1080, h=1920)
        elif style == "feast":
            return kt.generate_feast_intro(lines, duration=dur, w=1080, h=1920)
        else:
            title = lines[0] if lines else "MINIMAL"
            sub = lines[1] if len(lines) > 1 else ""
            return kt.generate_yoedit0r_intro(title, subtitle=sub, duration=dur, w=1080, h=1920)
    except Exception as e:
        print(f"[WARN] Kinetic intro failed: {e}")
        return None


def concat_segments(paths, out):
    if len(paths) == 1:
        shutil.copy2(paths[0], out)
        return out if os.path.exists(out) else None
    lf = f"{SAFE_TEMP}/concat.txt"
    with open(lf, "w", encoding="utf-8") as f:
        for p in paths:
            f.write(f"file '{p}'\n")
    run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lf,
        "-c:v", "libx264", "-crf", "22", "-pix_fmt", "yuv420p", "-an", out
    ])
    return out if os.path.exists(out) else None


def mix_audio(video, out, music_path, cut_times):
    dur = get_dur(video)
    # Base silence
    silence = f"{SAFE_TEMP}/silence.wav"
    run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
        "-t", str(dur), silence
    ])

    # SFX layer
    sfx_list = find_sfx()
    sfx_mix = f"{SAFE_TEMP}/sfx_mix.wav"
    if cut_times and sfx_list:
        max_sfx = min(len(cut_times), 12)
        inputs = [silence]
        filters = []
        for i in range(max_sfx):
            s = random.choice(sfx_list)
            inputs.append(s)
            delay = int(cut_times[i] * 1000)
            filters.append(f"[{i+1}:a]adelay={delay}|{delay},volume=0.4[s{i}]")
        mix_src = "[0:a]" + "".join(f"[s{i}]" for i in range(max_sfx))
        filters.append(f"{mix_src}amix=inputs={max_sfx+1}:duration=first[sfxout]")
        cmd = ["ffmpeg", "-y"]
        for inp in inputs:
            cmd.extend(["-i", inp])
        cmd.extend(["-filter_complex", ";".join(filters), "-map", "[sfxout]", sfx_mix])
        run(cmd)
    if not os.path.exists(sfx_mix):
        sfx_mix = silence

    # Music + final mix
    if music_path and os.path.exists(music_path):
        fade_start = max(0, dur - 3)
        run([
            "ffmpeg", "-y", "-i", video, "-i", sfx_mix, "-i", music_path,
            "-filter_complex",
            f"[2:a]loudnorm=I=-16:TP=-1.5:LRA=11,volume=0.28,"
            f"afade=t=in:ss=0:d=1.5,afade=t=out:st={fade_start}:d=3[mus];"
            f"[1:a][mus]amix=inputs=2:duration=first[aout]",
            "-map", "0:v", "-map", "[aout]",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", out
        ])
    else:
        run([
            "ffmpeg", "-y", "-i", video, "-i", sfx_mix,
            "-shortest", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", out
        ])
    return out if os.path.exists(out) else video


# ── Main build ──

def build(style, outpath):
    print(f"=== V9: {style} ===")
    clips = find_clips()
    if not clips:
        print("No clips found")
        return None
    print(f"  Clips: {len(clips)}")

    if style == "merzliakov":
        texts = ["TRENDY", "MONEY", "EDIT", "STYLE"]
    elif style == "feast":
        texts = ["MORNING", "MOTIVATION", "SUCCESS", "LEGEND"]
    else:
        texts = ["MINIMAL", "CLEAN", "PURE", "STYLE"]
    segs = []
    total_target = 10.0
    total = 0.0

    for idx, clip in enumerate(clips[:4]):
        cdur = get_dur(clip)
        sd = min(1.8, max(0.6, cdur * 0.5))
        if total + sd > total_target:
            sd = max(0.5, total_target - total)
        if sd < 0.5:
            break
        ss = random.uniform(0, max(0, cdur - sd - 0.5))

        raw = cut_segment(clip, f"{SAFE_TEMP}/s{idx}_raw.mp4", ss, sd)
        if not raw:
            continue
        ph = phone_mockup(raw, f"{SAFE_TEMP}/s{idx}_ph.mp4", style)
        if not ph:
            continue
        if style == "feast":
            fin = add_bold_text(ph, f"{SAFE_TEMP}/s{idx}_fin.mp4", texts[idx % len(texts)], 0.2, max(0.5, sd - 0.2), fontsize=70, fontcolor="white", borderw=4)
        else:
            fin = add_bold_text(ph, f"{SAFE_TEMP}/s{idx}_fin.mp4", texts[idx % len(texts)], 0.2, max(0.5, sd - 0.2))
        if not fin:
            fin = ph
        segs.append(fin)
        total += get_dur(fin)
        print(f"  seg{idx}: {texts[idx % len(texts)]} ({sd:.1f}s)")
        if total >= total_target:
            break

    if not segs:
        print("No segments")
        return None

    # Hard cuts: insert black flashes between segments
    flash = make_black_flash(f"{SAFE_TEMP}/flash.mp4", frames=random.choice([2, 3]))
    final_segs = []
    cut_times = []
    t = 0.0
    for idx, s in enumerate(segs):
        final_segs.append(s)
        sd = get_dur(s)
        t += sd
        if idx < len(segs) - 1 and flash:
            final_segs.append(flash)
            fd = get_dur(flash)
            cut_times.append(t + fd / 2)
            t += fd

    main_vid = concat_segments(final_segs, f"{SAFE_TEMP}/main.mp4")
    if not main_vid:
        return None

    # Kinetic intro
    intro_lines = ["TRENDY", "EDIT"] if style == "merzliakov" else ["MINIMAL", "STYLE"]
    intro = kinetic_intro(intro_lines, style, f"{SAFE_TEMP}/intro.mp4", dur=2.5)

    final = f"{SAFE_TEMP}/final.mp4"
    if intro and os.path.exists(intro) and main_vid:
        concat_segments([intro, main_vid], final)
    elif main_vid:
        shutil.copy2(main_vid, final)
    else:
        return None

    if not os.path.exists(final):
        return None

    # Apply global effects to the whole video (intro + main)
    fx_final = f"{SAFE_TEMP}/fx_final.mp4"
    if style == "merzliakov":
        fx_out = apply_merzliakov_fx(final, fx_final)
    elif style == "feast":
        fx_out = apply_feast_fx(final, fx_final)
    else:
        fx_out = apply_yoedit0r_fx(final, fx_final)
    if fx_out and os.path.exists(fx_out):
        final = fx_out

    # Audio
    music = find_music()
    result = mix_audio(final, outpath, music, cut_times)
    if result and os.path.exists(result):
        sz = os.path.getsize(result) / 1024 / 1024
        print(f"=== Done: {result} ({sz:.1f}MB) ===")
        return result
    return None


if __name__ == "__main__":
    s = sys.argv[1] if len(sys.argv) > 1 else "merzliakov"
    out = f"output/pro_v9_{s}.mp4"
    os.makedirs("output", exist_ok=True)
    build(s, out)
    # Build all styles if no arg
    if len(sys.argv) == 1:
        for style in ("merzliakov", "yoedit0r", "feast"):
            build(style, f"output/pro_v9_{style}.mp4")
