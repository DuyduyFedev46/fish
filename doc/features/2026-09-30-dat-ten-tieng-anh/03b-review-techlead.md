# 03b — Review Tech Lead: P8b Đổi tên định danh sang tiếng Anh

## Lô 0

> Tech Lead · 2026-10-01 · Diff chưa commit: `scripts/check_naming.py`, `scripts/naming_blocklist.txt`, `scripts/naming_baseline.json`,
> mục "Đặt tên" trong 5 skill và `AGENTS.md`, `03-dev-notes.md` mục Lô 0. Đối chiếu `02c-giao-viec.md` §1, §3 Lô 0, §4, §7b.

### Kết luận: **REVIEW PASS** (vòng 2, 01/10). Vòng 1: REVIEW FAIL, xem lịch sử bên dưới.

#### Vòng 2 — review lại sau khi be-dev sửa (01/10)
Đã đọc diff `scripts/check_naming.py` (`_python_tokens`, `base_ref`/`rename_map`/`head_token_counts`, `ALLOW_WITH_REASON`,
`EXEMPT_LINE_PATTERNS`, `MOCK_FILE`, `EXEMPT_STRING_FILES`, `--report` in các dòng dùng marker), `naming_blocklist.txt`, và phần hướng dẫn marker
trong `tdd-workflow` và `AGENTS.md` (`naming: allow - <lý do>`).

| Mục | Kết quả kiểm trong lượt này |
|---|---|
| B1 | `check_naming` ra `OK - 7584 vi phạm cũ trong 277 file` và `--self-test` OK, giống nhau trên Python 3.9.6, 3.10, 3.11, 3.12, 3.14. Thử f-string lồng nhau `f"nhap-lo/{f'{kho}'}"`: 3.11 và 3.12 cho cùng kết quả |
| B2 | Blocklist có `cao thap trung+binh vn+tz today+vn vn+today year+vn`; thử `"thap"`, `VN_TZ`, `todayVn` đều bị bắt. Việc đổi `todayVN` đã ghi cho Lô 1 trong dev notes |
| R1 | Trong clone: commit baseline, `git mv delivery/cskh -> confirmation`, **commit mà chưa `--update`**: OK, kế thừa đúng. Thêm `kiem_tra_nhap_lo` vào file đã dời: báo `[tăng so với baseline 10]` và chỉ in đúng dòng mới. `--update` hạ còn 7579/276 |
| R2 | `# naming: allow` không kèm lý do: vẫn bị bắt. Kèm `- username demo`: được miễn. Dòng khai báo `LEGACY_RECEIVE_BATCHES_DRAFT_PREFIX = …`: được miễn. Dòng chỉ dùng hằng (`startsWith(LEGACY_…) \|\| nhapLo`): vẫn bắt `nhapLo` |
| R3 | `legacy_ids.py`: chuỗi được miễn, định danh `nhom_cu` vẫn bị bắt. Việc dọn miễn trừ ở Lô 4 và Lô 5 đã ghi thành comment trong script |
| R4 | Chuỗi trong `mock.ts`/`*.mock.ts` không bị xét, định danh vẫn bị xét (có self-test) |
| R5, R6 | Đã thêm các cặp và ghi lại lý do allowlist; đã bỏ `gui`, `chan` |

**Còn một điểm nhỏ, không chặn:** đầu `naming_blocklist.txt` vẫn xếp `moi lai dau lam doi thu` vào nhóm "trùng từ tiếng Anh hợp lệ". Chỉ
`doi` (DOI) và `lam`/`thu` là gượng được; `moi`, `lai`, `dau` không phải từ tiếng Anh. Khi có dịp sửa file thì chuyển chúng sang nhóm
"quá phổ biến". Việc này không ảnh hưởng hành vi của script.

Lô 0 được commit cùng `naming_baseline.json` (7584/277). Phiếu §4 đã có dòng `check_naming`.

#### Vòng 1 (lịch sử) — REVIEW FAIL: 1 lỗi chặn, 1 lỗ hổng so với glossary

