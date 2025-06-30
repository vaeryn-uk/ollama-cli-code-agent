import subprocess
from pathlib import Path

from . import Tool, ToolSecurity
from ..util import can_access_path


class GitShowChanges(Tool):
    """Show git status and diff for the repository."""

    security = ToolSecurity.PERMISSIBLE

    def execute(self, path: str = ".") -> (str, str):
        repo = Path(path)
        if not can_access_path(repo):
            return "", f"OCLA cannot access: {path}"
        cmd_status = ["git", "-C", str(repo), "status", "--porcelain"]
        cmd_diff = ["git", "-C", str(repo), "diff"]
        try:
            status = subprocess.run(
                cmd_status, capture_output=True, text=True, check=False
            )
            diff = subprocess.run(cmd_diff, capture_output=True, text=True, check=False)
            output = status.stdout + diff.stdout
            if not output:
                output = "no changes"
            return output.strip(), ""
        except Exception as e:
            return "", str(e)


class GitCommit(Tool):
    """Commit staged changes with the given message."""

    security = ToolSecurity.ASK

    def execute(self, message: str, path: str = ".") -> (str, str):
        repo = Path(path)
        if not can_access_path(repo, for_write=True):
            return "", f"OCLA cannot access: {path}"
        cmd = ["git", "-C", str(repo), "commit", "-am", message]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if res.returncode != 0:
                return "", res.stderr.strip()
            return res.stdout.strip(), ""
        except Exception as e:
            return "", str(e)


class GitLog(Tool):
    """Show git log."""

    security = ToolSecurity.PERMISSIBLE

    def execute(self, n: int = 5, path: str = ".") -> (str, str):
        repo = Path(path)
        if not can_access_path(repo):
            return "", f"OCLA cannot access: {path}"
        cmd = ["git", "-C", str(repo), "log", "--oneline", f"-n{n}"]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if res.returncode != 0:
                return "", res.stderr.strip()
            return res.stdout.strip(), ""
        except Exception as e:
            return "", str(e)
