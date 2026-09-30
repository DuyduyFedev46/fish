# Giao việc — P8b Đổi tên định danh sang tiếng Anh
> Claude (Tech Lead) · 2026-10-01 · Trạng thái: **SẴN SÀNG CODE (Duy 01/10)**
> Người hiện thực: **đội Claude** (CLAUDE.md "Người hiện thực: đội Claude"). Điều phối viên giao `be-dev` ∥ `fe-dev`,
> `techlead` review diff, `qa-tester` kiểm; APPROVED thì commit + `git push origin main`, đánh ☑ ở bảng dưới.
> Nhánh làm việc: `main`.
> Nguồn: `01-ra-soat-dat-ten.md` (mục 1–3 + "Quyết định Duy 30/09"). Hồ sơ này **không có** `02-stories.md`/`02b` riêng:
> việc là đổi tên thuần, không đổi nghiệp vụ; contract đổi tên ghi ở §3 dưới đây và thay cho 02b.

## Điều kiện đầu vào
- P8 xong (Lô 1–8, `807159e`), staging chạy P1–P8 (`api:v6`, `doc/ops/moi-truong.md` "Nhật ký deploy staging").
- Duy đã chốt Q1–Q4 ngày 30/09 (cuối `01-ra-soat-dat-ten.md`). Phiếu này cần Duy duyệt thêm các câu 🔴 ở §7.
- Làm **sau P8, trước P9**. Không chạy song song với hồ sơ nào khác đụng `backend/apps/delivery/`, `backend/apps/ai/`,
  `erp-console/features/{cskh,purchasing,ai}/`, `frontend/features/site/` — đổi tên hàng loạt sẽ conflict.
- Trước Lô 0: `git pull`; chạy bộ lệnh kiểm chứng §4 một lần, ghi **số gốc** vào `03-dev-notes.md`: số test backend
  (lần gần nhất: 1674), số test vitest ERP (185), `test-format` Shop (26), adapter pytest.
- Production **đang tắt** (chế độ tiết kiệm, `moi-truong.md`) và chưa lên P1–P8. Staging là nơi duy nhất có người dùng
  (đội dự án). Vì vậy alias tương thích chỉ cần sống qua các lần deploy staging, xem Lô 5.

---

## 1. Glossary chốt (tên tiếng Việt → tên trong code)

Luật: định danh (hàm, biến, class, module, thư mục, file, test, script, route API, khoá JSON, biến env, Group, codename,
id lệnh AI, khoá lưu trình duyệt, `data-testid`) là **tiếng Anh chuẩn**. Chữ hiển thị, comment, docstring, tài liệu vẫn
tiếng Việt. Không đưa mã lô giao việc (`lo7`, `l8`, `p8_lo5`) vào tên; mã lô/story ghi trong docstring.
Viết tắt chỉ được dùng khi là chuẩn quốc tế: `VN` (ISO quốc gia), `VND` (ISO tiền tệ), `pnl`, `id`, `url`.

### 1a. Vai và Group (DB `auth_group`, đổi ở Lô 4, giữ id)
| Tiếng Việt | Group cũ | Group mới | Hằng BE (`apps/accounts/roles.py`) | Khoá FE (`ROLE.*` ở `erp-console/shared/lib/roles.ts`) |
|---|---|---|---|---|
| Chủ | `chu` | `owner` | `OWNER` | `ROLE.owner` |
| Quản lý | `quan_ly` | `manager` | `MANAGER` | `ROLE.manager` |
| NV kho | `nv_kho` | `warehouse_staff` | `WAREHOUSE_STAFF` | `ROLE.warehouseStaff` |
| NV giao | `nv_giao` | `delivery_staff` | `DELIVERY_STAFF` | `ROLE.deliveryStaff` |
| CSKH | `cskh` | `customer_service` | `CUSTOMER_SERVICE` | `ROLE.customerService` |

- Người giao trên **một phiếu** (không phải vai): `courier`. Hàm/biến theo vai: `is_owner`, `is_customer_service`,
  `owner_user`, `active_owner_ids`, `_escalate_to_owner`… (đã có sẵn `actor_is_owner`, gộp về một cách gọi).
- Nhãn hiển thị ("Chủ", "Quản lý", "Nhân viên kho", "Nhân viên giao", "CSKH") **giữ nguyên**.

### 1b. Cụm CSKH — vai đặt theo `customer_service`, việc gọi xác nhận đặt theo `confirmation`
| Tiếng Việt | Tên cũ | Tên mới | Lô |
|---|---|---|---|
| Module BE gọi xác nhận đơn | `apps/delivery/cskh/` | `apps/delivery/confirmation/` | 1 |
| Module FE ERP | `erp-console/features/cskh/` (`CskhQueueView`, `CskhCallModal`, `cskh.module.css`) | `features/confirmation/` (`ConfirmationQueueView`, `ConfirmationCallModal`, `confirmation.module.css`) | 1 |
| Class/type `Cskh*` BE | `CskhQueueViewSet`, `CskhSearchView`, `CskhQueuePagination`, `CskhQueueItemSerializer`, `CskhQueueDetailSerializer`, `CskhSearchThrottle` | `ConfirmationQueueViewSet`, `CustomerSearchView`, `ConfirmationQueuePagination`, `ConfirmationQueueItemSerializer`, `ConfirmationQueueDetailSerializer`, `CustomerSearchThrottle` | 1 |
| Hàm phạm vi | `is_cskh`, `cskh_q`, `cskh_note_q`, `note_in_cskh_scope` | `is_customer_service`, `customer_service_q`, `customer_service_note_q`, `note_in_customer_service_scope` | 1 |
| Alias import | `cskh_services` | `confirmation_services` | 1 |
| FE `Cskh*` | `fetchCskhQueue`, `claimCskhTask`, `searchCskh`, `CskhQueueItem`… | `fetchConfirmationQueue`, `claimConfirmationTask`, `searchCustomers`, `ConfirmationQueueItem`… | 1 |
| Khối Shop "Lưu ý xác nhận đơn" | file `CskhNotice.tsx` + `.module.css`, `CskhNotice`, `CskhNoticeConfig` | `ConfirmationPolicyNotice.tsx` + `.module.css`, `ConfirmationPolicyNotice`, `ConfirmationPolicyConfig`. `CallNoticeBox`, `callHours`, `DEFAULT_CALL_HOURS` **giữ** (đã tiếng Anh) | 1 |
| View key ERP | `"cskh"` (`ViewGuard`, `nav.ts`) | `"confirmation"` | 1 |
| `data-testid` | `cskh-notice`, `cskh-stale-alert` | `confirmation-policy-notice`, `confirmation-stale-alert` | 1 |
| Hằng trang chủ | `HOME_CSKH_QUEUE` (giá trị `"cskh-queue"`) | `HOME_CONFIRMATION_QUEUE` (giá trị đổi ở Lô 4: `"confirmation-queue"`) | 1 / 4 |
| Route API | `/api/cskh/queue/…`, `/api/cskh/search/` | `/api/confirmation/queue/…`, `/api/confirmation/search/` | 3 |
| Route ERP | `/cskh/` | `/confirmation/` | 3 |
| Khoá JSON `/api/dashboard/attention/` | `cskh_queue_waiting`, `cskh_escalated`, `cskh_auto_cancel_blocked` | `confirmation_queue_waiting`, `confirmation_escalated`, `confirmation_auto_cancel_blocked` | 3 |
| Khoá JSON công khai `/api/public/site-info/` | `cskh_notice` (object) | **`confirmation_policy`** — *sửa đề xuất `confirm_call_notice` ở 01 vì khoá này đã tồn tại (boolean GL-04)* | 3 |
| Env + settings | `CSKH_*` (11 biến), `THROTTLE_CSKH_SEARCH` | `CONFIRMATION_*` (vd `CONFIRMATION_MAX_UNREACHABLE_ATTEMPTS`), `THROTTLE_CUSTOMER_SEARCH` | 3 |
| Throttle scope | `cskh_search` | `customer_search` | 3 |
| Lệnh quản trị | `process_cskh_deadlines`, `check_cskh_job_health` | `process_confirmation_deadlines`, `check_confirmation_job_health` | 3 |
| Logger | `cangca.delivery.cskh` | `cangca.delivery.confirmation` | 3 |

