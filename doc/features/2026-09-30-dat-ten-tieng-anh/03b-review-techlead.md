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

---

## Lô 3

> Tech Lead · 2026-10-01 · Diff chưa commit (72 file sửa, 4 rename, 12 file mới). Đối chiếu `02c-giao-viec.md` §1b, §1c, §3 Lô 3, §6
> và `03-dev-notes.md` mục "Lô 3 — BE", "Lô 3 — FE".

### Kết luận: **REVIEW PASS** (vòng 2, 01/10). Vòng 1: CẦN SỬA (S1), xem bên dưới.

#### Vòng 2: review lại S1, N1, N2, N3 (01/10)
| Mục | Kết quả kiểm trong lượt này |
|---|---|
| S1 | `test_receive_batches_alias.py:84-110`: hàm `test_receive_batches_cost_fields_follow_view_costprice_on_both_paths` chạy trên **cả hai** path. Với NV kho và Quản lý: `purchase_rate`/`landed_unit_cost` không có trong `batches[0]`, `rate` không có trong mọi `receipt.lines`, và có kiểm danh sách khác rỗng nên vòng lặp không chạy rỗng. Với Chủ: cả ba field có mặt, `rate` = 80000.00. **Đột biến (tôi tự chạy):** đặt `sensitive_fields=()` cho `ReceivedBatchOutput` và `PurchaseReceiptLineSerializer` trong tiến trình test riêng thì test **đỏ 4 ca** (2 path × 2 vai). Test có tác dụng thật |
| N1 | `ENV_CASES` dòng throttle giờ đọc `CAVEVE_THROTTLE_RATES.customer_search` (`_load_settings` đọc giá trị trong dict). Test cả 4 ca: tên mới, tên cũ, cả hai, mặc định `30/min` |
| N2 | `frontend/features/site/types.ts:11` và `ConfirmationPolicyNotice.tsx:16` đã ghi `CONFIRMATION_WORKING_HOURS`, tên cũ ghi là fallback |
| N3 | Marker ở 2 dòng import `test_cskh_l2` đã ghi "đổi ở Lô 5 (02c)", khớp với §7c do điều phối ghi |
| Lệnh | `manage.py test apps.purchasing.receipts.tests.test_receive_batches_alias apps.delivery.tests.test_confirmation_env_commands`: `Ran 22 tests … OK`. `check_naming.py`: OK 6554, exit 0. `git diff` snapshot chỉ mục AI và `purchasing/receipts/serializers.py`: rỗng (code sản phẩm không bị sửa) |

Bộ đầy đủ 1714 test do be-dev báo. Trong lượt này tôi chỉ chạy lại 2 file test bị sửa; 600 test của 4 app chạy ở vòng 1 vẫn còn giá trị, vì
vòng 2 không đụng code sản phẩm BE. Mục 4 (điểm chốt Lô 4) và mục 5 (lưu ý commit) bên dưới vẫn áp dụng; file
`test_receive_batches_alias.py` vẫn untracked, cần `git add`.

#### Vòng 1 (lịch sử): CẦN SỬA. Có một việc sửa nhỏ, chỉ trong test (S1). Contract, phân quyền, chống rò giá vốn/PII và R1 đều đạt.

### Lệnh đã chạy trong lượt review
| Lệnh | Kết quả |
|---|---|
| `cd backend && DJANGO_DEBUG=1 env -u DATABASE_URL .venv/bin/python manage.py test apps.delivery apps.purchasing apps.ai apps.content` (không `--parallel`) | `Ran 600 tests … OK`. QA-LO2 quét theo vai: `{'chu': 43, 'quan_ly': 39, 'nv_kho': 28, 'nv_giao': 5, 'cskh': 3}`, khoá giống PII ngoài tập lọc `{}` |
| `cd erp-console && npm test` | 16 file, **217/217 pass** |
| `python3 scripts/check_naming.py` | `OK - 6554 vi phạm cũ trong 203 file`, exit 0 |
| `git diff --exit-code -- backend/apps/ai/registry/tests/snapshots/` | exit 0, snapshot chỉ mục AI không đổi |
| `git status -- '*/migrations/*'` | rỗng |
| So `naming_baseline.json` HEAD với worktree, từng file | Không file nào tăng. Chỉ có một key mới là `erp-console/e2e/sr07_receive_batches_draft.py` = 7, do `git mv` từ `sr07_nhap_lo_draft.py` = 11 (key cũ đã bị xoá), nên được chấp nhận |
| Nạp `config.settings` trong tiến trình con với `THROTTLE_CSKH_SEARCH=4/min`, rồi với cả hai tên, rồi `=off`, rồi để trống | `CAVEVE_THROTTLE_RATES["customer_search"]` lần lượt = `4/min`, `6/min` (tên mới thắng), `None`, `30/min`. Đúng |

