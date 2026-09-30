# 03 — Ghi chú dev: P8b Đổi tên định danh sang tiếng Anh

## Lô 0 — Chặn tên tiếng Việt mới (BE, 01/10)

Trạng thái: xong vòng 1 và đã sửa theo `03b-review-techlead.md` (B1, B2, R1-R6), chưa commit (chờ techlead review lại phần `scripts/`).
Không đổi tên code nào, không migration, không đụng `02*.md` và `doc/decisions.md`.

### File
Mới:
- `scripts/check_naming.py` — bộ quét (Python 3 stdlib, chạy từ gốc repo, không cần venv).
- `scripts/naming_blocklist.txt` — danh sách từ tiếng Việt bị chặn + allowlist (có giải thích ở đầu file).
- `scripts/naming_baseline.json` — `{đường dẫn file: số vi phạm}` chụp ở HEAD (8cec800): **7584 vi phạm trong 277 file** (sinh lại sau vòng sửa review, xem mục Vòng sửa review).

Sửa (chỉ thêm mục "Đặt tên" ở cuối file):
- `.claude/skills/{caveve-domain,django-drf-patterns,nextjs-shop-patterns,tdd-workflow,e2e-playwright}/SKILL.md`
  (`.agents/skills/*` là symlink về đây nên không sửa riêng).
- `AGENTS.md`.
- `tdd-workflow` có thêm cách dùng script (`--update`, `git mv`, `naming: allow`) và quy ước tên test theo hành vi;
  `e2e-playwright` có quy ước tên kịch bản, `review_*`, không mã lô.

### Cách chạy
```
python3 scripts/check_naming.py               # kiểm (exit 0 = sạch so với baseline, exit 1 = có phát sinh)
python3 scripts/check_naming.py --update      # hạ baseline sau khi đổi tên; TỪ CHỐI ghi nếu có file tăng
python3 scripts/check_naming.py --report      # liệt kê toàn bộ vi phạm cũ (file:dòng token)
python3 scripts/check_naming.py --words       # đếm theo từ bị chặn, để chọn việc đổi tên
python3 scripts/check_naming.py --self-test   # kiểm bộ quét bằng mẫu nhỏ (gồm f-string, marker, mock), chạy sau khi sửa script
```
Thời gian chạy khoảng 1,6 giây (yêu cầu < 10 giây).

### Thiết kế
- Quét file git-tracked (và file mới chưa ignore) trong `backend/ adapter/ frontend/ erp-console/`; bỏ `node_modules .next out .venv
  staticfiles shots __pycache__` và mọi thư mục `migrations`.
- Python: `tokenize`, xét token NAME và chuỗi literal; bỏ comment và docstring (chuỗi đứng đầu câu lệnh). **f-string luôn được gom
  thành một token STRING ở mọi phiên bản Python** (Python 3.12+ tách f-string thành nhiều token, `_python_tokens` gom lại bằng đoạn nguồn).
- TS/TSX: bộ quét tự viết (ngăn xếp code / thẻ JSX / nội dung JSX / template string), nhận diện regex literal; bỏ comment, bỏ chữ trong
  nội dung JSX, bỏ phần `${}` không phải code. Thuộc tính JSX dạng chuỗi (`data-testid`, `className`) vẫn xét như chuỗi literal.
- Chuỗi literal chỉ xét khi không có dấu và không có khoảng trắng (`"nhap-lo"`, `"cskh_notice"`); chuỗi chỉ gồm một từ hoa đầu
  (`"Ghi"`) hoặc toàn chữ hoa/số/gạch (`"TOM-SU-1"`, `"BR-LO-04"`) coi là chữ hiển thị/mã dữ liệu, bỏ qua.
- File test và e2e (`tests/`, `e2e/`, `test_*.py`, `conftest.py`, `*.test.*`) và **file mock FE** (`mock.ts`, `*.mock.ts`): chỉ xét định danh
  và tên file, không xét chuỗi literal (dữ liệu demo như `"kho1"` không phải định danh). Định danh trong mock vẫn bị xét.
