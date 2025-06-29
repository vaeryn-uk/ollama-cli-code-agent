import os
from ocla.tools.file_system import generate_patch


def test_generate_patch(tmp_path):
    f = tmp_path / "t.txt"
    f.write_text("a\nb\nc\n")
    patch = generate_patch(str(f), "a\nb\nx\n")
    assert "--- " in patch and "+++ " in patch
    assert "-c" in patch
    assert "+x" in patch
