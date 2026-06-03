import os
import time
from datetime import datetime

import requests
from requests import exceptions as request_exceptions

from app.services.scm_common import parse_iso_datetime

_UPDATE_STEPS = (
    "update_recent_parts",
    "update_purchase_orders",
    "update_sales_orders",
    "update_build_orders",
)

_LIST_LIMIT = 30


def empty_inventree_data() -> dict:
    return {
        "recent_parts": [],
        "purchase_orders": [],
        "sales_orders": [],
        "build_orders": [],
        "recent_parts_count": 0,
        "purchase_orders_count": 0,
        "sales_orders_count": 0,
        "build_orders_count": 0,
    }


def normalize_inventree_base_url(url: str) -> str:
    base = (url or "").strip().rstrip("/")
    for suffix in ("/web/logged-in", "/web"):
        if base.endswith(suffix):
            base = base[: -len(suffix)].rstrip("/")
    return base


class InvenTreeService:
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = normalize_inventree_base_url(base_url)
        self.username = username
        self.password = password
        self._token: str | None = None
        self.latest_data = empty_inventree_data()
        self.last_updated = None

    def fetch_data(self):
        while True:
            for step_name in _UPDATE_STEPS:
                step = getattr(self, step_name)
                try:
                    step()
                except request_exceptions.RequestException as exc:
                    print(f"InvenTree {step.__name__} failed: {exc}")
                except Exception as exc:
                    print(f"InvenTree {step.__name__} failed (unexpected): {exc}")

            print("Updated InvenTree data.")
            self.last_updated = datetime.now()
            time.sleep(int(os.getenv("API_REFRESH_DURATION", 200)))

    def bootstrap(self):
        for step_name in _UPDATE_STEPS:
            try:
                getattr(self, step_name)()
            except (request_exceptions.RequestException, Exception) as exc:
                print(f"InvenTree bootstrap {step_name} failed: {exc}")
        self.last_updated = datetime.now()

    def _ensure_token(self):
        if self._token:
            return
        for path in ("/api/user/token/", "/api/user/me/token/"):
            try:
                response = requests.get(
                    f"{self.base_url}{path}",
                    auth=(self.username, self.password),
                    timeout=30,
                )
                if response.status_code != 200:
                    continue
                data = response.json()
                token = data.get("token") or data.get("key")
                if token:
                    self._token = token
                    return
            except request_exceptions.RequestException:
                continue

    def _auth_headers(self) -> dict:
        self._ensure_token()
        if self._token:
            return {"Authorization": f"Token {self._token}"}
        return {}

    def _api(self, path: str, params: dict | None = None) -> list:
        url = f"{self.base_url}{path}"
        auth = None if self._token else (self.username, self.password)
        response = requests.get(
            url,
            headers=self._auth_headers(),
            auth=auth,
            params=params or {},
            timeout=30,
        )
        if response.status_code == 401 and self._token:
            self._token = None
            self._ensure_token()
            response = requests.get(
                url,
                headers=self._auth_headers(),
                auth=None if self._token else (self.username, self.password),
                params=params or {},
                timeout=30,
            )
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list):
            return data
        return data.get("results") or []

    @staticmethod
    def _detail_name(detail: dict | None, fallback: str = "") -> str:
        if not detail:
            return fallback
        return detail.get("name") or detail.get("title") or fallback

    @staticmethod
    def _format_date(value: str | None) -> str | None:
        if not value:
            return None
        dt = parse_iso_datetime(value if "T" in value else f"{value}T00:00:00")
        if dt:
            return dt.strftime("%b %d")
        return value

    def update_recent_parts(self):
        rows = self._api(
            "/api/part/",
            {
                "ordering": "-creation_date",
                "limit": _LIST_LIMIT,
            },
        )
        parts = []
        for row in rows:
            parts.append(
                {
                    "name": row.get("name") or "—",
                    "ipn": row.get("IPN") or row.get("ipn") or "",
                    "description": (row.get("description") or "")[:120],
                    "category": self._detail_name(row.get("category_detail")),
                    "created_at": parse_iso_datetime(row.get("creation_date")),
                }
            )
        self.latest_data["recent_parts"] = parts
        self.latest_data["recent_parts_count"] = len(parts)

    def update_purchase_orders(self):
        rows = self._api(
            "/api/order/po/",
            {
                "outstanding": True,
                "ordering": "-creation_date",
                "limit": _LIST_LIMIT,
                "supplier_detail": True,
            },
        )
        orders = []
        for row in rows:
            orders.append(
                {
                    "reference": row.get("reference") or "—",
                    "supplier": self._detail_name(
                        row.get("supplier_detail"), "Unknown supplier"
                    ),
                    "description": (row.get("description") or "")[:100],
                    "status": row.get("status_text") or str(row.get("status") or ""),
                    "target_date": self._format_date(row.get("target_date")),
                    "overdue": bool(row.get("overdue")),
                    "created_at": parse_iso_datetime(row.get("creation_date")),
                }
            )
        self.latest_data["purchase_orders"] = orders
        self.latest_data["purchase_orders_count"] = len(orders)

    def update_sales_orders(self):
        rows = self._api(
            "/api/order/so/",
            {
                "outstanding": True,
                "ordering": "-creation_date",
                "limit": _LIST_LIMIT,
                "customer_detail": True,
            },
        )
        orders = []
        for row in rows:
            orders.append(
                {
                    "reference": row.get("reference") or "—",
                    "customer": self._detail_name(
                        row.get("customer_detail"), "Unknown customer"
                    ),
                    "description": (row.get("description") or "")[:100],
                    "status": row.get("status_text") or str(row.get("status") or ""),
                    "target_date": self._format_date(row.get("target_date")),
                    "overdue": bool(row.get("overdue")),
                    "created_at": parse_iso_datetime(row.get("creation_date")),
                }
            )
        self.latest_data["sales_orders"] = orders
        self.latest_data["sales_orders_count"] = len(orders)

    def update_build_orders(self):
        rows = self._api(
            "/api/build/",
            {
                "outstanding": True,
                "ordering": "-creation_date",
                "limit": _LIST_LIMIT,
                "part_detail": True,
            },
        )
        builds = []
        for row in rows:
            part_detail = row.get("part_detail") or {}
            part_name = (
                row.get("part_name")
                or part_detail.get("name")
                or part_detail.get("full_name")
                or "—"
            )
            qty = row.get("quantity") or 0
            completed = row.get("completed") or 0
            builds.append(
                {
                    "reference": row.get("reference") or "—",
                    "title": row.get("title") or part_name,
                    "part_name": part_name,
                    "status": row.get("status_text") or str(row.get("status") or ""),
                    "progress": f"{int(completed)}/{int(qty)}",
                    "target_date": self._format_date(row.get("target_date")),
                    "overdue": bool(row.get("overdue")),
                    "created_at": parse_iso_datetime(row.get("creation_date")),
                }
            )
        self.latest_data["build_orders"] = builds
        self.latest_data["build_orders_count"] = len(builds)
