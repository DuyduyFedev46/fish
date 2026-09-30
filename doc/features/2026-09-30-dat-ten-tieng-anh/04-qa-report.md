# QA — P8b Đổi tên định danh sang tiếng Anh

## Lô 0 — Chặn định danh tiếng Việt mới · lần 1 · 01/10/2026

### Kết luận: APPROVED — mọi ca chặn/không-chặn chính đều đúng trên Python 3.11, 3.12, 3.14; 2 lỗi Low ghi nhận, không chặn
### Tổng: 99 ca · ✅ 97 · ❌ 2 (đều Low) · ⏸ 0

Phạm vi: `scripts/check_naming.py`, `scripts/naming_blocklist.txt`, `scripts/naming_baseline.json`, mục "Đặt tên" trong 5 skill và `AGENTS.md`. Không sửa code sản phẩm. Toàn bộ ca thử tạo/sửa file đều chạy trong bản clone tạm (`scratchpad/qa-p8b-l0/repo`); repo thật không bị đụng, `git status` ở repo thật sau QA giống lúc bắt đầu (6 file sửa skill/AGENTS + 5 file chưa theo dõi của Lô 0). Không có ảnh chụp, không dữ liệu khách (script chỉ quét tên trong code).

Mỗi ca chạy trên 3 phiên bản Python (3.11.4, 3.12.13, 3.14.4); kết quả giống nhau ở mọi ca.

### Theo yêu cầu giao

| # | Yêu cầu | Kết quả | Bằng chứng |
|---|---|---|---|
| 1 | HEAD sạch → exit 0 | ✅ | Python 3.10, 3.11, 3.12, 3.13, 3.14: đều in `check_naming: OK - 7584 vi phạm cũ trong 277 file`, exit 0. `--self-test` OK trên cả 5 bản. |
| 2 | Ca phải bắt (exit 1, đúng file:dòng:token) | ✅ 47/48, ❌ 1 (B2) | Bảng C01–C48 dưới đây |
| 3 | Ca không được bắt | ✅ 22/23, ❌ 1 (B1) | Bảng N01–N23 dưới đây |
| 4 | `naming: allow` không lý do vẫn bị bắt | ✅ 8/8 | Bảng A01–A08 |
| 5 | `git mv` + baseline | ✅ 6/6 | Mục "Ca kế thừa baseline" |
| 6 | Thời gian < 10 s; backend 1674 OK | ✅ | 1,2 đến 1,9 giây trên repo thật; `manage.py test`: `Ran 1674 tests in 75.434s OK` |

### Ca phải bắt (mỗi ca kiểm exit 1 và đúng `file:dòng 'token'`)

