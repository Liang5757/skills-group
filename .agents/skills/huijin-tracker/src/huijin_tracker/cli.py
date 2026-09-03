from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import date, timedelta
from pathlib import Path

from .db import TrackerDatabase
from .notifier import render_event, summarize_events
from .service import TrackerService


def _csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _open(args: argparse.Namespace) -> tuple[TrackerDatabase, TrackerService]:
    db = TrackerDatabase(args.db)
    db.initialize()
    service = TrackerService(db, archive_dir=args.archive_dir)
    return db, service


def _print_event_batch(events, *, include_related: bool, show_limit: int) -> None:
    visible_universe = [
        event
        for event in events
        if include_related or event.attribution.value != "RELATED_CONTROLLED"
    ]
    related_count = len(events) - len(visible_universe)
    print(
        f"new_events_total={len(events)} non_related_events={len(visible_universe)} "
        f"related_controlled_events={related_count}"
    )
    print(summarize_events(visible_universe))
    for event in visible_universe[:show_limit]:
        print(render_event(event), "", sep="\n")
    omitted = len(visible_universe) - show_limit
    if omitted > 0:
        print(f"... 另有 {omitted} 条已入账；使用 --show-limit 调整展开数量。")
    if related_count and not include_related:
        print("关联受控主体事件已单独入账，默认不作为中央汇金直接操作展示；用 --include-related 查看。")


