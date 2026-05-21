#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
asset_finder.py
===============

Профессиональный поисковик ассетов для монтажа.

НЕ генерирует фейковые градиенты. НЕ делает «заглушки».
Ищет реальные видео, картинки, звуки — или честно говорит что ничего не нашёл.

Usage:
    >>> import asyncio
    >>> from core.asset_finder import AssetFinder
    >>> finder = AssetFinder()
    >>> clips = asyncio.run(finder.find_videos_for_topic("AI business", count=3))
    >>> # clips == []  →  нет API ключей, надо установить
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path
from typing import List, Optional

from core.asset_cache import AssetCache
from core.asset_downloader import AssetDownloader
from core.sound_library import SoundLibrary


# Тематические маппинги для разных ниш
TOPIC_KEYWORDS = {
    "business": ["laptop work", "money cash", "luxury car", "office desk", "success handshake"],
    "ai": ["artificial intelligence", "robot technology", "data code screen", "futuristic city"],
    "fitness": ["gym workout", "running athlete", "healthy food", "muscular body"],
    "motivation": ["sunrise mountain", "person walking road", "ocean waves", "city night lights"],
    "money": ["counting money", "gold coins", "luxury lifestyle", "stock market chart"],
}

# Музыка под стили
STYLE_MUSIC = {
    "gadzhi": "epic motivation cinematic",
    "yoedit": "trendy viral upbeat trap",
    "merzliakov": "minimal calm ambient focus",
}

# Звуки на переходы
TRANSITION_SOUNDS = {
    "whoosh": "whoosh swoosh transition",
    "impact": "impact hit bass drop",
    "notification": "notification ping pop",
}


