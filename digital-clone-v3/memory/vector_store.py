"""
Vector Store — лёгкое векторное хранилище для проекта.

Архитектура:
    VectorStore    → долгосрочная память (tasks, results, knowledge)
    SessionMemory  → краткосрочная память текущей сессии

Интеграция:
    - JarvisOrchestrator использует через .memory интерфейс
    - В будущем: миграция на Hermes FTS5 или Chroma/Qdrant
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class MemoryEntry:
    """Одна запись в памяти."""

    id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }


class VectorStore:
    """In-memory векторное хранилище с file-based persistence.

    Lightweight реализация. Для production рекомендуется:
    - ChromaDB
    - Qdrant
    - Weaviate
    - Hermes FTS5 (future integration)
    """

    def __init__(self, storage_path: str = "data/memory.jsonl") -> None:
        self.storage_path = Path(storage_path)
        self.entries: List[MemoryEntry] = []
        self._load()

    # -- persistence ---------------------------------------------------------

    def _load(self) -> None:
        """Загрузить записи из файла."""
        if not self.storage_path.exists():
            return
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    data = json.loads(line)
                    self.entries.append(
                        MemoryEntry(
                            id=data["id"],
                            content=data["content"],
                            metadata=data.get("metadata", {}),
                            timestamp=data.get("timestamp", time.time()),
                        )
                    )
        except (json.JSONDecodeError, KeyError):
            # Corrupted file — start fresh
            self.entries = []

    def _save(self) -> None:
        """Сохранить записи в файл."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.storage_path, "w", encoding="utf-8") as f:
            for entry in self.entries:
                f.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")

    # -- public API ----------------------------------------------------------

    async def add(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Добавить запись в память.

        Returns:
            ID созданной записи.
        """
        entry_id = f"mem_{int(time.time() * 1000)}"
        entry = MemoryEntry(
            id=entry_id,
            content=content,
            metadata=metadata or {},
        )
        self.entries.append(entry)
        self._save()
        return entry_id

    async def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Поиск по памяти (keyword-based fallback).

        В будущем: semantic search через embeddings.
        """
        query_lower = query.lower()
        results = []
        for entry in self.entries:
            score = 0.0
            content_lower = entry.content.lower()
            # Simple keyword matching
            query_words = query_lower.split()
            match_count = sum(1 for w in query_words if w in content_lower)
            if match_count:
                score = match_count / len(query_words)
                results.append((score, entry))

        # Sort by score desc
        results.sort(key=lambda x: x[0], reverse=True)
        return [r[1].to_dict() for r in results[:k]]

    async def save(self, data: Dict[str, Any]) -> None:
        """Сохранить произвольные данные (interface compatible with Jarvis)."""
        content = json.dumps(data, ensure_ascii=False)
        await self.add(content, metadata={"type": "structured", "source": "jarvis"})

    def get_recent(self, n: int = 10) -> List[Dict[str, Any]]:
        """Получить N последних записей."""
        recent = sorted(self.entries, key=lambda e: e.timestamp, reverse=True)
        return [e.to_dict() for e in recent[:n]]


class SessionMemory:
    """Краткосрочная память текущей сессии.

    Хранится только в RAM, не сохраняется между перезапусками.
    """

    def __init__(self) -> None:
        self.messages: List[Dict[str, Any]] = []

    def add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Добавить сообщение в сессию."""
        self.messages.append({
            "role": role,
            "content": content,
            "metadata": metadata or {},
            "timestamp": time.time(),
        })

    def get_context(self, n: int = 10) -> List[Dict[str, Any]]:
        """Получить последние N сообщений для контекста."""
        return self.messages[-n:]

    def clear(self) -> None:
        """Очистить сессию."""
        self.messages = []
