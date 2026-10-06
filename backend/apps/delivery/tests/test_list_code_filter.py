"""
ED-07-BE (Lô 17a, A9): GET /api/delivery/notes/?code=<mã> khớp ĐÚNG mã phiếu giao (không phân biệt hoa thường).

Chạy trên `get_queryset()` đã có phạm vi: người giao tra mã phiếu của người khác thì `count: 0`, giống mã không tồn tại
(ED-07-AC3). Dữ liệu giả.
"""
from apps.common.tests.fixtures import client_for

from .test_note_detail_filters import NoteScopeBase

LIST = "/api/delivery/notes/"


class DeliveryListCodeFilterTests(NoteScopeBase):
    def codes(self, user, code):
        response = client_for(user).get(LIST, {"code": code})
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual(body["count"], len(body["results"]))
        return [row["code"] for row in body["results"]]

    def test_ed07_exact_code_matches_one_note_case_insensitive(self):
        code = self.note_p.code
        self.assertEqual(self.codes(self.manager, code), [code])
        self.assertEqual(self.codes(self.manager, code.lower()), [code])

    def test_ed07_partial_code_does_not_match(self):
        self.assertEqual(self.codes(self.manager, self.note_p.code[:-1]), [])
        self.assertEqual(self.codes(self.manager, self.note_p.code[1:]), [])

    def test_ed07_unknown_code_returns_empty_page(self):
        self.assertEqual(self.codes(self.owner, "PG-KHONG-CO"), [])

    def test_ed07_empty_code_means_no_filter(self):
        response = client_for(self.owner).get(LIST, {"code": ""})
        self.assertEqual(response.json()["count"], 3)

    def test_ed07_courier_sees_own_note_but_other_couriers_code_gives_count_zero(self):
        self.assertEqual(self.codes(self.phuc, self.note_p.code), [self.note_p.code])
        other = client_for(self.phuc).get(LIST, {"code": self.note_l.code})
        self.assertEqual(other.status_code, 200)
        self.assertEqual(other.json()["count"], 0)
        self.assertEqual(other.json()["results"], [])
        unknown = client_for(self.phuc).get(LIST, {"code": "PG-KHONG-CO"})
        self.assertEqual(other.json(), unknown.json())  # giống hệt mã không tồn tại
        self.assertNotIn("0900000402", other.content.decode())

    def test_ed07_combines_with_status_filter(self):
        response = client_for(self.owner).get(LIST, {"code": self.note_p.code, "status": "DONE_NOT_A_STATUS"})
        self.assertEqual(response.json()["count"], 0)

    def test_ed07_without_permission_403_and_unauthenticated_401(self):
        from apps.common.tests.fixtures import make_user
        nobody = make_user("u_nobody")
        self.assertEqual(client_for(nobody).get(LIST, {"code": self.note_p.code}).status_code, 403)
        self.assertEqual(client_for(None).get(LIST, {"code": self.note_p.code}).status_code, 401)
