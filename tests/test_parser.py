import unittest

from envguard.parser import parse_text


class ParserTests(unittest.TestCase):
    def test_basic_pairs_comments_and_export(self):
        env = parse_text("# comment\n\nA=1\nexport B=two\nC = spaced \n")
        self.assertEqual(env.as_dict(), {"A": "1", "B": "two", "C": "spaced"})
        self.assertEqual(env.errors, [])

    def test_inline_comment_only_on_unquoted_values(self):
        env = parse_text('A=val # note\nB="val # kept"\nC=pass#word\n')
        self.assertEqual(env.as_dict(), {"A": "val", "B": "val # kept", "C": "pass#word"})

    def test_quotes_and_escapes(self):
        env = parse_text("A='single $raw \\n'\nB=\"line\\nbreak\"\nC=\"q\\\"uote\"\n")
        self.assertEqual(env.as_dict()["A"], "single $raw \\n")
        self.assertEqual(env.as_dict()["B"], "line\nbreak")
        self.assertEqual(env.as_dict()["C"], 'q"uote')

    def test_multiline_double_quoted(self):
        env = parse_text('KEY="-----BEGIN-----\nabc\n-----END-----"\nNEXT=1\n')
        self.assertEqual(env.as_dict()["KEY"], "-----BEGIN-----\nabc\n-----END-----")
        self.assertEqual(env.entries[1].line, 4)

    def test_errors(self):
        env = parse_text("NOEQUALS\n1BAD=x\nOPEN='never closed\nOK=1\n")
        self.assertEqual([e.line for e in env.errors], [1, 2, 3])
        self.assertEqual(env.as_dict(), {"OK": "1"})

    def test_duplicates_last_wins(self):
        env = parse_text("A=1\nB=2\nA=3\n")
        self.assertEqual(env.as_dict()["A"], "3")
        self.assertEqual(env.duplicates(), {"A": [1, 3]})
        self.assertEqual(env.keys, ["A", "B"])

    def test_empty_values(self):
        env = parse_text('A=\nB=""\nC=\'\'\n')
        self.assertEqual(env.as_dict(), {"A": "", "B": "", "C": ""})


if __name__ == "__main__":
    unittest.main()
