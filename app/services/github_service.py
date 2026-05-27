import os
import time
import threading

from datetime import datetime

from github import Github

from collections import defaultdict

from app.services.scm_common import (
    empty_table_data,
    label_color,
    normalize_ci_run,
    to_local_naive,
)


class GitHubService:
    def __init__(self, token, repos, username_mapping):
        self.gh = Github(token)
        self.repos = repos
        self.username_mapping = username_mapping
        self.latest_data = empty_table_data()
        self.last_updated = None

    def fetch_data(self):
        while True:
            self.update_general_data()
            self.update_pending_reviews()
            self.update_ci_jobs()
            print("Updated github data.")
            self.last_updated = datetime.now()
            time.sleep(int(os.getenv("API_REFRESH_DURATION", 200)))

    def get_mapped_username(self, username):
        return self.username_mapping.get(username, username)

    def _short_repo_name(self, repo_name: str) -> str:
        return repo_name.split("/")[-1] if "/" in repo_name else repo_name

    def update_general_data(self):
        milestones_data = []
        issues_data = []
        pr_data = []

        for repo_name in self.repos:
            repo = self.gh.get_repo(repo_name)
            short_repo = self._short_repo_name(repo_name)

            milestones = repo.get_milestones(state="open")
            for milestone in milestones:
                closed = milestone.closed_issues
                open_count = milestone.open_issues
                total = closed + open_count
                milestones_data.append(
                    {
                        "repo_name": short_repo,
                        "name": milestone.title,
                        "progress": round(closed / total * 100, 2) if total else 0,
                        "issues": total,
                    }
                )

            issues = repo.get_issues(state="open")
            for issue in issues:
                if issue.pull_request:
                    continue
                issues_data.append(
                    {
                        "number": issue.number,
                        "title": issue.title,
                        "user": issue.user.login if issue.user else "unknown",
                        "repo_name": short_repo,
                        "labels": [
                            {
                                "name": label.name,
                                "color": label_color(label.color),
                            }
                            for label in issue.labels
                        ],
                        "assignees": [
                            a.login for a in issue.assignees if a.login
                        ],
                        "updated_at": issue.updated_at,
                    }
                )

            pull_requests = repo.get_pulls(state="open")
            for pr in pull_requests:
                pr_data.append(
                    {
                        "number": pr.number,
                        "title": pr.title,
                        "user": pr.user.login if pr.user else "unknown",
                        "repo_name": short_repo,
                        "labels": [
                            {
                                "name": label.name,
                                "color": label_color(label.color),
                            }
                            for label in pr.labels
                        ],
                        "assignees": [
                            a.login for a in pr.assignees if a.login
                        ],
                        "updated_at": pr.updated_at,
                        "is_draft": pr.draft,
                        "additions": getattr(pr, "additions", 0) or 0,
                        "deletions": getattr(pr, "deletions", 0) or 0,
                    }
                )

        pending = self.latest_data.get("pending_reviews", [])
        self.latest_data = {
            "milestones": milestones_data,
            "issues": issues_data,
            "pull_requests": pr_data,
            "issues_count": len(issues_data),
            "pull_requests_count": len(pr_data),
            "pending_reviews": pending,
            "commits": [],
            "ci_jobs": self.latest_data.get("ci_jobs", []),
            "projects": [],
        }

    def update_ci_jobs(self):
        all_jobs = []

        for repo_name in self.repos:
            repo = self.gh.get_repo(repo_name)
            short_repo = self._short_repo_name(repo_name)
            try:
                runs = list(repo.get_workflow_runs())[:15]
            except Exception:
                continue

            for run in runs:
                started = to_local_naive(run.run_started_at or run.created_at)
                ended = to_local_naive(run.updated_at)
                job = normalize_ci_run(
                    repo_name=short_repo,
                    name=run.name or f"#{run.run_number}",
                    status=run.status,
                    conclusion=run.conclusion,
                    started_at=started,
                    ended_at=ended,
                )
                if job:
                    all_jobs.append(job)

        all_jobs.sort(key=lambda j: j["started_at"], reverse=True)
        self.latest_data["ci_jobs"] = all_jobs[:40]

    def update_pending_reviews(self):
        pending_reviews = defaultdict(list)

        for repo_name in self.repos:
            repo = self.gh.get_repo(repo_name)
            short_repo = self._short_repo_name(repo_name)

            pull_requests = repo.get_pulls(state="open")
            for pr in pull_requests:
                pr_details = repo.get_pull(pr.number)

                if pr.draft:
                    continue

                requested_reviewers = pr_details.get_review_requests()
                for reviewer in requested_reviewers[0]:
                    mapped_name = self.get_mapped_username(reviewer.login)
                    pending_reviews[mapped_name].append(
                        {
                            "pr_number": pr.number,
                            "repo_name": short_repo,
                            "is_review": True,
                        }
                    )

                if pr.assignees:
                    for assignee in pr.assignees:
                        mapped_name = self.get_mapped_username(assignee.login)
                        if not any(
                            a["pr_number"] == pr.number
                            for a in pending_reviews[mapped_name]
                        ):
                            pending_reviews[mapped_name].append(
                                {
                                    "pr_number": pr.number,
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
