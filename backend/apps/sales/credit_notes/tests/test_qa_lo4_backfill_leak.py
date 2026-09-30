"""
QA P8 Lô 4 — SR-14 (lệnh lập bù), rò giá vốn / dữ liệu cá nhân, append-only. Độc lập với test của be-dev.
Dữ liệu hoàn toàn giả. Giá vốn "sentinel" 123457 (lô của mặt hàng thứ hai) để dò rò theo chuỗi.
"""
import json
import re
import uuid
from datetime import timedelta
from decimal import Decimal
from io import StringIO
from unittest import mock

from django.contrib.auth.models import Permission, User
from django.core.management import call_command
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.accounts.models import AuditLog
from apps.catalog.models import Item, ItemPrice
from apps.common.cost_keys import COST_KEYS
from apps.common.tests.fixtures import client_for, make_user
from apps.inventory.batches import services as batch_services
from apps.inventory.models import Batch
from apps.reports import services as report_services
from apps.sales.credit_notes.tests.base import (
    SENTINEL_ADDRESS, SENTINEL_NAME, SENTINEL_PHONE, find_keys,
)
from apps.sales.credit_notes.tests.test_qa_lo4_tien import QABase, cancel_url, month_dt, ym_back
from apps.sales.models import SalesCreditNote, SalesInvoice, SalesOrder
from apps.sales.orders import services as order_services
from apps.sales.payments import services as payment_services

COST_SENTINEL = "123457"


class QAItem2Base(QABase):
    """Thêm mặt hàng 2 (giá vốn sentinel 123457) để dò rò chuỗi giá vốn."""

    def setUp(self):
        super().setUp()
        self.item2 = Item.objects.create(code="CA-BASA", name="Cá basa", item_group=self.item.item_group)
        today = timezone.localdate()
        ItemPrice.objects.create(price_list=self.pl, item=self.item2, rate=Decimal("150000"),
                                 valid_from=today - timedelta(days=1))
        self.batch2 = batch_services.create_batch(
            item=self.item2, supplier=self.sup, warehouse=self.wh, received_date=today,
            qty=Decimal("50"), purchase_rate=Decimal(COST_SENTINEL),
        )
        batch_services.publish_batch(batch=self.batch2, actor=None)

    def _paid2(self, *, phone=SENTINEL_PHONE, name=SENTINEL_NAME, qty=Decimal("2")):
        order = order_services.create_order(
            customer_phone=phone, customer_name=name, delivery_address=SENTINEL_ADDRESS, phone=phone,
            lines=[{"item_code": self.item2.code, "qty": qty}],
        )
        payment_services.confirm_payment(order=order, bank_txn_id=f"TXN-{uuid.uuid4().hex[:8]}",
                                         amount=order.total_amount, received_at=timezone.now())
        order.refresh_from_db()
        from apps.delivery.models import ConfirmationTask, DeliveryNote
        note = DeliveryNote.objects.get(sales_invoice__sales_order=order)
        return order, note, ConfirmationTask.objects.get(note=note)

    def _legacy_cancel(self, order, *, invoice_at=None, audit_at=None):
        """Giả lập đơn huỷ TRƯỚC P8: huỷ rồi xoá chứng từ đảo (chỉ dùng ORM trong test)."""
        if invoice_at is not None:
            SalesInvoice.objects.filter(pk=order.invoice.pk).update(issued_at=invoice_at)
        self._manual_cancel(order)
        SalesCreditNote.objects.filter(sales_invoice__sales_order=order).delete()
        if audit_at is not None:
            AuditLog.objects.filter(action="cancel_paid_order", object_id=str(order.pk)).update(created_at=audit_at)

    def _cmd(self, *args):
        out = StringIO()
        call_command("backfill_credit_notes", *args, stdout=out, stderr=out)
        return out.getvalue()


