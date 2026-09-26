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
| Bucket ảnh (A1, `doc/features/2026-09-26-anh-mat-hang`) | `cangca-item-images-keolai-staging` (đọc công khai qua `https://storage.googleapis.com/cangca-item-images-keolai-staging/…`) — **đã tạo 2026-09-27** | `cangca-item-images-keolai` (đọc công khai qua `https://storage.googleapis.com/cangca-item-images-keolai/…`) — **đã tạo 2026-09-27** |

## Danh sách link
| Dùng cho | Staging (thử) | Production (thật) |
|---|---|---|
| Shop (khách đặt hàng) | https://cangca-loc-staging.web.app/shop/ | https://cangca-loc.web.app/shop/ |
| ERP console (Chủ, nhân viên) | https://cangca-erp-staging.web.app | https://cangca-erp.web.app |
| API backend | https://cangca-api-staging-675411800433.asia-southeast1.run.app | https://cangca-api-675411800433.asia-southeast1.run.app |
| Django Admin | https://cangca-api-staging-675411800433.asia-southeast1.run.app/admin/ | https://cangca-api-675411800433.asia-southeast1.run.app/admin/ |
| IPN SePay (khai trên SePay) | https://cangca-adapter-staging-675411800433.asia-southeast1.run.app/ipn/sepay | https://cangca-adapter-675411800433.asia-southeast1.run.app/ipn/sepay |

Trang quản trị bên ngoài:
- SePay: https://my.sepay.vn
- Supabase: https://supabase.com/dashboard/project/nxfesdkckiqlplvxpyny
- Cloud Run: https://console.cloud.google.com/run?project=keolai-63ec1
- Firebase Hosting: https://console.firebase.google.com/project/keolai-63ec1/hosting
- Chi phí GCP: https://console.cloud.google.com/billing?project=keolai-63ec1
- Mã nguồn: https://github.com/DuyduyFedev46/fish

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

## Bucket ảnh mặt hàng (A1 — đã tạo 2026-09-27; kiểm: đọc object 200, liệt kê 403)
> Còn nợ: cả `cangca-api` và `cangca-api-staging` đang chạy bằng SA mặc định `675411800433-compute@` (roles/editor cả project), nên chưa tách quyền ghi theo môi trường. Chưa đặt budget alert 5 USD.
Hai bucket tách staging/production, `asia-southeast1`, đọc công khai từng object (không
liệt kê), ghi chỉ qua SA Cloud Run (không xoá — BR-DM-14). Xem
`doc/features/2026-09-26-anh-mat-hang/` cho AC chi tiết (A1).

```bash
PROJECT=keolai-63ec1
for BUCKET in cangca-item-images-keolai-staging cangca-item-images-keolai; do
  gcloud storage buckets create "gs://$BUCKET" \
    --project="$PROJECT" --location=asia-southeast1 \
    --uniform-bucket-level-access

  # Đọc công khai TỪNG object, KHÔNG cho liệt kê (roles/storage.objectViewer sẽ cho list -> không dùng).
  gcloud storage buckets add-iam-policy-binding "gs://$BUCKET" \
    --member=allUsers --role=roles/storage.legacyObjectReader
done

# Cache-Control mặc định cho object mới (tuỳ chọn — code đã set Cache-Control lúc upload,
# xem apps/catalog/images/storage.py).

# SA Cloud Run staging: chỉ ghi (objectCreator), KHÔNG xoá, CHỈ bucket staging.
gcloud storage buckets add-iam-policy-binding gs://cangca-item-images-keolai-staging \
  --member="serviceAccount:<SA-cangca-api-staging>" --role=roles/storage.objectCreator

# SA Cloud Run production: chỉ ghi, CHỈ bucket production.
gcloud storage buckets add-iam-policy-binding gs://cangca-item-images-keolai \
  --member="serviceAccount:<SA-cangca-api>" --role=roles/storage.objectCreator
```

Sau khi tạo, gắn env cho từng service (một lệnh, kèm biến khác nếu có thay đổi cùng lúc):
```bash
# staging
gcloud run services update cangca-api-staging --region=asia-southeast1 \
  --update-env-vars ITEM_IMAGE_STORAGE=gcs,ITEM_IMAGE_BUCKET=cangca-item-images-keolai-staging

# production (chỉ sau khi Duy duyệt)
gcloud run services update cangca-api --region=asia-southeast1 \
  --update-env-vars ITEM_IMAGE_STORAGE=gcs,ITEM_IMAGE_BUCKET=cangca-item-images-keolai
```
`ITEM_IMAGE_PUBLIC_BASE_URL` không cần đặt — BE tự suy ra
`https://storage.googleapis.com/<bucket>` từ `ITEM_IMAGE_BUCKET` khi `ITEM_IMAGE_STORAGE=gcs`.
Billing budget cảnh báo (C1, Duy 2026-09-27): 5 USD/tháng cho cả project, cảnh báo ở
50/90/100%, gửi email quản trị billing hiện có — đặt qua Billing → Budgets (thao tác tay,
không có lệnh `gcloud` chuẩn cho budget theo project + label).

## Sao lưu
- Bucket `gs://cangca-db-backups-keolai/export/` chứa các bản xuất lúc chuyển DB, gồm cả bản production trước khi làm sạch.
- Supabase Free không tự sao lưu. Job `pg_dump` hằng đêm: **còn nợ**.
- Cloud SQL `cangca-loc-db` **đã xoá** ngày 2026-09-27 (Duy duyệt). Dữ liệu cũ vẫn giữ ở các file `.sql` trong bucket nói trên.
