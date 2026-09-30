"""
P8 Lô 4 — SR-12: huỷ đơn đã thanh toán lập chứng từ đảo doanh thu (F04, BR-HT-06, BR-HT-10, BR-PQ-10/11).

R6 (review 30/09) chuyển từ `repro/review_repro_tests.py`: đơn PAID 2 kg x 150.000 từ lô X, job tự huỷ CSKH
chạy -> phải có đúng 1 chứng từ đảo, hoá đơn gốc vẫn ISSUED. Dữ liệu hoàn toàn giả.
"""
import json
import re
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from unittest import mock

from django.contrib import admin
from django.contrib.auth.models import Permission
from django.forms.models import model_to_dict
from django.test import RequestFactory
from django.utils import timezone

from apps.accounts.models import AuditLog
from apps.common.cost_keys import COST_KEYS
from apps.common.tests.fixtures import client_for
from apps.inventory.batches import services as batch_services
from apps.inventory.models import Batch, StockLedgerEntry
from apps.sales.credit_notes import services as cn_services
from apps.sales.models import SalesCreditNote, SalesCreditNoteLine, SalesInvoice, SalesOrder
from apps.sales.models.invoices import SalesInvoiceLineBatch
from apps.sales.orders import services as order_services

from .base import (
    SENTINEL_ADDRESS, SENTINEL_NAME, SENTINEL_PHONE, CreditNoteBase, find_keys,
)


def cancel_url(pk):
    return f"/api/sales/orders/{pk}/cancel/"


def _snapshot(obj):
    return model_to_dict(type(obj).objects.get(pk=obj.pk))


