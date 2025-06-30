import subprocess
from pathlib import Path

from ocla.tools.git import GitShowChanges, GitCommit, GitLog


def init_repo(path: Path):
    subprocess.run(["git", "init", str(path)], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(path), "config", "user.email", "test@example.com"], check=True
    )
    subprocess.run(["git", "-C", str(path), "config", "user.name", "Test"], check=True)


def test_git_show_changes():
    repo = Path.cwd() / "tmp_repo_changes"
    if repo.exists():
        subprocess.run(["rm", "-rf", str(repo)])
    repo.mkdir()
    init_repo(repo)
    (repo / "a.txt").write_text("hello")
    subprocess.run(["git", "-C", str(repo), "add", "a.txt"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", "init"], check=True)
    (repo / "a.txt").write_text("world")
    output, err = GitShowChanges().execute(path=str(repo))
    assert err == ""
    assert "world" in output


def test_git_commit_and_log():
    repo = Path.cwd() / "tmp_repo_commit"
    if repo.exists():
        subprocess.run(["rm", "-rf", str(repo)])
    repo.mkdir()
    init_repo(repo)
    (repo / "b.txt").write_text("one")
    subprocess.run(["git", "-C", str(repo), "add", "b.txt"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", "start"], check=True)
    (repo / "b.txt").write_text("two")
    subprocess.run(["git", "-C", str(repo), "add", "b.txt"], check=True)
    commit_out, err = GitCommit().execute(message="update", path=str(repo))
    assert err == ""
    log_out, err = GitLog().execute(n=1, path=str(repo))
    assert err == ""
    assert "update" in log_out