### Lệnh đã chạy trong lượt review
| Lệnh | Kết quả |
|---|---|
| `python3 scripts/check_naming.py` (Python 3.11.4, mặc định máy) | `OK - 7647 vi phạm cũ trong 274 file`, exit 0, 1,8 giây |
| `python3 scripts/check_naming.py --self-test` | `OK` |
| Chạy lại bằng Python 3.9, 3.10, 3.12, 3.13, 3.14 (`/opt/homebrew/bin/python3.x`) | 3.9/3.10: OK 7647. **3.12/3.13/3.14: exit 1**, 7 file test "tăng so với baseline", tổng 7660 |
| Mô phỏng Lô 1 trong bản clone ở scratchpad: `git mv backend/apps/delivery/cskh …/confirmation` và đổi 1 file TSX | Trước commit: OK, kế thừa baseline, báo 5 file giảm. `--update` rồi commit: OK. **Commit trước `--update`: 5 file bị báo "[file mới]"** |
| `--words` và quét thử thêm từ ứng viên trên HEAD | Xem mục 2 và mục 4 |

### 1. Lỗi chặn (phải sửa trước khi commit)

**B1 — Kết quả phụ thuộc phiên bản Python.** Từ Python 3.12, `tokenize` tách f-string thành `FSTRING_START/MIDDLE/END` và trả
token `NAME` cho biểu thức trong `{…}`. Python 3.11 trở xuống trả nguyên f-string thành một token `STRING`. Vì vậy cùng một HEAD
cho 7647 vi phạm trên 3.11 nhưng 7660 trên 3.12 trở lên, và script exit 1 ngay ở HEAD sạch. Ví dụ
`backend/apps/ai/settings/tests/test_my_config_api.py:311` có `user_kho` trong f-string.
Máy của Gemini CLI/Antigravity, hoặc Homebrew mặc định mới, rất có thể dùng 3.12 trở lên. Khi đó cổng kiểm chứng đỏ sẵn, hoặc
`--update` ghi ra baseline không khớp giữa các máy.
- Chỗ lỗi: `scripts/check_naming.py:190-212` (`extract_python`, nhánh `FSTRING_MIDDLE` ở dòng 207).
- Sửa: trên 3.12 trở lên, gặp `FSTRING_START` thì bỏ mọi token cho tới `FSTRING_END` tương ứng (đếm lồng nhau). Lấy đoạn nguồn từ
  điểm bắt đầu tới điểm kết thúc và xử lý như một token `STRING`, gồm cả luật docstring và `_literal_body`. Như vậy mọi phiên bản
  cho cùng kết quả với 3.11, baseline hiện tại không đổi, và nhánh `FSTRING_MIDDLE` (dòng 207-209) bị bỏ.
- Thêm vào `--self-test`: f-string trong file test (`f"/x/{self.user_kho.id}/"` không được tính) và trong file thường
  (`f"nhap-lo/{x}"` phải bị bắt). Assert số vi phạm giống nhau trên mọi phiên bản.
- Kiểm chứng: dán output `check_naming` chạy bằng ít nhất 3.9 hoặc 3.11 **và** 3.12 trở lên (máy có sẵn `/opt/homebrew/bin/python3.12`),
  cả hai phải ra `7647 … 274 file`, cộng thêm phần tăng do B2 nếu làm.

**B2 — Blocklist chưa chặn các tên mà glossary ghi ở cột "Không dùng".** Skill và `AGENTS.md` nói bảng glossary được "kiểm bằng
máy", nhưng hai dòng sau không bị chặn:
- Mức nhạy cảm lệnh AI `cao`, `trung_binh`, `thap`: một định danh mới `sensitivity="thap"` hoặc `SENSITIVITY_CAO` vẫn qua. Sau Lô 4,
  nếu ai đó viết lại giá trị cũ thì không có gì bắt được.
- Giờ Việt Nam `VN_TZ`, `todayVn`, `vn_today`, `currentYearVn`.
- Sửa: thêm vào `scripts/naming_blocklist.txt` từ đơn `cao`, `thap`, cặp `trung+binh`, `vn+tz`, `today+vn`, `vn+today`, `year+vn`.
  Không từ nào trong số này trùng từ tiếng Anh. Sau đó sinh lại baseline ở HEAD sạch và chạy lại `--self-test`.
  - Đo thử trên HEAD: khoảng +33 vi phạm, gồm `VN_TZ` (adapter, ERP `format.ts`), `todayVn`/`currentYearVn` (Shop),
    `"cao"/"thap"/"trung_binh"` (`ai/registry/{spec,discovery}.py`, `inventory/batches/api.py`, `erp-console/features/ai/types.ts`)
    và **`todayVN` ở `erp-console/features/deliveries/components/DeliveriesView.tsx`**. Tên `todayVN` chưa có trong §1c. Lô 1
    phải đổi luôn tên này thành `todayInVietnam()`.

