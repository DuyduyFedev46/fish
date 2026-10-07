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
from django.db import transaction
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
    # Người kiêm nhiệm NV kho + NV giao: có V2 qua nhóm NV kho nên cùng một ngoại lệ Q-4 (D2 của họ = all, như NV kho).
    ("warehouse_courier", "invoices.list", "+", "pii:*:customer_name"),  # Duy duyệt 02/10 Q-4 (thành viên NV kho)
)

# CHỜ Duy D-3 (review techlead Lô 4, M1): người không nhóm (`direct_permissions`, quyền gán trực tiếp) bị THU HẸP ở phiếu nhập (D6)
# và khách (D7). Mỗi mục là một thay đổi hành vi chưa được Duy duyệt, nên nằm ở đây thay vì `APPROVED_DIFFS`, và tệp mốc vẫn ghi
# hành vi cũ. Chỉ được thu hẹp: dòng biến mất (`-`) hoặc 200 thành 404 (`+ status:*=404`). Không merge main khi còn mục nào.
# Khi Duy trả lời: chuyển sang `APPROVED_DIFFS` kèm "Duy duyệt <ngày> D-3", hoặc sửa code nếu Duy chọn khác.
_PENDING_DUY_ENDPOINTS = (
    "receipts.list", "receipts.detail", "guidance.receipt",
    "directory.list", "directory.detail", "directory.search", "customers.list", "customers.detail", "guidance.customer",
    "refunds.list", "refunds.detail",  # C1 (Lô 5): D1 cho phiếu hoàn tiền
    "dashboard.summary",  # C1 (Lô 5): D1 cho bảng điều hành
)
PENDING_DUY_DIFFS = tuple(
    entry
    for endpoint in _PENDING_DUY_ENDPOINTS
    for entry in (
        ("direct_permissions", endpoint, "-", "*"),  # CHỜ Duy D-3
        ("direct_permissions", endpoint, "+", "status:*=404"),  # CHỜ Duy D-3
    )
) + (
    # Bảng điều hành của người không nhóm (D1 = assigned_deliveries): số đếm co lại (`+ extra:kpis.*` là con số MỚI nhỏ hơn, đi cùng
    # dòng `-` của số cũ) và đơn của chính họ lọt vào cửa sổ 8 đơn gần nhất khi các đơn khác ra khỏi phạm vi. Không ai thấy thêm đơn.
    ("direct_permissions", "dashboard.summary", "+", "extra:kpis.*"),  # CHỜ Duy D-3
    ("direct_permissions", "dashboard.summary", "+", "visible:order_assigned_direct"),  # CHỜ Duy D-3
) + tuple(
    # O1 (QA Lô 4 + 5, L2 review Lô 4): người kiêm nhiệm NV kho + CSKH. Trước PV-05 `has_full_delivery_scope` (NV kho) cho họ thấy mọi
    # phiếu chờ gọi; nay chỉ nhóm CSKH đủ điều kiện D4 (NV kho không có `confirm_with_customer`) nên còn `pending_or_called_recently`.
    entry
    for endpoint in (
        "confirmation.detail", "confirmation.queue_done", "confirmation.search_called", "confirmation.search_phone",
        "actions.confirmation_call", "actions.confirmation_claim", "actions.confirmation_recipient",
        "actions.confirmation_unconfirm",
    )
    for entry in (
        ("warehouse_service", endpoint, "-", "*"),  # CHỜ Duy D-3
        ("warehouse_service", endpoint, "+", "status:*=404"),  # CHỜ Duy D-3
    )
)
PENDING_DUY_USERS = ("direct_permissions", "warehouse_service")


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
                user_label, "/api/sales/orders/search/", "orders", method="post", body={"q": order_phone_prefix}),
            "orders.search_name": lambda: self.list_facts(
                user_label, "/api/sales/orders/search/", "orders", method="post", body={"q": "Giả"}),
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
            "actions.confirmation_claim": lambda: self.action_facts(
                user_label, "notes", lambda o: ("post", f"/api/confirmation/queue/{o.pk}/claim/", {})),
            "actions.confirmation_call": lambda: self.action_facts(
                user_label, "notes",
                lambda o: ("post", f"/api/confirmation/queue/{o.pk}/calls/", {"result": "UNREACHABLE", "note": "x"})),
            "actions.confirmation_unconfirm": lambda: self.action_facts(
                user_label, "notes",
                lambda o: ("post", f"/api/confirmation/queue/{o.pk}/unconfirm/", {"reason": "x"})),
            "actions.confirmation_recipient": lambda: self.action_facts(
                user_label, "notes",
                lambda o: ("post", f"/api/confirmation/queue/{o.pk}/recipient/", {
                    "recipient_name": "Người nhận giả", "recipient_phone": "0900000888",
                    "delivery_address": "Số 88 Đường Giả"})),
            "actions.returns_create": lambda: self.action_facts(
                user_label, "notes",
                lambda o: ("post", "/api/inventory/returns/",
                           {"delivery_note": o.pk, "batch": scene.batch.pk, "qty": "0.500"}),
                extra_subjects=[("no_note", ("post", "/api/inventory/returns/",
                                             {"batch": scene.batch.pk, "qty": "0.500"}))]),
            "actions.returns_cancel": lambda: self.action_facts(
                user_label, "returns", lambda o: ("post", f"/api/inventory/returns/{o.pk}/cancel/", {})),
            "actions.returns_update": lambda: self.action_facts(
                user_label, "returns", lambda o: ("patch", f"/api/inventory/returns/{o.pk}/", {"note": "x"})),
            "actions.receipts_update": lambda: self.action_facts(
                user_label, "receipts", lambda o: ("patch", f"/api/purchasing/receipts/{o.pk}/", {"note": "x"})),
            "actions.receipts_submit": lambda: self.action_facts(
                user_label, "receipts", lambda o: ("post", f"/api/purchasing/receipts/{o.pk}/submit/", {})),
            "actions.receipts_cancel": lambda: self.action_facts(
                user_label, "receipts", lambda o: ("post", f"/api/purchasing/receipts/{o.pk}/cancel/", {})),
            "actions.deliveries_assign": lambda: self.action_facts(
                user_label, "notes",
                lambda o: ("post", f"/api/delivery/notes/{o.pk}/assign/",
                           {"assigned_to": scene.users["courier_other"].pk})),
            "actions.deliveries_status": lambda: self.action_facts(
                user_label, "notes",
                lambda o: ("post", f"/api/delivery/notes/{o.pk}/status/", {"to_status": "READY"})),
            "actions.deliveries_label": lambda: self.action_facts(
                user_label, "notes", lambda o: ("get", f"/api/delivery/notes/{o.pk}/label/", None)),
            "actions.deliveries_label_print": lambda: self.action_facts(
                user_label, "notes", lambda o: ("post", f"/api/delivery/notes/{o.pk}/label/print/", {})),
            "actions.deliveries_label_void": lambda: self.action_facts(
                user_label, "notes", lambda o: ("post", f"/api/delivery/notes/{o.pk}/label/void/", {})),
            "ai.orders_list": lambda: self.ai_list_facts(user_label, "sales.salesorder.list", "orders"),
            "ai.deliveries_list": lambda: self.ai_list_facts(user_label, "delivery.deliverynote.list", "notes"),
            "ai.orders_detail": lambda: self.ai_detail_facts(user_label, "sales.salesorder.retrieve", "orders"),
        }
        return {
            name: sorted(fn())
            for name, fn in calls.items()
            if only is None or name in only
        }


    # --- đường hành động (M1 review 06/10) ------------------------------------

    def _act(self, user_label, method, url, body=None):
        """Gọi một hành động GHI rồi rollback (savepoint) để dữ liệu không đổi. Trả mã HTTP, hoặc 'EXC' nếu view ném lỗi."""
        cache.clear()
        client = self.clients[user_label]
        try:
            with transaction.atomic():
                if method == "get":
                    response = client.get(url)
                elif method == "patch":
                    response = client.patch(url, body or {}, format="json")
                else:
                    response = client.post(url, body or {}, format="json")
                transaction.set_rollback(True)
        except Exception as exc:  # noqa: BLE001 - ghi tên lỗi, không ghi nội dung
            return f"EXC:{type(exc).__name__}"
        return response.status_code

    def action_facts(self, user_label, kind, build, *, extra_subjects=()):
        """`build(obj) -> (method, url, body)`; mỗi dòng mẫu một sự kiện `status:<nhãn>=<mã>`."""
        facts = set()
        for label, obj in getattr(self.scene, kind).items():
            method, url, body = build(obj)
            facts.add(f"status:{label}={self._act(user_label, method, url, body)}")
        for label, (method, url, body) in extra_subjects:
            facts.add(f"status:{label}={self._act(user_label, method, url, body)}")
        return facts

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
        facts.add(f"extra:kpis.revenue_today={kpis.get('revenue_today')}")  # doanh thu, không phải giá vốn hay dữ liệu cá nhân
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
        for user, endpoint, sign, glob in APPROVED_DIFFS + PENDING_DUY_DIFFS
    )


def unapproved(diffs):
    return [d for d in diffs if not is_approved(d)]


def format_diffs(diffs):
    return "\n".join(f"  [{d.user}] {d.endpoint} {d.sign} {d.fact}" for d in diffs)


PHONE_LIKE = re.compile(r"\d{9,}")
