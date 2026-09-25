"""
S10 — Danh sách và chi tiết đơn (UC-02, BR-BH-03/06, BR-PQ-12/15).

Contract: 02-stories.md mục S10. Giá vốn (`allocations[].unit_cost`) KHÔNG có key với
người thiếu `inventory.view_costprice`; NV giao chỉ thấy đơn của phiếu mình (S5).
"""
import datetime
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.catalog.models import Item, ItemGroup, ItemPrice, PriceList
from apps.common.tests.fixtures import client_for, make_user
from apps.delivery.models import DeliveryNote
from apps.inventory.batches import services as batch_services
from apps.inventory.models import Warehouse
from apps.purchasing.models import Supplier
from apps.sales.models import Customer, PaymentTransaction, Refund, SalesOrder
from apps.sales.orders import services as order_services
from apps.sales.payments import services as payment_services

SENSITIVE_KEYS = {"unit_cost", "purchase_rate", "landed_unit_cost"}
LIST_KEYS = {
    "id", "code", "status", "status_label", "customer_name", "customer_phone",
    "total_amount", "created_at", "reserved_until", "delivery_status", "needs_attention",
}


def find_keys(data, keys):
    """Quét đệ quy JSON, trả tập key nhạy cảm tìm thấy."""
    found = set()
    if isinstance(data, dict):
        for k, v in data.items():
            if k in keys:
                found.add(k)
            found |= find_keys(v, keys)
    elif isinstance(data, list):
        for v in data:
            found |= find_keys(v, keys)
    return found


class OrderApiBase(TestCase):
    def setUp(self):
        g = ItemGroup.objects.create(name="Hải sản")
        self.sup = Supplier.objects.create(name="Đầu mối A")
        self.wh = Warehouse.objects.create(name="Kho chính")
        self.pl = PriceList.objects.create(name="Bán lẻ", is_default=True)
        today = timezone.localdate()
        self.item = Item.objects.create(code="TOM-SU-1", name="Tôm sú loại 1", item_group=g)
        ItemPrice.objects.create(
            price_list=self.pl, item=self.item, rate=Decimal("270000"),
            valid_from=today - datetime.timedelta(days=1), valid_upto=None,
        )
        self.batch = batch_services.create_batch(
            item=self.item, supplier=self.sup, warehouse=self.wh, received_date=today,
            qty=Decimal("100"), purchase_rate=Decimal("180000"),
        )
        batch_services.publish_batch(batch=self.batch, actor=None)
        self.batch.refresh_from_db()

        self.chu = make_user("chu1", "chu")
        self.ql = make_user("ql1", "quan_ly")
        self.kho = make_user("kho1", "nv_kho")
        self.giao = make_user("giao1", "nv_giao")
        self.nobody = make_user("nobody")

    def _order(self, phone="0901234567", qty="2", name="Chị Hoa"):
        return order_services.create_order(
            customer_phone=phone, customer_name=name, delivery_address="12 Lê Lợi, Vũng Tàu",
            phone=phone, lines=[{"item_code": self.item.code, "qty": Decimal(qty)}],
        )

    def _paid_order(self, phone="0901234567", txn="FT2626712345"):
        order = self._order(phone=phone)
        payment_services.confirm_payment(
            order=order, bank_txn_id=txn, amount=order.total_amount, received_at=timezone.now(),
        )
        order.refresh_from_db()
        return order


