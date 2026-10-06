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
| Tài khoản thử (QA/team, tạo 2026-09-27) | `demo_chu` (nhóm `owner`) · `demo_nv_kho` · `demo_nv_giao` — cùng mật khẩu, **không ghi mật khẩu vào repo công khai**; hỏi Duy/điều phối khi cần | — |

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
| Thời hạn xác nhận đơn (nhắc, chuyển Quản lý, tự huỷ nếu bật) | `python manage.py process_confirmation_deadlines` | mỗi 5 phút (`*/5 * * * *`) | Có | Có, sau khi `legal-vn` duyệt câu thông báo huỷ (xem `doc/ops/go-live-phap-ly.md`) |
| Giám sát job xác nhận đơn | `python manage.py check_confirmation_job_health` | mỗi 15 phút, exit code 1 thì cảnh báo | Có | Có |

**Đổi tên (P8b Lô 3, gỡ ở Lô 5):** hai lệnh tên cũ `process_cskh_deadlines` và `check_cskh_job_health` **đã bị xoá** ở P8b Lô 5. Job Cloud Run nào còn
chạy tên cũ sẽ báo `Unknown command` và không chạy việc gì. Kiểm tra args của job staging và production trước khi deploy Lô 5, đổi sang
`process_confirmation_deadlines` / `check_confirmation_job_health` (cùng tham số `--grace-minutes`, cùng exit code). Logger đổi `cangca.delivery.cskh` thành
`cangca.delivery.confirmation`: nếu có bộ lọc log hay cảnh báo theo tên logger cũ thì cập nhật cùng lúc.

### Biến môi trường xác nhận đơn (P8b Lô 3, gỡ tên cũ ở Lô 5)
Từ P8b Lô 5 backend **chỉ đọc tên mới**. Các biến `CSKH_*` và `THROTTLE_CSKH_SEARCH` **không còn được đọc**: nếu Cloud Run còn đặt tên cũ, giá trị bị bỏ qua
và hệ thống chạy bằng mặc định (không báo lỗi). Duy cần đổi tên (không đổi giá trị) trước khi deploy Lô 5 nếu có đặt. Hiện staging chưa đặt biến `CSKH_*` nào;
production kiểm tra lại bằng `gcloud run services describe` trước khi lên.

| Tên (duy nhất được đọc) | Tên cũ (không còn đọc) | Mặc định | Ý nghĩa |
|---|---|---|---|
| `CONFIRMATION_MAX_UNREACHABLE_ATTEMPTS` | `CSKH_MAX_UNREACHABLE_ATTEMPTS` | 3 | Số lần gọi không được trước khi chuyển Quản lý |
| `CONFIRMATION_UNREACHABLE_WINDOW_MINUTES` | `CSKH_UNREACHABLE_WINDOW_MINUTES` | 30 | Cửa sổ (phút) để chuyển Quản lý |
| `CONFIRMATION_MIN_RETRY_MINUTES` | `CSKH_MIN_RETRY_MINUTES` | 10 | Giãn cách tối thiểu giữa hai lần gọi |
| `CONFIRMATION_MANAGER_DECISION_MINUTES` | `CSKH_MANAGER_DECISION_MINUTES` | 30 | Hạn Quản lý quyết định trước khi tự huỷ |
| `CONFIRMATION_PII_RECENT_DAYS` | `CSKH_PII_RECENT_DAYS` | 7 | Số ngày dữ liệu khách còn thấy được với vai CSKH |
| `CONFIRMATION_CLAIM_MINUTES` | `CSKH_CLAIM_MINUTES` | 5 | Thời gian giữ phiếu khi nhận gọi |
| `CONFIRMATION_EXTEND_MAX_HOURS` | `CSKH_EXTEND_MAX_HOURS` | 24 | Giới hạn gia hạn |
| `CONFIRMATION_WORKING_HOURS` | `CSKH_WORKING_HOURS` | `07:00-21:00` | Khung giờ gọi (cũng hiện trên Shop) |
| `CONFIRMATION_QUEUE_ALERT_MINUTES` | `CSKH_QUEUE_ALERT_MINUTES` | 60 | Ngưỡng cảnh báo phiếu chờ gọi lâu |
| `CONFIRMATION_AUTO_CANCEL_ENABLED` | `CSKH_AUTO_CANCEL_ENABLED` | 0 | Cờ tự huỷ (chỉ bật sau khi `legal-vn` duyệt) |
| `CONFIRMATION_NOTICE_ENABLED` | `CSKH_NOTICE_ENABLED` | 1 | Hiện thông báo quy trình gọi trên Shop |
| `THROTTLE_CUSTOMER_SEARCH` | `THROTTLE_CSKH_SEARCH` | `30/min` | Giới hạn tốc độ tìm kiếm khách (route `confirmation/search/`; route `cskh/search/` đã gỡ) |

