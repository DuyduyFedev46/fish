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

---

## Lô 1 — Đổi tên nội bộ sang tiếng Anh (`cskh`→`confirmation`, `NhapLo*`→`ReceiveBatches*`, gom Group vào `roles.py`/`roles.ts`) · lần 1 · 01/10/2026

### Kết luận: APPROVED — hành vi và contract y nguyên (HEAD và working tree cho cùng JSON, cùng ma trận quyền, cùng màn hình), không có lỗi chặn
### Tổng: 47 ca · ✅ 47 · ❌ 0 · ⏸ 0 (kèm 1 phát hiện có từ trước về quyền dữ liệu khách ở mục "Ghi nhận", không do Lô 1)

Cách chứng minh: dựng bản HEAD (`git archive`) và working tree cạnh nhau, cho cùng dữ liệu giả (`seed_demo`), cùng bộ request, rồi so JSON đã chuẩn hoá (bỏ id, thời điểm, hậu tố ngẫu nhiên). Cây mã đổi giữa chừng (Techlead/BE sửa theo review: đưa `command_groups.py` lên `apps/ai/`, đổi kwarg `active_owner_ids`→`owner_ids`), nên toàn bộ kiểm backend và FE đã chạy lại ở cây cuối, dấu vân tay cây `98c06412c04f` (đo đầu và cuối mỗi lượt, không đổi).

### Theo yêu cầu giao
| Mã | Kết quả | Bằng chứng |
|---|---|---|
| Contract API không đổi (route, JSON, status) | ✅ | 1704 request (mọi route `/api/` × 6 danh tính anon/chu/quan_ly/nv_kho/nv_giao/cskh + ca riêng `cskh/*`, `nhap-lo`). HEAD vs working tree: 0 dòng khác biệt; chạy 2 lần trên DB mới (0 khác), 1 lần trên DB do HEAD tạo rồi chạy mã mới (0 khác). Kiểm chứng: chạy HEAD vs HEAD cũng 0. |
| Ma trận phân quyền không đổi | ✅ | Nằm trong 1704 request trên: status từng (danh tính × route) giống hệt, gồm 401 cho anon và 403 cho Group thiếu quyền |
| Tên Group/giá trị Group trong DB không đổi | ✅ | `groups_in_db`, `group_perm_counts`, `group_ids` giống HEAD; `makemigrations --check`: "No changes detected"; không có file migration mới/sửa |
| R3: test Group xanh, không đổi assertion | ✅ | `backend` test 1674 OK (không `--parallel`). Kiểm AST diff test: 1722 hàm test giống nhau, chỉ khác dòng import/hằng số/tên đổi; 0 assertion bị sửa hay xoá |
| R8: bản chụp chỉ mục lệnh AI không đổi | ✅ | `ai_index` của 5 vai + chi tiết từng lệnh giống HEAD; giá trị nhóm lệnh `thu_mua/ban_hang/cskh` và độ nhạy `cao/trung_binh/thap` vẫn là giá trị cũ (đổi ở Lô 4) |
| Giữ nguyên các thứ chủ định chưa đổi (route `/api/cskh/*`, `url_path="nhap-lo"`, khoá `cskh_*`, `cskh_notice`, env `CSKH_*`, logger, management command, `me.home = "cskh-queue"`, tiền tố nháp `cave_draft_nhap_lo`) | ✅ | Có trong bản so JSON; 2 management command (`process_cskh_deadlines`, `check_cskh_job_health`) cùng output; e2e nháp Nhập lô vẫn dùng khoá `cave_draft_nhap_lo:<id>` |
| Adapter | ✅ | `adapter` pytest 68 passed |
| Quét tên | ✅ | `python3 scripts/check_naming.py` exit 0; `naming_baseline.json` 6724/224, không tệp nào tăng |
| FE: `/cskh/` mở được với tài khoản cskh, nav đúng theo 5 Group, `me.home` cskh về đúng trang | ✅ | `nav_compare.py` (mock) và `real_stack.py` (Django thật + bản build ERP thật): chung kết quả HEAD/working tree cho 5 vai (chi tiết bên dưới) |
| FE e2e 4 kịch bản + Shop | ✅ | Bảng "FE" bên dưới |
| `npm ci` + tsc + build thật + `check-no-mock` + `check-ai-chunks` | ✅ | Bảng "Lệnh đã chạy" |

