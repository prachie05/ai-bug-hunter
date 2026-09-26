from pydantic import BaseModel

from src.chunker.chunking import CodeChunk
from src.investigator.schemas import InvestigatorHypothesis
from src.test_generator.schemas import GeneratedTest
from src.patch_generator.schemas import GeneratedPatch


class InvestigatorState(BaseModel):
    bug_description: str
    retrieved_chunks: list[CodeChunk]
    hypothesis:InvestigatorHypothesis | None  = None
    generated_test:GeneratedTest | None = None
    generated_patch: GeneratedPatch |None = None
    retrieval_k: int
    error: str | None = None