| Ca | Mẫu | KQ |
|---|---|---|
| C01 | `def tinh_tien_hang` (py) → `:4 'tinh_tien_hang'` | ✅ |
| C02 | biến snake `so_luong_kho` | ✅ |
| C03 | biến camelCase `soLuongKho` | ✅ |
| C04 | class PascalCase `PhieuGiaoHang` | ✅ |
| C05 | tham số/thuộc tính `khach_hang`, `ten_kho` | ✅ |
| C06 | hàm tiếng Việt trong file test | ✅ |
| C07 | TS function camel `tinhTienHang` | ✅ |
| C08 | TS const snake | ✅ |
| C09 | TS type PascalCase | ✅ |
| C10 | TSX component `DanhSachKho` | ✅ |
| C11 | TSX field interface `soLuongNhap` (dòng 2) | ✅ |
| C12 | tên file py mới `phieu_giao.py`, nội dung sạch → `(tên file/thư mục)` | ✅ |
| C13 | tên file ts `nhapLo.ts` | ✅ |
| C14 | tên file tsx `CskhPanel.tsx` | ✅ |
| C15 | thư mục mới `nhap_lo/` | ✅ |
| C16 | route py `"api/nhap-lo/"` | ✅ |
| C17 | route ts `fetch("/api/nhap-lo/")` | ✅ |
| C18 | `data-testid="nhap-lo-form"` (tsx, dòng 2) | ✅ |
| C19 | `data-testid="cskh-notice"` | ✅ |
| C20 | f-string không khoảng trắng `f"/x/{so_luong_kho}/"` (py sản phẩm) | ✅ |
| C21 | f-string có khoảng trắng, biến đã khai/nhập trong file | ✅ (bắt ở dòng khai) |
| C22 | f-string có khoảng trắng, thuộc tính tiếng Việt không khai trong file | ❌ B2 (Low) |
| C23 | template TS `` `/api/${x}/nhap-lo` `` | ✅ |
| C24–C27 | cặp `trang_thai`, `don_hang`, `donHang`, `TrangThai` (py, ts) | ✅ |
| C28–C32 | `todayVn`, `todayVN`, `VN_TZ` (py, ts), `vn_today` | ✅ (hit `today+vn`, `vn+tz`, `vn+today`) |
| C33 | `lo7_undo` | ✅ |
| C34 | tên file test `test_l7_undo.py` | ✅ |
| C35 | `p8_lo5_check.py` (e2e) | ✅ |
| C36 | `qa-lo7-flow.py` | ✅ (hit `qa+lo`) |
| C37 | `ra_soat_ton` | ✅ |
| C38–C41 | biến env `CSKH_CALL_HOURS`, `NEXT_PUBLIC_CSKH_ON`; khoá localStorage `cave_draft_nhap_lo`; Group `"nv_kho"` | ✅ |
| C42–C45 | e2e py, `.mjs`, adapter, erp-console ts | ✅ |
| C46–C48 | file CŨ trong baseline tăng 1 vi phạm: `sales/orders/services.py` (3→4, in `:460`), `erp-console/shared/lib/format.ts` (in `:123`), test cũ `test_f1_fefo.py` (in `:213`); in `[tăng so với baseline N]` | ✅ |
| X01–X06 | bổ sung: `ban_hang`, `thuMua`, `quan_ly`, `bosung`/`bo_sung`, `qua_han`, `self.chu`/`client_kho` | ✅ |

### Ca KHÔNG được bắt

| Ca | Mẫu | KQ |
|---|---|---|
| N01–N02 | chuỗi hiển thị py có dấu / không dấu có khoảng trắng ("Nhập lô hàng", "Khong du ton kho") | ✅ |
| N03–N04 | comment; docstring module, class, hàm | ✅ |
| N05b | từ Anh `ton don hang ban chi lo GUI channel`, `class Ban`, `def chi` (py) | ✅ (N05 bản đầu lỗi do mẫu của QA dùng `chi_tiet`, `tiet` là từ Việt nên bị bắt đúng) |
| N06–N07 | `# naming: allow - <lý do>` và `(khoá cũ)` | ✅ |
| N08 | file test: chuỗi `"kho1"`, `"nv_kho"`, `"chu_vua"` | ✅ |
| N09–N11 | TS chuỗi hiển thị, comment, JSX text/`title="Kho hàng"`/`{/* cskh */}` | ✅ |
| N12 | TS từ Anh `ton don hang ban chi lo GUI channel` | ✅ |
| N13 | TS `// naming: allow - <lý do>` | ✅ |
| N14–N15 | `mock.ts`, `*.mock.ts`: chuỗi dữ liệu demo | ✅ |
| N16 | `frontend/app/bai-viet/` (miễn đường dẫn) | ✅ |
| N17, N19–N23 | từ hoa đầu "Ghi/Chu/NCC", mã `TOM-SU-1`, `BR-LO-04`, múi giờ IANA, tên chuẩn mới (`VN_TIME_ZONE`, `todayInVietnam`, `ROLE.warehouseStaff`), regex literal, test hàm Anh + docstring Việt | ✅ |
| N18 | chuỗi `"?chuyen-muc=ca"` và `` `/bai-viet?chuyen-muc=${s}` `` ngoài thư mục miễn | ❌ B1 (Low) |

