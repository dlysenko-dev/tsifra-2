#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
asset_cache.py
==============

SQLite кэш для ассетов (видео, картинки, звуки).

Хранит:
  - query: поисковый запрос
  - asset_type: video | image | sound
  - source_url: откуда скачано
  - local_path: путь к файлу на диске
  - tags: тематические теги
  - created_at: дата скачивания
  - expires_at: дата протухания (TTL)

Usage:
    >>> from core.asset_cache import AssetCache
    >>> cache = AssetCache()
    >>> cache.put("laptop work", "video", "/assets/videos/pexels_123.mp4", tags=["business"])
    >>> paths = cache.get("laptop work", "video")
    ['assets/videos/pexels_123.mp4']
"""

import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional


DEFAULT_DB_PATH = "./assets/cache.db"
DEFAULT_TTL_DAYS = 7


class AssetCache:
    """Потокобезопасный SQLite-кэш для ассетов."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH, ttl_days: int = DEFAULT_TTL_DAYS) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.ttl_days = ttl_days
        self._local = threading.local()
        self._ensure_table()

    # ------------------------------------------------------------------
    # Connection (thread-local)
    # ------------------------------------------------------------------
    def _conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    def _ensure_table(self) -> None:
        self._conn().execute(
            """
            CREATE TABLE IF NOT EXISTS assets (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                query       TEXT NOT NULL,
                asset_type  TEXT NOT NULL,
                source_url  TEXT,
                local_path  TEXT NOT NULL,
                tags        TEXT,
                created_at  TEXT NOT NULL,
                expires_at  TEXT NOT NULL
            )
            """
        )
        self._conn().execute(
            "CREATE INDEX IF NOT EXISTS idx_query_type ON assets(query, asset_type)"
        )
        self._conn().commit()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def put(
        self,
        query: str,
        asset_type: str,
        local_path: str,
        source_url: str = "",
        tags: Optional[List[str]] = None,
    ) -> None:
        """Сохранить ассет в кэш."""
        now = datetime.utcnow().isoformat()
        expires = (datetime.utcnow() + timedelta(days=self.ttl_days)).isoformat()
        tags_str = ",".join(tags) if tags else ""

        self._conn().execute(
            """
            INSERT INTO assets (query, asset_type, source_url, local_path, tags, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (query.lower().strip(), asset_type, source_url, local_path, tags_str, now, expires),
        )
        self._conn().commit()

    def get(self, query: str, asset_type: str, limit: int = 10) -> List[str]:
        """Получить непротухшие пути из кэша."""
        now = datetime.utcnow().isoformat()
        rows = self._conn().execute(
            """
            SELECT local_path FROM assets
            WHERE query = ? AND asset_type = ? AND expires_at > ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (query.lower().strip(), asset_type, now, limit),
        ).fetchall()
        return [r["local_path"] for r in rows if Path(r["local_path"]).exists()]

    def get_by_tag(self, tag: str, asset_type: str, limit: int = 10) -> List[str]:
        """Поиск по тегу."""
        now = datetime.utcnow().isoformat()
        rows = self._conn().execute(
            """
            SELECT local_path FROM assets
            WHERE tags LIKE ? AND asset_type = ? AND expires_at > ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (f"%{tag}%", asset_type, now, limit),
        ).fetchall()
        return [r["local_path"] for r in rows if Path(r["local_path"]).exists()]

    def exists(self, query: str, asset_type: str) -> bool:
        """Есть ли свежий кэш по запросу."""
        return len(self.get(query, asset_type, limit=1)) > 0

    def cleanup(self) -> int:
        """Удалить протухшие записи. Возвращает количество удалённых."""
        now = datetime.utcnow().isoformat()
        cur = self._conn().execute(
            "DELETE FROM assets WHERE expires_at < ?",
            (now,),
        )
        self._conn().commit()
        return cur.rowcount

    def clear(self) -> None:
        """Очистить весь кэш."""
        self._conn().execute("DELETE FROM assets")
        self._conn().commit()