class S10ListTests(OrderApiBase):
    def _bulk(self, n, status, day, phone_prefix="0912"):
        cust = Customer.objects.create(phone=f"{phone_prefix}000000", name="Khách")
        ids = []
        for i in range(n):
            o = SalesOrder.objects.create(
                code=f"DH-{status[:2]}-{day:%m%d}-{i:03d}", customer=cust, status=status,
                delivery_address="x", phone=f"{phone_prefix}{i:06d}", total_amount=Decimal("100000"),
            )
            ids.append(o.pk)
        created = timezone.make_aware(datetime.datetime.combine(day, datetime.time(10, 0)))
        SalesOrder.objects.filter(pk__in=ids).update(created_at=created)
        return ids

    def test_s10_ac1_loc_trang_thai_va_ngay_phan_trang_20(self):
        d24 = datetime.date(2026, 9, 24)
        d23 = datetime.date(2026, 9, 23)
        booked24 = self._bulk(25, SalesOrder.Status.BOOKED, d24)
        self._bulk(10, SalesOrder.Status.PROCESSING, d24, phone_prefix="0913")
        self._bulk(10, SalesOrder.Status.BOOKED, d23, phone_prefix="0914")

        c = client_for(self.ql)
        resp = c.get("/api/sales/orders/?status=BOOKED&date_from=2026-09-24&date_to=2026-09-24")
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertEqual(body["count"], 25)
        self.assertEqual(len(body["results"]), 20)
        self.assertIsNotNone(body["next"])
        self.assertIsNone(body["previous"])
        page2 = c.get(
            "/api/sales/orders/?status=BOOKED&date_from=2026-09-24&date_to=2026-09-24&page=2"
        ).json()
        got = {r["id"] for r in body["results"]} | {r["id"] for r in page2["results"]}
        self.assertEqual(got, set(booked24))
        self.assertTrue(all(r["status"] == "BOOKED" for r in body["results"]))

    def test_s10_ac1_loc_nhieu_trang_thai_cach_nhau_dau_phay(self):
        d = datetime.date(2026, 9, 24)
        self._bulk(2, SalesOrder.Status.BOOKED, d)
        self._bulk(3, SalesOrder.Status.PAID, d, phone_prefix="0913")
        self._bulk(4, SalesOrder.Status.COMPLETED, d, phone_prefix="0914")
        resp = client_for(self.chu).get("/api/sales/orders/?status=BOOKED,PAID")
        self.assertEqual(resp.json()["count"], 5)

    def test_s10_ac1_ngay_sai_dinh_dang_400(self):
        resp = client_for(self.chu).get("/api/sales/orders/?date_from=24-09-2026")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("detail", resp.json())
        self.assertIn("code", resp.json())

    def test_s10_ac2_tim_theo_sdt_mot_phan(self):
        target = self._order(phone="0901234567")
        self._order(phone="0987654321", name="Anh Ba")
        resp = client_for(self.kho).get("/api/sales/orders/?q=0901234")
        self.assertEqual([r["id"] for r in resp.json()["results"]], [target.pk])

    def test_s10_ac2_tim_theo_ma_don_mot_phan(self):
        target = self._order(phone="0901234567")
        self._order(phone="0987654321", name="Anh Ba")
        part = target.code[-5:]
        resp = client_for(self.kho).get(f"/api/sales/orders/?q={part}")
        self.assertIn(target.pk, [r["id"] for r in resp.json()["results"]])
        self.assertEqual(resp.json()["count"], 1)

    def test_s10_list_dung_hinh_contract(self):
        order = self._order()
        paid = self._paid_order(phone="0908888888", txn="FTLIST1")
        resp = client_for(self.ql).get("/api/sales/orders/")
        rows = {r["id"]: r for r in resp.json()["results"]}
        row = rows[order.pk]
        self.assertEqual(set(row.keys()), LIST_KEYS)
        self.assertEqual(row["status_label"], "Giữ chỗ")
        self.assertEqual(row["customer_name"], "Chị Hoa")
        self.assertEqual(row["customer_phone"], "0901234567")
        self.assertEqual(row["total_amount"], "540000")
        self.assertIsNotNone(row["reserved_until"])
        self.assertIsNone(row["delivery_status"])
        self.assertFalse(row["needs_attention"])
        self.assertEqual(rows[paid.pk]["delivery_status"], "PREPARING")

    def test_s10_list_needs_attention_khi_co_giao_dich_lech(self):
        order = self._order()
        payment_services.confirm_payment(
            order=order, bank_txn_id="FTLOW", amount=Decimal("100"), received_at=timezone.now(),
        )
        row = client_for(self.chu).get("/api/sales/orders/").json()["results"][0]
        self.assertTrue(row["needs_attention"])

    def test_s10_ac6_khong_co_view_salesorder_403(self):
        order = self._order()
        c = client_for(self.nobody)
        self.assertEqual(c.get("/api/sales/orders/").status_code, 403)
        self.assertEqual(c.get(f"/api/sales/orders/{order.pk}/").status_code, 403)

    def test_s10_chua_dang_nhap_401(self):
        self.assertEqual(client_for(None).get("/api/sales/orders/").status_code, 401)

    def test_s10_list_khong_ro_gia_von(self):
        self._paid_order()
        for user in (self.ql, self.kho, self.chu):
            resp = client_for(user).get("/api/sales/orders/")
            self.assertEqual(find_keys(resp.json(), SENSITIVE_KEYS), set(), user.username)


