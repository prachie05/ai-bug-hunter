from openai import OpenAI

from src.cache.cache_manager import CacheManager
from src.config import (
    EMBEDDING_DIMENSION,
    EMBEDDING_MODEL,
    INVESTIGATOR_MODEL,
    RETRIEVAL_K,
)
from src.embeddings.bm25 import BM25Index
from src.embeddings.hybrid import hybrid_search
from src.embeddings.openai_backend import OpenAIEmbeddingBackend
from src.investigator.prompts import INVESTIGATOR_PROMPT
from src.investigator.schemas import InvestigatorHypothesis
from src.investigator.state import InvestigatorState
from src.test_generator.generator import generator_test
from src.test_generator.test_runner import run_generated_test
from src.chunker.chunking import CodeChunk, ChunkType


# ============================================================
# CONFIG
# ============================================================

REQUESTS_URL = "https://github.com/psf/requests.git"

BUGGY_REVISION = "cbce031327be4f1b4b5fd041ff4dcaa8efa2ce53"

CACHE_REVISION = BUGGY_REVISION

DEST_DIR = "data/requests"


BUG_DESCRIPTION = """
When following HTTP redirects, Response.history can contain a reference
to the response itself. This creates a self-referential history structure
and can cause code traversing the redirect history to loop indefinitely.
The bug was fixed in Requests 2.34.0.
"""


# ============================================================
# 1. LOAD CACHED REPO INDEX
# ============================================================

cache = CacheManager()

if not cache.is_cached(
    REQUESTS_URL,
    CACHE_REVISION,
):
    raise RuntimeError(
        f"Requests cache not found for revision {CACHE_REVISION}."
    )

store = cache.load_repo_cache(
    REQUESTS_URL,
    CACHE_REVISION,
    EMBEDDING_DIMENSION,
)

all_chunks = store.chunks

print("=" * 70)
print("REQUESTS TEST GENERATOR CONTROLLED EXPERIMENT")
print("=" * 70)

print(f"Index revision:     {CACHE_REVISION}")
print(f"Execution revision: {BUGGY_REVISION}")
print(f"Chunks:             {len(all_chunks)}")


# ============================================================
# 2. BUILD BM25
# ============================================================

print("\n" + "=" * 70)
print("BUILD BM25")
print("=" * 70)

bm25 = BM25Index(all_chunks)

backend = OpenAIEmbeddingBackend(
    EMBEDDING_MODEL
)


# ============================================================
# 3. HYBRID RETRIEVAL
# ============================================================

print("\n" + "=" * 70)
print("HYBRID RETRIEVAL")
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
# 4. ADD HISTORICAL REGRESSION TEST AS EVIDENCE
# ============================================================

historical_test = CodeChunk(
    content="""def test_redirect_history_no_self_reference(self, httpbin):
    r = requests.get(httpbin("redirect", "3"))

    assert r.status_code == 200
    assert len(r.history) == 3

    for i, resp in enumerate(r.history):
        assert resp not in resp.history
        assert resp.history == r.history[:i]
""",
    file_path="tests/test_requests.py [HISTORICAL REGRESSION TEST]",
    start_line=0,
    end_line=10,
    node_type=ChunkType.METHOD,
    name="test_redirect_history_no_self_reference",
    parent_class="TestRequests",
    is_generated=False,
)


# Only retrieved chunks + historical regression test
# are passed to the Investigator.
code_chunks = [
    chunk
    for chunk, score in hybrid_results
]

code_chunks.append(historical_test)


# ============================================================
# 5. INVESTIGATOR
# ============================================================

print("\n" + "=" * 70)
print("INVESTIGATOR")
print("=" * 70)

prompt = INVESTIGATOR_PROMPT.format(
    bug_description=BUG_DESCRIPTION,
    retrieved_chunks=code_chunks,
)

client = OpenAI()

response = client.responses.parse(
    model=INVESTIGATOR_MODEL,
    input=prompt,
    text_format=InvestigatorHypothesis,
)

hypothesis = response.output_parsed

print("\nHYPOTHESIS")
print("------------------")
print(hypothesis)


# ============================================================
# 6. TEST GENERATOR
# ============================================================

print("\n" + "=" * 70)
print("TEST GENERATOR")
print("=" * 70)

state = InvestigatorState(
    bug_description=BUG_DESCRIPTION,
    retrieved_chunks=code_chunks,
    hypothesis=hypothesis,
    retrieval_k=RETRIEVAL_K,
)

generated = generator_test(state)

state.generated_test = generated["generated_test"]


# ============================================================
# 7. SHOW GENERATED TEST
# ============================================================

print("\n" + "=" * 70)
print("GENERATED TEST")
print("=" * 70)

print(state.generated_test.test_code)

print("\nDESCRIPTION")
print("------------------")
print(state.generated_test.description)


# ============================================================
# 8. RUN TEST ON ACTUAL BUGGY REVISION
# ============================================================

print("\n" + "=" * 70)
print("RUNNING TEST ON BUGGY REVISION")
print("=" * 70)

print(f"Repository: {DEST_DIR}")
print(f"Expected revision: {BUGGY_REVISION}")

sandbox_result = run_generated_test(
    DEST_DIR,
    state.generated_test,
)

print("\nSANDBOX RESULT")
print("------------------")
print(f"passed:           {sandbox_result.passed}")
print(f"exit_code:        {sandbox_result.exit_code}")
print(f"ran_successfully: {sandbox_result.ran_successfully}")
print(f"assertion_failed: {sandbox_result.assertion_failed}")
print(f"timed_out:        {sandbox_result.timed_out}")

print("\nOUTPUT")
print("------------------")
print(sandbox_result.output)


# ============================================================
# 9. CONTROLLED EXPERIMENT COMPLETE
# ============================================================

print("\n" + "=" * 70)
print("CONTROLLED EXPERIMENT COMPLETE")
print("=" * 70)

print(
    "\nNo patch was generated or applied. "
    "The repository remains unchanged."
)