### `naming: allow` KHÔNG lý do (phải vẫn bị bắt)

| Ca | Mẫu | KQ |
|---|---|---|
| A01–A05 | `# naming: allow` trần; `allow -` rỗng; `allow - ` + khoảng trắng; TS trần; TS `allow ()` | ✅ bị bắt, đúng dòng |
| A06 | marker hợp lệ ở dòng TRÊN, tên vi phạm ở dòng dưới | ✅ bị bắt (`:2`) |
| A07 | lý do 1 ký tự (`- x`) | ✅ bị bắt |
| A08 | `allow vi ly do` (thiếu phân cách) | ✅ bị bắt |

### Ca kế thừa baseline (trong clone tạm, baseline commit làm mốc)

| Ca | Bước | KQ |
|---|---|---|
| 5a | `git mv erp-console/features/cskh → confirmation` và `CskhQueueView.tsx → ConfirmationQueueView.tsx`, commit, KHÔNG `--update` | ✅ exit 0, không "[file mới]", tổng giảm 7584 → 7576 (vì tên thư mục/file hết `cskh`) |
| 5a' | `git mv` đã stage, chưa commit | ✅ exit 0 |
| 5b | Sửa bớt vi phạm trong file đã dời (`types.ts` 12 → 8) rồi `--update` | ✅ `Đã ghi baseline: 7572 (trước đó 7584)`; khoá cũ `features/cskh/*` biến mất, `confirmation/types.ts` = 8 |
| 5b' | Commit rồi chạy lại | ✅ exit 0 |
| 5c | Thêm lại 1 vi phạm vào file đã dời | ✅ exit 1: `[tăng so với baseline 8] ...types.ts:211 'CskhDecision'` |
| 5d | `--update` khi đang có file tăng | ✅ từ chối, exit 1, baseline không đổi |

### Khác

| Ca | KQ | Bằng chứng |
|---|---|---|
| Thời gian < 10 s | ✅ | 1,2 đến 1,9 giây (3.10 chậm nhất 1,92 giây) |
| Backend không đổi số test | ✅ | `cd backend && DJANGO_DEBUG=1 env -u DATABASE_URL .venv/bin/python manage.py test` → `Ran 1674 tests in 75.434s OK` |
| Mục "Đặt tên (P8b" có trong 5 skill + `AGENTS.md` | ✅ | `grep -c` = 1 mỗi file; `git diff --stat`: chỉ thêm dòng (185 insertions, 0 deletions) |
| `--report` chạy, liệt kê marker | ✅ | `Dòng đang dùng naming: allow: 0` |
| Repo thật sạch sau QA | ✅ | `git status` không có file tạm; không có file test tạm nào được ghi vào repo thật |

### Lỗi (đều Low, không chặn)

**B1 — Tham số `chuyen-muc` chỉ được miễn khi cả chuỗi bằng đúng `chuyen-muc` · Low · 02c R13**
- Tái hiện: trong file ngoài `frontend/app/bai-viet/`, thêm `export const q = "?chuyen-muc=ca";` hoặc `` `/bai-viet?chuyen-muc=${s}` `` → exit 1 (`'?chuyen-muc=ca' -> chuyen`).
- Mong đợi: R13 nói tham số `chuyen-muc` nằm trong danh sách miễn, nên link `?chuyen-muc=` ở nơi khác (sitemap, link nội bộ) không phải báo động giả.
- Thực tế: `EXEMPT_LITERALS` so khớp nguyên chuỗi. Hiện HEAD không có chỗ nào khác dùng nên chưa gây lỗi.
- Ảnh hưởng: báo động giả khi có người thêm link mới; cách tránh là `// naming: allow - URL công khai chuyen-muc (R13)`. Đề xuất: miễn theo chuỗi con `chuyen-muc`.

