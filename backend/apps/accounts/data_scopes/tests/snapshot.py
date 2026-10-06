"""
Bộ thu ảnh chụp phạm vi dữ liệu (PV-01): gọi mọi đường đọc dữ liệu có phạm vi bằng từng tài khoản và ghi lại
**sự kiện** (fact), không ghi giá trị dữ liệu.

Mỗi (tài khoản, endpoint) là một tập chuỗi sự kiện, sắp xếp, dạng:
- `status=200`                      mã HTTP của danh sách / lệnh
- `visible:<nhãn>`                  dòng nào hiện trong danh sách
- `status:<nhãn>=404`               mã khi mở chi tiết từng dòng mẫu
- `pii:<nhãn>:<đường.dẫn>`          ô dữ liệu khách (tên, SĐT, địa chỉ, ghi chú) CÓ GIÁ TRỊ (không ghi giá trị)
- `extra:<khoá>=<giá trị>`          số liệu phụ không phải dữ liệu cá nhân (tổng tiền hoá đơn, số đơn chờ)

Lệch sự kiện giữa mốc và hiện tại -> `diff_snapshots` trả danh sách `(tài khoản, endpoint, dấu, sự kiện)`.
"""
import fnmatch
import re
from collections import namedtuple

from django.core.cache import cache
from rest_framework.test import APIClient

# Ô dữ liệu khách. `name`/`note` chỉ tính ở endpoint khách (khác tên nhân viên, tên hàng).
PII_LEAVES = frozenset({
    "phone", "address", "delivery_address", "default_address",
    "customer_name", "customer_phone", "customer_address", "recipient_name", "recipient_phone",
})
CUSTOMER_ENDPOINT_LEAVES = frozenset({"name", "note"})
# Nhánh của nhân viên (người giao, người gọi...): `phone` ở đây là của nhân viên, không phải của khách.
STAFF_SEGMENTS = frozenset({"assigned_to", "claimed_by", "created_by", "approved_by", "confirmed_by", "by", "actor",
                            "resolved_by"})

Diff = namedtuple("Diff", "user endpoint sign fact")

# Ngoại lệ DUY NHẤT được lệch (PV-01-AC3): nhóm NV kho thấy tên khách trên danh sách hoá đơn bán sau khi có việc V2.
# Duy duyệt 02/10 Q-4 (V2 mặc định bật cho NV kho). Mọi lệch khác -> test đỏ.
APPROVED_DIFFS = (
    ("warehouse_staff", "invoices.list", "+", "pii:*:customer_name"),  # Duy duyệt 02/10 Q-4
)


def pii_paths(node, *, customer_endpoint=False, path=()):
    """Tập đường dẫn (bỏ chỉ số mảng) của ô dữ liệu khách có giá trị khác rỗng trong JSON `node`."""
    found = set()
    leaves = PII_LEAVES | (CUSTOMER_ENDPOINT_LEAVES if customer_endpoint else frozenset())
    if isinstance(node, dict):
        for key, value in node.items():
            sub = (*path, key)
            if isinstance(value, (dict, list)):
                if key in STAFF_SEGMENTS:
                    continue
                found |= pii_paths(value, customer_endpoint=customer_endpoint, path=sub)
            elif value not in (None, "") and (key in leaves or (key == "name" and path[-1:] in (("customer",), ("recipient",)))):
                found.add(".".join(sub))
    elif isinstance(node, list):
        for item in node:
            found |= pii_paths(item, customer_endpoint=customer_endpoint, path=(*path, "[]"))
    return found


def _rows(data):
    if isinstance(data, dict):
        return data.get("results", data.get("rows", []))
    return data if isinstance(data, list) else []


