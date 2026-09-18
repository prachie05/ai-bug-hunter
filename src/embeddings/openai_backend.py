from dotenv import load_dotenv
from openai import OpenAI

from .base import EmbeddingBackend

load_dotenv()

class OpenAIEmbeddingBackend(EmbeddingBackend):
    def __init__(self):
        self.client = OpenAI()

    def embed(self, texts: list[str]) -> list[list[float]]:
        response = self.client.embeddings.create(
            model = "text-embedding-3-small",
            input=texts
        )

        return [item.embedding for item in response.data]

    