### 1c. Nhập lô, AI, định dạng, test
| Tiếng Việt | Tên cũ | Tên mới | Lô |
|---|---|---|---|
| Nhập lô (form, serializer, type) | `NhapLoForm.tsx`, `NhapLoInput`, `NhapLoLine`, `NhapLoBatchOutput`, `NhapLo*` FE, `submitNhapLo`, state `nhap_lo_kg/vnd/daily` | `ReceiveBatchesForm.tsx`, `ReceiveBatchesInput`, `ReceiveBatchesLine`, `ReceivedBatchOutput`, `ReceiveBatches*`, `submitReceiveBatches`, `receive_kg/vnd/daily` | 1 |
| Tiền tố khoá nháp | `NHAP_LO_DRAFT_PREFIX = "cave_draft_nhap_lo"` | tên hằng `RECEIVE_BATCHES_DRAFT_PREFIX` (Lô 1); giá trị `"cave_draft_receive_batches"` + hằng `LEGACY_RECEIVE_BATCHES_DRAFT_PREFIX = "cave_draft_nhap_lo"` giữ **vĩnh viễn** (Lô 3) | 1 / 3 |
| Action nhập lô | `POST /api/purchasing/receipts/nhap-lo/`, method `nhap_lo` | `POST …/receive-batches/`, method `receive_batches` | 3 / 4 |
| Id lệnh AI | `purchasing.purchasereceipt.nhap_lo` | `purchasing.purchasereceipt.receive_batches` | 4 |
| Nhóm lệnh AI | `thu_mua`, `ban_hang`, `cskh` | `purchasing`, `sales`, `customer_service` | 4 |
| Mức nhạy cảm lệnh AI | `cao`, `trung_binh`, `thap` | `high`, `medium`, `low` | 4 |
| Keyword AI dạng snake không dấu | `tra_ton`, `nhap_lo`, `chot_lo`… | **xoá** (giữ bản có dấu `"tra tồn"`…) | 4 |
| Múi giờ VN (hai FE + adapter) | ERP `VN_TZ`, Shop `VN_TIME_ZONE`, adapter `VN_TZ` | **`VN_TIME_ZONE`** ở cả ba | 1 |
| Ngày hôm nay theo giờ VN | ERP `todayInVietnam`, Shop `todayVn`, e2e `vn_today()` | **`todayInVietnam()`** (TS), `today_in_vietnam()` (Python e2e) | 1 |
| Năm hiện tại theo giờ VN | Shop `currentYearVn` | `currentYearInVietnam()` | 1 |
| Khoá ngày theo giờ VN | ERP `dateKeyInVietnam` | giữ | — |
| Hàm định dạng tiền/giờ | Shop `formatVnd`/`formatDate…`, ERP `vnd`/`kg`/`dateTime…`, BE `format_vnd`/`format_local_date` | **giữ** (đã tiếng Anh; mỗi FE giữ quy ước riêng, không đổi hàng loạt) | — |
| Mock kho lạnh | `KHO_LANH` | `COLD_STORAGE_NAME` | 1 |
| Bản rà soát QA | `ra_soat_*`, `ra-soat-*` | `review_*` | đổi dần |
| Bổ sung | `bosung` | `extra` / `followup` | đổi dần |
| Tên file/hàm test | `test_p8_lo7_*`, `test_*_sai_mat_khau_*`, biến `self.chu`, `client_kho` | theo hành vi, tiếng Anh (`test_undo_window.py`, `self.owner`, `warehouse_client`) | **đổi dần** (Q3) |

Các mục khác (lô hàng `batch`, phiếu nhập `purchase_receipt`, NCC `supplier`, giá vốn `landed_unit_cost`/`view_costprice`,
lãi lỗ `pnl`/`profit`, bài viết/trang `post`/`page`…) giữ như glossary mục 2 của `01-ra-soat-dat-ten.md` (đã cập nhật dòng CSKH).

### 1d. Không đổi (chốt)
- **Migration đã chạy** (`accounts/0011_seed_group_cskh.py`, `delivery/0004_cskh_confirmation.py`, `0002_seed_permission_groups`…):
  không đổi tên file, không sửa nội dung. DB mới chạy chúng trước migration đổi tên nên kết quả cuối vẫn đúng.
- **`AuditLog.action` đã ghi** (`execute_purchasing.purchasereceipt.nhap_lo`…): append-only, không UPDATE.
- **Bản ghi phiên bản cấu hình AI cũ** (`AiConfigVersion`, `AiPolicyVersion` là append-only): không sửa dòng cũ, xem Lô 4.
- **URL công khai Shop** `/bai-viet/`, `/trang/`, `?chuyen-muc=`, và `bai-viet.module.css`/`trang.module.css` đi theo thư mục route.
- **Dữ liệu**: username demo (`kho1`, `giao1`, `chu_vua`, `demo_chu`…), mã hàng, slug, mật khẩu thử, placeholder `.env.example`,
  keyword AI có dấu, `utm_medium=bai_viet`.
- Permission codename, model, bảng, `TextChoices`: đã tiếng Anh, không đụng.
- Chuỗi `cangca` trong hạ tầng/logger.

---

## 2. Lô

| ☐/☑ | Lô | Việc | BE / FE | Ước lượng | Được sửa | Không được đụng | Commit |
|---|---|---|---|---|---|---|---|
| ☑ | 0 | Chặn tên tiếng Việt mới: script `check_naming` + baseline + luật trong skill | BE (1 người) | 0,5 ngày | `scripts/check_naming.py`, `scripts/naming_blocklist.txt`, `scripts/naming_baseline.json` (mới); `.claude/skills/{caveve-domain,django-drf-patterns,nextjs-shop-patterns,tdd-workflow,e2e-playwright}/SKILL.md` (chỉ thêm mục "Đặt tên"); `AGENTS.md` (chỉ thêm mục "Đặt tên"); `03-dev-notes.md` | mọi code sản phẩm, `doc/decisions.md`, migration | `3d30789` |
| ☐ | 1 | M1 nội bộ: dời module `cskh`→`confirmation`, đổi class/hàm/type, gom tên Group về **1 file hằng mỗi phía** (giá trị vẫn cũ), thống nhất tên múi giờ | BE ∥ FE | 1,5 ngày | xem §3 Lô 1 | route, khoá JSON, env, id lệnh AI, giá trị Group, snapshot chỉ mục AI, migration | — |
| ☐ | 3 | M2 contract có alias: route/khoá JSON/env/lệnh mới chạy song song tên cũ; FE dùng tên mới + lớp chuẩn hoá nhận cả giá trị Lô 4 | BE ∥ FE (1 commit) | 2 ngày + E2E staging | xem §3 Lô 3 | giá trị Group, id lệnh AI, nhóm/mức nhạy cảm AI, migration | — |
| ☐ | 4 | M3 dữ liệu: đổi 5 Group giữ id, migrate khoá AI (append phiên bản mới), đổi id/nhóm/mức lệnh AI; sửa `decisions.md` dòng tên Group | 4a BE → 4b FE (2 commit) | 2 ngày + nghiệm thu staging | xem §3 Lô 4 | `AuditLog`, dòng `AiConfigVersion`/`AiPolicyVersion` cũ, migration cũ, chứng từ | — |
| ☐ | 5 | Gỡ alias tạm (route `/api/cskh/`, `nhap-lo`, khoá JSON cũ, env `CSKH_*`, lệnh bọc, chuẩn hoá tên cũ FE) — **đề xuất, chờ Duy (🔴 Q-A)** | BE ∥ FE | 0,5 ngày | xem §3 Lô 5 | những thứ giữ vĩnh viễn ở §3 Lô 5 | — |