class AssetFinder:
    """Профессиональный поисковик ассетов — только реальные файлы, никаких заглушек."""

    def __init__(
        self,
        output_dir: str = "./assets",
        cache_ttl_days: int = 7,
    ) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.downloader = AssetDownloader(output_dir=output_dir)
        self.cache = AssetCache(db_path=str(self.output_dir / "cache.db"), ttl_days=cache_ttl_days)
        self.sounds = SoundLibrary(library_dir=str(self.output_dir / "sounds"))

    # ------------------------------------------------------------------
    # Видео
    # ------------------------------------------------------------------
    async def find_videos_for_topic(
        self,
        topic: str,
        style: str = "gadzhi",
        count: int = 4,
    ) -> List[str]:
        """
        Найти реальные видео-клипы по теме ролика.

        Цепочка:
          1. Локальный кэш (уже скачанные)
          2. Stock API (Pexels / Pixabay) — нужен API ключ
          3. HTML scraping Pexels/Pixabay (без ключа, экспериментально)
          4. Ken Burns из реальных фото (Unsplash — нужен ключ)

        Если ничего не найдено — возвращает ПУСТОЙ список.
        НИКАКИХ градиентов, никаких цветных картинок.
        """
        keywords = self._topic_to_keywords(topic, style)
        results: List[str] = []

        for kw in keywords:
            if len(results) >= count:
                break

            # 1. Кэш
            cached = self.cache.get(kw, "video", limit=count - len(results))
            results.extend(cached)

            # 2. Stock API
            if len(results) < count:
                downloaded = await self.downloader.search_and_download(
                    kw, asset_type="video", count=count - len(results)
                )
                for path in downloaded:
                    self.cache.put(kw, "video", path, tags=[topic, style])
                results.extend(downloaded)

            # 3. HTML scraping (без API ключа)
            if len(results) < count:
                scraped = await self._scrape_videos(kw, count - len(results))
                for path in scraped:
                    self.cache.put(kw, "video", path, tags=[topic, style, "scraped"])
                results.extend(scraped)

        # 4. Ken Burns из реальных фото (только если нашлись фото)
        if len(results) < count:
            image_clips = await self._images_to_video_clips(topic, count - len(results))
            results.extend(image_clips)

        # Нет клипов? Вернём пустой список. Вызывающий код решает что делать.
        return results[:count]

    # ------------------------------------------------------------------
    # Музыка
    # ------------------------------------------------------------------
    async def find_music_for_topic(
        self,
        topic: str,
        style: str = "gadzhi",
    ) -> Optional[str]:
        """Найти фоновую музыку под тему и стиль."""
        # 1. Локальная библиотека
        music = self.sounds.get_sound("ambient", "epic")
        if music and Path(music).exists():
            return music

        # 2. Кэш
        music_query = STYLE_MUSIC.get(style, "background music")
        cached = self.cache.get(music_query, "sound", limit=1)
        if cached:
            return cached[0]

        # 3. Stock API
        downloaded = await self.downloader.search_and_download(
            music_query, asset_type="sound", count=1
        )
        if downloaded:
            self.cache.put(music_query, "sound", downloaded[0])
            return downloaded[0]

        return None

    # ------------------------------------------------------------------
    # Звуки переходов
    # ------------------------------------------------------------------
    async def find_transition_sounds(
        self,
        count: int = 3,
    ) -> List[str]:
        """Найти звуки для переходов между клипами."""
        results: List[str] = []
        for sound_type in ("whoosh", "impact", "notification"):
            if len(results) >= count:
                break

            query = TRANSITION_SOUNDS[sound_type]
            cached = self.cache.get(query, "sound", limit=1)
            if cached:
                results.extend(cached)
                continue

            downloaded = await self.downloader.search_and_download(
                query, asset_type="sound", count=1
            )
            if downloaded:
                self.cache.put(query, "sound", downloaded[0])
                results.extend(downloaded)

        return results[:count]

    # ------------------------------------------------------------------
    # Image → Video (Ken Burns) — только из реальных фото
    # ------------------------------------------------------------------
    async def _images_to_video_clips(
        self,
        topic: str,
        count: int,
        duration: float = 2.5,
    ) -> List[str]:
        """Найти реальные фото и превратить их в видео Ken Burns."""
        import shutil

        if not shutil.which("ffmpeg"):
            return []

        keywords = self._topic_to_keywords(topic, "")[:2]
        images: List[str] = []

        for kw in keywords:
            if len(images) >= count:
                break

            # Кэш фото
            cached = self.cache.get(kw, "image", limit=count - len(images))
            images.extend(cached)

            # Stock API фото
            downloaded = await self.downloader.search_and_download(
                kw, asset_type="image", count=count - len(images)
            )
            for path in downloaded:
                self.cache.put(kw, "image", path, tags=[topic])
            images.extend(downloaded)

        if not images:
            return []  # Нет фото — нет Ken Burns. Никаких заглушек.

        # Конвертация в видео через ffmpeg (Ken Burns: slow zoom + pan)
        clips: List[str] = []
        for i, img_path in enumerate(images[:count]):
            out_path = self.output_dir / "videos" / f"kenburns_{topic.replace(' ', '_')}_{i}.mp4"
            out_path.parent.mkdir(parents=True, exist_ok=True)

            if out_path.exists():
                clips.append(str(out_path))
                continue

            vf = (
                f"zoompan=z='min(zoom+0.0015,{1.15})':"
                f"d={int(duration * 30)}:s=1080x1920:fps=30,"
                f"crop=1080:1920"
            )
            proc = await asyncio.create_subprocess_exec(
                "ffmpeg", "-y", "-loop", "1", "-i", img_path,
                "-vf", vf,
                "-t", str(duration),
                "-pix_fmt", "yuv420p",
                str(out_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
            if out_path.exists():
                clips.append(str(out_path))

        return clips

    # ------------------------------------------------------------------
    # HTML Scraping (без API ключа)
    # ------------------------------------------------------------------
    async def _scrape_videos(self, query: str, count: int = 3) -> List[str]:
        """HTML scraping без API ключа: Mixkit → Pexels → Pixabay."""
        results: List[str] = []

        # Попытка 1: Mixkit (самый стабильный — прямые MP4)
        mixkit_results = await self._scrape_mixkit_html(query, count)
        results.extend(mixkit_results)

        if len(results) >= count:
            return results[:count]

        # Попытка 2: Pexels HTML scraping
        pexels_results = await self._scrape_pexels_html(query, count - len(results))
        results.extend(pexels_results)

        if len(results) >= count:
            return results[:count]

        # Попытка 3: Pixabay HTML scraping
        pixabay_results = await self._scrape_pixabay_html(query, count - len(results))
        results.extend(pixabay_results)

        return results[:count]

    async def _scrape_pexels_html(self, query: str, count: int) -> List[str]:
        """Парсинг страницы поиска Pexels для извлечения MP4 ссылок."""
        try:
            import aiohttp
        except ImportError:
            return []

        url = f"https://www.pexels.com/search/videos/{query.replace(' ', '%20')}/"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        }

        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
                async with session.get(url, headers=headers) as resp:
                    if resp.status != 200:
                        return []
                    html = await resp.text()
        except Exception as e:
            print(f"  [WARN] Pexels scrape error: {e}")
            return []

        # Ищем прямые MP4 ссылки в HTML
        # Pexels хранит видео-ссылки в data-video-src или в <script>
        mp4_urls = re.findall(r'https?://[^"\'\s]+\.mp4(?:\?[^"\'\s]*)?', html)
        # Уникальные
        mp4_urls = list(dict.fromkeys(mp4_urls))

        if not mp4_urls:
            # Ищем в JSON-LD или <script type="application/json">
            json_blocks = re.findall(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>', html, re.DOTALL)
            for block in json_blocks:
                urls = re.findall(r'https?://[^"\'\s]+\.mp4(?:\?[^"\'\s]*)?', block)
                mp4_urls.extend(urls)
            mp4_urls = list(dict.fromkeys(mp4_urls))

        # Скачиваем
        downloaded: List[str] = []
        for mp4_url in mp4_urls[:count]:
            try:
                file_name = f"scraped_pexels_{hash(mp4_url) % 100000}.mp4"
                out_path = self.output_dir / "videos" / file_name
                out_path.parent.mkdir(parents=True, exist_ok=True)

                if out_path.exists():
                    downloaded.append(str(out_path))
                    continue

                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                    async with session.get(mp4_url, headers=headers) as vid_resp:
                        if vid_resp.status == 200:
                            out_path.write_bytes(await vid_resp.read())
                            downloaded.append(str(out_path))
            except Exception as e:
                print(f"  [WARN] Failed to download scraped video: {e}")

        if downloaded:
            print(f"  [OK] Pexels HTML scrape: {len(downloaded)} videos")
        return downloaded

    async def _scrape_pixabay_html(self, query: str, count: int) -> List[str]:
        """Парсинг страницы поиска Pixabay для извлечения MP4 ссылок."""
        try:
            import aiohttp
        except ImportError:
            return []

        url = f"https://pixabay.com/videos/search/{query.replace(' ', '%20')}/"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        }

        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
                async with session.get(url, headers=headers) as resp:
                    if resp.status != 200:
                        return []
                    html = await resp.text()
        except Exception as e:
            print(f"  [WARN] Pixabay scrape error: {e}")
            return []

        # Pixabay хранит видео в data-mp4 или <source src="...">
        mp4_urls = re.findall(r'https?://[^"\'\s]+\.mp4(?:\?[^"\'\s]*)?', html)
        # Также ищем data-mp4
        data_mp4 = re.findall(r'data-mp4=["\'](https?://[^"\'\s]+\.mp4)', html)
        mp4_urls = list(dict.fromkeys(mp4_urls + data_mp4))

        downloaded: List[str] = []
        for mp4_url in mp4_urls[:count]:
            try:
                file_name = f"scraped_pixabay_{hash(mp4_url) % 100000}.mp4"
                out_path = self.output_dir / "videos" / file_name
                out_path.parent.mkdir(parents=True, exist_ok=True)

                if out_path.exists():
                    downloaded.append(str(out_path))
                    continue

                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                    async with session.get(mp4_url, headers=headers) as vid_resp:
                        if vid_resp.status == 200:
                            out_path.write_bytes(await vid_resp.read())
                            downloaded.append(str(out_path))
            except Exception as e:
                print(f"  [WARN] Failed to download scraped video: {e}")

        if downloaded:
            print(f"  [OK] Pixabay HTML scrape: {len(downloaded)} videos")
        return downloaded

    async def _scrape_mixkit_html(self, query: str, count: int) -> List[str]:
        """Парсинг Mixkit: поиск → ссылки на видео-страницы → прямые MP4.

        Mixkit отдаёт HTML с результатами поиска без JS.
        Формат MP4: https://assets.mixkit.co/videos/{id}/{id}-720.mp4
        """
        try:
            import aiohttp
        except ImportError:
            return []

        url = f"https://mixkit.co/free-stock-video/search/?query={query.replace(' ', '%20')}"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        }

        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
                async with session.get(url, headers=headers) as resp:
                    if resp.status != 200:
                        return []
                    html = await resp.text()
        except Exception as e:
            print(f"  [WARN] Mixkit scrape error: {e}")
            return []

        # Извлекаем ссылки вида /free-stock-video/slug-12345/
        links = re.findall(r'href="(/free-stock-video/[a-z0-9-]+-\d+/)"', html)
        links = list(dict.fromkeys(links))  # уникальные

        downloaded: List[str] = []
        for link in links[:count]:
            try:
                # ID — последнее число в ссылке
                video_id = link.rstrip('/').split('-')[-1]
                mp4_url = f"https://assets.mixkit.co/videos/{video_id}/{video_id}-720.mp4"

                file_name = f"mixkit_{video_id}.mp4"
                out_path = self.output_dir / "videos" / file_name
                out_path.parent.mkdir(parents=True, exist_ok=True)

                if out_path.exists():
                    downloaded.append(str(out_path))
                    continue

                # Проверяем что MP4 доступен
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                    async with session.get(mp4_url, headers=headers) as vid_resp:
                        if vid_resp.status == 200:
                            out_path.write_bytes(await vid_resp.read())
                            downloaded.append(str(out_path))
            except Exception as e:
                print(f"  [WARN] Mixkit download error: {e}")

        if downloaded:
            print(f"  [OK] Mixkit scrape: {len(downloaded)} videos")
        return downloaded

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _topic_to_keywords(self, topic: str, style: str) -> List[str]:
        """Разбить тему на ключевые слова для поиска."""
        topic_lower = topic.lower()

        matched = []
        for niche, kws in TOPIC_KEYWORDS.items():
            if niche in topic_lower:
                matched.extend(kws)

        if not matched:
            words = [w for w in topic_lower.split() if len(w) > 3]
            matched = words + ["motivation", "success"]

        if style == "gadzhi":
            matched = ["luxury " + m for m in matched[:2]] + matched
        elif style == "yoedit":
            matched = ["trendy " + m for m in matched[:2]] + matched

        return matched[:6]
