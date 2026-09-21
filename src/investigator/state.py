from pydantic import BaseModel

from src.chunker.chunking import CodeChunk
from src.investigator.schemas import InvestigatorHypothesis


class InvestigatorState(BaseModel):
    bug_description: str
    retrieved_chunks: list[CodeChunk]
    hypothesis:InvestigatorHypothesis | None  = None
    retrieval_k: int
    error: str | None = None
