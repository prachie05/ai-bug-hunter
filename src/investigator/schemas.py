from pydantic import BaseModel


class InvestigatorHypothesis(BaseModel):
    file_path: str
    symbol: str
    parent_class : str | None = None
    reasoning : str
    confidence: float