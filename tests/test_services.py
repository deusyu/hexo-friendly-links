import copy
import unittest
from unittest.mock import Mock, patch

import requests

from src.services.avatar_optimizer import AvatarOptimizer
from src.services.link_checker import LinkChecker
from src.services.rss_service import RSSService


FEED = b'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>Fixture</title><link>https://example.org/</link>
<description>Fixture feed</description>
<item><title>Old</title><link>https://example.org/old</link>
<pubDate>Mon, 01 Jan 2024 00:00:00 GMT</pubDate></item>
<item><title>New</title><link>https://example.org/new</link>
<pubDate>Tue, 02 Jan 2024 00:00:00 GMT</pubDate></item>
</channel></rss>'''
EMPTY_FEED = b'<rss version="2.0"><channel><title>Empty</title></channel></rss>'


def response(status=200, body=FEED, content_type="application/rss+xml"):
    result = requests.Response()
    result.status_code = status
    result.url = "https://example.org/feed"
    result.headers["Content-Type"] = content_type
    result._content = body
    result._content_consumed = True
    return result


class LinkCheckerTests(unittest.TestCase):
    def test_http_status_is_checked(self):
        for status, expected in [(200, "active"), (204, "active"),
                                 (302, "404"), (404, "404"), (500, "404")]:
            with self.subTest(status=status), patch(
                "src.services.link_checker.requests.head", return_value=response(status)
            ) as head:
                self.assertEqual(LinkChecker().check_link("https://example.org/"), expected)
                self.assertTrue(head.call_args.kwargs["allow_redirects"])

    def test_head_not_supported_falls_back_to_streamed_get(self):
        for head_status in (403, 405, 501):
            for get_status, expected in [(200, "active"), (404, "404"), (500, "404")]:
                with self.subTest(head=head_status, get=get_status), patch(
                    "src.services.link_checker.requests.head", return_value=response(head_status)
                ), patch("src.services.link_checker.requests.get", return_value=response(get_status)) as get:
                    self.assertEqual(LinkChecker().check_link("https://example.org/"), expected)
                    self.assertTrue(get.call_args.kwargs["stream"])
                    self.assertTrue(get.call_args.kwargs["allow_redirects"])
                    self.assertEqual(get.call_args.kwargs["timeout"], 5)

    def test_network_failures_are_not_active(self):
        for error in (requests.Timeout("slow"), requests.ConnectionError("offline"),
                      requests.TooManyRedirects("loop")):
            with self.subTest(error=type(error).__name__), patch(
                "src.services.link_checker.requests.head", side_effect=error
            ):
                self.assertNotEqual(LinkChecker().check_link("https://example.org/"), "active")

    def test_empty_url_does_not_request(self):
        with patch("src.services.link_checker.requests.head") as head:
            self.assertEqual(LinkChecker().check_link(" "), "404")
            head.assert_not_called()


class RSSServiceTests(unittest.TestCase):
    previous = [{"title": "Last valid", "link": "https://example.org/last"}]

    def test_valid_feed_sorted_and_limited_with_timeout(self):
        with patch("src.services.rss_service.requests.get", return_value=response()) as get:
            items = RSSService().get_feed_content("https://example.org/feed", max_items=1)
        self.assertEqual([item["title"] for item in items], ["New"])
        self.assertEqual(items[0]["link"], "https://example.org/new")
        self.assertIn("published_parsed", items[0])
        self.assertTrue(get.call_args.kwargs["allow_redirects"])
        self.assertIsNotNone(get.call_args.kwargs["timeout"])

    def test_http_error_preserves_previous_and_reports_http_details(self):
        with patch("src.services.rss_service.requests.get", return_value=response(404, b"<html>Not found</html>", "text/html")), self.assertLogs("src.services.rss_service", "WARNING") as logs:
            items = RSSService().get_feed_content("https://example.org/feed", previous_items=self.previous)
        self.assertEqual(items, self.previous)
        self.assertIn("404", " ".join(logs.output))
        self.assertIn("text/html", " ".join(logs.output))
        self.assertIn("last valid", " ".join(logs.output).lower())

    def test_timeout_preserves_previous_and_reports_exception_type(self):
        with patch("src.services.rss_service.requests.get", side_effect=requests.Timeout("slow")), self.assertLogs("src.services.rss_service", "WARNING") as logs:
            items = RSSService().get_feed_content("https://example.org/feed", previous_items=self.previous)
        self.assertEqual(items, self.previous)
        self.assertIn("Timeout", " ".join(logs.output))

    def test_html_and_malformed_xml_do_not_erase_previous_entries(self):
        for body, content_type in [(b"<html><title>Not a feed</title></html>", "text/html"),
                                   (b"<rss version='2.0'><channel><item>", "application/rss+xml")]:
            with self.subTest(body=body), patch(
                "src.services.rss_service.requests.get", return_value=response(body=body, content_type=content_type)
            ), self.assertLogs("src.services.rss_service", "WARNING"):
                self.assertEqual(RSSService().get_feed_content("https://example.org/feed", previous_items=self.previous), self.previous)

    def test_valid_empty_feed_clears_previous_entries(self):
        with patch("src.services.rss_service.requests.get", return_value=response(body=EMPTY_FEED)):
            self.assertEqual(RSSService().get_feed_content("https://example.org/feed", previous_items=self.previous), [])

    def test_failure_without_cache_remains_empty(self):
        with patch("src.services.rss_service.requests.get", return_value=response(500)), self.assertLogs("src.services.rss_service", "WARNING"):
            self.assertEqual(RSSService().get_feed_content("https://example.org/feed"), [])

    def test_fallback_does_not_mutate_cached_items(self):
        previous = copy.deepcopy(self.previous)
        with patch("src.services.rss_service.requests.get", side_effect=requests.Timeout()), self.assertLogs("src.services.rss_service", "WARNING"):
            items = RSSService().get_feed_content("https://example.org/feed", previous_items=previous)
        items[0]["title"] = "Changed by caller"
        self.assertEqual(previous, self.previous)


class AvatarStabilityTests(unittest.TestCase):
    def test_timing_changes_do_not_change_published_avatar_data(self):
        optimizer = AvatarOptimizer()
        original = {"title": "中文 Avatar", "avatar": "https://example.org/avatar.png"}
        with patch.object(optimizer, "_test_avatar_url", side_effect=[
            {"status": "success", "load_time": 12},
            {"status": "success", "load_time": 917},
        ]):
            first = optimizer.optimize_avatar(copy.deepcopy(original))
            second = optimizer.optimize_avatar(copy.deepcopy(original))
        self.assertEqual(first, second)
        self.assertEqual(first["avatar_load_time"], 0)
        self.assertEqual(first["avatar"], original["avatar"])
        self.assertTrue(first["avatar_optimized"])
        self.assertIsInstance(first["avatar_fallbacks"], list)

    def test_unavailable_avatar_keeps_existing_fallback_behavior(self):
        optimizer = AvatarOptimizer()
        with patch.object(optimizer, "_test_avatar_url", return_value={"status": "http_error", "code": 404}):
            result = optimizer.optimize_avatar({"title": "Fixture", "avatar": "https://example.org/missing.png"})
        self.assertEqual(result["avatar"], result["avatar_fallbacks"][0])


if __name__ == "__main__":
    unittest.main()