### 2. Đạt yêu cầu (đã soát)
- **Blocklist bắt buộc theo 02c Lô 0:** có đủ `cskh nhap kho giao chu nv soat bosung tien`, các cặp `quan+ly thu+mua ban+hang bo+sung
  qua+han qa+lo`, mẫu `lo\d+`, và `l\d+` chỉ áp cho tên file test. Các token từ bản rà soát 01 (`chot_lo`, `tra_ton`, `tra_don`,
  `tra_hang`, `tra_ncc`, `tao_phieu_hoan`, `xac_nhan_hoan`, `bao_cao_ton_kho`, `KHO_LANH`, `ra_soat_*`, `bosung`, `mat_khau`)
  đều bị bắt.
- **Không bắt nhầm từ tiếng Anh phổ biến:** `ton don hang ban chi lo mat tra so co la the no ma an be cap con` nằm ở allowlist và
  chỉ bị chặn khi đi thành cặp. Về câu hỏi `kho`: tiếng Anh không có từ thông dụng nào là "kho" (chỉ gặp như tên riêng), nên chặn
  từ đơn `kho` là đúng. Tôi đã dò mẫu các token trúng `gui chan hai anh dem tac som rac cong loi sach thi gia ghi luu trong hom khi
  von canh gio thang` trên HEAD: không có ca nào là tiếng Anh, tất cả đều là tên test hoặc slug tiếng Việt.
- **Không bắt chữ hiển thị, comment, docstring:** `--self-test` phủ docstring, comment `#`, `//` và `/* */`, chữ trong nội dung JSX,
  thuộc tính `title="Kho hàng"`, chuỗi có dấu hoặc có khoảng trắng, nhãn một từ viết hoa đầu, và mã viết hoa (`TOM-SU-1`, `BR-LO-04`).
  File test chỉ xét định danh.
- **Allowlist theo file:** `roles.py`, `roles.ts`, `command_groups.py`, `commandGroups.ts` miễn chuỗi nhưng vẫn xét định danh.
  `legacy_ids.py` và `legacyIds.ts` được miễn. `LEGACY_RECEIVE_BATCHES_DRAFT_PREFIX`, `chuyen-muc`, `frontend/app/{bai-viet,trang}/`
  và migration đều được miễn. Danh sách này khớp 02c Lô 0. Hai file `command_groups.*` là phần mở rộng hợp lý vì Lô 1 bắt buộc
  đặt giá trị cũ ở đó.
- **Baseline:** tính theo từng file. Script fail khi có file mới vi phạm hoặc khi một file tăng số vi phạm. `--update` từ chối ghi
  nếu có file tăng. Khi đổi tên bằng `git mv`, file mới kế thừa trần của đường dẫn cũ và chỉ in những dòng thực sự mới. Mô phỏng
  Lô 1 cho kết quả đúng như vậy.
- **Luật trong skill:** 5 skill và `AGENTS.md` có cùng một bảng. Bảng dùng `customer_service` cho vai, `confirmation` cho việc gọi
  xác nhận (khớp §7b), `review_*` thay `ra_soat_*`, và không còn chữ `customer_care` (tên cũ của bản 01). Phần dành riêng cho
  `tdd-workflow` và `e2e-playwright` đúng với §5 (test tiếng Việt được đổi dần).
- **Thời gian chạy:** 1,6–1,8 giây, dưới mức 10 giây.
- **§4 của `02c-giao-viec.md`:** dòng `python3 scripts/check_naming.py` đã có ở dòng đầu của bộ lệnh (có từ commit `8cec800`). Không
  cần sửa phiếu. Câu "§4 chưa có dòng này" trong `03-dev-notes.md` là sai, cần xoá.

### 3. Nên sửa (không chặn; làm cùng lượt sửa B1/B2 thì tốt)
- **R1 — Commit trước `--update` thì mất kế thừa.** `rename_map()` (`scripts/check_naming.py:559-575`) chỉ so với `HEAD`. Nếu đã
  commit phép đổi tên mà chưa chạy `--update`, file bị báo "[file mới]" và không có cách gỡ ngoài `git reset --soft`. Docstring
  ở dòng 560 ghi "hoặc đã commit sau baseline" là **sai**. Cách sửa: so với commit gần nhất có sửa baseline
  (`git log -1 --format=%H -- scripts/naming_baseline.json`, nếu baseline chưa commit thì dùng `HEAD`). Nếu không sửa thì phải
  sửa docstring và thêm cách gỡ vào `tdd-workflow`.
