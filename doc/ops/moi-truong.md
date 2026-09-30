# Hai môi trường: staging và production
> Tách ngày 2026-09-27 theo quyết định của Duy. Code xong thì deploy **staging**, QA hoặc Duy test trên đó, **Duy duyệt** rồi mới deploy **production**.

> ⏸ **Chế độ tiết kiệm (2026-09-27, Duy yêu cầu): PRODUCTION ĐANG TẮT, chỉ chạy STAGING.**
> Đang chạy: `cangca-api-staging`, `cangca-adapter-staging` (max 1 instance). Đang tắt: `cangca-api`, `cangca-adapter` (ingress `internal` → gọi từ ngoài trả 404; Shop/ERP production vẫn mở trang nhưng không gọi được API).
> Scheduler `cangca-ttl-trigger` + `cangca-batch-status-trigger` (production) **tạm dừng**.
> Bật lại: `gcloud run services update <svc> --region asia-southeast1 --project keolai-63ec1 --ingress all` và `gcloud scheduler jobs resume <job> --location asia-southeast1 --project keolai-63ec1`. Phải bật adapter + TTL trước khi mở thanh toán.

| | **Staging (thử)** | **Production (thật)** |
|---|---|---|
| Shop | https://cangca-loc-staging.web.app | https://cangca-loc.web.app |
| ERP | https://cangca-erp-staging.web.app | https://cangca-erp.web.app |
| Backend (Cloud Run) | `cangca-api-staging` → https://cangca-api-staging-675411800433.asia-southeast1.run.app | `cangca-api` → https://cangca-api-675411800433.asia-southeast1.run.app |
| Adapter IPN | `cangca-adapter-staging` → https://cangca-adapter-staging-675411800433.asia-southeast1.run.app/ipn/sepay | `cangca-adapter` → https://cangca-adapter-675411800433.asia-southeast1.run.app/ipn/sepay |
| Database | Supabase `fissh1`, database **`cangca_staging`** (secret `cangca-staging-database-url`) | Supabase `fissh1`, database **`postgres`** (secret `cangca-supabase-database-url`) |
| SePay | **Sandbox** (`cangca-sepay-sandbox-*`), `SEPAY_ENV=SANDBOX` | **Live** (`cangca-sepay-live-*`), `SEPAY_ENV=PRODUCTION`. ⛔ **Cổng đang TẮT trên dashboard SePay** (Duy tắt ngày 2026-09-27) cho tới khi đủ `go-live-phap-ly.md` và đã thông báo Sở Công Thương. Shop vẫn cho đặt đơn nhưng không thanh toán được. Công tắc trong code đang hoãn: `doc/features/2026-09-27-tam-tat-thanh-toan/`. |
| Khoá Django / token nội bộ | `cangca-staging-django-secret-key`, `cangca-staging-internal-token` | env riêng của `cangca-api` |
| Dữ liệu | Dữ liệu thử và dữ liệu mẫu, được phép tạo đơn thử | Chỉ dữ liệu thật (đã làm sạch 2026-09-27) |
| Job nền | chưa có (khi cần thì thêm `cangca-ttl-staging`) | `cangca-ttl` (*/15), `cangca-batch-status` (00:05), `cangca-migrate` |
| Bucket ảnh (A1, `doc/features/2026-09-26-anh-mat-hang`) | `cangca-item-images-keolai-staging` (đọc công khai qua `https://storage.googleapis.com/cangca-item-images-keolai-staging/…`) — **đã tạo 2026-09-27** | `cangca-item-images-keolai` (đọc công khai qua `https://storage.googleapis.com/cangca-item-images-keolai/…`) — **đã tạo 2026-09-27** |
| Tài khoản thử (QA/team, tạo 2026-09-27) | `demo_chu` (nhóm chu) · `demo_nv_kho` · `demo_nv_giao` — cùng mật khẩu, **không ghi mật khẩu vào repo công khai**; hỏi Duy/điều phối khi cần | — |

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

## Biến môi trường Khung go-live pháp lý (GL-01..GL-05)
Khai báo trên Cloud Run (`cangca-api-staging` và `cangca-api`):
- `SELLER_NAME`: Tên hộ kinh doanh hoặc doanh nghiệp.
- `SELLER_BUSINESS_TYPE`: Loại hình kinh doanh (ví dụ: Hộ kinh doanh, Công ty TNHH...).
- `SELLER_REG_NO`: Số giấy chứng nhận đăng ký kinh doanh.
- `SELLER_TAX_CODE`: Mã số thuế.
- `SELLER_ADDRESS`: Địa chỉ trụ sở / địa chỉ kinh doanh.
- `SELLER_PHONE`: Số điện thoại liên hệ chính thức.
- `SELLER_EMAIL`: Email liên hệ chính thức.
- `PRIVACY_CONSENT_REQUIRED`: Cờ yêu cầu đồng ý chính sách bảo mật khi đặt đơn (`1` hoặc `0`). Mặc định trên production/staging là bật (`1`), môi trường test/dev là tắt (`0`).
  > ⚠️ **LƯU Ý QUAN TRỌNG (G1)**: Trước khi bật API production và cờ `PRIVACY_CONSENT_REQUIRED=1`, **phải đăng trang chính sách bảo mật** (`page_role="privacy"`) trên CMS trước. Nếu chưa có trang Đã đăng, Shop sẽ từ chối tạo đơn với lỗi 503 `BR-BH-17` để đảm bảo tuân thủ pháp lý.
