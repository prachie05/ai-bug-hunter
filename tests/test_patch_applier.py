
from pathlib import Path

from src.patch_generator.patch_applier import apply_patch


def test_apply_patch(tmp_path):
    repo_path = tmp_path

    source_dir = repo_path / "src"
    source_dir.mkdir()

    source_file = source_dir / "example.py"

    source_file.write_text(
        """def add(a, b):
    return a - b
"""
    )

    patch = """--- a/src/example.py
+++ b/src/example.py
@@ -1,2 +1,2 @@
 def add(a, b):
-    return a - b
+    return a + b
"""

    apply_patch(str(repo_path), patch)

    updated_content = source_file.read_text()

    assert "return a + b" in updated_content
    assert "return a - b" not in updated_content