- **R2 — `naming: allow` chưa có điều kiện.** Hiện dòng nào có chuỗi này cũng được miễn, kể cả khi không ghi lý do
  (`scripts/check_naming.py:482-483`). Cách sửa: chỉ chấp nhận khi sau marker có lý do, ví dụ regex
  `naming: allow\s*[-:—(]\s*\S{3,}`. Có thể thêm `--report` in số dòng đang dùng marker để techlead soát. Ngoài ra,
  `EXEMPT_LINE_IDENTIFIERS` đang miễn mọi dòng có nhắc tới `LEGACY_RECEIVE_BATCHES_DRAFT_PREFIX`, nên thu hẹp về dòng khai báo
  (`LEGACY_RECEIVE_BATCHES_DRAFT_PREFIX =`).
- **R3 — Hai file map cũ đang được miễn cả định danh.** `legacy_ids.py` và `legacyIds.ts` nằm trong `EXEMPT_PATH_PREFIXES`
  (`:71-78`), nên tên hàm và biến trong đó cũng không bị xét. Nên chuyển hai file này sang `EXEMPT_STRING_FILES`, tức chỉ miễn chuỗi,
  giống cách làm với `roles.py`. Ghi thêm việc cho Lô 4: bỏ miễn `command_groups.py`/`commandGroups.ts` vì giá trị đã sang tiếng Anh.
  Ghi cho Lô 5: bỏ miễn `roles.py`/`roles.ts` khi `LEGACY_ROLE_NAMES` đã được gỡ.
- **R4 — Dữ liệu demo trong mock FE bị xét như định danh.** Mock đang bị xét chuỗi, ví dụ `kho1`, `giao2`, `matkhau123`, `nghi1` ở
  `erp-console/features/auth/mock.ts` và slug `chinh-sach-bao-mat`, `doi-tra-va-hoan-tien`, `loi-luu-tru` ở `features/content/mock.ts`.
  Điều này lệch với câu "dữ liệu demo giữ, không bị bắt" trong skill. Hiện tại baseline đã nuốt các vi phạm này, nên chỉ gây phiền
  khi thêm mock mới. Cách sửa: coi `mock.ts`, `*.mock.ts` và `frontend/lib/mock.ts` như file test, tức chỉ xét định danh. Định danh
  trong mock (tên khoá, tên hàm) vẫn bị bắt.
- **R5 — Allowlist ghi lý do chưa chính xác.** `nhan vien lam moi lai dau sau bai muc trang nha doi hoa` không phải từ tiếng Anh.
  Lý do thật để miễn là chúng nằm trong URL công khai, slug, dữ liệu demo, hoặc là từ quá phổ biến. Nên ghi lại lý do cho đúng.
  Có thể thêm các cặp `trang+thai`, `ly+do`, `hien+tai`, `ket+qua`, `nhan+vien`, `bao+cao`, `tao+moi`, `dang+ban`. Đo trên HEAD:
  khoảng +60 vi phạm, gần như toàn ở test; ở code chạy thật chỉ có 3 keyword `bao_cao_*` (Lô 4 xoá). Làm được thì chặn thêm được
  các tên ngắn như `trang_thai` và `ly_do`, là những tên hiện đang lọt.
- **R6 — Hai từ có thể bắt nhầm.** `gui` trùng GUI và `chan` trùng cách viết tắt của channel. Trên HEAD, mọi chỗ trúng hai từ này
  đều đã có từ khác cũng bị chặn. Nên chuyển `gui` và `chan` ra khỏi danh sách từ đơn mà không mất độ phủ, hoặc giữ nguyên và
  theo dõi thêm.

### 4. Việc sửa giao `be-dev` (một lượt, vẫn trong Lô 0)
1. Sửa B1: thống nhất cách xử lý f-string trên mọi phiên bản và thêm ca vào `--self-test`.
2. Sửa B2: thêm `cao thap trung+binh vn+tz today+vn vn+today year+vn` vào blocklist. Thêm R5 nếu đồng ý.
3. Nên làm cùng lượt: R1, R2, R3, R4, R6.
4. Sinh lại `naming_baseline.json` ở HEAD sạch. Chạy lại tự kiểm (a), (b), (c) như trong `03-dev-notes.md`, `--self-test`, và chạy
   `check_naming` trên hai phiên bản Python (≤3.11 và ≥3.12). Dán output và con số baseline mới vào `03-dev-notes.md`. Xoá câu
   "§4 chưa có dòng check_naming".