class Collector:
    """Gọi endpoint bằng từng tài khoản và gom sự kiện. `scene` lấy từ `fixtures.build_scene()`."""

    def __init__(self, scene):
        self.scene = scene
        self.clients = {}
        for label, user in scene.users.items():
            client = APIClient()
            if user is not None:
                client.force_authenticate(user)
            self.clients[label] = client

    # --- đọc một endpoint ---------------------------------------------------

    def _get(self, user_label, url, *, method="get", body=None):
        cache.clear()  # throttle tìm kiếm không cản các lần gọi liên tiếp
        client = self.clients[user_label]
        if method == "post":
            response = client.post(url, body or {}, format="json")
        else:
            response = client.get(url)
        try:
            data = response.json()
        except ValueError:
            data = None
        return response.status_code, data

    def list_facts(self, user_label, url, kind, *, id_field="id", customer_endpoint=False, method="get", body=None):
        """Sự kiện của một danh sách: mã, dòng hiện, ô dữ liệu khách có giá trị theo từng dòng."""
        labels = self.scene.labels(kind)
        status, data = self._get(user_label, url, method=method, body=body)
        facts = {f"status={status}"}
        if status != 200:
            return facts
        for row in _rows(data):
            label = labels.get(row.get(id_field), f"unknown:{row.get(id_field)}")
            facts.add(f"visible:{label}")
            for path in pii_paths(row, customer_endpoint=customer_endpoint):
                facts.add(f"pii:{label}:{path}")
        totals = data.get("totals") if isinstance(data, dict) else None
        if totals:
            facts.add(f"extra:totals.keys={','.join(sorted(totals))}")
            facts.add(f"extra:totals.amount={totals.get('amount')}")
        return facts

    def detail_facts(self, user_label, url_for, kind, *, customer_endpoint=False, extra=None):
        """Mở chi tiết từng dòng mẫu: mã trả về + ô dữ liệu khách có giá trị."""
        facts = set()
        for label, obj in getattr(self.scene, kind).items():
            status, data = self._get(user_label, url_for(obj))
            facts.add(f"status:{label}={status}")
            if status == 200 and data is not None:
                for path in pii_paths(data, customer_endpoint=customer_endpoint):
                    facts.add(f"pii:{label}:{path}")
        return facts

    def guidance_facts(self, user_label, doc_type, kind):
        facts = set()
        for label, obj in getattr(self.scene, kind).items():
            status, data = self._get(user_label, f"/api/guidance/{doc_type}/{obj.pk}/")
            facts.add(f"status:{label}={status}")
            if status == 200 and data is not None:
                for path in pii_paths(data):
                    facts.add(f"pii:{label}:{path}")
        return facts

    # --- danh mục endpoint ----------------------------------------------------

    def collect_user(self, user_label, only=None):
        scene = self.scene
        order_phone_prefix = "09000001"
        courier_customer = scene.customers["customer_of_order_assigned_courier"].pk
        other_order = scene.orders["order_assigned_other"]
        calls = {
            "orders.list": lambda: self.list_facts(user_label, "/api/sales/orders/", "orders"),
            "orders.search_phone": lambda: self.list_facts(
                user_label, f"/api/sales/orders/?q={order_phone_prefix}", "orders"),
            "orders.search_name": lambda: self.list_facts(user_label, "/api/sales/orders/?q=Giả", "orders"),
            "orders.filter_customer": lambda: self.list_facts(
                user_label, f"/api/sales/orders/?customer={courier_customer}", "orders"),
            "orders.detail": lambda: self.detail_facts(user_label, lambda o: f"/api/sales/orders/{o.pk}/", "orders"),
            "invoices.list": lambda: self.list_facts(user_label, "/api/sales/invoices/", "invoices"),
            "invoices.detail": lambda: self.detail_facts(
                user_label, lambda o: f"/api/sales/invoices/{o.pk}/", "invoices"),
            "refunds.list": lambda: self.list_facts(user_label, "/api/sales/refunds/", "refunds"),
            "refunds.detail": lambda: self.detail_facts(
                user_label, lambda o: f"/api/sales/refunds/{o.pk}/", "refunds"),
            "deliveries.list": lambda: self.list_facts(user_label, "/api/delivery/notes/", "notes"),
            "deliveries.mine": lambda: self.list_facts(user_label, "/api/delivery/notes/?assigned_to=me", "notes"),
            "deliveries.other": lambda: self.list_facts(
                user_label, f"/api/delivery/notes/?assigned_to={scene.users['courier_other'].pk}", "notes"),
            "deliveries.detail": lambda: self.detail_facts(
                user_label, lambda o: f"/api/delivery/notes/{o.pk}/", "notes"),
            "returns.list": lambda: self.list_facts(user_label, "/api/inventory/returns/", "returns"),
            "returns.detail": lambda: self.detail_facts(
                user_label, lambda o: f"/api/inventory/returns/{o.pk}/", "returns"),
            "receipts.list": lambda: self.list_facts(user_label, "/api/purchasing/receipts/", "receipts"),
            "receipts.detail": lambda: self.detail_facts(
                user_label, lambda o: f"/api/purchasing/receipts/{o.pk}/", "receipts"),
            "confirmation.queue": lambda: self.list_facts(
                user_label, "/api/confirmation/queue/", "notes", id_field="note_id"),
            "confirmation.queue_done": lambda: self.list_facts(
                user_label, "/api/confirmation/queue/?state=DONE", "notes", id_field="note_id"),
            "confirmation.queue_escalated": lambda: self.list_facts(
                user_label, "/api/confirmation/queue/?state=ESCALATED", "notes", id_field="note_id"),
            "confirmation.detail": lambda: self.detail_facts(
                user_label, lambda o: f"/api/confirmation/queue/{o.pk}/", "notes"),
            "confirmation.search_phone": lambda: self.search_facts(user_label, other_order.phone),
            "confirmation.search_called": lambda: self.search_facts(
                user_label, scene.orders["order_called_recent_by_cs"].phone),
            "directory.list": lambda: self.list_facts(
                user_label, "/api/sales/customer-directory/", "customers", customer_endpoint=True),
            "directory.search": lambda: self.list_facts(
                user_label, "/api/sales/customer-directory/search/", "customers", customer_endpoint=True,
                method="post", body={"q": "Giả"}),
            "directory.detail": lambda: self.detail_facts(
                user_label, lambda o: f"/api/sales/customer-directory/{o.pk}/", "customers", customer_endpoint=True),
            "customers.list": lambda: self.list_facts(
                user_label, "/api/sales/customers/", "customers", customer_endpoint=True),
            "customers.detail": lambda: self.detail_facts(
                user_label, lambda o: f"/api/sales/customers/{o.pk}/", "customers", customer_endpoint=True),
            "guidance.order": lambda: self.guidance_facts(user_label, "order", "orders"),
            "guidance.delivery": lambda: self.guidance_facts(user_label, "delivery", "notes"),
            "guidance.return": lambda: self.guidance_facts(user_label, "return", "returns"),
            "guidance.customer": lambda: self.guidance_facts(user_label, "customer", "customers"),
            "guidance.receipt": lambda: self.guidance_facts(user_label, "receipt", "receipts"),
            "dashboard.summary": lambda: self.dashboard_facts(user_label),
            "ai.orders_list": lambda: self.ai_list_facts(user_label, "sales.salesorder.list", "orders"),
            "ai.deliveries_list": lambda: self.ai_list_facts(user_label, "delivery.deliverynote.list", "notes"),
            "ai.orders_detail": lambda: self.ai_detail_facts(user_label, "sales.salesorder.retrieve", "orders"),
        }
        return {
            name: sorted(fn())
            for name, fn in calls.items()
            if only is None or name in only
        }

    def search_facts(self, user_label, query):
        """POST /api/confirmation/search/ — kết quả theo phiếu giao, ghi nhãn từ mã đơn."""
        status, data = self._get(user_label, "/api/confirmation/search/", method="post", body={"q": query})
        facts = {f"status={status}"}
        if status != 200:
            return facts
        by_code = self.scene.codes
        for row in _rows(data):
            label = by_code.get(row.get("order_code"), f"unknown:{row.get('order_code')}")
            facts.add(f"visible:{label}")
            for path in pii_paths(row):
                facts.add(f"pii:{label}:{path}")
        return facts

    def dashboard_facts(self, user_label):
        status, data = self._get(user_label, "/api/dashboard/summary/")
        facts = {f"status={status}"}
        if status != 200:
            return facts
        for row in data.get("recent_orders", []):
            facts.add(f"visible:{self.scene.codes.get(row.get('code'), 'unknown:' + str(row.get('code')))}")
            for path in pii_paths(row):
                facts.add(f"pii:recent_order:{path}")
        kpis = data.get("kpis", {})
        for key in ("pending_orders", "booked_soon"):
            facts.add(f"extra:kpis.{key}={kpis.get(key)}")
        facts.add(f"extra:kpis.revenue_today_present={'revenue_today' in kpis}")
        return facts

    def ai_list_facts(self, user_label, command_id, kind):
        from django.test import override_settings

        with override_settings(AI_ENABLED=True):
            status, data = self._get(
                user_label, f"/api/ai/commands/{command_id}/call/", method="post", body={"args": {}})
        facts = {f"status={status}"}
        if status != 200 or not isinstance(data, dict):
            return facts
        result = data.get("result") or {}
        labels = self.scene.labels(kind)
        for row in result.get("rows", []):
            label = labels.get(row.get("id"), self.scene.codes.get(row.get("code"), f"unknown:{row.get('id')}"))
            facts.add(f"visible:{label}")
        for path in pii_paths(data):
            facts.add(f"pii:response:{path}")
        return facts

    def ai_detail_facts(self, user_label, command_id, kind):
        from django.test import override_settings

        facts = set()
        for label, obj in getattr(self.scene, kind).items():
            with override_settings(AI_ENABLED=True):
                status, data = self._get(
                    user_label, f"/api/ai/commands/{command_id}/call/", method="post",
                    body={"target_id": str(obj.pk), "args": {}})
            facts.add(f"status:{label}={status}")
            if status == 200 and data is not None:
                for path in pii_paths(data):
                    facts.add(f"pii:{label}:{path}")
        return facts

    def collect(self, users=None, only=None):
        """{tài khoản: {endpoint: [sự kiện...]}}. `users`, `only` để thu một phần."""
        return {
            label: self.collect_user(label, only=only)
            for label in self.scene.users
            if users is None or label in users
        }