~~Lô 2 (đổi tên test hàng loạt)~~ — **bỏ** theo Q3: test tiếng Việt đổi dần (xem §5).
Tổng: khoảng 6–6,5 ngày công + 2 vòng nghiệm thu staging.

---

## 3. Chi tiết từng lô

### Lô 0 — Chặn phát sinh mới (rủi ro 0)
**Làm:**
1. `scripts/check_naming.py` (Python 3 stdlib, chạy từ gốc repo, không cần venv):
   - Quét file git-tracked trong `backend/ adapter/ frontend/ erp-console/` (bỏ `node_modules`, `.next`, `out`, `.venv`,
     `staticfiles`, `shots`, `**/migrations/**`).
   - Tách định danh: Python bằng `tokenize` (NAME + chuỗi literal dạng định danh, bỏ comment/docstring); TS/TSX bằng regex sau khi
     bỏ comment. Chuỗi literal chỉ xét khi **không có dấu và không có khoảng trắng** (vd `"chu"`, `"nhap-lo"`, `"cskh_notice"`), để
     chữ hiển thị `"Nhập lô"`, `"tra tồn"` không bị bắt. Với file test chỉ xét định danh + tên file (dữ liệu demo như `"kho1"` không bị bắt).
   - Tách từ theo `snake_case`/`camelCase`/`kebab-case`, đối chiếu `naming_blocklist.txt`: tối thiểu `cskh`, `nhap`, `kho`, `giao`,
     `chu`, cặp `quan+ly`, `nv`, cặp `thu+mua`, cặp `ban+hang`, `soat`, `bosung`, cặp `bo+sung`, `tien`, cặp `qua+han`, mẫu `lo\d+`,
     `l\d+` ở đầu tên file test, `qa-lo`. Có allowlist cho từ tiếng Anh trùng (`ton`, `don`, `hang`, `ban`, `chi`…) — tái dùng từ điển
     của bản rà soát 30/09, ghi nguồn trong đầu file.
   - Tên file cũng bị xét (vd `CskhNotice.tsx`, `test_p8_lo7_undo.py`).
   - Miễn vĩnh viễn (khai trong script, có comment lý do): migration; `frontend/app/bai-viet/`, `frontend/app/trang/`, tham số
     `chuyen-muc`; `apps/accounts/roles.py` khối `LEGACY_ROLE_NAMES`; `apps/ai/registry/legacy_ids.py`;
     `erp-console/shared/lib/roles.ts` + `features/ai/legacyIds.ts` khối tên cũ; hằng `LEGACY_RECEIVE_BATCHES_DRAFT_PREFIX`.
   - `naming_baseline.json` = `{file: số lần vi phạm}` chụp ở HEAD. **Fail** khi: file không có trong baseline có vi phạm; file trong
     baseline có số vi phạm **tăng**. `--update` chỉ cho phép **giảm** (từ chối ghi nếu có file tăng) — mỗi lô sau chạy `--update`
     để khoá thành quả. In ra file + dòng + token, exit 1.
2. Thêm mục "Đặt tên" (glossary §1 rút gọn + lệnh `python3 scripts/check_naming.py`) vào các skill ở cột "Được sửa" và `AGENTS.md`.
   `tdd-workflow`/`e2e-playwright`: tên test/script theo hành vi, tiếng Anh, bản rà soát QA dùng `review_*`, không mã lô trong tên.
3. Thêm `python3 scripts/check_naming.py` vào bộ lệnh kiểm chứng §4 (bắt buộc từ Lô 1 trở đi, và cho mọi hồ sơ sau P8b).

**Lệnh kiểm chứng:** `python3 scripts/check_naming.py` exit 0 ở HEAD; thử tạo file tạm `backend/apps/common/tests/test_lo9_thu.py`
có hàm `def kiem_tra_nhap_lo()` → exit 1 và in đúng file/token (dán output), rồi xoá file tạm. Bộ §4 không đổi số test.
**Điều kiện xong:** script chạy < 10 giây; baseline commit cùng lô; skill có mục "Đặt tên"; techlead review danh sách chặn/miễn.
**Điểm dừng hỏi Duy:** allowlist cần miễn một từ tiếng Việt mà code sản phẩm đang dùng làm định danh chính thức (không phải dữ liệu).

### Lô 1 — M1 nội bộ + 1 file hằng Group mỗi phía (rủi ro thấp, không đổi hành vi)
**BE (`be-dev`):**
- Tạo `backend/apps/accounts/roles.py` — **chỉ hằng, không import gì** (để `apps/common` import được mà không vòng):
  `OWNER = "chu"`, `MANAGER = "quan_ly"`, `WAREHOUSE_STAFF = "nv_kho"`, `DELIVERY_STAFF = "nv_giao"`, `CUSTOMER_SERVICE = "cskh"`,
  `ALL_ROLES` (đúng thứ tự `sorted_groups` hiện tại). Giá trị **vẫn là tên cũ** đến Lô 4.
- Thay mọi chuỗi tên Group trong code chạy thật (≈82 chỗ: `common/api.py` `FULL_SCOPE_GROUPS`, `accounts/auth/services.py`
  `GROUP_LABELS`/`sorted_groups`/home, `accounts/staff/services.py`, `sales/payments/auto_confirm.py`, `ai/actions/services.py`,
  `ai/management/commands/run_due_ai_actions.py`, `purchasing/receipts/services.py`, `delivery/cskh/scope.py`…) bằng hằng.
  Bỏ kiểu ghép chuỗi `"".join(["cs", "kh"])` (`ai/settings/services.py`, `ai/registry/discovery.py:61`).
- Thay chuỗi tên Group trong **test** (≈690 chỗ: `Group.objects.get(name="chu")`, `make_user(..., "nv_kho")`, assert `groups == [...]`)
  bằng hằng `roles.*`. Thay thế cơ học, không đổi tên biến/hàm test (đổi dần, §5). Mục đích: Lô 4 chỉ đổi giá trị 1 file.
- Hằng nhóm lệnh AI: tạo `backend/apps/ai/registry/command_groups.py` với `PURCHASING = "thu_mua"`, `SALES = "ban_hang"`,
  `CUSTOMER_SERVICE = "cskh"`; `SENSITIVITY_HIGH = "cao"`, `SENSITIVITY_MEDIUM = "trung_binh"`, `SENSITIVITY_LOW = "thap"`.
  Thay literal ở `discovery.py`, `spec.py`, `settings/services.py`, `policy/effective.py`, các `api.py` có `AiMeta(sensitivity=…)`.
- `git mv backend/apps/delivery/cskh backend/apps/delivery/confirmation`; sửa mọi import; đổi class/hàm §1b (cột Lô 1).
  Giữ nguyên `url_path`, `basename="cskh-queue"`, prefix route, tên settings `CSKH_*`, logger, lệnh quản trị (Lô 3).
