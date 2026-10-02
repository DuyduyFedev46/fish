# Cá Về: hệ thống mua, bán, quản lý kho cho vựa hải sản

Phần mềm cho một vựa hải sản đông lạnh bán lẻ cho khách cá nhân (B2C). Vựa mua cá theo **lô** tại cảng, bán online theo kg,
khách trả bằng **VietQR qua cổng SePay**, nhân viên của vựa giao tận nhà. Hệ thống theo dõi **giá vốn và lãi lỗ theo từng lô**.
Lộc là chủ vựa, Duy là PO. Chuỗi `cangca` trong tên hạ tầng là tên cũ, thương hiệu hiển thị là "Cá Về".

**Tài liệu hệ thống đầy đủ: [`doc/he-thong/`](doc/he-thong/README.md)** (kiến trúc, nghiệp vụ, backend, ERP, Shop, quy trình đội, thuật ngữ).

**Chuyển sang máy mới / dev tiếp: [`doc/ops/ban-giao-may-moi.md`](doc/ops/ban-giao-may-moi.md)** (cài đặt, file bí mật cần tự chuyển, trạng thái dự án, cách làm tiếp bằng Claude Code).

## Kiến trúc

```
Khách ──► Shop (frontend/, web tĩnh) ───┐                       ┌──► PostgreSQL (Supabase)
                                         ├──► Django + DRF API ──┤
Nhân viên ──► ERP (erp-console/, tĩnh) ──┘     (backend/)        └──► Bucket ảnh (Cloud Storage)
                                                 ▲
SePay ──IPN──► adapter/ (FastAPI, không đụng DB) ┘
```

- **Django là 100% lõi**: dữ liệu, nghiệp vụ, API, Django Admin. Nghiệp vụ nằm trong `services.py` của từng module.
- **Adapter FastAPI** chỉ nhận IPN thanh toán từ SePay, kiểm khoá, rồi gọi API nội bộ Django.
- **Shop và ERP** là Next.js 14 xuất tĩnh lên Firebase Hosting, gọi API lúc chạy trên trình duyệt.
- Backend và adapter chạy trên Cloud Run (GCP project `keolai-63ec1`, region `asia-southeast1`).

Quyết định kiến trúc đã chốt: `doc/decisions.md`. Chi tiết: [`doc/he-thong/tong-quan.md`](doc/he-thong/tong-quan.md).

## Cấu trúc thư mục

| Thư mục / file | Là gì |
|---|---|
| `backend/` | Django + DRF: các app `accounts`, `catalog`, `purchasing`, `inventory`, `sales`, `delivery`, `reports`, `content`, `ai`, `common`. Xem `backend/README.md` |
| `erp-console/` | ERP nội bộ cho Chủ và nhân viên (Next.js, chia `features/<module>` và `shared/`). Xem `erp-console/README.md` |
| `frontend/` | Trang giới thiệu, Shop, bài viết, trang chính sách cho khách (Next.js). Xem `frontend/features/checkout/README.md` |
| `adapter/` | FastAPI nhận IPN SePay. Xem `adapter/README.md` |
| `doc/` | Tài liệu: `he-thong/` (bộ tài liệu hệ thống), `URD.md`, `business-process-spec.md` (quy trình và luật `BR-*`), `decisions.md`, `ke-hoach-tong.md`, `ops/` (môi trường, pháp lý), `features/` (hồ sơ từng tính năng), `design/erp/` (thiết kế ERP mới) |
| `scripts/` | `check_naming.py` kiểm định danh tiếng Anh trong code |
| `DESIGN.md` | Hệ thiết kế dùng chung (màu sáng/tối, chữ, khoảng cách, bo góc, bóng, chuyển động). Token chạy thật của ERP: `erp-console/shared/ui/tokens.css` |
| `PRODUCT.md` | Bối cảnh sản phẩm và người dùng cho thiết kế giao diện (mục "(suy luận)" chờ Duy xác nhận) |
| `CLAUDE.md`, `.claude/` | Hướng dẫn và cấu hình đội agent Claude (skill, agent, lệnh) |
| `AGENTS.md`, `.agents/`, `.gemini/` | Cấu hình cho Gemini CLI / Antigravity (đang tạm dừng) |

## Chạy trên máy (dev)

Cần Python 3.11+ và Node 18+.

