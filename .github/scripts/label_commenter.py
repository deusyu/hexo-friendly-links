"""Post only the existing configured issue comments for label events."""

import argparse
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

import yaml


def comment_for_event(event, config):
    """Select a template without modifying issue state or labels."""
    action = event.get("action")
    if action not in ("labeled", "unlabeled") or "issue" not in event:
        return None
    label_name = event.get("label", {}).get("name")
    for label in config.get("labels", []):
        if label.get("name") == label_name:
            body = label.get(action, {}).get("issue", {}).get("body")
            if body:
                return {"issue_number": event["issue"]["number"], "body": body}
    return None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
    config = yaml.safe_load(Path(".github/configs/label-commenter-config.yml").read_text(encoding="utf-8"))
    comment = comment_for_event(event, config)
    if comment is None:
        print("No comment configured for this label event.")
        return
    if args.dry_run:
        print(json.dumps(comment, ensure_ascii=False))
        return

    repository = os.environ["GITHUB_REPOSITORY"]
    api_url = os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")
    request = Request(
        f"{api_url}/repos/{repository}/issues/{comment['issue_number']}/comments",
        data=json.dumps({"body": comment["body"]}).encode("utf-8"),
        headers={"Accept": "application/vnd.github+json", "Content-Type": "application/json",
                 "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
                 "X-GitHub-Api-Version": "2022-11-28"},
        method="POST",
    )
    with urlopen(request, timeout=10) as response:
        if response.status != 201:
            raise RuntimeError(f"Issue comment API returned HTTP {response.status}")
    print("Configured issue comment posted.")


if __name__ == "__main__":
    main()
