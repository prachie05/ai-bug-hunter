BENCHMARKS = [
    {
        "bug_description": """
        When upgrading from Click 8.1.8 to 8.2.0, boolean flags with a
        provided type are not parsed correctly. For example, an option using
        is_flag=True and type=click.BOOL remains at its default value even
        when the flag is provided on the command line.
        """,
        "ground_truth_file": "src/click/core.py",
        "ground_truth_symbol": "__init__",
        "ground_truth_parent_class": "Option",
        "issue": "#2897",
        "fix_pr": "#2930",
    },

    {
        "bug_description": """
        In Click 8.2.0, shell completion for commands inside nested groups
        is broken. Instead of completing the nested command's arguments or
        options, completion can repeatedly return the command name.
        """,
        "ground_truth_file": "src/click/shell_completion.py",
        "ground_truth_symbol": "_resolve_context",
        "ground_truth_parent_class": None,
        "issue": "#2906",
        "fix_pr": "#2935",
    },

    {
        "bug_description": """
        In Click 8.3.0, an option configured with is_flag=False and a
        flag_value can no longer be used without explicitly providing a
        value. Running the option without a value incorrectly produces an
        error saying that the option requires an argument.
        """,
        "ground_truth_file": "src/click/core.py",
        "ground_truth_symbol": "__init__",
        "ground_truth_parent_class": "Option",
        "issue": "#3084",
        "fix_pr": "#3152",
    },

    {
        "bug_description": """
        Click 8.2.2 fixes incorrect reconciliation between default,
        flag_value, and type for flag options, along with related parsing
        and normalization of environment variables.
        """,
        "ground_truth_file": "src/click/core.py",
        "ground_truth_symbol": "__init__",
        "ground_truth_parent_class": "Option",
        "issue": "#2952",
        "fix_pr": "#2956",
    },
]