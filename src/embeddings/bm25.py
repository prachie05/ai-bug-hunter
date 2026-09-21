from rank_bm25 import BM25Okapi

from src.embeddings.embedding_text import build_embedding_text


class BM25Index:
    def __init__(self,chunks):
        self.chunks = chunks

        self.documents =[build_embedding_text(chunk) for chunk in chunks]

        self.tokenized_docs = [document.lower().split() for document in self.documents]

        self.bm25 = BM25Okapi(self.tokenized_docs)

    def search(self, query, k):
            query_tokens = query.lower().split()

            scores = self.bm25.get_scores(query_tokens)

            results = list(zip(self.chunks, scores))

            results.sort(key=lambda x: x[1], reverse=True)

            return results[:k]



