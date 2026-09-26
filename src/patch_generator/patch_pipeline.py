from src.patch_generator.patch_generator import patch_generator
from src.patch_generator.patch_applier import apply_patch
from src.patch_generator.patch_builder import build_patch   


def generate_and_apply_patch(state, repo_path):
    result = patch_generator(state)

    generated_patch = result["generated_patch"]

    patch = build_patch(
        repo_path,
        generated_patch.file_path,
        generated_patch.old_code,
        generated_patch.new_code,
    )

    print("\nGENERATED PATCH")
    print("------------------")
    print(patch)


    apply_patch(repo_path=repo_path, patch=patch)

    return generated_patch