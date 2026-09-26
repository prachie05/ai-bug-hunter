import subprocess


def apply_patch(repo_path: str, patch: str):
    subprocess.run(
        ["git", "apply", "--check", "-"],
        input=patch,
        text=True,
        cwd=repo_path,
        check=True,
    )

    subprocess.run(
        ["git", "apply", "-"],
        input=patch,
        text=True,
        cwd=repo_path,
        check=True,
    )




