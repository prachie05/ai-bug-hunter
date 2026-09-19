import os
import pickle
import time

from src.chunker.chunking import chunk_file
from src.embeddings.embedding_text import build_embedding_text
from src.embeddings.openai_backend import OpenAIEmbeddingBackend
from src.embeddings.vector_store import VectorStore
from src.ingestion.repo_loader import ingest_repo

backend = OpenAIEmbeddingBackend("text-embedding-3-small")
store = VectorStore(1536)
index_path = "data/click.index"
path = "data/click_chunks.pkl"

if not os.path.exists(path):
    chunks = []
    source_files = ingest_repo(
        "https://github.com/pallets/click.git",
        "data/click"
    )

    for source_file in source_files:
        file_chunk = chunk_file(
            source=source_file.content,
            filepath=source_file.path,
            is_generated=source_file.is_generated
        )
        chunks.extend(file_chunk)

    embedding_texts = [
            build_embedding_text(chunk)
            for chunk in chunks
        ]
    
    embeddings = backend.embed(embedding_texts)
    
        
    
    
    store.add(embeddings, chunks)
    store.save(index_path)
    store.save_chunks(path)




with open(path, "rb") as file:
    chunks = pickle.load(file)


embedding_text =[build_embedding_text(chunk) for chunk in chunks]

print(len(chunks))

start = time.perf_counter()

embeddings, total_tokens = backend.embed_with_usage(embedding_text)

end = time.perf_counter()

print("Model: Small")
print("Time:", end - start)
print("Tokens:", total_tokens)