**B2 — f-string có khoảng trắng chứa thuộc tính tiếng Việt chưa khai trong file không bị bắt · Low · luật đặt tên**
- Tái hiện: `backend/apps/common/qa_probe.py` (file mới) gồm `def g(obj):\n    return f"Tong {obj.so_luong_kho} kg"` → exit 0 trên 3.11, 3.12, 3.14 (cùng kết quả, nhất quán giữa các bản).
- Mong đợi: yêu cầu giao "f-string có biến tiếng Việt" bị bắt.
- Thực tế: f-string được coi là một chuỗi literal; có khoảng trắng thì coi là chữ hiển thị nên không xét phần `{...}`. Biến tiếng Việt không có khoảng trắng (`f"/x/{so_luong_kho}/"`, C20) hoặc đã khai/nhập trong file (C21) thì bị bắt.
- Ảnh hưởng: nhỏ. Tên tiếng Việt chỉ tồn tại nếu đã khai ở đâu đó trong repo (chỗ khai bị bắt/nằm trong baseline). Chỉ lọt khi dùng lại thuộc tính cũ đã có trong baseline. Đề xuất (không bắt buộc): tách biểu thức `{...}` của f-string rồi quét như code.

### Ghi nhận thiết kế (không phải lỗi)
- Baseline tính theo tổng số vi phạm mỗi file, nên trong file cũ có thể bỏ 3 vi phạm rồi thêm 2 vi phạm mới mà vẫn exit 0 cho tới khi chạy `--update` (thử: `sales/orders/services.py`, đổi `cskh_services` → `confirmation_services` và thêm `def tinh_tien_hang()` → exit 0, thông báo "1 file đã giảm"). Đúng theo 02c ("số vi phạm tăng") nhưng có khe hở tạm: nên chạy `--update` ngay sau mỗi lần đổi tên, như 03-dev-notes đã nhắc.
- f-string trong file test và `mock.ts` không xét biến bên trong (theo thiết kế: file test chỉ xét định danh đã khai).
- Một số từ Anh/Việt trùng (`ton don hang ban chi lo ...`) chỉ bị chặn khi thành cặp; đã kiểm đúng (`ban_hang`, `don_hang`, `trang_thai` bị bắt; `ban`, `don`, `chi` đứng riêng thì không).

### Phân quyền, rò giá vốn, rò dữ liệu cá nhân, hồi quy
Lô 0 chỉ thêm script quét tên và thêm đoạn văn bản vào skill/`AGENTS.md`, không đổi code chạy, API, DB hay migration. Không áp dụng ca phân quyền/giá vốn/PII mới. Script chỉ in đường dẫn, dòng, token tên; không đọc dữ liệu khách; baseline chỉ chứa đường dẫn và số đếm. Hồi quy: backend 1674 test OK.

### Lệnh đã chạy (tóm tắt)
- `python3 scripts/check_naming.py` và `--self-test` trên Python 3.10, 3.11, 3.12, 3.13, 3.14: OK, exit 0, 1,2 đến 1,9 giây.
- Harness tự viết (`scratchpad/qa-p8b-l0/harness.py` + `cases_catch.py`, `cases_nocatch.py`, `cases_extra.py`, `cases_c48.py`): mỗi ca ghi file tạm trong clone, chạy 3 phiên bản Python, kiểm exit code và `file:dòng 'token'`, rồi gỡ file. Một ca (N16) ghi đè rồi xoá file thật `frontend/app/bai-viet/page.tsx` trong clone, đã `git checkout` lại; không ảnh hưởng repo thật.
- Clone tạm: `git clone --local`, chép 3 file `scripts/`, commit làm mốc baseline; ca `git mv`, `--update` chạy ở đó.
- `cd backend && DJANGO_DEBUG=1 env -u DATABASE_URL .venv/bin/python manage.py test` → 1674 OK.