- `purchasing/receipts`: đổi `NhapLoInput`→`ReceiveBatchesInput`, `NhapLoLine`→`ReceiveBatchesLine`,
  `NhapLoBatchOutput`→`ReceivedBatchOutput`. **Giữ** method `nhap_lo`, `url_path="nhap-lo"`, `custom_perm_actions` (id lệnh AI).
- Đổi `CHU`, `is_chu`, `active_chu_ids`, `_lock_target_and_chus`, `LAST_CHU_CODE`, `chu_user`, `_escalate_to_chu` theo §1a;
  gộp `is_chu` vào `actor_is_owner` nếu cùng nghĩa (đọc kỹ, không đổi hành vi).
- `HOME_CSKH_QUEUE` → `HOME_CONFIRMATION_QUEUE` (giá trị giữ `"cskh-queue"`).
- Test class/hàm hỗ trợ **tham chiếu tên code vừa đổi** (`CskhL3BaseTestCase` được 9 file import, `_create_order_with_cskh`,
  alias `cskh_services` trong test) đổi theo, vì đó là import chứ không phải tên test.
- `adapter/app/sepay.py`: `VN_TZ` → `VN_TIME_ZONE`.
- `backend/apps/delivery/README.md`, `backend/README.md` (bản đồ module): cập nhật đường dẫn module.

**FE (`fe-dev`):**
- Tạo `erp-console/shared/lib/roles.ts` — nơi **duy nhất** chứa chuỗi tên Group:
  `export const ROLE = { owner: "chu", manager: "quan_ly", warehouseStaff: "nv_kho", deliveryStaff: "nv_giao", customerService: "cskh" } as const;`
  `export type RoleCode = (typeof ROLE)[keyof typeof ROLE];`. `nav.ts` bỏ `GROUP`, import `ROLE`; `groups.ts` (nhãn/gợi ý) dùng `ROLE`;
  `features/auth/types.ts` `GroupCode = RoleCode`. Thay literal ở `content/edit/page.tsx:89-90`, `AiAssistantPanel.tsx:260`,
  `ai/policy/api.ts`, `ai/settings/api.ts`, mock và `*.test.ts`. `chuOnlyStep` → `ownerOnlyStep`.
- Hằng nhóm lệnh AI FE: `erp-console/features/ai/commandGroups.ts` (giá trị cũ), `AiCommandGroup` lấy kiểu từ đó; mức nhạy cảm tương tự.
- `git mv erp-console/features/cskh erp-console/features/confirmation`; đổi file/type/hàm §1b. Thư mục route
  `app/(console)/cskh/` **giữ** (Lô 3); `page.tsx` trong đó chỉ đổi import.
- View key `"cskh"` → `"confirmation"` (chỉ FE).
- `NhapLoForm.tsx` → `ReceiveBatchesForm.tsx`, type/hàm `NhapLo*` → `ReceiveBatches*`; `NHAP_LO_DRAFT_PREFIX` → `RECEIVE_BATCHES_DRAFT_PREFIX`
  (giá trị giữ `"cave_draft_nhap_lo"`); state `nhap_lo_*` → `receive_*` ở `AiPolicyScreen.tsx` (chỉ state nội bộ, key gửi BE không đổi).
- `KHO_LANH` → `COLD_STORAGE_NAME`.
- Múi giờ: ERP `VN_TZ` → `VN_TIME_ZONE`; Shop `todayVn` → `todayInVietnam`, `currentYearVn` → `currentYearInVietnam`;
  e2e `vn_today()` → `today_in_vietnam()`. Cập nhật `scripts/test-format.mjs`, `format.test.ts`, `noLocalTime.test.ts` theo tên mới.
- Shop: `git mv` `CskhNotice.tsx`/`.module.css` → `ConfirmationPolicyNotice.tsx`/`.module.css`; `CskhNotice` →
  `ConfirmationPolicyNotice`, `CskhNoticeConfig` → `ConfirmationPolicyConfig`; `ConfirmCallNotice.tsx`, `CheckoutScreen.tsx`,
  `PaymentPanel.tsx` sửa import. Khoá JSON `cskh_notice` **giữ** (Lô 3).
- `data-testid` `cskh-notice`, `cskh-stale-alert` → §1b, sửa e2e dùng chúng trong cùng commit.
- `erp-console/features/confirmation/README.md`, `erp-console/README.md`: cập nhật đường dẫn.

**Được sửa:** `backend/apps/**` (trừ `migrations/`, `models/`), `backend/config/api_urls.py` (chỉ đường import), `backend/README.md`,
`adapter/app/sepay.py`; `erp-console/features/**`, `erp-console/shared/**`, `erp-console/app/**` (chỉ import/view key),
`erp-console/e2e/**`; `frontend/features/site/**`, `frontend/features/checkout/**`, `frontend/app/shop/orders/OrderLookup.tsx`,
`frontend/lib/format.ts`, `frontend/lib/mock.ts`, `frontend/scripts/test-format.mjs`, `frontend/e2e/**`;
`scripts/naming_baseline.json` (`--update`, chỉ giảm); `03-dev-notes.md`.
**Không được đụng:** mọi `migrations/`, `models/`; `url_path`/prefix route/basename; khoá JSON trả ra; tên env/settings `CSKH_*`;
method `nhap_lo`; **`backend/apps/ai/registry/tests/snapshots/commands_index_snapshot.json`**; `FORBIDDEN_PREFIXES`;
giá trị chuỗi Group/nhóm AI/mức nhạy cảm; `doc/decisions.md`; `package.json`/lock.
**Lệnh kiểm chứng:** bộ §4, cộng:
- `git diff --exit-code HEAD~ -- backend/apps/ai/registry/tests/snapshots/` (snapshot chỉ mục AI **y hệt**; `test_discovery` xanh
  mà không regenerate — R8).
- `git grep -nE "delivery\.cskh|features/cskh|from \"\./CskhNotice\"" -- backend erp-console frontend` → rỗng.
- `git grep -nE "\"(chu|quan_ly|nv_kho|nv_giao|cskh)\"" -- backend/apps ':!**/migrations/**' ':!backend/apps/accounts/roles.py'` → rỗng
  (tương tự cho `erp-console` ngoài `shared/lib/roles.ts`).
**Điều kiện xong:** số test backend/vitest/test-format **bằng số gốc** (không thêm, không bớt, không skip); `makemigrations --check`
sạch; baseline naming giảm; QA chạy smoke E2E local 5 vai (menu đúng theo vai, hàng đợi gọi xác nhận mở được, form Nhập lô gửi
được, khối "Lưu ý xác nhận đơn" ở checkout hiện) — hành vi không đổi; techlead review diff.
**Điểm dừng hỏi Duy:** snapshot chỉ mục AI đổi dù chỉ 1 dòng (lệnh đổi nhóm do `_get_group` so chuỗi con tên module) → dừng, báo;
gộp `is_chu`/`actor_is_owner` phát hiện hai hàm **khác nghĩa** → giữ cả hai, ghi "Lệch thiết kế".

### Lô 3 — M2 contract có alias (BE ∥ FE, một commit; deploy BE trước, FE sau)
Nguyên tắc: BE **thêm** tên mới, **giữ** tên cũ chạy song song; không đổi giá trị nào mà FE cũ đang dựa vào. FE dùng tên mới và
cài sẵn lớp chuẩn hoá cho các giá trị sẽ đổi ở Lô 4. Snapshot chỉ mục AI vẫn **y hệt** (không thêm `ai=` ở alias).