### 1. Việc phải sửa trước khi commit
- **S1 — test chống rò giá vốn của route mới không kiểm gì.**
  `backend/apps/purchasing/receipts/tests/test_receive_batches_alias.py`, hàm `test_receive_batches_does_not_leak_cost_to_non_cost_roles_via_response`
  kiểm chuỗi `valuation_rate`, `cost_per_kg`, `landed_cost`. Không serializer nào có các field này. `landed_cost` cũng không phải chuỗi con
  của `landed_unit_cost`. Vì vậy test xanh kể cả khi phản hồi lộ giá vốn. Các field nhạy cảm thật là `rate`
  (`PurchaseReceiptLineSerializer.sensitive_fields`), `purchase_rate` và `landed_unit_cost` (`ReceivedBatchOutput.sensitive_fields`).
  Test cũ `test_nhap_lo.py` (DW-17-AC5) chỉ phủ đường `nhap-lo/`. Ở Lô 4, route `receive-batches/` sẽ được nối lại sang method mới, đúng chỗ
  dễ hồi quy, nên test này phải có tác dụng thật.
  **Sửa:** viết theo mẫu `test_nhap_lo.py:137-167` và chạy trên **cả hai** path. Với `warehouse_staff`, assert
  `"purchase_rate"` và `"landed_unit_cost"` không có trong `batches[0]`, và `"rate"` không có trong mọi dòng `receipt.lines`
  (`PurchaseReceiptSerializer` có trả `lines`). Với `owner`, assert các field này **có mặt**, để chứng minh test kiểm đúng chỗ. Không sửa code sản phẩm.

### 2. Đạt yêu cầu (đã soát)
| Trọng tâm | Kết quả |
|---|---|
| **R1 Critical**: `/api/confirmation/` bị chặn khỏi chỉ mục AI | `rules.py:17-18` có cả `"/api/cskh/"` (giữ vĩnh viễn) và `"/api/confirmation/"`, cùng commit với route. `test_forbidden_prefixes.py` có 4 test: hằng số; registry thật đếm được hơn 0 spec mà không spec nào nằm dưới hai prefix; URLconf thật có route dưới cả hai prefix; **đột biến** bỏ từng prefix thì route lọt vào chỉ mục. Test này có tác dụng thật |
| Route `receive-batches` không lọt chỉ mục AI | Alias tầng route `as_view({"post": "nhap_lo"})`. Discovery bỏ qua id trùng (`if cmd_id in specs: continue`), nên chỉ có một id `…nhap_lo`. Route cũ đứng trước nên `spec.path` vẫn là `/nhap-lo/`. Snapshot không đổi. `test_receive_batches_is_not_a_second_ai_command` có kiểm |
| Quyền 3 tầng trên `receive-batches` | `view.action = "nhap_lo"` (do `as_view` đặt). `BusinessModelPermissions` đọc `required_perms` từ chính hàm action (`add_` + `change_purchasereceipt`), sau đó `require_perm` trong thân hàm. Route alias không thêm action mới, nên rủi ro R10 không phát sinh. Ma trận 5 vai + ẩn danh: 201/403/401 giống nhau trên hai path. GET trả 405. Payload sai trả 400 |
| Ma trận vai của hàng đợi và tìm kiếm | `test_confirmation_route_aliases.py` chạy list, retrieve, claim, search trên cả hai prefix với 5 vai và ẩn danh. Trạng thái nhận phiếu dùng chung (409 chéo prefix). `no-store`. Dữ liệu ngoài phạm vi chỉ có SĐT đã che, đếm được 2 phản hồi 200 |
| Throttle tìm kiếm | Chỉ có một `scope = "customer_search"`. Cache key không gồm path. Test `2/min` cho thấy request thứ 3 bị 429 trên cả hai prefix |
| Khoá JSON mới không thêm PII hay giá vốn | `attention`: khoá mới là bản sao số đếm, nằm trong cùng nhánh `has_confirm`/`has_decide`. Test kiểm mọi giá trị là `int` và tập khoá theo vai. `site-info` (AllowAny): `confirmation_policy` gồm đúng 8 khoá cấu hình, `cskh_notice = dict(policy)`, test sentinel PII và giá vốn xanh |
| Env mới/cũ | `_env_first` đọc tên mới, rồi tên cũ, rồi mặc định. 12 biến, có test tiến trình con cho 4 ca. Grep không còn `getattr(settings, "CSKH_…")`, nên không có chỗ nào âm thầm rơi về mặc định |
| Lệnh quản trị cũ | `process_cskh_deadlines` / `check_cskh_job_health` chỉ `call_command` sang lệnh mới. `SystemExit(1)` truyền nguyên, `--grace-minutes` được chuyển tiếp. Test chạy 2 lần cho thấy lệnh idempotent và cho cùng hiệu ứng |
| Logger | Đổi hẳn sang `cangca.delivery.confirmation` (2 nơi). `settings.py` không có `LOGGING` theo tên logger, nên code không gãy. Ảnh hưởng chỉ ở phía ops (bộ lọc Cloud Logging nếu có), đã ghi ở `moi-truong.md:84-86` |
| FE redirect `/cskh/` | `window.location.replace("/confirmation/" + search + hash)`. Đích là path cố định nên không có open redirect. Trang không render dữ liệu. Có e2e `p8b_confirmation_route_redirect.py` |
| **R4**: `clearAllDrafts` | `drafts.ts`: lặp qua **cả hai** tiền tố, xoá ở cả local và session. `LEGACY_RECEIVE_BATCHES_DRAFT_PREFIX` được ghi chú "GIỮ VĨNH VIỄN". `migrateLegacyDraft` cho dữ liệu đi qua `sanitize` (bỏ `rate`), chỉ chuyển khoá session của đúng `userId`, còn khoá local cũ thì chỉ xoá. `clearDraft` xoá cả khoá cũ. Có 8 test vitest mới |
| `normalize*` | `roles.ts` vẫn là nơi duy nhất chứa tên Group. `normalizeRole/Roles/Home` được áp ở biên API (`auth`, `staff`, `ai/actions`, `ai/policy`). `legacyIds.ts` chỉ chuẩn hoá trường dùng để so sánh và hiển thị. `findByCommand` trả về khoá thật để ghi ngược. Có test vitest cho payload cũ và payload mới |
| Marker `naming: allow` mới | **Duyệt** 4 file sản phẩm: `overview/api.ts:39-41`, `overview/types.ts` (trường legacy), `frontend/features/site/types.ts:33`, `ConfirmationPolicyNotice.tsx:11`. Duyệt thêm các marker phía BE: `attention_api.py`, `site/api.py`, `api_urls.py` (2 route), 2 dòng import `test_cskh_l2`. Mọi marker đều có lý do và đều thuộc danh sách gỡ ở Lô 5 |
| **Chốt lệch BE (alias tầng route)** | **Chấp nhận, sửa 02c theo code.** Hai yêu cầu "action mới" và "snapshot y hệt" mâu thuẫn nhau, và cách chọn của be-dev giữ được cả quyền lẫn snapshot. Hệ quả cho Lô 4: xem mục 4, ý 3 |