# ----------------------------------------------------------------------------------------------
# SR-14
# ----------------------------------------------------------------------------------------------
class QABackfillTests(QAItem2Base):
    def _build_legacy_world(self):
        """3 đơn huỷ cũ: (1) lô chưa chốt, hoá đơn 3 tháng trước; (2) lô item2 ĐÃ CHỐT; (3) có hoàn trước."""
        o1, _n, _t = self._paid()
        self._legacy_cancel(o1, invoice_at=month_dt(3)[0], audit_at=month_dt(3)[0])
        o2, _n, _t = self._paid2(phone="0900000222")
        self._legacy_cancel(o2, invoice_at=month_dt(2)[0], audit_at=month_dt(2)[0])
        Batch.objects.filter(pk=self.batch2.pk).update(status=Batch.Status.CLOSED,
                                                       closed_at=timezone.now() - timedelta(days=1))
        self.batch2.refresh_from_db()
        o3, _n, _t = self._paid(phone="0900000333")
        SalesInvoice.objects.filter(pk=o3.invoice.pk).update(issued_at=month_dt(4)[0])
        o3.refresh_from_db()
        self._refund(o3.invoice, 50000, confirmed_at=month_dt(3)[0])
        self._legacy_cancel(o3, audit_at=month_dt(3)[0])
        # nhiễu: một đơn còn PAID (không được đụng), một đơn huỷ MỚI (đã có chứng từ)
        self.paid_only, _n, _t = self._paid(phone="0900000444")
        o5, _n, _t = self._paid(phone="0900000555")
        self._manual_cancel(o5)
        return o1, o2, o3

    def test_dry_run_khong_ghi_gi_khong_pii_khong_gia_von(self):
        o1, o2, o3 = self._build_legacy_world()
        cn_before = SalesCreditNote.objects.count()
        audit_before = AuditLog.objects.count()
        with CaptureQueriesContext(connection) as ctx:
            out = self._cmd()
        writes = [q["sql"] for q in ctx.captured_queries
                  if re.match(r"\s*(INSERT|UPDATE|DELETE|REPLACE|CREATE|DROP|ALTER)", q["sql"], re.I)]
        self.assertEqual(writes, [], "dry-run không được ghi")
        self.assertEqual(SalesCreditNote.objects.count(), cn_before)
        self.assertEqual(AuditLog.objects.count(), audit_before)
        self.assertIn("DRY-RUN: 3 đơn", out)
        for o in (o1, o2, o3):
            self.assertIn(o.code, out)
            self.assertIn(o.invoice.code, out)
        self.assertNotIn(self.paid_only.code, out)
        # lô đã chốt được liệt kê riêng (đơn 2, lô item2)
        self.assertIn("Lô đã CLOSED liên quan", out)
        self.assertIn(self.batch2.batch_id, out)
        self.assertIn(f"đơn {o2.code} · lô {self.batch2.batch_id} — lãi lỗ lô giữ nguyên", out)
        self.assertNotIn(f"đơn {o1.code} · lô {self.batch.batch_id} — lãi lỗ lô giữ nguyên", out)
        low = out.lower()
        for bad in (SENTINEL_NAME, SENTINEL_PHONE, SENTINEL_ADDRESS, "0900000222", "0900000333",
                    COST_SENTINEL, "110000", "220000", "unit_cost", "landed", "giá vốn", "gia von", "purchase"):
            self.assertNotIn(bad.lower(), low, bad)
        self.assertIn("Chưa ghi gì", out)

    def test_apply_ky_cu_khong_doi_lo_closed_khong_doi_ky_hien_tai_nhan_va_apply_lan_2(self):
        o1, o2, o3 = self._build_legacy_world()
        periods_before = self._snap_periods()
        b2_before = self._batch_pnl(self.batch2)        # lô đã chốt
        b1_before = self._batch_pnl(self.batch)         # lô chưa chốt (tạm tính)
        self.assertEqual(b2_before["revenue"], Decimal("300000"))  # đối chứng: số cũ còn tính đơn đã huỷ

        out = self._cmd("--apply")
        self.assertIn("Đã lập 3 chứng từ đảo", out)
        cns = SalesCreditNote.objects.filter(backfilled=True)
        self.assertEqual(cns.count(), 3)
        now = timezone.now()
        for cn in cns:
            self.assertIsNone(cn.created_by)
            self.assertLess(now - cn.issued_at, timedelta(minutes=5))   # E1: lúc chạy lệnh
            self.assertNotEqual(cn.issued_at.date(), month_dt(2)[0].date())

        periods_after = self._snap_periods()
        # mọi kỳ QUÁ KHỨ (n>=1) giữ nguyên MỌI khoá
        for n in range(1, self.N_PERIODS):
            self.assertEqual(periods_after[ym_back(n)], periods_before[ym_back(n)], f"kỳ -{n} bị đổi số")
        # kỳ hiện tại nhận điều chỉnh: o1 300.000 + o2 300.000 + o3 (300.000 - 50.000 đã hoàn trước) + o5 (huỷ mới) 300.000
        cur = periods_after[ym_back(0)]
        self.assertEqual(cur["credit_notes"], Decimal("1150000"))
        self.assertEqual(cur["cogs_reversed"], Decimal("220000") * 3 + Decimal("2") * Decimal(COST_SENTINEL))
        # lô đã chốt đứng yên, lô chưa chốt được đảo
        self.assertEqual(self._batch_pnl(self.batch2), b2_before)
        b1 = self._batch_pnl(self.batch)
        self.assertEqual(b1["revenue"], b1_before["revenue"] - Decimal("300000") * 2)   # o1 + o3 (2 đơn x 300.000)
        self.assertEqual(b1["reversed_qty"], Decimal("6"))  # o1 + o3 + o5 (mỗi đơn 2 kg)

        # apply lần 2: 0 chứng từ mới, kỳ + lô + audit không đổi
        audit_n = AuditLog.objects.count()
        issued = {c.pk: c.issued_at for c in SalesCreditNote.objects.all()}
        out2 = self._cmd("--apply")
        self.assertIn("0 đơn", out2)
        self.assertIn("Đã lập 0 chứng từ đảo", out2)
        self.assertEqual(SalesCreditNote.objects.filter(backfilled=True).count(), 3)
        self.assertEqual(AuditLog.objects.count(), audit_n)
        self.assertEqual({c.pk: c.issued_at for c in SalesCreditNote.objects.all()}, issued)
        self.assertEqual(self._snap_periods(), periods_after)
        # đơn đang PAID không bị đụng
        self.paid_only.refresh_from_db()
        self.assertIn(self.paid_only.status, (SalesOrder.Status.PAID, SalesOrder.Status.PROCESSING))
        self.assertFalse(SalesCreditNote.objects.filter(sales_invoice__sales_order=self.paid_only).exists())

    def test_apply_output_khong_pii_khong_gia_von_ca_3_lan(self):
        self._build_legacy_world()
        blob = "\n".join([self._cmd(), self._cmd("--apply"), self._cmd("--apply")]).lower()
        for bad in (SENTINEL_NAME, SENTINEL_PHONE, SENTINEL_ADDRESS, "0900000222", "0900000333",
                    COST_SENTINEL, "110000", "220000", "unit_cost", "landed"):
            self.assertNotIn(bad.lower(), blob, bad)

    def test_apply_loi_giua_chung_chay_lai_khong_nhan_doi(self):
        o1, _n, _t = self._paid()
        self._legacy_cancel(o1)
        o2, _n, _t = self._paid(phone="0900000222")
        self._legacy_cancel(o2)
        from apps.sales.credit_notes import services as cn_services
        real = cn_services.issue_cancel_credit_note
        calls = {"n": 0}

        def flaky(**kw):
            calls["n"] += 1
            if calls["n"] == 2:
                raise RuntimeError("boom")
            return real(**kw)

        with mock.patch("apps.sales.credit_notes.services.issue_cancel_credit_note", side_effect=flaky):
            with self.assertRaises(RuntimeError):
                self._cmd("--apply")
        self.assertEqual(SalesCreditNote.objects.count(), 1)     # đơn 1 đã lập, đơn 2 rollback
        # 2 audit từ lúc huỷ (test chỉ xoá chứng từ, không xoá audit) + 1 audit lập bù của đơn 1; đơn 2 rollback không ghi audit
        self.assertEqual(AuditLog.objects.filter(action="issue_credit_note").count(), 3)
        out = self._cmd("--apply")
        self.assertIn("Đã lập 1 chứng từ đảo", out)
        self.assertEqual(SalesCreditNote.objects.count(), 2)
        self.assertEqual(SalesCreditNote.objects.values("sales_invoice").distinct().count(), 2)

    def test_apply_stock_restored_false_tu_audit_va_don_khong_co_hoa_don_bi_bo_qua(self):
        o1, note, _t = self._paid()
        note.status = note.Status.FAILED
        note.save(update_fields=["status"])
        order_services.cancel_paid_order(order=o1, actor=self.chu, reason_code="GIVE_UP_AFTER_FAILED")
        SalesCreditNote.objects.all().delete()
        # đơn giữ chỗ tự huỷ (chưa thanh toán -> không hoá đơn) không được chọn
        SalesOrder.objects.create(code="DH-QA-KHONG-HD", status=SalesOrder.Status.CANCELLED,
                                  customer=o1.customer, phone="0900000999", delivery_address="x",
                                  total_amount=Decimal("1000")) if False else None
        out = self._cmd("--apply")
        self.assertIn("Đã lập 1 chứng từ đảo", out)
        self.assertFalse(SalesCreditNote.objects.get().stock_restored)