5. Ghi thêm cho Lô 1 trong `03-dev-notes.md`: đổi `todayVN` ở `erp-console/features/deliveries/components/DeliveriesView.tsx`,
   phát hiện nhờ B2.
6. Không phải hỏi Duy: không từ nào bị miễn mà code sản phẩm đang dùng làm định danh chính thức.

Sau khi sửa, Tech Lead review lại chỉ phần diff của `scripts/` và cập nhật mục này thành REVIEW PASS.

---

## Lô 1

> Tech Lead · 2026-10-01 · Diff chưa commit (215 dòng `git status`, 207 file, `git mv` cụm `delivery/cskh`, `features/cskh`,
> `NhapLoForm`, `CskhNotice`). Đối chiếu `02c-giao-viec.md` §1, §3 Lô 1, §6 và `03-dev-notes.md` mục "Lô 1 — BE", "Lô 1 — FE".

### Kết luận: **REVIEW PASS** (vòng 2, 01/10). Vòng 1: CẦN SỬA (S1), xem bên dưới.

#### Vòng 2 — review lại diff S1, N1, N2, N3 (01/10)
| Mục | Kết quả kiểm trong lượt này |
|---|---|
| S1 | `backend/apps/ai/command_groups.py` đã staged (`A`). File cũ `registry/command_groups.py` không còn. File mới chỉ có hằng, không import gì. Tìm `registry.command_groups`, `from . import command_groups` và `registry import command_groups` trong backend: không còn. 15 file đều dùng `from apps.ai import command_groups`. `effective.py:8` đã import ở đầu module, bỏ import trong hàm. `inventory/batches/api.py:9` import lá, đứng cạnh `apps.ai.declare`. `check_naming.py` chỉ đổi một dòng đường dẫn trong `EXEMPT_STRING_FILES` |
| N1 | `accounts/auth/services.py`: `from apps.accounts import roles` đã về nhóm import `apps.*`, trước import tương đối |
| N2 | Tham số đổi thành `owner_ids` ở `staff/services.py:324`, `staff/serializers.py:12` và 2 nơi gọi trong `staff/api.py:64,69`. Không còn chỗ nào gọi bằng tên cũ. Hàm `active_owner_ids()` không bị che nữa |
| N3 | Comment đầu `erp-console/shared/lib/roles.ts` đã nêu cả tên Group và `HOME_CONFIRMATION_QUEUE` |
| Lệnh | Backend `apps.delivery apps.accounts apps.ai apps.inventory apps.purchasing`: **875 test OK**. `makemigrations --check --dry-run`: No changes detected. Import riêng lẻ `apps.ai.command_groups`, `apps.ai.policy.effective`, `apps.inventory.batches.api`, `apps.ai.registry.spec`, `apps.accounts.auth.services`, `apps.accounts.staff.api`: OK. Snapshot chỉ mục AI: không đổi so với HEAD. `check_naming.py`: OK 6724. ERP `npm test`: 185/185 |

Bộ đầy đủ 1674 test do be-dev báo, tôi không chạy lại toàn bộ trong lượt này. Phần tôi chạy lại gồm mọi app bị S1 và N1–N3 đụng tới.
Lô 1 được commit sau khi QA chạy xong smoke E2E 5 vai. Lưu ý khi commit ở mục 4 vẫn áp dụng; file hằng AI lấy theo đường dẫn mới
`backend/apps/ai/command_groups.py`.

#### Vòng 1 (lịch sử) — CẦN SỬA: 1 việc sửa nhỏ về vị trí file hằng. Hành vi, contract, phân quyền, giá vốn và PII đều đạt.

