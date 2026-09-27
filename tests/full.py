from pathlib import Path

from git import Repo  # type: ignore
from openai import OpenAI

from src.cache.cache_manager import CacheManager
from src.chunker.chunking import chunk_file
from src.config import (
    EMBEDDING_DIMENSION,
    EMBEDDING_MODEL,
    INVESTIGATOR_MODEL,
    RETRIEVAL_K,
)
from src.embeddings.bm25 import BM25Index
from src.embeddings.embedding_text import build_embedding_text
from src.embeddings.hybrid import hybrid_search
from src.embeddings.openai_backend import OpenAIEmbeddingBackend
from src.embeddings.vector_store import VectorStore
from src.ingestion.repo_loader import ingest_repo
from src.investigator.prompts import INVESTIGATOR_PROMPT
from src.investigator.schemas import InvestigatorHypothesis
from src.investigator.state import InvestigatorState
from src.patch_generator.patch_generator import patch_generator  # noqa: F401
from src.patch_generator.patch_pipeline import generate_and_apply_patch
from src.test_generator.generator import generator_test
from src.test_generator.test_runner import run_generated_test
from src.validator.validator import validate

REQUESTS_URL = "https://github.com/psf/requests.git"
REQUESTS_REF = "cbce031327be4f1b4b5fd041ff4dcaa8efa2ce53"

DEST_DIR = "data/requests"


cache = CacheManager()

BUG_DESCRIPTION = """
When following HTTP redirects, Respose.history can contain a reference
to the response itself. This creates a self-referential history structure
and can cause code traversing the redirect history to loop indefinitely.
The bug was fixed in Requests 2.34.0.
"""

if cache.is_cached(REQUESTS_URL, REQUESTS_REF):
    print("cache hit!")

    store = cache.load_repo_cache(
        REQUESTS_URL,
        REQUESTS_REF,
        EMBEDDING_DIMENSION,
    )

    all_chunks = store.chunks

    if not Path(DEST_DIR).exists():
        ingest_repo(
            REQUESTS_URL,
            DEST_DIR,
            REQUESTS_REF,
        )

else:
    print("cache miss")

    
    # ============================================================
    # 1. INGESTION
    # ============================================================

    print("\n" + "=" * 70)
    print("1. INGESTION")
    print("=" * 70)

    source_files = ingest_repo(
        REQUESTS_URL,
        DEST_DIR,
        REQUESTS_REF,
    )

    repo = Repo(DEST_DIR)

    print("Commit:", repo.head.commit.hexsha)
    print("Python files:", len(source_files))





    # ============================================================
    # 2. CHUNKING
    # ============================================================

    print("\n" + "=" * 70)
    print("2. CHUNKING")
    print("=" * 70)

    all_chunks = []

    for source_file in source_files:

        chunks = chunk_file(
            source_file.content,
            source_file.path,
            source_file.is_generated,
        )

        all_chunks.extend(chunks)

    print("Chunks:", len(all_chunks))


    # ============================================================
    # 3. BUILD FAISS VECTOR STORE
    # ============================================================

    print("\n" + "=" * 70)
    print("3. VECTOR INDEX")
    print("=" * 70)

    backend = OpenAIEmbeddingBackend(
        EMBEDDING_MODEL
    )

    store = VectorStore(
        dimension=EMBEDDING_DIMENSION
    )


    embedding_texts = [
        build_embedding_text(chunk)
        for chunk in all_chunks
    ]

    print("Embedding chunks:", len(embedding_texts))

    embeddings, total_tokens = backend.embed_with_usage(
        embedding_texts
    )

    print("Embedding tokens:", total_tokens)

    store.add(
        embeddings,
        all_chunks
    )

    print("FAISS vectors:", store.index.ntotal)

    cache.save_repo_cache(REQUESTS_URL, REQUESTS_REF, store)

backend = OpenAIEmbeddingBackend(EMBEDDING_MODEL)
# ============================================================
# 4. BUILD BM25
# ============================================================

print("\n" + "=" * 70)
print("4. BM25 INDEX")
print("=" * 70)