### 3. Nên sửa (không chặn; nên làm cùng lượt S1)
- N1 — `test_confirmation_env_commands.py`, `ENV_CASES` dòng `THROTTLE_*`: test đang kiểm thuộc tính `settings.THROTTLE_CUSTOMER_SEARCH`.
  Thuộc tính này không được code nào đọc (code cũ cũng chết như vậy). Mức throttle thật nằm ở `CAVEVE_THROTTLE_RATES["customer_search"]`
  (`settings.py:231`, `_rate(..., legacy_name=)`). Nên cho `_load_settings` in thêm giá trị này và assert cả 3 ca (tôi đã kiểm tay, kết quả đúng).
  Hằng `THROTTLE_CUSTOMER_SEARCH` (`settings.py:311`) có thể bỏ ở Lô 5.
- N2 — comment cũ vẫn ghi `settings.CSKH_WORKING_HOURS`/`settings.CSKH_*`: `frontend/features/site/types.ts:11` và
  `frontend/features/site/components/ConfirmationPolicyNotice.tsx:16`. Đổi thành `CONFIRMATION_WORKING_HOURS`.
- N3 — marker ở hai dòng import `test_cskh_l2` ghi "đổi tên ở Lô 5", nhưng 02c §3 Lô 5 không có việc đổi tên tệp test (theo Q3 thì đổi dần).
  Cách sửa: hoặc ghi lý do là "đổi dần theo §5", hoặc ghi rõ tên `test_cskh_l*.py` vào phạm vi Lô 5. Đề xuất đưa vào Lô 5, vì hai test mới
  phụ thuộc file này.

### 4. Điểm chốt cho Lô 4 (ghi vào giao việc 4a/4b)
1. **`me.home`** chốt là **`"confirmation-queue"`** (`apps/accounts/auth/services.py:29` `HOME_CONFIRMATION_QUEUE`). FE Lô 3 đoán đúng giá trị này.
   Sửa assert `test_cskh_l1.py:130` theo, vì đây là assert **tên**, được phép.
2. **BE 4a phải nhận tên cũ trên mọi đường GHI**, vì FE Lô 3 có thể vẫn chạy trên staging trong lúc BE 4a đã lên:
   - `PUT /api/staff/{id}/groups/`: dùng `LEGACY_ROLE_NAMES`, như 02c đã ghi.
   - `PUT /api/ai/policy/`, khoá trong `caps`: `AiPolicyScreen` ghi bằng `RECEIVE_BATCHES_COMMAND_ID` (= id cũ `…nhap_lo`) khi chưa có cap nào.
     `PolicyUpdateSerializer.caps` là `DictField` nhận khoá tuỳ ý, nên nếu không chuẩn hoá thì phiên bản mới sẽ lưu khoá cũ, `effective.py` bỏ qua
     khoá đó và trần bị nới mà không ai biết (R5). **Phải đổi khoá cũ sang khoá mới (`legacy_ids.py`) trước khi append phiên bản.** Làm tương tự
     cho `overrides`/`limits` của `PUT /api/ai/my-config/`, vì cache descriptor ở FE có thể còn giữ id cũ.
   - Test bắt buộc: PUT với khoá cũ thì phiên bản mới lưu khoá mới, và `effective_level`/trần bằng với khi PUT bằng khoá mới.
3. **Route nhập lô ở Lô 4:** đổi tên method thành `receive_batches` (có `ai=`, `url_path="receive-batches"`). Thêm `"receive_batches"` vào
   `custom_perm_actions`; lúc này R10 bắt đầu có hiệu lực. Alias `nhap-lo/` đổi thành `as_view({"post": "receive_batches"})`. **Đặt route `receive-batches/`
   trước `nhap-lo/`** (hoặc bỏ path tường minh, để router tự sinh) để `spec.path` là `/receive-batches/`. Diff snapshot chỉ được gồm id và path
   của lệnh nhập lô. Test 403 cho `delivery_staff`/`customer_service` phải chạy trên cả hai path (S1 sau khi sửa sẽ phủ phần giá vốn).
4. FE 4b đổi giá trị `RECEIVE_BATCHES_COMMAND_ID`, `HOME_CONFIRMATION_QUEUE`, `ROLE`, `COMMAND_GROUP`, `SENSITIVITY`. Lớp `normalize*` đã nhận cả hai
   tên, nên không phải sửa nơi dùng.
5. Lô 5: giữ `"/api/cskh/"` trong `FORBIDDEN_PREFIXES` (be-dev hỏi, trả lời: **giữ**, đúng như 02c) và giữ `LEGACY_RECEIVE_BATCHES_DRAFT_PREFIX`.

