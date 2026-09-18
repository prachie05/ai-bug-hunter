from src.ingestion.ignore_rules import is_generated_file
from src.ingestion.repo_loader import (
    is_binary_file,
    read_source_files,
    walk_python_files,
)


def test_poison_repo(tmp_path):
    poison_repo = tmp_path / "poison_repo"
    poison_repo.mkdir()

    normal = poison_repo / "normal.py"
    normal.write_text("x=10")

    binary = poison_repo / "binary.py"
    binary.write_bytes(b"\x00\xff\x00\x89PNG")

    bad_encoding = poison_repo / "bad_encoding.py"
    bad_encoding.write_bytes(b"# caf\xe9")

    huge = poison_repo / "huge.py"
    huge.write_text("x = 1\n" * 600_000)

    generated = poison_repo / "generated.py"
    generated.write_text("# This file is auto-generated. Do not edit.\nx = 10")

    empty = poison_repo / "empty.py"
    empty.write_text("")

    fake_png = poison_repo / "fake_png.py"
    fake_png.write_bytes(b"\x89PNG\r\n\x1a\n")

    huge_bytes = poison_repo / "huge_bytes.py"
    huge_bytes.write_bytes(bytes(range(128, 255)))

    files = walk_python_files(str(poison_repo))
    print(files)

    sources = read_source_files(str(poison_repo), files)
    source_paths = [source.path for source in sources]

    assert "normal.py" in source_paths
    assert "empty.py" in source_paths
    assert "generated.py" in source_paths

    assert "binary.py" not in source_paths
    assert "bad_encoding.py" in source_paths
    assert "huge.py" not in source_paths

    assert is_binary_file(str(normal)) is False
    assert is_binary_file(str(binary)) is True
    assert is_binary_file(str(fake_png)) is True
    assert is_binary_file(str(huge_bytes)) is True

    with open(normal, "r") as f:
        content = f.read()

    assert is_generated_file(content) is False
