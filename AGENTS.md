# Skills Group repository instructions

## Repository skills

- Store each skill at `.agents/skills/<skill-name>/SKILL.md`. The directory name and frontmatter `name` must match and use only lowercase letters, digits, and hyphens.
- Keep supporting files such as `agents/openai.yaml`, `scripts/`, `references/`, and `assets/` inside the owning skill directory.
- Codex discovers skills directly from this checkout. Invoke them with `$skill-name` or select them from `/skills`.
- Use `skill-creator` for new or substantially revised skills. Run its `quick_validate.py` against each changed skill directory, then run the skill's focused tests when present.
- Use the generated Skill Market as the catalog and keep its link in `README.md`. The catalog reads Git-tracked files under `.agents/skills/`.
- Use `npx skills add` in the installation examples in `README.md` and Skill Market.

## Skill Market

- Keep static rendering and browser hydration on the shared React components. Keep component styles in their CSS Modules and prefer class selectors for component styling.
- Run the same checks as GitHub Pages for changes under `market/`. Install dependencies with `npm ci --prefix market` when needed.

```bash
npm run lint --prefix market
npm run format:check --prefix market
npm run typecheck --prefix market
npm test --prefix market
npm run build --prefix market
```