### 5. Lưu ý khi commit (điều phối)
- File untracked phải `git add` rõ ràng: `backend/apps/ai/registry/tests/test_forbidden_prefixes.py`,
  `backend/apps/delivery/management/commands/{process_cskh_deadlines,check_cskh_job_health}.py` (lệnh bọc; bản rename đang `RM`),
  `backend/apps/delivery/tests/test_confirmation_{env_commands,route_aliases}.py`, `backend/apps/purchasing/receipts/tests/test_receive_batches_alias.py`,
  `erp-console/app/(console)/cskh/page.tsx` (trang redirect; rename sang `confirmation/` đã staged), `erp-console/e2e/p8b_confirmation_route_redirect.py`,
  `erp-console/features/ai/legacyIds.ts`, `erp-console/features/confirmation/apiPaths.test.ts`, `erp-console/shared/lib/legacyNames.test.ts`.
- **Không** commit `doc/features/2026-09-30-ra-soat-agy/q1-pii-xac-minh.md` trong commit Lô 3. File này thuộc hồ sơ khác; điều phối tự quyết.
- Trước khi deploy BE lên staging: kiểm env `CSKH_*` và args của Cloud Run Job, và bộ lọc log theo `cangca.delivery.cskh` (02c §3 Lô 3).
- E2E QA (5 vai, FE cũ + BE mới) vẫn là điều kiện xong. Review này không thay cho bước đó.

## Lô 4a

Review BE đổi DỮ LIỆU sang tiếng Anh (chưa commit, 01/10). Phạm vi: `git diff` 51 file và 11 file mới (`accounts/0013`, `ai/0003`,
`legacy_ids.py`, `preview_group_rename`, 7 test). Đối chiếu với 02c §3 Lô 4, §6 (R2, R3, R5, R6, R8, R9, R10, R12) và §7c.

### Kết luận: **REVIEW PASS** (vòng 1, 01/10)
Không có lỗi chặn. Chấp nhận cả 4 lệch thiết kế mà be-dev ghi trong 03-dev-notes. Mục 3 là việc nên sửa, không chặn commit.
N1 nên làm trước khi chạy `preview_group_rename` trên staging. Deploy staging làm theo mục 4.

### Lệnh đã chạy trong lượt review
- `DJANGO_DEBUG=1 env -u DATABASE_URL manage.py test apps.accounts apps.ai apps.purchasing apps.delivery` (không `--parallel`): **724 tests OK**.
- `manage.py makemigrations --check --dry-run`: No changes detected. `python3 scripts/check_naming.py`: OK, không phát sinh mới.
- `git status backend/apps/*/migrations`: chỉ có 2 file mới (`accounts/0013`, `ai/0003`). Migration cũ không bị sửa (R12).
- **Chạy migrate thật trên SQLite** (scratchpad `p8b-l4-review/`, dữ liệu giả, username `fake_*`):
  1. Dựng DB giống staging: migrate tới `accounts 0012`, `ai 0002`, các app khác tới bản mới nhất. 5 Group mang tên cũ, id 1–5,
     lần lượt 147/67/36/9/4 quyền. Tạo 5 user, mỗi user một Group, thêm 1 user kiêm `quan_ly`+`nv_kho`. Tạo 2 `AiConfigVersion` có khoá cũ:
     `thu_mua`, id `…nhap_lo` và alias ngắn `nhap_lo` ở `limits`. Tạo 1 `AiPolicyVersion` có `caps[…nhap_lo]`. Tạo 2 `AiAction`:
     một việc ESCALATED giao `chu` và một việc PENDING giao `quan_ly`, cả hai mang id lệnh cũ.
  2. `preview_group_rename` trước migrate: in đúng số Group, quyền và thành viên. In 2 việc AI và 1 user, 1 chính sách còn khoá cũ, 0 xung đột.
     Không in username.
  3. `migrate`: chạy `accounts.0013` rồi `ai.0003`. So ảnh chụp trước và sau:
     - id Group giữ nguyên, tập quyền của từng Group giống hệt, thành viên giống hệt.
     - `get_all_permissions()` của **mọi user** giống hệt trước migrate (R2).
     - `warehouse_staff` không có `sales.view_customer`.
     - Dòng `AiConfigVersion`/`AiPolicyVersion` cũ không đổi. Mỗi bảng có thêm đúng 1 phiên bản mang khoá tiếng Anh, giá trị giữ nguyên (R9).
     - `AiAction` đổi sang `receive_batches` và giao `owner`/`manager` (R6). Chủ vẫn thấy việc ESCALATED qua `visible_actions_for`.
     - `effective_level`, mức khi ghim phiên bản cũ, cap và limit của `receive_batches` cho NV kho, Quản lý, Chủ đều như trước (R5).
  4. Rollback `migrate accounts 0012`: `ai.0003` gỡ trước, `0013` gỡ sau. Group trở về y hệt ảnh chụp ban đầu, `AiAction` trở về id và Group cũ.
     Phiên bản AI chỉ được **thêm** (ghi chú "P8b rollback"), không dòng nào bị sửa hay xoá. Code 4a chạy trên DB đã rollback vẫn tính
     đúng mức và trần. Sau đó migrate lại: kết quả giống lần 1.
  5. Ca xung đột: từ DB sạch giống staging, tạo thêm Group `owner`. `preview` báo "XUNG ĐỘT: 1". `migrate` dừng với `RuntimeError`,
     `0013` không được ghi vào `django_migrations` và Group không đổi.
  6. DB mới từ đầu: 5 Group tên tiếng Anh. Tập quyền theo tên **trùng khớp** với DB đi đường staging. Như vậy dependency chéo
     (`ai/0002`, `content/0002`, `sales/0010` chạy trước `0013`) là đủ và đúng.