### Lệnh đã chạy trong lượt review
| Lệnh | Kết quả |
|---|---|
| `cd backend && DJANGO_DEBUG=1 env -u DATABASE_URL .venv/bin/python manage.py test apps.delivery apps.accounts apps.ai` | `Ran 597 tests … OK` |
| `cd erp-console && npm test` | 14 file, **185/185 pass** |
| `python3 scripts/check_naming.py` | `OK - 6724 vi phạm cũ trong 224 file`, exit 0 |
| So chuỗi literal từng file HEAD↔worktree (tính theo rename, tokenize Python, regex TS) | Chỉ đổi: tên Group/nhóm/mức (thay bằng hằng), `data-testid` (đã giao), đường import, tên hàm mock `__caveMock.confirmation*` (e2e sửa cùng), username test `chu_user`→`owner_user`, chuỗi `mock.patch` `_lock_target_and_owners` |
| Kiểm **theo thứ tự**: thay ngược `roles.*`/`command_groups.*`/`ROLE.*`/`COMMAND_GROUP.*`/`SENSITIVITY.*` (và `GROUP.*` cũ) về giá trị, so dãy tên Group từng file | Khớp ở mọi file. 9 file lệch đều do tái cấu trúc hợp lệ (đã đọc tay): `ROLE_ORDER = roles.ALL_ROLES` (đúng thứ tự `chu, quan_ly, nv_kho, nv_giao, cskh`), hằng `CHU` cục bộ bị bỏ, `"".join(["cs","kh"])` bị bỏ, kiểu union TS chuyển sang `RoleCode`/`AiCommandGroup`/`AiSensitivity` |
| Import độc lập từng module đã sửa (`django.setup()` rồi import riêng lẻ 10 module, gồm `apps.inventory.batches.api`, `apps.ai.policy.effective`, `apps.ai.registry.spec`, `apps.common.api`) | Đều OK, không có import vòng |
| `git diff HEAD --stat -- backend/apps/ai/registry/tests/snapshots/ backend/apps/ai/policy/rules.py` | Rỗng |
| So `naming_baseline.json` HEAD↔worktree | 7584→6724. Không file nào tăng. 5 key mới là path sau rename và đều thấp hơn path cũ (`scope.py` 8→2, `serializers.py` 11→4, `services.py` 10→9, `api.ts` 36→8, `CskhNotice.tsx` 19→2). Phần còn lại là contract Lô 3 (`CSKH_*`, `/api/cskh/`, `cskh_notice`, logger) |

### 1. Việc phải sửa trước khi commit

**S1 — Dời `backend/apps/ai/registry/command_groups.py` sang `backend/apps/ai/command_groups.py`.** Trả lời câu (4) của điều phối: **dời
file, không giữ cách import trong hàm.**
- Lý do 1: file hằng nằm trong gói `apps.ai.registry`. Import `apps.ai.registry.command_groups` sẽ chạy `registry/__init__.py`, tức kéo theo
  `discovery`, `api` (view), `apps.ai.policy.effective` và `rules`. Vì vậy `effective.py` phải import trong hàm
  (`backend/apps/ai/policy/effective.py:112-113`).
- Lý do 2: `backend/apps/inventory/batches/api.py:16` (module view của domain) giờ import cả gói registry AI ở đầu module. HEAD giữ quy
  ước khác: module domain chỉ import lá `apps.ai.declare` (catalog, purchasing, sales đều vậy), còn `common/guidance/steps.py:55-56`
  import registry trong hàm. Hiện chưa vỡ (đã thử import từng module), nhưng đây đúng là kiểu nối vòng mà be-dev vừa gặp. Chỉ cần
  thêm một import ở đầu `registry/discovery.py` là vòng sẽ hiện ra.
- Lý do 3: Lô 1 có mục đích chốt **chỗ đặt cuối cùng** cho file hằng, để Lô 4 chỉ đổi giá trị. Nếu để Lô 4 mới dời thì phải đổi tên
  file lần hai, sửa danh sách miễn và baseline thêm một lần. `apps/ai/command_groups.py` là lá, không import gì, đứng cạnh `declare.py`
  (nơi có `AiMeta(sensitivity=…)`). Cách đặt này giống `apps/accounts/roles.py`.

Cách làm (`be-dev`):
1. `git mv backend/apps/ai/registry/command_groups.py backend/apps/ai/command_groups.py`. Sửa import ở 15 file backend (code và test đang
   import `apps.ai.registry.command_groups` hoặc `from . import command_groups`) thành `from apps.ai import command_groups`.
2. Ở `effective.py`, đưa import lên đầu module và xoá comment "Import trong hàm…". Ở `inventory/batches/api.py`, xếp import theo thứ tự
   như các import `apps.ai.declare` sẵn có.
3. `scripts/check_naming.py` `EXEMPT_STRING_FILES` (khoảng dòng 88): đổi path `backend/apps/ai/registry/command_groups.py` thành
   `backend/apps/ai/command_groups.py`, sửa luôn comment "Việc dọn" cho khớp. Đây là sửa đường dẫn cơ học ngoài danh sách "Được sửa"
   của Lô 1, Tech Lead cho phép. Không đụng blocklist hay logic.