### Biến môi trường phạm vi dữ liệu khách (SR-PII-02)
| Tên | Mặc định | Ý nghĩa |
|---|---|---|
| `DELIVERY_PII_RECENT_DAYS` | 7 | NV giao còn thấy tên, SĐT, địa chỉ, ghi chú của khách ở phiếu giao đã kết thúc (hoàn tất, huỷ) trong N ngày lịch giờ VN, kể từ ngày kết thúc. Quá hạn thì API trả `null` cho các trường đó. Không cần đặt nếu dùng 7 |

Deploy bản này có kèm data migration `accounts/0012` (gỡ `sales.view_customer` khỏi nhóm NV kho), chạy `manage.py migrate` như thường.

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
- **ERP, cờ giao diện AI:** `NEXT_PUBLIC_AI_FEATURES` (đọc ở một chỗ, `erp-console/shared/lib/features.ts`). **Mặc định tắt**: vắng cờ hoặc giá trị khác "1" đều ẩn menu, trang `/ai/*`, khối Trợ lý AI và nút AI (SR-HIDE-AI-01). Build với `NEXT_PUBLIC_AI_FEATURES=1` để bật lại. Cờ chỉ ẩn giao diện, backend `AI_ENABLED` là việc riêng.
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
- **2026-10-01 — Duy yêu cầu gỡ chặn BR-BH-17 trên staging:** `PRIVACY_CONSENT_REQUIRED=0` (revision `cangca-api-staging-00004-xqj`). Shop staging nhận đơn khi chưa có trang chính sách; có trang thì ô đồng ý là tuỳ chọn. **Production chưa đổi** (vẫn mặc định `1`) — quyết định riêng khi mở production (xem `go-live-phap-ly.md`).
- **2026-10-01 — P8b Lô 3 lên staging** (commit `849494d`): image `api:v7`, revision `cangca-api-staging-00005-7fp` (rollback: `00004-xqj`). Không migration. Route mới `/api/confirmation/*`, `receive-batches`, khoá `confirmation_*`/`confirmation_policy` chạy song song tên cũ. Shop/ERP staging build lại; ERP route `/confirmation/` (redirect `/cskh/`). Env `CSKH_*` chưa đặt trên staging (dùng mặc định) — không cần đổi. Logger đổi tên `cangca.delivery.confirmation`.
- **2026-10-01 — P8b Lô 4a + phạm vi dữ liệu khách lên staging** (commit `fd3b3bb`): image `api:v8`, revision `cangca-api-staging-00007-leg` (rollback: chạy job `cangca-migrate-staging` image v8 `--args manage.py,migrate,accounts,0011` rồi chuyển traffic về `00005-7fp`/v7). Migration: `accounts 0012` (gỡ `view_customer` của NV kho), `accounts 0013` (đổi tên 5 Group giữ id: owner, manager, warehouse_staff, delivery_staff, customer_service), `ai 0003` (khoá AI tiếng Anh, append phiên bản). `preview_group_rename` trước/sau: 0 xung đột, 0 Group lạ, số quyền/thành viên giữ nguyên (warehouse_staff 37→36). Env mới: `DELIVERY_PII_RECENT_DAYS` (mặc định 7, chưa đặt).
- **2026-10-01 — P8b Lô 4b + lưu cài đặt AI + RA-04 lên staging** (commit `48d5321`): image `api:v9`, revision `cangca-api-staging-00007-gck` (không migration; rollback về revision v8). Job `cangca-migrate-staging` đổi image v9. Shop + ERP staging build lại (ERP dùng tên Group/lệnh AI tiếng Anh — chỉ chạy được với BE đã migrate `accounts 0013` + `ai 0003`). AI vẫn tắt trên staging.