### 1. Lỗi chặn
Không có.

### 2. Đạt yêu cầu (đã soát)
- **R2, `accounts/0013`:** dùng `filter(name=old).update(name=new)` nên id giữ nguyên, không xoá rồi tạo lại Group. Hàm kiểm toàn bộ xung đột
  **trước** khi đổi bất kỳ Group nào. Có reverse, chạy lại không đổi gì, chỉ in số lượng. Tên Group đóng băng trong file, không import `roles`.
- **Dependency chéo (lệch 1, chấp nhận):** grep mọi migration có tên Group cũ thì chỉ có `accounts/0002…0012`, `ai/0002`, `content/0002`,
  `sales/0010`. Tất cả đều là tiền đề của `0013`. Trên staging các migration này đã chạy rồi, nên dependency chỉ có tác dụng với DB mới.
- **R5, R9, `ai/0003`:** chỉ append phiên bản, lấy từ phiên bản mới nhất của mỗi user và của chính sách. `killed`, `global_mode`,
  `red_zone_open` và `created_by` được giữ. Khi khoá mới đã có sẵn thì khoá mới thắng. Không có khoá cũ thì không tạo gì. Không đụng
  `AuditLog`. Bảng ánh xạ đóng băng trong file migration.
- **`legacy_ids.py`:** gồm các hàm thuần, chịu được `None` hoặc giá trị không phải dict. Được gọi ở mọi chỗ **đọc** `caps`, `overrides`,
  `group_levels`, `limits`: `effective_level` (cả khi ghim phiên bản), `get_cap_for_command` (pipeline dùng hàm này cho cả cap lẫn limit),
  `get_user_config_data`, `get_policy_data`. Đọc `red_zone_open` không cần chuẩn hoá vì khoá là codename quyền, không đổi.
- **§7c, mọi đường GHI nhận tên cũ và lưu tên mới:** `_resolve_groups` (tạo nhân viên, PUT groups) chuẩn hoá rồi mới tra DB. Gửi tên cũ của
  Chủ vẫn phải là Chủ mới được (có test). `update_policy.caps` chuẩn hoá trước khi kiểm và lưu; `caps=None` vẫn nghĩa là "không đổi".
  `update_user_config` chuẩn hoá `groups`, `overrides`, `limits` trước khi kiểm vượt trần. Không có đường nào nới trần.
- **Ma trận 21 endpoint × 7 actor** (`test_role_permission_matrix.py`): có cả 2 path nhập lô, `delivery_staff`/`customer_service` nhận 403 (R10).
  Test kiểm DB chỉ còn đúng 5 Group tên mới. `me.home` của CSKH là `confirmation-queue`.
- **Route nhập lô:** `receive-batches/` khai trước nên `spec.path` là `/receive-batches/`. `nhap-lo/` là alias route trỏ cùng method, nên
  không thêm id lệnh. `custom_perm_actions` đã có `receive_batches`. Cả hai path đều đặt `self.action="receive_batches"`, nên Tầng 1 và
  Tầng 2 giống nhau.
- **Snapshot (R8):** diff đúng 1 dòng, đổi `…nhap_lo` thành `…receive_batches`. Giá trị `group`/`sensitivity` không nằm trong snapshot;
  `registry.get_specs()` thật trả `purchasing/sales/customer_service` và `high/medium`.
- **Bỏ keyword snake-case không làm giảm recall:** `tokenize()` của ERP (`features/ai/commands/search.ts`) bỏ dấu rồi tách theo ký tự không
  phải chữ/số. Vì vậy `chot_lo` và `chốt lô` cho cùng token `chot`, `lo`. Bỏ bản snake chỉ bỏ token trùng lặp.
- **`FORBIDDEN_PREFIXES`:** không đổi, vẫn có cả `/api/cskh/` lẫn `/api/confirmation/`.
- **ERP Lô 3 (đang chạy trên staging) với BE 4a:** `normalizeRole`, `normalizeHome`, `normalizeAiGroup`, `normalizeSensitivity`,
  `findByCommand` nhận cả hai tên. FE ghi `caps`/`overrides` bằng khoá BE trả, còn `groups`/Group bằng tên cũ, và BE 4a chuẩn hoá các khoá
  này. Hai bên tương thích về contract. Cần E2E staging để xác nhận.
- **Lệch 2–4, chấp nhận:**
  - Lệch 2: test gọi hàm migration trực tiếp. Lượt review đã chạy migrate/rollback thật để bù.
  - Lệch 3: `test_s03_migration` bỏ `ai` khỏi leaf. Đúng, vì `ai/0003` kéo `accounts` tới `0013`.
  - Lệch 4: `test_customer_data_scope` đặt Group về `nv_kho` trong transaction của test. Đúng, vì `0012` đóng băng tên cũ, và test so
    "nhóm khác" theo `pk`.
  - `test_p8_qa_lo2_matrix` trả `roles.OWNER` về `"chu"`. Đây là tên **thuộc tính fixture** (`self.chu`), không phải tên Group. Assert
    chống rò không bị nới.
- **PII và giá vốn:** không thêm field hay serializer nào. Migration và `preview` chỉ in số lượng; có test kiểm output không chứa username.
  Log `auto_confirm` chỉ đổi từ chữ cố định sang `roles.OWNER`.
