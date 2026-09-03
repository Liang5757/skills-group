#!/usr/bin/env python3
"""General-purpose video/audio downloader wrapper around yt-dlp."""

from __future__ import annotations

import argparse
import importlib.util
import json
import shlex
import shutil
import subprocess
import sys
from pathlib import Path


DEFAULT_TEMPLATE = "%(extractor_key)s/%(title)s [%(id)s].%(ext)s"


def module_available(name: str) -> bool:
    importlib.invalidate_caches()
    return importlib.util.find_spec(name) is not None


def pip_install_command(upgrade: bool = False) -> list[str]:
    cmd = [sys.executable, "-m", "pip", "install"]
    if upgrade:
        cmd.append("--upgrade")
    if sys.prefix == getattr(sys, "base_prefix", sys.prefix):
        cmd.append("--user")
    cmd.append("yt-dlp")
    return cmd


def find_ytdlp(auto_install: bool) -> list[str]:
    cli = shutil.which("yt-dlp")
    if cli:
        return [cli]
    if module_available("yt_dlp"):
        return [sys.executable, "-m", "yt_dlp"]
    if not auto_install:
        raise SystemExit(
            "yt-dlp is not installed. Install it or rerun without --no-auto-install."
        )

    if sys.version_info < (3, 10):
        print(
            "Warning: Python < 3.10 may not be able to install the latest yt-dlp. "
            "Use Python 3.10+ for best site compatibility.",
            file=sys.stderr,
        )
    print("yt-dlp not found. Installing with pip...", file=sys.stderr)
    subprocess.run(pip_install_command(), check=True)
    cli = shutil.which("yt-dlp")
    if cli:
        return [cli]
    if module_available("yt_dlp"):
        return [sys.executable, "-m", "yt_dlp"]
    raise SystemExit("yt-dlp installation completed, but the executable was not found.")


def ytdlp_command_for_print() -> list[str]:
    cli = shutil.which("yt-dlp")
    if cli:
        return [cli]
    if module_available("yt_dlp"):
        return [sys.executable, "-m", "yt_dlp"]
    return ["yt-dlp"]


def maybe_update_ytdlp(ytdlp: list[str]) -> None:
    result = subprocess.run(ytdlp + ["-U"], check=False, capture_output=True, text=True)
    output = f"{result.stdout}{result.stderr}"
    if result.returncode == 0:
        print(output, end="")
        return

    if "installed yt-dlp with pip" in output or "using the wheel from PyPi" in output:
        print("yt-dlp is pip-installed; upgrading with pip...", file=sys.stderr)
        pip_result = subprocess.run(pip_install_command(upgrade=True), check=False)
        if pip_result.returncode == 0:
            return

    print(output, end="", file=sys.stderr)
    print("Warning: yt-dlp update failed; continuing with installed version.", file=sys.stderr)


def add_common_options(cmd: list[str], args: argparse.Namespace) -> None:
    if args.playlist:
        cmd.append("--yes-playlist")
    else:
        cmd.append("--no-playlist")

    if args.cookies:
        cmd.extend(["--cookies", str(Path(args.cookies).expanduser())])
    if args.cookies_from_browser:
        cmd.extend(["--cookies-from-browser", args.cookies_from_browser])
    if args.proxy:
        cmd.extend(["--proxy", args.proxy])
    if args.referer:
        cmd.extend(["--referer", args.referer])
    if args.user_agent:
        cmd.extend(["--user-agent", args.user_agent])
    if args.ffmpeg_location:
        cmd.extend(["--ffmpeg-location", args.ffmpeg_location])
    if args.js_runtimes:
        cmd.extend(["--js-runtimes", args.js_runtimes])
    if args.extractor_args:
        cmd.extend(["--extractor-args", args.extractor_args])
    if args.verbose:
        cmd.append("--verbose")


def quality_selector(quality: str) -> str:
    if quality == "best":
        return "bv*+ba/b"
    if quality == "worst":
        return "wv*+wa/w"
    if quality.endswith("p") and quality[:-1].isdigit():
        height = quality[:-1]
        return f"bv*[height<={height}]+ba/b[height<={height}]/b"
    return quality