- Tách từ theo snake, camel, kebab, bỏ chữ số cuối (`kho1` thành `kho`). Tên file cũng bị xét (`CskhNotice.tsx`, `test_p8_lo7_undo.py`).
- Đếm theo số lần trúng blocklist, không theo số định danh.
- Kế thừa khi đổi tên file: đọc `git diff -M` so với **commit gần nhất có sửa `naming_baseline.json`** (HEAD nếu baseline chưa commit),
  nên `git mv` đã stage, chưa stage, hoặc đã commit mà chưa `--update` đều kế thừa baseline của đường dẫn cũ và chỉ in dòng thực sự mới.
- Miễn vĩnh viễn (khai trong script, có comment lý do): thư mục migration; `frontend/app/bai-viet/`, `frontend/app/trang/`;
  chuỗi `chuyen-muc` và `Asia/Ho_Chi_Minh`; **chuỗi** (không phải định danh) trong `apps/accounts/roles.py`, `apps/ai/command_groups.py`,
  `apps/ai/registry/legacy_ids.py`, `erp-console/shared/lib/roles.ts`, `features/ai/commandGroups.ts`, `features/ai/legacyIds.ts` (các file này chưa
  tồn tại ở HEAD, script đã chờ sẵn); **dòng khai báo** `LEGACY_RECEIVE_BATCHES_DRAFT_PREFIX = ...` (dòng chỉ nhắc tên hằng không được miễn);
  dòng có `naming: allow - <lý do>` (thiếu lý do thì không được miễn; `--report` liệt kê các dòng dùng marker, hiện là 0).

### Blocklist và allowlist (techlead review)
- Bắt buộc theo 02c: `cskh nhap kho giao chu nv soat bosung tien`, cặp `quan+ly thu+mua ban+hang bo+sung qua+han qa+lo`,
  mẫu `lo\d+`, `testname:l\d+` (chỉ tên file/thư mục test).
- Thêm: viết tắt `ql ncc sdt mk matkhau quanly`; khoảng 90 âm tiết tiếng Việt không có nghĩa tiếng Anh; cặp `don+hang hang+hoa mat+hang
  lo+hang chot+lo tra+ton tra+don tra+hang mat+khau ton+kho`.
- Thêm theo review (B2, R5): từ đơn `cao thap`; cặp `trung+binh vn+tz today+vn vn+today year+vn` (glossary cột "Không dùng"); cặp
  `trang+thai ly+do hien+tai ket+qua nhan+vien bao+cao tao+moi dang+ban`. Bỏ `gui` và `chan` khỏi từ đơn (R6, trùng GUI / channel).
- Allowlist (không chặn từ đơn), lý do ghi đúng từng nhóm ở đầu `naming_blocklist.txt`: trùng từ tiếng Anh hợp lệ (`ban no be the cap con
  co la ...`); nằm trong URL công khai/slug/mã business rule (`bai muc trang`); từ quá phổ biến (`nhan vien sau`). Chỉ bị chặn khi đi thành cặp.
  Không có từ nào mà code sản phẩm dùng làm định danh chính thức phải miễn, nên không phải hỏi Duy.

### Vòng sửa review (03b-review-techlead.md, 01/10)
- **B1 (chặn) xong:** nguyên nhân là Python 3.12+ tách f-string. `_python_tokens` gom `FSTRING_START..FSTRING_END` (đếm lồng nhau) thành một token
  STRING từ đoạn nguồn, nên mọi phiên bản cho cùng kết quả. `--self-test` có ca f-string trong file test (`f"/x/{self.user_kho.id}/"` không tính),
  file thường (`f"nhap-lo/{x}"` bị bắt; `f"Nhập lô {x}"` không), f-string nhiều dòng và lồng nhau.
- **B2 xong:** thêm các từ ở trên. Baseline tăng ở code chạy thật (xem mục Việc cho Lô 1 bên dưới).
- **R1:** `rename_map`/`head_token_counts` so với commit của baseline (kiểm trong clone: đã commit `git mv` cskh -> confirmation chưa `--update` vẫn
  `OK`, không còn "[file mới]"). Docstring đã đúng.
