"""
Sound Library — upravlenije zvukovymi effektami i muzykoj.

Organizacija po kategorijam:
  transition — whoosh, swoosh, swipe
  impact     — hit, punch, boom
  notification — ping, pop, click
  ambient    — calm, tension, epic
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Dict, List, Optional


class SoundLibrary:
    """Biblioteka zvukov dlja rolikov."""

    CATEGORIES: Dict[str, List[str]] = {
        "transition": ["whoosh", "swoosh", "swipe", "woosh-fast", "woosh-slow"],
        "impact": ["hit", "punch", "boom", "slam", "crash"],
        "notification": ["ping", "pop", "click", "ding", "bell"],
        "ambient": ["calm", "tension", "epic", "dark", "lofi"],
        "typing": ["keyboard", "typewriter", "click-clack"],
        "riser": ["riser-short", "riser-long", "build-up"],
    }

    def __init__(self, library_dir: str = "./assets/sounds") -> None:
        self.library_dir = Path(library_dir)
        self.library_dir.mkdir(parents=True, exist_ok=True)

        # Sozdat podpapki pod kategorii
        for cat in self.CATEGORIES:
            (self.library_dir / cat).mkdir(exist_ok=True)

        # Skanirovanije imejushchikhsja zvukov
        self.sounds: Dict[str, Dict[str, str]] = self._scan_library()

    # ── Public API ──────────────────────────────────────────────────────────

    def get_sound(self, category: str, name: Optional[str] = None) -> Optional[str]:
        """Vozvrashajet put k zvukovomu fajlu.

        Args:
            category: transition | impact | notification | ambient | typing | riser
            name: imja zvuka. Esli None — sluchajnyj iz kategorii.

        Vozvrashajet:
            Put k fajlu ili None (esli net i nelzja sozdat placeholder).
        """
        if category not in self.CATEGORIES:
            print(f"[WARN] Neizvestnaja kategorija: {category}")
            return None

        cat_sounds = self.sounds.get(category, {})

        # Esli est v biblioteke
        if name and name in cat_sounds:
            return cat_sounds[name]

        if cat_sounds:
            # Berem pervyj dostupnyj
            return next(iter(cat_sounds.values()))

        # Net v biblioteke — probujem sozdat placeholder
        placeholder = self._create_placeholder(category, name or "generic")
        if placeholder:
            # Kesha
            key = name or "placeholder"
            if category not in self.sounds:
                self.sounds[category] = {}
            self.sounds[category][key] = placeholder
            return placeholder

        return None

    def add_sound(self, file_path: str, category: str, name: str) -> str:
        """Dobavljaet zvuk v biblioteku.

        Returns:
            Novyj put v biblioteke.
        """
        src = Path(file_path)
        if not src.exists():
            raise FileNotFoundError(f"Fajl ne najden: {file_path}")

        cat_dir = self.library_dir / category
        cat_dir.mkdir(parents=True, exist_ok=True)

        ext = src.suffix or ".mp3"
        dst = cat_dir / f"{name}{ext}"

        # Izbezhat perezapisi
        counter = 1
        while dst.exists():
            dst = cat_dir / f"{name}_{counter}{ext}"
            counter += 1

        shutil.copy2(src, dst)

        # Obnovit indeks
        if category not in self.sounds:
            self.sounds[category] = {}
        self.sounds[category][name] = str(dst)

        return str(dst)

    def list_available(self, category: Optional[str] = None) -> Dict[str, List[str]]:
        """Vozvrashajet slovar dostupnyh zvukov."""
        if category:
            return {category: list(self.sounds.get(category, {}).keys())}
        return {k: list(v.keys()) for k, v in self.sounds.items()}

    def generate_silence(self, duration: float, output_name: str) -> str:
        """Sozdajet tishinu zadannoj dlitelnosti (fallback dlja muzyki)."""
        out_path = self.library_dir / f"{output_name}.mp3"
        if out_path.exists():
            return str(out_path)

        if not shutil.which("ffmpeg"):
            return ""

        import subprocess

        proc = subprocess.run(
            [
                "ffmpeg", "-y", "-f", "lavfi", "-i",
                "anullsrc=r=44100:cl=mono",
                "-t", str(duration), "-acodec", "libmp3lame",
                "-q:a", "4",
                str(out_path),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return str(out_path) if out_path.exists() else ""

    # ── Internal ────────────────────────────────────────────────────────────

    def _scan_library(self) -> Dict[str, Dict[str, str]]:
        """Skanirujet papku i sobirajet indeks zvukov."""
        result: Dict[str, Dict[str, str]] = {}
        for cat_dir in self.library_dir.iterdir():
            if not cat_dir.is_dir():
                continue
            cat = cat_dir.name
            result[cat] = {}
            for f in cat_dir.iterdir():
                if f.suffix.lower() in (".mp3", ".wav", ".ogg", ".m4a", ".flac"):
                    result[cat][f.stem] = str(f)
        return result

    def _create_placeholder(self, category: str, name: str) -> Optional[str]:
        """Sozdajet sinteticheskij placeholder-zvuk cherez ffmpeg (sync).

        Generirujet raznye tipy zvukov v zavisimosti ot kategorii:
          - transition: white noise burst (0.3s)
          - impact: low sine burst (0.2s)
          - notification: high sine ping (0.15s)
          - ambient: pink noise (5s)
        """
        if not shutil.which("ffmpeg"):
            return None

        import subprocess

        out_path = self.library_dir / category / f"{name}_placeholder.mp3"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        if out_path.exists():
            return str(out_path)

        # Parametry v zavisimosti ot kategorii
        generators = {
            "transition": ("sine=frequency=800:duration=0.3", "afade=t=out:st=0.1:d=0.2"),
            "impact": ("sine=frequency=150:duration=0.25", "afade=t=out:st=0.05:d=0.2,volume=2.0"),
            "notification": ("sine=frequency=1200:duration=0.15", "afade=t=out:st=0.05:d=0.1"),
            "ambient": ("anoisesrc=a=0.02:color=pink:duration=5", "lowpass=f=800"),
            "typing": ("sine=frequency=2000:duration=0.05", "afade=t=out:st=0.01:d=0.04"),
            "riser": ("sine=frequency=200:duration=2", "afade=t=in:st=0:d=0.5,volume='max(1,2*t/2)'"),
        }

        gen, filter_str = generators.get(category, generators["transition"])

        proc = subprocess.run(
            [
                "ffmpeg", "-y", "-f", "lavfi", "-i", gen,
                "-af", filter_str,
                "-acodec", "libmp3lame", "-q:a", "4",
                str(out_path),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return str(out_path) if out_path.exists() else None
