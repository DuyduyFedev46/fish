---
name: caveve-domain
description: Kiến thức nghiệp vụ + bất biến kỹ thuật của dự án Cá Về (vựa cá B2C — mua lô ở cảng, bán online, quản lý kho/giá vốn). Dùng khi phân tích yêu cầu, viết story, code, test hay review BẤT KỲ phần nào của repo này — đặc biệt khi đụng tới lô (batch), FEFO, giữ chỗ/TTL, giá vốn, phân quyền 3 tầng, hoàn tiền, AuditLog, hoặc mã BR-*.
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
2. **Phân quyền 3 tầng** (BR-PQ): Tầng 1 = model perm qua 4 Group cộng dồn `owner`,
   `manager`, `warehouse_staff`, `delivery_staff` (`BusinessModelPermissions` ở `apps/common/api.py`);
   Tầng 2 = `Meta.permissions` tuỳ biến (`publish_batch`, `close_batch`,
   `cancel_paid_order`, `create_refund`, `confirm_refund`, `confirm_payment_manual`,
   `view_costprice`, `view_profitreport`, `manage_staff`…); Tầng 3 = scope dòng trong
   `get_queryset` + ẩn cột. Ranh giới: Quản lý được uỷ *việc làm khách phải chờ*; Chủ giữ
   *việc làm tiền rời túi hoặc đổi con số lời lỗ*.
3. **Chứng từ không xoá** — huỷ bằng trạng thái (BR-PQ-10). FK tới User dùng `PROTECT`.
4. `SalesOrder`/`SalesInvoice` chỉ Hệ thống tạo (BR-PQ-11). `AuditLog`, `StockLedgerEntry`,
   `*LineBatch` là append-only.
5. Thay đổi trạng thái quan trọng → ghi `AuditLog` (BR-PQ-04/05).
6. Xuất kho theo **FEFO**: lô hạn dùng sớm nhất ra trước; cùng hạn thì lô nhập trước, rồi lô tạo trước. Nguồn duy nhất cho thứ tự là `sellable_batches`. Lô chốt một lần lúc tạo đơn, khi thanh toán không chọn lại (BR-BH-05/11, decisions 2026-09-26). Có bảng phân bổ lô (BR-BH-06). Giữ chỗ có TTL
   (`SALES_ORDER_TTL_MINUTES`), job `cancel_expired_orders` phải **idempotent**.
7. Tiền dùng `Decimal`, không float. Tham số nghiệp vụ đọc từ `settings`/env, không hard-code.
8. Schema là tài sản đã ổn định: thêm model/field phải có lý do trong hồ sơ tính năng
   và migration đi kèm.
9. **Không rò dữ liệu cá nhân của khách** (Luật BVDLCN 2025, checklist `doc/ops/go-live-phap-ly.md`).
   Dữ liệu cá nhân gồm tên, SĐT, địa chỉ ở `Customer.*`, `SalesOrder.phone/delivery_address`, `DeliveryNote`,
   cùng nội dung IPN hay sao kê có tên người chuyển. Mức nghiêm trọng ngang rò giá vốn.
   - **Thu tối thiểu.** Chỉ thu field phục vụ giao hàng hoặc thanh toán. Thêm field cá nhân mới phải ghi lý do
     trong `01-analysis.md` và Duy duyệt.
   - **API công khai (`AllowAny`) không bao giờ trả tên, SĐT hay địa chỉ đầy đủ.** Nếu cần hiện thì che bớt,
     ví dụ `09xx xxx 123`. Tra đơn phải có yếu tố xác minh (mã đơn + SĐT) và **giới hạn tần suất**.
   - **Trong ERP, chỉ lộ cho ai cần** (Tầng 3). `delivery_staff` chỉ thấy khách của phiếu giao được giao cho mình.
     Serializer liệt kê field tường minh, giống quy tắc giá vốn.
   - **Không ghi dữ liệu cá nhân vào log**, gồm `logger`, `print`, Sentry và console FE. Không log nguyên
     `request.data` hay payload IPN. Chỉ log mã đơn, mã giao dịch và SĐT đã che. `AuditLog` ghi *ai làm gì
     với đơn nào*, không chép địa chỉ hay SĐT vào `detail`.
   - **Không đưa dữ liệu thật ra ngoài môi trường production.** Không dùng trong fixture, test, ảnh chụp QA,
     `doc/`, commit hay tin nhắn. Staging và demo dùng dữ liệu giả. Không copy DB production xuống máy.
     Repo đang công khai.
   - **Không gửi dữ liệu cá nhân cho bên thứ ba mới** (analytics, pixel quảng cáo, AI, SMS…) khi Duy chưa duyệt
     và chính sách quyền riêng tư chưa nêu. Đặc biệt không gửi tới dịch vụ đặt server ở nước ngoài
     (xem mục 6b trong checklist).
   - **FE không lưu dữ liệu cá nhân** vào `localStorage` hay URL (query string). Giỏ hàng chỉ giữ mã hàng và
     số lượng. Form checkout phải có ô đồng ý xử lý dữ liệu khi có chính sách (việc go-live).
   - **Chỉ truyền qua HTTPS.** Secret và chuỗi kết nối DB lấy từ Secret Manager, không commit.
   - Quyền của khách (xem, sửa, xoá) xử lý bằng **ẩn danh hoá** trường cá nhân. Chứng từ vẫn giữ (bất biến 3),
     không xoá dòng.

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