- **R2:** `naming: allow` bắt buộc lý do (regex `naming: allow\s*[-:—(]\s*\S.{2,}`); miễn hằng `LEGACY_RECEIVE_BATCHES_DRAFT_PREFIX` chỉ ở dòng khai báo;
  `--report` in danh sách dòng dùng marker.
- **R3:** `legacy_ids.py`, `legacyIds.ts` chuyển sang miễn chuỗi (định danh vẫn xét). Ghi chú trong script: Lô 4 bỏ miễn `command_groups.*`, Lô 5 bỏ miễn `roles.*`.
- **R4:** `mock.ts`, `*.mock.ts` (gồm `frontend/lib/mock.ts`) xét như file test (chỉ định danh). Baseline giảm 27 (auth), 15, 14, 13... ở các mock.
- **R5, R6:** xong như trên (baseline tăng vài chục ở test vì cặp `nhan+vien`, `trang+thai`...; giảm ở các test từng trúng `gui`/`chan`).

### Baseline sinh lại ở HEAD: 7584 vi phạm, 277 file (trước đó 7647/274)
| Nhóm | File | Vi phạm |
|---|---:|---:|
| backend test (`.py`) | 148 | 6636 |
| backend code sản phẩm (`.py`) | 39 | 254 |
| adapter test (`.py`) | 2 | 43 |
| adapter code sản phẩm (`.py`) | 1 | 3 |
| erp-console code sản phẩm + mock (`.ts/.tsx`) | 38 | 404 |
| erp-console test (`.ts/.tsx`) | 4 | 97 |
| erp-console e2e (`.py`) | 23 | 87 |
| erp-console khác (CSS) | 1 | 2 |
| frontend code sản phẩm + mock (`.ts/.tsx/.mjs`) | 10 | 39 |
| frontend e2e (`.py`) | 10 | 18 |
| frontend khác (CSS) | 1 | 1 |

Từ nhiều nhất: `chu` 1309, `kho` 839, `cskh` 747, `khong` 518, `giao` 471, `ql` 449, `quan+ly` 213, `nv` 198, `nhap` 185, `huy` 108.

### Việc cho Lô 1 (phát hiện nhờ B2)
Đổi về tên chuẩn: `VN_TZ` (adapter `app/sepay.py`, ERP `shared/lib/format.ts`) thành `VN_TIME_ZONE`; `todayVn`/`currentYearVn` (Shop `lib/format.ts`,
`app/page.tsx`, `scripts/test-format.mjs`) thành `todayInVietnam()`/`currentYearInVietnam()`; **`todayVN` ở
`erp-console/features/deliveries/components/DeliveriesView.tsx` (tên này chưa có trong 02c §1c) cũng thành `todayInVietnam()`**.
Giá trị mức nhạy cảm `"cao"/"thap"/"trung_binh"` (`ai/registry/{spec,discovery}.py`, `inventory/batches/api.py`, `reports/api.py`,
`reports/dashboard_api.py`, `erp-console/features/ai/types.ts`) đổi ở Lô 4 theo 02c.

### Tự kiểm (chạy lại 01/10 sau vòng sửa)
(a) HEAD sạch, Python 3.9.16, 3.10.11, 3.11.4, 3.12.13, 3.13.14, 3.14.4 đều ra đúng một dòng, exit 0, không lệch giữa các phiên bản:
```
check_naming: OK - 7584 vi phạm cũ trong 277 file, không phát sinh mới.
```
Thời gian 1,5 giây.

