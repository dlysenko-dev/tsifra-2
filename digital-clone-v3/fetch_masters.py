"""
Fetch Masters — skachivajet roliki s kanalov konkretnyh masterov.
Ne sluchajnye tutorialy, a luchshije v industrii.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

# KANALY masterov
MASTERS = {
    "ArseniiMerzliakov": {
        "channel": "@ArseniiMerzliakov",
        "style": "minimalist editing, storytelling, structure",
        "what_to_learn": "scene structure, pacing, visual hierarchy, transitions",
    },
    "egorlistopadov": {
        "channel": "@egorlistopadov",
        "style": "dynamic editing, style, visual",
        "what_to_learn": "color grading, rhythm, visual flow",
    },
    "YoEdit0r": {
        "channel": "@YoEdit0r",
        "style": "professional editing, effects, techniques",
        "what_to_learn": "ALL videos, every technique, every effect",
    },
}

# ETALONNYJE video (must-download)
ETALONS = [
    "https://youtu.be/QgHFU1aE0EE",  # gajd etalona kachestva shortsa
    "https://youtu.be/lebNuXNeKB8",   # etalon kachestva
    "https://youtu.be/mBfuy71d8FI",   # etalon kachestva
]


def find_yt_dlp():
    """Nahodit yt-dlp komandu."""
    if shutil.which("yt-dlp"):
        return ["yt-dlp"]
    scripts = Path(sys.executable).parent / "Scripts" / "yt-dlp.exe"
    if scripts.exists():
        return [str(scripts)]
    try:
        import yt_dlp
        return [sys.executable, "-m", "yt_dlp"]
    except ImportError:
        return None


YTDLP = find_yt_dlp()


def download_master_videos():
    """Skačivajet Shorts s kanalov masterov."""
    base = Path("learning/masters")
    base.mkdir(parents=True, exist_ok=True)

    for name, info in MASTERS.items():
        print(f"\n{'='*60}")
        print(f"[MASTER] {name}")
        print(f"   Stil: {info['style']}")
        print(f"   Uchit: {info['what_to_learn']}")

        outdir = base / name
        outdir.mkdir(exist_ok=True)

        channel_url = f"https://www.youtube.com/{info['channel']}/shorts"
        cmd = YTDLP + [
            "--playlist-end", "10",
            "-f", "best[height<=720][ext=mp4]/best[height<=720]/best",
            "--merge-output-format", "mp4",
            "-o", str(outdir / "%(title)s_%(id)s.%(ext)s"),
            channel_url,
        ]

        print(f"   [DL] Skachivaju s {channel_url}...")
        try:
            result = subprocess.run(
                cmd, capture_output=True, timeout=300,
                encoding="utf-8", errors="replace",
            )
            if result.returncode != 0:
                err = result.stderr[:300] if result.stderr else "unknown error"
                print(f"   [WARN] yt-dlp: {err}")
        except subprocess.TimeoutExpired:
            print(f"   [WARN] Timeout pri skachivanii")
        except Exception as e:
            print(f"   [WARN] Oshibka: {e}")

        files = list(outdir.glob("*.mp4"))
        print(f"   [OK] Skachano: {len(files)} rolikov")
        for f in files[:5]:
            size_mb = f.stat().st_size / (1024 * 1024)
            print(f"      - {f.name.encode("ascii", "ignore").decode()[:55]} ({size_mb:.1f} MB)")


def download_etalons():
    """Skačivajet etalonnyje video."""
    print(f"\n{'='*60}")
    print("[ETALON] KACHESTVA")

    outdir = Path("learning/etalons")
    outdir.mkdir(parents=True, exist_ok=True)

    for url in ETALONS:
        vid = url.split("/")[-1].split("?")[0]
        output = outdir / f"etalon_{vid}.mp4"

        if output.exists():
            print(f"   [OK] Uzhe est: {vid}")
            continue

        print(f"   [DL] Skachivaju: {vid}...")
        try:
            subprocess.run(
                YTDLP + [
                    "-f", "best[height<=720][ext=mp4]/best[height<=720]/best",
                    "--merge-output-format", "mp4",
                    "-o", str(output),
                    url,
                ],
                capture_output=True, timeout=120,
                encoding="utf-8", errors="replace",
            )
            if output.exists():
                size_mb = output.stat().st_size / (1024 * 1024)
                print(f"   [OK] Skachano ({size_mb:.1f} MB)")
            else:
                print(f"   [FAIL] Ne skachalos")
        except Exception as e:
            print(f"   [WARN] Oshibka: {e}")


if __name__ == "__main__":
    if not YTDLP:
        print("[ERROR] yt-dlp ne najden. Ustanovi: pip install yt-dlp")
        sys.exit(1)

    print(f"[INFO] yt-dlp: {' '.join(YTDLP)}")
    download_master_videos()
    download_etalons()

    # Itogi
    print(f"\n{'='*60}")
    print("[STAT] ITOGI:")

    for name in MASTERS:
        outdir = Path("learning/masters") / name
        files = list(outdir.glob("*.mp4")) if outdir.exists() else []
        total_mb = sum(f.stat().st_size for f in files) / (1024 * 1024)
        print(f"   {name}: {len(files)} rolikov ({total_mb:.1f} MB)")

    etalon_dir = Path("learning/etalons")
    etalon_files = list(etalon_dir.glob("*.mp4")) if etalon_dir.exists() else []
    etalon_mb = sum(f.stat().st_size for f in etalon_files) / (1024 * 1024)
    print(f"   Etalony: {len(etalon_files)} rolikov ({etalon_mb:.1f} MB)")

    total_all = sum(
        sum(f.stat().st_size for f in (Path("learning/masters") / n).glob("*.mp4"))
        for n in MASTERS
    ) + sum(f.stat().st_size for f in etalon_files)
    print(f"   VSEGO: {total_all / (1024*1024):.1f} MB")
