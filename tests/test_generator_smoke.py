from src.test_generator.generator import generator_test
from src.investigator.state import InvestigatorState
from src.investigator.schemas import InvestigatorHypothesis
from src.chunker.chunking import CodeChunk, ChunkType


def test_generator_smoke():

    chunk = CodeChunk(
        content="def add(a, b): return a * b",
        file_path="src/example.py",
        start_line=1,
        end_line=1,
        node_type=ChunkType.FUNCTION,
        name="add",
        parent_class=None,
        is_generated=False,
    )

    hypothesis = InvestigatorHypothesis(
        file_path="src/example.py",
        symbol="add",
        parent_class=None,
        reasoning="The function multiplies the inputs instead of adding them.",
        confidence=0.95,
    )

    state = InvestigatorState(
        bug_description="add() returns the wrong result.",
        retrieved_chunks=[chunk],
        hypothesis=hypothesis,
        retrieval_k=5,
    )

    result = generator_test(state)

    print(result)

    assert result["generated_test"] is not None
    assert result["generated_test"].test_code
    assert result["generated_test"].description