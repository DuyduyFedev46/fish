"""SHOP-3b-01 — API ERP mã giảm giá: phân quyền, kiểm dữ liệu, sửa theo hướng có lợi, tắt/bật, lượt, nhật ký."""
import datetime
import json
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.accounts.capabilities.tests.base import put_caps
from apps.accounts.models import AuditLog
from apps.catalog.models import Voucher
from apps.common.tests.fixtures import client_for
from apps.sales.models import SalesOrder, VoucherRedemption
from apps.sales.models import Customer

from .base import VoucherUsers, create_body, make_voucher

URL = "/api/catalog/vouchers/"
D = Decimal


def detail(pk, tail=""):
    return f"{URL}{pk}/{tail}"


class PermissionTests(VoucherUsers, TestCase):
    def setUp(self):
        self.make_users()
        self.voucher = make_voucher(owner=self.owner)

    def requests(self):
        pk = self.voucher.pk
        return [
            ("get", URL, None), ("post", URL, create_body(code="MOI12345")), ("get", detail(pk), None),
            ("patch", detail(pk), {"name": "Đổi tên"}), ("post", detail(pk, "disable/"), {"reason": "BUDGET"}),
            ("post", detail(pk, "enable/"), {}), ("get", detail(pk, "redemptions/"), None),
        ]

    def test_s3b_01_ac8_each_group_forbidden_and_data_unchanged(self):
        for user in (self.manager, self.warehouse, self.courier, self.service):
            client = client_for(user)
            for method, url, body in self.requests():
                with self.subTest(user=user.username, method=method, url=url):
                    kwargs = {"format": "json"} if body is not None else {}
                    response = getattr(client, method)(url, body, **kwargs) if body is not None else getattr(client, method)(url)
                    self.assertEqual(response.status_code, 403, response.content)
        self.assertEqual(Voucher.objects.count(), 1)
        self.voucher.refresh_from_db()
        self.assertEqual((self.voucher.name, self.voucher.is_active), ("Khai trương", True))
        self.assertFalse(AuditLog.objects.filter(action__in=["create_voucher", "update_voucher", "disable_voucher"]).exists())

    def test_unauthenticated_is_401_on_every_endpoint(self):
        from rest_framework.test import APIClient

        anonymous = APIClient()
        for method, url, body in self.requests():
            with self.subTest(method=method, url=url):
                response = getattr(anonymous, method)(url, body, format="json") if body is not None else getattr(anonymous, method)(url)
                self.assertEqual(response.status_code, 401)

    def test_s3b_01_ac6_delete_and_put_are_405_for_owner(self):
        self.assertEqual(self.owner_client.delete(detail(self.voucher.pk)).status_code, 405)
        self.assertEqual(self.owner_client.put(detail(self.voucher.pk), {"name": "x"}, format="json").status_code, 405)
        self.assertTrue(Voucher.objects.filter(pk=self.voucher.pk).exists())

    def test_s3b_01_ac9_owner_delegates_to_manager_then_revokes(self):
        self.assertEqual(client_for(self.manager).get(URL).status_code, 403)
        self.assertEqual(put_caps(self.owner_client, "manager", {"manage_voucher": True}).status_code, 200)
        manager_client = client_for(type(self.manager).objects.get(pk=self.manager.pk))
        self.assertEqual(manager_client.post(URL, create_body(code="MOI12345"), format="json").status_code, 201)
        self.assertEqual(put_caps(self.owner_client, "manager", {"manage_voucher": False}).status_code, 200)
        self.assertEqual(client_for(type(self.manager).objects.get(pk=self.manager.pk)).get(URL).status_code, 403)

    def test_only_owner_holds_the_permission_by_default(self):
        from apps.accounts.capabilities.tests.base import group_perms

        for group in ("manager", "warehouse_staff", "delivery_staff", "customer_service"):
            self.assertNotIn("catalog.manage_voucher", group_perms(group))
        self.assertIn("catalog.manage_voucher", group_perms("owner"))

    def test_capability_is_delegable_not_owner_only(self):
        from apps.accounts.capabilities import registry

        capability = registry.BY_KEY["manage_voucher"]
        self.assertEqual(capability.perms, ("catalog.manage_voucher",))
        self.assertFalse(capability.owner_only)