(b) Thêm tạm `backend/apps/common/tests/test_lo9_thu.py` (`def tinh_tien_hang()` kèm một f-string) và `frontend/lib/tmpNaming.ts`
(`export const soLuongKho = 1;`). Python 3.11.4 và 3.12.13 cho cùng kết quả, exit 1:
```
[file mới] backend/apps/common/tests/test_lo9_thu.py
  backend/apps/common/tests/test_lo9_thu.py (tên file/thư mục)  'test_lo9_thu.py'  -> từ tiếng Việt: lo9
  backend/apps/common/tests/test_lo9_thu.py:1  'tinh_tien_hang'  -> từ tiếng Việt: tinh, tien
[file mới] frontend/lib/tmpNaming.ts
  frontend/lib/tmpNaming.ts:1  'soLuongKho'  -> từ tiếng Việt: luong, kho
```
(c) Thêm tạm `def kiem_tra_nhap_lo(): pass` vào `backend/apps/sales/orders/services.py` (đã có trong baseline), cả 3.11 và 3.12, exit 1:
```
[tăng so với baseline 3] backend/apps/sales/orders/services.py
  backend/apps/sales/orders/services.py:458  'kiem_tra_nhap_lo'  -> từ tiếng Việt: kiem, nhap
```
Đã gỡ file tạm, khôi phục `services.py`; `git status` chỉ còn file của Lô 0.

`--self-test`: `check_naming --self-test: OK` trên 3.9, 3.10, 3.11, 3.12, 3.13, 3.14.

Backend: `cd backend && DJANGO_DEBUG=1 env -u DATABASE_URL .venv/bin/python manage.py test` chạy 1674 test, OK (không đổi số test). `makemigrations --check --dry-run`: No changes detected.

### Còn nợ / lưu ý cho người làm Lô 1 trở đi
- Lô 1 dùng `git mv` khi dời `cskh` sang `confirmation`; chạy `python3 scripts/check_naming.py --update` (cùng commit) để baseline hạ. Commit
  `naming_baseline.json` cùng lô.
- Nếu sửa script hoặc blocklist thì baseline phải sinh lại ở HEAD sạch (xoá `naming_baseline.json` rồi `--update`, chỉ khi chưa có thay đổi code khác), chạy lại
  `--self-test` trên ít nhất một phiên bản <=3.11 và một phiên bản >=3.12.
- Hạn chế đã biết: generic arrow `= <T,>(x) =>` trong TSX làm bộ quét nhầm thẻ (HEAD không có; nếu gặp, script in cảnh báo mất cân bằng).
  Script không quét tài liệu `.md` và không xét nội dung CSS (chỉ tên file).
- `02c-giao-viec.md` §4 đã có dòng `python3 scripts/check_naming.py` (từ commit 8cec800), không cần sửa phiếu.

## Lô 1 — BE (01/10)

Trạng thái: xong phần BE + adapter, chưa commit, chưa chạy `check_naming --update` (fe-dev làm song song; điều phối chạy `--update` sau cùng).
Không đổi hành vi, không migration, không đổi contract (route, khoá JSON, env, lệnh quản trị, id lệnh AI, giá trị Group đều giữ).

### File
Mới:
- `backend/apps/accounts/roles.py` — `OWNER="chu"`, `MANAGER="quan_ly"`, `WAREHOUSE_STAFF="nv_kho"`, `DELIVERY_STAFF="nv_giao"`, `CUSTOMER_SERVICE="cskh"`, `ALL_ROLES`. Chỉ hằng, không import gì.
- `backend/apps/ai/command_groups.py` — `PURCHASING="thu_mua"`, `SALES="ban_hang"`, `CUSTOMER_SERVICE="cskh"`, `SENSITIVITY_HIGH/MEDIUM/LOW = "cao"/"trung_binh"/"thap"`.

Dời (`git mv`): `backend/apps/delivery/cskh/` -> `backend/apps/delivery/confirmation/` (`__init__.py`, `api.py`, `scope.py`, `serializers.py`, `services.py`).