4. Sửa đường dẫn trong `03-dev-notes.md` mục Lô 1 — BE (file mới, mục "Import vòng" ghi "đã dời theo review") và trong
   `02c-giao-viec.md` §3 Lô 1 dòng "Hằng nhóm lệnh AI" (điều phối sửa, hoặc ghi "Lệch thiết kế: đã dời theo 03b").
5. Kiểm lại: bộ test backend đầy đủ (phải ra 1674 OK), `makemigrations --check`, `git diff --exit-code HEAD -- backend/apps/ai/registry/tests/snapshots/`,
   `check_naming.py` (vẫn 6724, không `--update` thêm), và `git grep -n "registry.command_groups\|from . import command_groups" -- backend`
   phải rỗng.

### 2. Đạt yêu cầu (đã soát)
- **(1) Contract giữ nguyên.** Route `cskh/queue` + basename `cskh-queue`, `cskh/search/` + name `cskh-search`
  (`backend/config/api_urls.py:83,120`, chỉ đổi class view). `url_path="nhap-lo"`, method `nhap_lo`, `custom_perm_actions` và keyword
  `nhap_lo` của AI đều giữ. Khoá JSON không đổi: serializer không đổi field, type FE `confirmation/types.ts` và `purchasing/types.ts`
  chỉ đổi tên type, không đổi property; `cskh_notice` và `cskh_*` ở attention vẫn là tên cũ. Env/settings `CSKH_*`, scope throttle
  `cskh_search` (`common/throttling.py`), hai lệnh quản trị `process_cskh_deadlines`/`check_cskh_job_health` (không đổi tên file) và
  logger `cangca.delivery.cskh` đều giữ. `config/settings` không có trong diff. Id lệnh AI giữ, snapshot không đổi. Khoá storage
  `RECEIVE_BATCHES_DRAFT_PREFIX = "cave_draft_nhap_lo"` giữ giá trị, `clearAllDrafts()` vẫn dọn cả local và session. Map caps AI
  `"purchasing.purchasereceipt.nhap_lo"` giữ, chỉ state nội bộ đổi thành `receive_*`. `me.home`: BE `HOME_CONFIRMATION_QUEUE = "cskh-queue"`,
  FE `roles.ts` cùng giá trị, `homePath` vẫn trả `/cskh/`. Route ERP `app/(console)/cskh/` giữ. Adapter chỉ đổi tên hằng `VN_TIME_ZONE`.
- **(2) Phân quyền không đổi hành vi.** Kiểm bằng máy theo thứ tự (bảng trên), nên không có chỗ nào bị tráo vai. Đã đọc tay các chỗ
  nhạy cảm: `FULL_SCOPE_GROUPS` (`common/api.py:112`), `home_for`/`GROUP_LABELS`/`ROLE_ORDER` (`accounts/auth/services.py`), toàn bộ
  `accounts/staff/services.py` (BR-PQ-17/18), `cancel_receipt` (`purchasing/receipts/services.py:171`), `find_assignee_group_for_step`,
  `AiActionViewSet` (`user_groups.add(roles.OWNER)`), `run_due_ai_actions`, `pipeline.py`, `_escalate_to_owner`, `is_customer_service`,
  `scope_orders_for`, và phía FE `nav.ts` (`onlyDelivery`, `inGroup`), `StaffDetail`/`StaffCreateForm` (xác nhận khi đụng nhóm Chủ),
  `auth/mock.ts` `GROUP_PERMS`. **`is_owner` và `actor_is_owner`:** be-dev giữ cả hai là đúng. `is_owner(user)` chỉ xét Group,
  `actor_is_owner(actor)` = superuser **hoặc** `is_owner`. `_check_can_touch` gọi `is_owner(target)` (đích là Chủ) và `actor_is_owner(actor)`,
  đúng nghĩa như HEAD. Nếu gộp lại thì tài khoản superuser không thuộc nhóm `chu` sẽ bị coi là "Chủ cuối cùng" ở BR-PQ-18.
- **(3) `FORBIDDEN_PREFIXES`** (`backend/apps/ai/policy/rules.py:8-19`) không đổi, vẫn có `"/api/cskh/"`, và route thật vẫn là `/api/cskh/…`.
  `test_discovery` xanh với snapshot không regenerate. `_get_screens` không sinh màn `cskh`. `_get_group` vẫn xếp `apps.delivery.confirmation.*`
  vào `ban_hang` vì chuỗi con `delivery` (R8).
