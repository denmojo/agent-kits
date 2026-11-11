"""Tests for agentbus: the plain-text thread store. Every test uses a temp AGENTS_ROOT."""
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import agentbus  # noqa: E402

WRITER = (
    "import sys; sys.path.insert(0, %r); import agentbus\n"
    "who = sys.argv[1]\n"
    "for i in range(50):\n"
    "    agentbus.append('stress', who, 'other', 'message %%d from %%s\\nsecond line' %% (i, who))\n"
) % HERE


class Bus(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = {"AGENTS_ROOT": self.tmp.name, "AGENTBUS_NOW": "2026-10-29 20:14"}
        self.saved = {k: os.environ.get(k) for k in self.env}
        os.environ.update(self.env)

    def tearDown(self):
        for k, v in self.saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        self.tmp.cleanup()

    def test_append_writes_exact_header(self):
        agentbus.append("deploy-notes", "claude", "reviewer", "Opening work.")
        path = os.path.join(self.tmp.name, "bus", "threads", "deploy-notes.md")
        with open(path, encoding="utf-8") as f:
            first = f.readline().rstrip("\n")
        self.assertEqual(
            first,
            "### 2026-10-29 20:14 · claude → reviewer · thread deploy-notes · open",
        )

    def test_round_trip(self):
        agentbus.append("t1", "a", "b", "first\n\nwith blank line")
        agentbus.append("t1", "b", "a", "second", status="answered")
        msgs = agentbus.read_thread("t1")
        self.assertEqual([m.index for m in msgs], [0, 1])
        self.assertEqual(msgs[0].body, "first\n\nwith blank line")
        self.assertEqual((msgs[1].sender, msgs[1].to, msgs[1].status), ("b", "a", "answered"))
        self.assertEqual((msgs[1].ts, msgs[1].thread), ("2026-10-29 20:14", "t1"))
        self.assertEqual(agentbus.threads(), ["t1"])

    def test_refuses_bad_thread(self):
        for bad in ("../x", "a b", "A", "", "-x", "foo\n"):
            with self.assertRaises(ValueError):
                agentbus.append(bad, "a", "b", "x")
            with self.assertRaises(ValueError):
                agentbus.read_thread(bad)

    def test_refuses_bad_agent_name(self):
        m = agentbus.append("t1", "a", "b", "x")
        for bad in ("b\n", "../b", "B"):
            with self.assertRaises(ValueError):
                agentbus.unread(bad)
            with self.assertRaises(ValueError):
                agentbus.mark_read(bad, [m])

    def test_refuses_bad_status(self):
        with self.assertRaises(ValueError):
            agentbus.append("t1", "a", "b", "x", status="bogus")

    def test_body_hash_line_escaped(self):
        agentbus.append("t1", "a", "b", "before\n### fake\n\\### already\nafter")
        agentbus.append("t1", "b", "a", "reply")
        msgs = agentbus.read_thread("t1")
        self.assertEqual(len(msgs), 2)
        self.assertEqual(msgs[0].body, "before\n### fake\n\\### already\nafter")

    def test_concurrent_appends(self):
        procs = [subprocess.Popen([sys.executable, "-c", WRITER, w]) for w in ("w1", "w2")]
        for p in procs:
            self.assertEqual(p.wait(), 0)
        msgs = agentbus.read_thread("stress")
        self.assertEqual(len(msgs), 100)
        for who in ("w1", "w2"):
            bodies = [m.body for m in msgs if m.sender == who]
            self.assertEqual(bodies, ["message %d from %s\nsecond line" % (i, who) for i in range(50)])

    def test_unread_and_cursor(self):
        agentbus.append("t1", "a", "b", "one")
        agentbus.append("t1", "a", "c", "not for b")
        agentbus.append("t2", "a", "b", "two")
        got = agentbus.unread("b")
        self.assertEqual([m.body for m in got], ["one", "two"])
        agentbus.mark_read("b", got)
        self.assertEqual(agentbus.unread("b"), [])
        self.assertTrue(os.path.exists(os.path.join(self.tmp.name, "b", "cursor.json")))
        agentbus.append("t1", "a", "b", "three")
        self.assertEqual([m.body for m in agentbus.unread("b")], ["three"])
        self.assertEqual([m.body for m in agentbus.unread("c")], ["not for b"])

    # ---- hash chain ----

    def _thread_file(self, t):
        return os.path.join(self.tmp.name, "bus", "threads", t + ".md")

    def test_chain_clean(self):
        for i in range(3):
            agentbus.append("c1", "a", "b", "msg %d" % i)
        v = agentbus.verify("c1")
        self.assertEqual((v["state"], v["count"]), ("ok", 3))

    def test_chain_detects_edited_body(self):
        agentbus.append("c1", "a", "b", "the build passed")
        agentbus.append("c1", "b", "a", "thanks", status="answered")
        p = self._thread_file("c1")
        s = open(p, encoding="utf-8").read().replace("the build passed", "the build failed")
        open(p, "w", encoding="utf-8").write(s)
        v = agentbus.verify("c1")
        self.assertEqual((v["state"], v["at"]), ("altered", 0))

    def test_chain_detects_edited_header(self):
        agentbus.append("c1", "a", "b", "x")
        p = self._thread_file("c1")
        s = open(p, encoding="utf-8").read().replace("· open", "· closed")
        open(p, "w", encoding="utf-8").write(s)
        self.assertEqual(agentbus.verify("c1")["state"], "altered")

    def test_chain_detects_deleted_message(self):
        agentbus.append("c1", "a", "b", "first")
        agentbus.append("c1", "a", "b", "second")
        agentbus.append("c1", "a", "b", "third")
        p = self._thread_file("c1")
        s = open(p, encoding="utf-8").read()
        start = s.index("### ", s.index("first"))
        end = s.index("### ", start + 4)
        open(p, "w", encoding="utf-8").write(s[:start] + s[end:])
        v = agentbus.verify("c1")
        self.assertEqual((v["state"], v["at"]), ("altered", 1))

    def test_chain_detects_truncation(self):
        agentbus.append("c1", "a", "b", "first")
        agentbus.append("c1", "a", "b", "second")
        p = self._thread_file("c1")
        s = open(p, encoding="utf-8").read()
        open(p, "w", encoding="utf-8").write(s[:s.index("### ", 4)])
        v = agentbus.verify("c1")
        self.assertEqual((v["state"], v["at"]), ("missing", 1))

    def test_chain_detects_direct_append(self):
        agentbus.append("c1", "a", "b", "first")
        with open(self._thread_file("c1"), "a", encoding="utf-8") as f:
            f.write("### 2026-10-29 20:15 · b → a · thread c1 · answered\nforged\n\n")
        v = agentbus.verify("c1")
        self.assertEqual((v["state"], v["at"]), ("unsealed", 1))

    def test_chain_detects_rewritten_chain_entry(self):
        agentbus.append("c1", "a", "b", "first")
        agentbus.append("c1", "a", "b", "second")
        cp = os.path.join(self.tmp.name, "bus", "chain", "c1.jsonl")
        lines = open(cp, encoding="utf-8").read().splitlines()
        lines[0] = lines[0].replace(lines[0][-10:-2], "deadbeef")
        open(cp, "w", encoding="utf-8").write("\n".join(lines) + "\n")
        self.assertNotEqual(agentbus.verify("c1")["state"], "ok")

    def test_seal_existing_is_one_shot(self):
        os.makedirs(os.path.dirname(self._thread_file("old")), exist_ok=True)
        with open(self._thread_file("old"), "w", encoding="utf-8") as f:
            f.write("### 2026-10-29 20:14 · a → b · thread old · open\nlegacy\n\n")
        self.assertEqual(agentbus.verify("old")["state"], "unsealed")
        self.assertEqual(agentbus.seal_existing(), ["old"])
        self.assertEqual(agentbus.verify("old")["state"], "ok")
        with open(self._thread_file("late"), "w", encoding="utf-8") as f:
            f.write("### 2026-10-29 20:14 · a → b · thread late · open\nsneaky\n\n")
        with self.assertRaises(RuntimeError):
            agentbus.seal_existing()
        self.assertEqual(agentbus.verify("late")["state"], "unsealed")

    def test_chain_continues_after_seal(self):
        os.makedirs(os.path.dirname(self._thread_file("old")), exist_ok=True)
        with open(self._thread_file("old"), "w", encoding="utf-8") as f:
            f.write("### 2026-10-29 20:14 · a → b · thread old · open\nlegacy\n\n")
        agentbus.seal_existing()
        agentbus.append("old", "b", "a", "new reply", status="answered")
        self.assertEqual(agentbus.verify("old"), {"state": "ok", "count": 2, "at": None, "detail": ""})

    # ---- done receipts ----

    def _repo(self):
        repo = os.path.join(self.tmp.name, "repo")
        os.makedirs(repo)
        git = ["git", "-C", repo, "-c", "user.name=t", "-c", "user.email=t@t", "-c", "core.hooksPath=/dev/null"]
        subprocess.run(git[:3] + ["init", "-q"], check=True)
        for name in ("a.py", "b.py"):
            with open(os.path.join(repo, name), "w") as f:
                f.write(name)
        subprocess.run(git + ["add", "a.py"], check=True)
        subprocess.run(git + ["commit", "-q", "-m", "one"], check=True)
        first = subprocess.run(git[:3] + ["rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        subprocess.run(git + ["add", "b.py"], check=True)
        subprocess.run(git + ["commit", "-q", "-m", "two"], check=True)
        return repo, first

    def test_receipt_good(self):
        repo, first = self._repo()
        trailer = agentbus.make_receipt(repo, first[:7], ["a.py"])
        self.assertIn("Receipt: %s in " % first, trailer)
        agentbus.append("r1", "a", "b", "done\n\n" + trailer, status="closed")
        r = agentbus.check_receipt(agentbus.read_thread("r1")[0].body)
        self.assertEqual((r["ok"], r["sha"], r["files"]), (True, first, ["a.py"]))

    def test_receipt_missing_commit(self):
        repo, _ = self._repo()
        with self.assertRaises(ValueError):
            agentbus.make_receipt(repo, "deadbeef", [])
        body = "done\n\nReceipt: %s in %s" % ("d" * 40, repo)
        r = agentbus.check_receipt(body)
        self.assertFalse(r["ok"])
        self.assertIn("commit", r["problem"])

    def test_receipt_file_not_in_commit(self):
        repo, first = self._repo()
        with self.assertRaises(ValueError):
            agentbus.make_receipt(repo, first, ["b.py"])
        body = "done\n\nReceipt: %s in %s\nFiles: a.py, b.py" % (first, repo)
        r = agentbus.check_receipt(body)
        self.assertFalse(r["ok"])
        self.assertIn("b.py", r["problem"])

    def test_receipt_absent(self):
        self.assertIsNone(agentbus.check_receipt("just a message"))

    def test_cli_say_with_receipt(self):
        repo, first = self._repo()
        import json as _j
        with open(os.path.join(self.tmp.name, "registry.json"), "w") as f:
            _j.dump({"a": {}, "b": {}}, f)
        rc = agentbus.cli_say("a", ["--to", "b", "--thread", "r2", "--status", "closed",
                                    "--repo", repo, "--sha", first, "--files", "a.py", "shipped"], "agent-say")
        self.assertEqual(rc, 0)
        r = agentbus.check_receipt(agentbus.read_thread("r2")[0].body)
        self.assertTrue(r["ok"])
        rc = agentbus.cli_say("a", ["--to", "b", "--thread", "r2", "--repo", repo, "--sha", "0" * 40, "x"], "agent-say")
        self.assertEqual(rc, 1)
        self.assertEqual(len(agentbus.read_thread("r2")), 1)


if __name__ == "__main__":
    unittest.main()