Đổi tên (toàn bộ `backend/apps`, `backend/config`, gồm test import chúng):
| Cũ | Mới |
|---|---|
| `CskhQueueViewSet`, `CskhQueuePagination`, `CskhQueueItemSerializer`, `CskhQueueDetailSerializer` | `ConfirmationQueueViewSet`, `ConfirmationQueuePagination`, `ConfirmationQueueItemSerializer`, `ConfirmationQueueDetailSerializer` |
| `CskhSearchView`, `CskhSearchThrottle` | `CustomerSearchView`, `CustomerSearchThrottle` |
| `is_cskh`, `cskh_q`, `cskh_note_q`, `note_in_cskh_scope` | `is_customer_service`, `customer_service_q`, `customer_service_note_q`, `note_in_customer_service_scope` |
| alias `cskh_services` | `confirmation_services` |
| `HOME_CSKH_QUEUE` (giá trị `"cskh-queue"` giữ) | `HOME_CONFIRMATION_QUEUE` |
| `NhapLoLine`, `NhapLoInput`, `NhapLoBatchOutput` | `ReceiveBatchesLine`, `ReceiveBatchesInput`, `ReceivedBatchOutput` |
| `is_chu`, `active_chu_ids`, `active_chus` (tham số), `_lock_target_and_chus`, `LAST_CHU_CODE`, `_escalate_to_chu`, `chu_user`, `CHU` | `is_owner`, `active_owner_ids`, `active_owner_ids`, `_lock_target_and_owners`, `LAST_OWNER_CODE`, `_escalate_to_owner`, `owner_user`, `roles.OWNER` |
| test helper `CskhL2/L3/L4BaseTestCase`, `_create_order_with_cskh` | `ConfirmationL2/L3/L4BaseTestCase`, `_create_order_with_confirmation` |
| adapter `VN_TZ` (`adapter/app/sepay.py`) | `VN_TIME_ZONE` |

Chuỗi tên Group/nhóm lệnh AI/mức nhạy cảm: thay bằng hằng ở code chạy thật (`common/api.py` `FULL_SCOPE_GROUPS`, `accounts/auth/services.py`
`ROLE_ORDER = roles.ALL_ROLES`/`GROUP_LABELS`/`home_for`, `accounts/staff/services.py`, `sales/payments/auto_confirm.py`, `ai/actions/{api,services}.py`,
`ai/execution/pipeline.py`, `ai/management/commands/run_due_ai_actions.py`, `purchasing/receipts/services.py`, `delivery/confirmation/scope.py`,
`ai/registry/{discovery,spec}.py`, `ai/settings/services.py`, `ai/policy/effective.py`, `inventory/batches/api.py`) và ở **125 file test, 824 chuỗi** (thay cơ học
bằng `roles.*`/`command_groups.*` qua AST, không đổi tên hàm/biến test). Hai kiểu ghép chuỗi `"".join(["cs","kh"])` đã bỏ.
Doc: `backend/README.md` (bản đồ module), `backend/apps/delivery/README.md`, `backend/apps/accounts/README.md`, `backend/apps/accounts/staff/README.md` (tên hàm khoá).

### Giữ nguyên (đúng 02c, để Lô 3/4)
Route `cskh/queue`, `cskh/search/` và basename `cskh-queue`, `cskh-search`; khoá JSON `cskh_*`; env/settings `CSKH_*`, `THROTTLE_CSKH_SEARCH`, scope `cskh_search`;
lệnh `process_cskh_deadlines`, `check_cskh_job_health`; logger `cangca.delivery.cskh`; method `nhap_lo` + `url_path="nhap-lo"` + `custom_perm_actions`; giá trị các hằng; migration.

### Lệch thiết kế / lưu ý
- **`is_chu` không gộp vào `actor_is_owner`:** hai hàm khác nghĩa (`actor_is_owner` = Chủ **hoặc superuser**, `is_owner` chỉ xét Group). Giữ cả hai, đổi tên `is_chu` -> `is_owner` (theo điều kiện "giữ cả hai" của 02c).
- **Import vòng (đã xử lý theo review S1):** `command_groups.py` dời ra `backend/apps/ai/command_groups.py` (lá, không import gì), mọi nơi import `from apps.ai import command_groups`; `apps/ai/policy/effective.py` import ở đầu module, không còn import trong hàm; `inventory/batches/api.py` không kéo gói `apps.ai.registry`.
- **Review Lô 1 (N1, N2):** `from apps.accounts import roles` ở `accounts/auth/services.py` đưa về đúng nhóm import; tham số `active_owner_ids` của `staff/services.available_actions` và `staff/serializers.staff_item` đổi thành `owner_ids`.
- Lệnh `git grep -nE "delivery\.cskh"` của 02c còn 4 dòng: đều là **tên logger** `cangca.delivery.cskh` (giữ tới Lô 3), không phải đường dẫn module.
- Còn 2 dòng comment/docstring nhắc `'chu'` (`ai/actions/api.py:130`, `run_due_ai_actions.py:69`): chữ trong chú thích, không phải định danh.
- Tên test, tên file test, biến theo vai (`self.chu`, `client_kho`) **không đổi** (đổi dần, §5).