**BE:**
- Route: đăng ký `ConfirmationQueueViewSet` ở `/api/confirmation/queue/` (basename `confirmation-queue`) **và** giữ `/api/cskh/queue/`
  (basename `cskh-queue-legacy`); `CustomerSearchView` ở `/api/confirmation/search/` và `/api/cskh/search/`. Cùng class, cùng
  permission, cùng throttle, cùng `NoStoreMixin` nếu có.
- **`FORBIDDEN_PREFIXES` thêm `"/api/confirmation/"`** trong cùng commit (`backend/apps/ai/policy/rules.py`). Giữ `"/api/cskh/"`
  vĩnh viễn (phòng thủ nhiều lớp). → R1.
- Receipts: thêm action `receive_batches` (`url_path="receive-batches"`, `detail=False`, POST, **không `ai=`**) và giữ `nhap_lo`
  (`nhap-lo`, **còn `ai=`**) — cả hai gọi chung một hàm nội bộ, cùng `require_perm`. **Thêm `"receive_batches"` vào
  `custom_perm_actions`.** → R10.
- Khoá JSON `attention`: trả cả `confirmation_*` và `cskh_*` (cùng giá trị, cùng điều kiện 403/ẩn theo quyền).
- Khoá JSON công khai `site-info`: trả cả `confirmation_policy` và `cskh_notice` (cùng object, chỉ field cấu hình, không PII).
- Settings: đổi tên thuộc tính settings sang `CONFIRMATION_*`/`THROTTLE_CUSTOMER_SEARCH`; đọc env bằng helper
  `_env_first("CONFIRMATION_X", "CSKH_X", default)` (tên mới trước, tên cũ sau). Test `override_settings(CSKH_…)` đổi theo.
  Throttle scope `cskh_search` → `customer_search`.
- Lệnh quản trị: tạo `process_confirmation_deadlines`, `check_confirmation_job_health` (nội dung chuyển từ lệnh cũ); file lệnh cũ
  chỉ còn `call_command` sang lệnh mới (giữ exit code). Logger → `cangca.delivery.confirmation`.
- `doc/ops/moi-truong.md`: bảng job đổi tên lệnh (ghi tên cũ vẫn chạy tới Lô 5), bảng env ghi `CONFIRMATION_*` (tên cũ còn đọc tới Lô 5).

**FE ERP:**
- `features/confirmation/api.ts` gọi `/api/confirmation/…`; `features/purchasing/api.ts` gọi `receive-batches`.
- Route: `app/(console)/confirmation/` (trang thật); `app/(console)/cskh/page.tsx` chỉ còn client redirect sang `/confirmation/`
  (giữ query string, không render dữ liệu). `nav.ts`, `AttentionBlock.tsx` trỏ `/confirmation/`.
- `AttentionBlock` đọc `confirmation_*`, thiếu thì đọc `cskh_*`.
- Khoá nháp: giá trị `RECEIVE_BATCHES_DRAFT_PREFIX = "cave_draft_receive_batches"` (sessionStorage, `:<userId>`);
  `LEGACY_RECEIVE_BATCHES_DRAFT_PREFIX = "cave_draft_nhap_lo"`. **`clearAllDrafts()` xoá mọi khoá bắt đầu bằng cả hai tiền tố,
  ở cả localStorage và sessionStorage, vĩnh viễn.** Khi mở form: nếu có nháp session cũ của đúng userId → chuyển sang khoá mới
  (bỏ mọi field giá, theo SR-07) rồi xoá khoá cũ; khoá localStorage cũ (có giá mua) → xoá, không chuyển. → R4.
- Lớp chuẩn hoá chuẩn bị Lô 4 (đặt ở ranh giới API, không rải trong component):
  - `shared/lib/roles.ts`: `LEGACY_ROLE_NAMES` (hai chiều cũ↔mới) + `normalizeRole(name)` trả **giá trị nội bộ hiện tại** của `ROLE`;
    áp cho `me.groups`, danh sách nhân viên, `AiAction.assignee_group` ngay khi parse JSON. `normalizeHome()` nhận cả
    `"cskh-queue"` và `"confirmation-queue"`.
  - `features/ai/legacyIds.ts`: map id lệnh `…nhap_lo` ↔ `…receive_batches`, nhóm AI (`thu_mua`↔`purchasing`…), mức nhạy cảm
    (`cao`↔`high`…) + hàm `normalizeCommandId/normalizeAiGroup/normalizeSensitivity`; `features/ai/commands/call.ts:17`,
    `AiPolicyScreen` (đọc trần), `ActionDetailModal` dùng hàm này.
  - Test vitest: với **cả** payload tên cũ và tên mới, menu theo vai, trang chủ, màn Cài đặt AI và Chính sách AI hiển thị giống nhau.
**FE Shop:** `site/types.ts` thêm `confirmation_policy`; mọi chỗ đọc dùng `info.confirmation_policy ?? info.cskh_notice`
(`callHours`, `ConfirmationPolicyNotice`). Mock trả khoá mới.

**Được sửa:** `backend/config/api_urls.py`, `backend/config/settings.py` (khối CSKH + throttle), `backend/apps/ai/policy/rules.py`
(**chỉ thêm 1 prefix**), `backend/apps/delivery/**`, `backend/apps/purchasing/receipts/**`, `backend/apps/content/site/**`,
`backend/apps/common/throttling.py`, test tương ứng; `erp-console/app/(console)/{confirmation,cskh}/`, `erp-console/features/**`,
`erp-console/shared/**`, `erp-console/e2e/**`; `frontend/features/site/**`, `frontend/lib/{api,mock}.ts` (nếu site-info đi qua đây),
`frontend/e2e/**`; `doc/ops/moi-truong.md` (2 bảng nêu trên); `scripts/naming_baseline.json` (giảm); `03-dev-notes.md`.
**Không được đụng:** giá trị `roles.py`/`ROLE`, `command_groups.py`/`commandGroups.ts`, id lệnh AI (method `nhap_lo` vẫn giữ `ai=`),
snapshot chỉ mục AI, `migrations/`, `models/`, `AuditLog`, `doc/decisions.md`, `package.json`/lock.
**Test bắt buộc (mới, tên tiếng Anh):**
- `ai/registry/tests/test_forbidden_prefixes.py`: quét registry thật — không spec nào có path bắt đầu bằng `/api/cskh/` **hoặc**
  `/api/confirmation/`; test phải chứng minh đã quét > 0 spec. Và assert `"/api/confirmation/"` có trong `FORBIDDEN_PREFIXES`.
- Hai route queue/search: ma trận vai (`owner`, `manager`, `warehouse_staff`, `delivery_staff`, `customer_service`, ẩn danh 401) cho
  **cả hai prefix**, kết quả giống hệt nhau; throttle chung một bộ đếm.
- `receive-batches` và `nhap-lo`: happy path (owner/manager/warehouse_staff tuỳ quyền hiện có), **403 với `delivery_staff` và
  `customer_service` ở cả hai path**, 401 ẩn danh; dữ liệu không đổi khi 403.
- `site-info` (AllowAny): `confirmation_policy == cskh_notice`; quét JSON không có tên/SĐT/địa chỉ (sentinel PII giả).
- `attention`: khoá mới = khoá cũ; vai thiếu quyền vẫn không thấy.
- Env: `CONFIRMATION_X` thắng `CSKH_X`; chỉ có `CSKH_X` vẫn đọc được.
- Lệnh cũ và lệnh mới chạy 2 lần liên tiếp cho cùng kết quả (idempotent), exit code giống nhau.
- vitest `drafts`/`draftStorage`: đặt khoá `cave_draft_nhap_lo` (local, có `rate`) và `cave_draft_nhap_lo:7` (session) →
  `clearAllDrafts()` xoá hết; mở form chuyển nháp session cũ không mang giá.
