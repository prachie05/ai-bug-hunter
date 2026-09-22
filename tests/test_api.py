from fastapi.testclient import TestClient

from src.api.main import app
from src.investigator.schemas import InvestigatorHypothesis


client = TestClient(app)


def test_investigate_endpoint():
    fake_hypothesis = InvestigatorHypothesis(
        file_path="src/example.py",
        symbol="foo",
        parent_class=None,
        reasoning="Fake test hypothesis.",
        confidence=0.9,
    )

    def fake_investigate_repo(*args):
        return fake_hypothesis, [], None

    import src.api.main

    src.api.main.investigate_repo = fake_investigate_repo

    response = client.post(
        "/investigate",
        json={
            "repo_url": "https://github.com/example/example.git",
            "bug_description": "Something is broken.",
            "k": 5,
            "revision": "HEAD",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert "hypothesis" in body
    assert "evidence_chunks" in body
    assert "error" in body

    assert body["hypothesis"]["symbol"] == "foo"
    assert body["error"] is None