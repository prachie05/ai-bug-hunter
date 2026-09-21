import hashlib
from pathlib import Path

from src.config import CACHE_DIR
from src.embeddings.vector_store import VectorStore


class CacheManager:
    def __init__(self, cache_dir=CACHE_DIR):
        self.cache_dir = Path(cache_dir)

    def get_cache_key(self, repo_url: str, revision: str) -> str:
        hash_string = f"{repo_url.strip()}:{revision.strip()}"
        hash_val=  hashlib.sha256(hash_string.encode('utf-8')).hexdigest()
        return hash_val

    def get_cache_paths(self, repo_url : str, revision: str) -> tuple[Path, Path]:
        cache_key = self.get_cache_key(repo_url, revision)

        cache_path = self.cache_dir/cache_key

        index_path = cache_path/"embeddings.index"
        chunks_path = cache_path/"chunks.pkl"

        return index_path,chunks_path

    def is_cached(self, repo_url: str, revision: str)-> bool:
        index_path, chunks_path = self.get_cache_paths(repo_url,revision)

        return index_path.exists() and chunks_path.exists()


    def save_repo_cache(self, repo_url: str, revision: str, store: VectorStore):
        index_path, chunks_path = self.get_cache_paths(repo_url,revision)

        index_path.parent.mkdir(parents=True, exist_ok=True)

        store.save(index_path)
        store.save_chunks(chunks_path)


    def load_repo_cache(self, repo_url: str, revision: str, dimension: int) -> VectorStore:
        index_path, chunks_path = self.get_cache_paths(repo_url, revision)
        store = VectorStore(dimension)
        store.load(index_path)
        store.load_chunks(chunks_path)
        return store



    

        
