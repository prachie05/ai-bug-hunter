from abc import ABC, abstractmethod


class EmbeddingBackend(ABC):

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        ...