### Kiểm chứng (chạy trong lượt này)
- `cd backend && DJANGO_DEBUG=1 env -u DATABASE_URL .venv/bin/python manage.py test`: **Ran 1674 tests, OK** (trước: 1674, không thêm/bớt/skip).
- `makemigrations --check --dry-run`: No changes detected. `git diff HEAD --stat -- '*/migrations/*'`: rỗng.
- Snapshot chỉ mục AI `backend/apps/ai/registry/tests/snapshots/commands_index_snapshot.json`: `git diff HEAD --stat` rỗng (không regenerate); `test_discovery` xanh. `_get_group` không đổi nhóm vì `apps.delivery.confirmation.*` vẫn chứa "delivery".
- `cd adapter && .venv/bin/python -m pytest -q`: 68 passed.
- Grep: `"(chu|quan_ly|nv_kho|nv_giao|cskh)"` ngoài `roles.py` và migration: chỉ còn 2 chú thích nói trên; `"(thu_mua|ban_hang|cao|trung_binh|thap)"` ngoài `command_groups.py`: rỗng; `delivery.cskh|features/cskh`: chỉ 4 tên logger.
- `python3 scripts/check_naming.py`: `OK - 6724 vi phạm cũ trong 224 file, không phát sinh mới.` (gồm cả phần FE đang làm song song; baseline ở HEAD là 7584/277).
  Riêng `backend/ + adapter/`: 6936 (190 file) -> 6515 (170 file), giảm 421. Chưa `--update`: chờ điều phối (fe-dev làm song song).

## Lô 1 — FE (01/10)

Đổi tên nội bộ `erp-console/` và `frontend/` sang tiếng Anh, không đổi hành vi và không đổi contract.

### Đã dời / đổi tên (git mv)
- `erp-console/features/cskh/` -> `features/confirmation/`: `ConfirmationCallModal.tsx`, `ConfirmationQueueView.tsx`, `confirmation.module.css`, `confirmation.test.ts`, `api.ts`, `mock.ts`, `types.ts`. Toàn bộ định danh `Cskh*` đổi sang `Confirmation*` (hàm API, kiểu, hook, testid `confirmation-stale-alert`).
- `features/purchasing/components/NhapLoForm.tsx` -> `ReceiveBatchesForm.tsx`; kiểu/hàm `NhapLo*` -> `ReceiveBatches*`; `shared/lib/drafts.ts` dùng `RECEIVE_BATCHES_DRAFT_PREFIX` (giá trị vẫn `cave_draft_nhap_lo`).
- Shop: `CskhNotice.tsx/.module.css` -> `ConfirmationPolicyNotice.tsx/.module.css`; kiểu `ConfirmationPolicyConfig`; testid `confirmation-policy-notice`.
- `app/(console)/cskh/page.tsx`: `ConfirmationPage`, `ViewGuard view="confirmation"` (route `/cskh/` giữ nguyên); `ViewKey` trong `nav.ts` = `"confirmation"`.

### File hằng mới (chỗ duy nhất giữ chuỗi tên cũ, Lô 4 chỉ sửa ở đây)
- `erp-console/shared/lib/roles.ts`: `ROLE` (owner/manager/warehouseStaff/deliveryStaff/customerService), `RoleCode`, `HOME_CONFIRMATION_QUEUE` (giá trị `"cskh-queue"`).
- `erp-console/features/ai/commandGroups.ts`: `COMMAND_GROUP`, `SENSITIVITY`, kiểu `AiCommandGroup`, `AiSensitivity`; `features/ai/types.ts` import và re-export.
- Đã thay chuỗi Group bằng `ROLE.*` ở: `nav.ts`, `groups.ts`, `features/auth/{types,mock}.ts`, `features/ai/*` (panel, mock, policy, actions), `features/inventory|overview|staff|content|guidance` (mock, component, test), `content/edit/page.tsx`. Biến `isChu/isQuanLy/...` -> `isOwner/isManager/...`; `chuOnlyStep` -> `ownerOnlyStep`.

