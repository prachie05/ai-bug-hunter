from git import Repo
import pytest

from src.chunker.chunking import chunk_file
from src.ingestion.repo_loader import ingest_repo

REQUESTS_URL = "https://github.com/psf/requests.git"
REQUESTS_REF = "185f587"
DEST_DIR = "data/requests"


@pytest.fixture(scope="session")
def requests_repo():
    source_files = ingest_repo(
        REQUESTS_URL,
        DEST_DIR,
        REQUESTS_REF,
    )

    yield source_files


def test_requests_ingestion(requests_repo):
    source_files = requests_repo

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

    assert len(source_files) > 0
    assert len(all_chunks) > 0