bm25 = BM25Index(
    all_chunks
)

print("BM25 documents:", len(bm25.chunks))


# ============================================================
# 5. SEMANTIC RETRIEVAL
# ============================================================

print("\n" + "=" * 70)
print("5. SEMANTIC RETRIEVAL")
print("=" * 70)

query_embedding = backend.embed(
    [BUG_DESCRIPTION]
)[0]

semantic_results = store.search(
    query_embedding,
    RETRIEVAL_K
)

print("\nTop semantic results:")

for rank, (chunk, score) in enumerate(
    semantic_results,
    start=1,
):

    print(
        f"{rank}. "
        f"{chunk.file_path} :: "
        f"{chunk.name} "
        f"[{chunk.parent_class}] "
        f"(score={score:.4f})"
    )


# ============================================================
# 6. BM25 RETRIEVAL
# ============================================================

print("\n" + "=" * 70)
print("6. BM25 RETRIEVAL")
print("=" * 70)

bm25_results = bm25.search(
    BUG_DESCRIPTION,
    RETRIEVAL_K
)

print("\nTop BM25 results:")

for rank, (chunk, score) in enumerate(
    bm25_results,
    start=1,
):

    print(
        f"{rank}. "
        f"{chunk.file_path} :: "
        f"{chunk.name} "
        f"[{chunk.parent_class}] "
        f"(score={score:.4f})"
    )


# ============================================================
# 7. HYBRID RETRIEVAL
# ============================================================

print("\n" + "=" * 70)
print("7. HYBRID RETRIEVAL")
print("=" * 70)

hybrid_results = hybrid_search(
    BUG_DESCRIPTION,
    backend,
    store,
    bm25,
    RETRIEVAL_K,
)

print("\nTop hybrid results:")

for rank, (chunk, score) in enumerate(
    hybrid_results,
    start=1,
):

    print(
        f"{rank}. "
        f"{chunk.file_path} :: "
        f"{chunk.name} "
        f"[{chunk.parent_class}] "
        f"(RRF={score:.6f})"
    )


# ============================================================
# 8. INVESTIGATOR
# ============================================================

print("\n" + "=" * 70)
print("8. INVESTIGATOR")
print("=" * 70)

code_chunks = [
    chunk
    for chunk, score in hybrid_results
]

prompt = INVESTIGATOR_PROMPT.format(
    bug_description=BUG_DESCRIPTION,
    retrieved_chunks=code_chunks,
)

client = OpenAI()

try:

    response = client.responses.parse(
        model= INVESTIGATOR_MODEL,
        input=prompt,
        text_format=InvestigatorHypothesis,
    )

    hypothesis = response.output_parsed

    state = InvestigatorState(
        bug_description= BUG_DESCRIPTION,
        retrieved_chunks= code_chunks,
        hypothesis= hypothesis,
        retrieval_k=RETRIEVAL_K,
    )

    generated = generator_test(state)

    state.generated_test = generated["generated_test"]

    sandbox_result = run_generated_test(
        DEST_DIR,
        generated["generated_test"]
    )

    patch_result = generate_and_apply_patch(state,DEST_DIR)

    print("\n>>> STARTING VALIDATOR")

    validation = validate(
        DEST_DIR,
        "tests/generated_test.py",
        "tests",
    )

    print("\n>>> VALIDATOR RETURNED")

    print("\nVALIDATION RESULT")
    print("------------------")

    print("Overall:", validation.overall_status)

    print("\nRegression test:")
    print("  Status:", validation.regression_test.status)
    print("  Failed:", validation.regression_test.failed_tests)

    print("\nExisting suite:")
    print("  Status:", validation.existing_suite.status)
    print("  Failed:", validation.existing_suite.failed_tests)
    
    print("\nPATCH RESULT")
    print("------------------")
    print(patch_result)

except Exception:  # noqa: BLE001
    import traceback
    traceback.print_exc()
    raise


# ============================================================
# 9. DONE
# ============================================================

print("\n" + "=" * 70)
print("REQUESTS FULL PIPELINE COMPLETE")
print("=" * 70)

