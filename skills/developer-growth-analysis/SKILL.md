---
name: developer-growth-analysis
description: Analyze recent Codex or development-assistant work history to identify coding patterns, strengths, repeated friction, technical learning gaps, and focused growth actions. Use when asked to review recent developer activity, summarize work patterns, create a personal growth report, prepare weekly engineering reflection, recommend learning topics, inspect Codex chat history, or automate recurring developer-growth analysis from local history files or provided transcripts.
---

# Developer Growth Analysis

## Overview

Create evidence-based developer growth reports from recent work history. Keep the analysis private by default, grounded in observed work, and focused on practical next steps rather than generic advice.

## Privacy Rules

- Treat chat history, pasted code, project names, credentials, and customer data as private.
- Do not send reports to chat apps, email, docs, or external services unless the user explicitly asks and the destination is authorized.
- Redact obvious secrets before quoting evidence.
- Quote only short snippets needed to support an observation; prefer paraphrase.
- If the source history is unavailable or sparse, say what evidence is missing and ask for transcripts, summaries, or a date range.

## Workflow

1. Determine the period and source. Default to the last 7 days for weekly review, or 24-48 hours for "today/recent" requests.
2. Collect evidence from local Codex history, current conversation, user-provided transcripts, commits, PRs, tasks, or notes.
3. Summarize actual work: projects, technologies, task types, decisions, debugging areas, and delivery style.
4. Identify patterns: repeated questions, repeated fixes, architecture uncertainty, tooling friction, testing gaps, security concerns, async/concurrency issues, frontend layout issues, data modeling, release workflow, or communication habits.
5. Separate strengths from improvement areas. A strong report should include both.
6. Recommend 3-5 prioritized growth areas with evidence, why it matters, one concrete practice action, and an estimated learning investment.
7. Suggest learning queries or resources. Browse only when the user asks for current resources or when the topic benefits from up-to-date material.
8. Produce the report in the requested destination. Keep output local unless external delivery is explicitly requested.

## Automation Helper

Use the bundled script to collect and pre-analyze local Codex history:

```bash
python scripts/analyze_growth_history.py --days 7 --format markdown --output growth-report.md
python scripts/analyze_growth_history.py --history "$CODEX_HOME/history.jsonl" --since-hours 48 --format json
python scripts/analyze_growth_history.py --project my-repo --days 14
```

The script reads `$CODEX_HOME/history.jsonl` when set, otherwise `~/.codex/history.jsonl`. It produces a heuristic evidence report. Use agent judgment to improve the final narrative, but do not add claims that are not supported by the collected evidence or user-provided context.

For recurring automation, create a scheduled Codex job that:

- Runs in this repository.
- Uses this skill and the helper script.
- Analyzes the last 7 days by default.
- Writes a dated report under `outputs/developer-growth-analysis/`.
- Avoids external sending unless the user configured a delivery channel.

## Report Structure

```markdown
# Developer Growth Report

**Report Period**: <date range>
**Source**: <history/transcripts/commits/etc.>
**Generated**: <timestamp>

## Work Summary
<2-4 concise paragraphs grounded in observed work>

## Strengths Observed
- <strength and evidence>

## Growth Areas
### 1. <Area>
**Why This Matters**:
**Evidence**:
**Recommended Practice**:
**Time to Skill Up**:

## Action Plan
1. <highest-leverage next action>
2. <next action>
3. <next action>

## Learning Queries Or Resources
- <query/resource matched to an area>

## Evidence Notes
- <short, non-sensitive examples>
```

## Quality Bar

- Make observations specific: "testing coverage around async UI states" is better than "write better tests."
- Tie every recommendation to a project, task type, repeated friction, or explicit user goal.
- Prefer one-week practice actions over vague long-term learning plans.
- Include "continue doing" behaviors so the report is motivating and balanced.
- Avoid judging the developer personally. Analyze patterns in work, tooling, and process.
- If recommending resources without browsing, provide search queries and learning targets instead of invented links.
