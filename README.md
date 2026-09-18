# AI Bug Hunter

An agentic system that investigates a real GitHub repo, locates the code
relevant to a bug report, and (eventually) generates and validates a fix —
built to test real agentic pipeline design, not a single-shot LLM wrapper.

Test repository used throughout: [`pallets/click`](https://github.com/pallets/click).

## Status

Currently through (ingestion → chunking →
retrieval, before the investigator agent and API layer are wired in).

- [x] Day 1 — Repo ingestion (clone, walk, filter, read Python files)
- [x] Day 2 — Ingestion hardening (binary/huge/generated/bad-encoding files)
- [x] Day 3 — AST-based chunking (functions, methods, classes, decorators)
- [x] Day 4 — Swappable embeddings + FAISS retrieval, baseline evaluation
- [ ] Day 5 — Embedding model comparison (small vs. large), retrieval tuning
- [ ] Day 6 — LangGraph investigator agent
- [ ] Day 7 — FastAPI wrapper + cleanup

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file with your OpenAI API key:

```
OPENAI_API_KEY=your-key-here
```

## Usage

Ingest a repo and check file discovery:

```bash
python -m scripts.run_ingest https://github.com/pallets/click
```

Run the full pipeline (ingest → chunk → embed → index → query):

```bash
python -m src.embeddings.test_retrieval
```

Run tests:

```bash
pytest tests/ -v
```

## Architecture (built so far)

```
GitHub repo URL
      |
Repository ingestion (src/ingestion/)
  - clone, walk tree, filter (binary/huge/generated files skipped or flagged)
      |
AST chunking (src/chunker/)
  - functions, methods, classes -> CodeChunk objects
  - decorator-aware source slicing (exact original text, never ast.unparse())
      |
Embedding (src/embeddings/)
  - swappable EmbeddingBackend interface
  - OpenAI text-embedding-3-small (current baseline)
      |
FAISS vector store
  - IndexFlatIP, vector -> CodeChunk mapping, persisted to disk
      |
Retrieval
  - text query -> top-k relevant code chunks
```

## Design decisions worth noting

- **Source is sliced from the original file, never regenerated via
  `ast.unparse()`** — preserves exact formatting, comments, and decorators,
  since a bug-investigation tool needs to see precisely what the developer
  wrote.
- **Classes are chunked by behavior, not mechanically**: a class with 2+
  methods is split into per-method chunks (with `parent_class` metadata); a
  simple data/container class becomes a single chunk.
- **Nested functions stay inside their enclosing function's chunk** —
  deliberate V1 simplification, not an oversight.
- **Generated files are kept, not excluded**, and tagged `is_generated` —
  generated code can still contain real bugs; the decision of whether to
  deprioritize it is left to later stages.
- **Embedding backend is swappable by design** (small -> large -> hybrid
  planned) so model comparisons are a config change, not a rewrite.

## Evaluation — Day 4 baseline

Four fixed test queries against real `pallets/click` chunks
(`text-embedding-3-small`, 1536-dim, verified unit-normalized so
`IndexFlatIP` scores are directly interpretable as cosine similarity):

| Query | Expected target | Top-1? | In top-3? |
|---|---|---|---|
| Where does Click parse command line arguments? | `core.py::parse_args` | Yes | Yes |
| Where does Click resolve a command name to a command object? | `core.py::resolve_command` | Yes | Yes |
| Where does Click handle exceptions and convert them to messages? | `exceptions.py::show` | No (rank 3) | Yes |
| Where does Click invoke the callback for a command? | `core.py::invoke` | Yes | Yes |

**Result: 3/4 correct at top-1, 4/4 within top-3.**

Findings:
- Semantic retrieval works on real, unmodified source — not just filename
  matching.
- Larger k improves recall but introduces noise: overloaded (`@t.overload`)
  stub definitions and near-duplicate symbols across classes consume
  top-k slots without adding new information. This is a **chunking/retrieval
  interaction**, not purely an embedding-quality issue — the chunker
  correctly preserves overload stubs as separate nodes, but semantic
  similarity can't distinguish "stub" from "real implementation."
- Not yet tuned based on these results by design — the plan is to compare
  `text-embedding-3-small` vs. `text-embedding-3-large` on these same fixed
  queries before making any changes, so improvements are measured, not
  assumed.

## Log — what worked / what didn't

**Day 1:** Ingestion worked cleanly against `pallets/click` on the first
real run — 79 Python files found (later 90 after adding docs/examples
handling), all non-empty files read successfully.

**Day 2:** Built a poison-repo pytest fixture (binary, bad-encoding, huge,
generated, empty files) to deterministically test hardening rather than
relying on finding a naturally messy repo. Layered binary detection
(null-byte + printable-ratio heuristics + magic-number signatures) caught
a fake-PNG-signature file that heuristics alone would have missed.

**Day 3:** Found and fixed a real bug: `ast.FunctionDef.lineno` does not
include decorator lines, so decorators (`@click.command()`, `@dataclass`,
etc.) were being silently stripped from chunk content — significant for
this specific repo, since `click`'s entire public API is decorator-based.
Fixed with a shared `get_effective_start_lineno()` used across functions,
async functions, and classes alike, and refactored duplicated chunk-
building logic into one `build_chunk()` helper. Known remaining gap: a
class decorator (e.g. `@click.group()`) is lost when the class is split
into per-method chunks rather than kept as one chunk — not yet fixed.

**Day 4:** Verified OpenAI embeddings are unit-normalized (~1.0 L2 norm),
confirming `IndexFlatIP` scores are valid cosine similarities. Ran a full
k=1/3/5/10 sweep on 4 fixed queries; see Evaluation section above.