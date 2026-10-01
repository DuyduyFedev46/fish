"""
Contract P8b Lô 3: route `/api/confirmation/...` (tên mới) và `/api/cskh/...` (tên cũ, alias tới Lô 5)
trỏ cùng một view: cùng ma trận vai, cùng kết quả, cùng bộ đếm throttle, không rò dữ liệu khách (bất biến 9).
Khoá JSON của `/api/dashboard/attention/` trả cả tên mới `confirmation_*` và tên cũ `cskh_*`.
Dữ liệu dùng SĐT và địa chỉ giả.
"""
from django.core.cache import cache
from django.test import override_settings

from apps.accounts import roles
from apps.common.tests.fixtures import client_for, make_user
from apps.delivery.models import ConfirmationTask, DeliveryNote
from apps.delivery.tests.test_cskh_l2 import ConfirmationL2BaseTestCase  # naming: allow - tên tệp test_cskh_l*.py đổi ở Lô 5 (02c), khi đó sửa import này

NEW = "/api/confirmation"
OLD = "/api/cskh"
PREFIXES = (NEW, OLD)

FAKE_PHONE = "0904445556"


class ConfirmationRouteAliasTests(ConfirmationL2BaseTestCase):
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
        """{prefix: {vai: status}} cho cùng một đường dẫn con, trên cả hai tiền tố."""
        matrix = {}
        for prefix in PREFIXES:
            matrix[prefix] = {}
            for role, user in self.users.items():
                res = getattr(client_for(user), method)(f"{prefix}{path}", **kwargs)
                matrix[prefix][role] = res.status_code
        return matrix

    # --- hàng đợi (GET list / retrieve) ------------------------------------

    def test_queue_list_role_matrix_same_on_both_prefixes(self):
        self._create_paid_order("DH-ALIAS-1", FAKE_PHONE)
        matrix = self._status_matrix("get", "/queue/")
        self.assertEqual(matrix[NEW], matrix[OLD])
        self.assertEqual(matrix[NEW][roles.CUSTOMER_SERVICE], 200)
        self.assertEqual(matrix[NEW][roles.WAREHOUSE_STAFF], 403)
        self.assertEqual(matrix[NEW][roles.DELIVERY_STAFF], 403)
        self.assertEqual(matrix[NEW]["anonymous"], 401)

    def test_queue_list_same_payload_shape_on_both_prefixes(self):
        _, _, note, _ = self._create_paid_order("DH-ALIAS-2", FAKE_PHONE)
        bodies = {p: client_for(self.cs1).get(f"{p}/queue/") for p in PREFIXES}
        for p, res in bodies.items():
            self.assertEqual(res.status_code, 200, p)
            self.assertEqual(res.headers.get("Cache-Control"), "no-store", p)
        new_rows, old_rows = (bodies[p].json()["results"] for p in (NEW, OLD))
        self.assertEqual([r["note_id"] for r in new_rows], [r["note_id"] for r in old_rows])
        self.assertIn(note.pk, [r["note_id"] for r in new_rows])
        self.assertEqual(set(new_rows[0].keys()), set(old_rows[0].keys()))

    def test_queue_retrieve_role_matrix_same_on_both_prefixes(self):
        _, _, note, _ = self._create_paid_order("DH-ALIAS-3", FAKE_PHONE)
        matrix = self._status_matrix("get", f"/queue/{note.pk}/")
        self.assertEqual(matrix[NEW], matrix[OLD])
        self.assertEqual(matrix[NEW][roles.CUSTOMER_SERVICE], 200)
        self.assertEqual(matrix[NEW][roles.WAREHOUSE_STAFF], 403)
        self.assertEqual(matrix[NEW]["anonymous"], 401)

    def test_queue_forbidden_roles_cannot_claim_on_either_prefix(self):
        _, _, note, task = self._create_paid_order("DH-ALIAS-4", FAKE_PHONE)
        for prefix in PREFIXES:
            for role in (roles.WAREHOUSE_STAFF, roles.DELIVERY_STAFF):
                res = client_for(self.users[role]).post(f"{prefix}/queue/{note.pk}/claim/")
                self.assertEqual(res.status_code, 403, (prefix, role))
            self.assertEqual(client_for(None).post(f"{prefix}/queue/{note.pk}/claim/").status_code, 401)
        task.refresh_from_db()
        self.assertIsNone(task.claimed_by_id)

    def test_claim_state_is_shared_between_prefixes(self):
        """cs1 nhận đơn qua tên mới thì cs2 gọi qua tên cũ vẫn bị 409: một view, một trạng thái."""
        _, _, note, _ = self._create_paid_order("DH-ALIAS-5", FAKE_PHONE)
        first = client_for(self.cs1).post(f"{NEW}/queue/{note.pk}/claim/")
        self.assertEqual(first.status_code, 200)
        second = client_for(self.cs2).post(f"{OLD}/queue/{note.pk}/claim/")
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

    def test_search_role_matrix_same_on_both_prefixes(self):
        self._create_paid_order("DH-ALIAS-7", FAKE_PHONE)
        matrix = self._status_matrix("post", "/search/", data={"q": FAKE_PHONE}, format="json")
        self.assertEqual(matrix[NEW], matrix[OLD])
        self.assertEqual(matrix[NEW][roles.CUSTOMER_SERVICE], 200)
        self.assertEqual(matrix[NEW][roles.OWNER], matrix[OLD][roles.OWNER])
        self.assertEqual(matrix[NEW][roles.WAREHOUSE_STAFF], 403)
        self.assertEqual(matrix[NEW][roles.DELIVERY_STAFF], 403)
        self.assertEqual(matrix[NEW]["anonymous"], 401)

    def test_search_only_accepts_post_on_both_prefixes(self):
        for prefix in PREFIXES:
            res = client_for(self.cs1).get(f"{prefix}/search/?q={FAKE_PHONE}")
            self.assertEqual(res.status_code, 405, prefix)

    def test_search_same_results_and_errors_on_both_prefixes(self):
        _, _, note, _ = self._create_paid_order("DH-ALIAS-8", FAKE_PHONE)
        for q, expected in ((FAKE_PHONE, 200), ("DH-ALIAS-8", 200), ("090444", 400)):
            statuses = {
                p: client_for(self.cs1).post(f"{p}/search/", {"q": q}, format="json") for p in PREFIXES
            }
            self.assertEqual({r.status_code for r in statuses.values()}, {expected}, q)
            if expected == 200:
                ids = [[r["note_id"] for r in res.json()["results"]] for res in statuses.values()]
                self.assertEqual(ids[0], ids[1])
                self.assertIn(note.pk, ids[0])
            else:
                self.assertEqual({res.json()["code"] for res in statuses.values()}, {"INVALID_QUERY"})

    def test_search_does_not_leak_personal_data_out_of_scope_on_both_prefixes(self):
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
        self.assertEqual(counted, 2)

    @override_settings(CAVEVE_THROTTLE_RATES={"customer_search": "2/min"})
    def test_search_throttle_shares_one_counter_across_prefixes(self):
        client = client_for(self.cs1)
        self.assertEqual(client.post(f"{NEW}/search/", {"q": FAKE_PHONE}, format="json").status_code, 200)
        self.assertEqual(client.post(f"{OLD}/search/", {"q": FAKE_PHONE}, format="json").status_code, 200)
        self.assertEqual(client.post(f"{NEW}/search/", {"q": FAKE_PHONE}, format="json").status_code, 429)
        self.assertEqual(client.post(f"{OLD}/search/", {"q": FAKE_PHONE}, format="json").status_code, 429)

    # --- dashboard attention: khoá JSON mới + cũ ----------------------------

    def test_attention_returns_new_and_legacy_keys_with_same_values(self):
        _, _, _, _ = self._create_paid_order("DH-ALIAS-10", FAKE_PHONE)
        pairs = {
            "confirmation_queue_waiting": "cskh_queue_waiting",
            "confirmation_escalated": "cskh_escalated",
            "confirmation_auto_cancel_blocked": "cskh_auto_cancel_blocked",
        }
        data = client_for(self.owner).get("/api/dashboard/attention/").json()
        for new_key, old_key in pairs.items():
            self.assertIn(new_key, data)
            self.assertIn(old_key, data)
            self.assertEqual(data[new_key], data[old_key])

    def test_attention_new_keys_follow_same_permission_as_old_keys(self):
        """CSKH chỉ thấy nhóm hàng đợi; Quản lý thấy cả nhóm quyết định; kho không thấy khoá xác nhận nào."""
        cs = client_for(self.cs1).get("/api/dashboard/attention/").json()
        self.assertEqual(set(cs), {"confirmation_queue_waiting", "cskh_queue_waiting", "refund_calls_open"})
        manager = client_for(self.manager).get("/api/dashboard/attention/").json()
        for key in ("confirmation_queue_waiting", "confirmation_escalated", "confirmation_auto_cancel_blocked",
                    "cskh_queue_waiting", "cskh_escalated", "cskh_auto_cancel_blocked"):
            self.assertIn(key, manager)
        warehouse = client_for(self.warehouse_staff).get("/api/dashboard/attention/").json()
        self.assertFalse([k for k in warehouse if k.startswith(("confirmation_", "cskh_"))])
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
