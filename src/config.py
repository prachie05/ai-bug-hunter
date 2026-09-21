import os

from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
INVESTIGATOR_MODEL = os.getenv("INVESTIGATOR_MODEL", "gpt-5-mini")

EMBEDDING_DIMENSION = 1536
RETRIEVAL_K = 10
CACHE_DIR = "data/cache"

print(EMBEDDING_MODEL)
print(INVESTIGATOR_MODEL)
print(EMBEDDING_DIMENSION)
print(RETRIEVAL_K)