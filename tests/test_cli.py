import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from envguard.cli import EXIT_FINDINGS, EXIT_OK, EXIT_USAGE, main


class CliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        (self.dir / ".env.example").write_text("API_KEY=abc\nPORT=8000\n")

    def tearDown(self):
        self.tmp.cleanup()

    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(list(args))
        return code, out.getvalue(), err.getvalue()

    def write_env(self, text):
        path = self.dir / ".env"
        path.write_text(text)
        return str(path)

    def test_finds_template_next_to_env(self):
        code, out, _ = self.run_cli(self.write_env("API_KEY=x\nPORT=1\n"))
        self.assertEqual(code, EXIT_OK)
        self.assertIn("all keys present", out)

    def test_missing_key_exits_1(self):
        code, out, _ = self.run_cli(self.write_env("API_KEY=x\n"), "--no-color")
        self.assertEqual(code, EXIT_FINDINGS)
        self.assertIn("PORT is in the template but not set", out)

    def test_strict(self):
        env = self.write_env("API_KEY=x\nPORT=1\nOTHER=1\n")
        self.assertEqual(self.run_cli(env)[0], EXIT_OK)
        self.assertEqual(self.run_cli(env, "--strict")[0], EXIT_FINDINGS)

    def test_json_output(self):
        code, out, _ = self.run_cli(self.write_env("API_KEY=\n"), "--format", "json")
        data = json.loads(out)
        self.assertFalse(data["ok"])
        self.assertEqual({f["kind"] for f in data["findings"]}, {"missing", "empty"})
        self.assertEqual(code, EXIT_FINDINGS)

    def test_github_annotations(self):
        _, out, _ = self.run_cli(self.write_env("API_KEY=x\n"), "--format", "github")
        self.assertTrue(out.startswith("::error file="))

    def test_missing_files_exit_2(self):
        self.assertEqual(self.run_cli(str(self.dir / "nope.env"))[0], EXIT_USAGE)
        empty = tempfile.mkdtemp()
        env = Path(empty) / ".env"
        env.write_text("A=1\n")
        code, _, err = self.run_cli(str(env))
        self.assertEqual(code, EXIT_USAGE)
        self.assertIn("no template found", err)

    def test_process_env(self):
        template = str(self.dir / ".env.example")
        with mock.patch.dict(os.environ, {"API_KEY": "k", "PORT": "1"}):
            self.assertEqual(self.run_cli("--process-env", "-t", template)[0], EXIT_OK)
        with mock.patch.dict(os.environ, {"API_KEY": "k"}, clear=True):
            code, out, _ = self.run_cli("--process-env", "-t", template, "--strict", "--no-color")
        self.assertEqual(code, EXIT_FINDINGS)
        self.assertIn("PORT", out)
        self.assertNotIn("extra", out)


if __name__ == "__main__":
    unittest.main()
