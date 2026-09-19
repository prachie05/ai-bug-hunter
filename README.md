# AI Bug Hunter

An agentic system that investigates a real GitHub repo, locates the code relevant to a bug report, and (eventually) generates and validates a fix — built to test real agentic pipeline design, not a single-shot LLM wrapper.

Test repository used throughout: [`pallets/click`](https://github.com/pallets/click).

## Status

Currently through ingestion → chunking → retrieval, before the investigator agent and API layer are wired in.

* [x] Day 1 — Repo ingestion (clone, walk, filter, read Python files)
* [x] Day 2 — Ingestion hardening (binary/huge/generated/bad-encoding files)
* [x] Day 3 — AST-based chunking (functions, methods, classes, decorators)
* [x] Day 4 — Swappable embeddings + FAISS retrieval, baseline evaluation
* [x] Day 5 — Embedding model comparison, retrieval evaluation, overload filtering
* [ ] Day 6 — LangGraph investigator agent
* [ ] Day 7 — FastAPI wrapper + cleanup

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file with your OpenAI API key:

```text
OPENAI_API_KEY=your-key-here
```

## Usage

Ingest a repo and check file discovery:

```bash
python -m scripts.run_ingest https://github.com/pallets/click
```

Run the retrieval pipeline:

```bash
python -m src.embeddings.test_retrieval
```

Run tests:

```bash
pytest tests/ -v
```

## Architecture (built so far)

```text
GitHub repo URL
      |
Repository ingestion (src/ingestion/)
  - clone, walk, filter (binary/huge/generated files skipped or flagged)
      |
AST chunking (src/chunker/)
  - functions, methods, classes -> CodeChunk objects
  - decorator-aware source slicing (exact original text, never ast.unparse())
      |
Embedding (src/embeddings/)
  - swappable EmbeddingBackend interface
  - OpenAI text-embedding-3-small (current retrieval baseline)
      |
FAISS vector store
  - IndexFlatIP, vector -> CodeChunk mapping, persisted to disk
      |
Retrieval
  - text query -> top-k relevant code chunks
```

## Design decisions worth noting

* **Source is sliced from the original file, never regenerated via `ast.unparse()`** — preserves exact formatting, comments, and decorators, since a bug-investigation tool needs to see precisely what the developer wrote.

* **Classes are chunked by behavior, not mechanically**: a class with 2+ methods is split into per-method chunks (with `parent_class` metadata); a simple data/container class becomes a single chunk.

* **Nested functions stay inside their enclosing function's chunk** — deliberate V1 simplification, not an oversight.

* **Generated files are kept, not excluded**, and tagged `is_generated` — generated code can still contain real bugs; the decision of whether to deprioritize it is left to later stages.

* **Embedding backend is swappable by design** (small → large → hybrid planned) so model comparisons are a configuration change, not a rewrite.

* **Overload stubs are filtered during chunking** — functions decorated with `@overload` are type-checking signatures rather than executable implementations, so keeping them as retrieval candidates can consume top-k slots without adding useful implementation context.

## Evaluation — Day 4 baseline

Four fixed test queries against real `pallets/click` chunks using `text-embedding-3-small` (1536-dim, verified unit-normalized so `IndexFlatIP` scores are directly interpretable as cosine similarity):

| Query                                                            | Expected target            | Top-1?      | In top-3? |
| ---------------------------------------------------------------- | --------------------------- | ----------- | --------- |
| Where does Click parse command line arguments?                   | `core.py::parse_args`       | Yes         | Yes       |
| Where does Click resolve a command name to a command object?     | `core.py::resolve_command`  | Yes         | Yes       |
| Where does Click handle exceptions and convert them to messages? | `exceptions.py::show`       | No (rank 3) | Yes       |
| Where does Click invoke the callback for a command?               | `core.py::invoke`           | Yes         | Yes       |

**Result: 3/4 correct at top-1, 4/4 within top-3.**

The baseline showed that semantic retrieval works on real, unmodified source rather than relying only on filename matching.

Larger k improves recall but can introduce noise: overloaded (`@overload`) stubs and similar symbols across classes can consume top-k slots without adding new implementation information.

## Evaluation — Day 5 embedding comparison

The same 1,380 chunks and 247,649 input tokens were used for both embedding models. The same four fixed queries and k values from the Day 4 baseline were re-run against `text-embedding-3-large` for a controlled comparison.

**Cost and normalization:**

| Metric                       | `text-embedding-3-small` | `text-embedding-3-large` |
| ----------------------------- | ------------------------: | ------------------------: |
| Dimensions                    |                      1536 |                      3072 |
| Chunks                        |                     1,380 |                     1,380 |
| Input tokens                  |                   247,649 |                   247,649 |
| Cost per full embedding pass  |                 ~$0.00495 |                 ~$0.03219 |
| Cost ratio                    |                        1× |                     ~6.5× |
| Measured time — run 1         |                    5.80 s |                    7.38 s |
| Measured time — later run     |                   12.78 s |                    9.34 s |

Latency varied between API runs, so the measurements are treated as observations rather than a claim that either model is consistently faster. The large model produced effectively unit-normalized embeddings (L2 norm ≈ 1.00018), so the same `IndexFlatIP` similarity interpretation applies to both.

**Retrieval accuracy (correct target found within top-k, out of 4 fixed queries):**

| Model                     | k=1 | k=3 | k=5 | k=10  |
| ------------------------- | :-: | :-: | :-: | :---: |
| `text-embedding-3-small`  | 3/4 | 4/4 | 4/4 | 3–4/4 |
| `text-embedding-3-large`  | 2/4 | 3/4 | 3/4 |  3/4  |

At k=1, `large`'s two misses were qualitatively worse than a near-match: the exception-handling query returned a chunk of raw `import` statements (`exceptions.py::<module>`) rather than any function, and the callback-invocation query returned an `@overload` stub (`def invoke(...) -> t.Any: ...`) with no executable body rather than the real implementation.

**Conclusion:** on this fixed Click benchmark, `text-embedding-3-small` matches or outperforms `text-embedding-3-large` at every k value tested, while costing roughly 6.5× less per embedding pass. There is no evidence here that the larger model improves retrieval quality for this task, so `text-embedding-3-small` is used as the V1 default embedding model.

## Evaluation — Day 5 retrieval and overload filtering

The four fixed retrieval queries were re-run with `text-embedding-3-small` at `k=1`, `3`, `5`, and `10` after the overload filtering change.

The overload filter is applied during chunking rather than retrieval: `@overload` definitions are excluded before embeddings are generated, so non-executable signatures do not occupy retrieval slots.

The filter reduced the Click corpus from **1,380 → 1,340 chunks**, removing **40 overload chunks (~2.9%)**.

The change successfully removes overload stubs from retrieval candidates, but it did **not materially change the top-1 result for the four benchmark queries**. This is a filtering/precision improvement in the candidate set, not evidence of improved retrieval accuracy.

One remaining retrieval weakness is the exception-handling query: `exceptions.py::format_message` ranked first for that query rather than the expected higher-level `show`/orchestration path. This indicates that semantic similarity can surface a closely related implementation detail rather than the exact behavioral entry point.

A separate, unresolved form of duplication also remains visible at higher k: multiple real (non-stub) implementations sharing the same method name across different classes — e.g. `invoke` implemented separately by `Command`, `MultiCommand`, and `Context` — legitimately occupy several top-k slots. This is a different root cause from the overload-stub issue (which has been fixed) and is left as a known, explicitly out-of-scope issue for now rather than something the V1 pipeline addresses.

The current V1 retrieval strategy therefore favors broad semantic recall and leaves deeper relevance reasoning to the investigator stage.

## Log — what worked / what didn't

**Day 1:** Ingestion worked cleanly against `pallets/click` on the first real run — 79 Python files found (later 90 after adding docs/examples handling), all non-empty files read successfully.

**Day 2:** Built a poison-repo pytest fixture (binary, bad-encoding, huge, generated, empty files) to deterministically test hardening rather than relying on finding a naturally messy repo. Layered binary detection (null-byte + printable-ratio heuristics + magic-number signatures) caught a fake-PNG-signature file that heuristics alone would have missed.

**Day 3:** Found and fixed a real bug: `ast.FunctionDef.lineno` does not include decorator lines, so decorators (`@click.command()`, `@dataclass`, etc.) were being silently stripped from chunk content — significant for this specific repo, since Click's public API is heavily decorator-based.

Fixed with a shared `get_effective_start_lineno()` used across functions, async functions, and classes alike, and refactored duplicated chunk-building logic into one `build_chunk()` helper.

Known remaining gap: a class decorator (e.g. `@click.group()`) is lost when the class is split into per-method chunks rather than kept as one chunk — not yet fixed.

**Day 4:** Verified OpenAI embeddings are unit-normalized (~1.0 L2 norm), confirming `IndexFlatIP` scores are valid cosine similarities. Ran the baseline k=1/3/5/10 retrieval sweep on four fixed queries.

**Day 5:** Compared `text-embedding-3-small` and `text-embedding-3-large` on the same corpus using the same fixed queries and k values. `large` matched or underperformed `small` at every k tested (including two qualitatively bad misses at k=1) while costing ~6.5× more — `small` remains the V1 default. Added chunking-time filtering for `@overload` definitions, reducing the retrieval corpus by 40 chunks; this improved candidate-set precision but did not materially change top-1 accuracy on the fixed benchmark. A separate, legitimate form of duplication (same method name implemented across multiple real classes) remains and is documented as a known open issue rather than addressed today.