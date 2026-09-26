"""A small, forgiving parser for dotenv files.

Supports the common subset used by docker compose, python-dotenv and friends:
comments, blank lines, an optional ``export`` prefix, single and double quoted
values (double quotes may span lines), and inline ``# comments`` after
unquoted values.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]*$")


@dataclass
class Entry:
    key: str
    value: str
    line: int


@dataclass
class ParseError:
    line: int
    message: str


@dataclass
class EnvFile:
    path: str
    entries: list[Entry] = field(default_factory=list)
    errors: list[ParseError] = field(default_factory=list)

    @property
    def keys(self) -> list[str]:
        seen: dict[str, None] = {}
        for entry in self.entries:
            seen.setdefault(entry.key, None)
        return list(seen)

    def as_dict(self) -> dict[str, str]:
        # Last assignment wins, like most dotenv loaders.
        return {entry.key: entry.value for entry in self.entries}

    def duplicates(self) -> dict[str, list[int]]:
        lines: dict[str, list[int]] = {}
        for entry in self.entries:
            lines.setdefault(entry.key, []).append(entry.line)
        return {key: nums for key, nums in lines.items() if len(nums) > 1}


def parse_file(path: str | Path) -> EnvFile:
    text = Path(path).read_text(encoding="utf-8-sig")
    return parse_text(text, str(path))


def parse_text(text: str, path: str = "<string>") -> EnvFile:
    result = EnvFile(path=path)
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        lineno = i + 1
        raw = lines[i]
        i += 1
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("export "):
            stripped = stripped[len("export "):].lstrip()
        if "=" not in stripped:
            result.errors.append(ParseError(lineno, f"expected KEY=VALUE, got {stripped!r}"))
            continue
        key, _, rest = stripped.partition("=")
        key = key.strip()
        if not KEY_RE.match(key):
            result.errors.append(ParseError(lineno, f"invalid key {key!r}"))
            continue
        rest = rest.strip()

        if rest[:1] in ("'", '"'):
            quote = rest[0]
            body = rest[1:]
            end = _find_closing(body, quote)
            # Double-quoted values may continue onto following lines.
            while end == -1 and quote == '"' and i < len(lines):
                body += "\n" + lines[i]
                i += 1
                end = _find_closing(body, quote)
            if end == -1:
                result.errors.append(ParseError(lineno, f"unterminated {quote} quote for {key}"))
                continue
            value = body[:end]
            if quote == '"':
                value = _unescape(value)
        else:
            value = re.split(r"\s+#", rest, maxsplit=1)[0].strip()

        result.entries.append(Entry(key, value, lineno))
    return result


def _find_closing(body: str, quote: str) -> int:
    escaped = False
    for idx, ch in enumerate(body):
        if escaped:
            escaped = False
        elif ch == "\\" and quote == '"':
            escaped = True
        elif ch == quote:
            return idx
    return -1


def _unescape(value: str) -> str:
    replacements = {"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\"}
    out = []
    chars = iter(value)
    for ch in chars:
        if ch == "\\":
            nxt = next(chars, "")
            out.append(replacements.get(nxt, "\\" + nxt))
        else:
            out.append(ch)
    return "".join(out)
