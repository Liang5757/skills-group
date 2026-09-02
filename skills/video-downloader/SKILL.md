---
name: video-downloader
description: Download public or user-authorized videos and audio from yt-dlp supported websites with configurable quality, container, playlist handling, cookies, subtitles, metadata, proxies, and troubleshooting helpers. Use when the user asks to download, save, archive, inspect, list formats for, or extract audio from video URLs across YouTube, Vimeo, X/Twitter, TikTok, Twitch, Bilibili, news sites, direct HLS/DASH links, or other yt-dlp compatible sources.
metadata:
  version: "0.1.0"
---

# Video Downloader

## Overview

Use this skill to download videos or audio through `yt-dlp` while keeping the agent workflow consistent, lawful, and repeatable. The bundled script wraps common `yt-dlp` operations and leaves an escape hatch for advanced site-specific arguments.

Do not help bypass DRM, paywalls, or access controls. Only download content the user owns, has permission to save, or can lawfully archive from a public or user-authorized URL.

## Workflow

1. Confirm the URL and desired output: video, audio-only, quality, playlist behavior, subtitles, and output directory.
2. Use the default single-item mode unless the user explicitly asks for a playlist or channel batch.
3. Inspect first when support is uncertain:

```bash
python scripts/download_video.py "URL" --info
python scripts/download_video.py "URL" --list-formats
```

4. Download with the narrowest options that match the request.
5. If a site fails, update `yt-dlp`, retry with legitimate cookies or headers when the user is authorized, then report unsupported or restricted sources clearly.

## Quick Start

Use Python 3.10+ when possible. Modern site extractors, especially YouTube, may require a recent `yt-dlp` release that older Python versions cannot install.

Download best available video as MP4:

```bash
python scripts/download_video.py "URL"
```

Download up to 720p:

```bash
python scripts/download_video.py "URL" --quality 720p
```

Extract MP3 audio:

```bash
python scripts/download_video.py "URL" --audio-only --audio-format mp3
```

Download an explicit playlist:

```bash
python scripts/download_video.py "PLAYLIST_OR_CHANNEL_URL" --playlist --download-archive archive.txt
```

Use authorized cookies:

```bash
python scripts/download_video.py "URL" --cookies cookies.txt
python scripts/download_video.py "URL" --cookies-from-browser chrome
```

Write subtitles and metadata:

```bash
python scripts/download_video.py "URL" --write-subs --write-auto-subs --sub-langs "en.*,zh.*" --embed-metadata
```

Preview the command without running it:

```bash
python scripts/download_video.py "URL" --quality 1080p --print-command
```

## Output

By default, downloads go to `./outputs/<extractor>/<title> [id].<ext>` relative to the current working directory. Use `--output` to choose a different directory, and `--output-template` when the user needs a custom archive naming scheme.

## Troubleshooting

Use `--update` when an extractor appears stale. Use `--proxy`, `--referer`, or `--user-agent` only when they reflect the user's legitimate access path. Use `--yt-format` for custom yt-dlp format selectors and `--yt-dlp-arg=...` for advanced options not exposed by this wrapper.

For YouTube warnings about JavaScript runtimes, pass `--js-runtimes` with an available runtime. For site-specific extractor flags such as YouTube player clients or PO tokens, prefer `--extractor-args` before falling back to `--yt-dlp-arg`.

If a URL is unsupported, ask for another source or explain that the site may have changed, require authentication, block automated retrieval, or use DRM.
