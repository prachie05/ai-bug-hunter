import os

from src.chunker.chunking import chunk_file
from src.embeddings.embedding_text import build_embedding_text
from src.embeddings.openai_backend import OpenAIEmbeddingBackend
from src.embeddings.vector_store import VectorStore
from src.ingestion.repo_loader import ingest_repo

index_path = "data/click.index"
chunk_path = "data/click_chunks.pkl"

store = VectorStore(dimension=1536)
backend = OpenAIEmbeddingBackend("text-embedding-3-small")
if not os.path.exists(index_path) or not os.path.exists(chunk_path):
    chunks = []

    source_files = ingest_repo(
        "https://github.com/pallets/click.git",
        "data/click"
    )

    for source_file in source_files:
        file_chunks = chunk_file(
            source=source_file.content,
            filepath=source_file.path,
            is_generated=source_file.is_generated
        )

        chunks.extend(file_chunks)


   

    embedding_texts = [
        build_embedding_text(chunk)
        for chunk in chunks
    ]

    embeddings = backend.embed(embedding_texts)

    


    store.add(embeddings, chunks)
    store.save(index_path)
    store.save_chunks(chunk_path)

else: 

    store.load(index_path)
    store.load_chunks(chunk_path)

print("Model: text-embedding-3-small")
print("k: 10")

queries = [
    "Where does Click parse command line arguments?",
    "Where does Click resolve a command name to a command object?",
    "Where does Click handle exceptions and convert them into error messages?",
    "Where does Click invoke the callback function for a command?",
]

query_embeddings = backend.embed(queries)

for query, query_embedding in zip(queries,query_embeddings):
    result = store.search(query_embedding, k=10)
    print("Query: ", query)
    for chunk, score in result:
        print("--Result--")
        print("Score:", score)
        print("File:", chunk.file_path)
        print("Symbol:", chunk.name)
        #print(chunk.content)