### Ngoại lệ & biên (mỗi AC có ít nhất một ca ngoài đường thuận)
| Ca | Kết quả | Bằng chứng |
|---|---|---|
| Nhập lô hợp lệ 201 cho chu/quan_ly/nv_kho; nv_giao, cskh, anon bị chặn đúng mã | ✅ | Driver: 6 danh tính × 4 biến thể (ok, replay, lines rỗng, qty âm), trạng thái và body giống HEAD |
| Idempotent replay cùng `idempotency_key` (gửi 2 lần) | ✅ | Biến thể "replay" giống HEAD, không tạo lô thứ 2 |
| Biên: `lines=[]`, `qty=-1` | ✅ | 400 cùng body tiếng Việt như HEAD |
| Đã có giao dịch / DB cũ: DB tạo bởi HEAD, chạy mã mới | ✅ | `out-legacy-head` vs `out-legacy-work` giống nhau |
| Job chạy 2 lần (management command) | ✅ | Chạy 2 lần, cùng output, không đổi số phiếu/đơn |
| Màn hình cũ, trạng thái đã đổi (đơn đã huỷ khi Quản lý đang mở hộp) | ✅ | `sr09_ac4_stale_state.py` 22 PASS (bằng số PASS của HEAD) |
| Khoá nháp Nhập lô: dọn khi đăng xuất, không lưu giá mua, tách theo người | ✅ | `sr07_nhap_lo_draft.py` 18 PASS (bằng HEAD), storage không chứa giá gõ thử |
| Gõ giá mua 987000 ở ERP thật, sau đó kiểm localStorage/sessionStorage/URL/console | ✅ | `real_stack.py`: `leaks []` cho cả 5 vai |
| Cờ/tham số: `?state=PENDING`, `?state=CALLBACK`, `?page_size=1`, `queue/1/claim/` | ✅ | Có trong driver, giống HEAD |
| Kiểm tên kwarg `owner_ids` (đổi giữa QA) còn nơi gọi sót | ✅ | `grep`: chỉ 3 tệp `staff/{api,serializers,services}.py`; không gọi sót; test staff (`test_q1_concurrency`, `test_s41_*`, `test_s42_*`) nằm trong 1674 OK |

### FE (chạy thật, cây cuối `98c06412c04f`)
| Kịch bản | Kết quả | Ghi chú |
|---|---|---|
| `erp-console/e2e/sr09_ac4_stale_state.py` (mock, cổng 3233) | ✅ 22 PASS, 0 FAIL | HEAD cũng 22 |
| `erp-console/e2e/sr07_nhap_lo_draft.py` | ✅ 18 PASS, 0 FAIL | HEAD 18 |
| `erp-console/e2e/p8_lo7_fe_erp.py` | ✅ 79 PASS, 0 FAIL | HEAD 79 |
| `erp-console/e2e/p8_lo5_fe_lo_qua_han.py` | ✅ 77 PASS, 0 FAIL | HEAD 77 |
| `frontend/e2e/qa-lo7-shop-real.py` (build thật, API giả) | ✅ 21 ca, 0 FAIL | |
| `frontend/e2e/qa-lo6-sr21-shop.py` (build thật) | ✅ 279 ca, 0 FAIL | Chú ý: biến `QA_OUT_DIR` phải trỏ đúng thư mục build; lần đầu tôi trỏ nhầm nên 1 ca báo FAIL (lỗi cách chạy của tôi, không phải lỗi sản phẩm), chạy lại đúng thì xanh |
| `nav_compare.py` (mock, 6 tài khoản × desktop/mobile = 12 tổ hợp) | ✅ | Trang đích, menu, khoá storage, URL và nội dung `/cskh/` giống HEAD ở 12/12; khác duy nhất là danh sách lỗi console. Phía HEAD có thêm 404 phông `material-symbols-outlined.woff2` vì tệp `.woff2` bị `.gitignore` nên không có trong `git archive` (lỗi dựng hiện trường của tôi), và cả hai phía có vài cảnh báo `Failed to fetch RSC payload` ngẫu nhiên khi trình duyệt huỷ prefetch lúc chuyển trang |
| `real_stack.py`: bản build ERP thật + Django thật (SQLite tạm, dữ liệu giả), 5 vai | ✅ | `SAME` cả 5: chu/quan_ly/kho1 vào `/overview/` (nav 24/19/14), giao1 vào `/my-deliveries/` (nav 2), **cs1 vào `/cskh/`** (nav 9, 3 thẻ hàng chờ); form Nhập lô mở cho chu/quan_ly/nv_kho và gửi được `POST .../nhap-lo/` 201; giao1/cs1 không có form. `DIFF users: 0` |