**Lệnh kiểm chứng:** bộ §4, cộng `git diff --exit-code HEAD~ -- backend/apps/ai/registry/tests/snapshots/` (y hệt).
**E2E (QA, chạy thật trên local rồi staging):** 5 vai đăng nhập; hàng đợi gọi xác nhận qua `/confirmation/` và bookmark `/cskh/`
chuyển hướng đúng; Nhập lô gửi qua `receive-batches`; nháp cũ bị xoá khi đăng xuất (sửa `sr07_*` thành `sr07_receive_batches_draft.py`);
checkout Shop hiện khối lưu ý; **ca ngoài đường thuận**: FE bản cũ (build trước Lô 3) + BE Lô 3 vẫn chạy (không 404, không mất khối).
**Thứ tự deploy (mỗi bước cần Duy cho phép deploy):** BE Lô 3 → staging, E2E với FE cũ → FE Lô 3 (ERP + Shop) → staging, E2E 5 vai.
Trước khi deploy BE: điều phối viên kiểm env `CSKH_*` và args của Cloud Run Job `process_cskh_deadlines`/`check_cskh_job_health`
(nếu đã tạo) trên staging, ghi vào `03-dev-notes.md` (chỉ tên biến, không ghi giá trị secret).
**Điểm dừng hỏi Duy:** test quét thấy spec AI nào có path chứa dữ liệu khách ngoài 2 prefix trên → dừng; alias route làm registry sinh
**thêm** lệnh AI (snapshot đổi) → dừng; Cloud Run staging/production đang đặt env `CSKH_*` giá trị khác mặc định → báo trước khi deploy.

### Lô 4 — M3 dữ liệu và quyền (4a BE → 4b FE; nghiệm thu staging)
**4a BE (`be-dev`):**
- Migration `backend/apps/accounts/migrations/0012_rename_groups_to_english.py` (RunPython, `atomic`):
  - Với từng cặp (`chu`→`owner`, `quan_ly`→`manager`, `nv_kho`→`warehouse_staff`, `nv_giao`→`delivery_staff`, `cskh`→`customer_service`):
    `Group.objects.filter(name=old).update(name=new)` — **giữ id**, nên `group.permissions` và `user.groups` không đổi. **Không**
    xoá rồi tạo lại Group.
  - Chỉ có tên mới → bỏ qua (idempotent). Có **cả hai** tên → `raise` (dừng migrate, không đoán). Không có cả hai → bỏ qua.
  - Reverse đổi ngược lại. Migration **không đọc/không in** dữ liệu người dùng; chỉ in số Group đã đổi.
- Migration `backend/apps/ai/migrations/0003_rename_ai_keys_to_english.py` (phụ thuộc `accounts.0012`):
  - `AiAction.assignee_group`: tên Group cũ → mới (mọi dòng). `AiAction.command`: `…nhap_lo` → `…receive_batches` (mọi dòng;
    việc chờ/hẹn giờ phải tra được spec mới). Không đụng `AuditLog`.
  - `AiConfigVersion`, `AiPolicyVersion` là **append-only** → **không UPDATE dòng cũ**. Với mỗi user có phiên bản mới nhất chứa
    khoá cũ (`group_levels` có `thu_mua/ban_hang/cskh`; `overrides`/`limits` có id `…nhap_lo`) → **thêm 1 phiên bản mới** = bản sao
    với khoá đổi tên, giá trị giữ nguyên, `created_by` = `created_by` của bản mới nhất, `note="P8b: đổi khoá sang tiếng Anh, giá trị giữ nguyên"`.
    Tương tự 1 `AiPolicyVersion` mới cho `caps`/`red_zone_open`. Không có khoá cũ → không tạo gì (idempotent).
  - `backend/apps/ai/registry/legacy_ids.py`: map id/nhóm cũ → mới, dùng trong `policy/effective.py` **chỉ khi** đọc một phiên bản
    được ghim (`config_version`/`policy_version` truyền vào) có khoá cũ — để việc AI tạo trước migration không bị nới trần (R5/R6).
    Map này giữ vĩnh viễn (lịch sử append-only còn khoá cũ).
- Đổi giá trị `roles.py` sang tên mới; thêm `LEGACY_ROLE_NAMES = {"chu": OWNER, …}` và dùng ở **đầu vào** API nhận tên Group
  (tạo/sửa nhân viên ở `/api/staff/` (field `groups`), tham số lọc theo Group nếu có) để FE cũ còn trong cache gửi tên cũ vẫn đúng. Đầu ra luôn tên mới.
- Đổi giá trị `command_groups.py` (`purchasing`/`sales`/`customer_service`, `high`/`medium`/`low`); xoá keyword snake không dấu.
- Receipts: method `receive_batches` nhận `ai=AiMeta(…)` (id mới `purchasing.purchasereceipt.receive_batches`, path `receive-batches`);
  `nhap_lo` còn là alias **không `ai=`** (tới Lô 5). `custom_perm_actions` giữ cả hai.
- `HOME_CONFIRMATION_QUEUE = "confirmation-queue"`.
- Regenerate `commands_index_snapshot.json`. **Diff chỉ được phép:** id + path lệnh nhập lô, giá trị `group`, giá trị `sensitivity`,
  keyword snake bị xoá. Techlead đọc diff từng dòng.
- Test mới (tên tiếng Anh): `accounts/staff/tests/test_group_rename_migration.py` (dùng `MigrationExecutor` từ `0011` → `0012`: id Group,
  tập permission từng Group, thành viên từng user giống hệt trước/sau; chạy 2 lần; reverse; trường hợp có cả hai tên → lỗi);
  `ai/policy/tests/test_ai_key_migration.py` (trước/sau: `effective_level` và trần kg/VND/lần/ngày của lệnh nhập lô **bằng nhau** cho user
  có override; phiên bản cũ không bị sửa; `run_due_ai_actions` chạy được việc tạo bằng id cũ; `assignee_group` giao đúng người).
  Toàn bộ test chống rò giá vốn (`test_permissions_matrix`, `test_dashboard_cost_leak`, `test_l3_cost_redaction`, `batches/tests/test_api.py`)
  và phạm vi `delivery_staff` phải xanh không sửa assert (fixture đã dùng hằng từ Lô 1).
- Lệnh xem trước chỉ đọc `backend/apps/accounts/management/commands/preview_group_rename.py`: in số Group theo tên cũ/mới, số
  `AiAction` cần đổi, số user có cấu hình AI chứa khoá cũ. **Không in username, tên, SĐT.**
- Tài liệu (Duy đã cho phép sửa `decisions.md` dòng liên quan): `doc/decisions.md` dòng 123 và 149 — **chỉ đổi mã định danh** Group,
  thêm ghi chú cuối dòng "(mã đổi sang tiếng Anh ngày …, P8b; nội dung quyết định giữ nguyên)"; `doc/business-process-spec.md` §1.5
  (bảng Group); `.claude/skills/caveve-domain/SKILL.md` (bất biến 2, 9), `.claude/skills/django-drf-patterns/SKILL.md` (mẫu test),
  `AGENTS.md`, `.claude/agents/*.md` và `CLAUDE.md` nếu có nhắc mã Group. **Không** sửa hồ sơ tính năng cũ trong `doc/features/*`
  (lịch sử). `doc/ops/moi-truong.md`: ghi tên Group mới ở dòng tài khoản thử (username demo giữ).

