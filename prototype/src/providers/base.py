from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class BaseProvider(ABC):
    """Base interface for all data providers."""

    @abstractmethod
    def fetch(self, limit: Optional[int] = None) -> List[Dict[str, str]]:
        """Return provider rows as a list of dictionaries."""
        raise NotImplementedError
