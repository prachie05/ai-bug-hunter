import pickle

from src.embeddings.bm25 import BM25Index

with open("data/click_chunks.pkl", "rb") as file:
    chunks = pickle.load(file)


bm25 = BM25Index(chunks)


for chunk, tokens in zip(bm25.chunks, bm25.tokenized_docs):
    if chunk.name == "__init__" and chunk.parent_class == "Option":
        print("CHUNK:")
        print(chunk.content)

        print("\nTOKENS:")
        print(tokens)

        break