**4b FE (`fe-dev`):** đổi giá trị `ROLE` và `commandGroups.ts`/mức nhạy cảm sang tên mới; `normalizeRole`/`normalizeAiGroup`/
`normalizeSensitivity`/`normalizeCommandId` giờ map **cũ → mới** (giữ tới Lô 5); mock + vitest + e2e Python (tên Group literal trong
`erp-console/e2e/*.py`, `frontend/e2e/*.py`) sang tên mới.

**Được sửa:** 4a — `backend/apps/accounts/{roles.py,migrations/0012_*,management/commands/preview_group_rename.py,staff/tests/}`,
`backend/apps/ai/{migrations/0003_*,registry/,policy/effective.py,policy/tests/}`, `backend/apps/purchasing/receipts/api.py`,
`backend/apps/accounts/auth/services.py`, `backend/apps/accounts/staff/**` (chỉ chuẩn hoá đầu vào), `backend/apps/**/api.py`
(chỉ `AiMeta` keyword/sensitivity), snapshot, và 7 file tài liệu nêu trên. 4b — `erp-console/shared/lib/roles.ts`,
`erp-console/features/**`, `erp-console/e2e/**`, `frontend/e2e/**`. Cả hai: `scripts/naming_baseline.json` (giảm), `03-dev-notes.md`.
**Không được đụng:** migration cũ; bảng `AuditLog`, `StockLedgerEntry`, `*LineBatch`, chứng từ; dòng `AiConfigVersion`/`AiPolicyVersion`
đã có; permission codename; nội dung (không phải mã) của `doc/decisions.md`; `FORBIDDEN_PREFIXES` (chỉ được thêm, không bớt).
**Lệnh kiểm chứng:** bộ §4, cộng: `manage.py migrate` trên DB test sạch từ đầu; `manage.py migrate accounts 0011 && manage.py migrate`
(reverse rồi tiến lại) trên DB test; `manage.py preview_group_rename` trước/sau (dán output); đọc lại 2 file migration.
**Thứ tự deploy (mỗi bước cần Duy cho phép; staging trước):**
1. Điều kiện: FE Lô 3 (có lớp chuẩn hoá) **đã chạy trên staging**.
2. Chạy `preview_group_rename` trên staging qua job `cangca-migrate-staging` (`--args`), dán số liệu.
3. Deploy BE 4a lên staging + chạy migrate bằng `cangca-migrate-staging`. E2E 5 vai với **FE Lô 3** (tên Group mới đi qua `normalizeRole`):
   menu, trang chủ, sửa nhóm nhân viên, hàng đợi gọi xác nhận, Nhập lô, màn Cài đặt AI/Chính sách AI hiển thị đúng trần cũ.
4. Deploy FE 4b lên staging, E2E 5 vai lại.
5. Duy duyệt → production (đang tắt, chưa có P1–P8) đi **một lượt**: BE (mọi migration P1–P8b) → migrate `cangca-migrate` → FE.
   Nếu production được bật lại trước khi làm Lô 4 thì làm lại đúng thứ tự 1–4 trên production.
**Điểm dừng hỏi Duy:** `preview_group_rename` thấy DB có sẵn Group tên mới, thiếu Group cũ, hoặc Group lạ ngoài 5 tên → dừng;
diff snapshot AI có thay đổi ngoài 4 loại được phép → dừng; có tài liệu/kịch bản gửi Lộc hoặc tài khoản ngoài hệ thống nhắc mã Group →
báo trước khi deploy; bất kỳ test chống rò giá vốn/PII nào phải sửa assert → dừng.

### Lô 5 — Gỡ alias tạm (đề xuất, 🔴 Q-A)
Làm sau khi FE 4b đã chạy trên staging và E2E xanh (production đang tắt nên không cần chờ thêm):
gỡ route `/api/cskh/*`, action `nhap-lo`, khoá JSON `cskh_*` ở attention và `cskh_notice` ở site-info, đọc env `CSKH_*`, 2 file lệnh bọc,
`LEGACY_ROLE_NAMES` ở đầu vào BE, nhánh tên cũ trong `normalize*` FE, trang redirect `/cskh/`; FE Shop bỏ fallback `cskh_notice`.
**Giữ vĩnh viễn:** `"/api/cskh/"` trong `FORBIDDEN_PREFIXES`; `LEGACY_RECEIVE_BATCHES_DRAFT_PREFIX` trong `clearAllDrafts()`;
`ai/registry/legacy_ids.py` (phiên bản AI cũ được ghim); migration. Test: route cũ trả 404, test chống rò vẫn xanh, `check_naming`
baseline về gần 0 cho code chạy thật (chỉ còn test đổi dần). Điều kiện: production chưa từng chạy bản có tên cũ **hoặc** đã qua một bản
phát hành có alias.

---

## 4. Bộ lệnh kiểm chứng (mọi lô; dán output tóm tắt vào `03-dev-notes.md`, chạy trong đúng lượt báo xong)
```bash
python3 scripts/check_naming.py
cd backend && .venv/bin/python manage.py test && .venv/bin/python manage.py makemigrations --check --dry-run
cd adapter && .venv/bin/python -m pytest -q
cd erp-console && rm -rf node_modules && npm ci && npx tsc --noEmit && npm test && npm run build \
  && node scripts/check-no-mock.mjs && node scripts/check-ai-chunks.mjs
cd frontend && rm -rf node_modules && npm ci && npx tsc --noEmit && npm run build \
  && node scripts/test-format.mjs && node scripts/test-safe-href.mjs && node scripts/check-no-mock.mjs
```
- Dùng `git mv` để giữ lịch sử. Mỗi lô **chỉ đổi tên, không đổi hành vi** (trừ alias/migration ghi rõ ở lô đó).
- Số test: Lô 0–1 bằng số gốc; Lô 3–5 = số gốc + test mới liệt kê trong lô (liệt kê tên trong `03-dev-notes.md`). Không test nào bị
  xoá, skip hay sửa assert, trừ assert **tên** (route/khoá/Group) đúng với lô.
- QA theo luật đã siết: không PASS bằng đọc code; AC FE có Playwright/ảnh chụp dữ liệu giả; mỗi lô có ca ngoài đường thuận (FE cũ + BE mới,
  chạy lệnh/migration 2 lần, dữ liệu tạo trước khi đổi tên). Test quét PII/giá vốn phải đếm được response 200 > 0.
- APPROVED → commit tiếng Việt có mã lô (vd `P8b Lô 1: dời module cskh→confirmation, gom tên Group về roles.py/roles.ts, thống nhất VN_TIME_ZONE`)
  → `git push origin main` → đánh ☑ + mã commit ở bảng §2 và `doc/ke-hoach-tong.md`.

## 5. Test tiếng Việt — đổi dần (Q3)
- Test/script **mới** (kể cả trong P8b) đặt tên tiếng Anh theo hành vi; bản rà soát QA mới dùng `review_*`. `check_naming` chặn.
- Khi một file test được sửa **vì hành vi** (tính năng/sửa lỗi từ P9 trở đi): đổi tên file (nếu mang mã lô/tiếng Việt), tên hàm `test_*`,
  biến theo vai (`self.chu` → `self.owner`, `client_kho` → `warehouse_client`) **của file đó**, cùng commit, và chạy lại baseline `--update`.
