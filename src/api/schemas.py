from pydantic import BaseModel

from src.chunker.chunking import CodeChunk
from src.investigator.schemas import InvestigatorHypothesis


class Request(BaseModel):
    repo_url: str
    bug_description: str
    k:int = 5
    revision: str = "HEAD"

class Response(BaseModel):
    evidence_chunks: list[CodeChunk] 
    hypothesis: InvestigatorHypothesis |None = None
    error: str | None = None
