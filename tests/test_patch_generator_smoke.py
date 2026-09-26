from src.chunker.chunking import CodeChunk
from src.investigator.schemas import InvestigatorHypothesis
from src.test_generator.schemas import GeneratedTest
from src.patch_generator.schemas import GeneratedPatch
from src.investigator.state import InvestigatorState
from src.chunker.chunking import ChunkType

from src.patch_generator.patch_generator import patch_generator
from src.patch_generator.patch_applier import apply_patch

chunk = CodeChunk(
    content="""
def add(a, b):
    return a - b
""",
    file_path="src/example.py",
    start_line=1,
    end_line=2,
    node_type=ChunkType.FUNCTION,
    name="add",
    parent_class=None,
    is_generated=False,
)

hypothesis = InvestigatorHypothesis(
    file_path="src/example.py",
    symbol="add",
    parent_class=None,
    reasoning="The function subtracts the arguments instead of adding them.",
    confidence=0.95,
)

generated_test = GeneratedTest(
    test_code="""
def test_add():
    assert add(2, 3) == 5
""",
    description="Verifies that add returns the sum of its arguments.",
)

state = InvestigatorState(
    bug_description="add() returns the wrong result.",
    retrieved_chunks=[chunk],
    hypothesis=hypothesis,
    generated_test=generated_test,
    retrieval_k=5,
)

response = patch_generator(state)

print(response)
