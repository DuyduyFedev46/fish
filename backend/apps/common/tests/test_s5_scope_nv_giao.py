"""
S5 — NV giao chỉ thấy đơn và khách của phiếu giao gán cho mình (Tầng 3 dòng,
BR-PQ-12, spec §1.6). Người kiêm nhiệm thấy hợp quyền (BR-PQ-09).
"""
from django.test import TestCase

from apps.delivery.models import DeliveryNote

from .fixtures import client_for, make_order_with_note, make_user


class S5ScopeTests(TestCase):
    def setUp(self):
        self.giao1 = make_user("giao1", "nv_giao")
        self.giao2 = make_user("giao2", "nv_giao")
        self.d1, self.c1, self.n1 = make_order_with_note("SO-D1", "0900000001", assigned_to=self.giao1)
        self.d2, self.c2, self.n2 = make_order_with_note("SO-D2", "0900000002", assigned_to=self.giao2)
        # đơn chưa gán ai + khách chưa có đơn
        self.d3, self.c3, _ = make_order_with_note("SO-D3", "0900000003")
        self.c4 = type(self.c1).objects.create(phone="0900000004", name="Khách lẻ")

    def _ids(self, resp):
        self.assertEqual(resp.status_code, 200, resp.content)
        return sorted(row["id"] for row in resp.json()["results"])

    def test_s5_ac1_nv_giao_chi_thay_don_cua_phieu_minh(self):
        resp = client_for(self.giao1).get("/api/sales/orders/")
        self.assertEqual(self._ids(resp), [self.d1.pk])
        self.assertEqual(resp.json()["count"], 1)

    def test_s5_ac1_don_nhieu_phieu_khong_bi_nhan_doi(self):
        DeliveryNote.objects.create(
            code="DN-EXTRA", sales_invoice=self.d1.invoice, assigned_to=self.giao1,
        )
        resp = client_for(self.giao1).get("/api/sales/orders/")
        self.assertEqual(self._ids(resp), [self.d1.pk])

    def test_s5_ac2_chi_tiet_don_va_khach_ngoai_pham_vi_404(self):
        c = client_for(self.giao1)
        self.assertEqual(c.get(f"/api/sales/orders/{self.d2.pk}/").status_code, 404)
        self.assertEqual(c.get(f"/api/sales/orders/{self.d3.pk}/").status_code, 404)
        self.assertEqual(c.get(f"/api/sales/customers/{self.c2.pk}/").status_code, 404)
        self.assertEqual(c.get(f"/api/sales/customers/{self.c4.pk}/").status_code, 404)

    def test_s5_ac2_chi_tiet_trong_pham_vi_200(self):
        c = client_for(self.giao1)
        resp = c.get(f"/api/sales/orders/{self.d1.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["customer"]["phone"], "0900000001")  # S10: SĐT nằm trong customer
        self.assertEqual(c.get(f"/api/sales/customers/{self.c1.pk}/").status_code, 200)

    def test_s5_ac3_danh_sach_khach_chi_khach_cua_don_minh(self):
        resp = client_for(self.giao1).get("/api/sales/customers/")
        self.assertEqual(self._ids(resp), [self.c1.pk])

    def test_s5_ac4_kiem_nhiem_nv_kho_va_nv_giao_thay_moi_don(self):
        kho1 = make_user("kho1", "nv_kho", "nv_giao")
        self.assertEqual(
            self._ids(client_for(kho1).get("/api/sales/orders/")),
            sorted([self.d1.pk, self.d2.pk, self.d3.pk]),
        )
        self.assertEqual(
            self._ids(client_for(kho1).get("/api/sales/customers/")),
            sorted([self.c1.pk, self.c2.pk, self.c3.pk, self.c4.pk]),
        )

    def test_s5_ac4_quan_ly_va_chu_thay_moi_don(self):
        for group in ("quan_ly", "chu"):
            user = make_user(f"u_{group}", group)
            self.assertEqual(len(self._ids(client_for(user).get("/api/sales/orders/"))), 3, group)

    def test_s5_ac5_phieu_doi_nguoi_giao_thi_mat_quyen_xem(self):
        c = client_for(self.giao1)
        self.assertEqual(c.get(f"/api/sales/orders/{self.d1.pk}/").status_code, 200)
        self.n1.assigned_to = self.giao2
        self.n1.save(update_fields=["assigned_to"])
        self.assertEqual(c.get(f"/api/sales/orders/{self.d1.pk}/").status_code, 404)
        self.assertEqual(c.get(f"/api/sales/customers/{self.c1.pk}/").status_code, 404)
        self.assertEqual(self._ids(c.get("/api/sales/orders/")), [])

    def test_s5_nv_giao_khong_sua_duoc_khach(self):
        resp = client_for(self.giao1).patch(
            f"/api/sales/customers/{self.c1.pk}/", {"name": "Đổi tên"}, format="json"
        )
        self.assertEqual(resp.status_code, 403)
        self.c1.refresh_from_db()
        self.assertEqual(self.c1.name, "Khách SO-D1")

    def test_s5_nguoi_khong_nhom_403_va_chua_dang_nhap_401(self):
        nobody = make_user("nobody")
        self.assertEqual(client_for(nobody).get("/api/sales/orders/").status_code, 403)
        self.assertEqual(client_for(None).get("/api/sales/orders/").status_code, 401)
        self.assertEqual(client_for(None).get("/api/sales/customers/").status_code, 401)

    def test_s5_nv_giao_khong_thay_hoa_don(self):
        """nv_giao không có view_salesinvoice → 403 (không vòng qua hoá đơn để lấy khách)."""
        resp = client_for(self.giao1).get("/api/sales/invoices/")
        self.assertEqual(resp.status_code, 403)