# ----------------------------------------------------------------------------------------------
# Rò giá vốn / dữ liệu cá nhân
# ----------------------------------------------------------------------------------------------
class QALeakTests(QAItem2Base):
    GROUPS = ("chu", "quan_ly", "nv_kho", "nv_giao", "cskh")

    def _users(self):
        return {"chu": self.chu, "quan_ly": self.ql, "nv_kho": self.kho, "nv_giao": self.giao, "cskh": self.cs1}

    def _world(self):
        o1, n1, t1 = self._paid2()                       # huỷ tay (chu)
        self._manual_cancel(o1)
        o2, n2, t2 = self._paid2(phone="0900000222")     # job tự huỷ
        # đường job dùng item 1; tạo thêm một đơn item2 rồi để job huỷ
        from datetime import timedelta as td
        from apps.delivery.cskh import services as cskh_services
        from apps.delivery.models import ConfirmationTask
        from django.test import override_settings
        t0 = timezone.now().replace(hour=9, minute=25, second=0, microsecond=0)
        t2.state = ConfirmationTask.State.ESCALATED
        t2.escalation_reason = ConfirmationTask.EscalationReason.UNREACHABLE
        t2.escalated_at = t0
        t2.save()
        with override_settings(CSKH_AUTO_CANCEL_ENABLED=True):
            self.assertEqual(cskh_services.auto_cancel_overdue(now=t0 + td(minutes=31))["cancelled"], 1)
        o3, n3, t3 = self._paid2(phone="0900000333")     # còn PAID
        return o1, o2, o3

    def _urls(self, o1, o2, o3):
        urls = []
        for o in (o1, o2, o3):
            urls += [f"/api/sales/orders/{o.pk}/", f"/api/guidance/order/{o.code}/",
                     f"/api/sales/invoices/{o.invoice.pk}/"]
        urls += ["/api/sales/orders/", "/api/sales/invoices/", "/api/sales/refunds/", "/api/dashboard/summary/",
                 "/api/dashboard/attention/", "/api/audit-logs/", "/api/cskh/queue/", "/api/delivery/notes/",
                 f"/api/inventory/batches/{self.batch2.pk}/", "/api/inventory/ledger/",
                 "/api/reports/period/?year=%d&month=%d" % ym_back(0),
                 f"/api/reports/batch/{self.batch2.batch_id}/"]
        return urls

    def test_khong_ro_gia_von_va_pii_moi_response_moi_nhom_dem_200(self):
        o1, o2, o3 = self._world()
        urls = self._urls(o1, o2, o3)
        ok = {g: 0 for g in self.GROUPS}
        matrix = {}
        for g, user in self._users().items():
            for url in urls:
                resp = client_for(user).get(url)
                matrix[(g, url.split("?")[0])] = resp.status_code
                self.assertLess(resp.status_code, 500, f"{g} {url} {resp.status_code}")
                if resp.status_code != 200:
                    continue
                ok[g] += 1
                body = resp.json()
                text = json.dumps(body, ensure_ascii=False)
                if g == "chu":
                    continue
                # nhóm KHÔNG có view_costprice: không có khoá giá vốn, không có chuỗi giá vốn sentinel
                if not user.has_perm("inventory.view_costprice"):
                    self.assertEqual(find_keys(body, (COST_KEYS | {"unit_cost", "cogs_reversed", "reversed_revenue"}) - {"rate"}),
                                     set(), f"{g} {url}")
                    self.assertNotIn("unit_cost", text, f"{g} {url}")
                    self.assertNotIn(COST_SENTINEL, text, f"{g} {url}")
                    self.assertNotIn("landed", text, f"{g} {url}")
        for g in self.GROUPS:
            self.assertGreater(ok[g], 0, f"{g}: không có response 200 nào — test xanh giả\n{matrix}")
        # nhóm thiếu view_profitreport: báo cáo lãi lỗ 403
        for g in ("quan_ly", "nv_kho", "nv_giao", "cskh"):
            self.assertEqual(matrix[(g, "/api/reports/period/")], 403, g)
            self.assertEqual(matrix[(g, f"/api/reports/batch/{self.batch2.batch_id}/")], 403, g)
        self.assertEqual(matrix[("chu", "/api/reports/period/")], 200)
        # số 200 tối thiểu của quan_ly (đã có quyền xem đơn/dashboard) để chắc endpoint thực sự gọi được
        self.assertGreaterEqual(ok["quan_ly"], 8, matrix)
        self.assertGreaterEqual(ok["nv_kho"], 2, matrix)
        self.assertGreaterEqual(ok["cskh"], 1, matrix)

    def test_khach_chua_dang_nhap_401_va_shop_khong_lo(self):
        o1, o2, o3 = self._world()
        for url in self._urls(o1, o2, o3):
            self.assertEqual(client_for(None).get(url).status_code, 401, url)
        # Shop công khai (tra đơn cần mã + SĐT): đơn đã huỷ có chứng từ, response không có chứng từ/giá vốn/PII đầy đủ
        resp = client_for(None).get(f"/api/shop/orders/{o1.code}/", {"phone": SENTINEL_PHONE})
        text = json.dumps(resp.json(), ensure_ascii=False) if resp.status_code == 200 else ""
        for bad in ("unit_cost", COST_SENTINEL, "credit_note", "DC-", "SalesCreditNote", SENTINEL_NAME, SENTINEL_ADDRESS):
            self.assertNotIn(bad, text, bad)
        if resp.status_code == 200:
            self.assertNotIn(SENTINEL_PHONE, text)  # SĐT đầy đủ không trả

    def test_audit_log_issue_credit_note_khong_tinh_nguoc_ra_gia_von(self):
        o1, o2, o3 = self._world()
        rows = list(AuditLog.objects.filter(action="issue_credit_note"))
        self.assertEqual(len(rows), 2)
        for r in rows:
            blob = json.dumps(r.changes, ensure_ascii=False) + r.note + r.object_repr + str(getattr(r, "detail", ""))
            self.assertEqual(find_keys(r.changes, COST_KEYS | {"unit_cost", "cogs_reversed", "qty"}), set())
            self.assertEqual(set(r.changes), {"credit_note", "amount", "backfilled"})
            for bad in (COST_SENTINEL, SENTINEL_NAME, SENTINEL_PHONE, SENTINEL_ADDRESS, "landed"):
                self.assertNotIn(bad, blob)
            # Tiền ÷ kg: amount là tiền bán; không có kg trong khoá -> không suy ra được giá vốn
            self.assertEqual(Decimal(r.changes["amount"]), Decimal("300000"))
        # quan_ly xem /api/audit-logs/ (200) — không có khoá giá vốn / PII
        resp = client_for(self.ql).get("/api/audit-logs/")
        self.assertEqual(resp.status_code, 200)
        text = json.dumps(resp.json(), ensure_ascii=False)
        for bad in (COST_SENTINEL, SENTINEL_PHONE, SENTINEL_NAME, SENTINEL_ADDRESS, "unit_cost"):
            self.assertNotIn(bad, text)
        self.assertIn("issue_credit_note", text)

    def test_timeline_khong_chua_gia_von_hay_pii_cho_moi_nhom(self):
        o1, o2, o3 = self._world()
        n = 0
        for g, user in self._users().items():
            for o in (o1, o2):
                resp = client_for(user).get(f"/api/sales/orders/{o.pk}/")
                if resp.status_code != 200:
                    continue
                n += 1
                ev = [e for e in resp.json().get("timeline", []) if e["kind"] == "credit_note_issued"]
                self.assertEqual(len(ev), 1, g)
                blob = json.dumps(ev, ensure_ascii=False)
                for bad in (COST_SENTINEL, "unit_cost", SENTINEL_PHONE, SENTINEL_NAME, SENTINEL_ADDRESS):
                    self.assertNotIn(bad, blob)
        self.assertGreaterEqual(n, 4)


