from src.embeddings.retrieval import retrieve


#reciprocal rank fusion
def rrf(semantic_results, bm25_results, k_constant=60):
    scores = {}
    chunks = {}

    for rank, (chunk, _) in enumerate(semantic_results, start=1):
        key = (chunk.file_path, chunk.start_line, chunk.end_line)

        score = 1 / (k_constant + rank)

        scores[key] = scores.get(key, 0) + score
        chunks[key] = chunk

    for rank, (chunk, _) in enumerate(bm25_results, start=1):
        key = (chunk.file_path, chunk.start_line, chunk.end_line)

        score = 1 / (k_constant + rank)

        scores[key] = scores.get(key, 0) + score
        chunks[key] = chunk

    results = [
        (chunks[key], score)
        for key, score in scores.items()
    ]

    results.sort(key=lambda x: x[1], reverse=True)

    return results


def hybrid_search(query, backend, store, bm25, k):
    query_embedding = backend.embed([query])[0]

    semantic_results = store.search(query_embedding, 20)

    bm25_results = bm25.search(query, 20)

    results = rrf(semantic_results, bm25_results)

    return results[:k]
     
     