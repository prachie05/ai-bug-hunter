from src.patch_generator.patch_applier import apply_patch
from src.patch_generator.patch_builder import build_patch
from src.patch_generator.patch_generator import patch_generator


def generate_and_apply_patch(state, repo_path): 
    result = patch_generator(state)

    generated_patch = result["generated_patch"]

    print("\nOLD CODE")
    print(generated_patch.old_code)

    print("\nNEW CODE")
    print(generated_patch.new_code)

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