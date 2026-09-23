from openai import OpenAI

from src.cache.cache_manager import CacheManager
from src.chunker.chunking import chunk_file
from src.config import EMBEDDING_DIMENSION, INVESTIGATOR_MODEL
from src.embeddings.bm25 import BM25Index
from src.embeddings.embedding_text import build_embedding_text
from src.embeddings.hybrid import hybrid_search
from src.embeddings.openai_backend import OpenAIEmbeddingBackend
from src.embeddings.vector_store import VectorStore
from src.ingestion.repo_loader import ingest_repo
from src.investigator.prompts import INVESTIGATOR_PROMPT
from src.investigator.schemas import InvestigatorHypothesis

cache = CacheManager()
DEST_DIR = "data/repo"


def investigate_repo(
    repo_url: str,
    bug_description: str,
    k: int,
    revision: str,
):
    backend = OpenAIEmbeddingBackend()

    if cache.is_cached(repo_url, revision):
        store = cache.load_repo_cache(
            repo_url,
            revision,
            EMBEDDING_DIMENSION,
        )
        all_chunks = store.chunks

    else:
        source_files = ingest_repo(
            repo_url,
            DEST_DIR,
            revision,
        )

       

        all_chunks = []

        for source_file in source_files:
            chunks = chunk_file(
                source_file.content,
                source_file.path,
                source_file.is_generated,
            )
            all_chunks.extend(chunks)

        store = VectorStore(
            dimension=EMBEDDING_DIMENSION
        )

        embedding_texts = [
            build_embedding_text(chunk)
            for chunk in all_chunks
        ]

        embeddings, _ = backend.embed_with_usage(
            embedding_texts
        )

        store.add(
            embeddings,
            all_chunks,
        )

        cache.save_repo_cache(
            repo_url,
            revision,
            store,
        )

    bm25 = BM25Index(all_chunks)

    hybrid_results = hybrid_search(
        bug_description,
        backend,
        store,
        bm25,
        k,
    )

    code_chunks = [
        chunk
        for chunk, score in hybrid_results
    ]

    prompt = INVESTIGATOR_PROMPT.format(
        bug_description=bug_description,
        retrieved_chunks=code_chunks,
    )

    client = OpenAI()

    try:
        response = client.responses.parse(
            model=INVESTIGATOR_MODEL,
            input=prompt,
            text_format=InvestigatorHypothesis,
        )

        hypothesis = response.output_parsed
        error = None

        

    except Exception as e:  # noqa: BLE001
        hypothesis = None 
        error =str(e)

    return hypothesis, code_chunks, error
