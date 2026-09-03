---
name: changelog-generator
description: Generate user-facing changelogs, release notes, app store update text, GitHub release notes, weekly/monthly product summaries, and internal release summaries from git commit history, tags, PR summaries, issue lists, or raw change notes. Use when asked to create, update, polish, categorize, or publish a changelog; turn technical commits into customer-readable language; compare versions or date ranges; or filter release noise before documenting changes.
metadata:
  version: "0.1.0"
---

# Changelog Generator

## Overview

Create clear release communication from technical change history. Prefer grounded output: collect source evidence first, translate user-visible impact, and separate publishable notes from internal implementation detail.

## Workflow

1. Determine the target audience, time range or version range, and output format. If the user does not specify a range, default to commits since the latest reachable tag; if there is no tag, use a concise recent range and say what was used.
2. Inspect existing release style before writing. Check files such as `CHANGELOG.md`, `RELEASE.md`, `.github/release.yml`, package manifests, prior GitHub releases, or app store text when available.
3. Collect change evidence. Prefer the bundled script for git history, and combine it with user-provided PR summaries, issue links, or release notes when available.
4. Classify changes by user impact, not by commit prefix alone. Merge duplicate commits that describe the same feature or fix.
5. Write the changelog in the requested style. Keep it useful to readers who did not see the implementation.
6. Verify that every claim is supported by commits, files, PRs, issues, or explicit user input. Mark uncertain items as needing review instead of inventing impact.

## Git Context

Run the helper from this skill directory, or call it by absolute path from another repository.

```bash
python scripts/collect_changelog_context.py --repo /path/to/repo --last-tag --format markdown
python scripts/collect_changelog_context.py --repo /path/to/repo --from v1.4.0 --to HEAD --format json
python scripts/collect_changelog_context.py --repo /path/to/repo --since 2026-06-01 --until 2026-06-30
```

Use `--include-merges` only when merge commits or PR titles are the best source of product intent. Use `--output <file>` for large histories so the context can be reviewed without flooding the conversation.

## Classification

Use only categories that have real entries:

- Breaking changes
- Security
- New features
- Improvements
- Bug fixes
- Performance
- Documentation or developer experience
- Deprecations or removals

Filter or demote internal noise unless it matters to users: formatting-only commits, test-only changes, mechanical refactors, CI maintenance, dependency bumps with no visible effect, generated files, and revert churn. Keep developer-facing changes when the audience is developers.

## Writing Rules

- Start with the outcome, then mention the implementation only when it helps readers understand risk or behavior.
- Convert commit subjects such as `fix auth null pointer` into concrete impact such as "Fixed sign-in failures for accounts missing optional profile data."
- Avoid marketing fluff, unsupported metrics, and vague claims like "improved experience" unless evidence explains how.
- Avoid emoji unless the project already uses them or the user asks for them.
- Preserve the user's brand voice, tense, heading style, and release format when an existing changelog or style guide is present.
- Include upgrade notes, migrations, breaking changes, or known limitations before minor fixes.
- Keep internal notes separate from publishable notes when both are useful.

## Output Shapes

Default Markdown:

```markdown
# Release Notes - <version or date range>

## Highlights
- ...

## New Features
- ...

## Improvements
- ...

## Fixes
- ...

## Upgrade Notes
- ...
```

For GitHub releases, include a short summary, grouped changes, contributors or PR numbers when available, and any migration notes. For app store updates, write concise user-facing paragraphs with no commit jargon. For internal summaries, add risk, rollout, testing, and follow-up sections when evidence supports them.

## File Updates

Do not modify `CHANGELOG.md`, release drafts, package versions, or tags unless the user asks. When updating a file, preserve existing formatting, add only the new entry, and report the source range used.
