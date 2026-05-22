"""
Memory Layer v3
================
Система памяти Digital Clone: векторное хранилище + сессионная память.

Интеграция с Hermes Agent:
- В будущем может быть заменено/дополнено Hermes FTS5 + Honcho
- На текущий момент — lightweight in-memory + file-based fallback
"""

from .vector_store import VectorStore, SessionMemory

__all__ = ["VectorStore", "SessionMemory"]
