"""Compare an env file against a template and collect findings."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from .parser import EnvFile

# Severity per finding kind. Errors fail the check; warnings only with --strict.
SEVERITY = {
    "parse": "error",
    "missing": "error",
    "empty": "warning",
    "extra": "warning",
    "duplicate": "warning",
}


@dataclass
class Finding:
    kind: str
    key: str
    message: str
    file: str
    line: int | None = None

    @property
    def severity(self) -> str:
        return SEVERITY[self.kind]

    def to_dict(self) -> dict:
        data = asdict(self)
        data["severity"] = self.severity
        return data


@dataclass
class Report:
    env: str
    template: str
    findings: list[Finding] = field(default_factory=list)

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "error"]

    @property
    def warnings(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "warning"]

    def ok(self, strict: bool = False) -> bool:
        return not self.errors and not (strict and self.warnings)


def compare(
    env: EnvFile,
    template: EnvFile,
    *,
    allow_empty: frozenset[str] = frozenset(),
    ignore: frozenset[str] = frozenset(),
) -> Report:
    report = Report(env=env.path, template=template.path)
    add = report.findings.append

    for source in (template, env):
        for err in source.errors:
            add(Finding("parse", "", err.message, source.path, err.line))

    env_values = env.as_dict()
    env_lines = {e.key: e.line for e in env.entries}
    template_values = template.as_dict()

    for key in template.keys:
        if key in ignore:
            continue
        if key not in env_values:
            add(Finding("missing", key, f"{key} is in the template but not set", env.path))
        elif env_values[key] == "" and key not in allow_empty and template_values[key] != "":
            # Empty is only suspicious when the template shows a real example value.
            add(Finding("empty", key, f"{key} is set but empty", env.path, env_lines[key]))

    for key in env.keys:
        if key not in template_values and key not in ignore:
            add(Finding("extra", key, f"{key} is not in the template", env.path, env_lines[key]))

    for key, lines in env.duplicates().items():
        joined = ", ".join(str(n) for n in lines)
        add(Finding("duplicate", key, f"{key} is defined {len(lines)} times (lines {joined})", env.path, lines[-1]))

    return report