- `SHOP_CONFIRM_CALL_NOTICE`: Bật thông báo gọi xác nhận đơn (`1` hoặc `0`).
- `SHOP_CONFIRM_CALL_HOURS`: Khung giờ gọi xác nhận (ví dụ: `8:00 - 18:00`).

*Tuyệt đối không lưu giá trị thật của người bán vào mã nguồn git. Đặt biến trực tiếp qua Google Cloud Run Secrets / Environment Variables.*

## Biến môi trường và job nền của AI (P8 Lô 7, SR-24 F13)
> Tên biến `AI_PRODUCTION_READY` dễ gây nhầm: giá trị `1` nghĩa là "môi trường này được phép mở vùng đỏ, mức B và DW-26", **chỉ đặt ở staging**. Production giữ `0`.

| Biến (Cloud Run) | Staging (`cangca-api-staging`) | Production (`cangca-api`) | Tác dụng |
|---|---|---|---|
| `AI_ENABLED` | `1` khi thử AI | theo quyết định của Duy | Công tắc gốc của AI Native. `0` thì mọi lệnh AI trả 410 (trừ rút lại/hoàn tác việc đã có) |
| `AI_PRODUCTION_READY` | **`1`** | **`0`** | `0` khoá vùng đỏ, khoá mức B, khoá DW-26 (`auto_confirm_exact_payments` trả `PRODUCTION_NOT_READY`) |
| `AI_WRITE_LEVELS_ALLOWED` | **`B`** | **`C`** | Trần mức ghi của AI: `C` = AI chỉ đề xuất, người bấm xác nhận; `B` = AI ghi rồi cho hoàn tác hoặc trì hoãn |
| `AI_UNDO_WINDOW_MINUTES` | mặc định `10` | mặc định `10` | Cửa sổ hoàn tác việc mức B đã ghi |

Ba bước cùng mở mới có hiệu lực: biến môi trường (bảng trên), công tắc theo nhóm/lệnh trong màn Cài đặt AI của Chủ, và công tắc vùng đỏ trong chính sách AI
(`system.auto_confirm_exact_match` cho DW-26). Đặt nhầm `AI_PRODUCTION_READY=1` trên production là lỗi cấu hình nghiêm trọng: kiểm lại sau mỗi lần `gcloud run services update`.

### Lịch chạy các job (management command)
Cơ chế giống `cancel_expired_orders`/`update_batch_status`: Cloud Run Job + Cloud Scheduler (production không có Celery/Redis). Không có endpoint HTTP kích job.
Bảng dưới là **khuyến nghị**; tạo job và lịch thật là việc deploy do Duy duyệt, chưa tạo trong lô này.

| Job | Lệnh | Tần suất khuyến nghị | Staging | Production |
|---|---|---|---|---|
| Chạy việc AI mức B tới hạn (trì hoãn 30 phút, hạ mức, đưa việc quá hạn lên Chủ) | `python manage.py run_due_ai_actions` | mỗi 5 phút (`*/5 * * * *`) | Có, khi `AI_ENABLED=1` | Chỉ khi Duy mở mức B. Tắt AI vẫn chạy được để hạ mức việc đang chờ |
| Tự khớp giao dịch chuyển khoản khớp tuyệt đối (DW-26) | `python manage.py auto_confirm_exact_payments` | mỗi 5 phút | Có, khi `AI_PRODUCTION_READY=1` và Chủ mở công tắc `system.auto_confirm_exact_match` | **Không tạo job** (job chạy cũng chỉ trả `PRODUCTION_NOT_READY`) |
| Thời hạn CSKH (nhắc, chuyển Quản lý, tự huỷ nếu bật) | `python manage.py process_cskh_deadlines` | mỗi 5 phút (`*/5 * * * *`) | Có | Có, sau khi `legal-vn` duyệt câu thông báo huỷ (xem `doc/ops/go-live-phap-ly.md`) |
| Giám sát job CSKH | `python manage.py check_cskh_job_health` | mỗi 15 phút, exit code 1 thì cảnh báo | Có | Có |

Các job đều idempotent (khoá dòng, chạy lại không làm hai lần). Log job chỉ ghi mã việc/mã giao dịch/tên lỗi, không ghi tên, SĐT, địa chỉ hay nội dung chuyển khoản.

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
- Staging được gắn header `X-Robots-Tag: noindex, nofollow` qua `firebase.staging.json` để chặn máy tìm kiếm index; sau deploy kiểm bằng `curl -sI https://cangca-loc-staging.web.app/shop/ | grep -i x-robots-tag` và `https://cangca-erp-staging.web.app/`.

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

## Nhật ký deploy staging
- **2026-09-30 — P1–P8 lên staging** (commit `6da8dd7`): image `api:v6`, revision `cangca-api-staging-00003-7sv` (rollback: `00002-4nl`, image `api:v5`). Chạy 21 migration trên `cangca_staging` bằng job **`cangca-migrate-staging`** (mới, đọc secret staging; đổi lệnh bằng `--args`, mặc định `manage.py,migrate,--noinput`). Thêm env `ITEM_IMAGE_STORAGE=gcs`, `ITEM_IMAGE_BUCKET=cangca-item-images-keolai-staging`. AI vẫn tắt (`AI_ENABLED` chưa đặt). `backfill_credit_notes` dry-run: 0 đơn cần lập bù. Shop/ERP staging build trỏ API staging, `check-no-mock` xanh, header noindex có. Adapter không đổi. Bucket ảnh cả hai môi trường: liệt kê công khai trả 403 (đã kiểm).
