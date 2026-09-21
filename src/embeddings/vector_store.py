import pickle

import faiss
import numpy as np

from src.chunker.chunking import CodeChunk


class VectorStore:
    def __init__(self,dimension: int):
        self.index = faiss.IndexFlatIP(dimension)
        self.chunks =[]

    def add(self, embeddings: list[list[float]], chunks: list[CodeChunk]):
        assert len(embeddings) == len(chunks)
        faiss_array = np.array(embeddings, dtype="float32")

        self.index.add(faiss_array)

        self.chunks.extend(chunks)
        

       

    def search(self, query_embedding: list[float], k:int):
        query_array = np.array(query_embedding, dtype="float32").reshape(1,-1)
        scores, indices = self.index.search(query_array, k)
   

        chunk_ans = []
        for index,score in zip(indices[0],scores[0]):
            if index==-1:
                continue
            chunk_ans.append((self.chunks[index],score))  

        return chunk_ans

    def save(self, path:str):
        faiss.write_index(self.index,str(path))

    def save_chunks(self,path:str):
        
        with open(path, "wb") as file:
            pickle.dump(self.chunks,file)

    def load(self, path: str):
        self.index =faiss.read_index(str(path))

    def load_chunks(self,path: str):
        with open(path, "rb") as file:
            self.chunks = pickle.load(file)

