# Repository instructions

## Skill layout

- Store every repository-owned skill under `.agents/skills/<skill-name>/`.
- Each skill must contain `SKILL.md`; its frontmatter `name` must match the directory name and use lowercase letters, digits, and hyphens.
- Do not create a top-level `skills/` directory. `.agents/skills/` is the canonical source used both by Codex repository discovery and by the cross-agent installers.
- Keep optional `agents/openai.yaml`, `scripts/`, `references/`, and `assets/` inside the owning skill directory.

## Creating or updating skills

- Use the available `skill-creator` skill for new or substantially revised skills.
- Add new skills directly to `.agents/skills/`; do not require a user-level Codex installation for use in this repository.
- Update the skill table in `README.md` when adding, removing, or renaming a skill.
- Validate every changed skill with the Codex `skill-creator` `quick_validate.py` script, then run the skill's focused tests when present.
- After changing the repository layout or installers, test the macOS installer with an isolated temporary home. Keep the PowerShell installer behavior aligned and call out when it could not be executed locally.

## Invocation

- In Codex, explicitly invoke repository skills as `$skill-name`, or use `/skills` and select the skill.
- Do not document arbitrary `/skill-name` as supported Codex syntax.