def _run_watch_cycle(
    service: TrackerService,
    *,
    years: list[int],
    lookback_days: int,
    plates: list[str],
) -> int:
    today = date.today()
    since = today - timedelta(days=lookback_days)
    failures = 0
    try:
        events = service.collect_huijin(years)
        print(f"[{today.isoformat()}] huijin_official new_events={len(events)}", flush=True)
    except Exception as error:
        failures += 1
        print(f"[{today.isoformat()}] huijin_official error: {error}", file=sys.stderr, flush=True)
    try:
        documents = service.collect_cninfo(
            since=since.isoformat(),
            until=today.isoformat(),
            keywords=["中央汇金", "汇金资管"],
            plates=plates,
        )
        print(f"[{today.isoformat()}] cninfo new_documents={documents}", flush=True)
    except Exception as error:
        failures += 1
        print(f"[{today.isoformat()}] cninfo error: {error}", file=sys.stderr, flush=True)
    try:
        events = service.collect_hkex(since=since.isoformat(), until=today.isoformat())
        print(f"[{today.isoformat()}] hkex_di new_events={len(events)}", flush=True)
    except Exception as error:
        failures += 1
        print(f"[{today.isoformat()}] hkex_di error: {error}", file=sys.stderr, flush=True)
    try:
        service.retry_notifications()
    except Exception as error:
        failures += 1
        print(f"[{today.isoformat()}] notification error: {error}", file=sys.stderr, flush=True)
    return failures


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="huijin-tracker",
        description="Track publicly disclosed Central Huijin events without pretending snapshot changes are live trades.",
    )
    parser.add_argument("--db", default="data/huijin.db", help="SQLite database path")
    parser.add_argument("--archive-dir", default="data/archive", help="raw evidence archive directory")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="initialize the SQLite ledger")

    huijin = sub.add_parser("collect-huijin", help="collect Central Huijin official information-center pages")
    huijin.add_argument("--years", default=str(date.today().year), help="comma-separated years")

    cninfo = sub.add_parser("collect-cninfo", help="collect CNINFO announcement metadata whose titles match keywords")
    cninfo.add_argument("--since", required=True, help="YYYY-MM-DD")
    cninfo.add_argument("--until", required=True, help="YYYY-MM-DD")
    cninfo.add_argument(
        "--keywords",
        default="中央汇金,汇金资管",
        help="comma-separated title keywords; CNINFO searchkey does not search every PDF body",
    )
    cninfo.add_argument("--plates", default="sh,sz,bj", help="comma-separated sh,sz,bj")

    hkex = sub.add_parser("collect-hkex", help="collect official HKEX disclosure-of-interests filings")
    hkex.add_argument("--since", required=True, help="YYYY-MM-DD; interval cannot exceed 366 days")
    hkex.add_argument("--until", required=True, help="YYYY-MM-DD")

    holdings = sub.add_parser("sync-holdings", help="run a full-market top-10 holder scan via Eastmoney aggregation")
    holdings.add_argument("--period", required=True, help="quarter end in YYYY-MM-DD")
    holdings.add_argument("--scope", choices=("top10", "top10_float"), required=True)
    holdings.add_argument(
        "--include-related",
        action="store_true",
        help="also display and notify China Securities Finance events; they are always stored separately",
    )
    holdings.add_argument("--show-limit", type=int, default=20, help="maximum expanded events (default: 20)")
    holdings.add_argument("--max-pages", type=int, help="smoke-test limit; incomplete scans suppress LEFT_TOP10")
    holdings.add_argument(
        "--force-complete",
        action="store_true",
        help="treat an open reporting period as complete; use only after independently verifying coverage",
    )

    events = sub.add_parser("events", help="show recorded events")
    events.add_argument("--limit", type=int, default=100)
    events.add_argument("--json", action="store_true")
    events.add_argument("--include-related", action="store_true")

    sub.add_parser("status", help="show per-source freshness and failures")

    watch = sub.add_parser("watch", help="continuously poll official disclosure sources")
    watch.add_argument("--interval-seconds", type=int, default=1800)
    watch.add_argument("--lookback-days", type=int, default=14)
    watch.add_argument("--years", help="comma-separated years; default: current and previous year")
    watch.add_argument("--plates", default="sh,sz,bj")
    watch.add_argument("--once", action="store_true", help="run one cycle and exit")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    db, service = _open(args)
    try:
        if args.command == "init":
            print(f"initialized {Path(args.db).resolve()}")
        elif args.command == "collect-huijin":
            events = service.collect_huijin(int(year) for year in _csv(args.years))
            print(f"new_events={len(events)}")
            for event in events:
                print(render_event(event), "", sep="\n")
        elif args.command == "collect-cninfo":
            count = service.collect_cninfo(
                since=args.since,
                until=args.until,
                keywords=_csv(args.keywords),
                plates=_csv(args.plates),
            )
            print(f"new_documents={count}")
        elif args.command == "collect-hkex":
            events = service.collect_hkex(since=args.since, until=args.until)
            _print_event_batch(events, include_related=False, show_limit=20)
        elif args.command == "sync-holdings":
            events = service.sync_eastmoney_holdings(
                period_end=args.period,
                scope=args.scope,
                notify_related=args.include_related,
                max_pages=args.max_pages,
                force_complete=args.force_complete,
            )
            _print_event_batch(
                events,
                include_related=args.include_related,
                show_limit=max(0, args.show_limit),
            )
        elif args.command == "events":
            rows = db.list_events(args.limit, include_related=args.include_related)
            if args.json:
                print(json.dumps(rows, ensure_ascii=False, indent=2))
            else:
                for row in rows:
                    print(
                        f"{row['event_type']:<22} {row['event_date'] or '—':<10} "
                        f"{row['holder_name']} | {row['instrument_code']} {row['instrument_name']} | "
                        f"{row['confidence']}"
                    )
        elif args.command == "status":
            rows = db.source_status()
            if not rows:
                print("no source runs recorded")
            for row in rows:
                health = "FAILED" if row["consecutive_failures"] >= 2 else "OK"
                print(
                    f"{row['source']:<30} {health:<6} failures={row['consecutive_failures']} "
                    f"last_success={row['last_success_at'] or '—'} last_record={row['last_record_at'] or '—'}"
                )
        elif args.command == "watch":
            if args.interval_seconds < 60 and not args.once:
                parser.error("--interval-seconds must be at least 60 for continuous polling")
            if args.lookback_days < 1:
                parser.error("--lookback-days must be positive")
            current_year = date.today().year
            years = (
                [int(year) for year in _csv(args.years)]
                if args.years
                else [current_year - 1, current_year]
            )
            while True:
                failures = _run_watch_cycle(
                    service,
                    years=years,
                    lookback_days=args.lookback_days,
                    plates=_csv(args.plates),
                )
                if args.once:
                    return 1 if failures else 0
                time.sleep(args.interval_seconds)
        return 0
    except KeyboardInterrupt:
        print("stopped", file=sys.stderr)
        return 130
    except Exception as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    finally:
        db.close()