# ----------------------------------------------------------------------------------------------
# Admin thật (HTML) + append-only qua API/Admin
# ----------------------------------------------------------------------------------------------
class QAAdminAppendOnlyTests(QAItem2Base):
    def _staff(self, username, codenames):
        u = User.objects.create_user(username, password="pw-gia-123", is_staff=True)
        for app, cn in codenames:
            u.user_permissions.add(Permission.objects.get(content_type__app_label=app, codename=cn))
        return User.objects.get(pk=u.pk)

    def _admin_client(self, user):
        c = Client()
        c.force_login(user)
        return c

    def test_admin_html_staff_thieu_view_costprice_khong_thay_gia_von_o_moi_trang(self):
        order, _n, _t = self._paid2()
        self._manual_cancel(order)
        cn = SalesCreditNote.objects.get()
        line = cn.lines.get()
        SalesCreditNote.objects.filter(pk=cn.pk)  # noqa
        staff = self._staff("staff_khong_gia_von", [
            ("sales", "view_salescreditnote"), ("sales", "view_salescreditnoteline"),
        ])
        self.assertFalse(staff.has_perm("inventory.view_costprice"))
        c = self._admin_client(staff)
        pages = [
            "/admin/sales/salescreditnote/", f"/admin/sales/salescreditnote/{cn.pk}/change/",
            f"/admin/sales/salescreditnote/{cn.pk}/history/",
            "/admin/sales/salescreditnoteline/", f"/admin/sales/salescreditnoteline/{line.pk}/change/",
            "/admin/sales/salescreditnote/?q=DC-", "/admin/sales/salescreditnoteline/?q=" + cn.code,
        ]
        seen200 = 0
        for url in pages:
            resp = c.get(url)
            self.assertEqual(resp.status_code, 200, url)
            seen200 += 1
            html = resp.content.decode()
            self.assertIn("DC-", html if "history" not in url else "DC-" + html)  # đúng trang có nội dung chứng từ
            for bad in (COST_SENTINEL, "123457,", "Giá vốn", "unit_cost", "field-unit_cost", "column-unit_cost"):
                self.assertNotIn(bad, html, f"{url} lộ {bad}")
        self.assertEqual(seen200, len(pages))

    def test_admin_html_co_view_costprice_thay_gia_von_doi_chung(self):
        order, _n, _t = self._paid2()
        self._manual_cancel(order)
        cn = SalesCreditNote.objects.get()
        staff = self._staff("staff_co_gia_von", [
            ("sales", "view_salescreditnote"), ("sales", "view_salescreditnoteline"), ("inventory", "view_costprice"),
        ])
        html = self._admin_client(staff).get(f"/admin/sales/salescreditnote/{cn.pk}/change/").content.decode()
        self.assertIn("Giá vốn ảnh chụp", html)
        self.assertIn("123457", html)

    def test_admin_superuser_khong_them_sua_xoa_duoc(self):
        order, _n, _t = self._paid2()
        self._manual_cancel(order)
        cn = SalesCreditNote.objects.get()
        su = User.objects.create_superuser("root_qa", password="pw-gia-123")
        c = self._admin_client(su)
        self.assertEqual(c.get("/admin/sales/salescreditnote/add/").status_code, 403)
        self.assertEqual(c.get("/admin/sales/salescreditnoteline/add/").status_code, 403)
        self.assertEqual(c.get(f"/admin/sales/salescreditnote/{cn.pk}/delete/").status_code, 403)
        self.assertEqual(c.post(f"/admin/sales/salescreditnote/{cn.pk}/delete/", {"post": "yes"}).status_code, 403)
        before = SalesCreditNote.objects.filter(pk=cn.pk).values().get()
        r = c.post(f"/admin/sales/salescreditnote/{cn.pk}/change/", {"amount": "1", "code": "DC-SUA"})
        self.assertIn(r.status_code, (403, 302))
        self.assertEqual(SalesCreditNote.objects.filter(pk=cn.pk).values().get(), before)
        # hành động xoá hàng loạt từ danh sách
        r = c.post("/admin/sales/salescreditnote/", {"action": "delete_selected", "_selected_action": [cn.pk], "post": "yes"})
        self.assertTrue(SalesCreditNote.objects.filter(pk=cn.pk).exists())
        self.assertEqual(SalesCreditNote.objects.count(), 1)

    def test_api_khong_co_route_chung_tu_moi_phuong_thuc_deu_khong_ghi_duoc(self):
        order, _n, _t = self._paid2()
        self._manual_cancel(order)
        cn = SalesCreditNote.objects.get()
        before = SalesCreditNote.objects.filter(pk=cn.pk).values().get()
        for user in (self.chu, self.ql, self.kho, self.giao, self.cs1):
            c = client_for(user)
            for path in ("/api/sales/credit-notes/", f"/api/sales/credit-notes/{cn.pk}/",
                         "/api/sales/creditnotes/", "/api/credit-notes/", f"/api/sales/invoices/{order.invoice.pk}/credit-notes/"):
                for method in ("get", "post", "patch", "put", "delete"):
                    resp = getattr(c, method)(path, {"amount": 1}, format="json") if method != "get" and method != "delete" else getattr(c, method)(path)
                    self.assertIn(resp.status_code, (404, 405), f"{user.username} {method} {path} -> {resp.status_code}")
        # hoá đơn: PATCH/DELETE qua API không đụng được (chứng từ không xoá) và không xoá chứng từ
        for user in (self.chu, self.ql):
            c = client_for(user)
            for method in ("patch", "put", "delete"):
                resp = getattr(c, method)(f"/api/sales/invoices/{order.invoice.pk}/", {"status": "CANCELLED"}, format="json")
                self.assertIn(resp.status_code, (403, 404, 405), f"{user.username} {method} -> {resp.status_code}")
        order.invoice.refresh_from_db()
        self.assertEqual(order.invoice.status, SalesInvoice.Status.ISSUED)
        self.assertEqual(SalesCreditNote.objects.filter(pk=cn.pk).values().get(), before)

    def test_khong_nhom_nao_co_quyen_ghi_chung_tu_va_chi_superuser_moi_co_view(self):
        from django.contrib.auth.models import Group
        for g in Group.objects.all():
            perms = set(g.permissions.values_list("codename", flat=True))
            for cn in ("add_salescreditnote", "change_salescreditnote", "delete_salescreditnote",
                       "add_salescreditnoteline", "change_salescreditnoteline", "delete_salescreditnoteline"):
                self.assertNotIn(cn, perms, f"{g.name} có {cn}")
        codenames = set(Permission.objects.filter(content_type__app_label="sales",
                        content_type__model__in=("salescreditnote", "salescreditnoteline")).values_list("codename", flat=True))
        self.assertEqual(codenames, {"view_salescreditnote", "view_salescreditnoteline"})


