import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def disposable_repo_copy(repo_path: str):
    temp_dir = tempfile.mkdtemp()

    try:
        shutil.copytree(
            repo_path,
            temp_dir,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns(".git"),
)
        yield Path(temp_dir)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
