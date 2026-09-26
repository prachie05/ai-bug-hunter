import os

from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
INVESTIGATOR_MODEL = os.getenv("INVESTIGATOR_MODEL", "gpt-5.6-terra")

EMBEDDING_DIMENSION = 1536
RETRIEVAL_K = 10
CACHE_DIR = "data/cache"
RRF_K_CONSTANT = 60