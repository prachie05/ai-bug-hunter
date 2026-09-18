# Embedding & Retrieval Evaluation

## Overview

This evaluation establishes a baseline for semantic code retrieval in AI Bug Hunter.

The pipeline evaluated was:

```text
Python repository
    ↓
AST-based chunking
    ↓
Metadata + source code
    ↓
OpenAI text-embedding-3-small
    ↓
FAISS IndexFlatIP
    ↓
Semantic query
    ↓
Top-k code chunks
```

The evaluation was performed on the real `pallets/click` repository.

## Embedding Configuration

* **Embedding model:** `text-embedding-3-small`
* **Embedding dimension:** 1536
* **Embedding input:** chunk metadata + source code
* **Vector store:** FAISS `IndexFlatIP`
* **Similarity:** inner product
* **Normalization:** embeddings were empirically verified to have unit norm (~1.0), so inner product is equivalent to cosine similarity for these vectors.

Example embedding verification:

```text
Embedding dimension: 1536
Embedding norm: 1.0003657353778976
```

## Retrieval Queries

Four fixed queries were selected based on real functionality in Click:

1. Where does Click parse command line arguments?
2. Where does Click resolve a command name to a command object?
3. Where does Click handle exceptions and convert them into error messages?
4. Where does Click invoke the callback function for a command?

Expected relevant symbols included:

* `parse_args`
* `resolve_command`
* `show` / related exception-handling logic
* `invoke`

## Results

Retrieval was tested with:

* `k = 1`
* `k = 3`
* `k = 5`
* `k = 10`

### k = 1

**3/4 queries produced a direct or strong top-1 result.**

| Query                        | Top result                       | Result                              |
| ---------------------------- | -------------------------------- | ----------------------------------- |
| Parse command line arguments | `core.py → parse_args`           | Direct hit                          |
| Resolve command name         | `core.py → resolve_command`      | Direct hit                          |
| Handle exceptions            | `exceptions.py → format_message` | Related, but not the primary target |
| Invoke callback              | `core.py → invoke`               | Direct/strong hit                   |

The exception-handling query was the weakest retrieval case.

### k = 3

All four expected functionalities appeared within the top 3 results.

The exception query was rescued by the presence of the relevant `show` method in the top 3.

However, some returned results were duplicate or closely related definitions of the same symbol.

### k = 5

All four expected functionalities remained present within the retrieved results.

Increasing `k` primarily added related or duplicate chunks rather than substantially different relevant functionality.

### k = 10

All four expected functionalities appeared within the top 10.

The larger result set exposed more retrieval redundancy, including repeated overloads, related methods, and duplicate symbol names.

## Observations

### 1. Semantic retrieval works on real repository code

The baseline successfully retrieves relevant Click implementation code from natural-language queries.

The system is not relying on exact keyword matching alone; queries such as "resolve a command name to a command object" successfully retrieved the `resolve_command` implementation.

### 2. Increasing k improves recall

The expected functionality was not always the first result, but increasing `k` allowed relevant chunks to appear in the candidate set.

The observed results were:

| k  | Expected functionality retrieved |
| -- | -------------------------------- |
| 1  | 3/4                              |
| 3  | 4/4                              |
| 5  | 4/4                              |
| 10 | 4/4                              |

### 3. Larger k introduces redundancy

Higher `k` values increasingly returned:

* overloaded methods
* repeated symbol names
* closely related implementations
* neighboring functionality

This means simply increasing `k` is not necessarily the best way to improve retrieval quality.

### 4. Exception handling is a harder retrieval case

The exception query retrieved `format_message`, `__str__`, and `show` because these functions are semantically related.

This demonstrates a limitation of pure semantic retrieval: several chunks can be conceptually relevant while only one contains the exact behavior being requested.

## Current Baseline

The current retrieval system provides a working semantic-search baseline:

* **Top-1:** 3/4 direct or strong results
* **Top-3:** 4/4 expected functionalities retrieved
* **Top-5:** 4/4
* **Top-10:** 4/4

No retrieval tuning was performed after establishing this baseline.

Potential future improvements include:

* duplicate/near-duplicate filtering
* reranking
* hybrid semantic + keyword/BM25 retrieval
* metadata-aware filtering
* improved query formulation
* evaluating `text-embedding-3-large`

These should be evaluated against this baseline rather than tuned before the baseline is recorded.

## Persistence

The FAISS index and chunk metadata are persisted locally so subsequent retrieval experiments do not require re-cloning and re-embedding the entire repository.

The persisted artifacts are intentionally excluded from Git because they are generated local data.

## Conclusion

Day 4 establishes that the embedding and retrieval pipeline works end-to-end on a real Python repository.

The baseline also identifies a concrete next retrieval problem: **relevant results are being retrieved, but higher `k` values can contain substantial redundancy.**

This gives the project a measurable baseline for future retrieval improvements.
