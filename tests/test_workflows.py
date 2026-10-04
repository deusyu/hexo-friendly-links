import contextlib
import importlib.util
import io
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import yaml


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("label_commenter", ROOT / ".github/scripts/label_commenter.py")
label_commenter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(label_commenter)


def workflow(name):
    # BaseLoader also preserves the Actions `on` key instead of YAML 1.1 bools.
    return yaml.load((ROOT / f".github/workflows/{name}.yml").read_text(), Loader=yaml.BaseLoader)


class LabelCommenterTests(unittest.TestCase):
    config = yaml.safe_load((ROOT / ".github/configs/label-commenter-config.yml").read_text())

    def event(self, name="active", action="labeled"):
        return {"action": action, "label": {"name": name}, "issue": {"number": 42}}

    def test_all_existing_templates_are_selected_without_policy_changes(self):
        self.assertEqual([label["name"] for label in self.config["labels"]],
                         ["active", "checklist", "suspend", "404"])
        for label in self.config["labels"]:
            with self.subTest(label=label["name"]):
                result = label_commenter.comment_for_event(self.event(label["name"]), self.config)
                self.assertEqual(result, {"issue_number": 42, "body": label["labeled"]["issue"]["body"]})

    def test_unlabeled_unknown_and_non_issue_events_do_nothing(self):
        for event in [self.event(action="unlabeled"), self.event("other"),
                      self.event(action="edited"), {"action": "labeled", "label": {"name": "active"}}]:
            with self.subTest(event=event):
                self.assertIsNone(label_commenter.comment_for_event(event, self.config))

    def test_dry_run_does_not_require_token_or_make_api_request(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "event.json"
            path.write_text(json.dumps(self.event()))
            output = io.StringIO()
            with patch.dict(os.environ, {"GITHUB_EVENT_PATH": str(path)}, clear=True), patch.object(label_commenter, "urlopen") as api, contextlib.redirect_stdout(output):
                label_commenter.main(["--dry-run"])
            api.assert_not_called()
            self.assertEqual(json.loads(output.getvalue())["issue_number"], 42)

    def test_post_transport_is_scoped_to_one_issue_comment(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "event.json"
            path.write_text(json.dumps(self.event()))
            env = {"GITHUB_EVENT_PATH": str(path), "GITHUB_REPOSITORY": "fixture/repo", "GITHUB_TOKEN": "fake-test-token"}
            response = Mock(status=201)
            transport = Mock()
            transport.__enter__ = Mock(return_value=response)
            transport.__exit__ = Mock(return_value=False)
            with patch.dict(os.environ, env, clear=True), patch.object(label_commenter, "urlopen", return_value=transport) as api, contextlib.redirect_stdout(io.StringIO()):
                label_commenter.main([])
            api.assert_called_once()
            request = api.call_args.args[0]
            self.assertEqual(request.method, "POST")
            self.assertEqual(request.full_url, "https://api.github.com/repos/fixture/repo/issues/42/comments")
            self.assertEqual(json.loads(request.data), {"body": self.config["labels"][0]["labeled"]["issue"]["body"]})
            self.assertEqual(api.call_args.kwargs["timeout"], 10)


class WorkflowTests(unittest.TestCase):
    def test_actions_are_fixed_to_full_commit_sha_and_runner_supported(self):
        for path in (ROOT / ".github/workflows").glob("*.yml"):
            data = yaml.load(path.read_text(), Loader=yaml.BaseLoader)
            for job in data["jobs"].values():
                self.assertEqual(job["runs-on"], "ubuntu-24.04")
                for step in job["steps"]:
                    if "uses" in step:
                        self.assertRegex(step["uses"], r"^[\w-]+/[\w-]+@[0-9a-f]{40}$")
                    if "run" in step:
                        self.assertNotIn("::set-output", step["run"])
                        if "${{" not in step["run"]:
                            subprocess.run(["bash", "-n"], input=step["run"], text=True, check=True)

    def test_permissions_remain_scoped_to_each_existing_job(self):
        self.assertEqual(workflow("label-commenter")["permissions"], {"contents": "read", "issues": "write"})
        self.assertEqual(workflow("generator")["permissions"], {"contents": "write", "issues": "read"})
        self.assertEqual(workflow("sync_json")["permissions"], {"contents": "read"})
        self.assertEqual(workflow("tests")["permissions"], {"contents": "read"})
        self.assertEqual(workflow("label-commenter")["on"], {"issues": {"types": ["labeled", "unlabeled"]}})

    def test_sync_real_scripts_commit_push_and_no_change(self):
        scripts = {s["name"]: s["run"] for s in workflow("sync_json")["jobs"]["sync"]["steps"] if "run" in s}
        scripts = {name: script.replace("${{ secrets.USER_NAME }}", "deusyu").replace("${{ secrets.PRIVATE_PATH }}", "links") for name, script in scripts.items()}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            env = os.environ.copy()
            for key in list(env):
                if key.startswith(("GIT_AUTHOR_", "GIT_COMMITTER_")):
                    env.pop(key)
            env.update(GIT_CONFIG_GLOBAL=str(root / "gitconfig"), GIT_CONFIG_NOSYSTEM="1", GITHUB_OUTPUT=str(root / "outputs"))
            def run(args, cwd=root):
                return subprocess.run(args, cwd=cwd, env=env, check=True, capture_output=True, text=True).stdout
            def shell(name):
                return run(["bash", "-e", "-c", scripts[name]])
            run(["git", "init", "--bare", "--initial-branch=master", "remote.git"])
            run(["git", "init", "--initial-branch=master", "private-repo"])
            private = root / "private-repo"
            (private / "links").mkdir()
            (private / "links/friendly.json").write_text("[]\n")
            source = root / "public-repo/json/all.json"
            source.parent.mkdir(parents=True)
            source.write_text('[{"title":"Fixture"}]\n')
            shell("Setup Git")
            run(["git", "add", "."], private)
            run(["git", "commit", "-m", "Initial"], private)
            run(["git", "remote", "add", "origin", str(root / "remote.git")], private)
            run(["git", "push", "-u", "origin", "master"], private)
            shell("Check if JSON file has changed")
            self.assertEqual((root / "outputs").read_text(), "sync_needed=true\n")
            shell("Copy JSON files to private repository")
            shell("Commit and Push changes to private repository")
            self.assertEqual(run(["git", "log", "-1", "--format=%ae%n%ce"], private).splitlines(),
                             ["42929363+deusyu@users.noreply.github.com"] * 2)
            self.assertEqual(run(["git", "--git-dir", str(root / "remote.git"), "show", "master:links/friendly.json"]), source.read_text())
            (root / "outputs").write_text("")
            shell("Check if JSON file has changed")
            self.assertEqual((root / "outputs").read_text(), "sync_needed=false\n")

    def test_generator_publish_skips_identical_data_and_only_stages_json(self):
        script = next(s["run"] for s in workflow("generator")["jobs"]["build"]["steps"] if s["name"] == "Commit & Push")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            env = os.environ.copy()
            env.update(GIT_CONFIG_GLOBAL=str(root / "gitconfig"), GIT_CONFIG_NOSYSTEM="1")
            for key in list(env):
                if key.startswith(("GIT_AUTHOR_", "GIT_COMMITTER_")):
                    env.pop(key)
            def run(args, cwd=root, check=True):
                return subprocess.run(args, cwd=cwd, env=env, check=check, capture_output=True, text=True)
            run(["git", "init", "--bare", "remote.git"])
            run(["git", "init", "--initial-branch=main", "working"])
            working = root / "working"
            run(["git", "config", "user.name", "Fixture"], working)
            run(["git", "config", "user.email", "fixture@users.noreply.github.com"], working)
            (working / "json").mkdir()
            (working / "json/all.json").write_text("[]\n")
            run(["git", "add", "json"], working)
            run(["git", "commit", "-m", "Initial"], working)
            run(["git", "branch", "output"], working)
            run(["git", "remote", "add", "origin", str(root / "remote.git")], working)
            run(["git", "push", "origin", "main", "output"], working)
            run(["git", "clone", "--branch", "output", str(root / "remote.git"), "previous-output"], working)
            initial = run(["git", "rev-parse", "HEAD"], working).stdout
            result = run(["bash", "-e", "-c", script], working)
            self.assertIn("unchanged", result.stdout)
            self.assertEqual(run(["git", "rev-parse", "HEAD"], working).stdout, initial)
            (working / "json/all.json").write_text('[{"title":"Changed"}]\n')
            (working / "unrelated.txt").write_text("Must not publish")
            run(["bash", "-e", "-c", script], working)
            self.assertEqual(run(["git", "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"], working).stdout.strip(), "json/all.json")
            published = run(["git", "--git-dir", str(root / "remote.git"), "rev-parse", "output"]).stdout
            self.assertEqual(published, run(["git", "rev-parse", "HEAD"], working).stdout)
            # A newer remote output must not be overwritten by an old cache.
            (working / "json/all.json").write_text('[{"title":"Another change"}]\n')
            result = run(["bash", "-e", "-c", script], working, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(run(["git", "--git-dir", str(root / "remote.git"), "rev-parse", "output"]).stdout, published)


if __name__ == "__main__":
    unittest.main()
