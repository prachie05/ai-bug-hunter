from dotenv import load_dotenv
from openai import OpenAI

from .base import EmbeddingBackend

load_dotenv()

class OpenAIEmbeddingBackend(EmbeddingBackend):
    def __init__(self,model):
        self.client = OpenAI()
        self.model = model

    def embed(self, texts: list[str]) -> list[list[float]]:
        response = self.client.embeddings.create(
            model = self.model,
            input=texts
        )

        return [item.embedding for item in response.data]

    def embed_with_usage(self,texts):
        response = self.client.embeddings.create(
            model=self.model,
            input= texts
        )

        embeddings =[item.embedding for item in response.data]
        total_tokens = response.usage.total_tokens

        return embeddings,total_tokens

    

