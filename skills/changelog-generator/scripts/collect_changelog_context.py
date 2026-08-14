#!/usr/bin/env python3
"""Collect git history context for changelog generation."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Tuple


FIELD_SEP = "\x1f"
RECORD_SEP = "\x1e"


@dataclass
class Commit:
    sha: str
    short_sha: str
    date: str
    author: str
    subject: str


def run_git(repo: Path, args: Iterable[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def git_output(repo: Path, args: Iterable[str], *, check: bool = True) -> str:
    return run_git(repo, args, check=check).stdout.strip()


def git_root(repo: Path) -> Path:
    try:
        root = git_output(repo, ["rev-parse", "--show-toplevel"])
    except subprocess.CalledProcessError as exc:
        message = exc.stderr.strip() or "not a git repository"
        raise SystemExit(f"error: {message}") from exc
    return Path(root)


def latest_tag(repo: Path, rev: str) -> Optional[str]:
    result = run_git(repo, ["describe", "--tags", "--abbrev=0", rev], check=False)
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def parse_commits(raw: str) -> List[Commit]:
    commits: List[Commit] = []
    for record in raw.split(RECORD_SEP):
        record = record.strip()
        if not record:
            continue
        parts = record.split(FIELD_SEP)
        if len(parts) != 5:
            continue
        commits.append(Commit(*parts))
    return commits


def build_log_args(args: argparse.Namespace, base_ref: Optional[str]) -> Tuple[List[str], str]:
    log_args = ["log", "--date=short", f"--pretty=format:%H{FIELD_SEP}%h{FIELD_SEP}%ad{FIELD_SEP}%an{FIELD_SEP}%s{RECORD_SEP}"]
    if not args.include_merges:
        log_args.append("--no-merges")
    if args.since:
        log_args.extend(["--since", args.since])
    if args.until:
        log_args.extend(["--until", args.until])
    if args.max_count:
        log_args.extend(["--max-count", str(args.max_count)])

    if base_ref:
        revision = f"{base_ref}..{args.to}"
        log_args.append(revision)
        label = revision
    else:
        log_args.append(args.to)
        label = args.to

    return log_args, label


def collect_context(args: argparse.Namespace) -> dict:
    repo = git_root(Path(args.repo).expanduser().resolve())
    base_ref = args.from_ref
    if args.last_tag and not base_ref:
        base_ref = latest_tag(repo, args.to)

    log_args, range_label = build_log_args(args, base_ref)
    commits = parse_commits(git_output(repo, log_args))

    diffstat = ""
    if base_ref:
        diffstat = git_output(repo, ["diff", "--stat", "--find-renames", f"{base_ref}..{args.to}"], check=False)

    tags = git_output(repo, ["tag", "--points-at", args.to], check=False).splitlines()

    return {
        "repository": str(repo),
        "range": {
            "from": base_ref,
            "to": args.to,
            "label": range_label,
            "since": args.since,
            "until": args.until,
            "include_merges": args.include_merges,
        },
        "tags_at_to": tags,
        "commit_count": len(commits),
        "commits": [asdict(commit) for commit in commits],
        "diffstat": diffstat,
    }


def render_markdown(context: dict) -> str:
    range_info = context["range"]
    lines = [
        "# Changelog Source Context",
        "",
        f"- Repository: `{context['repository']}`",
        f"- Range: `{range_info['label']}`",
        f"- Commits: {context['commit_count']}",
    ]
    if range_info.get("since") or range_info.get("until"):
        lines.append(f"- Date filter: `{range_info.get('since') or 'start'}` to `{range_info.get('until') or 'end'}`")
    if context["tags_at_to"]:
        lines.append("- Tags at target: " + ", ".join(f"`{tag}`" for tag in context["tags_at_to"]))

    lines.extend(["", "## Commits", ""])
    if context["commits"]:
        for commit in context["commits"]:
            lines.append(
                f"- `{commit['short_sha']}` {commit['date']} {commit['subject']} ({commit['author']})"
            )
    else:
        lines.append("- No commits matched the requested range.")

    if context["diffstat"]:
        lines.extend(["", "## Diffstat", "", "```", context["diffstat"], "```"])

    return "\n".join(lines).rstrip() + "\n"


def write_output(text: str, output: Optional[str]) -> None:
    if output:
        Path(output).expanduser().write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="Git repository to inspect")
    parser.add_argument("--from", dest="from_ref", help="Start ref, tag, or commit (exclusive)")
    parser.add_argument("--to", default="HEAD", help="End ref, tag, or commit (inclusive)")
    parser.add_argument("--last-tag", action="store_true", help="Use the latest reachable tag as --from when --from is omitted")
    parser.add_argument("--since", help="Pass through to git log --since")
    parser.add_argument("--until", help="Pass through to git log --until")
    parser.add_argument("--max-count", type=int, help="Limit number of commits")
    parser.add_argument("--include-merges", action="store_true", help="Include merge commits")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown", help="Output format")
    parser.add_argument("--output", help="Write output to a file instead of stdout")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    context = collect_context(args)
    if args.format == "json":
        rendered = json.dumps(context, indent=2, ensure_ascii=False) + "\n"
    else:
        rendered = render_markdown(context)
    write_output(rendered, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
