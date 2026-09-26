# AI Bug Hunter

An agentic system that investigates real GitHub repositories, locates code relevant to a bug report, and generates and validates a fix.

The project is being built incrementally to explore **real agentic software-engineering pipelines** rather than wrapping a single LLM call around a codebase. Each stage is evaluated against real repositories, real code, and known bugs wherever possible.

**Primary benchmark repository:** [`pallets/click`](https://github.com/pallets/click)

**Cross-repository validation:** [`psf/requests`](https://github.com/psf/requests)

---

# Status

* [x] **Day 1** — Repository ingestion
* [x] **Day 2** — Ingestion hardening
* [x] **Day 3** — AST-based code chunking
* [x] **Day 4** — Swappable embeddings + FAISS retrieval + baseline evaluation
* [x] **Day 5** — Embedding comparison + retrieval tuning + overload filtering
* [x] **Day 6** — LangGraph investigator + hybrid retrieval + real-bug benchmarking + cross-repository validation
* [x] **Day 7** — Repository caching + configuration + reusable pipeline + FastAPI service
* [x] **Day 8** — Docker sandbox + disposable repository workspaces
* [x] **Day 9** — Regression test generation + sandbox test execution
* [x] **Day 10** — Patch generation + deterministic patch construction
---

# Project Goal

The eventual system is intended to take a bug report such as:

> "After a redirect, `Response.history` can contain a reference to the response itself."

and automatically:

1. Clone the target repository.
2. Ingest and filter its source files.
3. Parse the code into meaningful AST-based chunks.
4. Build semantic and lexical indexes.
5. Retrieve potentially relevant code.
6. Investigate the retrieved candidates using an LLM.
7. Identify the most likely root-cause location.
8. Generate a regression test.
9. Generate a patch.
10. Run the patch in an isolated environment.
11. Validate the result.
12. Re-plan if the patch fails.

The current implementation reaches **patch generation and safe patch application**. Validation and replanning are the next stages.

---

# Architecture

```text
GitHub repository URL + bug report
                |
                v
+---------------------------+
| FastAPI Service           |
| /investigate              |
+---------------------------+
                |
                v
+---------------------------+
| Repository Cache          |
| repo URL + revision       |
+---------------------------+
                |
          cache hit?
          /       \
        yes        no
         |          |
         |          v
         |   Repository Ingestion
         |          |
         |          v
         |     AST Chunking
         |          |
         |          v
         |    Embedding + FAISS
         |          |
         |          v
         |      Save Cache
         |          |
         +----+-----+
              |
              v
+---------------------------+
| BM25 Lexical Index        |
+---------------------------+
              |
              v
+---------------------------+
| Hybrid Retrieval          |
| Semantic + BM25 + RRF     |
+---------------------------+
              |
              v
+---------------------------+
| LangGraph Investigator    |
| bug report + candidates    |
+---------------------------+
              |
              v
+---------------------------+
| Structured Hypothesis      |
| file / symbol / class      |
| reasoning / confidence     |
+---------------------------+
              |
              v
+---------------------------+
| Test Generator            |
+---------------------------+
              |
              v
+---------------------------+
| Docker Sandbox             |
| Regression Test            |
+---------------------------+
              |
              v
+---------------------------+
| Patch Generator            |
| file / old_code / new_code |
+---------------------------+
              |
              v
+---------------------------+
| Deterministic Patch Builder|
| Python difflib             |
+---------------------------+
              |
              v
+---------------------------+
| git apply --check          |
+---------------------------+
              |
              v
+---------------------------+
| git apply                  |
+---------------------------+
              |
              v
+---------------------------+
| Test Validator             |
+---------------------------+
              |
              v
+---------------------------+
| Replanner                  |
+---------------------------+
```

The investigation stage originally began as a single LangGraph node. The larger multi-stage graph is being introduced incrementally as each component becomes reliable enough to justify the next stage.

---

# Day 1 — Repository Ingestion

The first stage builds the foundation for everything downstream.

The ingestion pipeline:

* clones a GitHub repository
* walks the repository tree
* identifies Python source files
* filters irrelevant files
* reads source code
* returns normalized source-file objects

The initial implementation was tested against the real `pallets/click` repository.

The main goal of Day 1 was not sophisticated intelligence. It was establishing a reliable boundary between an arbitrary GitHub repository and the rest of the system.

---

# Day 2 — Ingestion Hardening

Real repositories contain files that should not blindly enter a Python parser or embedding pipeline.

A deterministic **poison-repository test fixture** was created containing:

* binary files
* files with invalid UTF-8
* very large files
* generated files
* empty files
* files with misleading extensions

## Binary detection

Binary detection uses multiple signals rather than relying on a single heuristic:

* NUL-byte detection
* printable-character ratio
* known binary/magic signatures
* inspection of the first 8192 bytes

This caught cases such as a fake PNG signature that a simple text heuristic could otherwise mishandle.

## Encoding fallback

Source files are first decoded as UTF-8.

If that fails, the ingestion layer falls back to CP1252 rather than immediately discarding the file.

## Generated files

Generated files are **not automatically discarded**.

Instead, they are retained and tagged with:

```text
is_generated = True
```

This preserves potentially useful context while allowing later stages to treat generated code differently if necessary.

The goal was to make ingestion deterministic and robust before adding any LLM-based behavior.

---

# Day 3 — AST-Based Code Chunking

Embedding an entire source file as one document creates poor retrieval granularity.

Day 3 introduced AST-based chunking using Python's `ast` module.

Supported chunk types include:

* functions
* async functions
* methods
* classes
* module-level code
* class headers

Each chunk stores metadata including:

```text
file_path
start_line
end_line
node_type
name
parent_class
is_generated
content
```

## Exact source preservation

The chunker deliberately slices source from the **original file** rather than using:

```python
ast.unparse(...)
```

This preserves:

* formatting
* comments
* decorators
* whitespace
* the author's original source representation

## Decorator bug discovered

`ast.FunctionDef.lineno` points to the function definition rather than the first decorator.

That meant decorator lines could silently disappear from chunks.

A shared:

```text
get_effective_start_lineno()
```

helper was introduced so functions and classes include their decorators when appropriate.

A single `build_chunk()` helper then centralizes source slicing.

## Class chunking

Classes are not mechanically treated as one giant chunk.

The current strategy is:

* classes with multiple methods → split into method-level chunks
* simple data/container classes → keep as a single chunk

This provides more useful retrieval granularity while avoiding unnecessary fragmentation.

## Deliberate V1 simplifications

Nested functions remain inside their enclosing function's chunk.

One known remaining edge case is that a **class decorator can be lost when a class is split into per-method chunks**.

This is documented rather than silently ignored.

---

# Day 4 — Embeddings + FAISS Retrieval

Day 4 introduced a swappable embedding abstraction.

```text
EmbeddingBackend
        |
        +-- OpenAIEmbeddingBackend
```

The current default model is:

```text
text-embedding-3-small
```

The embedding layer is intentionally independent of the retrieval/indexing layer so that different embedding models can be evaluated without rewriting the pipeline.

## Embedding text

Chunks are converted into searchable text containing contextual metadata such as:

* file path
* symbol name
* chunk type
* parent class where applicable
* source content

## FAISS

Semantic search uses:

```text
FAISS IndexFlatIP
```

The embeddings were verified to be approximately unit-normalized, meaning inner product behaves as cosine similarity for these vectors.

Each FAISS vector maintains a positional mapping back to its original `CodeChunk`.

---

# Day 4 Baseline Evaluation

Four fixed retrieval queries were evaluated against real `pallets/click` chunks.

| Query                                                            | Expected target            |       Top-1 | Top-3 |
| ---------------------------------------------------------------- | -------------------------- | ----------: | ----: |
| Where does Click parse command line arguments?                   | `core.py::parse_args`      |         Yes |   Yes |
| Where does Click resolve a command name to a command object?     | `core.py::resolve_command` |         Yes |   Yes |
| Where does Click handle exceptions and convert them to messages? | `exceptions.py::show`      | No — rank 3 |   Yes |
| Where does Click invoke the callback for a command?              | `core.py::invoke`          |         Yes |   Yes |

### Result

**Top-1: 3/4**

**Top-3: 4/4**

This established a concrete baseline before introducing additional retrieval techniques.

---

# Day 5 — Embedding Model Comparison

Two OpenAI embedding models were evaluated using the same repository, chunks, and fixed queries.

| Metric              | `text-embedding-3-small` | `text-embedding-3-large` |
| ------------------- | -----------------------: | -----------------------: |
| Dimensions          |                     1536 |                     3072 |
| Full embedding pass |                ~$0.00495 |                ~$0.03219 |
| Relative cost       |                       1× |                    ~6.5× |

## Retrieval accuracy

| Model                    | k=1 | k=3 | k=5 |  k=10 |
| ------------------------ | --: | --: | --: | ----: |
| `text-embedding-3-small` | 3/4 | 4/4 | 4/4 | 3–4/4 |
| `text-embedding-3-large` | 2/4 | 3/4 | 3/4 |   3/4 |

At k=1, the large model's misses were qualitatively poor in two cases:

* raw module imports
* an empty `@overload` stub

The smaller model therefore matched or outperformed the larger model across every tested k while costing approximately 6.5× less for the full embedding pass.

**Decision:** `text-embedding-3-small` became the V1 default.

This is a benchmark-specific result, not a claim that the smaller model is universally better.

---

# Day 5 — Overload Filtering

The retrieval benchmark exposed another issue.

`@overload` functions describe typing signatures but do not contain the executable implementation.

They were therefore consuming retrieval candidate slots without providing useful implementation context.

The chunker was updated to detect and filter overload stubs.

```text
Click chunks:

1,380 → 1,340
```

The filter **did not materially improve top-1 accuracy** on the four fixed queries.

That distinction is important:

> The overload filter improved the quality of the candidate pool, but this experiment did not demonstrate an accuracy improvement.

It was therefore kept as an engineering precision improvement rather than being presented as a benchmark win.

A separate unresolved issue was also identified: legitimate duplicate method names across unrelated classes still require contextual disambiguation.

---

# Day 6 — Investigator + Hybrid Retrieval

Day 6 moved the project from:

> "Which code looks semantically similar?"

toward:

> "Given these candidates, where is the most likely root cause?"

## Investigator Schema

The investigator returns a structured hypothesis:

```text
file_path
symbol
parent_class
reasoning
confidence
```

`confidence` is explicitly defined as confidence in the **root-cause location**, rather than confidence that the code is merely related to the bug.

`parent_class` was added because real repositories frequently contain repeated method names.

A symbol name alone is therefore insufficient to uniquely identify a location.

---

# Hybrid Retrieval

Semantic retrieval alone has a vocabulary limitation.

A bug report may describe a **symptom**, while the responsible implementation may use completely different terminology.

For example:

```text
"boolean flag remains at its default value"
```

may lead to code involving:

```text
flag_value
is_bool_flag
consume_value
```

without explicitly containing the words from the bug report.

To supplement semantic retrieval, BM25 lexical search was added using `rank-bm25`.

The pipeline now retrieves:

```text
Semantic search → top 20
BM25 search     → top 20

                    |
                    v

             Reciprocal Rank Fusion

                    |
                    v

               requested top-k
```

## Why RRF?

Semantic and BM25 scores are on different scales.

Instead of inventing a weighted combination such as:

```text
0.7 * semantic + 0.3 * BM25
```

the system uses **Reciprocal Rank Fusion**.

RRF combines the rank positions of candidates without requiring an experimentally chosen score-weighting constant.

---

# Click Real-Bug Benchmark

Four real, closed `pallets/click` issues were selected.

Unlike the Day 4/5 queries, these represent actual bug-report-style investigation:

> symptom → relevant code → likely root cause

The benchmark records the historical fix location as ground truth.

| Issue | Recorded ground truth                   | GT retrieved? | Investigator prediction    | Classification        |
| ----- | --------------------------------------- | ------------- | -------------------------- | --------------------- |
| #2897 | `core.py::Option.__init__`              | No            | `Option.is_bool_flag`      | Retrieval failure     |
| #2906 | `shell_completion.py::_resolve_context` | No            | `Command.shell_complete`   | Unexamined candidate* |
| #3084 | `core.py::Option.__init__`              | No            | `Option._infer_flag_kind`  | Benchmark ambiguity   |
| #2952 | `core.py::Option.__init__`              | No            | `Option.value_from_envvar` | Benchmark ambiguity   |

### Exact ground-truth recall

**0/4**

Hybrid RRF retrieval did not improve exact recorded-ground-truth recall over semantic retrieval for this benchmark.

However, treating this as simply:

> "The investigator failed 4/4"

would hide important information.

---

# Failure Categories

## #2897 — Retrieval failure

The recorded implementation never entered the candidate set.

The investigator therefore selected a related property with plausible reasoning, but it did not have access to the recorded ground-truth implementation.

This is primarily a **retrieval failure**.

## #2906 — Unexamined candidate

A better-aligned `_resolve_*` candidate was present in the retrieved set, but the investigator did not engage with or rule out that candidate.

Instead, its reasoning focused on a more public-facing method.

This is different from a confirmed reasoning failure because the unexamined candidate was not independently verified to be sufficient to change the diagnosis.

However, it is also different from a clean retrieval failure because more relevant code **was available**.

## #3084 — Benchmark ambiguity

The recorded ground truth is where the historical patch landed:

```text
Option.__init__
```

The investigator instead identified:

```text
Option._infer_flag_kind
```

and produced a detailed causal argument involving:

* the exact conditional controlling flag behavior
* `Option.consume_value`
* sentinel handling
* the associated regression test

This is an important distinction:

> A prediction that differs from the historical patch location is not automatically a reasoning failure.

The benchmark is measuring **patch location agreement**, while the investigator is attempting **conceptual root-cause localization**.

## #2952 — Benchmark ambiguity

Similarly, the recorded patch location was `Option.__init__`, while the investigator selected another implementation involved in environment-variable/value handling.

This requires further source-level investigation before classifying the prediction as simply wrong.

---

# What Day 6 Actually Demonstrated

The Click benchmark revealed two important bottlenecks.

## 1. Retrieval remains the main limitation

The recorded ground-truth chunks were absent from the candidate set in all four cases.

This means the investigator cannot recover a missing implementation regardless of how good its reasoning is.

## 2. Ground truth needs careful interpretation

A historical patch location is useful ground truth, but it is not always identical to conceptual root cause.

This matters particularly for constructor-heavy code where:

* the constructor performs parameter reconciliation
* the actual behavior emerges elsewhere
* the bug report describes the resulting behavior rather than the constructor's internal assignments

Three of the four recorded ground-truth locations were:

```text
Option.__init__
```

This terse, assignment-heavy implementation shares relatively little vocabulary with symptoms such as:

```text
"boolean flag stays at its default"
```

That vocabulary mismatch is a plausible explanation for the retrieval failures.

## Next Candidate Experiment

Query rewriting / HyDE is a natural next experiment:

```text
Bug report
    ↓
Hypothetical fix / implementation description
    ↓
Embedding
    ↓
Retrieval
```

Rather than embedding only the bug report's vocabulary, retrieval could use a generated description of what the responsible implementation might look like.

This remains future work rather than a claimed improvement.

---

# Cross-Repository Validation — Requests #7328

The original Day 6 plan included dogfooding the system on its own repository.

Instead, an independent validation was performed against a real historical bug from an unrelated repository:

[`psf/requests`](https://github.com/psf/requests)

This was an intentional substitution because a second, unfamiliar repository provides a different form of evidence than testing against code the system itself helped produce.

The repository was checked out at the pre-fix revision.

## Bug

Requests issue #7328 involved `Response.history` incorrectly containing a reference to the response itself, creating the possibility of looping when traversing redirect history.

## Investigation

The full investigation pipeline was executed:

```text
Requests repository
        ↓
36 Python files
        ↓
670 AST chunks
        ↓
OpenAI embeddings
        ↓
FAISS + BM25
        ↓
Hybrid RRF retrieval
        ↓
LangGraph investigator
```

### Semantic retrieval

The actual responsible implementation:

```text
SessionRedirectMixin.resolve_redirects
```

was ranked **#5** by semantic retrieval.

The top four results were tests describing expected behavior rather than the implementation itself.

### Hybrid retrieval

RRF moved:

```text
resolve_redirects
```

from **#5 → #2**.

This is a concrete measured improvement from combining lexical and semantic signals on this example.

### Investigator result

The investigator selected:

```text
src/requests/sessions.py

SessionRedirectMixin.resolve_redirects
```

with high confidence.

It distinguished this from:

```text
get_redirect_target
```

which is involved in detecting redirects but does not perform the relevant history mutation.

### Historical fix verification

The actual historical fix for Requests issue #7328 modified this same redirect-history area.

Therefore this experiment is classified as a:

**verified root-cause localization success.**

This remains **one independent repository example** and should therefore be described as successful transfer to a second repository rather than proof of broad cross-repository generalization.

---

# Day 7 — Repository Caching + Service Layer

Day 7 moved the project from a benchmark-oriented collection of scripts toward a reusable investigation service.

The main goal was to make the investigation pipeline callable through an API while avoiding unnecessary repository processing and embedding costs.

## Repository + Revision Caching

Repository processing can be expensive because it may require:

```text
clone
  ↓
ingestion
  ↓
AST chunking
  ↓
embedding
  ↓
FAISS indexing
```

A cache was introduced using:

```text
repo URL + revision
```

as the cache identity.

The cache structure is:

```text
data/cache/

    <repo-hash>/

        embeddings.index

        chunks.pkl
```

The investigator result itself is **not cached**, because different bug descriptions against the same repository should produce fresh hypotheses.

BM25 is also rebuilt when loading a cached repository because it is inexpensive compared with embedding the entire repository again.

### Cache behavior

The implementation was tested for:

```text
Same repo + same revision
        → cache hit

Same repo + different revision
        → cache miss

Original revision again
        → cache hit
```

This prevents repeated cloning, chunking, and full-repository embedding for the same repository revision.

A future improvement will be resolving `HEAD` to its actual commit SHA before constructing the cache key so that a moving branch cannot map to stale cached content.

---

# Configuration

Environment-based configuration was added using `.env` and `python-dotenv`.

The following values can now be configured without changing source code:

```text
OPENAI_API_KEY
EMBEDDING_MODEL
INVESTIGATOR_MODEL
```

Stable application settings remain in `src/config.py`, including:

```text
EMBEDDING_DIMENSION
RETRIEVAL_K
CACHE_DIR
```

The `.env` file is excluded from version control.

---

# Reusable Investigation Pipeline

The previous Requests experiment was extracted into a reusable:

```text
investigate_repo()
```

pipeline.

The function now handles:

```text
repository
    ↓
cache lookup
    ↓
ingestion if required
    ↓
chunking
    ↓
embedding + FAISS
    ↓
BM25
    ↓
hybrid retrieval
    ↓
investigator
    ↓
structured hypothesis
```

Benchmark-specific retrieval printing and experiment scaffolding were separated from the core service path.

---

# FastAPI Service

A FastAPI service was added with:

```text
POST /investigate
```

The endpoint accepts:

```json
{
  "repo_url": "https://github.com/psf/requests.git",
  "bug_description": "Response.history can contain a reference to the Response object itself after redirects.",
  "k": 5,
  "revision": "HEAD"
}
```

The retrieval depth `k` and repository revision are configurable per request.

The API returns:

```json
{
  "evidence_chunks": [...],
  "hypothesis": {
    "file_path": "src/requests/sessions.py",
    "symbol": "resolve_redirects",
    "parent_class": "SessionRedirectMixin",
    "reasoning": "...",
    "confidence": 0.9
  }
}
```

The service therefore exposes the investigator as a reusable boundary:

```text
Repository URL
Bug description

      ↓

POST /investigate

      ↓

Evidence + structured hypothesis
```

API failures are converted into HTTP error responses rather than leaking unhandled exceptions through the service boundary.

---

# Day 8 — Docker Sandbox + Disposable Workspaces

Day 8 introduced isolated execution for generated code.

The sandbox uses Docker to execute generated tests against repository copies rather than the original working repository.

The sandbox enforces:

* isolated container execution
* disabled network access
* memory limits
* CPU limits
* execution timeout
* automatic container cleanup

The repository is mounted into the container as:

```text
/repo
```

and tests are executed using `pytest`.

## Disposable repository copies

A disposable workspace helper was introduced:

```text
src/sandbox/workspace.py
```

The helper:

1. creates a temporary directory
2. copies the repository into it
3. excludes `.git`
4. yields the temporary repository path
5. deletes the workspace afterward

This establishes an important safety boundary:

```text
Original repository
        |
        | never directly modified
        v
Disposable repository copy
        |
        v
Docker sandbox
```

The eventual full pipeline will reuse one disposable workspace across test generation, test execution, patch application, and post-patch validation.

---

# Day 9 — Regression Test Generator

Day 9 introduced an LLM-based regression test generator.

The generator receives:

```text
bug description
investigator hypothesis
retrieved implementation chunks
```

and returns a structured:

```text
GeneratedTest
    |
    +-- test_code
    +-- description
```

The generated test is then written into a disposable repository copy and executed inside the Docker sandbox.

## Sandbox result classification

The sandbox returns structured execution information including:

```text
passed
exit_code
output
ran_successfully
assertion_failed
timed_out
```

This distinguishes basic failure classes such as:

```text
test passed
test assertion failed
test execution failed
test timed out
```

The current assertion classification is intentionally simple and is a V1 implementation rather than a complete pytest error parser.

## Important lesson

Testing the generator against real bugs exposed a critical failure mode:

> An LLM can invent behavior or construct an artificial reproduction that does not actually correspond to the historical bug.

For example, an early Click regression test passed on both buggy and fixed versions, meaning it was not a valid regression test.

This established an important rule for the later pipeline:

**A generated test is evidence, not ground truth.**

A test must fail on the buggy revision and pass on the fixed revision before it can be treated as a meaningful regression test.

Day 9 therefore established the test-generation and execution infrastructure without claiming that generated tests are automatically correct.

---

# Day 10 — Patch Generator + Deterministic Patch Construction

Day 10 introduced automated patch generation and safe patch application.

The initial design asked the LLM to directly produce a Git unified diff.

That approach exposed a specific reliability problem:

> The model could identify the correct implementation change but produce malformed unified-diff hunk arithmetic.

For example, the model could generate an incorrect:

```text
@@ -X,Y +A,B @@
```

header even when the actual code change was correct.

Instead of adding increasingly complicated prompt instructions for arithmetic, the architecture was changed to **remove diff construction from the LLM's responsibilities entirely**.

## New Patch Generator Contract

The LLM now returns a structured implementation change:

```text
GeneratedPatch

file_path
old_code
new_code
description
```

The model is responsible for answering:

> **What code should change?**

It is no longer responsible for answering:

> **How do I encode that change as a valid Git diff?**

### Deterministic Patch Builder

A new:

```text
src/patch_generator/patch_builder.py
```

was introduced.

The patch builder:

1. resolves the repository-relative file path
2. verifies that the file exists
3. reads the actual repository source
4. checks that `old_code` occurs exactly once
5. replaces `old_code` with `new_code`
6. uses Python's `difflib.unified_diff()` to compare the original and modified content
7. generates the unified diff deterministically

The resulting diff is then passed to the existing patch applier.

### Architecture

```text
LLM Patch Generator
        |
        | file_path
        | old_code
        | new_code
        | description
        v
Deterministic Patch Builder
        |
        | difflib.unified_diff()
        v
Git Unified Diff
        |
        v
git apply --check
        |
        v
git apply
```

### Why this architecture?

This separates **reasoning from deterministic formatting**.

The LLM handles the part that requires semantic understanding:

```text
"What implementation change fixes this bug?"
```

Python handles the part that should not depend on probabilistic generation:

```text
"Where are the changed lines?"
"How many lines are in the hunk?"
"What is the correct diff syntax?"
```

This eliminates the class of failures caused by LLM-generated hunk arithmetic.

### Exact source matching

The patch builder requires:

```text
old_code.count(...) == 1
```

If the old code appears zero times or multiple times, the builder fails loudly rather than guessing.

This prevents:

* silent partial matches
* accidental replacement of the wrong occurrence
* whitespace mismatch being ignored
* ambiguous replacement locations

### Git safety

Before mutation, the generated diff is passed through:

```text
git apply --check
```

Only a mechanically valid patch is then applied using:

```text
git apply
```

This gives the patch pipeline a deterministic validation boundary before modifying the disposable repository.

### Requests validation

The architecture was validated against the Requests redirect-history bug.

The LLM produced:

```text
file_path:
src/requests/sessions.py

old_code:
hist.append(resp)
resp.history = hist[1:]

new_code:
resp.history = hist[:]
hist.append(resp)
```

The deterministic builder converted this structured change into a valid unified diff, which was accepted by `git apply`.

The generated implementation change also matched the historical fix.

This demonstrates successful **patch-generation mechanics**, but does not yet prove that the generated regression test and patch actually fix the bug.

That verification belongs to Day 11.

## V1 Patch Scope

The current Patch Generator supports **one implementation-file change per generated patch**.

Multi-file patches are intentionally deferred until a concrete bug requires them.

---

# Structured-Output Failure Handling

The investigator uses Pydantic structured output:

```text
InvestigatorHypothesis
```

The underlying LangGraph investigator catches LLM/API/structured-output failures and records:

```text
hypothesis = None

error = <error message>
```

This keeps failures inside the graph state model and leaves room for future retry/replanning behavior.

The current implementation intentionally does not implement retries yet.

---

# Engineering Lessons So Far

## 1. Retrieval quality matters before agent complexity

Adding an LLM investigator does not solve missing candidates.

If the relevant implementation never reaches the investigator, better reasoning cannot recover it.

This makes retrieval evaluation a first-class part of the project rather than a hidden implementation detail.

## 2. Benchmark labels need to match the question being asked

A historical patch location is useful ground truth, but it is not always identical to conceptual root cause.

Future evaluations should distinguish:

```text
patch location

implementation responsible for behavior

conceptual root cause
```

where possible.

## 3. Real repositories expose problems synthetic tests hide

The project has already encountered:

* decorators being lost during AST slicing
* generated files
* binary files
* encoding failures
* overload stubs
* duplicate symbols
* vocabulary mismatch
* repository revision/caching concerns
* patch-location vs root-cause ambiguity
* LLM-generated regression tests that encode unsupported behavior
* LLM-generated patch hunk arithmetic failures

These emerged from working with actual repositories rather than only toy examples.

## 4. More powerful models are not automatically better

The larger embedding model was more expensive and performed worse on the fixed benchmark.

The project therefore treats model selection as an empirical engineering decision rather than assuming a larger model is automatically superior.

## 5. Agent architecture should be earned

The eventual system is intended to contain multiple stages and replanning.

However, the project deliberately started with:

```text
retrieve → investigate
```

before introducing:

```text
retrieve → investigate → generate test → patch → validate → replan
```

This makes it possible to identify which component actually fails instead of hiding failures inside a large agent loop.

## 6. Expensive computation should be cached

Repository ingestion, chunking, and full-repository embedding are deterministic for a fixed repository revision.

Caching these artifacts makes repeated investigations substantially cheaper while still allowing different bug reports to reuse the same repository representation.

## 7. LLMs should not own deterministic transformations

Day 10 demonstrated a broader engineering principle:

> If a task is deterministic and mechanically verifiable, it should be handled by deterministic software rather than delegated to an LLM.

The LLM is useful for determining:

```text
old_code → new_code
```

Python is better suited to determining:

```text
old file + new file → valid unified diff
```

This reduces the LLM's failure surface without reducing its role in semantic reasoning.

---

# Current Limitations

The current system does **not yet**:

* reliably generate valid regression tests for arbitrary bugs
* prove generated tests reproduce the historical bug automatically
* validate generated patches against the full repository test suite
* re-plan retrieval based on validator failures
* perform query rewriting / HyDE
* fully disambiguate duplicate symbols across classes
* resolve moving `HEAD` references to immutable commit SHAs for caching
* support multi-file patches
* support all programming languages
* establish broad cross-repository generalization
* provide complete pytest failure classification

The current Patch Generator is also intentionally limited to **one implementation-file change per patch**.

The initial Click evaluation used a dedicated benchmark path, while the Requests validation demonstrated that the underlying investigation architecture can operate on a second unfamiliar repository.

These are intentional V1 boundaries rather than hidden gaps.

---

# What's Next

The next stage is the **Test Validator**.

```text
Generated regression test
        ↓
Run against buggy revision
        ↓
Expected: FAIL
        ↓
Apply generated patch
        ↓
Run regression test
        ↓
Expected: PASS
        ↓
Run existing test suite
        ↓
Expected: no new failures
```

The validator will establish whether the patch actually fixes the reported bug rather than merely being syntactically applicable.

After that:

```text
Day 11
Test Validator
        ↓
Day 12
Full linear pipeline
        ↓
Day 13–14
Integration hardening + logging + traces
        ↓
Future
Replanning
```

Future retrieval work may also investigate:

```text
Bug report
    ↓
Query rewriting / HyDE
    ↓
Retrieval
```

but this will be evaluated experimentally rather than assumed to improve performance.

---

# Development Log

### Day 1

Built the initial repository ingestion pipeline and verified it against real `pallets/click` source.

### Day 2

Built a deterministic poison-repository fixture to test ingestion hardening. Added layered binary detection, encoding fallback, large-file handling, and generated-file detection.

### Day 3

Built AST-based chunking and discovered a real decorator-line bug caused by `ast.FunctionDef.lineno`. Fixed it with shared decorator-aware source slicing. Documented the remaining class-decorator edge case.

### Day 4

Added the swappable embedding backend and FAISS vector store. Verified embedding normalization and established a 3/4 top-1, 4/4 top-3 retrieval baseline.

### Day 5

Compared `text-embedding-3-small` and `text-embedding-3-large`. The smaller model matched or outperformed the larger model across tested k values at approximately 6.5× lower cost. Added `@overload` filtering and documented the distinction between candidate precision and measured accuracy.

### Day 6

Built the LangGraph investigator with structured Pydantic output and added hybrid semantic + BM25 retrieval using RRF.

Evaluated four real Click issues and found **0/4 exact recorded-ground-truth recall**. Rather than treating this as four identical failures, the results were separated into retrieval failure, an unexamined candidate, and benchmark-ambiguity cases.

The originally planned self-repository dogfood test was intentionally substituted with an independent validation on a real historical Requests issue. The pipeline successfully localized the responsible `resolve_redirects` implementation, hybrid retrieval moved it from rank 5 to rank 2, and the historical fix was verified to modify the same redirect-history logic.

Added graceful structured-output failure handling so malformed or failed LLM responses are captured in `state.error` with `hypothesis=None` rather than crashing the graph.

### Day 7

Added repository/revision-based caching so repeated investigations of the same repository revision can reuse stored FAISS embeddings and chunks instead of recloning, rechunking, and re-embedding the repository.

Added `.env`-based configuration for the OpenAI API key and model selection while keeping stable application settings in `src/config.py`.

Extracted the investigation logic into a reusable `investigate_repo()` pipeline and separated it from benchmark-specific experiment code.

Added a FastAPI `/investigate` endpoint with Pydantic request/response schemas, configurable retrieval depth, optional repository revision, and API-level error handling.

Verified the service using the Requests #7328 bug. The API returned evidence chunks and a structured hypothesis identifying `SessionRedirectMixin.resolve_redirects` as the likely root-cause location with 0.9 confidence.

### Day 8

Introduced Docker-based sandbox execution for generated tests.

Added disposable repository copies so generated code is executed against isolated repository workspaces rather than the original repository.

Added sandbox resource controls including network isolation, memory limits, CPU limits, execution timeouts, and automatic container cleanup.

### Day 9

Built the LLM Test Generator with structured `GeneratedTest` output.

Connected generated tests to the Docker sandbox and added structured execution results for pass/fail, assertion failure, execution failure, and timeout cases.

Real-bug experimentation exposed that generated tests can invent unsupported behavior or construct unrealistic reproductions. This established the rule that generated tests are evidence rather than ground truth.

### Day 10

Built the Patch Generator and initially tested direct LLM-generated unified diffs.

The LLM successfully identified implementation changes but produced unreliable unified-diff hunk arithmetic.

Instead of continuing to prompt the model around arithmetic, the architecture was redesigned:

```text
LLM
 ↓
file_path + old_code + new_code
 ↓
Python patch builder
 ↓
difflib.unified_diff()
 ↓
git apply --check
 ↓
git apply
```

The deterministic builder now verifies that `old_code` occurs exactly once in the actual repository before constructing the patch.

Validated the architecture against Requests #7328. The LLM produced the correct historical implementation change, the Python builder generated a valid unified diff, and Git accepted the patch.

This establishes patch-generation **mechanics**, while actual bug-fix validation is intentionally deferred to Day 11.

---

# Current Takeaway

The project has now moved beyond:

> **"Can embeddings find relevant code?"**

to:

> **"Can an agent investigate a real bug report, identify the implementation responsible for the behavior, generate a regression test, and propose a mechanically valid implementation change?"**

The current evidence is mixed by design:

* semantic retrieval works well on straightforward code-location queries
* hybrid retrieval improves ranking in the Requests validation example
* real Click bug localization exposes significant retrieval limitations
* some benchmark disagreements are caused by ambiguity between historical patch location and conceptual root cause
* the investigator can make useful distinctions between competing candidates when the relevant implementation is available
* successful localization was verified on a second, unfamiliar repository
* repository caching now avoids repeating expensive indexing work for the same revision
* the investigation pipeline is exposed through a reusable FastAPI service
* generated tests can be unreliable and therefore cannot automatically be treated as ground truth
* patch generation benefits from separating LLM reasoning from deterministic patch construction
* `difflib` now handles unified-diff construction instead of relying on LLM-generated hunk arithmetic

The next major challenge is therefore not simply making the LLM "smarter."

It is building a retrieval → investigation → testing → patching → validation loop where every stage can be measured independently.
