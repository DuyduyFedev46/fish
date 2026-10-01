"""
Contract route việc gọi xác nhận đơn (P8b Lô 3, alias tên cũ gỡ ở Lô 5): chỉ còn `/api/confirmation/...`.
Ma trận vai, throttle `customer_search`, không rò dữ liệu khách (bất biến 9). Route cũ `/api/cskh/...` trả 404 với mọi vai
và không được chạy view. Khoá JSON của `/api/dashboard/attention/` chỉ còn tên `confirmation_*`.
Dữ liệu dùng SĐT và địa chỉ giả.
"""
from django.core.cache import cache
from django.test import override_settings

from apps.accounts import roles
from apps.common.tests.fixtures import client_for, make_user
from apps.delivery.models import ConfirmationTask, DeliveryNote
from apps.delivery.tests.test_confirmation_queue_and_labels import ConfirmationL2BaseTestCase

NEW = "/api/confirmation"
REMOVED_PREFIX = "/api/cskh"  # tên cũ đã gỡ ở P8b Lô 5
PREFIXES = (NEW,)

FAKE_PHONE = "0904445556"


class ConfirmationRouteTests(ConfirmationL2BaseTestCase):
    def setUp(self):
        super().setUp()
        cache.clear()
        self.owner = make_user("owner_alias", roles.OWNER)
        self.manager = make_user("manager_alias", roles.MANAGER)
        self.warehouse_staff = make_user("warehouse_alias", roles.WAREHOUSE_STAFF)
        self.delivery_staff = make_user("delivery_alias", roles.DELIVERY_STAFF)
        self.users = {
            roles.OWNER: self.owner,
            roles.MANAGER: self.manager,
            roles.WAREHOUSE_STAFF: self.warehouse_staff,
            roles.DELIVERY_STAFF: self.delivery_staff,
            roles.CUSTOMER_SERVICE: self.cs1,
            "anonymous": None,
        }

    def _status_matrix(self, method, path, **kwargs):
        """{prefix: {vai: status}} cho cùng một đường dẫn con."""
        matrix = {}
        for prefix in PREFIXES:
            matrix[prefix] = {}
            for role, user in self.users.items():
                res = getattr(client_for(user), method)(f"{prefix}{path}", **kwargs)
                matrix[prefix][role] = res.status_code
        return matrix

    # --- hàng đợi (GET list / retrieve) ------------------------------------

    def test_queue_list_role_matrix(self):
        self._create_paid_order("DH-ALIAS-1", FAKE_PHONE)
        matrix = self._status_matrix("get", "/queue/")
        self.assertEqual(matrix[NEW][roles.CUSTOMER_SERVICE], 200)
        self.assertEqual(matrix[NEW][roles.WAREHOUSE_STAFF], 403)
        self.assertEqual(matrix[NEW][roles.DELIVERY_STAFF], 403)
        self.assertEqual(matrix[NEW]["anonymous"], 401)

    def test_queue_list_is_no_store_and_lists_the_note(self):
        _, _, note, _ = self._create_paid_order("DH-ALIAS-2", FAKE_PHONE)
        res = client_for(self.cs1).get(f"{NEW}/queue/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get("Cache-Control"), "no-store")
        self.assertIn(note.pk, [r["note_id"] for r in res.json()["results"]])

    def test_queue_retrieve_role_matrix(self):
        _, _, note, _ = self._create_paid_order("DH-ALIAS-3", FAKE_PHONE)
        matrix = self._status_matrix("get", f"/queue/{note.pk}/")
        self.assertEqual(matrix[NEW][roles.CUSTOMER_SERVICE], 200)
        self.assertEqual(matrix[NEW][roles.WAREHOUSE_STAFF], 403)
        self.assertEqual(matrix[NEW]["anonymous"], 401)

    def test_queue_forbidden_roles_cannot_claim(self):
        _, _, note, task = self._create_paid_order("DH-ALIAS-4", FAKE_PHONE)
        for prefix in PREFIXES:
            for role in (roles.WAREHOUSE_STAFF, roles.DELIVERY_STAFF):
                res = client_for(self.users[role]).post(f"{prefix}/queue/{note.pk}/claim/")
                self.assertEqual(res.status_code, 403, (prefix, role))
            self.assertEqual(client_for(None).post(f"{prefix}/queue/{note.pk}/claim/").status_code, 401)
        task.refresh_from_db()
        self.assertIsNone(task.claimed_by_id)

    def test_claim_by_one_user_blocks_another_with_409(self):
        _, _, note, _ = self._create_paid_order("DH-ALIAS-5", FAKE_PHONE)
        first = client_for(self.cs1).post(f"{NEW}/queue/{note.pk}/claim/")
        self.assertEqual(first.status_code, 200)
        second = client_for(self.cs2).post(f"{NEW}/queue/{note.pk}/claim/")
        self.assertEqual(second.status_code, 409)
        self.assertEqual(second.json()["code"], "CLAIMED")

    def test_record_call_works_on_new_prefix(self):
        _, _, note, task = self._create_paid_order("DH-ALIAS-6", FAKE_PHONE)
        res = client_for(self.cs1).post(f"{NEW}/queue/{note.pk}/calls/", {"result": "CONFIRMED"}, format="json")
        self.assertEqual(res.status_code, 201)
        note.refresh_from_db()
        self.assertEqual(note.status, DeliveryNote.Status.PREPARING)
        task.refresh_from_db()
        self.assertEqual(task.state, ConfirmationTask.State.DONE)

    # --- tìm kiếm ----------------------------------------------------------

    def test_search_role_matrix(self):
        self._create_paid_order("DH-ALIAS-7", FAKE_PHONE)
        matrix = self._status_matrix("post", "/search/", data={"q": FAKE_PHONE}, format="json")
        self.assertEqual(matrix[NEW][roles.CUSTOMER_SERVICE], 200)
        self.assertEqual(matrix[NEW][roles.WAREHOUSE_STAFF], 403)
        self.assertEqual(matrix[NEW][roles.DELIVERY_STAFF], 403)
        self.assertEqual(matrix[NEW]["anonymous"], 401)

    def test_search_only_accepts_post(self):
        for prefix in PREFIXES:
            res = client_for(self.cs1).get(f"{prefix}/search/?q={FAKE_PHONE}")
            self.assertEqual(res.status_code, 405, prefix)

    def test_search_results_and_errors(self):
        _, _, note, _ = self._create_paid_order("DH-ALIAS-8", FAKE_PHONE)
        for q, expected in ((FAKE_PHONE, 200), ("DH-ALIAS-8", 200), ("090444", 400)):
            res = client_for(self.cs1).post(f"{NEW}/search/", {"q": q}, format="json")
            self.assertEqual(res.status_code, expected, q)
            if expected == 200:
                self.assertIn(note.pk, [r["note_id"] for r in res.json()["results"]])
            else:
                self.assertEqual(res.json()["code"], "INVALID_QUERY")

    def test_search_does_not_leak_personal_data_out_of_scope(self):
        """Đơn ngoài phạm vi của CSKH: chỉ có SĐT đã che, không có tên/địa chỉ/SĐT đủ (bất biến 9)."""
        _, _, note, task = self._create_paid_order("DH-ALIAS-9", FAKE_PHONE)
        note.status = DeliveryNote.Status.READY
        note.save(update_fields=["status"])
        task.state = ConfirmationTask.State.DONE
        task.save(update_fields=["state"])
        counted = 0
        for prefix in PREFIXES:
            res = client_for(self.cs1).post(f"{prefix}/search/", {"q": "DH-ALIAS-9"}, format="json")
            self.assertEqual(res.status_code, 200, prefix)
            counted += 1
            rows = [r for r in res.json()["results"] if r["note_id"] == note.pk]
            self.assertEqual(len(rows), 1)
            row = rows[0]
            self.assertFalse(row["in_scope"])
            self.assertEqual(row["phone_masked"], "09xx xxx 556")
            for key in ("phone", "customer_name", "address"):
                self.assertNotIn(key, row)
            body = res.content.decode()
            self.assertNotIn(FAKE_PHONE, body)
            self.assertNotIn("Nguyễn Huệ", body)
            self.assertNotIn("Khách DH-ALIAS-9", body)
        self.assertEqual(counted, 1)

    @override_settings(CAVEVE_THROTTLE_RATES={"customer_search": "2/min"})
    def test_search_throttle_limits_the_confirmation_route(self):
        client = client_for(self.cs1)
        self.assertEqual(client.post(f"{NEW}/search/", {"q": FAKE_PHONE}, format="json").status_code, 200)
        self.assertEqual(client.post(f"{NEW}/search/", {"q": FAKE_PHONE}, format="json").status_code, 200)
        self.assertEqual(client.post(f"{NEW}/search/", {"q": FAKE_PHONE}, format="json").status_code, 429)

    # --- dashboard attention: khoá JSON mới + cũ ----------------------------

    def test_attention_returns_only_confirmation_keys(self):
        self._create_paid_order("DH-ALIAS-10", FAKE_PHONE)
        data = client_for(self.owner).get("/api/dashboard/attention/").json()
        for key in ("confirmation_queue_waiting", "confirmation_escalated", "confirmation_auto_cancel_blocked"):
            self.assertIn(key, data)
        self.assertEqual([k for k in data if k.startswith("cskh")], [], "khoá JSON cskh_* đã gỡ ở Lô 5")

    def test_attention_keys_follow_role_permission(self):
        """CSKH chỉ thấy nhóm hàng đợi; Quản lý thấy cả nhóm quyết định; kho không thấy khoá xác nhận nào."""
        cs = client_for(self.cs1).get("/api/dashboard/attention/").json()
        self.assertEqual(set(cs), {"confirmation_queue_waiting", "refund_calls_open"})
        manager = client_for(self.manager).get("/api/dashboard/attention/").json()
        for key in ("confirmation_queue_waiting", "confirmation_escalated", "confirmation_auto_cancel_blocked"):
            self.assertIn(key, manager)
        self.assertEqual([k for k in manager if k.startswith("cskh")], [])
        warehouse = client_for(self.warehouse_staff).get("/api/dashboard/attention/").json()
        self.assertFalse([k for k in warehouse if k.startswith(("confirmation_", "cskh"))])
        self.assertEqual(client_for(self.delivery_staff).get("/api/dashboard/attention/").status_code, 403)
        self.assertEqual(client_for(None).get("/api/dashboard/attention/").status_code, 401)

    def test_attention_has_only_counters_no_personal_data(self):
        """Khoá mới chỉ là số đếm: không tên, SĐT, địa chỉ (bất biến 9), không giá vốn (bất biến 1)."""
        self._create_paid_order("DH-ALIAS-11", FAKE_PHONE)
        res = client_for(self.owner).get("/api/dashboard/attention/")
        self.assertEqual(res.status_code, 200)
        for key, value in res.json().items():
            self.assertIsInstance(value, int, key)
        body = res.content.decode()
        self.assertNotIn(FAKE_PHONE, body)
        self.assertNotIn("Nguyễn Huệ", body)


class RemovedConfirmationAliasTests(ConfirmationL2BaseTestCase):
    """P8b Lô 5: tên cũ `/api/cskh/...` đã gỡ, mọi vai (kể cả chưa đăng nhập) nhận 404 và không chạy view nào."""

    def setUp(self):
        super().setUp()
        cache.clear()
        self.users = {
            roles.OWNER: make_user("owner_removed", roles.OWNER),
            roles.MANAGER: make_user("manager_removed", roles.MANAGER),
            roles.WAREHOUSE_STAFF: make_user("warehouse_removed", roles.WAREHOUSE_STAFF),
            roles.DELIVERY_STAFF: make_user("delivery_removed", roles.DELIVERY_STAFF),
            roles.CUSTOMER_SERVICE: self.cs1,
            "anonymous": None,
        }

    def test_removed_prefix_returns_404_for_every_role_and_method(self):
        _, _, note, task = self._create_paid_order("DH-REMOVED-1", FAKE_PHONE)
        calls = (
            ("get", f"{REMOVED_PREFIX}/queue/", {}),
            ("get", f"{REMOVED_PREFIX}/queue/{note.pk}/", {}),
            ("post", f"{REMOVED_PREFIX}/queue/{note.pk}/claim/", {}),
            ("post", f"{REMOVED_PREFIX}/queue/{note.pk}/calls/", {"data": {"result": "CONFIRMED"}, "format": "json"}),
            ("post", f"{REMOVED_PREFIX}/search/", {"data": {"q": FAKE_PHONE}, "format": "json"}),
        )
        statuses = 0
        for role, user in self.users.items():
            for method, path, kwargs in calls:
                with self.subTest(role=role, path=path):
                    res = getattr(client_for(user), method)(path, **kwargs)
                    self.assertEqual(res.status_code, 404)
                    self.assertNotIn(FAKE_PHONE, res.content.decode())
                    statuses += 1
        self.assertEqual(statuses, len(calls) * len(self.users))
        # Không view nào chạy: phiếu vẫn chưa ai nhận, chưa ghi cuộc gọi.
        task.refresh_from_db()
        note.refresh_from_db()
        self.assertIsNone(task.claimed_by_id)
        self.assertEqual(note.status, DeliveryNote.Status.CONFIRMING)

    def test_new_route_still_answers_so_the_404_above_is_meaningful(self):
        self._create_paid_order("DH-REMOVED-2", FAKE_PHONE)
        self.assertEqual(client_for(self.cs1).get(f"{NEW}/queue/").status_code, 200)
        self.assertEqual(client_for(self.cs1).get(f"{REMOVED_PREFIX}/queue/").status_code, 404)

    def test_removed_prefix_stays_forbidden_for_ai_index(self):
        """Giữ vĩnh viễn (phòng thủ nhiều lớp): nếu ai đó thêm lại route tên cũ thì AI vẫn không thấy."""
        from apps.ai.policy.rules import FORBIDDEN_PREFIXES, is_url_forbidden

        self.assertIn(f"{REMOVED_PREFIX}/", FORBIDDEN_PREFIXES)
        self.assertTrue(is_url_forbidden(f"{REMOVED_PREFIX}/queue/"))