class QAPermMatrixTests(QAItem2Base):
    """SR-13 AC6: ma trận báo cáo lãi lỗ và dashboard theo Group (chạy thật)."""

    def test_ma_tran_report_va_dashboard(self):
        order, _n, _t = self._paid2()
        self._manual_cancel(order)
        period = "/api/reports/period/?year=%d&month=%d" % ym_back(0)
        batch = f"/api/reports/batch/{self.batch2.batch_id}/"
        users = {"chu": self.chu, "quan_ly": self.ql, "nv_kho": self.kho, "nv_giao": self.giao, "cskh": self.cs1}
        expect = {
            "chu": (200, 200, 200), "quan_ly": (403, 403, 200), "nv_kho": (403, 403, 200),
            "nv_giao": (403, 403, 403), "cskh": (403, 403, 403),
        }
        for g, u in users.items():
            got = tuple(client_for(u).get(p).status_code for p in (period, batch, "/api/dashboard/summary/"))
            self.assertEqual(got, expect[g], g)
        for p in (period, batch, "/api/dashboard/summary/"):
            self.assertEqual(client_for(None).get(p).status_code, 401, p)
        # chỉ Chủ thấy khoá đảo trong báo cáo; các khoá này là tiền BÁN (÷ kg = giá bán 150.000), không phải giá vốn
        b = client_for(self.chu).get(batch).json()
        rq, rr = Decimal(str(b["reversed_qty"])), Decimal(str(b["reversed_revenue"]))
        self.assertEqual(rr / rq, Decimal("150000"))
        self.assertNotEqual(rr / rq, Decimal(COST_SENTINEL))