> ⚠️ **Trước khi đưa P8b Lô 5 lên production (techlead 01/10):** từ Lô 5 backend **không còn đọc** env `CSKH_*` / `THROTTLE_CSKH_SEARCH` và đã xoá lệnh `process_cskh_deadlines`, `check_cskh_job_health`.
> 1. Đổi tên mọi env `CSKH_*` → `CONFIRMATION_*` (giữ nguyên giá trị) trên `cangca-api` **trước** khi deploy. Không đổi thì mặc định chạy thay: ví dụ `CSKH_NOTICE_ENABLED=0` sẽ thành **bật**, `CSKH_AUTO_CANCEL_ENABLED=1` sẽ thành **tắt**.
> 2. Đổi args Cloud Run Job / Scheduler sang `process_confirmation_deadlines`, `check_confirmation_job_health`.
> 3. Chạy `preview_group_rename` (image mới) → 0 xung đột, 0 Group lạ → `migrate` (gồm `accounts 0012/0013`, `ai 0003` và mọi migration P1–P8 còn thiếu) → chạy lại preview (id/quyền/thành viên giữ, `warehouse_staff` −1 quyền) → **mới** chuyển traffic BE → smoke → deploy FE. BE Lô 5 không được chạy trên DB còn tên Group cũ.
- **2026-10-01 — P8b Lô 5 lên staging** (commit `6e37d08`): image `api:v10`, revision `cangca-api-staging-00008-ssf` (không migration; rollback về revision v9 `00007-gck` + FE bản trước). Staging không có env `CSKH_*` và không job nào gọi lệnh cũ. Smoke: `/api/cskh/queue/` 404, `/api/confirmation/queue/` 401, site-info chỉ còn `confirmation_policy`. Shop + ERP staging build lại; ERP `/cskh/` 404 tĩnh.
- **2026-10-03 — ERP theo design Lô 1–13 + Lô bổ sung A lên staging** (commit `e8bd360`): image `api:v11`, revision `cangca-api-staging-00009-5s9` (rollback: chuyển traffic về `00008-ssf`/v10 — các migration mới chỉ thêm nên v10 vẫn chạy được trên DB đã migrate). Job `cangca-migrate-staging` đổi image v11, chạy 9 migration: `delivery 0005–0007`, `inventory 0005–0008`, `sales 0012–0013`. Smoke: `/api/ai/status/`, `/api/sales/customer-directory/search/`, `/api/inventory/reconciliations/` trả 401 (route có), `/api/public/site-info/` và `/api/shop/catalog/` 200. ERP + Shop staging build lại trỏ API staging (`check-no-mock` xanh, không còn `localhost:8000`), header noindex có. Quyền deploy staging cho Claude: `.claude/settings.local.json` (không commit).
- **2026-10-05 — Ẩn tính năng AI (SR-HIDE-AI-01/02) lên staging** (commit `416e90a`): chỉ build lại ERP staging, không có `NEXT_PUBLIC_AI_FEATURES` nên AI bị ẩn. Backend, Shop và adapter không đổi. `check-no-mock` xanh, header noindex có. Rollback: build lại commit `d5b37d1` và deploy ERP staging.
- **2026-10-08 — Đợt 06–08/10 lên staging** (commit `c0e5522`): image `api:v13`, revision `cangca-api-staging-00011-4xg` (rollback: chuyển traffic về `00010-zl5`/v12 — 9 migration mới chỉ thêm bảng/cột/quyền nên v12 vẫn chạy được). Job `cangca-migrate-staging` đổi image v13, chạy: `accounts 0014–0015` (phạm vi dữ liệu theo nhóm, gieo theo hiện trạng), `delivery 0008–0010` (kịch bản gọi, quyền, `decision_note`), `inventory 0009` (xoá mềm phiếu hàng hoàn), `sales 0014–0016` (`cancel_note`, quyền V2 "Xem thông tin khách trên đơn" cấp cho 5 nhóm). Gồm: #3/#8, CSKH Lô 5, rà soát C/D/E, Lô 15, Phạm vi Lô 1–3, AuditLog không chép chữ tự do, nút Liên hệ, lô dọn chữ AI (`ai_features_enabled`), W37 L1/L2/L4 (đơn tự Hoàn tất; lệnh `backfill_completed_orders` **chưa chạy**), #15 BE+FE, #8 FE. AI vẫn tắt. Smoke: catalog/site-info 200; `/me`, `record-late`, `staff/groups`, `delivery/notes/lookup`, `confirmation/scripts` 401. ERP + Shop staging build lại trỏ API staging, `check-no-mock` + `check-ai-chunks` xanh, header noindex có. **Không** gồm Phạm vi Lô 4–5 và F1 (chờ Duy D-3).
- **2026-10-08 — W37 L3 + sửa mock lọt bản build lên staging** (commit `00da7e8`): image `api:v14`, revision `cangca-api-staging-00012-w4t` (rollback: `00011-4xg`/v13; không migration mới). ERP + Shop build lại; `check-no-mock` (đã quét `*.mock.ts`) xanh, grep seed mock trên `out/` rỗng, không còn `localhost:8000`. **Chạy `backfill_completed_orders` trên staging** (job `cangca-migrate-staging` với `--args`): `--dry-run` → 1 đơn; chạy thật → "Đã chuyển 1 đơn"; chạy lại `--dry-run` → 0 đơn. Mã đơn không ghi vào doc (repo công khai). Production chưa chạy — chờ Duy duyệt.
- **2026-10-08 — Lô áp tên chuẩn + Lô 17a lên staging** (commit `42d5b8b`): image `api:v15`, revision `cangca-api-staging-00013-5q6` (rollback: `00012-w4t`/v14 — 11 migration chỉ đổi metadata `choices`/`verbose_name` + data migration `accounts 0017/0018` đổi `auth_permission.name`, có chiều ngược). Migration: `accounts 0016–0018`, `catalog 0004`, `content 0003`, `delivery 0011`, `inventory 0010`, `purchasing 0004`, `reports 0003`, `sales 0017–0018`. Smoke: catalog/site-info 200, các route có quyền 401. ERP + Shop build lại, `check-no-mock` xanh, không còn `localhost:8000`.