class CreateTests(VoucherUsers, TestCase):
    def setUp(self):
        self.make_users()

    def test_s3b_01_ac1_create_stores_utc_times_and_audits(self):
        body = create_body(starts_at="2026-10-15T08:00:00+07:00", ends_at="2026-10-31T23:59:00+07:00")
        response = self.owner_client.post(URL, body, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        data = response.json()
        self.assertEqual(data["code"], "CAVE10")
        self.assertEqual(data["starts_at"], "2026-10-15T01:00:00Z")
        self.assertEqual(data["ends_at"], "2026-10-31T16:59:00Z")
        self.assertEqual((data["kind"], data["value"], data["max_discount"], data["min_order_amount"]),
                         ("PERCENT", "10", "50000", "300000"))
        self.assertEqual((data["total_uses"], data["used_count"], data["held_count"]), (100, 0, 0))
        self.assertEqual((data["status"], data["is_active"], data["disabled_reason"]), ("scheduled", True, ""))
        self.assertEqual(
            set(data),
            {"id", "code", "name", "kind", "value", "max_discount", "min_order_amount", "starts_at", "ends_at",
             "total_uses", "used_count", "held_count", "status", "is_active", "disabled_reason", "disabled_note",
             "customer_terms", "created_at"},
        )
        log = AuditLog.objects.get(action="create_voucher")
        self.assertEqual(log.actor, self.owner)
        self.assertEqual(log.changes["value"]["to"], "10")
        self.assertEqual(log.changes["code"]["to"], "CAVE10")

    def test_code_is_normalized_to_upper_without_spaces(self):
        data = self.owner_client.post(URL, create_body(code="cave 10"), format="json").json()
        self.assertEqual(data["code"], "CAVE10")

    def test_s3b_01_ac2_duplicate_code_ignoring_case_is_400(self):
        make_voucher(owner=self.owner)
        response = self.owner_client.post(URL, create_body(code="cave10"), format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "VALIDATION")
        self.assertIn("code", response.json()["fields"])
        self.assertEqual(Voucher.objects.count(), 1)

    def test_s3b_01_ac3_each_invalid_case_names_its_own_field(self):
        cases = {
            "percent_without_cap": ({"max_discount": None}, "max_discount"),
            "percent_over_limit": ({"value": "60"}, "value"),
            "percent_zero": ({"value": "0"}, "value"),
            "ends_before_starts": ({"ends_at": "2020-01-01T00:00:00+07:00"}, "ends_at"),
            "code_with_phone_like_digits": ({"code": "A0900000123"}, "code"),
            "code_too_short": ({"code": "AB"}, "code"),
            "code_accent": ({"code": "GIẢM10"}, "code"),
            "amount_not_whole": ({"kind": "AMOUNT", "value": "1000.5"}, "value"),
            "min_order_negative": ({"min_order_amount": "-1"}, "min_order_amount"),
            "total_uses_zero": ({"total_uses": 0}, "total_uses"),
            "terms_with_phone": ({"customer_terms": "Gọi 0900 000 123"}, "customer_terms"),
            "terms_too_long": ({"customer_terms": "x" * 301}, "customer_terms"),
            "name_empty": ({"name": " "}, "name"),
            "bad_kind": ({"kind": "FREE"}, "kind"),
        }
        for label, (override, field) in cases.items():
            with self.subTest(label):
                response = self.owner_client.post(URL, create_body(**override), format="json")
                self.assertEqual(response.status_code, 400, response.content)
                self.assertEqual(response.json()["code"], "VALIDATION")
                self.assertIn(field, response.json()["fields"])
        self.assertEqual(Voucher.objects.count(), 0)

    def test_amount_voucher_ignores_max_discount(self):
        data = self.owner_client.post(
            URL, create_body(code="GIAM50K", kind="AMOUNT", value="50000", max_discount="1"), format="json"
        ).json()
        self.assertIsNone(data["max_discount"])

    def test_percent_limit_comes_from_setting(self):
        with self.settings(VOUCHER_MAX_PERCENT=D("20")):
            self.assertEqual(self.owner_client.post(URL, create_body(value="25"), format="json").status_code, 400)
            self.assertEqual(self.owner_client.post(URL, create_body(value="20"), format="json").status_code, 201)


class UpdateTests(VoucherUsers, TestCase):
    def setUp(self):
        self.make_users()

    def patch(self, voucher, body):
        return self.owner_client.patch(detail(voucher.pk), body, format="json")

    def test_before_start_everything_free_except_code_and_kind(self):
        v = make_voucher(owner=self.owner, starts_at=timezone.now() + datetime.timedelta(days=1),
                         ends_at=timezone.now() + datetime.timedelta(days=9))
        response = self.patch(v, {"value": "5", "min_order_amount": "500000", "total_uses": 10, "max_discount": "20000",
                                  "customer_terms": "Mới", "name": "Tên mới"})
        self.assertEqual(response.status_code, 200, response.content)
        v.refresh_from_db()
        self.assertEqual((v.value, v.min_order_amount, v.total_uses), (D("5"), D("500000"), 10))
        for body in ({"code": "KHAC1234"}, {"kind": "AMOUNT"}):
            with self.subTest(body=body):
                locked = self.patch(v, body)
                self.assertEqual(locked.status_code, 400)
                self.assertEqual(locked.json()["code"], "FIELD_LOCKED")
                self.assertEqual(locked.json()["fields"], list(body))

    def test_sending_the_unchanged_code_and_kind_is_not_locked(self):
        v = make_voucher(owner=self.owner)
        self.assertEqual(self.patch(v, {"code": "cave10", "kind": "PERCENT", "name": "Tên khác"}).status_code, 200)

    def test_s3b_01_ac4_running_voucher_favorable_changes_are_audited_before_after(self):
        v = make_voucher(owner=self.owner)
        new_end = (v.ends_at + datetime.timedelta(days=5)).isoformat()
        response = self.patch(v, {"ends_at": new_end, "total_uses": 150, "min_order_amount": "200000",
                                  "value": "12", "max_discount": "60000"})
        self.assertEqual(response.status_code, 200, response.content)
        v.refresh_from_db()
        self.assertEqual((v.total_uses, v.min_order_amount, v.value, v.max_discount),
                         (150, D("200000"), D("12"), D("60000")))
        log = AuditLog.objects.get(action="update_voucher")
        self.assertEqual(log.changes["total_uses"], {"from": 100, "to": 150})
        self.assertEqual(log.changes["min_order_amount"], {"from": "300000", "to": "200000"})

    def test_s3b_01_ac5_running_voucher_unfavorable_changes_are_rejected_with_fields(self):
        v = make_voucher(owner=self.owner)
        cases = {
            "min_order_amount": "400000", "value": "5", "max_discount": "40000", "total_uses": 20,
            "ends_at": (timezone.now() + datetime.timedelta(days=1)).isoformat(),
        }
        for field, value in cases.items():
            with self.subTest(field):
                response = self.patch(v, {field: value})
                self.assertEqual(response.status_code, 400, response.content)
                body = response.json()
                self.assertEqual((body["code"], body["fields"]), ("UNFAVORABLE_CHANGE", [field]))
                self.assertIn("Tắt mã này và tạo mã mới", body["detail"])
        v.refresh_from_db()
        self.assertEqual((v.value, v.total_uses, v.min_order_amount), (D("10"), 100, D("300000")))
        self.assertFalse(AuditLog.objects.filter(action="update_voucher").exists())

    def test_running_voucher_other_fields_are_locked(self):
        v = make_voucher(owner=self.owner)
        for body in ({"customer_terms": "Điều kiện khác"}, {"starts_at": (timezone.now() - datetime.timedelta(days=3)).isoformat()},
                     {"kind": "AMOUNT"}, {"code": "KHAC1234"}):
            with self.subTest(body=body):
                response = self.patch(v, body)
                self.assertEqual(response.json()["code"], "FIELD_LOCKED")

    def test_running_percent_cannot_be_raised_above_limit(self):
        v = make_voucher(owner=self.owner)
        response = self.patch(v, {"value": "60"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "VALIDATION")

    def test_name_is_free_even_while_running(self):
        v = make_voucher(owner=self.owner)
        self.assertEqual(self.patch(v, {"name": "Tên mới"}).status_code, 200)


class DisableEnableTests(VoucherUsers, TestCase):
    def setUp(self):
        self.make_users()
        self.voucher = make_voucher(owner=self.owner)

    def disable(self, body):
        return self.owner_client.post(detail(self.voucher.pk, "disable/"), body, format="json")

    def test_s3b_01_ac6_reason_required(self):
        for body in ({}, {"reason": "KHAC"}, {"reason": "OTHER"}, {"reason": "OTHER", "note": "  "},
                     {"reason": "OTHER", "note": "Gọi 0900000123"}, {"reason": "OTHER", "note": "x" * 201}):
            with self.subTest(body=body):
                response = self.disable(body)
                self.assertEqual(response.status_code, 400, response.content)
                self.assertEqual(response.json()["code"], "VALIDATION")
        self.voucher.refresh_from_db()
        self.assertTrue(self.voucher.is_active)

    def test_s3b_01_ac6_disable_keeps_the_voucher_and_audits_without_note_text(self):
        response = self.disable({"reason": "OTHER", "note": "Hết ngân sách quý này"})
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertEqual((data["is_active"], data["status"], data["disabled_reason"]), (False, "paused", "OTHER"))
        self.assertEqual(data["disabled_note"], "Hết ngân sách quý này")
        self.assertTrue(Voucher.objects.filter(pk=self.voucher.pk).exists())
        log = AuditLog.objects.get(action="disable_voucher")
        self.assertEqual(log.changes["reason_code"], "OTHER")
        self.assertTrue(log.changes["note_marker"])
        self.assertNotIn("ngân sách", json.dumps(log.changes, ensure_ascii=False))
        self.assertNotIn("ngân sách", log.note)

    def test_disable_is_idempotent_and_keeps_first_reason(self):
        self.disable({"reason": "BUDGET"})
        self.disable({"reason": "INCIDENT"})
        self.voucher.refresh_from_db()
        self.assertEqual(self.voucher.disabled_reason, "BUDGET")
        self.assertEqual(AuditLog.objects.filter(action="disable_voucher").count(), 1)

    def test_s3b_01_ac7_enable_when_still_valid(self):
        self.disable({"reason": "BUDGET"})
        response = self.owner_client.post(detail(self.voucher.pk, "enable/"), {}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertEqual((data["is_active"], data["status"], data["disabled_reason"], data["disabled_note"]),
                         (True, "running", "", ""))
        self.assertTrue(AuditLog.objects.filter(action="enable_voucher").exists())

    def test_s3b_01_ac7_enable_expired_is_400_expired(self):
        expired = make_voucher(owner=self.owner, code="HETHAN1", is_active=False,
                               starts_at=timezone.now() - datetime.timedelta(days=10),
                               ends_at=timezone.now() - datetime.timedelta(days=1))
        response = self.owner_client.post(detail(expired.pk, "enable/"), {}, format="json")
        self.assertEqual((response.status_code, response.json()["code"]), (400, "EXPIRED"))

    def test_enable_used_up_is_400_used_up(self):
        full = make_voucher(owner=self.owner, code="HETLUOT1", total_uses=1, is_active=False)
        order = make_order("0900000001")
        VoucherRedemption.objects.create(order=order, voucher=full, code=full.code, discount_amount=D("1000"),
                                         state=VoucherRedemption.State.HELD)
        response = self.owner_client.post(detail(full.pk, "enable/"), {}, format="json")
        self.assertEqual((response.status_code, response.json()["code"]), (400, "USED_UP"))


def make_order(phone, status=SalesOrder.Status.BOOKED):
    customer, _ = Customer.objects.get_or_create(phone=phone, defaults={"name": "Khách Giả"})
    return SalesOrder.objects.create(
        code=f"SO-{phone[-4:]}", customer=customer, status=status, delivery_address="1 Đường Thử", phone=phone,
        total_amount=D("100000"),
    )


class ListAndRedemptionTests(VoucherUsers, TestCase):
    def setUp(self):
        self.make_users()
        now = timezone.now()
        self.running = make_voucher(owner=self.owner, code="CHAYNGAY")
        self.scheduled = make_voucher(owner=self.owner, code="SAPCHAY1", starts_at=now + datetime.timedelta(days=2))
        self.paused = make_voucher(owner=self.owner, code="DATAMTAT", is_active=False)
        self.expired = make_voucher(owner=self.owner, code="HETHAN01", starts_at=now - datetime.timedelta(days=9),
                                    ends_at=now - datetime.timedelta(days=1))
        self.used_up = make_voucher(owner=self.owner, code="HETLUOT1", total_uses=2)
        for i, state in enumerate((VoucherRedemption.State.USED, VoucherRedemption.State.HELD)):
            VoucherRedemption.objects.create(order=make_order(f"090000010{i}"), voucher=self.used_up, code="HETLUOT1",
                                             discount_amount=D("1000"), state=state)

    def codes(self, query=""):
        response = self.owner_client.get(f"{URL}{query}")
        self.assertEqual(response.status_code, 200)
        return {row["code"] for row in response.json()["results"]}

    def test_list_filters_by_status_in_priority_order(self):
        self.assertEqual(self.codes("?status=running"), {"CHAYNGAY"})
        self.assertEqual(self.codes("?status=scheduled"), {"SAPCHAY1"})
        self.assertEqual(self.codes("?status=paused"), {"DATAMTAT"})
        self.assertEqual(self.codes("?status=expired"), {"HETHAN01"})
        self.assertEqual(self.codes("?status=used_up"), {"HETLUOT1"})
        self.assertEqual(len(self.codes()), 5)

    def test_row_status_and_counts_match_filters(self):
        rows = {r["code"]: r for r in self.owner_client.get(URL).json()["results"]}
        self.assertEqual({c: r["status"] for c, r in rows.items()},
                         {"CHAYNGAY": "running", "SAPCHAY1": "scheduled", "DATAMTAT": "paused",
                          "HETHAN01": "expired", "HETLUOT1": "used_up"})
        self.assertEqual((rows["HETLUOT1"]["used_count"], rows["HETLUOT1"]["held_count"]), (1, 1))

    def test_list_is_paginated_with_contract_envelope(self):
        body = self.owner_client.get(URL).json()
        self.assertEqual({"count", "next", "previous", "results"}, set(body))
        self.assertEqual(body["count"], 5)
        self.assertEqual(self.owner_client.get(f"{URL}?page=2").status_code, 404)  # 5 dòng < 1 trang

    def test_s3b_01_ac10_redemptions_have_exactly_four_keys_and_no_personal_data(self):
        response = self.owner_client.get(detail(self.used_up.pk, "redemptions/"))
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["count"], 2)
        for row in body["results"]:
            self.assertEqual(set(row), {"order_code", "discount_amount", "at", "state"})
            self.assertIn(row["state"], {"held", "used", "released"})
            self.assertTrue(row["at"].endswith("Z"))
        text = response.content.decode()
        for forbidden in ("0900000100", "0900000101", "Khách Giả", "Đường Thử", "unit_cost", "profit", "landed", "phone"):
            self.assertNotIn(forbidden, text)

    def test_voucher_json_has_no_cost_or_customer_fields(self):
        def keys(node):
            if isinstance(node, dict):
                return set(node) | {k for v in node.values() for k in keys(v)}
            if isinstance(node, list):
                return {k for v in node for k in keys(v)}
            return set()

        found = keys(self.owner_client.get(URL).json())
        for forbidden in ("purchase_rate", "landed_unit_cost", "unit_cost", "profit", "margin", "phone", "customer",
                          "address", "created_by", "name_of_customer"):
            self.assertNotIn(forbidden, found)

    def test_redemption_state_dates_follow_state(self):
        VoucherRedemption.objects.filter(state="USED").update(used_at=timezone.now())
        row = [r for r in self.owner_client.get(detail(self.used_up.pk, "redemptions/")).json()["results"]
               if r["state"] == "used"][0]
        self.assertTrue(row["at"])


class IsActiveLockedTests(VoucherUsers, TestCase):
    def test_is_active_via_patch_says_use_disable_enable_even_before_start(self):
        self.make_users()
        v = make_voucher(owner=self.owner, starts_at=timezone.now() + datetime.timedelta(days=1),
                         ends_at=timezone.now() + datetime.timedelta(days=9))
        response = self.owner_client.patch(detail(v.pk), {"is_active": False}, format="json")
        body = response.json()
        self.assertEqual((response.status_code, body["code"], body["fields"]), (400, "FIELD_LOCKED", ["is_active"]))
        self.assertIn("Tắt mã", body["detail"])
        self.assertNotIn("đã bắt đầu", body["detail"])
        v.refresh_from_db()
        self.assertTrue(v.is_active)
