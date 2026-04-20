from abc import ABC, abstractmethod
from typing import Any


class BaseStorage(ABC):
    """Base interface for writing normalized records."""

    @abstractmethod
    def upsert(self, records: list[dict[str, Any]]) -> int:
        """Write records and return the number persisted."""
        raise NotImplementedError