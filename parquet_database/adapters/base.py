from __future__ import annotations

from abc import ABC, abstractmethod
import hashlib
from pathlib import Path
from typing import Iterable


class SourceAdapter(ABC):
    """A pluggable source that discovers files and loads normalized candle rows."""

    name: str
    timeframe: str
    version: int = 1

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    @abstractmethod
    def discover(self) -> Iterable[Path]:
        """Return source files in deterministic order."""

    @abstractmethod
    def ingest(self, connection, source: Path, source_key: str) -> set[str]:
        """Insert one source into candles and return its affected symbols."""

    def source_key(self, source: Path) -> str:
        return f"{self.name}:{source.resolve().relative_to(self.root).as_posix()}"

    def fingerprint(self, source: Path) -> str:
        """Include adapter version so parser changes invalidate prior results."""
        stat = source.stat()
        payload = f"v{self.version}:{stat.st_size}:{stat.st_mtime_ns}".encode()
        return hashlib.sha256(payload).hexdigest()
