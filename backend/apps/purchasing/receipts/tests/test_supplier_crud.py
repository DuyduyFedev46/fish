"""
B3 — `/api/purchasing/suppliers/`: quyền, lọc, thêm/sửa (F1b, "Ngừng hợp tác"), audit không chứa SĐT.
Quyền Tầng 1 (BR-PQ): xem = owner, manager, warehouse_staff; thêm/sửa = owner, manager. Mọi dữ liệu là giả.
"""
import threading

from django.contrib.auth.models import User
from django.core.management import call_command
from django.db import connections
from django.test import TransactionTestCase

from apps.accounts import roles
from apps.accounts.models import AuditLog
from apps.common.exceptions import BusinessError
from apps.common.tests.fixtures import client_for, make_user
from apps.purchasing.models import Supplier
from apps.purchasing.receipts import supplier_services

from .api_base import ReceiptsApiBase

URL = "/api/purchasing/suppliers/"
PHONE = "0900000907"  # SĐT giả
PHONE_NEW = "0900000908"


class SupplierPermissionTests(ReceiptsApiBase):
    def test_supplier_read_permission_matrix(self):
        for user, expected in (
            (self.owner, 200), (self.manager, 200), (self.warehouse_staff, 200),
            (self.courier, 403), (self.customer_service, 403), (self.no_group, 403), (None, 401),
        ):
            for path in ("", f"{self.supplier.pk}/"):
                self.assertEqual(
                    client_for(user).get(f"{URL}{path}").status_code, expected,
                    f"{getattr(user, 'username', 'anon')} {path}",
                )

    def test_supplier_write_permission_matrix(self):
        for user, expected in (
            (self.owner, 201), (self.manager, 201), (self.warehouse_staff, 403),
            (self.courier, 403), (self.customer_service, 403), (None, 401),
        ):
            body = {"name": f"Vựa thử {getattr(user, 'username', 'anon')}"}
            self.assertEqual(client_for(user).post(URL, body, format="json").status_code, expected)
        for user, expected in (
            (self.owner, 200), (self.manager, 200), (self.warehouse_staff, 403),
            (self.courier, 403), (self.customer_service, 403), (None, 401),
        ):
            resp = client_for(user).patch(f"{URL}{self.other_supplier.pk}/", {"note": "x"}, format="json")
            self.assertEqual(resp.status_code, expected, getattr(user, "username", "anon"))

    def test_supplier_forbidden_write_changes_nothing(self):
        before = Supplier.objects.count()
        resp = client_for(self.warehouse_staff).post(URL, {"name": "Không được"}, format="json")
        self.assertEqual(resp.status_code, 403)
        client_for(self.warehouse_staff).patch(f"{URL}{self.supplier.pk}/", {"name": "Đổi bậy"}, format="json")
        self.supplier.refresh_from_db()
        self.assertEqual(Supplier.objects.count(), before)
        self.assertEqual(self.supplier.name, "Đầu mối A")


class SupplierMethodTests(ReceiptsApiBase):
    """Nhà cung cấp không xoá (BR-PQ-10): "ngừng hợp tác" là `PATCH is_active=false`. PUT không dùng, chỉ PATCH."""

    def test_supplier_delete_is_405_for_everyone_and_deletes_nothing(self):
        before = Supplier.objects.count()
        for user in (self.owner, self.manager, self.warehouse_staff):
            for target in (self.supplier, self.other_supplier):  # có phiếu / chưa có phiếu
                resp = client_for(user).delete(f"{URL}{target.pk}/")
                self.assertEqual(resp.status_code, 405, user.username)
        self.assertEqual(Supplier.objects.count(), before)

    def test_supplier_put_is_405(self):
        resp = client_for(self.owner).put(
            f"{URL}{self.supplier.pk}/", {"name": "Đổi bằng PUT"}, format="json"
        )
        self.assertEqual(resp.status_code, 405)
        self.supplier.refresh_from_db()
        self.assertEqual(self.supplier.name, "Đầu mối A")

    def test_supplier_allowed_methods_are_get_post_patch(self):
        resp = client_for(self.owner).options(f"{URL}{self.supplier.pk}/")
        allowed = {m.strip() for m in resp["Allow"].split(",")}
        self.assertEqual(allowed, {"GET", "PATCH", "HEAD", "OPTIONS"})


