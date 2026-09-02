# Skills Group

A collection of reusable skills for Codex, Claude Code, Trae, and Trae CN.

## One-command install

The installer detects supported agents, downloads the latest validated version of this repository, and links every skill into each detected agent.

### macOS

```bash
curl -fsSL https://raw.githubusercontent.com/Liang5757/skills-group/main/install.sh | bash
```

### Windows PowerShell

```powershell
irm https://raw.githubusercontent.com/Liang5757/skills-group/main/install.ps1 | iex
```

Running remote code directly is convenient but requires trusting the current repository contents. To review the installer first, download it and run the local file:

```bash
curl -fsSLO https://raw.githubusercontent.com/Liang5757/skills-group/main/install.sh
less install.sh
bash install.sh
```

```powershell
irm https://raw.githubusercontent.com/Liang5757/skills-group/main/install.ps1 -OutFile install.ps1
Get-Content .\install.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\install.ps1
```

The installer uses these user-level directories:

| Agent | Skill directory |
| --- | --- |
| Codex | `~/.agents/skills/` |
| Claude Code | `~/.claude/skills/` |
| Trae | `~/.trae/skills/` |
| Trae CN | `~/.trae-cn/skills/` |

On macOS, skills are symbolic links. On Windows, they are directory junctions. Source files live in `~/.skills-group/repository/`, so one cache update refreshes every installed agent.

## Install and update options

With no arguments, the installer detects agents, checks the remote `main` commit, updates the cache when necessary, and installs all skills. It does not create a background task.

Common macOS commands:

```bash
bash install.sh --agent codex --agent claude
bash install.sh --skill changelog-generator
bash install.sh --check        # exit 0: current, 10: update available, 1: error
bash install.sh --update
bash install.sh --status
bash install.sh --uninstall
bash install.sh --force
```

Equivalent Windows PowerShell commands:

```powershell
.\install.ps1 -Agent codex,claude
.\install.ps1 -Skill changelog-generator
.\install.ps1 -Check          # exit 0: current, 10: update available, 1: error
.\install.ps1 -Update
.\install.ps1 -Status
.\install.ps1 -Uninstall
.\install.ps1 -Force
```

If a destination already contains a file, directory, or link not managed by Skills Group, the installer moves it to `~/.skills-group/backups/<timestamp>/` before creating the managed link. Uninstall removes only managed links and preserves the cache, backups, and unrelated user content.

Restart the agent if a newly installed or updated skill does not appear immediately.

## Skills

| Skill | Description |
| --- | --- |
| [Changelog Generator](skills/changelog-generator) | Generate user-facing changelogs and release notes from git history, tags, PR summaries, issues, or raw change notes. |
| [Content Research Writer](skills/content-research-writer) | Research, outline, draft, cite, adapt, and polish long-form or short-form content in a source-grounded workflow. |
| [Developer Growth Analysis](skills/developer-growth-analysis) | Analyze recent Codex or development-assistant work history to identify strengths, growth areas, and focused next actions. |
| [GPT Image 2](skills/gpt-image-2) | Generate or edit images with GPT Image 2 using local, host-native, or prompt-advisor workflows and structured templates. |
| [Install Codex Chrome Extension](skills/install-codex-chrome-extension) | Install, unpack, validate, and troubleshoot the Codex Chrome Extension with the required official extension ID. |
| [Mine Patent Points](skills/mine-patent-points) | Mine, assess, and prioritize patentable technical ideas from source code, architecture, requirements, retrospectives, and engineering discussions. |
| [Video Downloader](skills/video-downloader) | Download videos and audio from yt-dlp supported websites with configurable quality, cookies, subtitles, and metadata. |

## Manual install

You can still install an individual skill without the installer. Copy one directory from `skills/` into the relevant agent directory listed above, then restart or reload the agent.
