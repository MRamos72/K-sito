"""
Memoria de conversación en memoria con TTL.
Para producción puedes cambiarlo por Redis sin tocar el resto del código.
"""
from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock
from typing import Dict, List

from app.core.config import settings
from app.core.logger import logger


class SessionStore:
    """Almacenamiento en memoria de historial por session_id."""

    def __init__(self) -> None:
        self._store: Dict[str, dict] = defaultdict(lambda: {"messages": [], "ts": time.time()})
        self._lock = Lock()

    def get_history(self, session_id: str) -> List[dict]:
        self._evict_expired()
        with self._lock:
            return list(self._store[session_id]["messages"])

    def add_message(self, session_id: str, role: str, content: str) -> None:
        with self._lock:
            session = self._store[session_id]
            session["messages"].append({"role": role, "content": content})
            session["ts"] = time.time()
            # Trim history
            if len(session["messages"]) > settings.session_history_max:
                session["messages"] = session["messages"][-settings.session_history_max:]

    def clear(self, session_id: str) -> None:
        with self._lock:
            self._store.pop(session_id, None)

    def _evict_expired(self) -> None:
        ttl_seconds = settings.session_ttl_hours * 3600
        cutoff = time.time() - ttl_seconds
        with self._lock:
            expired = [k for k, v in self._store.items() if v["ts"] < cutoff]
            for k in expired:
                del self._store[k]
        if expired:
            logger.info(f"Sesiones expiradas removidas: {len(expired)}")


session_store = SessionStore()


# ============ RATE LIMITER ============
class RateLimiter:
    """Rate limit por session_id (memoria local)."""
    def __init__(self) -> None:
        self._hits: Dict[str, list] = defaultdict(list)
        self._lock = Lock()

    def is_allowed(self, session_id: str) -> bool:
        now = time.time()
        window = 60  # segundos
        max_hits = settings.rate_limit_per_minute
        with self._lock:
            self._hits[session_id] = [t for t in self._hits[session_id] if now - t < window]
            if len(self._hits[session_id]) >= max_hits:
                return False
            self._hits[session_id].append(now)
            return True


rate_limiter = RateLimiter()
