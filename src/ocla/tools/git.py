from pathlib import Path

from git import Repo, GitCommandError

from . import Tool, ToolSecurity
from ..util import can_access_path


class GitShowChanges(Tool):
    """Show git status and diff for the repository."""

    security = ToolSecurity.PERMISSIBLE
    description = "Show git status and diff for the repository"

    def execute(self) -> (str, str):
        repo = Path(".")
        if not can_access_path(repo):
            return "", f"OCLA cannot access: {repo}"
        try:
            repo_obj = Repo(repo)
            status = repo_obj.git.status("--porcelain")
            diff = repo_obj.git.diff()
            output = status + diff
            if not output.strip():
                output = "no changes"
            return output.strip(), ""
        except GitCommandError as e:
            return "", e.stderr.strip()
        except Exception as e:
            return "", str(e)


class GitCommit(Tool):
    """Commit staged changes with the given message."""

    security = ToolSecurity.ASK
    description = "Commit staged changes with the given message"

    def execute(self, message: str) -> (str, str):
        repo = Path(".")
        if not can_access_path(repo, for_write=True):
            return "", f"OCLA cannot access: {repo}"
        try:
            repo_obj = Repo(repo)
            out = repo_obj.git.commit("-am", message)
            return out.strip(), ""
        except GitCommandError as e:
            return "", e.stderr.strip()
        except Exception as e:
            return "", str(e)


class GitLog(Tool):
    """Show git log."""

    security = ToolSecurity.PERMISSIBLE
    description = "Show the last n commits in the repository"

    def execute(self, n: int = 5) -> (str, str):
        repo = Path(".")
        if not can_access_path(repo):
            return "", f"OCLA cannot access: {repo}"
        try:
            repo_obj = Repo(repo)
            out = repo_obj.git.log("--oneline", f"-n{n}")
            return out.strip(), ""
        except GitCommandError as e:
            return "", e.stderr.strip()
        except Exception as e:
            return "", str(e)
