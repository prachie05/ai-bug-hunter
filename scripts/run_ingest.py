"""
Day 1 end-of-day test.

Run with:
    python -m scripts.run_ingest https://github.com/pallets/click

Should print a clean list of Python files found in the repo, plus a
sanity check on a couple of file contents.
"""

import sys

from src.ingestion.repo_loader import ingest_repo

DEFAULT_REPO_URL = "https://github.com/pallets/click"
DEST_DIR = "data/repos/click"


def main():
    github_url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_REPO_URL

    source_files = ingest_repo(github_url, DEST_DIR)

    print(f"\n{'=' * 60}")
    print(f"Ingested {len(source_files)} Python files from {github_url}")
    print(f"{'=' * 60}\n")

    for sf in source_files[:20]:
        print(f"  {sf.path}  ({len(sf.content)} chars)")

    if len(source_files) > 20:
        print(f"  ... and {len(source_files) - 20} more")

    # Quick sanity check: does at least one file have real content?
    non_empty = [sf for sf in source_files if sf.content.strip()]
    print(f"\n{len(non_empty)}/{len(source_files)} files have non-empty content")


if __name__ == "__main__":
    main()
