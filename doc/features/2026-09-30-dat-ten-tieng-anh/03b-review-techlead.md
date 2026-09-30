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
