from src.investigator.benchmarks import BENCHMARKS
from src.investigator.graph import graph

for benchmark in BENCHMARKS:

    print("\n" + "=" * 60)
    print("ISSUE:", benchmark["issue"])
    print(
        "GROUND TRUTH:",
        benchmark["ground_truth_file"],
        "→",
        benchmark["ground_truth_symbol"]
    )

    initial_state = {
        "bug_description": benchmark["bug_description"],
        "retrieved_chunks": [],
        "retrieval_k": 10,
    }

    result = graph.invoke(initial_state)

    if result.get("error"):
        print("ERROR:", result["error"])
        continue

    hypothesis = result["hypothesis"]

    print("\nPREDICTED:")
    print("File:", hypothesis.file_path)
    print("Symbol:", hypothesis.symbol)
    print("Parent:", hypothesis.parent_class)
    print("Confidence:", hypothesis.confidence)
    print("Reasoning:", hypothesis.reasoning)