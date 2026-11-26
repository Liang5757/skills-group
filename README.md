# Skills Group

A repository of reusable agent skills for Codex, Claude Code, Trae, and Trae CN.

## Skill Market

[Browse the Skill Market](https://liang5757.github.io/skills-group/) to see skill descriptions, versions, Markdown previews, and install commands.

## Install skills

To install one skill, run this from the target project with Node.js 22.20 or later, then select the agents.

```bash
npx -y skills add Liang5757/skills-group --skill video-downloader
```

Replace `video-downloader` with the skill name. The command installs from the repository's default branch. Add `--global` for a user-level install.

Use `--skill '*'` to select every skill. Use `--agent` to choose an agent directly, such as `codex`, `claude-code`, `trae`, or `trae-cn`.

```bash
npx -y skills add Liang5757/skills-group --skill '*' --agent codex
```

Manage installed skills with `npx skills list`, `npx skills check`, `npx skills update`, or `npx skills remove <skill-name>`.

## Develop the Skill Market

The catalog, file tree, and previews are generated from Git-tracked files under `.agents/skills/`. Each skill starts on its `SKILL.md`, with previews for Markdown, text, code, and common images. Source files and Markdown code blocks are highlighted at build time, and Markdown can also be viewed as highlighted source. File switches replace the current browser history entry. Large text files and other binary formats link to GitHub. Update `metadata.version` in the skill's YAML frontmatter when releasing a new version.

- `market/build/` reads skill metadata and prepares previews. `market/build.ts` bundles assets and renders each public URL to static HTML.
- `market/src/app/` owns the app shell and the static and browser entry points. Both use the same React components and generated CSS class names.
- `components/` groups the catalog, skill details, preferences controls, and shared components. Each component keeps its CSS Module alongside it. `styles/` contains shared layout and control styles.
- `hooks/` owns React state and browser effects for search, pagination, page metadata, and file loading. `lib/` contains the data functions and validators, and `types/` defines page, skill, and preview data shared by the generator and UI.
- `i18n/` owns the locale registry and message catalogs. Skill descriptions and files display the repository text.
- `theme/` owns theme colors, syntax highlighting tokens, and theme initialization. `preferences/` owns persisted language and appearance settings.
- In-place file navigation loads the target file's `preview.json`. Markdown source is loaded on demand from `source.json`. GitHub Actions runs ESLint, Prettier, TypeScript, and site tests for pull requests and before deploying.

Use Node.js 22.13+ or Node.js 24+ to build and check the market.

```bash
npm ci --prefix market
npm run lint --prefix market
npm run format:check --prefix market
npm run typecheck --prefix market
npm test --prefix market
npm run build --prefix market
python3 -m http.server 8000 --directory market/dist
```

Run `npm run format --prefix market` to apply Prettier formatting. Open `http://localhost:8000/` to preview the generated site. The GitHub Pages publishing source is **GitHub Actions**. The workflow rebuilds and deploys when changes to the skills or site land on `main`.