```bash
# 1. Backend -> http://localhost:8000 (/admin/ và /api/)
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # đặt DJANGO_DEBUG=1 cho dev; để trống DATABASE_URL thì dùng SQLite
python manage.py migrate      # tạo bảng + nhóm quyền
python manage.py bootstrap_masterdata   # Kho chính + bảng giá Bán lẻ
python manage.py seed_demo    # (tuỳ chọn) dữ liệu demo; gỡ bằng seed_demo --remove
python manage.py createsuperuser
python manage.py runserver

# 2. ERP console -> http://localhost:3100
cd erp-console && npm ci
NEXT_PUBLIC_USE_MOCK=1 npm run dev                          # mock, không cần backend
NEXT_PUBLIC_API_BASE=http://localhost:8000 npm run dev      # nối backend máy mình

# 3. Shop -> http://localhost:3000
cd frontend && npm ci
NEXT_PUBLIC_USE_MOCK=1 npm run dev                          # mock, không cần backend
NEXT_PUBLIC_USE_MOCK=0 NEXT_PUBLIC_API_BASE=http://localhost:8000 npm run dev

# 4. Adapter -> http://localhost:9000 (chỉ cần khi thử IPN)
cd adapter
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --port 9000
```

File `.env.example` của mỗi thư mục giải thích từng biến. Chép thành `.env` (backend, adapter) hoặc `.env.local` (ERP, Shop) rồi điền.
**Không commit `.env`, `.env.local`** và không đưa secret vào repo: repo đang công khai.

## Chạy test

```bash
cd backend && .venv/bin/python manage.py test              # toàn bộ backend; thêm apps.sales để chạy một app
cd adapter && .venv/bin/pip install -r requirements-dev.txt && .venv/bin/python -m pytest -q
cd erp-console && npm test && ./node_modules/.bin/tsc --noEmit && npm run build
cd frontend && npm run build
python3 scripts/check_naming.py                            # ở gốc repo
```

E2E (Playwright, Python) nằm ở `erp-console/e2e/` và `frontend/e2e/`. Đầu mỗi file ghi cách chạy.

## Môi trường

| | Staging (thử) | Production (thật) |
|---|---|---|
| Backend / adapter | Cloud Run `cangca-api-staging`, `cangca-adapter-staging` | `cangca-api`, `cangca-adapter` |
| Shop / ERP | Firebase site `cangca-loc-staging`, `cangca-erp-staging` | `cangca-loc`, `cangca-erp` |
| Database | Supabase, database `cangca_staging` | Supabase, database `postgres` |
| SePay | Sandbox | Live |

- Deploy staging trước, Duy duyệt rồi mới production. Không deploy khi Duy chưa yêu cầu.
- Build Shop/ERP để deploy **luôn truyền `NEXT_PUBLIC_USE_MOCK=0` và `NEXT_PUBLIC_API_BASE=...` trực tiếp trên dòng lệnh**, vì `.env.local` đè lên `.env.production`.
- URL, tên secret, lệnh deploy, trạng thái hiện tại (production đang tắt để tiết kiệm, cổng SePay live đang tắt chờ pháp lý): `doc/ops/moi-truong.md`.
- Trước khi mở bán thật: `doc/ops/go-live-phap-ly.md`.

## Tiến độ

Đã xong và có trên staging: nhập lô, giá vốn, bán hàng trên Shop, thanh toán cổng SePay, gọi xác nhận đơn, giao hàng, in tem,
huỷ đơn và hoàn tiền, chứng từ đảo doanh thu, CMS và trang chính sách, lớp lệnh AI, đổi định danh sang tiếng Anh (P1 đến P8b).

Đang làm và tiếp theo:
- ERP làm lại theo bộ thiết kế mới: `doc/features/2026-10-01-erp-theo-design/`.
- Màn ERP Kiểm kê, Báo cáo lãi lỗ, Việc giao của tôi còn là màn chờ (backend đã có API).
- P9: AI chạy model trên máy người dùng.

Bảng phase và trạng thái: `doc/ke-hoach-tong.md`.

## Quy ước

- Định danh trong code là tiếng Anh chuẩn. Giao diện, comment, tài liệu là tiếng Việt.
- Không rò giá vốn, không rò dữ liệu cá nhân của khách, không xoá chứng từ.
- Tiền VNĐ dùng `Decimal`. DB lưu giờ UTC, hiển thị giờ Việt Nam.
- Xong một lô đã QA đạt thì commit tiếng Việt có mã lô/story và `git push origin main`.
- Quy trình đội: [`doc/he-thong/quy-trinh-doi.md`](doc/he-thong/quy-trinh-doi.md) và `CLAUDE.md`.
