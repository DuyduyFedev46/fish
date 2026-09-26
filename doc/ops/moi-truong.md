# Hai môi trường: staging và production
> Tách ngày 2026-09-27 theo quyết định của Duy. Code xong thì deploy **staging**, QA hoặc Duy test trên đó, **Duy duyệt** rồi mới deploy **production**.

| | **Staging (thử)** | **Production (thật)** |
|---|---|---|
| Shop | https://cangca-loc-staging.web.app | https://cangca-loc.web.app |
| ERP | https://cangca-erp-staging.web.app | https://cangca-erp.web.app |
| Backend (Cloud Run) | `cangca-api-staging` → https://cangca-api-staging-675411800433.asia-southeast1.run.app | `cangca-api` → https://cangca-api-675411800433.asia-southeast1.run.app |
| Adapter IPN | `cangca-adapter-staging` → https://cangca-adapter-staging-675411800433.asia-southeast1.run.app/ipn/sepay | `cangca-adapter` → https://cangca-adapter-675411800433.asia-southeast1.run.app/ipn/sepay |
| Database | Supabase `fissh1`, database **`cangca_staging`** (secret `cangca-staging-database-url`) | Supabase `fissh1`, database **`postgres`** (secret `cangca-supabase-database-url`) |
| SePay | **Sandbox** (`cangca-sepay-sandbox-*`), `SEPAY_ENV=SANDBOX` | **Live** (`cangca-sepay-live-*`), `SEPAY_ENV=PRODUCTION` |
| Khoá Django / token nội bộ | `cangca-staging-django-secret-key`, `cangca-staging-internal-token` | env riêng của `cangca-api` |
| Dữ liệu | Dữ liệu thử và dữ liệu mẫu, được phép tạo đơn thử | Chỉ dữ liệu thật (đã làm sạch 2026-09-27) |
| Job nền | chưa có (khi cần thì thêm `cangca-ttl-staging`) | `cangca-ttl` (*/15), `cangca-batch-status` (00:05), `cangca-migrate` |

## Cấu hình trên SePay (Cổng thanh toán → Cấu hình → IPN)
- **Sandbox:** IPN URL trỏ adapter **staging**, Auth Type = **Secret Key** (khoá sandbox).
- **Live:** IPN URL trỏ adapter **production**, Auth Type = **Secret Key** (khoá live).

## Deploy
**Backend / adapter:**
- Build image một lần, deploy lên `*-staging` trước. Staging đạt thì deploy **cùng image** lên production.
- Có migration: chạy migrate trên staging trước (dùng job tạm, hoặc `DATABASE_URL` staging trên máy dev), sau đó mới chạy job `cangca-migrate` cho production.
- Khi đổi biến và secret, làm trong **một lệnh** `gcloud run services update … --update-env-vars … --update-secrets …`. Nếu tách `--remove-env-vars` và `--update-secrets` thành hai lệnh thì sẽ sinh ra một revision trung gian không có DB.

**Shop / ERP:**
- `frontend/.env.local` (mock) đè lên `.env.production`. **Luôn build bằng cách truyền biến trực tiếp**:
  ```bash
  # staging
  NEXT_PUBLIC_USE_MOCK=0 NEXT_PUBLIC_API_BASE=https://cangca-api-staging-675411800433.asia-southeast1.run.app npm run build
  firebase deploy --only hosting --config firebase.staging.json --project keolai-63ec1
  # production
  NEXT_PUBLIC_USE_MOCK=0 NEXT_PUBLIC_API_BASE=https://cangca-api-675411800433.asia-southeast1.run.app npm run build
  firebase deploy --only hosting --project keolai-63ec1
  ```
- Sau khi build, grep thư mục `out/_next` để chắc bản build trỏ đúng URL. Thư mục `out/` đang chứa bản build nào thì deploy ra đúng bản đó.

## Sao lưu
- Bucket `gs://cangca-db-backups-keolai/export/` chứa các bản xuất lúc chuyển DB, gồm cả bản production trước khi làm sạch.
- Supabase Free không tự sao lưu. Job `pg_dump` hằng đêm: **còn nợ**.
- Cloud SQL `cangca-loc-db` đang STOPPED, chờ Duy duyệt thì xoá.