## Đặt tên (P8b, Duy chốt 01/10)

Định danh trong code (hàm, biến, class, module, thư mục, file, test, script, route API, khoá JSON, biến env, Group,
`data-testid`, id lệnh AI, khoá lưu trình duyệt) là **tiếng Anh chuẩn, không viết tắt tiếng Việt**. Chữ hiển thị cho người
dùng, comment, docstring và tài liệu vẫn tiếng Việt. Viết tắt chỉ dùng khi là chuẩn quốc tế: `VN`, `VND`, `pnl`, `id`, `url`.
Không đưa mã lô giao việc (`lo7`, `l8`, `p8_lo5`) vào tên; mã lô/story ghi trong docstring.

| Khái niệm | Dùng | Không dùng |
|---|---|---|
| Vai (Group) | `owner` `manager` `warehouse_staff` `delivery_staff` `customer_service` | `chu` `quan_ly` `nv_kho` `nv_giao` `cskh` |
| Người giao trên một phiếu | `courier` | `nv_giao` |
| Việc gọi xác nhận đơn | `confirmation` | `cskh` (module, route, khoá JSON, env) |
| Nhập lô | `receive_batches`, `ReceiveBatches*` | `nhap_lo`, `NhapLo*` |
| Lệnh AI: nhóm / mức nhạy cảm | `purchasing` `sales` `customer_service` / `high` `medium` `low` | `thu_mua` `ban_hang` / `cao` `trung_binh` `thap` |
| Giờ Việt Nam | `VN_TIME_ZONE`, `todayInVietnam()`, `today_in_vietnam()` | `VN_TZ`, `todayVn`, `vn_today` |
| Bản rà soát QA / bổ sung | `review_*` / `extra`, `followup` | `ra_soat_*` / `bosung` |

Giữ nguyên (không đổi): migration đã chạy, `AuditLog.action` đã ghi, dòng phiên bản cấu hình AI cũ, URL công khai Shop
`/bai-viet/` `/trang/` `?chuyen-muc=`, dữ liệu demo (username `kho1`, `chu_vua`..., slug, mã hàng), keyword AI có dấu, chuỗi `cangca`.
Bảng đầy đủ: `doc/features/2026-09-30-dat-ten-tieng-anh/02c-giao-viec.md` mục 1.

**Kiểm bằng máy** (Python 3 stdlib, chạy từ gốc repo, dưới 10 giây, không cần venv):
`python3 scripts/check_naming.py`. Exit 1 khi file MỚI có định danh tiếng Việt, hoặc số vi phạm của một file TĂNG so với
`scripts/naming_baseline.json`; in file, dòng, token. Script không xét chuỗi hiển thị, comment, docstring. Danh sách từ chặn và
allowlist ở `scripts/naming_blocklist.txt`. Chạy lệnh này trước khi báo xong mọi việc có sửa code.