### Múi giờ thống nhất
- erp: `VN_TIME_ZONE` (`shared/lib/format.ts`), `COLD_STORAGE_NAME`, `todayInVietnam()` inline ở `DeliveriesView.tsx`.
- Shop: `todayInVietnam`, `currentYearInVietnam` (`lib/format.ts`, `app/page.tsx`, `lib/mock.ts`, `scripts/test-format.mjs`).

### Giữ nguyên (đúng 02c, để Lô 3/4)
Route `/cskh/`, `/nhap-lo`; đường dẫn `/api/cskh/*`; khoá JSON `cskh_*` và `cskh_notice`; id lệnh AI `...nhap_lo`; mã lỗi BE `CHU_*`; khoá nháp `cave_draft_nhap_lo`; giá trị Group gửi/nhận (nằm trong `roles.ts`, `commandGroups.ts`); giá trị `me.home = "cskh-queue"`.

### Lệch / lưu ý
- Không đổi tên file e2e (`sr07_nhap_lo_draft.py`...): 02c không giao cho Lô 1. Trong e2e chỉ cập nhật testid, tên hàm mock helper và biến (`p8_lo7_fe_erp.py`, `sr09_ac4_real_backend.py`, `sr09_ac4_stale_state.py`, `s10_s11_orders.py`, `qa-lo7-shop-real.py`, `qa-lo6-sr21-shop.py`). Literal Group trong `e2e/*.py` còn nguyên (Lô 4).
- `README.md` các module còn nhắc tên Group cũ trong phần mô tả (chữ thường, không phải định danh); `erp-console/README.md` đã cập nhật dòng `roles.ts` và `confirmation/`.
- Logger `cangca.delivery.cskh` và `VN_TZ` của adapter thuộc phần BE.
- Shop: `frontend/.env.local` đặt `NEXT_PUBLIC_USE_MOCK=1` nên `npm run build` trần cho `check-no-mock` ĐỎ (có từ trước); build thật phải truyền `NEXT_PUBLIC_USE_MOCK=0 NEXT_PUBLIC_API_BASE=...` (như `doc/ops/moi-truong.md`). Bản `out/` cuối của Shop được build với `NEXT_PUBLIC_API_BASE=http://localhost:8199`, cần build lại với URL môi trường đích trước khi deploy.

### Kiểm chứng (chạy trong lượt này)
- erp: `npx tsc --noEmit` sạch; `npm test`: 14 file, **185/185 pass** (không đổi số test).
- frontend: `npx tsc --noEmit` sạch; `test-format.mjs` 26/26; `test-safe-href.mjs` 40/40.
- Build thật erp (`NEXT_PUBLIC_USE_MOCK=0`): `check-no-mock.mjs` XANH (131 file build); `check-ai-chunks.mjs` XANH.
- Build thật Shop (`USE_MOCK=0`, API `http://localhost:8199`): `check-no-mock.mjs` XANH (46 file build).
- e2e trên build mock erp (cổng 3230): `p8_lo7_fe_erp.py` **79/79 PASS**; `p8_lo8_fe_erp_tz.py` **71/71 PASS**.
- e2e Shop (cổng 3232, build USE_MOCK=0 chặn /api bằng page.route): `qa-lo6-sr21-shop.py` **279 ca, 0 FAIL**. Bản out copy ở `scratchpad/p8b-l1-fe/{erp-mock,shop}`. Server đã tắt.
- `python3 scripts/check_naming.py`: `OK - 6724 vi phạm cũ trong 224 file, không phát sinh mới` (46 file đã giảm; chưa `--update`, chờ điều phối).