Ảnh chụp (toàn dữ liệu giả): `scratchpad/qa-p8b-l1/shots/` (`real-work-cs1-modal.png`, `real-work-loc-receive.png`, `nav-work-cs1-cskh.png`, ...).

### Phân quyền (bảng Group × hành động, đo trên Django thật, giống HEAD)
| Hành động | chu | quan_ly | nv_kho | nv_giao | cskh | chưa đăng nhập |
|---|---|---|---|---|---|---|
| `POST /api/purchasing/receipts/nhap-lo/` | 201 | 201 | 201 | 403 | 403 | 401 |
| `GET /api/cskh/queue/` | 200 | 200 | 403 | 403 | 200 | 401 |
| `POST /api/cskh/search/` | 200 | 200 | 403 | 403 | 200 | 401 |
| Nhập lô: replay / lines rỗng | 201 / 400 | 201 / 400 | 201 / 400 | 403 / 403 | 403 / 403 | 401 / 401 |
| `/api/auth/me/` (`home`) | `dashboard` | `dashboard` | `dashboard` | `my-deliveries` | `cskh-queue` | 401 |
| Vào màn `/cskh/` ở ERP thật | thấy hàng chờ | thấy hàng chờ | không thấy hàng chờ | không thấy hàng chờ | thấy hàng chờ | về đăng nhập |
Đã đối chiếu từng ô với HEAD: không ô nào khác.

### Rò giá vốn
Đã quét toàn bộ JSON của 1704 request: anon/nv_giao/cskh không có trường giá vốn (`unit_cost`, `cost_*`, `buy_price`...). Khoá mới ghi vào AuditLog `changes`/`note` hoặc trả qua API: không có (Lô 1 không thêm khoá nào; bản so JSON giống HEAD, nên không thêm đường tính ngược giá vốn). Giá mua gõ thử ở form Nhập lô không còn trong localStorage/sessionStorage/URL/console. Đạt.

### Rò dữ liệu cá nhân
- API công khai (`/api/public/site-info/`, catalog) và anon: không có trường tên/SĐT/địa chỉ khách ở bất kỳ phản hồi nào trong 1704 request; giống HEAD.
- Group thấy dữ liệu khách: cskh (đúng nghiệp vụ, SĐT có bản che `phone_masked`), nv_giao và nv_kho (xem Ghi nhận 1). Giống HEAD từng trường.
- Quét 6 SĐT giả của `seed_demo` trong console, URL, storage ở 5 vai: không có (`leaks []`).
- Log, ảnh chụp và report chỉ dùng dữ liệu giả.
- Tra đơn công khai có giới hạn tần suất: scope throttle `cskh_search` giữ tên cũ (chủ định, đổi ở Lô 3), hành vi không đổi.

### Hồi quy
Backend 1674 OK; adapter 68; ERP vitest 185/185; Shop `test-format` 26/26, `test-safe-href` 40/40; hai FE `tsc --noEmit` exit 0; `check_naming` exit 0; chứng từ không bị xoá (không có thay đổi model/migration); AuditLog ghi như cũ (test `accounts/audit` nằm trong 1674).

