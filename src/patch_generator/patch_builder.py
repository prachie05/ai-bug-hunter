import os 
import difflib

def build_patch(repo_path, file_path, old_code, new_code):
    full_path = os.path.join(repo_path, file_path)

    if not os.path.exists(full_path):
        raise FileNotFoundError(full_path)

    with open(full_path, "r") as file:
        content = file.read()

    count = content.count(old_code)

    if count!=1 :
        raise ValueError("Old Code must occur exactly once in the file")

    new_content = content.replace(old_code, new_code)

    diff = difflib.unified_diff(
    content.splitlines(keepends=True),
    new_content.splitlines(keepends=True),
    fromfile=f"a/{file_path}",
    tofile=f"b/{file_path}",
    n=3,
    )

    return "".join(diff)