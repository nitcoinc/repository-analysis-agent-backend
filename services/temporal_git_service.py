"""Git history ingestion for temporal / drift analysis (GitPython)."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class CommitRecord:
    sha: str
    short_sha: str
    author_name: str
    author_email: str
    committed_at: datetime  # UTC
    subject: str
    body_preview: str
    files_changed: List[str]
    insertions: int
    deletions: int
    total_lines_changed: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sha": self.sha,
            "short_sha": self.short_sha,
            "author_name": self.author_name,
            "author_email": self.author_email,
            "committed_at": self.committed_at.isoformat(),
            "subject": self.subject,
            "body_preview": self.body_preview[:500],
            "files_changed": self.files_changed,
            "insertions": self.insertions,
            "deletions": self.deletions,
            "total_lines_changed": self.total_lines_changed,
        }


def _utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


# Note: Per-commit diffs are bounded by max_count; for very large repos consider lowering max_count.


def _commit_files_and_line_stats(repo: Any, commit: Any) -> tuple[List[str], int, int]:
    """
    File list and line change totals for one commit.

    Shallow clones often omit parent objects; ``git diff parent..commit`` then fails with
    "fatal: bad object". In that case we fall back to ``git ls-tree`` (file names only, 0/0 lines).
    """
    from git.exc import GitCommandError

    files: List[str] = []
    ins = dels = 0

    try:
        if commit.parents:
            diff_index = commit.parents[0].diff(commit, create_patch=False)
            for d in diff_index:
                p = d.b_path or d.a_path
                if p:
                    files.append(str(p).replace("\\", "/"))
            st = commit.stats.total
            ins = int(st.get("insertions", 0) or 0)
            dels = int(st.get("deletions", 0) or 0)
        else:
            if commit.tree:
                for blob in commit.tree.traverse():
                    if blob.type == "blob":
                        files.append(str(blob.path).replace("\\", "/"))
        return (sorted(set(files)), ins, dels)
    except GitCommandError as exc:
        err = str(exc).lower()
        if "bad object" in err or "unknown revision" in err:
            logger.info(
                "temporal_git: missing parent/object for %s (shallow clone?); using tree listing",
                commit.hexsha[:7],
            )
        else:
            logger.debug("commit diff stats (GitCommandError): %s", exc)
    except Exception as exc:
        logger.debug("commit diff stats: %s", exc)

    # Fallback: no parent in repo — list tree paths only; line stats unavailable
    try:
        raw = repo.git.ls_tree("-r", "--name-only", commit.hexsha)
        files = [ln.strip().replace("\\", "/") for ln in raw.splitlines() if ln.strip()]
    except Exception as exc2:
        logger.warning("temporal_git: ls-tree fallback failed for %s: %s", commit.hexsha[:7], exc2)
        files = []
    return (sorted(set(files)), 0, 0)


def _deepen_if_shallow(repo: Any, repo_path: str, *, min_commits: int = 0) -> None:
    """Auto-deepen a shallow clone so temporal analysis has enough history."""
    from core.config import get_settings
    shallow_file = Path(repo_path) / ".git" / "shallow"
    if not shallow_file.is_file():
        return
    s = get_settings()
    configured_step = int(getattr(s, "temporal_fetch_depth", 200) or 0)
    try:
        local_count = int((repo.git.rev_list("--count", "HEAD") or "0").strip())
    except Exception:
        local_count = 0
    # Skip network fetch once local history is already deep enough for this request.
    if min_commits > 0 and local_count >= min_commits:
        logger.info(
            "temporal_git: shallow clone has enough local commits (%d >= %d); skip deepen",
            local_count,
            min_commits,
        )
        return
    # Fetch enough in one call for this request window; keep configured step as a minimum.
    # Cap each deepen burst to avoid long blocking network calls from a single API request.
    needed = max(0, min_commits - local_count)
    depth = min(max(configured_step, needed), 300)
    try:
        if depth > 0:
            logger.info(
                "temporal_git: shallow clone detected — local=%d target>=%d; fetching +%d commits",
                local_count,
                min_commits,
                depth,
            )
            repo.git.fetch("--deepen", str(depth), kill_after_timeout=25)
        else:
            logger.info("temporal_git: shallow clone detected — unshallowing")
            repo.git.fetch("--unshallow", kill_after_timeout=25)
    except Exception as exc:
        logger.warning("temporal_git: deepen/unshallow failed (network?): %s", exc)


def list_commits(
    repo_path: str,
    *,
    branch: Optional[str] = None,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    max_count: int = 600,
    author_filter: Optional[str] = None,
) -> List[CommitRecord]:
    """Walk commit history newest-first. Caps work for large repos."""
    try:
        from git import Repo
        from git.exc import GitCommandError
    except ImportError as exc:
        raise RuntimeError("GitPython is required for temporal analysis") from exc

    root = Path(repo_path)
    if not root.is_dir():
        raise ValueError(f"Not a directory: {repo_path}")

    repo = Repo(str(root))
    _deepen_if_shallow(repo, repo_path, min_commits=max_count)

    rev = branch or "HEAD"
    try:
        repo.git.rev_parse("--verify", rev)
    except Exception:
        rev = "HEAD"

    kwargs: Dict[str, Any] = {"max_count": max_count}
    # GitPython passes kwargs to `git rev-list`; datetime objects are not reliably serialized — use ISO strings.
    if since:
        su = _utc(since)
        kwargs["since"] = su.isoformat()
    if until:
        uu = _utc(until)
        kwargs["until"] = uu.isoformat()

    try:
        commits_iter = repo.iter_commits(rev, **kwargs)
    except GitCommandError as exc:
        logger.warning("temporal_git: iter_commits failed rev=%s: %s", rev, exc)
        raise RuntimeError(f"Git history could not be read: {exc}") from exc
    out: List[CommitRecord] = []

    author_re = None
    if author_filter and author_filter.strip():
        author_re = re.compile(re.escape(author_filter.strip()), re.I)

    for commit in commits_iter:
        try:
            committed = _utc(datetime.fromtimestamp(commit.committed_date, tz=timezone.utc))
        except Exception:
            continue

        author = commit.author or commit.committer
        aname = (author.name if author else "") or ""
        aemail = (author.email if author else "") or ""
        if author_re and not (author_re.search(aname) or author_re.search(aemail)):
            continue

        subj, _, body = (commit.message or "").partition("\n")
        subj = (subj or "").strip()
        body = body.strip()

        files, ins, dels = _commit_files_and_line_stats(repo, commit)
        total_lc = ins + dels

        out.append(
            CommitRecord(
                sha=commit.hexsha,
                short_sha=commit.hexsha[:7],
                author_name=aname,
                author_email=aemail,
                committed_at=committed,
                subject=subj or "(no subject)",
                body_preview=body[:800],
                files_changed=sorted(set(files)),
                insertions=ins,
                deletions=dels,
                total_lines_changed=total_lc,
            )
        )

    logger.info("temporal_git: collected %d commits (rev=%s)", len(out), rev)
    return out