class S10DetailTests(OrderApiBase):
    def test_s10_ac3_quan_ly_nv_kho_co_phan_bo_lo_khong_co_unit_cost(self):
        order = self._paid_order()
        for user in (self.ql, self.kho):
            resp = client_for(user).get(f"/api/sales/orders/{order.pk}/")
            self.assertEqual(resp.status_code, 200, resp.content)
            body = resp.json()
            self.assertEqual(len(body["allocations"]), 1)
            alloc = body["allocations"][0]
            self.assertEqual(alloc["batch_id"], self.batch.batch_id)
            self.assertEqual(alloc["qty_kg"], "2.000")
            self.assertEqual(alloc["line_no"], 1)
            self.assertNotIn("unit_cost", alloc)
            self.assertEqual(find_keys(body, SENSITIVE_KEYS), set(), user.username)

    def test_s10_ac3_don_giu_cho_cung_khong_ro_unit_cost(self):
        order = self._order()
        body = client_for(self.kho).get(f"/api/sales/orders/{order.pk}/").json()
        self.assertEqual(len(body["allocations"]), 1)
        self.assertEqual(find_keys(body, SENSITIVE_KEYS), set())

    def test_s10_ac4_chu_thay_unit_cost(self):
        order = self._paid_order()
        body = client_for(self.chu).get(f"/api/sales/orders/{order.pk}/").json()
        self.assertEqual(body["allocations"][0]["unit_cost"], "180000")

    def test_s10_ac5_don_giu_cho_co_reserved_until(self):
        order = self._order()
        body = client_for(self.ql).get(f"/api/sales/orders/{order.pk}/").json()
        self.assertEqual(body["status"], "BOOKED")
        self.assertIsNotNone(body["reserved_until"])
        self.assertEqual(
            datetime.datetime.fromisoformat(body["reserved_until"]), order.booked_expires_at
        )

    def test_s10_chi_tiet_day_du_tien_giao_hoan(self):
        order = self._paid_order()
        note = DeliveryNote.objects.get(sales_invoice=order.invoice)
        note.assigned_to = self.giao
        note.save(update_fields=["assigned_to"])
        from apps.accounts.models import StaffProfile
        StaffProfile.objects.create(user=self.giao, phone="0908111222", display_name="Anh Tư")
        Refund.objects.create(sales_invoice=order.invoice, amount=Decimal("540000"), created_by=self.chu)

        body = client_for(self.ql).get(f"/api/sales/orders/{order.pk}/").json()
        self.assertEqual(body["code"], order.code)
        self.assertEqual(body["status"], "PROCESSING")
        self.assertEqual(body["customer"], {
            "name": "Chị Hoa", "phone": "0901234567", "address": "12 Lê Lợi, Vũng Tàu",
        })
        self.assertEqual(body["lines"], [{
            "no": 1, "item_code": "TOM-SU-1", "item_name": "Tôm sú loại 1", "qty_kg": "2.000",
            "unit_price": "270000", "discount": "0", "line_total": "540000",
        }])
        self.assertEqual(body["invoice"]["id"], order.invoice.pk)
        self.assertEqual(body["invoice"]["code"], order.invoice.code)
        self.assertIn("issued_at", body["invoice"])
        self.assertEqual(len(body["payments"]), 1)
        pay = body["payments"][0]
        self.assertEqual(pay["bank_txn_id"], "FT2626712345")
        self.assertEqual(pay["amount"], "540000")
        self.assertEqual(pay["match_status"], "MATCHED")
        self.assertIn("received_at", pay)
        self.assertEqual(body["delivery"]["id"], note.pk)
        self.assertEqual(body["delivery"]["code"], note.code)
        self.assertEqual(body["delivery"]["status"], "PREPARING")
        self.assertEqual(body["delivery"]["failed_attempts"], 0)
        self.assertEqual(body["delivery"]["assigned_to"], {
            "id": self.giao.pk, "display_name": "Anh Tư", "phone": "0908111222",
        })
        self.assertEqual(body["refunds"], [{
            "id": Refund.objects.get().pk, "amount": "540000", "status": "PENDING",
            "status_label": "Chờ hoàn", "bank_txn_ref": "",  # L7: thêm nhãn
        }])
        self.assertIn("available_actions", body)

    def test_s10_chi_tiet_don_giu_cho_chua_co_hoa_don(self):
        order = self._order()
        body = client_for(self.ql).get(f"/api/sales/orders/{order.pk}/").json()
        self.assertIsNone(body["invoice"])
        self.assertIsNone(body["delivery"])
        self.assertEqual(body["payments"], [])
        self.assertEqual(body["refunds"], [])

    def test_s10_available_actions_theo_luat_va_quyen(self):
        booked = self._order()
        paid = self._paid_order(phone="0908888888", txn="FTX2")

        def actions(user, order):
            return client_for(user).get(f"/api/sales/orders/{order.pk}/").json()["available_actions"]

        self.assertEqual(actions(self.chu, booked), ["confirm_payment"])
        self.assertEqual(actions(self.ql, booked), [])  # S11-AC7
        self.assertEqual(actions(self.kho, booked), [])
        self.assertEqual(actions(self.chu, paid), ["cancel", "create_refund"])
        self.assertEqual(actions(self.ql, paid), ["cancel", "create_refund"])
        self.assertEqual(actions(self.kho, paid), [])

    def test_s10_available_actions_hoan_het_thi_khong_con_create_refund(self):
        paid = self._paid_order()
        Refund.objects.create(sales_invoice=paid.invoice, amount=paid.total_amount, created_by=self.chu)
        body = client_for(self.chu).get(f"/api/sales/orders/{paid.pk}/").json()
        self.assertNotIn("create_refund", body["available_actions"])

    def test_s10_available_actions_don_tu_huy_chu_van_ghi_duoc_tien(self):
        order = self._order()
        SalesOrder.objects.filter(pk=order.pk).update(status=SalesOrder.Status.AUTO_CANCELLED)
        body = client_for(self.chu).get(f"/api/sales/orders/{order.pk}/").json()
        self.assertEqual(body["available_actions"], ["confirm_payment"])

    def test_s10_s5_nv_giao_ngoai_pham_vi_404_trong_pham_vi_200(self):
        mine = self._paid_order()
        other = self._paid_order(phone="0908888888", txn="FTX3")
        DeliveryNote.objects.filter(sales_invoice=mine.invoice).update(assigned_to=self.giao)
        c = client_for(self.giao)
        self.assertEqual(c.get(f"/api/sales/orders/{other.pk}/").status_code, 404)
        resp = c.get(f"/api/sales/orders/{mine.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(find_keys(resp.json(), SENSITIVE_KEYS), set())
        self.assertEqual(resp.json()["available_actions"], [])
        self.assertEqual([r["id"] for r in c.get("/api/sales/orders/").json()["results"]], [mine.pk])

    def test_s10_khong_ton_tai_404(self):
        self.assertEqual(client_for(self.chu).get("/api/sales/orders/999999/").status_code, 404)

    def test_s10_payment_underpaid_hien_trong_chi_tiet(self):
        order = self._order()
        payment_services.confirm_payment(
            order=order, bank_txn_id="FTLOW", amount=Decimal("300000"), received_at=timezone.now(),
        )
        body = client_for(self.chu).get(f"/api/sales/orders/{order.pk}/").json()
        self.assertEqual(body["payments"][0]["match_status"], PaymentTransaction.MatchStatus.UNDERPAID)
        self.assertEqual(body["payments"][0]["amount"], "300000")


class S10QueryCountTests(OrderApiBase):
    def test_s10_list_va_chi_tiet_khong_n_cong_1(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        def count(path):
            c = client_for(self.chu)
            with CaptureQueriesContext(connection) as ctx:
                self.assertEqual(c.get(path).status_code, 200)
            return len(ctx.captured_queries)

        first = self._paid_order(phone="0900000001", txn="Q1")
        count("/api/sales/orders/")  # làm nóng cache quyền của user (không phụ thuộc số đơn)
        few_list = count("/api/sales/orders/")
        few_detail = count(f"/api/sales/orders/{first.pk}/")
        for i in range(2, 7):
            self._paid_order(phone=f"090000000{i}", txn=f"Q{i}")
        self.assertEqual(count("/api/sales/orders/"), few_list)
        self.assertEqual(count(f"/api/sales/orders/{first.pk}/"), few_detail)
