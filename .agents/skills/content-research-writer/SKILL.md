---
name: content-research-writer
description: Research, outline, draft, revise, cite, and polish long-form or short-form written content including blog posts, articles, newsletters, tutorials, thought leadership, case studies, technical documentation, social posts, scripts, and presentation narratives. Use when asked to develop a topic, find and evaluate sources, create or improve an outline, strengthen hooks and introductions, preserve an author's voice, give section-by-section feedback, manage citations, adapt content for an audience or channel, or prepare publish-ready copy.
metadata:
  version: "0.1.0"
---

# Content Research Writer

## Overview

Act as a research-grounded writing partner. Help the user move from idea to publishable content while keeping claims sourced, structure intentional, and voice recognizably theirs.

## Workflow

1. Clarify the writing job: topic, audience, goal, format, length, tone, deadline, target publication, source requirements, and whether the user wants inline output or files.
2. Inspect available material: user notes, drafts, prior writing samples, brand/style guides, research docs, source links, transcripts, or code/docs when relevant.
3. Create or refine the outline. Mark thesis, reader promise, sections, evidence needed, examples, and open questions.
4. Research only as needed. Use user-provided sources first; browse or query authoritative sources when facts may be current, specialized, or disputed. Record source URLs and publication dates when available.
5. Draft in stages. Prefer outline -> introduction/hook -> body sections -> conclusion -> title/meta/social variants unless the user asks for a complete draft immediately.
6. Review each draft for argument, evidence, clarity, flow, voice, and reader value. Offer options rather than replacing the user's style by default.
7. Finalize with citation cleanup, factual checks, consistency pass, and a publication checklist.

## Research Rules

- Do not invent statistics, quotes, examples, dates, studies, or company claims.
- Prefer primary sources: official docs, original research, public filings, standards, product pages, interviews, datasets, or directly linked materials.
- Use recent sources for fast-moving topics such as AI, software products, laws, prices, benchmarks, market data, and public-company facts.
- Distinguish evidence from interpretation. Say when something is an inference.
- When sources conflict, name the disagreement and avoid smoothing it into false certainty.
- Keep a running research log when the task is source-heavy: claim, source, date, reliability, and where it belongs in the draft.

## Outline Pattern

Use this shape when the user wants structure:

```markdown
# Working Title

## Reader
- Audience:
- Need or pain:
- Desired takeaway:

## Thesis
- Main argument:
- Why now:

## Hook Options
- Story:
- Data:
- Contrarian claim:

## Sections
1. <Section title>
   - Key point:
   - Evidence:
   - Example:
   - Research needed:

## Conclusion
- Recap:
- Next step or call to action:

## Research To-Do
- [ ] Claim/source needed:
```

## Drafting Guidance

- Start from a clear reader promise. The introduction should tell readers why the piece matters and what they will gain.
- Keep paragraphs purposeful: one idea, one job, one transition.
- Support strong claims with evidence, concrete examples, or clearly labeled opinion.
- Explain jargon the first time it appears unless the audience is expert.
- Preserve the user's voice. If writing samples exist, infer sentence length, rhythm, directness, humor, vocabulary, and stance from those samples.
- Offer alternatives for high-leverage passages: hooks, section openers, transitions, titles, and calls to action.
- For technical content, verify code, commands, APIs, and version-specific statements before presenting them as instructions.

## Feedback Format

For section reviews, use a focused structure:

```markdown
# Feedback: <section>

## What Works
- ...

## Improve Next
- Clarity:
- Flow:
- Evidence:
- Voice:

## Suggested Edits
Original:
> ...

Suggested:
> ...

Why:
- ...

## Open Questions
- ...
```

Keep feedback actionable and proportionate. For early drafts, prioritize structure and argument. For near-final drafts, prioritize line edits, precision, citation completeness, and polish.

## Citation Formats

Match the user's requested format. If unspecified, use simple Markdown links for web content and a `References` section for research-heavy work.

Common options:

- Inline links: `According to [Source Name](https://example.com), ...`
- Numbered references: `The report found ... [1]`
- Footnotes: `The report found ...[^1]`
- Academic style: APA, MLA, Chicago, or another requested style

For every citation, retain enough information to audit it later: title, publisher or author, date when available, URL, and access date when useful.

## Output Modes

- **Outline**: working title, thesis, sections, evidence gaps, research to-do.
- **Research brief**: key findings, source table, useful quotes or paraphrases, contradictions, recommended angle.
- **Draft**: publishable prose with citations and notes where evidence is missing.
- **Rewrite**: improved version plus a short explanation of changes.
- **Editorial review**: strengths, issues, suggested edits, open questions.
- **Adaptation**: transform a source piece into newsletter, social thread, executive summary, tutorial, script, or slides narrative while preserving the core argument.

## File Workflow

If the user wants files, use a small project folder and clear names:

```text
outline.md
research.md
draft-v1.md
draft-v2.md
final.md
sources/
```

Do not create or overwrite files unless the user asks. When editing an existing draft, preserve the user's content and make scoped changes.

## Final Checklist

- Main promise is clear in the first few paragraphs.
- Audience, tone, and depth match the user's goal.
- Each major claim has evidence or is framed as opinion.
- Citations are complete and consistently formatted.
- Examples are concrete.
- Transitions make the structure easy to follow.
- Title, intro, and conclusion work together.
- No unsupported current facts, fabricated quotes, or stale claims remain.
