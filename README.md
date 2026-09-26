# envguard

**Catch the missing environment variable before your app does.**

`envguard` checks a `.env` file against its template (`.env.example`) and tells you
what's missing, empty, extra or duplicated. It exits non-zero on problems, so it
fits in a pre-commit hook, a `make` target or CI. Pure Python, no dependencies.

```console
$ envguard
Checking .env against .env.example
  ! empty     SECRET_KEY is set but empty (line 2)
  ✗ missing   STRIPE_KEY is in the template but not set
  ! extra     OLD_FLAG is not in the template (line 4)
1 error(s), 2 warning(s)
```

## Install

```console
pipx install git+https://github.com/UmutAlisoglu/envguard
```

Requires Python 3.9+.

## Usage

```console
envguard                         # check ./.env against ./.env.example
envguard config/.env.local       # template is looked up next to the file
envguard -t .env.dist            # explicit template
envguard --strict                # warnings fail too
envguard --allow-empty DEBUG     # DEBUG may be empty (repeatable)
envguard --ignore LOCAL_ONLY     # skip a key entirely (repeatable)
envguard --process-env           # check the real environment (CI, containers)
envguard --format json           # machine-readable output
envguard --format github         # GitHub Actions annotations
```

Templates are found automatically in this order: `.env.example`, `.env.sample`,
`.env.template`, `.env.dist`.

## What it checks

| Finding     | Severity | Meaning |
|-------------|----------|---------|
| `missing`   | error    | Key is in the template but not in your env. |
| `parse`     | error    | A line that isn't `KEY=VALUE`, a bad key name, or an unclosed quote. |
| `empty`     | warning  | Key is set to an empty value while the template shows an example value. |
| `extra`     | warning  | Key is in your env but not in the template (typo? stale?). |
| `duplicate` | warning  | Key is assigned more than once; the last one silently wins. |

A key with an empty value in the template (`DEBUG=`) is treated as optional-to-fill,
so leaving it empty is fine.

The parser understands comments, `export KEY=...`, single and double quotes,
escapes in double quotes, multi-line double-quoted values (PEM keys) and inline
`# comments` after unquoted values.

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | No errors (and no warnings with `--strict`). |
| 1 | Findings that fail the check. |
| 2 | Usage problem: env file or template not found. |

## In CI

Check the job's real environment against the committed template:

```yaml
- uses: UmutAlisoglu/envguard@v0.1.0
  with:
    args: --process-env --strict
```

Or call it directly:

```yaml
- run: pipx run --spec git+https://github.com/UmutAlisoglu/envguard envguard --process-env --format github
```

With `--process-env`, variables that aren't in the template are ignored, since a
process environment always contains plenty of unrelated ones.

## As a pre-commit hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: envguard
        name: envguard
        entry: envguard --strict
        language: system
        pass_filenames: false
        files: ^\.env
```

## Development

```console
python -m unittest discover -s tests
```

## License

MIT