class SupplierFilterTests(ReceiptsApiBase):
    def setUp(self):
        super().setUp()
        self.company = Supplier.objects.create(name="Công ty Biển Xanh", supplier_type="COMPANY", phone=PHONE)
        self.inactive = Supplier.objects.create(name="Ghe Cũ", is_active=False)

    def names(self, query):
        resp = client_for(self.owner).get(f"{URL}{query}")
        self.assertEqual(resp.status_code, 200, query)
        return [row["name"] for row in resp.json()["results"]]

    def test_supplier_list_is_sorted_by_name_and_unfiltered_by_default(self):
        self.assertEqual(self.names(""), sorted(["Đầu mối A", "Vựa B", "Công ty Biển Xanh", "Ghe Cũ"]))

    def test_supplier_filter_is_active(self):
        self.assertEqual(self.names("?is_active=false"), ["Ghe Cũ"])
        self.assertNotIn("Ghe Cũ", self.names("?is_active=1"))
        self.assertEqual(len(self.names("?is_active=true")), 3)

    def test_supplier_filter_supplier_type(self):
        self.assertEqual(self.names("?supplier_type=COMPANY"), ["Công ty Biển Xanh"])
        self.assertEqual(len(self.names("?supplier_type=INDIVIDUAL")), 3)

    def test_supplier_filter_q_matches_name_case_insensitive(self):
        self.assertEqual(self.names("?q=biển"), ["Công ty Biển Xanh"])
        self.assertEqual(self.names("?q=VỰA"), ["Vựa B"])

    def test_supplier_filter_q_matches_phone(self):
        self.assertEqual(self.names(f"?q={PHONE[-4:]}"), ["Công ty Biển Xanh"])

    def test_supplier_filters_combine(self):
        self.assertEqual(self.names("?supplier_type=INDIVIDUAL&is_active=false"), ["Ghe Cũ"])
        self.assertEqual(self.names("?supplier_type=COMPANY&is_active=false"), [])

    def test_supplier_empty_params_do_not_filter(self):
        self.assertEqual(len(self.names("?q=&supplier_type=&is_active=")), 4)

    def test_supplier_invalid_filters_return_400_without_echoing_value(self):
        for query in ("?is_active=maybe", "?supplier_type=ROBOT", "?q=" + "a" * 101):
            resp = client_for(self.owner).get(f"{URL}{query}")
            self.assertEqual(resp.status_code, 400, query)
            self.assertEqual(resp.json()["code"], "INVALID_FILTER")
            self.assertNotIn(query.split("=", 1)[1], resp.json()["detail"])

    def test_supplier_filter_sql_wildcards_are_literal_text(self):
        self.assertEqual(self.names("?q=%25"), [])  # "%" không khớp mọi tên


