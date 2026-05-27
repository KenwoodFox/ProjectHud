import os
import time
from collections import defaultdict
from datetime import datetime

import requests
from requests import exceptions as request_exceptions

from app.services.scm_common import (
    empty_table_data,
    label_color,
    normalize_ci_run,
    parse_iso_datetime,
)


_UPDATE_STEPS = (
    "update_general_data",
    "update_pending_reviews",
    "update_commits",
    "update_ci_jobs",
)


class GiteaService:
    def __init__(self, base_url, token, organization, repos, username_mapping):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.organization = organization
        self.repos = [r.strip() for r in repos if r.strip()]
        self.username_mapping = username_mapping
        self.latest_data = empty_table_data()
        self.last_updated = None
        self._resolved_repos: list[str] | None = None

    def fetch_data(self):
        while True:
            for step_name in _UPDATE_STEPS:
                step = getattr(self, step_name)
                try:
                    step()
                except request_exceptions.RequestException as exc:
                    print(f"Gitea {step.__name__} failed: {exc}")
                except Exception as exc:
                    print(f"Gitea {step.__name__} failed (unexpected): {exc}")

            print("Updated gitea data.")
            self.last_updated = datetime.now()
            time.sleep(int(os.getenv("API_REFRESH_DURATION", 200)))

    def bootstrap(self):
        """Load data once before the background thread's first sleep."""
        self._repo_list()
        for step_name in _UPDATE_STEPS:
            try:
                getattr(self, step_name)()
            except (request_exceptions.RequestException, Exception) as exc:
                print(f"Gitea bootstrap {step_name} failed: {exc}")
        self.last_updated = datetime.now()

    def get_mapped_username(self, username: str) -> str:
        return self.username_mapping.get(username, username)

    def _headers(self) -> dict:
        return {"Authorization": f"token {self.token}"}

    def _api(self, path: str, params: dict | None = None):
        url = f"{self.base_url}/api/v1{path}"
        response = requests.get(
            url, headers=self._headers(), params=params or {}, timeout=30
        )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _as_list(data) -> list:
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("data") or data.get("items") or []
        return []

    def _repo_list(self) -> list[str]:
        if self._resolved_repos is not None:
            return self._resolved_repos
        if self.repos:
            self._resolved_repos = self.repos
            return self._resolved_repos

        for path in (
            f"/orgs/{self.organization}/repos",
            f"/users/{self.organization}/repos",
        ):
            try:
                data = self._as_list(self._api(path, {"limit": 100}))
                self._resolved_repos = [repo["full_name"] for repo in data]
                return self._resolved_repos
            except requests.HTTPError:
                continue

        self._resolved_repos = []
        return self._resolved_repos

    def _split_repo(self, repo_name: str) -> tuple[str, str]:
        if "/" in repo_name:
            owner, name = repo_name.split("/", 1)
            return owner, name
        return self.organization, repo_name

    def update_general_data(self):
        milestones_data = []
        issues_data = []
        pr_data = []

        for repo_name in self._repo_list():
            owner, name = self._split_repo(repo_name)
            short_repo = name

            for milestone in self._api(
                f"/repos/{owner}/{name}/milestones", {"state": "open", "limit": 50}
            ):
                closed = milestone.get("closed_issues", 0)
                open_count = milestone.get("open_issues", 0)
                total = closed + open_count
                milestones_data.append(
                    {
                        "repo_name": short_repo,
                        "name": milestone["title"],
                        "progress": round(closed / total * 100, 2) if total else 0,
                        "issues": total,
                    }
                )

            for issue in self._api(
                f"/repos/{owner}/{name}/issues", {"state": "open", "limit": 50}
            ):
                if issue.get("pull_request"):
                    continue
                user = issue.get("user") or {}
                issues_data.append(
                    {
                        "number": issue["number"],
                        "title": issue["title"],
                        "user": user.get("login", "unknown"),
                        "repo_name": short_repo,
                        "labels": [
                            {
                                "name": label["name"],
                                "color": label_color(label.get("color", "")),
                            }
                            for label in (issue.get("labels") or [])
                        ],
                        "assignees": [
                            a.get("login", "")
                            for a in (issue.get("assignees") or [])
                            if a.get("login")
                        ],
                        "updated_at": parse_iso_datetime(issue.get("updated_at")),
                    }
                )

            for pr in self._api(
                f"/repos/{owner}/{name}/pulls", {"state": "open", "limit": 50}
            ):
                user = pr.get("user") or {}
                pr_data.append(
                    {
                        "number": pr["number"],
                        "title": pr["title"],
                        "user": user.get("login", "unknown"),
                        "repo_name": short_repo,
                        "labels": [],
                        "assignees": [
                            a.get("login", "")
                            for a in (pr.get("assignees") or [])
                            if a.get("login")
                        ],
                        "updated_at": parse_iso_datetime(pr.get("updated_at")),
                        "is_draft": pr.get("draft", False),
                        "additions": pr.get("additions", 0) or 0,
                        "deletions": pr.get("deletions", 0) or 0,
                    }
                )

        pending = self.latest_data.get("pending_reviews", [])
        commits = self.latest_data.get("commits", [])
        ci_jobs = self.latest_data.get("ci_jobs", [])
        self.latest_data = {
            "milestones": milestones_data,
            "issues": issues_data,
            "pull_requests": pr_data,
            "issues_count": len(issues_data),
            "pull_requests_count": len(pr_data),
            "pending_reviews": pending,
            "commits": commits,
            "ci_jobs": ci_jobs,
        }

    def update_pending_reviews(self):
        pending_reviews = defaultdict(list)

        for repo_name in self._repo_list():
            owner, name = self._split_repo(repo_name)
            short_repo = name

            for pr in self._api(
                f"/repos/{owner}/{name}/pulls", {"state": "open", "limit": 50}
            ):
                if pr.get("draft"):
                    continue

                pr_number = pr["number"]
                for reviewer in (pr.get("requested_reviewers") or []):
                    login = reviewer.get("login")
                    if not login:
                        continue
                    mapped = self.get_mapped_username(login)
                    pending_reviews[mapped].append(
                        {
                            "pr_number": pr_number,
                            "repo_name": short_repo,
                            "is_review": True,
                        }
                    )

                for assignee in (pr.get("assignees") or []):
                    login = assignee.get("login")
                    if not login:
                        continue
                    mapped = self.get_mapped_username(login)
                    if any(
                        a["pr_number"] == pr_number
                        for a in pending_reviews[mapped]
                    ):
                        continue
                    pending_reviews[mapped].append(
                        {
                            "pr_number": pr_number,
                            "repo_name": short_repo,
                            "is_review": False,
                        }
                    )

        for reviewer in pending_reviews:
            pending_reviews[reviewer] = sorted(
                pending_reviews[reviewer], key=lambda x: not x["is_review"]
            )

        sorted_reviewers = sorted(
            pending_reviews.items(), key=lambda x: len(x[1]), reverse=True
        )

        self.latest_data["pending_reviews"] = [
            {"name": name, "assignments": assignments}
            for name, assignments in sorted_reviewers
        ]

    def update_commits(self):
        all_commits = []

        for repo_name in self._repo_list():
            owner, name = self._split_repo(repo_name)
            short_repo = name
            try:
                commits = self._api(
                    f"/repos/{owner}/{name}/commits", {"limit": 15}
                )
            except requests.HTTPError:
                continue

            for entry in commits:
                commit = entry.get("commit") or {}
                author = commit.get("author") or {}
                committed_at = parse_iso_datetime(author.get("date"))
                if not committed_at:
                    continue
                message = (commit.get("message") or "").split("\n")[0]
                all_commits.append(
                    {
                        "repo_name": short_repo,
                        "sha": (entry.get("sha") or "")[:7],
                        "message": message,
                        "author": author.get("name") or "unknown",
                        "committed_at": committed_at,
                    }
                )

        all_commits.sort(key=lambda c: c["committed_at"], reverse=True)
        self.latest_data["commits"] = all_commits[:40]

    def update_ci_jobs(self):
        all_jobs = []

        for repo_name in self._repo_list():
            owner, name = self._split_repo(repo_name)
            short_repo = name
            try:
                data = self._api(
                    f"/repos/{owner}/{name}/actions/runs",
                    {"page": 1, "limit": 15},
                )
            except requests.HTTPError:
                continue

            if isinstance(data, list):
                runs = data
            else:
                runs = data.get("workflow_runs") or data.get("runs") or []

            for run in runs:
                started = parse_iso_datetime(
                    run.get("run_started_at") or run.get("started_at")
                )
                ended = parse_iso_datetime(
                    run.get("updated_at") or run.get("completed_at")
                )
                job_name = (
                    run.get("display_title")
                    or run.get("title")
                    or f"#{run.get('run_number', '?')}"
                )
                job = normalize_ci_run(
                    repo_name=short_repo,
                    name=job_name,
                    status=run.get("status"),
                    conclusion=run.get("conclusion"),
                    started_at=started,
                    ended_at=ended,
                )
                if job:
                    all_jobs.append(job)

        all_jobs.sort(key=lambda j: j["started_at"], reverse=True)
        self.latest_data["ci_jobs"] = all_jobs[:40]