### Ghi nhận (không chặn Lô 1, cần Duy/Techlead xét)
1. **Dữ liệu khách hiện có từ trước, giống hệt HEAD (không do Lô 1 gây ra).** Trong 1704 phản hồi: `nv_giao` nhận `customer_phone`/`customer_name` ở `GET /api/sales/orders/` và `phone`/`default_address` ở `GET /api/sales/customers/` (gồm khách không thuộc phiếu được giao, vì bản seed chỉ phân 1 phiếu); `nv_kho` nhận `customer_name`/`address` ở `GET /api/delivery/notes/` và danh sách khách/đơn. Theo bất biến 9 ("Group không cần thì không thấy dữ liệu khách") đây là ứng viên lỗi Critical về quyền dữ liệu. Lô 1 bị ràng buộc "KHÔNG đổi hành vi" nên tôi không chấm REJECTED lô này, nhưng đề nghị mở thẻ riêng để siết phạm vi (nv_giao chỉ thấy phiếu mình được giao; nv_kho không cần SĐT). Chưa có quyết định trong `doc/decisions.md` tôi biết nói ngược lại, cần Duy xác nhận.
2. Khi `giao1` mở `/cskh/` ở ERP thật, trang vẫn tải nhưng 0 thẻ (API trả 403): giống HEAD.
3. Dựng HEAD bằng `git archive` thiếu tệp `.woff2` vì `.gitignore`; chỉ ảnh hưởng cách tôi dựng để so, không ảnh hưởng sản phẩm.

### Lỗi
Không có lỗi chặn (Critical/High/Medium). Không có lỗi Low phát sinh từ Lô 1.

### Lệnh đã chạy (tóm tắt)
- `cd backend && DJANGO_DEBUG=1 env -u DATABASE_URL .venv/bin/python manage.py test` → Ran 1674 tests, OK (73,8 giây, cây `98c06412c04f`).
- `manage.py makemigrations --check --dry-run` → No changes detected.
- `cd adapter && .venv/bin/python -m pytest -q` → 68 passed.
- `python3 scripts/check_naming.py` → exit 0.
- Contract: `scratchpad/qa-p8b-l1/driver.py` (HEAD, working tree ×2, DB do HEAD tạo) → `diff` 0 dòng trên 1704 request.
- Kiểm assertion test: `test_audit.py` (AST) → 1722 hàm test giống nhau, 0 assertion đổi.
- `cd erp-console && npm ci` (không `--legacy-peer-deps`, cache trong scratchpad) → OK; `npx tsc --noEmit` exit 0; `npm test` 14 file, 185 test đạt; build mock + 4 e2e (22/18/79/77 PASS); build thật (API 127.0.0.1:8236) + `check-no-mock` XANH + `check-ai-chunks` XANH.
- `cd frontend && npm ci` OK; `npx tsc --noEmit` exit 0; `test-format` 26/26, `test-safe-href` 40/40; build thật + `check-no-mock` XANH; `qa-lo7-shop-real.py` 21/0 FAIL; `qa-lo6-sr21-shop.py` 279/0 FAIL.
- `nav_compare.py` (12 tổ hợp) và `real_stack.py` (Django thật + ERP thật, 5 vai): SAME ở cả 5, `DIFF users: 0`.
- Bước cuối, dựng lại hai bản thật với API base production `https://cangca-api-675411800433.asia-southeast1.run.app` (truyền `NEXT_PUBLIC_USE_MOCK=0` và `NEXT_PUBLIC_API_BASE` trên dòng lệnh): ERP và Shop đều build exit 0, `check-no-mock` XANH, ERP `check-ai-chunks` XANH, `out/_next` chứa URL production (ERP 3 tệp, Shop 5 tệp), 0 tham chiếu `127.0.0.1:8236`/`localhost:8199`.
- Đã dừng mọi `http.server`/`runserver` do tôi mở (cổng 3233–3237, 8236–8237).