- Sửa **cơ học** trong P8b (đổi import, thay literal Group bằng hằng) **không** kéo theo dịch tên test — giữ diff đọc được.
- Hồ sơ QA cũ trích tên test cũ: không sửa; `git log --follow` tra được.
- Nợ còn lại tại HEAD (tham khảo, không làm trong P8b): 959/1.615 hàm test, ≈3.000 biến theo vai, ≈80 file test/e2e mang mã lô hoặc
  tiếng Việt (gồm 50 file thêm ở P8: `test_p8_lo7_*`, `test_p8_lo8_*`, `test_qa_lo4_tien.py`, `p8_lo5_fe_lo_qua_han.py`, `qa-lo7-*`, `qa-lo8-*`…).

## 6. Rủi ro và cơ chế chặn

| # | Mức | Rủi ro | Cơ chế chặn | Test/kiểm bắt lỗi | Lô |
|---|---|---|---|---|---|
| R1 | **Critical** | Route `/api/confirmation/` có tên/SĐT khách lọt vào chỉ mục lệnh AI (bất biến 9) | Thêm `"/api/confirmation/"` vào `FORBIDDEN_PREFIXES` **cùng commit** với route; không bao giờ bỏ `"/api/cskh/"` | `test_forbidden_prefixes.py` quét registry thật cả 2 prefix, đếm spec > 0; snapshot chỉ mục AI không đổi ở Lô 3 | 3 |
| R2 | **Critical** | Đổi tên Group làm mất quyền hoặc leo quyền | `update(name=…)` giữ id; không xoá/tạo lại; có cả hai tên → dừng | `test_group_rename_migration.py`: id, permission, thành viên giống hệt; `preview_group_rename` trên staging | 4 |
| R3 | **Critical** | Lộ giá vốn/PII vì `FULL_SCOPE_GROUPS`/`is_owner`/phạm vi `delivery_staff` so theo tên | Tên Group chỉ ở `roles.py`/`roles.ts` từ Lô 1; test dùng hằng | Test chống rò giá vốn + ma trận vai + phạm vi `delivery_staff` xanh **không sửa assert** ở Lô 1 và Lô 4 | 1, 4 |
| R4 | **Critical** | Nháp "Nhập lô" cũ có giá mua còn trong trình duyệt sau khi đổi khoá (SR-07, bất biến 1) | `clearAllDrafts()` xoá **vĩnh viễn** cả tiền tố cũ `cave_draft_nhap_lo` ở local + session; chuyển nháp không mang giá | vitest `drafts`/`draftStorage` + e2e `sr07_receive_batches_draft.py` ca "khoá cũ bị xoá khi đăng xuất" | 3 (giữ ở 5) |
| R5 | High | Trần/cấu hình AI mất hiệu lực khi đổi khoá → nới an toàn không ai biết | Append phiên bản mới có khoá mới trong cùng deploy; `legacy_ids.py` cho phiên bản ghim | `test_ai_key_migration.py`: `effective_level` và trần trước = sau | 4 |
| R6 | High | Việc AI đang chờ/hẹn giờ trỏ id cũ bị lỗi hoặc giao sai nhóm | Migrate `AiAction.command` + `assignee_group` | Test `run_due_ai_actions` với việc tạo bằng id cũ trước migration | 4 |
| R7 | High | FE/BE lệch trong khoảng giữa hai lần deploy (static export) | Lô 3: BE thêm, không bớt; FE Lô 3 cài chuẩn hoá trước; Lô 4: BE nhận tên cũ ở đầu vào | E2E staging 5 vai **sau từng bước deploy**, gồm FE cũ + BE mới | 3, 4 |
| R8 | High | Đổi tên module làm lệnh AI đổi nhóm (`_get_group` so chuỗi con tên module) | Snapshot chỉ mục AI không được đổi ở Lô 1, 3; Lô 4 chỉ đổi 4 loại được phép | `test_discovery` với snapshot không regenerate; `git diff --exit-code` thư mục snapshot | 1, 3, 4 |
| R9 | High | Đụng chứng từ / sửa lịch sử append-only | Chỉ UPDATE tên Group và `AiAction`; append (không sửa) phiên bản AI; không đụng `AuditLog.action` cũ | Techlead đọc 2 file migration; test phiên bản AI cũ không đổi | 4 |
| R10 | High | Action mới `receive_batches` quên `custom_perm_actions` → rơi về quyền model mặc định (leo quyền) | Thêm vào `custom_perm_actions` cùng commit, cùng `require_perm` | 403 với `delivery_staff`/`customer_service` ở **cả hai** path | 3 |
| R11 | Medium | Env `CSKH_*` đang đặt trên Cloud Run bị bỏ qua sau khi đổi tên | Đọc tên mới trước, tên cũ sau tới Lô 5; kiểm Cloud Run trước deploy | Test `_env_first`; ghi kết quả kiểm env vào `03-dev-notes.md` | 3 |
| R12 | Medium | Đổi migration đã chạy làm lệch `django_migrations` staging/prod | Cấm sửa `migrations/` cũ ở mọi lô | `makemigrations --check`; `git diff --stat` không có migration cũ | mọi lô |
| R13 | Medium | URL công khai Shop đổi làm gãy link/QR đã phát | `/bai-viet/`, `/trang/`, `?chuyen-muc=` nằm trong danh sách miễn của `check_naming` | Review diff `frontend/app/` | mọi lô |

## 7. Câu hỏi cho Duy
- 🔴 **Q-A. Làm Lô 5 (gỡ alias) ngay trong P8b, trước P9?** Tech Lead đề xuất **có**: production đang tắt và chưa từng chạy P1–P8, nên
  alias chỉ cần sống qua các lần deploy staging; gỡ sớm để P9 viết trên code sạch. Nếu Duy muốn bật production trước khi xong P8b thì
  Lô 5 phải chờ production chạy một bản có alias.
- 🔴 **Q-B. Tên theo vai và theo việc.** Q1 chốt vai CSKH là `customer_service` (Group, nhóm lệnh AI, hàm `is_customer_service`).
  Tech Lead giữ tên **theo việc** cho module/route/env gọi xác nhận đơn: `confirmation` (`/api/confirmation/…`, `CONFIRMATION_*`,
  `features/confirmation/`), vì model và quyền đã là `ConfirmationTask`, `confirm_with_customer`. Duy đồng ý, hay muốn mọi chỗ "CSKH" đều
  là `customer_service` (vd `/api/customer-service/queue/`, `CUSTOMER_SERVICE_*`)? Chi phí hai cách như nhau; cần chốt trước Lô 1.
- 🔴 **Q-C. Có tài liệu/kịch bản ngoài repo nhắc mã Group** (hướng dẫn gửi Lộc, ghi chú tài khoản)? Nếu có, cần báo trước Lô 4.
  Nhãn hiển thị ("Chủ", "Quản lý"…) và username demo không đổi.

## 7b. Trả lời của Duy (01/10)
- **Q-A:** gỡ alias luôn trong P8b (**làm Lô 5**).
- **Q-B:** việc gọi xác nhận đơn (module, route, env) = **`confirmation`**; vai/Group CSKH = `customer_service`.
- **Q-C:** ngoài repo **không có** tài liệu/script nhắc mã Group.
- Duyệt phiếu, đội Claude làm Lô 0 → 1 → 3 → 4 → 5 (Lô 3/4 deploy **staging** để E2E; production không đụng).

## Điểm dừng chung
- Contract/thiết kế không khớp code → ghi "Lệch thiết kế" trong `03-dev-notes.md`, dừng lô, báo Tech Lead.
- Bất kỳ việc nào đụng tiền, giá vốn, phân quyền, dữ liệu cá nhân ngoài phạm vi đổi tên.
- Mọi bước deploy staging/production: chỉ khi Duy cho phép (CLAUDE.md).
