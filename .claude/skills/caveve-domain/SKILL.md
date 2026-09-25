---
name: caveve-domain
description: Kiến thức nghiệp vụ + bất biến kỹ thuật của dự án Cá Về (vựa cá B2C — mua lô ở cảng, bán online, quản lý kho/giá vốn). Dùng khi phân tích yêu cầu, viết story, code, test hay review BẤT KỲ phần nào của repo này — đặc biệt khi đụng tới lô (batch), FIFO, giữ chỗ/TTL, giá vốn, phân quyền 3 tầng, hoàn tiền, AuditLog, hoặc mã BR-*.
---

# Cá Về — bản đồ nghiệp vụ & bất biến

Tên sản phẩm hiển thị là **"Cá Về"**. "Lộc" là chủ vựa (người), "Duy" là PO. Chuỗi
`cangca` còn trong tên hạ tầng (Cloud Run, Firebase site) — không phải brand.

## Nguồn sự thật (đọc theo thứ tự, không đoán)

| File | Dùng khi |
|---|---|
| `doc/URD.md` | Yêu cầu người dùng (mục 5 = tác nhân, mục 6 = chức năng) |
| `doc/business-process-spec.md` | Quy trình P-01…P-10 + business rule `BR-*` + §13 ngoại lệ + §15 câu hỏi mở |
| `doc/decisions.md` | Quyết định đã chốt — **không tự lật** |
| `doc/BUILD-PLAN.md` | Contract hàm service/API |
| `doc/features/<ngày>-<slug>/` | Hồ sơ từng tính năng mới (xem skill `feature`) |

**Nhãn nguồn** trong spec: **(L)** Lộc nói trực tiếp → yêu cầu thật, không sửa ·
**(D)** Duy quyết · **(PA)** giả định thiết kế → được đề xuất đổi nhưng phải ghi rõ.

## Mã business rule

| Tiền tố | Quy trình | | Tiền tố | Quy trình |
|---|---|---|---|---|
| BR-PQ | Phân quyền §1 | | BR-GH | P-06 Soạn & giao hàng |
| BR-DM | P-01 Danh mục, giá, combo | | BR-HT | P-07 Huỷ đơn & hoàn tiền |
| BR-MH | P-02 Mua hàng & nhập lô | | BR-HV | P-08 Giao thất bại về kho |
| BR-GV | P-03 Chi phí mua & giá vốn lô | | BR-KK | P-09 Kiểm kê & hao hụt |
| BR-LO | P-04 Vòng đời lô | | BR-BC | P-10 Báo cáo lãi lỗ |
| BR-BH, BR-TT | P-05 Bán hàng Shop, thanh toán | | | |

Mọi story/test/commit liên quan nghiệp vụ phải **trích mã BR** nó thực thi hoặc thay đổi.
Rule mới → đề xuất mã kế tiếp trong nhóm (vd BR-BH-11) và ghi vào hồ sơ tính năng.

## Kiến trúc

```
frontend/ (Next.js 14, static export → Firebase cangca-loc)   erp-console/ (Next.js 14 static export, chia features/ → Firebase cangca-erp)
        │                                                               │
        └──────────►  backend/ Django + DRF (Cloud Run cangca-api, Cloud SQL Postgres 16)  ◄── adapter/ FastAPI (webhook SePay, không đụng DB)
```

- Django là **100% lõi**. FastAPI chỉ là adapter mỏng gọi API nội bộ Django.
- App theo domain: `accounts catalog purchasing inventory sales delivery reports common`.
- Mỗi app domain chia module tính năng `apps/<domain>/<tinh_nang>/` (xem `backend/README.md` — bản đồ module). Logic nghiệp vụ ở `<tinh_nang>/services.py`; API ở `api.py` / `shop_api.py` /
  `internal_api.py`; route ở `config/api_urls.py`. View **không** chứa logic nghiệp vụ.
- Lỗi nghiệp vụ → raise `apps.common.exceptions.BusinessError` (thông điệp tiếng Việt,
  kèm mã BR). `actor=None` = Hệ thống.

## Bất biến — vi phạm là bug nghiêm trọng

1. **Không rò giá vốn.** Field nhạy cảm (`Batch.purchase_rate`, `Batch.landed_unit_cost`,
   `PurchaseReceiptLine.rate`, `*LineBatch.unit_cost`, lãi lỗ) chỉ lộ khi user có
   `view_costprice` / `view_profitreport`. Serializer tách theo quyền, **cấm `fields="__all__"`**.
   Có test mẫu: `backend/apps/inventory/batches/tests/test_api.py`.
2. **Phân quyền 3 tầng** (BR-PQ): Tầng 1 = model perm qua 4 Group cộng dồn `chu`,
   `quan_ly`, `nv_kho`, `nv_giao` (`BusinessModelPermissions` ở `apps/common/api.py`);
   Tầng 2 = `Meta.permissions` tuỳ biến (`publish_batch`, `close_batch`,
   `cancel_paid_order`, `create_refund`, `confirm_refund`, `confirm_payment_manual`,
   `view_costprice`, `view_profitreport`, `manage_staff`…); Tầng 3 = scope dòng trong
   `get_queryset` + ẩn cột. Ranh giới: Quản lý được uỷ *việc làm khách phải chờ*; Chủ giữ
   *việc làm tiền rời túi hoặc đổi con số lời lỗ*.
3. **Chứng từ không xoá** — huỷ bằng trạng thái (BR-PQ-10). FK tới User dùng `PROTECT`.
4. `SalesOrder`/`SalesInvoice` chỉ Hệ thống tạo (BR-PQ-11). `AuditLog`, `StockLedgerEntry`,
   `*LineBatch` là append-only.
5. Thay đổi trạng thái quan trọng → ghi `AuditLog` (BR-PQ-04/05).
6. Xuất kho theo **FIFO lô** + bảng phân bổ lô (BR-BH-06). Giữ chỗ có TTL
   (`SALES_ORDER_TTL_MINUTES`), job `cancel_expired_orders` phải **idempotent**.
7. Tiền dùng `Decimal`, không float. Tham số nghiệp vụ đọc từ `settings`/env, không hard-code.
8. Schema là tài sản đã ổn định: thêm model/field phải có lý do trong hồ sơ tính năng
   và migration đi kèm.

## Lệnh chuẩn

```bash
cd backend && .venv/bin/python manage.py test                 # backend (Django TestCase)
cd backend && .venv/bin/python manage.py test apps.sales       # một app
cd adapter && .venv/bin/python -m pytest -q                    # adapter
cd frontend && npm run build                                   # FE: build tĩnh phải sạch
cd frontend && NEXT_PUBLIC_USE_MOCK=1 npm run dev              # FE chạy mock, không cần backend
cd erp-console && ./node_modules/.bin/tsc --noEmit && npm run build   # ERP console
```

Production (chỉ deploy khi Duy duyệt): GCP project `keolai-63ec1`, region
`asia-southeast1`; xem `backend/Dockerfile`, `frontend/firebase.json`.
