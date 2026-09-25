# Deploy lần 1: ERP console mới + tài khoản & phân quyền
> Điều phối viên · 2026-09-24 · Trạng thái: **ĐÃ CHẠY 2026-09-25**. Bước 1–7 xong. Ở bước 5, Duy chọn gỡ 51 bản ghi demo cũ rồi seed bộ mẫu mới (6 mặt hàng, 6 lô, 6 đơn, 3 hoá đơn). Còn bước 8, Duy làm.

Phạm vi: S1–S9, S41, S42, S46, S47, S48, D1, sửa lỗi QA lần 2. QA lần 3 **APPROVED**.
Backend 369 test xanh (gồm sửa theo code review; QA lần 4 xác nhận trước khi chạy). Shop (`frontend/`) không đổi code nên **không deploy lại**.

## 0. Trước khi chạy
- Review mã xong, lỗi xác thực được đã sửa.
- Có 5 migration mới, tất cả chỉ **thêm**: `reports 0002`, `accounts 0003–0005` (quyền xem Tổng quan, cờ đổi mật khẩu, sổ đánh dấu dữ liệu demo).

## 1. Sao lưu DB
```bash
gcloud sql backups create --instance cangca-loc-db --project keolai-63ec1
```

## 2. Build image backend `api:v4`
```bash
gcloud builds submit backend --tag asia-southeast1-docker.pkg.dev/keolai-63ec1/cangca/api:v4 --project keolai-63ec1
```

## 3. Chạy migrate bằng image mới, trước khi đổi service
Tạo Cloud Run Job một lần tên `cangca-migrate`, dùng cùng env và Cloud SQL với `cangca-api`. Job **bắt buộc có `DJANGO_SECRET_KEY` và `DJANGO_DEBUG=0`**: từ bản này, thiếu khoá bí mật là hệ thống không khởi động. Trước khi đổi `cangca-ttl` sang v4, kiểm job đó cũng có đủ hai biến này. Chạy `manage.py migrate`, rồi `manage.py showmigrations accounts reports` để kiểm.

## 4. Đổi backend sang v4
```bash
gcloud run deploy cangca-api --image …/api:v4 --region asia-southeast1 --project keolai-63ec1
gcloud run jobs update cangca-ttl --image …/api:v4 --region asia-southeast1
```
Kiểm nhanh:
- Shop `/api/shop/catalog/` trả 200.
- `/api/auth/me/` không token trả 401.
- `/admin/` trả 302.

## 5. Dữ liệu demo trên production: hỏi Duy trước khi gỡ
```bash
manage.py seed_demo --remove --adopt-legacy --dry-run      # chạy qua job, gửi kết quả cho Duy
```
- Duy quyết có gỡ không. Nếu dry-run có dòng "Giữ lại" là **Lô hàng** thì **dừng và báo Duy** (QA ghi nhận: lô demo bị giữ vẫn bán tồn demo).
- Gỡ xong, lô demo nào còn sót thì **đóng lô trên ERP**.

## 6. Job hạn lô hằng ngày (S2)
Tạo Cloud Run Job `cangca-batch-status` chạy `manage.py update_batch_status`, image v4, env giống `cangca-ttl`, **bắt buộc có `DJANGO_SECRET_KEY` + `DJANGO_DEBUG=0`**.
Tạo Scheduler `cangca-batch-status-trigger` với lịch `5 0 * * *`, múi giờ Asia/Ho_Chi_Minh, SA `675411800433-compute@developer.gserviceaccount.com`.
Kiểm: chạy tay 2 lần liên tiếp, lần 2 phải in "Đã cập nhật 0 lô".

## 7. ERP console mới lên `cangca-erp`
```bash
cd erp-console
printf 'NEXT_PUBLIC_USE_MOCK=0\nNEXT_PUBLIC_API_BASE=https://cangca-api-675411800433.asia-southeast1.run.app\n' > .env.production
npm run build && grep -rl "demo1234" out | wc -l        # phải = 0
firebase deploy --only hosting --project keolai-63ec1
rm -rf legacy/        # D2: bản cũ quay lại được bằng rollback release của Firebase
```

## 8. Sau deploy (cần Duy làm)
1. Đăng nhập `admin` trên https://cangca-erp.web.app. Màn sẽ báo "chưa được phân quyền" vì `admin` không thuộc nhóm nào; đây là hành vi đúng.
2. Vào Django Admin (bằng superuser), **tạo tài khoản riêng `loc` thuộc nhóm `chu`**. **Không** gán `admin` vào nhóm nào. Từ đó Lộc tạo tài khoản cho từng nhân viên trên màn Nhân sự. Mỗi người phải đặt mật khẩu riêng ở lần đăng nhập đầu.
3. **Đổi mật khẩu `admin`** (mật khẩu cũ đã nằm trong lịch sử chat) và chỉ dùng tài khoản này để cứu hộ.

## Quay lại nếu có sự cố
- Backend: `gcloud run services update-traffic cangca-api --to-revisions <rev v3>=100`. Migration chỉ thêm nên code v3 vẫn chạy được trên schema mới.
- ERP: Firebase Console → Hosting → cangca-erp → Release history → Rollback.