# --- so sánh ------------------------------------------------------------------


def diff_snapshots(expected, actual, *, users=None):
    """Mọi lệch sự kiện giữa mốc `expected` và `actual`: danh sách `Diff(user, endpoint, '+'|'-', fact)`.
    `+` = hiện tại có mà mốc không có (thấy thêm), `-` = mốc có mà hiện tại mất (thấy bớt)."""
    out = []
    for user in sorted(set(expected) | set(actual)):
        if users is not None and user not in users:
            continue
        for endpoint in sorted(set(expected.get(user, {})) | set(actual.get(user, {}))):
            before = set(expected.get(user, {}).get(endpoint, []))
            after = set(actual.get(user, {}).get(endpoint, []))
            for fact in sorted(after - before):
                out.append(Diff(user, endpoint, "+", fact))
            for fact in sorted(before - after):
                out.append(Diff(user, endpoint, "-", fact))
    return out


def is_approved(diff):
    return any(
        diff.user == user and diff.endpoint == endpoint and diff.sign == sign and fnmatch.fnmatchcase(diff.fact, glob)
        for user, endpoint, sign, glob in APPROVED_DIFFS
    )


def unapproved(diffs):
    return [d for d in diffs if not is_approved(d)]


def format_diffs(diffs):
    return "\n".join(f"  [{d.user}] {d.endpoint} {d.sign} {d.fact}" for d in diffs)


PHONE_LIKE = re.compile(r"\d{9,}")
