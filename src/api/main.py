from fastapi import FastAPI, HTTPException

from src.api.schemas import Request, Response
from src.pipeline import investigate_repo

app = FastAPI()

@app.post("/investigate", response_model=Response)
def investigate(request: Request):
    try:
        hypothesis, evidence_chunks,error = investigate_repo(
        request.repo_url,
        request.bug_description,
        request.k,
        request.revision,
    )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    return Response(
        hypothesis= hypothesis,
        evidence_chunks=evidence_chunks,
        error = error,
    )