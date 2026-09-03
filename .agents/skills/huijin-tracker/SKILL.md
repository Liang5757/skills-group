---
name: huijin-tracker
description: Track and compare Central Huijin public disclosures and holdings snapshots with evidence-preserving collectors. Use when monitoring Central Huijin, Huijin Asset Management, named Huijin plans, or China Securities Finance, or when distinguishing disclosed operations from quarterly shareholder-list changes.
---

# Huijin Tracker

Use the bundled tracker to collect, archive, reconcile, and report public information about Central Huijin. Run commands from this skill directory with `PYTHONPATH=src python -m huijin_tracker ...`.

Read [references/operation.md](references/operation.md) before installing, running a full-market scan, configuring continuous monitoring, or interpreting event output.

## Evidence rules

- Treat an operation as confirmed only when an official source explicitly describes it.
- Treat changes between reporting-period snapshots as period-end differences, not as known trade dates.
- Never describe disappearance from a top-ten shareholder list as a sale or liquidation without separate evidence.
- Keep Central Huijin, Huijin Asset Management, named asset-management plans, and China Securities Finance as distinct holders. Label China Securities Finance as a related controlled entity, not a direct Central Huijin trade.
- State the reporting period, disclosure date, source type, and coverage limitations in user-facing results. Public data cannot prove real-time or complete positions below disclosure thresholds.

## Typical workflow

1. Initialize or inspect the SQLite state with `init` and `status`.
2. Collect Central Huijin and exchange disclosures, preserving the raw archive.
3. Establish an older complete reporting-period baseline before syncing a newer period.
4. Review generated events and source evidence before notifying the user.
5. Use `watch` only for lightweight disclosure polling; run full-market holdings scans around reporting periods.

Do not configure or send webhook notifications unless the user explicitly requests that external side effect. Never place webhook URLs or signing secrets in source files, examples, or logs.

After changing the tracker, run:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```
