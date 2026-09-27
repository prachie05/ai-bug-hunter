from src.cache.cache_manager import CacheManager
from src.chunker.chunking import chunk_file
from src.config import EMBEDDING_DIMENSION
from src.embeddings.embedding_text import build_embedding_text
from src.embeddings.openai_backend import OpenAIEmbeddingBackend
from src.embeddings.vector_store import VectorStore
from src.ingestion.repo_loader import ingest_repo


REPO_URL = "https://github.com/psf/requests.git"
REVISION = "cbce031327be4f1b4b5fd041ff4dcaa8efa2ce53"
DEST_DIR = "data/requests"


cache = CacheManager()

if cache.is_cached(REPO_URL, REVISION):
    print("Cache already exists.")
    raise SystemExit


print("Ingesting Requests...")
source_files = ingest_repo(
    REPO_URL,
    DEST_DIR,
    REVISION,
)

print(f"Source files: {len(source_files)}")


print("Chunking...")

all_chunks = []

for source_file in source_files:
    chunks = chunk_file(
        source_file.content,
        source_file.path,
        source_file.is_generated,
    )
    all_chunks.extend(chunks)

print(f"Chunks: {len(all_chunks)}")


print("Generating embeddings...")

backend = OpenAIEmbeddingBackend()

embedding_texts = [
    build_embedding_text(chunk)
    for chunk in all_chunks
]

embeddings, usage = backend.embed_with_usage(
    embedding_texts
)

print(f"Embedding usage: {usage}")


print("Building vector store...")

store = VectorStore(
    dimension=EMBEDDING_DIMENSION
)

store.add(
    embeddings,
    all_chunks,
)


print("Saving cache...")

cache.save_repo_cache(
    REPO_URL,
    REVISION,
    store,
)

print("DONE")
print(f"Cached revision: {REVISION}")