class SR12CreditNoteTests(CreditNoteBase):
    # ---- AC1 (R6) -----------------------------------------------------------------------
    def test_sr12_ac1_r6_job_tu_huy_lap_dung_1_chung_tu(self):
        order, note, task = self._paid()
        invoice = order.invoice
        before = _snapshot(invoice)
        lines_before = [model_to_dict(x) for x in SalesInvoiceLineBatch.objects.order_by("pk")]

        result = self._auto_cancel(task)
        self.assertEqual(result["cancelled"], 1)

        order.refresh_from_db()
        self.assertEqual(order.status, SalesOrder.Status.CANCELLED)
        notes = SalesCreditNote.objects.filter(sales_invoice=invoice)
        self.assertEqual(notes.count(), 1)
        cn = notes.get()
        self.assertEqual(cn.amount, invoice.amount)
        self.assertEqual(cn.code, f"DC-{invoice.code}")
        self.assertEqual(cn.kind, SalesCreditNote.Kind.CANCEL_ORDER)
        self.assertIsNone(cn.created_by)  # AC2: job -> Hệ thống
        self.assertTrue(cn.stock_restored)
        self.assertFalse(cn.backfilled)
        self.assertEqual(cn.reason_code, "UNREACHABLE_AUTO")

        self.assertEqual(cn.lines.count(), 1)
        line = cn.lines.get()
        self.assertEqual(line.batch_id, self.batch.pk)
        self.assertEqual(line.qty, Decimal("2.000"))
        self.assertEqual(line.rate, Decimal("150000"))
        self.assertEqual(line.amount, Decimal("300000"))

        # hoá đơn gốc KHÔNG đổi field nào, vẫn ISSUED; phân bổ lô gốc nguyên vẹn
        self.assertEqual(_snapshot(invoice), before)
        self.assertEqual(SalesInvoice.objects.get(pk=invoice.pk).status, SalesInvoice.Status.ISSUED)
        self.assertEqual(
            [model_to_dict(x) for x in SalesInvoiceLineBatch.objects.order_by("pk")], lines_before
        )

    # ---- AC2 ----------------------------------------------------------------------------
    def test_sr12_ac2_huy_tay_chu_created_by_la_nguoi_huy(self):
        order, _note, _task = self._paid()
        resp = client_for(self.chu).post(
            cancel_url(order.pk), {"reason_code": "CUSTOMER_CHANGED_MIND"}, format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        cn = SalesCreditNote.objects.get()
        self.assertEqual(cn.created_by, self.chu)
        self.assertEqual(cn.amount, order.invoice.amount)
        self.assertEqual(cn.reason_code, "CUSTOMER_CHANGED_MIND")
        # hợp đồng API không đổi: không thêm khoá chứng từ vào response huỷ
        self.assertEqual(
            set(resp.json()),
            {"order_status", "stock_restored", "delivery_status", "suggest_refund_amount", "invoice_id"},
        )

    def test_sr12_ac2_huy_tay_quan_ly_created_by_la_nguoi_huy(self):
        order, _note, _task = self._paid()
        resp = client_for(self.ql).post(
            cancel_url(order.pk), {"reason_code": "DAMAGED_WHEN_PACKING"}, format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(SalesCreditNote.objects.get().created_by, self.ql)

    def test_sr12_ac2_ma_tran_group_khong_du_quyen_khong_lap_chung_tu(self):
        order, _note, _task = self._paid()
        payload = {"reason_code": "CUSTOMER_CHANGED_MIND"}
        for user in (self.kho, self.giao, self.cs1):
            resp = client_for(user).post(cancel_url(order.pk), payload, format="json")
            self.assertEqual(resp.status_code, 403, user.username)
        self.assertEqual(client_for(None).post(cancel_url(order.pk), payload, format="json").status_code, 401)
        self.assertEqual(SalesCreditNote.objects.count(), 0)
        order.refresh_from_db()
        self.assertIn(order.status, (SalesOrder.Status.PAID, SalesOrder.Status.PROCESSING))

    # ---- AC3 ----------------------------------------------------------------------------
    def test_sr12_ac3_don_phan_bo_2_lo_chung_tu_2_dong(self):
        # Lô nhỏ nhập sớm hơn -> hạn dùng sớm hơn -> FEFO lấy trước (1 kg), phần còn lại từ lô X.
        small = batch_services.create_batch(
            item=self.item, supplier=self.sup, warehouse=self.wh,
            received_date=timezone.localdate() - timedelta(days=1), qty=Decimal("1"),
            purchase_rate=Decimal("90000"),
        )
        batch_services.publish_batch(batch=small, actor=None)
        order, _note, _task = self._paid(qty=Decimal("2.5"))
        allocs = list(SalesInvoiceLineBatch.objects.filter(invoice_line__invoice=order.invoice))
        self.assertEqual({a.batch_id for a in allocs}, {small.pk, self.batch.pk})

        resp = client_for(self.chu).post(
            cancel_url(order.pk), {"reason_code": "CUSTOMER_CHANGED_MIND"}, format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        cn = SalesCreditNote.objects.get()
        self.assertEqual(cn.lines.count(), 2)
        for a in allocs:
            line = cn.lines.get(invoice_line_batch=a)
            self.assertEqual(line.batch_id, a.batch_id)
            self.assertEqual(line.qty, a.qty)
            self.assertEqual(line.rate, a.invoice_line.rate)
            self.assertEqual(line.amount, a.qty * a.invoice_line.rate)
            self.assertEqual(line.unit_cost, a.unit_cost)
        self.assertEqual(sum(x.amount for x in cn.lines.all()), Decimal("375000"))
        self.assertEqual(cn.amount, order.invoice.amount)

    # ---- AC4 ----------------------------------------------------------------------------
    def test_sr12_ac4_huy_lan_2_van_400_va_1_chung_tu(self):
        order, _note, _task = self._paid()
        c = client_for(self.chu)
        self.assertEqual(c.post(cancel_url(order.pk), {"reason_code": "CUSTOMER_CHANGED_MIND"}, format="json").status_code, 200)
        again = c.post(cancel_url(order.pk), {"reason_code": "CUSTOMER_CHANGED_MIND"}, format="json")
        self.assertEqual(again.status_code, 400)
        self.assertEqual(SalesCreditNote.objects.count(), 1)

    def test_sr12_ac4_job_chay_2_lan_van_1_chung_tu(self):
        order, _note, task = self._paid()
        self._auto_cancel(task)
        again = self._auto_cancel(task)
        self.assertEqual(again["cancelled"], 0)
        self.assertEqual(SalesCreditNote.objects.count(), 1)
        self.assertEqual(SalesCreditNoteLine.objects.count(), 1)

    def test_sr12_ac4_issue_goi_lai_tra_cung_chung_tu_khong_nhan_doi(self):
        order, _note, _task = self._paid()
        client_for(self.chu).post(cancel_url(order.pk), {"reason_code": "CUSTOMER_CHANGED_MIND"}, format="json")
        first = SalesCreditNote.objects.get()
        again = cn_services.issue_cancel_credit_note(
            invoice=order.invoice, actor=self.chu, reason_code="X", stock_restored=True,
        )
        self.assertEqual(again.pk, first.pk)
        self.assertEqual(SalesCreditNote.objects.count(), 1)
        self.assertEqual(AuditLog.objects.filter(action="issue_credit_note").count(), 1)

    # ---- AC5 ----------------------------------------------------------------------------
    def test_sr12_ac5_loi_lap_chung_tu_rollback_ca_huy_don(self):
        order, note, _task = self._paid()
        self.batch.refresh_from_db()
        avail_before = self.batch.qty_available
        with mock.patch(
            "apps.sales.credit_notes.services.issue_cancel_credit_note",
            side_effect=RuntimeError("boom"),
        ):
            with self.assertRaises(RuntimeError):
                order_services.cancel_paid_order(order=order, actor=self.chu, reason_code="CUSTOMER_CHANGED_MIND")
        order.refresh_from_db()
        note.refresh_from_db()
        self.batch.refresh_from_db()
        self.assertIn(order.status, (SalesOrder.Status.PAID, SalesOrder.Status.PROCESSING))
        self.assertNotEqual(note.status, "CANCELLED")
        self.assertEqual(self.batch.qty_available, avail_before)
        self.assertFalse(
            StockLedgerEntry.objects.filter(movement_type=StockLedgerEntry.MovementType.CANCEL_RESTORE).exists()
        )
        self.assertFalse(AuditLog.objects.filter(action="cancel_paid_order").exists())
        self.assertEqual(SalesCreditNote.objects.count(), 0)

    # ---- AC6 ----------------------------------------------------------------------------
    def test_sr12_ac6_giao_that_bai_van_lap_chung_tu_stock_restored_false(self):
        order, note, _task = self._paid()
        note.status = note.Status.FAILED
        note.save(update_fields=["status"])
        result = order_services.cancel_paid_order(order=order, actor=self.chu, reason_code="GIVE_UP_AFTER_FAILED")
        self.assertFalse(result["stock_restored"])
        cn = SalesCreditNote.objects.get()
        self.assertFalse(cn.stock_restored)
        self.assertEqual(cn.lines.count(), 1)
        self.assertEqual(cn.amount, order.invoice.amount)

    # ---- AC7 ----------------------------------------------------------------------------
    def test_sr12_ac7_model_chi_co_quyen_view_khong_add_change_delete(self):
        for model in (SalesCreditNote, SalesCreditNoteLine):
            self.assertEqual(tuple(model._meta.default_permissions), ("view",))
            codenames = set(
                Permission.objects.filter(
                    content_type__app_label="sales", content_type__model=model._meta.model_name,
                ).values_list("codename", flat=True)
            )
            self.assertEqual(codenames, {f"view_{model._meta.model_name}"})

    def test_sr12_ac7_admin_chi_doc_ke_ca_superuser(self):
        from django.contrib.auth.models import User

        su = User.objects.create_superuser("root1", password="x")
        req = RequestFactory().get("/")
        req.user = su
        order, _n, _t = self._paid()
        client_for(self.chu).post(cancel_url(order.pk), {"reason_code": "CUSTOMER_CHANGED_MIND"}, format="json")
        cn = SalesCreditNote.objects.get()
        for model in (SalesCreditNote, SalesCreditNoteLine):
            self.assertIn(model, admin.site._registry)
            ma = admin.site._registry[model]
            self.assertFalse(ma.has_add_permission(req))
            self.assertFalse(ma.has_change_permission(req))
            self.assertFalse(ma.has_delete_permission(req))
            self.assertTrue(ma.has_view_permission(req))
        self.assertTrue(SalesCreditNote.objects.filter(pk=cn.pk).exists())

    def test_sr12_ac7_admin_an_unit_cost_voi_staff_thieu_view_costprice(self):
        """Techlead M1: inline Admin không được lộ giá vốn ảnh chụp (bất biến 1, SR-12-AC8)."""
        from django.contrib.auth.models import User
        from django.test import Client

        order, _n, _t = self._paid()
        client_for(self.chu).post(cancel_url(order.pk), {"reason_code": "CUSTOMER_CHANGED_MIND"}, format="json")
        cn = SalesCreditNote.objects.get()
        SalesCreditNoteLine.objects.filter(credit_note=cn).update(unit_cost=Decimal("123457.7777"))
        label = SalesCreditNoteLine._meta.get_field("unit_cost").verbose_name
        values = ("123457,7777", "123457.7777", "123.457,7777")
        url = f"/admin/sales/salescreditnote/{cn.pk}/change/"

        staff = User.objects.create_user("staff_cn", password="x", is_staff=True)
        for codename in ("view_salescreditnote", "view_salescreditnoteline"):
            staff.user_permissions.add(Permission.objects.get(content_type__app_label="sales", codename=codename))
        self.assertFalse(User.objects.get(pk=staff.pk).has_perm("inventory.view_costprice"))
        c = Client()
        c.force_login(staff)
        resp = c.get(url)
        self.assertEqual(resp.status_code, 200)  # không xanh giả vì 302/403
        html = resp.content.decode()
        self.assertIn(cn.code, html)             # đúng trang chứng từ
        self.assertNotIn(str(label), html)
        for v in values:
            self.assertNotIn(v, html)

        line = SalesCreditNoteLine.objects.get(credit_note=cn)
        for line_url in (f"/admin/sales/salescreditnoteline/{line.pk}/change/", "/admin/sales/salescreditnoteline/"):
            r = c.get(line_url)
            self.assertEqual(r.status_code, 200, line_url)
            self.assertNotIn(str(label), r.content.decode(), line_url)
            for v in values:
                self.assertNotIn(v, r.content.decode(), line_url)

        # đối chứng: người có view_costprice (và superuser) thấy
        boss = User.objects.create_user("boss_cn", password="x", is_staff=True)
        for app, codename in (("sales", "view_salescreditnote"), ("sales", "view_salescreditnoteline"),
                              ("inventory", "view_costprice")):
            boss.user_permissions.add(Permission.objects.get(content_type__app_label=app, codename=codename))
        su = User.objects.create_superuser("root_cn", password="x")
        for user in (boss, su):
            c2 = Client()
            c2.force_login(user)
            resp2 = c2.get(url)
            self.assertEqual(resp2.status_code, 200, user.username)
            html2 = resp2.content.decode()
            self.assertIn(str(label), html2, user.username)
            self.assertTrue(any(v in html2 for v in values), user.username)

    def test_sr12_ac7_khong_code_nao_sua_hoac_xoa_chung_tu(self):
        root = Path(__file__).resolve().parents[3]  # backend/apps
        pattern = re.compile(
            r"SalesCreditNote(Line)?\.objects[^\n]*\.(update|delete|bulk_update)\(|"
            r"credit_notes\.(update|delete)\(|\.credit_notes\.all\(\)\.(update|delete)\("
        )
        offenders = []
        for path in root.rglob("*.py"):
            rel = str(path.relative_to(root))
            if "/tests/" in rel or "/migrations/" in rel:
                continue
            for i, text in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if pattern.search(text) and not text.strip().startswith("#"):
                    offenders.append(f"{rel}:{i}")
        self.assertEqual(offenders, [])

    # ---- AC8 ----------------------------------------------------------------------------
    def test_sr12_ac8_timeline_co_su_kien_chung_tu_khong_lo_gia_von(self):
        order, note, task = self._paid()
        self._auto_cancel(task)
        cn = SalesCreditNote.objects.get()
        order.refresh_from_db()

        ok = 0
        # Chi tiết đơn (timeline) + guidance đơn (timeline riêng) x 5 Group; đếm 200 > 0 để không xanh giả.
        for who in (self.chu, self.ql, self.kho, self.giao, self.cs1):
            for url in (f"/api/sales/orders/{order.pk}/", f"/api/guidance/order/{order.code}/"):
                resp = client_for(who).get(url)
                self.assertIn(resp.status_code, (200, 404), f"{who.username} {url} -> {resp.status_code}")
                if resp.status_code != 200:
                    continue
                ok += 1
                body = resp.json()
                text = json.dumps(body, ensure_ascii=False)
                if who in (self.ql, self.kho, self.giao, self.cs1):
                    self.assertEqual(find_keys(body, COST_KEYS | {"unit_cost"}) - {"rate"}, set(), who.username)
                    self.assertNotIn("unit_cost", text)
                # sự kiện chứng từ đảo chỉ có giá bán
                self.assertIn(f"DC-{order.invoice.code}", text)
                self.assertIn("300.000", text)
        self.assertGreaterEqual(ok, 4)

        detail = client_for(self.chu).get(f"/api/sales/orders/{order.pk}/").json()
        events = [e for e in detail["timeline"] if e["kind"] == "credit_note_issued"]
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["label"], f"Lập chứng từ đảo doanh thu {cn.code} (300.000 ₫)")
        self.assertEqual(events[0]["actor_display"], "Hệ thống")
        self.assertNotIn(SENTINEL_ADDRESS, events[0]["label"])
        self.assertNotIn(SENTINEL_PHONE, events[0]["label"])

    def test_sr12_ac8_timeline_huy_tay_ghi_nguoi_huy(self):
        order, _n, _t = self._paid()
        client_for(self.ql).post(cancel_url(order.pk), {"reason_code": "CUSTOMER_CHANGED_MIND"}, format="json")
        detail = client_for(self.chu).get(f"/api/sales/orders/{order.pk}/").json()
        events = [e for e in detail["timeline"] if e["kind"] == "credit_note_issued"]
        self.assertEqual(len(events), 1)
        self.assertNotEqual(events[0]["actor_display"], "Hệ thống")

    def test_sr12_ac8_audit_issue_credit_note_khong_khoa_gia_von_khong_pii(self):
        order, _n, task = self._paid()
        self._auto_cancel(task)
        rows = list(AuditLog.objects.filter(action="issue_credit_note"))
        self.assertEqual(len(rows), 1)
        changes = rows[0].changes
        self.assertEqual(find_keys(changes, COST_KEYS), set())
        self.assertEqual(changes["credit_note"], f"DC-{order.invoice.code}")
        blob = json.dumps(changes, ensure_ascii=False) + rows[0].note + rows[0].object_repr
        for secret in (SENTINEL_NAME, SENTINEL_PHONE, SENTINEL_ADDRESS, "110000"):
            self.assertNotIn(secret, blob)

        # quan_ly xem nhật ký: không khoá giá vốn (redact) — và request thực sự 200
        resp = client_for(self.ql).get("/api/audit-logs/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(find_keys(resp.json(), COST_KEYS), set())
        self.assertIn("issue_credit_note", json.dumps(resp.json()))