- `doc/decisions.md`: chỉ đổi mã Group ở 2 dòng và thêm ghi chú, đúng phạm vi Duy cho phép ở §7b.

### 3. Nên sửa (không chặn)
- **N1 (nên làm trước khi chạy preview trên staging), `apps/accounts/management/commands/preview_group_rename.py:37-50`:** lệnh chưa báo Group
  **lạ**, tức Group ngoài 10 tên cũ và mới, trong khi đó là một điểm dừng ở 02c §3 Lô 4. Thêm một dòng
  `Group khác ngoài 5 vai: N`, đếm bằng `Group.objects.exclude(name__in=[*LEGACY_ROLE_NAMES, *ALL_ROLES]).count()`, chỉ in số lượng.
  Thêm 1 assert vào `test_preview_group_rename.py`. Nếu chưa sửa thì người chạy staging phải đếm tay bằng `manage.py shell`.
- **N2, `apps/ai/migrations/0003_rename_ai_keys_to_english.py:63-69`:** `_rename_actions` cộng số lượt UPDATE. Một việc vừa đổi lệnh vừa
  đổi Group bị đếm 2 lần: thử nghiệm in "4 việc AI" trong khi chỉ có 2 dòng. Số liệu này dùng để đối chiếu với `preview`, vì vậy cần sửa
  chữ thành "lượt cập nhật việc AI" hoặc đếm số dòng riêng. Sửa được vì migration chưa chạy ở đâu.
- **N3, `apps/ai/settings/serializers.py:47` và `apps/ai/settings/services.py:341`:** lịch sử cấu hình AI so `overrides` thô giữa hai
  phiên bản. Vì vậy phiên bản "P8b: đổi khoá" sẽ hiện `receive_batches: default → C` như thể người dùng vừa đổi mức. Cần chuẩn hoá cả hai
  phía bằng `legacy_ids.normalize_command_keys` trước khi so.
- **N4, `apps/accounts/staff/tests/test_group_rename_migration.py:139-147`:** test thứ tự đang liệt kê cứng 3 migration. Nên quét mọi file
  `apps/*/migrations/*.py` có chứa tên Group cũ và assert từng file nằm trong `forwards_plan(0013)`, để migration gán quyền theo tên cũ
  thêm sau này không lọt.
- **N5, R6:** chưa có test `run_due_ai_actions` chạy việc tạo bằng id cũ sau khi đổi tên, như 02c yêu cầu. Lượt review đã kiểm bằng
  sandbox: registry tra được id mới và việc vẫn giao đúng Group. Nên bổ sung một test trong `test_ai_key_migration.py`.
- **N6:** còn comment và docstring nhắc `'chu'` ở `apps/ai/management/commands/run_due_ai_actions.py:69` và
  `apps/ai/actions/api.py:130`. Cần đổi thành `owner`.
- **Ghi cho 4b (FE):** khi `COMMAND_GROUP` nội bộ đổi sang tiếng Anh, `BM25Index` đưa `doc.group` vào text nên mất token tiếng Việt
  `thu mua`/`ban hang`. Cần thêm nhãn nhóm tiếng Việt vào text chỉ mục (hoặc keyword), rồi thử vài câu hỏi "thu mua…", "bán hàng…"
  trước và sau khi đổi.

### 4. Hướng dẫn deploy staging an toàn (mỗi bước cần Duy cho phép)
Trong khoảng *code 4a chạy trên DB chưa migrate*, các kiểm tra theo tên Group sẽ **đóng chặt chứ không lộ dữ liệu**:
`FULL_SCOPE_GROUPS`, `sees_customer_directory`, `is_customer_service`, `actor_is_owner`, `home_for`. Ví dụ Chủ tạm thời không quản lý
được nhân viên, NV kho thấy ít đơn hơn. Không có rò rỉ, nhưng vẫn nên giữ khoảng này gần bằng 0:
1. Build image mới `api:v8` từ commit 4a. **Chưa** chuyển traffic: `gcloud run deploy cangca-api-staging --image …:v8 --no-traffic --tag p8b4a`.
2. Cập nhật job `cangca-migrate-staging` sang image `v8`. Job cũ chạy image cũ thì không có `0013`/`0003` và không có lệnh `preview`.
3. Chạy job với `--args manage.py,preview_group_rename` rồi dán số liệu vào 03-dev-notes. **Dừng** nếu có xung đột, thiếu Group cũ, Group lạ
   (N1) hoặc số khác dự kiến.
4. Chạy job với lệnh mặc định `manage.py,migrate,--noinput`. Log phải có "đã đổi tên 5 Group (giữ id)" và dòng `ai:`.
5. Chạy lại `preview_group_rename`: id, số quyền, số thành viên của từng vai phải **giống hệt** bước 3, và mọi số "còn khoá cũ" phải bằng 0.
6. `gcloud run services update-traffic cangca-api-staging --to-latest`.
7. E2E 5 vai với **ERP Lô 3** (FE chưa đổi): menu, trang chủ (CSKH vào `/confirmation/`), sửa nhóm nhân viên (FE gửi tên cũ), hàng đợi
   gọi xác nhận, Nhập lô qua cả hai path, màn Cài đặt AI và Chính sách AI hiện đúng trần cũ. Phạm vi `delivery_staff` phải vẫn chỉ thấy
   khách của phiếu mình.
8. Sau đó mới deploy FE 4b và chạy lại E2E 5 vai. Thứ tự bắt buộc: **BE 4a và migrate trước, FE 4b sau.** FE 4b gửi tên mới, BE cũ không
   hiểu tên này.
