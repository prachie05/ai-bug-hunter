from src.chunker.chunking import chunk_file

SOURCE = """
from typing import overload

@overload
def foo(x: int) -> int: ...

@overload
def foo(x: str) -> str: ...

def foo(x):
    return x


@overload
async def bar(x: int) -> int: ...

async def bar(x):
    return x
"""


def test_overloads_are_not_chunked():
    chunks = chunk_file(
        source=SOURCE,
        filepath="test.py",
        is_generated=False,
    )

    names = [chunk.name for chunk in chunks]

    assert names.count("foo") == 1
    assert names.count("bar") == 1

    for chunk in chunks:
        if chunk.name in ["foo", "bar"]:
            assert "@overload" not in chunk.content