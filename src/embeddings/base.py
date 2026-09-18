from abc import ABC, abstractmethod

from dotenv import load_dotenv

load_dotenv()
class EmbeddingBackend(ABC):

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        ...
