"""
Asset Downloader — skachivajet besplatnyje assety dlja rolikov.

Podderzhivajet:
  - Pexels (video/foto) — https://www.pexels.com/api/
  - Pixabay (video/foto) — https://pixabay.com/api/docs/
  - Unsplash (foto) — https://unsplash.com/developers
  - Freesound (zvuk) — https://freesound.org/docs/api/

Bez API-kluchej: fallback na public dummy-assety i placeholder-kartinki.
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
from pathlib import Path
from typing import List, Optional
from urllib.parse import quote_plus

import aiohttp


class AssetDownloader:
    """Async downloader dlya stock-assetov."""

    SOURCES = {
        "video": {
            "pexels": "https://api.pexels.com/videos/search",
            "pixabay": "https://pixabay.com/api/videos/",
        },
        "image": {
            "unsplash": "https://api.unsplash.com/search/photos",
            "pexels": "https://api.pexels.com/v1/search",
            "pixabay": "https://pixabay.com/api/",
        },
        "sound": {
            "freesound": "https://freesound.org/apiv2/search/text/",
        },
    }

    def __init__(
        self,
        output_dir: str = "./assets",
        timeout: int = 30,
    ) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = aiohttp.ClientTimeout(total=timeout)

        # API keys iz env / .env
        self.keys = {
            "pexels": os.getenv("PEXELS_API_KEY", ""),
            "pixabay": os.getenv("PIXABAY_API_KEY", ""),
            "unsplash": os.getenv("UNSPLASH_ACCESS_KEY", ""),
            "freesound": os.getenv("FREESOUND_API_KEY", ""),
        }

    # ── Public API ──────────────────────────────────────────────────────────

    async def search_and_download(
        self,
        query: str,
        asset_type: str = "video",
        count: int = 5,
        source_priority: Optional[List[str]] = None,
    ) -> List[str]:
        """Ishet i skachivajet assety po zaprosu.

        Vozvrashajet spisok putej k fajlam.
        Bez API-kluchej — vozvrashajet pustoj spisok.
        """
        if asset_type not in self.SOURCES:
            print(f"[WARN] Neizvestnyj tip asseta: {asset_type}")
            return []

        # Prioritet istochnikov
        sources = source_priority or list(self.SOURCES[asset_type].keys())
        downloaded: List[str] = []

        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            for source in sources:
                if len(downloaded) >= count:
                    break

                key = self.keys.get(source)
                if not key:
                    continue  # net klyucha — propuskaem

                try:
                    items = await self._search(
                        session, source, self.SOURCES[asset_type][source], query, count
                    )
                    for item in items:
                        if len(downloaded) >= count:
                            break
                        file_path = await self._download_item(
                            session, item, source, asset_type
                        )
                        if file_path:
                            downloaded.append(file_path)
                except Exception as e:
                    print(f"  [WARN] {source} error: {e}")
                    continue

        if not downloaded:
            print(f"  [INFO] Net API-kluchej dlja '{query}' ({asset_type}). "
                  f"Ustanovi: PEXELS_API_KEY, PIXABAY_API_KEY, UNSPLASH_ACCESS_KEY")
        return downloaded

    async def download_from_url(self, url: str, output_path: str) -> str:
        """Skachivajet fajl po URL."""
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.get(url) as response:
                response.raise_for_status()
                data = await response.read()
                Path(output_path).write_bytes(data)
                return output_path

    async def create_color_card(
        self,
        color: str,
        width: int = 1920,
        height: int = 1080,
        duration: float = 5.0,
        output_name: Optional[str] = None,
    ) -> str:
        """Sozdajet placeholder-video iz spolnogo cveta (cherez ffmpeg).

        Polезen kak fallback kogda net stock-asseta.
        """
        safe_name = output_name or f"colorcard_{color.replace('#','')}_{int(duration)}s"
        out_path = self.output_dir / "videos" / f"{safe_name}.mp4"
        out_path.parent.mkdir(parents=True, exist_ok=True)

        if out_path.exists():
            return str(out_path)

        if not shutil.which("ffmpeg"):
            print("[WARN] ffmpeg ne najden, nelzja sozdat color-card")
            return ""

        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y",
            "-f", "lavfi", "-i",
            f"color=c={color}:s={width}x{height}:d={duration}",
            "-pix_fmt", "yuv420p",
            str(out_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()
        return str(out_path) if out_path.exists() else ""

    # ── Internal helpers ────────────────────────────────────────────────────

    async def _search(
        self,
        session: aiohttp.ClientSession,
        source: str,
        endpoint: str,
        query: str,
        per_page: int,
    ) -> List[dict]:
        """Vozvrashajet spisok rezultatov poiska."""
        q = quote_plus(query)

        if source == "pexels":
            headers = {"Authorization": self.keys["pexels"]}
            url = f"{endpoint}?query={q}&per_page={per_page}"
            async with session.get(url, headers=headers) as resp:
                data = await resp.json()
                if "videos" in data:
                    return data["videos"]
                elif "photos" in data:
                    return data["photos"]
                return []

        elif source == "pixabay":
            key = self.keys["pixabay"]
            url = f"{endpoint}?key={key}&q={q}&per_page={per_page}"
            async with session.get(url) as resp:
                data = await resp.json()
                return data.get("hits", [])

        elif source == "unsplash":
            key = self.keys["unsplash"]
            url = f"{endpoint}?query={q}&per_page={per_page}&client_id={key}"
            async with session.get(url) as resp:
                data = await resp.json()
                return data.get("results", [])

        elif source == "freesound":
            key = self.keys["freesound"]
            url = f"{endpoint}?query={q}&token={key}&page_size={per_page}&fields=id,name,previews"
            async with session.get(url) as resp:
                data = await resp.json()
                return data.get("results", [])

        return []

    async def _download_item(
        self,
        session: aiohttp.ClientSession,
        item: dict,
        source: str,
        asset_type: str,
    ) -> Optional[str]:
        """Skachivajet odin item i vozvrashajet put k fajlu."""
        url = self._extract_url(item, source, asset_type)
        if not url:
            return None

        # Sozdaem bezopasnoje imja fajla
        ext = self._guess_ext(url, asset_type)
        item_id = str(item.get("id", hash(url) % 100000))
        file_name = f"{source}_{asset_type}_{item_id}{ext}"

        subdir = self.output_dir / ("videos" if asset_type == "video" else asset_type + "s")
        subdir.mkdir(parents=True, exist_ok=True)
        out_path = subdir / file_name

        if out_path.exists():
            return str(out_path)

        try:
            async with session.get(url) as resp:
                resp.raise_for_status()
                out_path.write_bytes(await resp.read())
                return str(out_path)
        except Exception as e:
            print(f"  [WARN] Download failed: {e}")
            return None

    @staticmethod
    def _extract_url(item: dict, source: str, asset_type: str) -> Optional[str]:
        """Izvlekajet pryamoj URL iz otveta API."""
        try:
            if source == "pexels":
                if asset_type == "video":
                    files = item.get("video_files", [])
                    # Berem HD (ne 4K, ne mobilku)
                    for f in sorted(files, key=lambda x: x.get("width", 0)):
                        if f.get("width", 0) >= 1280:
                            return f["link"]
                    return files[0]["link"] if files else None
                else:
                    return item["src"]["original"]

            elif source == "pixabay":
                if asset_type == "video":
                    videos = item.get("videos", {})
                    # medium / large
                    for quality in ("large", "medium", "small"):
                        if quality in videos:
                            return videos[quality]["url"]
                    return None
                else:
                    return item.get("largeImageURL") or item.get("webformatURL")

            elif source == "unsplash":
                return item["urls"]["raw"]

            elif source == "freesound":
                previews = item.get("previews", {})
                return previews.get("preview-hq-mp3") or previews.get("preview-lq-mp3")

        except (KeyError, IndexError):
            pass
        return None

    @staticmethod
    def _guess_ext(url: str, asset_type: str) -> str:
        """Opredeljajet rashirenie fajla po URL."""
        url_lower = url.lower()
        for ext in (".mp4", ".mov", ".webm", ".jpg", ".jpeg", ".png", ".mp3", ".wav"):
            if ext in url_lower:
                return ext
        defaults = {"video": ".mp4", "image": ".jpg", "sound": ".mp3"}
        return defaults.get(asset_type, ".bin")
