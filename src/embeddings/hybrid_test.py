import pickle

from src.embeddings.bm25 import BM25Index
from src.embeddings.hybrid import hybrid_search
from src.embeddings.openai_backend import OpenAIEmbeddingBackend
from src.embeddings.vector_store import VectorStore
from src.investigator.benchmarks import BENCHMARKS

with open("data/click_chunks.pkl", "rb") as file:
    chunks = pickle.load(file)

backend = OpenAIEmbeddingBackend("text-embedding-3-small")

store = VectorStore(dimension=1536)
store.load("data/click.index")
store.load_chunks("data/click_chunks.pkl")

bm25 = BM25Index(chunks)

for benchmark in BENCHMARKS:
    print("\n" + "=" * 60)
    print("Issue:", benchmark["issue"])
    print("Ground truth:", benchmark["ground_truth_file"], 
          benchmark["ground_truth_symbol"])

    results = hybrid_search(
        benchmark["bug_description"],
        backend,
        store,
        bm25,
        10
    )

    for chunk, score in results:
        print(
            chunk.file_path,
            chunk.name,
            chunk.parent_class,
            score
        )