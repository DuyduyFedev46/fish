# Cảng cá Lộc — Hệ thống Mua – Bán – Quản lý kho

Vựa cá B2C bán hải sản đông lạnh: mua tại cảng theo lô → bán online (giao tận nhà) →
quản lý giá vốn/lãi lỗ theo lô. Dự án tương lai (chưa vận hành thực tế).

## Kiến trúc (đã chốt — xem `doc/decisions.md`)

```
Next.js (frontend/)  ──►  Django DRF API (backend/)  ◄──  FastAPI adapter (adapter/)  ◄── webhook SePay
   Landing + Shop            100% lõi: ORM, Admin,          lớp mỏng, không đụng DB
   guest checkout            API, PostgreSQL
```

- **backend/** — Django 100% lõi (data model, business logic, API, Admin). Xem `backend/README.md`.
- **frontend/** — Next.js: Landing (SEO) + Shop (giỏ hàng, VietQR, tra đơn).
- **adapter/** — FastAPI: nhận webhook SePay → gọi API nội bộ Django (cô lập bên thứ 3).
- **doc/** — tài liệu nghiệp vụ: `URD.md`, `business-process-spec.md` (business rules
  BR-*), `decisions.md` (nhật ký kiến trúc), `BUILD-PLAN.md` (kế hoạch build + contract).
- **DESIGN.md** — design system dùng chung ERP/Shop/app (màu light/dark, chữ, khoảng cách, bo góc, bóng, chuyển động).
  Token chạy thật của ERP: `erp-console/shared/ui/tokens.css`.
- **PRODUCT.md** — bối cảnh sản phẩm/người dùng cho skill `impeccable` (đọc cùng DESIGN.md; mục "(suy luận)" chờ Duy xác nhận).

## Chạy nhanh (dev)

```bash
# Backend
cd backend && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate && python manage.py bootstrap_masterdata
python manage.py createsuperuser && python manage.py runserver   # :8000

# Frontend
cd frontend && npm install && npm run dev                        # :3000

# Adapter
cd adapter && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && uvicorn app:app --port 9000
```

## Tiến độ — tất cả các phase đã xong (V1)

- ✅ Phase 1 — Data model (Django), phân quyền 3 tầng, Admin.
- ✅ Phase 2 — Business logic (FIFO → FEFO từ 2026-09-26, giữ chỗ/TTL, landed cost, hoàn tiền, báo cáo).
- ✅ Phase 3 — DRF API (serializer tách Group chống rò rỉ giá vốn, scope dòng).
- ✅ Phase 4 — FastAPI adapter (webhook SePay, 10 test).
- ✅ Phase 5 — Next.js (Landing + Shop, build sạch).
- ✅ Phase 6 — Celery + job huỷ TTL + giám sát sức khoẻ job.

**Test**: backend 66 test xanh · adapter 10 test xanh · frontend build sạch.

### Còn lại trước khi chạy thật (hạ tầng/nghiệp vụ, không phải code lõi)
- Dựng PostgreSQL + Redis thật (dev đang dùng SQLite; Celery cần broker Redis).
- Chốt hợp đồng SePay + sinh mã VietQR thật (hiện là stub trong `shop_api`).
- Trả lời các câu hỏi mở nghiệp vụ trong `doc/` (ngưỡng chuỗi lạnh, combo thực tế…).
- QA giao diện Shop chạy thật với API (frontend có sẵn chế độ mock để dev độc lập).