- **Rollback:** dùng chính image `v8` (image có hàm reverse) để chạy job với `--args manage.py,migrate,accounts,0012`. Lệnh này gỡ
  `ai.0003` rồi `0013`, và chỉ thêm phiên bản AI "P8b rollback", không xoá dòng nào. Sau đó chuyển traffic về revision Lô 3
  (`cangca-api-staging-00005-7fp`, `api:v7`). Không được chuyển traffic về `v7` khi DB vẫn mang tên mới: tình trạng đó cũng đóng chặt
  chứ không lộ, nhưng mất quyền theo vai.
- Trên Postgres, mỗi migration chạy trong một transaction riêng. Nếu `0013` xong mà `ai.0003` lỗi, Group đã mang tên mới nhưng
  `AiAction.assignee_group` còn tên cũ, và việc ESCALATED cũ sẽ không hiện cho Chủ. Khi đó sửa nguyên nhân rồi chạy lại `migrate`.
  `0003` chạy lại an toàn.
- Production đang tắt, nên đi một lượt theo 02c §3 Lô 4 bước 5. Không đụng production trong lô này.

### 5. Lưu ý khi commit (điều phối)
- `git add` rõ 11 file mới: 2 migration, `legacy_ids.py`, `preview_group_rename.py`, 7 file test trong `accounts/staff/tests/`,
  `ai/policy/tests/`, `ai/registry/tests/`, `ai/settings/tests/`.
- Nếu sửa N1, N2 thì chạy lại bộ test của 4 app, `makemigrations --check` và `check_naming` trong cùng lượt báo xong.

## Lô 4b

Phạm vi: diff chưa commit ở `erp-console/` (5 hằng, `search.ts`, `policy/caps.ts`, `AiPolicyScreen.tsx`, `mock.ts`, 13 file e2e Python),
`scripts/naming_baseline.json`, `03-dev-notes.md` mục "Lô 4b — FE". Đối chiếu BE Lô 4a đã commit `fd3b3bb`.

### Kết luận: **REVIEW PASS** (vòng 1, 01/10)

Không có lỗi chặn. Ở mục 3 có 3 ghi chú không chặn và 1 ràng buộc deploy bắt buộc (mục 4).

### Lệnh đã chạy trong lượt review
- `cd erp-console && npx tsc --noEmit`: sạch.
- `cd erp-console && npm test`: 22 file, 251 test xanh.
- `python3 scripts/check_naming.py`: OK, 6536 vi phạm cũ trong 195 file, không phát sinh mới (exit 0).
- Grep chuỗi cũ (`chu quan_ly nv_kho nv_giao cskh thu_mua ban_hang cao trung_binh thap cskh-queue nhap_lo`) trong
  `features/ shared/ app/`: chỉ còn ở bảng chuẩn hoá `roles.ts`/`legacyIds.ts`, test của lớp chuẩn hoá, khoá nháp cũ
  `cave_draft_nhap_lo` (đường chuyển nháp Lô 3) và nhãn tìm kiếm `"cskh"`. Đúng phạm vi.
- `git show dd49133:backend/apps/accounts/staff/services.py`: BE trước 4a báo lỗi "Nhóm không tồn tại" khi nhận tên mới. Đây là căn cứ của mục 4.

### 1. Lỗi chặn
Không có.

### 2. Đạt yêu cầu (đã soát)
- **Giá trị hằng khớp BE thật.**
  - `ROLE` khớp `backend/apps/accounts/roles.py` (`owner manager warehouse_staff delivery_staff customer_service`).
  - `HOME_CONFIRMATION_QUEUE = "confirmation-queue"` khớp `backend/apps/accounts/auth/services.py:29`.
  - `COMMAND_GROUP` và `SENSITIVITY` khớp `backend/apps/ai/command_groups.py`.
  - `RECEIVE_BATCHES_COMMAND_ID = "purchasing.purchasereceipt.receive_batches"` khớp registry và snapshot 4a.
  - `englishNames.test.ts` chốt các giá trị này bằng chuỗi thẳng, nên đổi nhầm thì test đỏ.
- **`normalize*` vẫn nhận tên cũ.** Bảng `LEGACY_ROLE_NAMES`, `LEGACY_COMMAND_IDS/GROUPS/SENSITIVITIES` không đổi, cả hai chiều
  đều trỏ về hằng mới. `legacyNames.test.ts` xanh y nguyên, và `englishNames.test.ts` thêm ca cũ -> mới.
- **Đường ghi gửi tên mới.**
  - Staff: `StaffDetail` gửi `groups` lấy từ `ROLE.*` / member đã `normalizeRoles` (`features/staff/api.ts:21-26`).
  - my-config: `overrides` khoá theo `cmd.id` do BE trả, sau 4a là id mới.
  - caps: `buildCapsForSave` luôn ghi `RECEIVE_BATCHES_COMMAND_ID`.
- **`buildCapsForSave` không làm mất cap đặt bằng khoá cũ.**
  - Giá trị của khoá cũ được trộn vào khoá mới (`{...existing.value, ...next}`). Ví dụ `max_level` vẫn giữ, có test `caps.test.ts` ca 2.
  - Các lệnh khác giữ nguyên.
  - Thực tế BE 4a đã chuẩn hoá `caps` khi ĐỌC (`backend/apps/ai/policy/services.py:27`) và khi GHI (`:122`), nên FE không còn nhận khoá cũ. Nhánh bỏ khoá cũ chỉ là lưới an toàn.
