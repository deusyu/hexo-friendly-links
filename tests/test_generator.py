import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests

from src.main import FriendlyLinksGenerator
from src.models.config import Config, GroupConfig, IssuesConfig
from test_services import response


def config(keep_raw=False):
    return Config(issues=IssuesConfig(repo="fixture/repo", keep_raw=keep_raw, groups=[
        GroupConfig(name="active", labels=["active"]),
        GroupConfig(name="checklist", state="open", labels=["checklist"]),
    ]))


def issue(number, state="open", labels=("active",), url="https://example.org/"):
    data = {"title": f"Fixture {number}", "url": url}
    return {"number": number, "state": state, "labels": [{"name": name} for name in labels],
            "body": "```json\n" + json.dumps(data) + "\n```"}


class GeneratorTests(unittest.TestCase):
    def generator(self, issues, **kwargs):
        with patch("src.main.load_config", return_value=config()):
            generator = FriendlyLinksGenerator(**kwargs)
        generator.github_service.get_issues = Mock(return_value=copy.deepcopy(issues))
        return generator

    def test_404_and_500_are_not_marked_active_by_main(self):
        for status in (404, 500):
            with self.subTest(status=status), patch("requests.head", return_value=response(status)):
                output = self.generator([issue(1)]).process_issues()
            self.assertEqual(output["all"][0]["status"], "404")
            # Health never changes the existing label-based review/display rule.
            self.assertEqual(output["active"], output["all"])

    def test_transient_error_retains_existing_status_schema(self):
        with patch("requests.head", side_effect=requests.Timeout("slow")):
            output = self.generator([issue(1)]).process_issues()
        self.assertEqual(output["all"][0]["status"], "404")

    def test_all_and_configured_groups_keep_state_and_label_rules(self):
        issues = [issue(1), issue(2, state="closed"),
                  issue(3, labels=("checklist",)), issue(4, state="closed", labels=("checklist",))]
        generator = self.generator(issues)
        generator.link_checker.check_link = Mock(return_value="active")
        with patch("requests.head", return_value=response()):
            output = generator.process_issues()
        self.assertEqual([i["title"] for i in output["all"]], [f"Fixture {i}" for i in range(1, 5)])
        self.assertEqual([i["title"] for i in output["active"]], ["Fixture 1", "Fixture 2"])
        self.assertEqual([i["title"] for i in output["checklist"]], ["Fixture 3"])
        self.assertTrue(all("raw" not in i for i in output["all"]))

    def write_cache(self, directory, entries, repo="fixture/repo"):
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "all.json").write_text(json.dumps({
            "config": {"issues": {"repo": repo}},
            "content": [{"url": "https://example.org/", "url-feed": "https://example.org/feed", "rss": entries}],
        }))

    def feed_issue(self):
        result = issue(1)
        data = {"title": "Fixture 1", "url": "https://example.org/", "url-feed": "https://example.org/feed"}
        result["body"] = "```json\n" + json.dumps(data) + "\n```"
        return result

    def test_rss_failure_keeps_published_last_valid_entries(self):
        previous = [{"title": "Last valid", "link": "https://example.org/last"}]
        with tempfile.TemporaryDirectory() as directory:
            self.write_cache(directory, previous)
            generator = self.generator([self.feed_issue()], previous_output_dir=directory)
            with patch("requests.head", return_value=response()), patch("requests.get", return_value=response(404)), self.assertLogs("src.services.rss_service", "WARNING"):
                output = generator.process_issues()
        self.assertEqual(output["all"][0]["rss"], previous)

    def test_empty_output_cache_does_not_erase_valid_seed(self):
        previous = [{"title": "Seed", "link": "https://example.org/seed"}]
        with tempfile.TemporaryDirectory() as directory:
            seed, published = Path(directory) / "json", Path(directory) / "published"
            self.write_cache(seed, previous)
            self.write_cache(published, [])
            with patch("src.main.Path.cwd", return_value=Path(directory)):
                generator = self.generator([self.feed_issue()], previous_output_dir=str(published))
            with patch("requests.head", return_value=response()), patch("requests.get", return_value=response(404)), self.assertLogs("src.services.rss_service", "WARNING"):
                output = generator.process_issues()
        self.assertEqual(output["all"][0]["rss"], previous)

    def test_cache_from_other_repository_is_not_reused(self):
        with tempfile.TemporaryDirectory() as directory:
            self.write_cache(directory, [{"title": "Wrong repo"}], repo="other/repo")
            generator = self.generator([self.feed_issue()], previous_output_dir=directory)
            with patch("requests.head", return_value=response()), patch("requests.get", return_value=response(404)), self.assertLogs("src.services.rss_service", "WARNING"):
                output = generator.process_issues()
        self.assertEqual(output["all"][0]["rss"], [])

    def test_same_feed_for_different_site_is_not_reused(self):
        with tempfile.TemporaryDirectory() as directory:
            self.write_cache(directory, [{"title": "Other site"}])
            data = self.feed_issue()
            data["body"] = data["body"].replace('"url": "https://example.org/"', '"url": "https://different.org/"')
            generator = self.generator([data], previous_output_dir=directory)
            with patch("requests.head", return_value=response()), patch("requests.get", return_value=response(404)), self.assertLogs("src.services.rss_service", "WARNING"):
                output = generator.process_issues()
        self.assertEqual(output["all"][0]["rss"], [])

    def test_corrupt_cache_does_not_abort_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "all.json").write_text("not JSON")
            with self.assertLogs("src.main", "WARNING"):
                generator = self.generator([], previous_output_dir=directory)
            self.assertEqual(generator.process_issues(), {"all": [], "active": [], "checklist": []})

    def test_malformed_issue_and_empty_input_are_supported(self):
        self.assertEqual(self.generator([]).process_issues()["all"], [])
        invalid = issue(1)
        invalid["body"] = "```json\ninvalid\n```"
        with self.assertLogs("src.parsers.json_parser", "ERROR"):
            output = self.generator([invalid]).process_issues()
        self.assertEqual(len(output["all"]), 1)
        self.assertNotIn("raw", output["all"][0])

    def test_saving_unchanged_output_produces_identical_json_bytes(self):
        generator = self.generator([])
        output = {"all": [{"title": "中文", "status": "active", "rss": []}]}
        with tempfile.TemporaryDirectory() as directory:
            generator.save_results(output, directory)
            path = Path(directory) / "all.json"
            first = path.read_bytes()
            generator.save_results(output, directory)
            self.assertEqual(path.read_bytes(), first)
            self.assertEqual(json.loads(first)["content"], output["all"])

    def test_same_inputs_keep_legacy_parsing_and_grouping(self):
        """Compare the documented original generator with the current pipeline."""
        raw = [issue(1), issue(2, state="closed"), issue(3, labels=("checklist",))]
        raw[2]["body"] = "### 博客名称\n\n中文表格\n\n### 博客地址\n\nhttps://example.org/\n\n### 博客图标\n\n_No response_"
        source = (Path(__file__).resolve().parents[1] / "generator/main.py").read_text()
        namespace = {}
        # Load definitions without running the legacy script's publishing tail.
        exec(source.split("\noutput_dict = generate_json_based_on_issues()")[0], namespace)
        namespace["cfg"] = config().model_dump()
        labels_response = Mock(status_code=200)
        labels_response.json.return_value = []
        issues_response = Mock(status_code=200)
        issues_response.json.return_value = copy.deepcopy(raw)
        with patch("requests.get", side_effect=[labels_response, issues_response]), patch("requests.head", return_value=response()):
            legacy = namespace["generate_json_based_on_issues"]()
        generator = self.generator(raw)
        generator.avatar_optimizer.optimize_avatar = Mock(side_effect=lambda data: data)
        with patch("requests.head", return_value=response()):
            current = generator.process_issues()
        self.assertEqual(current, legacy)


if __name__ == "__main__":
    unittest.main()
