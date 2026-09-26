"""Command line interface: ``envguard [ENV] [--template FILE]``."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from . import __version__
from .checker import Report, compare
from .parser import parse_file

EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_USAGE = 2

TEMPLATE_CANDIDATES = (".env.example", ".env.sample", ".env.template", ".env.dist")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="envguard",
        description="Check a .env file against its template (.env.example).",
    )
    p.add_argument("env", nargs="?", default=".env", help="env file to check (default: .env)")
    p.add_argument("-t", "--template", help="template file (default: first of %s)" % ", ".join(TEMPLATE_CANDIDATES))
    p.add_argument("--strict", action="store_true", help="treat warnings (extra, empty, duplicate) as failures")
    p.add_argument("--allow-empty", action="append", default=[], metavar="KEY", help="key allowed to be empty (repeatable)")
    p.add_argument("--ignore", action="append", default=[], metavar="KEY", help="key to skip entirely (repeatable)")
    p.add_argument("--process-env", action="store_true", help="check the current process environment instead of a file (useful in CI)")
    p.add_argument("--format", choices=("text", "json", "github"), default="text", help="output format")
    p.add_argument("--no-color", action="store_true", help="disable colored output")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def find_template(env_path: Path) -> Path | None:
    for name in TEMPLATE_CANDIDATES:
        candidate = env_path.parent / name
        if candidate.is_file():
            return candidate
    return None


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    env_path = Path(args.env)

    template_path = Path(args.template) if args.template else find_template(env_path)
    if template_path is None or not template_path.is_file():
        print(f"envguard: no template found (looked for {', '.join(TEMPLATE_CANDIDATES)})", file=sys.stderr)
        return EXIT_USAGE

    template = parse_file(template_path)
    if args.process_env:
        from .parser import Entry, EnvFile

        env = EnvFile(path="<environment>", entries=[Entry(k, v, 0) for k, v in os.environ.items()])
        # The process environment holds far more than the app needs, so extras are noise here.
        ignore = set(args.ignore) | (set(env.keys) - set(template.keys))
    else:
        if not env_path.is_file():
            print(f"envguard: {env_path} not found", file=sys.stderr)
            return EXIT_USAGE
        env = parse_file(env_path)
        ignore = set(args.ignore)

    report = compare(env, template, allow_empty=frozenset(args.allow_empty), ignore=frozenset(ignore))

    if args.format == "json":
        print(render_json(report, args.strict))
    elif args.format == "github":
        print(render_github(report, args.strict))
    else:
        color = not args.no_color and sys.stdout.isatty() and "NO_COLOR" not in os.environ
        print(render_text(report, args.strict, color))

    return EXIT_OK if report.ok(args.strict) else EXIT_FINDINGS


def render_text(report: Report, strict: bool, color: bool) -> str:
    def paint(text: str, code: str) -> str:
        return f"\033[{code}m{text}\033[0m" if color else text

    lines = [f"Checking {report.env} against {report.template}"]
    for f in report.findings:
        failing = f.severity == "error" or strict
        tag = paint("✗", "31") if failing else paint("!", "33")
        where = f" (line {f.line})" if f.line else ""
        lines.append(f"  {tag} {f.kind:<9} {f.message}{where}")
    if not report.findings:
        lines.append("  " + paint("✓", "32") + " all keys present")
    summary = f"{len(report.errors)} error(s), {len(report.warnings)} warning(s)"
    lines.append(paint(summary, "32" if report.ok(strict) else "31"))
    return "\n".join(lines)


def render_json(report: Report, strict: bool) -> str:
    return json.dumps(
        {
            "env": report.env,
            "template": report.template,
            "ok": report.ok(strict),
            "findings": [f.to_dict() for f in report.findings],
        },
        indent=2,
    )


def render_github(report: Report, strict: bool) -> str:
    """GitHub Actions workflow commands, so findings show up as annotations."""
    out = []
    for f in report.findings:
        level = "error" if f.severity == "error" or strict else "warning"
        loc = f"file={f.file}" + (f",line={f.line}" if f.line else "")
        out.append(f"::{level} {loc},title=envguard {f.kind}::{f.message}")
    return "\n".join(out) or "envguard: no findings"


if __name__ == "__main__":
    sys.exit(main())