- **Recall bộ tìm lệnh.**
  - `COMMAND_GROUP_SEARCH_LABEL` thay khoá nhóm trong văn bản chỉ mục. Sau khi bỏ dấu và tách từ, `"thu mua"`/`"bán hàng"`/`"cskh"`
    ra đúng các token của khoá cũ `thu_mua`/`ban_hang`/`cskh`, nên độ dài tài liệu BM25 không đổi.
  - `groupSearchText` nhận cả khoá cũ và mới qua `normalizeAiGroup`. Nhóm lạ giữ nguyên khoá như trước.
  - `groupSearch.test.ts` chứng minh chỉ mục khoá cũ và chỉ mục khoá mới cho cùng thứ tự kết quả.
  - Phép đo 14 câu trên chỉ mục thật 111 lệnh: 9/14 câu lệch khi chưa có nhãn, 0/14 sau khi thêm. Đủ thuyết phục, dù phép đo này không commit (xem 3c).
- **`groupLabel` ở màn chính sách AI.** `u.groups` đã qua `normalizeAiPolicy` (tên mới), nên `groupLabel` ra "Chủ", "Nhân viên kho"… Không để lộ mã
  tiếng Anh ra giao diện. Nhóm lệnh trong my-config và modal hiện `grp.label` do BE trả, không phải mã. `sensitivity` không được render thô.
- **PII và giá vốn.** Diff không thêm field, không thêm log hay console. `mock.ts` chỉ đổi chữ mô tả nhật ký giả. Dev chạy `check-no-mock.mjs` xanh trên build thật.
- **e2e literal.** Các assert JSON `groups` (`s41_s47_staff.py`, `s41_s47_real.py`), `patchUser(... groups: [...])` và nhãn tài khoản ở
  `a2_catalog_real.py` đã đổi đúng sang tên mới. Hai literal cố ý giữ: `cave_draft_nhap_lo` (kiểm chuyển nháp) và `/cskh/` (kiểm redirect).
- **Baseline naming.** Baseline chỉ xoá 8 mục BE đã về 0 vi phạm sau 4a, không nới file nào.

### 3. Nên sửa (không chặn)
- **3a. `features/ai/commands/budget.ts:62`: prompt LLM có `Nhóm: purchasing`.** Đề xuất **giữ nguyên**, không đổi sang nhãn Việt.
  - Khoá tiếng Anh rõ nghĩa với LLM hơn `thu_mua` cũ, và tốn ít token hơn.
  - Không chứa PII.
  - Việc chọn lệnh do BM25 làm. LLM chỉ chọn trong top-5 nên nhóm chỉ là gợi ý phụ.
  - Nếu sau này muốn prompt thuần Việt, đừng dùng lại `COMMAND_GROUP_SEARCH_LABEL`, vì hằng đó là để tìm kiếm, không phải để hiển thị. Nên tạo một nhãn hiển thị riêng.
- **3b. `features/ai/policy/caps.ts:16`: `findByCommand` lấy khoá khớp ĐẦU TIÊN.** Nếu bảng có cả khoá cũ lẫn khoá mới, field phụ (vd `max_level`)
  có thể lấy từ khoá cũ, trái quy tắc "khoá mới thắng" của BE (`legacy_ids.normalize_command_keys`). Hiện không xảy ra vì BE chuẩn hoá khi đọc.
  Nếu sửa: ưu tiên `caps[RECEIVE_BATCHES_COMMAND_ID]` trước, rồi mới `findByCommand`, kèm 1 ca test. Có thể dồn vào Lô 5, lúc gỡ hẳn khoá cũ.
- **3c. Chú thích lệch:**
  - `erp-console/e2e/s7_shell.py` còn ghi "chu, manager" (nửa cũ nửa mới). Sửa thành "owner, manager".
  - Phép đo recall 14 câu trên chỉ mục thật chỉ nằm ở scratchpad. Nếu muốn giữ làm hồi quy thì cần commit một snapshot chỉ mục (không PII) kèm test, có thể làm ở Lô 5.

### 4. Ràng buộc deploy (bắt buộc, điều phối ghi vào kế hoạch deploy)
FE 4b **GHI** tên mới:
- `PUT /api/staff/{id}/groups/` và tạo nhân viên với `owner`/`warehouse_staff`…
- khoá caps `…receive_batches`.

BE trước 4a báo 400 "Nhóm không tồn tại" (kiểm ở `dd49133:backend/apps/accounts/staff/services.py:77-81`). Vì vậy, ở **mỗi môi trường**, FE 4b chỉ được deploy
**sau khi** BE 4a đã chạy migrate `accounts.0013` + `ai.0003` ở môi trường đó.
- Staging: BE 4a đã lên (api:v8), nên deploy được.
- Production: BE 4a phải lên trước, Duy duyệt theo hướng dẫn ở mục 4 của Lô 4a.

Chiều ĐỌC an toàn ở cả hai phía nhờ lớp `normalize*`.

### 5. Lưu ý khi commit (điều phối)
- Commit chung `erp-console/` (gồm 4 file mới `caps.ts`, `caps.test.ts`, `groupSearch.test.ts`, `englishNames.test.ts`), `scripts/naming_baseline.json`, `03-dev-notes.md`
  và file review này. Không commit `erp-console/out/`.
- `erp-console/out` hiện là bản build thật trỏ API **production**. Khi deploy staging, phải build lại với `NEXT_PUBLIC_API_BASE` của staging (`doc/ops/moi-truong.md`).
