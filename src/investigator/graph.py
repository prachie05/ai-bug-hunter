from langgraph.graph import END, START, StateGraph
from openai import OpenAI

from src.embeddings.bm25 import BM25Index
from src.embeddings.hybrid import hybrid_search
from src.embeddings.openai_backend import OpenAIEmbeddingBackend
from src.embeddings.vector_store import VectorStore
from src.investigator.prompts import INVESTIGATOR_PROMPT
from src.investigator.schemas import InvestigatorHypothesis
from src.investigator.state import InvestigatorState

client = OpenAI()

backend = OpenAIEmbeddingBackend('text-embedding-3-small')
store = VectorStore(dimension=1536)

store.load("data/click.index")
store.load_chunks("data/click_chunks.pkl")

bm25 = BM25Index(store.chunks)


def investigator(state: InvestigatorState):
    hybrid_results = hybrid_search(
        state.bug_description,
        backend,
        store,
        bm25,
        state.retrieval_k
)

    code_chunks = [chunk for chunk, score in hybrid_results]
    prompt = INVESTIGATOR_PROMPT.format(
        bug_description = state.bug_description,
        retrieved_chunks = code_chunks

    )

    try:
        response = client.responses.parse(
            model = "gpt-5-mini",
            input=prompt,
            text_format= InvestigatorHypothesis
        )

        return {
    "retrieved_chunks": code_chunks,
    "hypothesis": response.output_parsed
}

    except Exception as e:  # noqa: BLE001
        return {
        "retrieved_chunks": code_chunks,
        "hypothesis": None,
        "error": str(e)
    }

builder = StateGraph(InvestigatorState)


builder.add_node("investigator", investigator)

builder.add_edge(START, "investigator")
builder.add_edge("investigator", END)

graph = builder.compile()