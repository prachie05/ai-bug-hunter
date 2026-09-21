from git import Repo

from src.ingestion.repo_loader import ingest_repo
from src.chunker.chunking import chunk_file


REQUESTS_URL = "https://github.com/psf/requests.git"
REQUESTS_REF = "185f587"
DEST_DIR = "data/requests"


source_files = ingest_repo(
    REQUESTS_URL,
    DEST_DIR,
    REQUESTS_REF,
)

repo = Repo(DEST_DIR)

print("Commit:", repo.head.commit.hexsha)
print("Python files:", len(source_files))


all_chunks = []

for source_file in source_files:
    chunks = chunk_file(
        source_file.content,
        source_file.path,
        source_file.is_generated,
    )

    all_chunks.extend(chunks)


print("Chunks:", len(all_chunks))