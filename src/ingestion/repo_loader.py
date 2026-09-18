"""
Day 1 — Repository ingestion.

Scope for today: clone a repo, walk its tree, find Python files, read their
contents. Deliberately NOT handling edge cases yet (binary files, huge files,
weird encodings, etc.) — that's Day 2's job. Keeping this file simple now so
Day 2 hardening has a clean, obvious place to slot in.
"""

import logging
import os
import shutil
from dataclasses import dataclass

from git import Repo

from src.ingestion.ignore_rules import (
    MAX_FILE_SIZE,
    is_binary_file,
    is_generated_file,
    is_ignored_dir,
    is_python_file,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class SourceFile:
    """A single ingested source file."""

    path: str  # path relative to repo root, e.g. "src/click/core.py"
    absolute_path: str  # full path on disk
    content: str
    is_generated: bool


def read_file_with_encoding_fallback(file_path: str) -> str:
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()
    except UnicodeDecodeError:
        with open(file_path, encoding="CP1252") as f:
            content = f.read()

    return content


def clone_repo(github_url: str, dest_dir: str) -> str:
    """
    Clone a GitHub repo to dest_dir. If dest_dir already exists, wipes and
    re-clones — keeps this idempotent so you can re-run freely during dev.
    Returns the local path to the cloned repo.
    """
    if os.path.exists(dest_dir):
        logger.info("Removing existing clone at %s", dest_dir)
        shutil.rmtree(dest_dir)

    logger.info("Cloning %s -> %s", github_url, dest_dir)
    Repo.clone_from(
        github_url, dest_dir, depth=1
    )  # shallow clone: don't need full history
    logger.info("Clone complete")
    return dest_dir


def walk_python_files(repo_path: str) -> list[str]:
    """
    Walk the repo tree and return relative paths of all Python files,
    skipping ignored directories (.git, venv, build, etc.).
    """
    python_files = []

    for root, dirs, files in os.walk(repo_path):
        # Mutating dirs in-place prunes os.walk's traversal — this is the
        # standard way to skip whole subtrees efficiently instead of
        # walking into them and filtering after the fact.
        dirs[:] = [d for d in dirs if not is_ignored_dir(d)]

        for filename in files:
            if is_python_file(filename):
                full_path = os.path.join(root, filename)
                rel_path = os.path.relpath(full_path, repo_path)
                python_files.append(rel_path)

    logger.info("Found %d Python files", len(python_files))
    return sorted(python_files)


def read_source_files(repo_path: str, relative_paths: list[str]) -> list[SourceFile]:
    """
    Read the content of each file. Day 1: naive read, assume UTF-8, skip
    a file with a warning if it fails to read rather than crashing the
    whole ingestion run.
    """
    source_files = []

    for rel_path in relative_paths:
        absolute_path = os.path.join(repo_path, rel_path)
        file_size = os.path.getsize(absolute_path)

        if file_size > MAX_FILE_SIZE:
            logger.warning(
                "Skipping %s (file too large: %d bytes)", rel_path, file_size
            )
            continue

        if is_binary_file(absolute_path):
            logger.warning("Skipping %s as its a Binary File", rel_path)
            continue

        try:
            content = read_file_with_encoding_fallback(absolute_path)
            is_generated = is_generated_file(content)
            source_files.append(
                SourceFile(
                    path=rel_path,
                    absolute_path=absolute_path,
                    content=content,
                    is_generated=is_generated,
                )
            )
        except (UnicodeDecodeError, OSError) as e:
            logger.warning("Skipping %s (%s)", rel_path, e)

    logger.info("Successfully read %d/%d files", len(source_files), len(relative_paths))
    return source_files


def ingest_repo(github_url: str, dest_dir: str) -> list[SourceFile]:
    """End-to-end Day 1 pipeline: clone -> walk -> read."""
    repo_path = clone_repo(github_url, dest_dir)
    relative_paths = walk_python_files(repo_path)
    return read_source_files(repo_path, relative_paths)
