#!/usr/bin/env python3
"""Analyze local Codex history for developer growth signals."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|token|secret|password|authorization)\s*[:=]\s*['\"]?[^'\"\s]+"),
    re.compile(r"(?i)bearer\s+[a-z0-9._\-]+"),
]

TECH_PATTERNS = {
    "Python": r"\bpython|pytest|pip|venv|fastapi|django|flask\b",
    "JavaScript/TypeScript": r"\btypescript|javascript|node|npm|pnpm|yarn|tsx?|jsx?\b",
    "React/frontend": r"\breact|next\.?js|vue|svelte|css|tailwind|frontend|ui|layout|responsive\b",
    "Backend/API": r"\bapi|backend|server|endpoint|graphql|rest|auth|oauth\b",
    "Database/data": r"\bsql|postgres|mysql|sqlite|redis|database|migration|schema|query\b",
    "Testing": r"\btest|tests|pytest|jest|vitest|playwright|coverage|mock\b",
    "DevOps": r"\bdocker|kubernetes|deploy|ci|cd|github actions|workflow|release|build\b",
    "AI/LLM": r"\bllm|openai|codex|agent|prompt|embedding|rag|model\b",
}

PROBLEM_PATTERNS = {
    "Debugging and bug fixing": r"\bbug|fix|error|exception|traceback|failed|failure|broken|debug\b",
    "Feature implementation": r"\bimplement|add|create|build|feature|support|enable\b",
    "Refactoring and maintainability": r"\brefactor|cleanup|simplify|rename|restructure|maintain\b",
    "Testing and validation": r"\btest|validate|verify|lint|typecheck|coverage|playwright\b",
    "Architecture and design": r"\barchitecture|design|plan|approach|tradeoff|schema|interface\b",
    "Performance and reliability": r"\bperformance|slow|optimi[sz]e|race|timeout|cache|reliable\b",
    "Security and privacy": r"\bsecurity|privacy|secret|token|credential|permission|auth\b",
    "Documentation and communication": r"\breadme|doc|documentation|explain|summary|write\b",
}

GROWTH_SIGNALS = {
    "Testing discipline": {
        "pattern": r"\b(test failed|failing test|no tests|untested|coverage|regression|flaky)\b",
        "practice": "Add a small red/green test or verification checklist before changing shared behavior.",
        "time": "2-4 hours to set up a reusable habit, then ongoing practice",
    },
    "Debugging strategy": {
        "pattern": r"\b(debug|traceback|error|exception|stuck|doesn't work|not working|failed)\b",
        "practice": "Write down the observed symptom, one hypothesis, and the next smallest diagnostic command before patching.",
        "time": "1-3 focused sessions",
    },
    "Type and data modeling": {
        "pattern": r"\b(type error|typing|schema|interface|model|validation|null|undefined|optional)\b",
        "practice": "Model input/output shapes explicitly and add boundary validation near external data.",
        "time": "4-8 hours depending on language depth",
    },
    "Async and state management": {
        "pattern": r"\b(async|await|promise|race|state|loading|timeout|concurrent|parallel)\b",
        "practice": "Diagram request/state transitions and test loading, failure, retry, and cancellation paths.",
        "time": "3-6 hours plus one applied refactor",
    },
    "Security and sensitive data handling": {
        "pattern": r"\b(secret|token|credential|password|privacy|permission|auth|leak|sanitize)\b",
        "practice": "Create a whitelist for safe display/logging and review data boundaries before UI or log output.",
        "time": "2-5 hours plus a project-specific checklist",
    },
    "Frontend layout robustness": {
        "pattern": r"\b(css|layout|responsive|overflow|mobile|viewport|grid|flex|ui)\b",
        "practice": "Verify the key screen at mobile and desktop widths and add constraints for fixed-format controls.",
        "time": "3-6 hours of focused layout practice",
    },
    "Release and automation hygiene": {
        "pattern": r"\b(release|deploy|ci|workflow|automation|script|build|version)\b",
        "practice": "Document the release path and automate one repeatable check at a time.",
        "time": "2-4 hours for the first automation pass",
    },
}

STRENGTH_SIGNALS = {
    "Verification mindset": r"\b(test|verify|validate|check|lint|typecheck|screenshot|inspect)\b",
    "Iterative implementation": r"\b(iterate|revise|adjust|polish|fix|follow[- ]?up|update)\b",
    "User-facing quality": r"\b(user|ux|copy|design|responsive|accessibility|readable)\b",
    "Security awareness": r"\b(security|privacy|secret|token|credential|permission)\b",
    "Automation orientation": r"\b(automate|script|workflow|ci|repeatable|schedule)\b",
}

ZH_LABELS = {
    "React/frontend": "React/前端",
    "Backend/API": "后端/API",
    "Database/data": "数据库/数据",
    "Testing": "测试",
    "DevOps": "DevOps",
    "AI/LLM": "AI/LLM",
    "Debugging and bug fixing": "调试与缺陷修复",
    "Feature implementation": "功能实现",
    "Refactoring and maintainability": "重构与可维护性",
    "Testing and validation": "测试与验证",
    "Architecture and design": "架构与设计",
    "Performance and reliability": "性能与可靠性",
    "Security and privacy": "安全与隐私",
    "Documentation and communication": "文档与沟通",
    "Testing discipline": "测试纪律",
    "Debugging strategy": "调试策略",
    "Type and data modeling": "类型与数据建模",
    "Async and state management": "异步与状态管理",
    "Security and sensitive data handling": "安全与敏感数据处理",
    "Frontend layout robustness": "前端布局韧性",
    "Release and automation hygiene": "发布与自动化规范",
    "Verification mindset": "验证意识",
    "Iterative implementation": "迭代实现能力",
    "User-facing quality": "用户体验质量意识",
    "Security awareness": "安全意识",
    "Automation orientation": "自动化倾向",
}

ZH_GROWTH_DETAILS = {
    "Testing discipline": {
        "practice": "在修改共享行为前，先补一个小型红绿测试或验证清单。",
        "time": "2-4 小时建立可复用习惯，之后持续练习",
        "learning_query": "软件工程测试纪律 回归测试 最佳实践",
    },
    "Debugging strategy": {
        "practice": "动手修改前，先写下观察到的现象、一个假设和下一条最小诊断命令。",
        "time": "1-3 次专注练习",
        "learning_query": "软件调试策略 假设驱动排查 方法",
    },
    "Type and data modeling": {
        "practice": "明确建模输入/输出形状，并在外部数据边界附近加入校验。",
        "time": "4-8 小时，取决于语言和类型系统深度",
        "learning_query": "TypeScript 类型建模 数据边界校验 最佳实践",
    },
    "Async and state management": {
        "practice": "画出请求与状态流转，并覆盖加载、失败、重试和取消路径。",
        "time": "3-6 小时，加一次真实代码重构练习",
        "learning_query": "异步状态管理 loading error retry cancellation 测试",
    },
    "Security and sensitive data handling": {
        "practice": "为安全展示/日志建立白名单，并在 UI 或日志输出前复查数据边界。",
        "time": "2-5 小时，加一份项目级检查清单",
        "learning_query": "敏感数据处理 日志脱敏 安全边界 最佳实践",
    },
    "Frontend layout robustness": {
        "practice": "在移动端和桌面宽度验证关键页面，并为固定格式控件增加稳定尺寸约束。",
        "time": "3-6 小时专注布局练习",
        "learning_query": "前端响应式布局 溢出处理 稳定控件尺寸 最佳实践",
    },
    "Release and automation hygiene": {
        "practice": "写清发布路径，并每次自动化一个可重复检查。",
        "time": "2-4 小时完成第一轮自动化整理",
        "learning_query": "发布流程自动化 CI 检查 工程实践",
    },
}


def default_history_path() -> Path:
    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        return Path(codex_home).expanduser() / "history.jsonl"
    return Path.home() / ".codex" / "history.jsonl"


def parse_timestamp(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        seconds = value / 1000 if value > 10_000_000_000 else value
        return datetime.fromtimestamp(seconds, tz=timezone.utc)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        if text.isdigit():
            return parse_timestamp(int(text))
        try:
            if text.endswith("Z"):
                text = text[:-1] + "+00:00"
            parsed = datetime.fromisoformat(text)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except ValueError:
            return None
    return None


def redact(text: str) -> str:
    redacted = text
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub(lambda match: re.split(r"[:=]", match.group(0), maxsplit=1)[0] + "=[REDACTED]", redacted)
    return redacted


def entry_text(entry: Dict[str, Any]) -> str:
    chunks: List[str] = []
    for key in ("display", "text", "message", "prompt", "project"):
        value = entry.get(key)
        if isinstance(value, str):
            chunks.append(value)
    pasted = entry.get("pastedContents")
    if isinstance(pasted, str):
        chunks.append(pasted)
    elif isinstance(pasted, list):
        for item in pasted:
            if isinstance(item, str):
                chunks.append(item)
            elif isinstance(item, dict):
                for value in item.values():
                    if isinstance(value, str):
                        chunks.append(value)
    return "\n".join(chunks)


def load_entries(history: Path, start: datetime, end: datetime, projects: Optional[List[str]], max_entries: Optional[int]) -> List[Dict[str, Any]]:
    if not history.exists():
        return []

    selected: List[Dict[str, Any]] = []
    project_filters = [item.lower() for item in projects or []]
    with history.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            timestamp = parse_timestamp(entry.get("timestamp") or entry.get("time") or entry.get("created_at") or entry.get("ts"))
            if timestamp is None or timestamp < start or timestamp > end:
                continue
            project = str(entry.get("project") or "")
            if project_filters and not any(filter_text in project.lower() for filter_text in project_filters):
                continue
            entry["_line"] = line_number
            entry["_timestamp"] = timestamp.isoformat()
            entry["_text"] = redact(entry_text(entry))
            selected.append(entry)

    selected.sort(key=lambda item: item.get("_timestamp", ""))
    if max_entries:
        selected = selected[-max_entries:]
    return selected


def count_patterns(entries: Iterable[Dict[str, Any]], patterns: Dict[str, str]) -> Counter:
    counts: Counter = Counter()
    compiled = {name: re.compile(pattern, re.IGNORECASE) for name, pattern in patterns.items()}
    for entry in entries:
        text = entry.get("_text", "")
        for name, pattern in compiled.items():
            if pattern.search(text):
                counts[name] += 1
    return counts


def evidence_for(entries: List[Dict[str, Any]], pattern: str, limit: int = 3) -> List[str]:
    compiled = re.compile(pattern, re.IGNORECASE)
    evidence: List[str] = []
    for entry in entries:
        text = " ".join(entry.get("_text", "").split())
        if not compiled.search(text):
            continue
        snippet = text[:220] + ("..." if len(text) > 220 else "")
        project = entry.get("project") or "unknown project"
        evidence.append(f"{entry.get('_timestamp', 'unknown time')} - {project}: {snippet}")
        if len(evidence) >= limit:
            break
    return evidence


def summarize(entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    tech_counts = count_patterns(entries, TECH_PATTERNS)
    problem_counts = count_patterns(entries, PROBLEM_PATTERNS)
    strength_counts = count_patterns(entries, STRENGTH_SIGNALS)

    growth_areas: List[Dict[str, Any]] = []
    for area, config in GROWTH_SIGNALS.items():
        pattern = config["pattern"]
        count = count_patterns(entries, {area: pattern})[area]
        if count == 0:
            continue
        growth_areas.append(
            {
                "area": area,
                "signal_count": count,
                "evidence": evidence_for(entries, pattern),
                "recommended_practice": config["practice"],
                "time_to_skill_up": config["time"],
                "learning_query": f"{area} best practices for software developers",
            }
        )
    growth_areas.sort(key=lambda item: item["signal_count"], reverse=True)

    projects = Counter(str(entry.get("project") or "unknown project") for entry in entries)
    return {
        "entry_count": len(entries),
        "projects": projects.most_common(),
        "technologies": tech_counts.most_common(),
        "problem_types": problem_counts.most_common(),
        "strengths": strength_counts.most_common(),
        "growth_areas": growth_areas[:5],
    }


def report_period(args: argparse.Namespace) -> Tuple[datetime, datetime]:
    end = datetime.now(timezone.utc)
    if args.until:
        parsed_end = parse_timestamp(args.until)
        if parsed_end:
            end = parsed_end
    if args.since:
        start = parse_timestamp(args.since)
        if start is None:
            raise SystemExit(f"error: could not parse --since timestamp: {args.since}")
    elif args.since_hours:
        start = end - timedelta(hours=args.since_hours)
    else:
        start = end - timedelta(days=args.days)
    return start, end


def render_markdown(context: Dict[str, Any]) -> str:
    if context.get("language") == "zh":
        return render_markdown_zh(context)
    return render_markdown_en(context)


def render_markdown_en(context: Dict[str, Any]) -> str:
    summary = context["summary"]
    period = context["period"]
    lines = [
        "# Developer Growth Report",
        "",
        f"**Report Period**: {period['start']} to {period['end']} UTC",
        f"**Source**: `{context['history']}`",
        f"**Generated**: {context['generated_at']}",
        f"**Entries Analyzed**: {summary['entry_count']}",
        "",
        "## Work Summary",
        "",
    ]
    if summary["entry_count"] == 0:
        lines.extend(["No matching history entries were found for this period.", ""])
    else:
        project_text = ", ".join(f"{name} ({count})" for name, count in summary["projects"][:5]) or "unknown"
        tech_text = ", ".join(f"{name} ({count})" for name, count in summary["technologies"][:6]) or "not enough signal"
        problem_text = ", ".join(f"{name} ({count})" for name, count in summary["problem_types"][:6]) or "not enough signal"
        lines.extend(
            [
                f"You worked across: {project_text}.",
                f"Technology signals: {tech_text}.",
                f"Problem-type signals: {problem_text}.",
                "",
            ]
        )

    lines.extend(["## Strengths Observed", ""])
    if summary["strengths"]:
        for name, count in summary["strengths"][:5]:
            lines.append(f"- **{name}**: observed in {count} history entries.")
    else:
        lines.append("- Not enough signal to identify strengths from the selected entries.")

    lines.extend(["", "## Growth Areas", ""])
    if summary["growth_areas"]:
        for index, area in enumerate(summary["growth_areas"], start=1):
            lines.extend(
                [
                    f"### {index}. {area['area']}",
                    f"**Signal Count**: {area['signal_count']}",
                    f"**Recommended Practice**: {area['recommended_practice']}",
                    f"**Time to Skill Up**: {area['time_to_skill_up']}",
                    "**Evidence**:",
                ]
            )
            for evidence in area["evidence"]:
                lines.append(f"- {evidence}")
            lines.append("")
    else:
        lines.append("No strong repeated growth signals were detected. Use a longer range or provide more work context.")
        lines.append("")

    lines.extend(["## Action Plan", ""])
    if summary["growth_areas"]:
        for index, area in enumerate(summary["growth_areas"][:3], start=1):
            lines.append(f"{index}. Practice: {area['recommended_practice']}")
    else:
        lines.append("1. Review a broader period or add project notes to improve the analysis.")

    lines.extend(["", "## Learning Queries", ""])
    if summary["growth_areas"]:
        for area in summary["growth_areas"]:
            lines.append(f"- {area['learning_query']}")
    else:
        lines.append("- No targeted queries generated.")

    return "\n".join(lines).rstrip() + "\n"


def zh_label(name: str) -> str:
    return ZH_LABELS.get(name, name)


def zh_project_name(name: str) -> str:
    return "未知项目" if name == "unknown project" else name


def zh_evidence(text: str) -> str:
    return text.replace("unknown time", "未知时间").replace("unknown project", "未知项目")


def zh_growth_detail(area: Dict[str, Any], key: str) -> str:
    details = ZH_GROWTH_DETAILS.get(area["area"], {})
    return details.get(key, area.get({"practice": "recommended_practice", "time": "time_to_skill_up", "learning_query": "learning_query"}[key], ""))


def render_markdown_zh(context: Dict[str, Any]) -> str:
    summary = context["summary"]
    period = context["period"]
    lines = [
        "# 开发者成长报告",
        "",
        f"**报告周期**: {period['start']} 至 {period['end']} UTC",
        f"**来源**: `{context['history']}`",
        f"**生成时间**: {context['generated_at']}",
        f"**分析条目数**: {summary['entry_count']}",
        "",
        "## 工作概览",
        "",
    ]
    if context.get("source_missing"):
        lines.extend([f"历史文件不存在：`{context['history']}`。", ""])
    if summary["entry_count"] == 0:
        lines.extend(["所选周期内没有找到匹配的历史记录。", ""])
    else:
        project_text = ", ".join(f"{zh_project_name(name)} ({count})" for name, count in summary["projects"][:5]) or "未知"
        tech_text = ", ".join(f"{zh_label(name)} ({count})" for name, count in summary["technologies"][:6]) or "信号不足"
        problem_text = ", ".join(f"{zh_label(name)} ({count})" for name, count in summary["problem_types"][:6]) or "信号不足"
        lines.extend(
            [
                f"本周期涉及项目：{project_text}。",
                f"技术信号：{tech_text}。",
                f"任务类型信号：{problem_text}。",
                "",
            ]
        )

    lines.extend(["## 已观察到的优势", ""])
    if summary["strengths"]:
        for name, count in summary["strengths"][:5]:
            lines.append(f"- **{zh_label(name)}**：在 {count} 条历史记录中出现。")
    else:
        lines.append("- 所选记录信号不足，暂时无法稳定识别优势。")

    lines.extend(["", "## 成长重点", ""])
    if summary["growth_areas"]:
        for index, area in enumerate(summary["growth_areas"], start=1):
            lines.extend(
                [
                    f"### {index}. {zh_label(area['area'])}",
                    f"**信号次数**: {area['signal_count']}",
                    f"**推荐练习**: {zh_growth_detail(area, 'practice')}",
                    f"**预计投入**: {zh_growth_detail(area, 'time')}",
                    "**证据**:",
                ]
            )
            for evidence in area["evidence"]:
                lines.append(f"- {zh_evidence(evidence)}")
            lines.append("")
    else:
        lines.append("没有检测到足够强的重复成长信号。可以拉长时间范围，或补充更多项目上下文。")
        lines.append("")

    lines.extend(["## 行动计划", ""])
    if summary["growth_areas"]:
        for index, area in enumerate(summary["growth_areas"][:3], start=1):
            lines.append(f"{index}. 练习：{zh_growth_detail(area, 'practice')}")
    else:
        lines.append("1. 复盘更长周期，或补充项目笔记，以提升分析质量。")

    lines.extend(["", "## 学习查询", ""])
    if summary["growth_areas"]:
        for area in summary["growth_areas"]:
            lines.append(f"- {zh_growth_detail(area, 'learning_query')}")
    else:
        lines.append("- 暂无可生成的定向学习查询。")

    return "\n".join(lines).rstrip() + "\n"


def build_context(args: argparse.Namespace) -> Dict[str, Any]:
    history = Path(args.history).expanduser().resolve() if args.history else default_history_path()
    start, end = report_period(args)
    source_missing = not history.exists()
    entries = load_entries(history, start, end, args.project, args.max_entries)
    summary = summarize(entries)
    return {
        "history": str(history),
        "period": {"start": start.isoformat(), "end": end.isoformat()},
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "language": args.language,
        "source_missing": source_missing,
        "summary": summary,
    }


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--history", help="Path to Codex history JSONL. Defaults to $CODEX_HOME/history.jsonl or ~/.codex/history.jsonl")
    parser.add_argument("--days", type=float, default=7, help="Days to analyze when --since/--since-hours is omitted")
    parser.add_argument("--since-hours", type=float, help="Analyze the trailing N hours")
    parser.add_argument("--since", help="Start timestamp, ISO string or Unix timestamp")
    parser.add_argument("--until", help="End timestamp, ISO string or Unix timestamp")
    parser.add_argument("--project", action="append", help="Filter by project substring. Can be repeated")
    parser.add_argument("--max-entries", type=int, help="Limit entries after filtering")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--language", choices=("en", "zh"), default="en", help="Language for markdown reports")
    parser.add_argument("--output", help="Write report to this file")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    context = build_context(args)
    if args.format == "json":
        rendered = json.dumps(context, indent=2, ensure_ascii=False) + "\n"
    else:
        rendered = render_markdown(context)

    if args.output:
        output = Path(args.output).expanduser()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