def add_extra_args(cmd: list[str], args: argparse.Namespace) -> None:
    for item in args.yt_dlp_arg or []:
        cmd.extend(shlex.split(item))


def build_download_command(ytdlp: list[str], args: argparse.Namespace) -> list[str]:
    cmd = ytdlp + ["--newline"]
    add_common_options(cmd, args)

    cmd.extend(["--paths", str(Path(args.output).expanduser())])
    cmd.extend(["-o", args.output_template])

    if args.audio_only:
        cmd.extend(["-f", args.yt_format or "bestaudio/best"])
        cmd.extend(["-x", "--audio-format", args.audio_format])
        if args.audio_quality is not None:
            cmd.extend(["--audio-quality", str(args.audio_quality)])
    else:
        cmd.extend(["-f", args.yt_format or quality_selector(args.quality)])
        if args.container != "native":
            cmd.extend(["--merge-output-format", args.container])

    if args.write_info_json:
        cmd.append("--write-info-json")
    if args.write_thumbnail:
        cmd.append("--write-thumbnail")
    if args.embed_thumbnail:
        cmd.append("--embed-thumbnail")
    if args.embed_metadata:
        cmd.append("--embed-metadata")

    if args.write_subs:
        cmd.append("--write-subs")
    if args.write_auto_subs:
        cmd.append("--write-auto-subs")
    if args.sub_langs:
        cmd.extend(["--sub-langs", args.sub_langs])
    if args.embed_subs:
        cmd.append("--embed-subs")

    if args.download_archive:
        cmd.extend(["--download-archive", str(Path(args.download_archive).expanduser())])
    if args.ignore_errors:
        cmd.append("--ignore-errors")
    if args.restrict_filenames:
        cmd.append("--restrict-filenames")
    if args.no_overwrites:
        cmd.append("--no-overwrites")
    if args.rate_limit:
        cmd.extend(["--limit-rate", args.rate_limit])
    if args.concurrent_fragments:
        cmd.extend(["--concurrent-fragments", str(args.concurrent_fragments)])
    if args.retries is not None:
        cmd.extend(["--retries", str(args.retries)])
    if args.fragment_retries is not None:
        cmd.extend(["--fragment-retries", str(args.fragment_retries)])
    if args.sleep_requests is not None:
        cmd.extend(["--sleep-requests", str(args.sleep_requests)])
    if args.sleep_interval is not None:
        cmd.extend(["--sleep-interval", str(args.sleep_interval)])
    if args.max_sleep_interval is not None:
        cmd.extend(["--max-sleep-interval", str(args.max_sleep_interval)])
    if args.live_from_start:
        cmd.append("--live-from-start")
    for section in args.download_section or []:
        cmd.extend(["--download-sections", section])

    add_extra_args(cmd, args)
    cmd.append(args.url)
    return cmd


def build_probe_command(ytdlp: list[str], args: argparse.Namespace) -> list[str]:
    cmd = ytdlp.copy()
    add_common_options(cmd, args)
    if args.list_formats:
        cmd.append("--list-formats")
    else:
        cmd.append("--dump-single-json")
    add_extra_args(cmd, args)
    cmd.append(args.url)
    return cmd


def print_summary(raw_json: str) -> None:
    info = json.loads(raw_json)
    kind = info.get("_type") or "video"
    print(f"Type: {kind}")
    for key, label in [
        ("title", "Title"),
        ("extractor_key", "Extractor"),
        ("uploader", "Uploader"),
        ("duration_string", "Duration"),
        ("webpage_url", "URL"),
        ("availability", "Availability"),
    ]:
        value = info.get(key)
        if value:
            print(f"{label}: {value}")
    if "entries" in info and isinstance(info["entries"], list):
        print(f"Entries: {len(info['entries'])}")