- **(5) Không rò giá vốn/PII mới.** `ReceivedBatchOutput` giữ `CostFieldSerializerMixin` + `sensitive_fields`. Serializer
  `Confirmation*` chỉ đổi tên class, vẫn gọi `note_in_customer_service_scope`. Không thêm log mới. Comment log "nhóm chu" giữ nguyên
  chữ. Không có dữ liệu thật trong diff (mock chỉ đổi literal thành `ROLE.*`, SĐT mock `0909…` có sẵn từ trước).
- **(6) File hằng khớp allowlist.** `EXEMPT_STRING_FILES` có đúng 4 path `accounts/roles.py`, `ai/registry/command_groups.py` (đổi path
  theo S1), `shared/lib/roles.ts`, `features/ai/commandGroups.ts`. Chỉ miễn chuỗi, định danh vẫn bị xét. Cả 4 file chỉ chứa hằng, không
  import gì. Hai file Python có docstring nêu lý do và thời điểm đổi giá trị (Lô 4).
- **(7) `ViewKey` "cskh"→"confirmation"** chỉ là khoá kiểu TS trong FE. Tìm trong repo: `ViewKey` chỉ dùng ở `canView`, `navItem`,
  `ViewGuard`, `Placeholder`, `LoginScreen` (lấy `item.key` từ `NAV`). Không lưu vào storage, không gửi BE, không so với `screens` của AI
  (BE không sinh màn `cskh`). Luật `visible` và `href: "/cskh/"` của mục menu không đổi. `me.home` không phụ thuộc view key. `tsc` sạch
  thì không còn chỗ nào dùng `"cskh"` làm ViewKey.
- Không còn tên cũ ngoài phạm vi Lô 3: tìm `cskhArmStale|cskh-stale-alert|cskh-notice|CskhNotice|NhapLoForm|NHAP_LO_DRAFT_PREFIX|VN_TZ|todayVn|currentYearVn|vn_today|KHO_LANH|delivery\.cskh|features/cskh|GROUP\.`
  chỉ ra 4 dòng logger `cangca.delivery.cskh` (giữ tới Lô 3) và dòng glossary trong `AGENTS.md`.
- Test không đổi assert: số test giữ nguyên. Thay đổi trong test chỉ là literal thành hằng, đường import, tên helper
  (`Confirmation*BaseTestCase`, đúng 02c) và username test.

### 3. Nên sửa (không chặn, làm cùng lượt S1 nếu tiện)
- N1 — `backend/apps/accounts/auth/services.py:20`: `from apps.accounts import roles` đang nằm sau import tương đối `.authentication`.
  Nên đưa lên nhóm import tuyệt đối `apps.*`, cho giống các file khác.
- N2 — `backend/apps/accounts/staff/services.py:324` và `staff/serializers.py:12`: tham số `active_owner_ids` trùng tên hàm module
  `active_owner_ids()` và che hàm này trong thân `available_actions`. Hiện chưa gây lỗi, nhưng về sau ai gọi `active_owner_ids()` trong
  hàm đó sẽ gặp `TypeError`. Nên đặt lại tên tham số, ví dụ `owner_ids` (cả hai nơi gọi trong `staff/api.py`).
- N3 — `HOME_CONFIRMATION_QUEUE` nằm trong `erp-console/shared/lib/roles.ts`, là file 02c dành riêng cho tên Group. Chấp nhận được vì
  Lô 4 đổi cả hai giá trị cùng lúc và file đã được miễn chuỗi. Nếu để vậy thì sửa comment đầu file cho khớp ("tên Group và mã trang chủ
  theo vai").

### 4. Lưu ý khi commit (điều phối)
- 4 file mới đang untracked (`??`), phải `git add` rõ ràng: `backend/apps/accounts/roles.py`, file hằng nhóm lệnh AI (path mới sau S1),
  `erp-console/shared/lib/roles.ts`, `erp-console/features/ai/commandGroups.ts`. Nhiều file rename đang ở trạng thái `RM`, nên `git add`
  cả phần sửa trước khi commit.
- Sau S1 không cần chạy `--update` baseline: path mới được miễn chuỗi, định danh không đổi.
- Smoke E2E 5 vai của QA (điều kiện xong ở §3 Lô 1) vẫn phải chạy. Review này không thay cho bước đó.

Đã review lại S1 và N1–N3 ở vòng 2: REVIEW PASS.
