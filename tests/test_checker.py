import unittest

from envguard.checker import compare
from envguard.parser import parse_text

TEMPLATE = "DATABASE_URL=postgres://localhost/app\nSECRET_KEY=change-me\nDEBUG=\n"


def kinds(report):
    return sorted((f.kind, f.key) for f in report.findings)


class CheckerTests(unittest.TestCase):
    def test_clean(self):
        env = parse_text("DATABASE_URL=x\nSECRET_KEY=y\nDEBUG=\n", ".env")
        report = compare(env, parse_text(TEMPLATE))
        self.assertEqual(report.findings, [])
        self.assertTrue(report.ok(strict=True))

    def test_missing_is_error(self):
        env = parse_text("DATABASE_URL=x\n", ".env")
        report = compare(env, parse_text(TEMPLATE))
        self.assertEqual(kinds(report), [("missing", "DEBUG"), ("missing", "SECRET_KEY")])
        self.assertFalse(report.ok())

    def test_warnings_only_fail_in_strict(self):
        env = parse_text("DATABASE_URL=x\nSECRET_KEY=\nDEBUG=\nEXTRA=1\nEXTRA=2\n", ".env")
        report = compare(env, parse_text(TEMPLATE))
        self.assertEqual(kinds(report), [("duplicate", "EXTRA"), ("empty", "SECRET_KEY"), ("extra", "EXTRA")])
        self.assertTrue(report.ok())
        self.assertFalse(report.ok(strict=True))

    def test_empty_template_value_allows_empty(self):
        env = parse_text("DATABASE_URL=x\nSECRET_KEY=y\nDEBUG=\n", ".env")
        self.assertEqual(compare(env, parse_text(TEMPLATE)).findings, [])

    def test_allow_empty_and_ignore(self):
        env = parse_text("DATABASE_URL=x\nSECRET_KEY=\nLOCAL=1\n", ".env")
        report = compare(
            env,
            parse_text(TEMPLATE),
            allow_empty=frozenset({"SECRET_KEY"}),
            ignore=frozenset({"DEBUG", "LOCAL"}),
        )
        self.assertEqual(report.findings, [])

    def test_parse_errors_are_errors(self):
        env = parse_text("DATABASE_URL=x\nSECRET_KEY=y\nDEBUG=\nbroken line\n", ".env")
        report = compare(env, parse_text(TEMPLATE))
        self.assertEqual(kinds(report), [("parse", "")])
        self.assertEqual(report.findings[0].line, 4)
        self.assertFalse(report.ok())


if __name__ == "__main__":
    unittest.main()