def ffmpeg_command(ffmpeg_location: str | None) -> list[str] | None:
    if ffmpeg_location:
        path = Path(ffmpeg_location).expanduser()
        if path.is_dir():
            for name in ("ffmpeg", "ffmpeg.exe"):
                candidate = path / name
                if candidate.exists():
                    return [str(candidate)]
            path = path / ("ffmpeg.exe" if sys.platform.startswith("win") else "ffmpeg")
        return [str(path)]
    ffmpeg = shutil.which("ffmpeg")
    return [ffmpeg] if ffmpeg else None


def warn_about_ffmpeg(args: argparse.Namespace) -> None:
    needs_ffmpeg = (
        args.audio_only
        or args.container != "native"
        or args.embed_subs
        or args.embed_thumbnail
        or args.embed_metadata
    )
    if not needs_ffmpeg:
        return

    cmd = ffmpeg_command(args.ffmpeg_location)
    if not cmd:
        print("Warning: ffmpeg was not found. Merging, remuxing, audio extraction, and embedding may fail.", file=sys.stderr)
        return

    try:
        result = subprocess.run(cmd + ["-version"], check=False, capture_output=True, text=True)
    except OSError as exc:
        print(
            "Warning: ffmpeg was not found or could not run. Merging, remuxing, "
            "audio extraction, and embedding may fail.",
            file=sys.stderr,
        )
        print(str(exc), file=sys.stderr)
        return

    if result.returncode != 0:
        print(
            "Warning: ffmpeg was found but could not run. Merging, remuxing, "
            "audio extraction, and embedding may fail.",
            file=sys.stderr,
        )
        if result.stderr:
            print(result.stderr.strip(), file=sys.stderr)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download videos or audio from yt-dlp supported websites."
    )
    parser.add_argument("url", help="Video, playlist, channel, or direct media URL")
    parser.add_argument(
        "-o",
        "--output",
        default="./outputs",
        help="Output directory (default: ./outputs)",
    )
    parser.add_argument(
        "--output-template",
        default=DEFAULT_TEMPLATE,
        help=f"yt-dlp output template (default: {DEFAULT_TEMPLATE.replace('%', '%%')})",
    )
    parser.add_argument(
        "-q",
        "--quality",
        default="best",
        choices=["best", "2160p", "1440p", "1080p", "720p", "480p", "360p", "worst"],
        help="Maximum video quality (default: best)",
    )
    parser.add_argument(
        "-c",
        "--container",
        default="mp4",
        choices=["mp4", "mkv", "webm", "native"],
        help="Merged video container; native leaves yt-dlp's chosen container unchanged",
    )
    parser.add_argument(
        "--yt-format",
        help="Raw yt-dlp format selector; overrides --quality for video and default bestaudio for audio",
    )

    parser.add_argument("-a", "--audio-only", action="store_true", help="Extract audio")
    parser.add_argument(
        "--audio-format",
        default="mp3",
        choices=["mp3", "m4a", "opus", "vorbis", "wav", "flac", "best"],
        help="Audio format for --audio-only (default: mp3)",
    )
    parser.add_argument(
        "--audio-quality",
        default="0",
        help="yt-dlp audio quality, where 0 is best for most encoders (default: 0)",
    )

    parser.add_argument("--playlist", action="store_true", help="Allow playlist downloads")
    parser.add_argument("--write-subs", action="store_true", help="Write available subtitles")
    parser.add_argument(
        "--write-auto-subs",
        action="store_true",
        help="Write auto-generated subtitles when available",
    )
    parser.add_argument("--sub-langs", help='Subtitle languages, e.g. "en.*,zh.*" or "all"')
    parser.add_argument("--embed-subs", action="store_true", help="Embed subtitles into the output")
    parser.add_argument("--embed-metadata", action="store_true", help="Embed media metadata")
    parser.add_argument("--write-info-json", action="store_true", help="Write yt-dlp info JSON")
    parser.add_argument("--write-thumbnail", action="store_true", help="Download thumbnail")
    parser.add_argument("--embed-thumbnail", action="store_true", help="Embed thumbnail when possible")

    parser.add_argument("--cookies", help="Path to a Netscape cookies.txt file")
    parser.add_argument(
        "--cookies-from-browser",
        help="Read cookies from a local browser profile, e.g. chrome, safari, firefox",
    )
    parser.add_argument("--proxy", help="Proxy URL, e.g. socks5://127.0.0.1:1080")
    parser.add_argument("--referer", help="HTTP referer header")
    parser.add_argument("--user-agent", help="HTTP user-agent header")
    parser.add_argument("--ffmpeg-location", help="Path to ffmpeg binary or directory")
    parser.add_argument("--js-runtimes", help="yt-dlp JavaScript runtime config, e.g. node:/path/to/node")
    parser.add_argument("--extractor-args", help='yt-dlp extractor args, e.g. "youtube:player-client=ios"')

    parser.add_argument("--download-archive", help="Record downloaded IDs and skip repeats")
    parser.add_argument("--ignore-errors", action="store_true", help="Continue on playlist item errors")
    parser.add_argument("--restrict-filenames", action="store_true", help="Use filesystem-safe ASCII names")
    parser.add_argument("--no-overwrites", action="store_true", help="Do not overwrite existing files")
    parser.add_argument("--rate-limit", help="Limit download rate, e.g. 2M or 500K")
    parser.add_argument("--concurrent-fragments", type=int, help="Parallel fragments for HLS/DASH")
    parser.add_argument("--retries", type=int, help="Retry count for normal downloads")
    parser.add_argument("--fragment-retries", type=int, help="Retry count for fragmented downloads")
    parser.add_argument("--sleep-requests", type=float, help="Sleep seconds between requests")
    parser.add_argument("--sleep-interval", type=float, help="Minimum sleep seconds between downloads")
    parser.add_argument("--max-sleep-interval", type=float, help="Maximum sleep seconds between downloads")
    parser.add_argument("--live-from-start", action="store_true", help="Download livestream from start")
    parser.add_argument(
        "--download-section",
        action="append",
        help='Download a section, e.g. "*00:01:00-00:02:00"; can be repeated',
    )

    parser.add_argument("--info", action="store_true", help="Print a concise info summary and exit")
    parser.add_argument("--json-info", action="store_true", help="Print raw yt-dlp JSON info and exit")
    parser.add_argument("--list-formats", action="store_true", help="List available formats and exit")
    parser.add_argument("--print-command", action="store_true", help="Print the yt-dlp command and exit")
    parser.add_argument("--update", action="store_true", help="Update yt-dlp before running")
    parser.add_argument("--no-auto-install", action="store_true", help="Do not install yt-dlp automatically")
    parser.add_argument("--verbose", action="store_true", help="Pass --verbose to yt-dlp")
    parser.add_argument(
        "--yt-dlp-arg",
        action="append",
        help="Extra yt-dlp argument string. For values starting with '-', use --yt-dlp-arg=--force-ipv4",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])

    if args.print_command:
        ytdlp = ytdlp_command_for_print()
    else:
        ytdlp = find_ytdlp(auto_install=not args.no_auto_install)

    if args.update and not args.print_command:
        maybe_update_ytdlp(ytdlp)

    if args.info or args.json_info or args.list_formats:
        cmd = build_probe_command(ytdlp, args)
        if args.print_command:
            print(shlex.join(cmd))
            return 0
        if args.list_formats:
            return subprocess.run(cmd, check=False).returncode
        result = subprocess.run(cmd, check=False, capture_output=True, text=True)
        if result.returncode != 0:
            sys.stderr.write(result.stderr)
            return result.returncode
        if args.json_info:
            print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
        else:
            print_summary(result.stdout)
        return 0

    if not args.print_command:
        output_dir = Path(args.output).expanduser()
        output_dir.mkdir(parents=True, exist_ok=True)
        warn_about_ffmpeg(args)

    cmd = build_download_command(ytdlp, args)
    if args.print_command:
        print(shlex.join(cmd))
        return 0
    return subprocess.run(cmd, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