class SupplierWriteTests(ReceiptsApiBase):
    def test_supplier_create_returns_201_and_saves(self):
        resp = client_for(self.owner).post(
            URL,
            {"name": "  Ghe Tư Hải  ", "supplier_type": "COMPANY", "phone": PHONE, "note": "mối ruột"},
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        body = resp.json()
        self.assertEqual(body["name"], "Ghe Tư Hải")  # cắt khoảng trắng hai đầu
        self.assertEqual(body["supplier_type_label"], "Doanh nghiệp")
        self.assertTrue(body["is_active"])
        self.assertEqual(Supplier.objects.get(pk=body["id"]).phone, PHONE)

    def test_supplier_create_defaults(self):
        body = client_for(self.manager).post(URL, {"name": "Vựa Mới"}, format="json").json()
        self.assertEqual((body["supplier_type"], body["phone"], body["note"], body["is_active"]),
                         ("INDIVIDUAL", "", "", True))

    def test_supplier_create_duplicate_name_is_400(self):
        for name in ("Đầu mối A", "  đầu mối a "):
            resp = client_for(self.owner).post(URL, {"name": name}, format="json")
            self.assertEqual(resp.status_code, 400, name)
            self.assertIn("name", resp.json())
        self.assertEqual(Supplier.objects.filter(name__iexact="Đầu mối A").count(), 1)

    def test_supplier_update_duplicate_name_is_400_but_own_name_is_ok(self):
        resp = client_for(self.owner).patch(f"{URL}{self.other_supplier.pk}/", {"name": "Đầu mối A"}, format="json")
        self.assertEqual(resp.status_code, 400)
        same = client_for(self.owner).patch(f"{URL}{self.supplier.pk}/", {"name": "Đầu mối A", "note": "n"}, format="json")
        self.assertEqual(same.status_code, 200)

    def test_supplier_create_invalid_input_is_400(self):
        for body in ({}, {"name": "   "}, {"name": "x" * 201}, {"name": "ok", "supplier_type": "ROBOT"},
                     {"name": "ok", "phone": "9" * 21}):
            resp = client_for(self.owner).post(URL, body, format="json")
            self.assertEqual(resp.status_code, 400, body)

    def test_supplier_stop_cooperating_is_patch_is_active_false(self):
        resp = client_for(self.manager).patch(f"{URL}{self.supplier.pk}/", {"is_active": False}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json()["is_active"])
        self.supplier.refresh_from_db()
        self.assertFalse(self.supplier.is_active)

    def test_supplier_update_keeps_receipts_and_ignores_aggregate_fields(self):
        resp = client_for(self.owner).patch(
            f"{URL}{self.supplier.pk}/",
            {"receipt_count": 99, "purchase_total": "1", "last_received_at": "2020-01-01T00:00:00Z"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["receipt_count"], 1)
        self.assertEqual(resp.json()["purchase_total"], "1634570.00")


class SupplierAuditTests(ReceiptsApiBase):
    def logs(self, action):
        return list(AuditLog.objects.filter(action=action))

    def assert_no_phone_in_audit(self, log):
        blob = f"{log.changes} {log.note} {log.object_repr}"
        for phone in (PHONE, PHONE_NEW):
            self.assertNotIn(phone, blob)

    def test_supplier_create_writes_audit_without_phone(self):
        resp = client_for(self.manager).post(URL, {"name": "Ghe Tư Hải", "phone": PHONE}, format="json")
        log = self.logs("supplier_create")[0]
        self.assertEqual(log.actor, self.manager)
        self.assertEqual(log.object_id, str(resp.json()["id"]))
        self.assertEqual(log.model_name, "purchasing.Supplier")
        self.assert_no_phone_in_audit(log)

    def test_supplier_update_audit_lists_field_names_only(self):
        self.supplier.phone = PHONE
        self.supplier.save()
        client_for(self.owner).patch(
            f"{URL}{self.supplier.pk}/", {"phone": PHONE_NEW, "note": "ghi chú bí mật", "is_active": False},
            format="json",
        )
        log = self.logs("supplier_update")[0]
        self.assertEqual(sorted(log.changes["fields"]), ["is_active", "note", "phone"])
        self.assert_no_phone_in_audit(log)
        self.assertNotIn("bí mật", str(log.changes))

    def test_supplier_update_without_real_change_writes_no_audit(self):
        client_for(self.owner).patch(f"{URL}{self.supplier.pk}/", {"name": "Đầu mối A"}, format="json")
        self.assertEqual(self.logs("supplier_update"), [])

    def test_supplier_failed_write_writes_no_audit(self):
        client_for(self.owner).post(URL, {"name": "Đầu mối A"}, format="json")
        self.assertEqual(self.logs("supplier_create"), [])


class SupplierNameRaceTests(ReceiptsApiBase):
    """
    B11-1: kiểm trùng tên phải nằm cùng khoá tuần tự với lệnh ghi, nếu không hai yêu cầu cùng lúc (bấm đúp) cùng qua
    bước kiểm rồi cùng ghi. Không có ràng buộc unique ở DB (không thêm migration), nên service tự kiểm lại trong khoá.
    """

    def test_supplier_service_create_rechecks_duplicate_name_inside_the_lock(self):
        # Mô phỏng yêu cầu thua cuộc: serializer đã cho qua (lúc đó chưa có tên), service gọi sau khi yêu cầu kia ghi xong.
        supplier_services.create_supplier(data={"name": "Ghe Đua Tranh"}, actor=self.owner)
        with self.assertRaises(BusinessError) as ctx:
            supplier_services.create_supplier(data={"name": "  ghe đua tranh "}, actor=self.owner)
        self.assertEqual(ctx.exception.code, "SUPPLIER_NAME_TAKEN")
        self.assertEqual(Supplier.objects.filter(name="Ghe Đua Tranh").count(), 1)
        self.assertEqual(Supplier.objects.count(), 3)  # 2 nhà cung cấp của setUp + 1
        self.assertEqual(AuditLog.objects.filter(action="supplier_create").count(), 1)

    def test_supplier_service_update_rechecks_duplicate_name_inside_the_lock(self):
        with self.assertRaises(BusinessError) as ctx:
            supplier_services.update_supplier(supplier=self.other_supplier, data={"name": "ĐẦU MỐI A"}, actor=self.owner)
        self.assertEqual(ctx.exception.code, "SUPPLIER_NAME_TAKEN")
        self.other_supplier.refresh_from_db()
        self.assertEqual(self.other_supplier.name, "Vựa B")
        self.assertEqual(AuditLog.objects.filter(action="supplier_update").count(), 0)

    def test_supplier_service_update_allows_recasing_own_name(self):
        supplier_services.update_supplier(supplier=self.supplier, data={"name": "ĐẦU MỐI A"}, actor=self.owner)
        self.supplier.refresh_from_db()
        self.assertEqual(self.supplier.name, "ĐẦU MỐI A")

    def test_supplier_race_loser_gets_400_over_http(self):
        # Chen bản ghi trùng tên sau khi serializer đã kiểm: bỏ qua `validate_name` để chỉ thử lớp kiểm trong service.
        from unittest import mock

        supplier_services.create_supplier(data={"name": "Ghe Song Song"}, actor=self.owner)
        with mock.patch("apps.purchasing.receipts.serializers.name_taken", return_value=False):
            resp = client_for(self.owner).post(URL, {"name": "Ghe Song Song"}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], "SUPPLIER_NAME_TAKEN")
        self.assertEqual(Supplier.objects.filter(name="Ghe Song Song").count(), 1)


class SupplierNameConcurrencyTests(TransactionTestCase):
    """6 luồng cùng tạo một tên: đúng 1 thành công, 5 bị 400 (B11-1). Chạy được trên SQLite nhờ khoá tiến trình;
    trên Postgres khoá là `pg_advisory_xact_lock` (⏸ chưa chạy được ở đây: chờ kiểm trên Postgres staging)."""

    def setUp(self):
        # Một số test migration (accounts/audit/test_s03_migration) để schema ở bản cũ sau khi chạy; đưa về bản mới nhất
        # để test này không phụ thuộc thứ tự chạy.
        call_command("migrate", verbosity=0, interactive=False)

    def test_supplier_concurrent_create_same_name_only_one_wins(self):
        owner = User.objects.create_user("race_owner", password="x")  # không cần nhóm; TransactionTestCase đã xoá dữ liệu nhóm
        barrier = threading.Barrier(6)
        results = []

        def worker():
            try:
                barrier.wait()
                supplier_services.create_supplier(data={"name": "Ghe Đua Tranh 1"}, actor=owner)
                results.append("ok")
            except BusinessError as exc:
                results.append(exc.code)
            except Exception as exc:  # noqa: BLE001 - mọi lỗi khác là bug cần thấy trong kết quả
                results.append(f"error:{type(exc).__name__}:{str(exc)[:80]}")
            finally:
                connections.close_all()

        threads = [threading.Thread(target=worker) for _ in range(6)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(sorted(results), ["SUPPLIER_NAME_TAKEN"] * 5 + ["ok"])
        self.assertEqual(Supplier.objects.filter(name="Ghe Đua Tranh 1").count(), 1)
