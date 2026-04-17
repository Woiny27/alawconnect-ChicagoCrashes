from abc import ABC, abstractmethod


class BaseStorage(ABC):
    """Abstract storage backend interface."""

    @abstractmethod
    def save(self, data, path=None):
        raise NotImplementedError
