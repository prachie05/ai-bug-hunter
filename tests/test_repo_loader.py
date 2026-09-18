"""
Day 1 baseline tests. Day 2 will add: binary files, huge files, empty repos,
bad encodings, etc.
"""

from src.ingestion.ignore_rules import is_ignored_dir, is_python_file


def test_is_python_file():
    assert is_python_file("core.py") is True
    assert is_python_file("README.md") is False
    assert is_python_file("script.pyc") is False


def test_is_ignored_dir():
    assert is_ignored_dir(".git") is True
    assert is_ignored_dir("__pycache__") is True
    assert is_ignored_dir("src") is False
    assert is_ignored_dir("some_thing.egg-info") is True
