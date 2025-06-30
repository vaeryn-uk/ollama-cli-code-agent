import os
from pathlib import Path

from ocla.util import can_access_path


def test_can_access_non_hidden():
    assert can_access_path(Path("foo/bar.txt"))


def test_can_access_hidden_directory_denied():
    assert not can_access_path(Path("foo/.hidden/bar.txt"))


def test_can_access_absolute_path_denied():
    assert not can_access_path(Path("/etc/passwd"))
