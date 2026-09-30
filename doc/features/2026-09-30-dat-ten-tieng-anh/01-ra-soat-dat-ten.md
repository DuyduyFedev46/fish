# Rà soát đặt tên tiếng Anh trong code (2026-09-30)

Người làm: Tech Lead. Ngày làm: 30/09/2026, lúc P8 Lô 7 đang code dở. Đây là bản chỉ đọc, chưa sửa dòng code nào.
Yêu cầu của Duy: mọi định danh trong code phải là **tiếng Anh chuẩn, dễ hiểu**, không viết tắt tiếng Việt. Định danh gồm hàm,
biến, class, module, thư mục, file, test, script, route API, khoá JSON, tên Group, codename quyền, tên bảng và model.
Những thứ vẫn giữ tiếng Việt và **không bị tính là lỗi**: chữ hiển thị cho người dùng, comment, docstring, tài liệu.

Phạm vi quét gồm `backend/`, `adapter/`, `frontend/` và `erp-console/`. Đã bỏ qua `node_modules`, `.next`, `out`, `.venv`,
`staticfiles` và `shots`. Migration cũ chỉ được ghi nhận, không đề xuất sửa.
Cách quét: tách định danh Python bằng `tokenize` (bỏ comment và docstring), tách định danh TS/TSX bằng regex (bỏ comment),
rồi tách từ theo `snake_case`, `camelCase` và `kebab-case`, đối chiếu với từ điển token tiếng Việt không dấu. Số liệu là số lần
xuất hiện đếm bằng script ở thời điểm quét. Vì cây làm việc đang có thay đổi chưa commit của Lô 7, sai số khoảng ±5%.

---

## 0. Kết quả chính

- **Model, bảng DB, codename permission và giá trị `choices`: không có chỗ nào tiếng Việt.** Cả 46 model đều tên tiếng Anh,
  không model nào có `db_table` riêng. Các quyền Tầng 2 (`view_costprice`, `close_batch`, `confirm_with_customer`…) và toàn bộ
  `TextChoices` đều là tiếng Anh. Vì vậy phần đắt nhất (đổi tên bảng) **không phải làm**.
- Nợ đặt tên dồn vào 4 cụm sau:
  1. **Tên 5 Group**: `chu`, `quan_ly`, `nv_kho`, `nv_giao`, `cskh`. Tên Group nằm trong DB, contract `/api/auth/me/` và cả
     `doc/decisions.md`.
  2. **Cụm "CSKH"**: module BE `apps/delivery/cskh/`, module FE `features/cskh/`, route `/api/cskh/*`, 11 biến env `CSKH_*`,
     khoá JSON `cskh_*` và các class `Cskh*`.
  3. **Cụm "Nhập lô"**: action `nhap-lo`, id lệnh AI `purchasing.purchasereceipt.nhap_lo`, khoá nháp `cave_draft_nhap_lo` và
     các tên `NhapLo*`.
  4. **Test**: 959 trên 1.615 hàm `test_*` Python có tên tiếng Việt không dấu, khoảng 3.000 lần dùng biến test tiếng Việt
     (`client_kho`, `self.chu`, `ql`…), và 48 file test/e2e tên tiếng Việt (`ra_soat_*`, `p8_lo7_*`…).
- Hai dữ liệu phụ có lưu trong DB: nhóm lệnh AI `thu_mua`, `ban_hang`, `cskh` (lưu làm khoá JSON trong `AiConfigVersion`) và
  giá trị `AiAction.assignee_group` (lưu tên Group).
- **Nợ vẫn đang tăng.** Lô 7 vừa tạo thêm `frontend/features/site/components/CskhNotice.tsx` và `.module.css` (file chưa
  track). Vì vậy việc đầu tiên là **chốt quy ước và chặn phát sinh mới** (Lô 0 ở mục 3).

---

## 1. Bảng rà soát theo mức rủi ro

Quy ước cột "Số chỗ": `prod a/b` nghĩa là a lần xuất hiện trong b file code chạy thật. `test` là file test, e2e và mock-test.
`mig` là migration cũ, chỉ ghi nhận. Tên đề xuất lấy theo glossary ở mục 2.

### M1 — Nội bộ (đổi an toàn, chỉ cần test xanh và build sạch)

#### M1-a. Module, thư mục và file code chạy thật

| Hiện tại | Đề xuất | Số chỗ | Ghi chú |
|---|---|---|---|
| `backend/apps/delivery/cskh/` (5 file: `api.py`, `scope.py`, `serializers.py`, `services.py`, `__init__.py`) | `backend/apps/delivery/confirmation/` | import `delivery.cskh`: prod 11/9f, test 11/10f | Module này **không chứa model** nên chuyển thư mục không sinh migration. Tên theo việc nó làm (`ConfirmationTask`, quyền `confirm_with_customer`) |
| `erp-console/features/cskh/` (7 file: `api.ts`, `mock.ts`, `types.ts`, `CskhCallModal.tsx`, `CskhQueueView.tsx`, `cskh.module.css`, `cskh.test.ts`) | `erp-console/features/confirmation/` (`ConfirmationCallModal.tsx`, `ConfirmationQueueView.tsx`, `confirmation.module.css`…) | cùng dòng trên | Thư mục route `app/(console)/cskh/` là **M2** vì URL đổi |
| `erp-console/features/purchasing/components/NhapLoForm.tsx` | `ReceiveBatchesForm.tsx` | 1 file, 4 import | |
| `frontend/features/site/components/CskhNotice.tsx` + `CskhNotice.module.css` (mới, Lô 7) | Gộp vào `ConfirmCallNotice.tsx` hoặc đổi thành `ConfirmCallHours.tsx` | 2 file, 3 import | Đã có `ConfirmCallNotice.tsx` import `CallNoticeBox` từ `CskhNotice`, nên gộp là hợp lý nhất |
| `frontend/app/bai-viet/bai-viet.module.css`, `frontend/app/trang/trang.module.css` | Giữ tên theo thư mục route | 2 file | Đi theo URL công khai, xem mục 3.3 (không đổi) |

#### M1-b. Class, hàm, hằng và biến trong code chạy thật

| Hiện tại | Đề xuất | Số chỗ (prod) | File tiêu biểu |
|---|---|---|---|
| `CskhQueueViewSet`, `CskhSearchView`, `CskhQueuePagination` | `ConfirmationQueueViewSet`, `CustomerSearchView`, `ConfirmationQueuePagination` | 7 / 2f | `delivery/cskh/api.py`, `config/api_urls.py` |
| `CskhQueueItemSerializer`, `CskhQueueDetailSerializer` | `ConfirmationQueueItemSerializer`, `ConfirmationQueueDetailSerializer` | 7 / 2f | `delivery/cskh/serializers.py` |
| `CskhSearchThrottle` | `CustomerSearchThrottle` | 3 / 2f | `common/throttling.py` |
| `is_cskh`, `cskh_note_q`, `note_in_cskh_scope`, `cskh_q` | `is_customer_care`, `customer_care_note_q`, `note_in_customer_care_scope`, `customer_care_q` | 20 / 4f | `delivery/cskh/scope.py`, `sales/orders/scope.py` |
| alias import `cskh_services` | `confirmation_services` | 13 prod / 100 test | `sales/orders/services.py`, test CSKH |
| `CHU`, `is_chu`, `active_chu_ids`, `_lock_target_and_chus`, `LAST_CHU_CODE`, `chu_user`, `_escalate_to_chu` | `OWNER_GROUP`, `is_owner`, `active_owner_ids`, `_lock_target_and_owners`, `LAST_OWNER_CODE`, `owner_user`, `_escalate_to_owner` | khoảng 35 / 3f | `accounts/staff/services.py` (đã có sẵn `actor_is_owner`, nên hiện tồn tại song song 2 cách gọi), `sales/payments/auto_confirm.py` |
| `GROUP_CSKH = "".join(["cs", "kh"])` | `CUSTOMER_CARE_GROUP` lấy từ module hằng Role (mục 3, Lô 1) | 2 / 1f | `ai/settings/services.py`, `ai/registry/discovery.py:61` (cùng kiểu ghép chuỗi). Cố tình ghép chuỗi cho khỏi grep là mùi code, nên bỏ |
| `HOME_CSKH_QUEUE` | `HOME_CONFIRMATION_QUEUE` | 2 / 1f | `accounts/auth/services.py` (giá trị `"cskh-queue"` là M2) |
| `NhapLoInput`, `NhapLoLine`, `NhapLoBatchOutput`, method `nhap_lo` | `ReceiveBatchesInput`, `ReceiveBatchesLine`, `ReceivedBatchOutput`, `receive_batches` | 10 / 2f | `purchasing/receipts/api.py`, `serializers.py`. Đổi tên method làm đổi id lệnh AI, nên **phải đi cùng M2/M3** |
| FE `Cskh*` (`fetchCskhQueue`, `fetchCskhDetail`, `claimCskhTask`, `recordCskhCall`, `searchCskh`, `decideCskh`, `CskhQueueItem`, `CskhQueueDetail`, `CskhQueueResponse`, `CskhSearch*`, `CskhDecision`, `CskhConfirmState`, `CskhPage`, `CskhNoticeConfig`, `mock*Cskh*`, `cskhArmStale`) | Đổi `Cskh` thành `Confirmation` (vd `fetchConfirmationQueue`, `ConfirmationQueueItem`). Hàm tìm khách đổi thành `searchCustomers` | prod 122 / 15f, test 61 / 14f | `features/cskh/*`, `frontend/features/site/*` |
| FE `NhapLo*` (`NhapLoPayload`, `NhapLoResponse`, `NhapLoLineInput`, `NhapLoBatchItem`, `NhapLoDraft`, `NhapLoDraftLine`, `submitNhapLo`, `mockSubmitNhapLo`, `NHAP_LO_DRAFT_PREFIX`, `nhapLoCap`, state `nhap_lo_kg`, `nhap_lo_vnd`, `nhap_lo_daily`) | `ReceiveBatches*`, `submitReceiveBatches`, `RECEIVE_BATCHES_DRAFT_PREFIX`, `receiveCap`, `receive_kg`, `receive_vnd`, `receive_daily` | prod 63 / 10f, test 12 / 2f | `purchasing/*`, `shared/lib/drafts.ts`, `ai/policy/components/AiPolicyScreen.tsx` |
| FE `GROUP = { chu, quanLy, nvKho, nvGiao, cskh }`, `chuOnlyStep` | `ROLE = { owner, manager, warehouseStaff, deliveryStaff, customerCare }`, `ownerOnlyStep` | khoảng 30 / 6f | `shared/lib/nav.ts`, `shared/lib/groups.ts`, `features/staff/*`. Giữ nguyên **giá trị** chuỗi đến Lô 4 |
| FE mock `KHO_LANH` | `COLD_STORAGE_NAME` | 12 / 1f | `shared/lib/dashboardSummary.mock.ts` |
| View key `"cskh"` (`ViewGuard view="cskh"`, `nav.ts`) | `"confirmation"` | 3 / 2f | Chỉ FE dùng, không gửi lên BE |

#### M1-c. Test (tên file, class, hàm hỗ trợ, biến, tên hàm test)

| Hạng mục | Hiện tại (ví dụ) | Đề xuất | Số chỗ |
|---|---|---|---|
| File test BE | `test_cskh_l1..l4.py`, `test_ra_soat_cskh.py`, `test_ra_soat_extra.py`, `test_ra_soat_s03_checkout_throttle.py`, `test_nhap_lo.py`, `test_s5_scope_nv_giao.py`, `test_l7_bosung.py`, `test_l8_tien_bosung.py`, `test_qa_lo4_tien.py`, `test_qa_lo4_backfill_leak.py`, `test_p8_lo{1,3,5,7}_*.py`, `test_p8_qa_lo2_*.py` | Đặt theo **hành vi**, không theo lô giao việc. Vd `test_confirmation_queue.py`, `test_confirmation_deadlines.py`, `test_receive_batches.py`, `test_delivery_staff_scope.py`, `test_payment_amounts_extra.py`, `test_undo.py`, `test_daily_limit.py`. Mã story (SR-xx, BM-xx, P8) ghi trong docstring | 33 file |
| Script e2e | `ra_soat_*.py` (7 ERP + 3 Shop), `ra-soat-a2-golive.py`, `sr07_nhap_lo_draft.py`, `p8_lo5_fe_lo_qua_han.py`, `p8_lo{5,6,7}_*.py`, `qa-lo{6,7}-*.py` | `review_*.py`, `sr07_receive_batches_draft.py`, `p8_expired_batch_ui.py`… (bỏ "lo") | 15 file |
| Class base test | `CskhL1Tests`, `CskhL2/L3/L4BaseTestCase` (L3 được 9 file khác import) | `ConfirmationBaseTestCase`… | 20 lần / 9f |
| Hàm hỗ trợ test | `_create_order_with_cskh`, `assert_khong_go_nua_chung`, `create_giao4` | `_create_order_with_confirmation`, `assert_no_further_removal`, `create_courier4` | 67 lần / 7f |
| Biến test theo vai | `self.chu`, `ql`, `kho`, `giao`, `c_chu`, `client_kho`, `user_kho`, `kho1`, `giao1`, `quan_ly_group`, `g_nv_kho`, `u_cskh`, `res_kho`, `tom`… | `self.owner`, `manager`, `warehouse`, `courier`, `owner_client`, `warehouse_client`, `customer_care_user`… | **khoảng 2.980 lần, 150 tên khác nhau** trong khoảng 150 file |
| Tên hàm `test_*` | `test_s46_ac3_sai_mat_khau_hien_tai_400_token_cu_con_dung`, `test_f1_ac2_cung_han_lo_nhap_som_hon_ra_truoc`… | `test_s46_ac3_wrong_current_password_400_old_token_still_valid`… | **959 / 1.615 hàm** trong 112 file |
| `data-testid` | `cskh-notice`, `cskh-stale-alert` | `confirm-call-notice`, `confirmation-stale-alert` | prod 2 / 2f, e2e 10 / 5f (FE và e2e đổi cùng commit) |
| Username và dữ liệu demo trong test | `"kho"`, `"chu_vua"`, `"Loc-mat-khau-2026"`, mã hàng `TOM-SU-1` | **Không đổi.** Đây là dữ liệu, không phải định danh | — |

### M2 — Contract (BE và FE phải đổi cùng lúc, nên giữ alias tạm)

| Hiện tại | Đề xuất | Số chỗ | File tiêu biểu | Cách giữ tương thích |
|---|---|---|---|---|
| Route `/api/cskh/queue/…` (list, retrieve, `claim`, `calls`, `unconfirm`, `recipient`, `decide`), router basename `cskh-queue` | `/api/confirmation/queue/…`, basename `confirmation-queue` | prod 10 / 2f, test 70 / 7f | `config/api_urls.py:83`, `erp-console/features/cskh/api.ts` | Đăng ký **cả 2 prefix** trong 1 bản phát hành rồi mới bỏ prefix cũ. **Bắt buộc** thêm `/api/confirmation/` vào `FORBIDDEN_PREFIXES` (`ai/policy/rules.py:17`), xem rủi ro R1 |
| Route `/api/cskh/search/` | `/api/confirmation/search/` (hoặc `/api/customer-care/search/`) | như trên | `config/api_urls.py` | như trên |
| Action `POST /api/purchasing/receipts/nhap-lo/` | `POST /api/purchasing/receipts/receive-batches/` | prod 2 / 2f, test 17 / 4f | `purchasing/receipts/api.py:59`, `erp-console/features/purchasing/api.ts` | Giữ action alias cũ **không có `ai=`** trong 1 bản, để registry không sinh 2 lệnh AI |
| Id lệnh AI `purchasing.purchasereceipt.nhap_lo` (sinh tự động từ tên method) | `purchasing.purchasereceipt.receive_batches` | prod 10 / 6f, test 41 / 9f | `ai/*`, `erp-console/features/ai/**` | Kéo theo dữ liệu M3 (mục M3-b) |
| Khoá `sessionStorage`/`localStorage` `cave_draft_nhap_lo[:<userId>]` | `cave_draft_receive_batches:<userId>` | prod 6 / 3f, test 23 / 3f | `shared/lib/drafts.ts`, `purchasing/components/draftStorage.ts`, `AuthProvider.tsx` | `clearAllDrafts()` **phải xoá mãi mãi cả prefix cũ**, vì nháp cũ có giá mua (SR-07, bất biến 1). Có thể chuyển nháp cũ sang khoá mới một lần khi mở form |
| Khoá JSON `GET /api/dashboard/attention/`: `cskh_queue_waiting`, `cskh_escalated`, `cskh_auto_cancel_blocked` | `confirmation_queue_waiting`, `confirmation_escalated`, `confirmation_auto_cancel_blocked` | prod 30 / 4f, test 16 / 2f | `delivery/attention_api.py`, `overview/components/AttentionBlock.tsx` | BE trả **cả khoá cũ và mới** trong 1 bản, FE đọc khoá mới trước rồi mới tới khoá cũ |
| Khoá JSON công khai `GET /api/public/site-info/` → `cskh_notice` | `confirm_call_notice` | prod 19 / 7f, test 18 / 5f | `content/site/api.py:22`, `frontend/features/site/types.ts` | Trả cả 2 khoá. Shop là static export, trình duyệt có thể còn bản cũ trong cache nên giữ khoá cũ lâu hơn (2 bản) |
| Giá trị `home` trong `/api/auth/me/`: `"cskh-queue"` | `"confirmation-queue"` | prod 6 / 4f, test 2 / 1f | `accounts/auth/services.py:28`, `erp-console/shared/lib/nav.ts:391` | FE nhận cả 2 giá trị trước, BE đổi sau |
| Route ERP `/cskh/` (thư mục `app/(console)/cskh/`) | `/confirmation/` | prod 7 / 3f, test 7 / 5f | `nav.ts`, `AttentionBlock.tsx` | Giữ trang `/cskh/` chỉ để chuyển hướng (client redirect) cho ai đã bookmark |
| 11 biến env `CSKH_*` (`CSKH_MAX_UNREACHABLE_ATTEMPTS`, `CSKH_UNREACHABLE_WINDOW_MINUTES`, `CSKH_MIN_RETRY_MINUTES`, `CSKH_MANAGER_DECISION_MINUTES`, `CSKH_PII_RECENT_DAYS`, `CSKH_CLAIM_MINUTES`, `CSKH_EXTEND_MAX_HOURS`, `CSKH_WORKING_HOURS`, `CSKH_QUEUE_ALERT_MINUTES`, `CSKH_AUTO_CANCEL_ENABLED`, `CSKH_NOTICE_ENABLED`) + `THROTTLE_CSKH_SEARCH` | `CONFIRMATION_*` (vd `CONFIRMATION_MAX_UNREACHABLE_ATTEMPTS`), `THROTTLE_CUSTOMER_SEARCH` | prod 56 / 11f, test 30 / 10f | `config/settings.py:280-295` | Settings đọc tên mới trước, không có thì đọc tên cũ (`_env("NEW", "OLD", default)`). Phải kiểm Cloud Run staging và production xem có đặt env `CSKH_*` nào không; hiện `doc/ops/` không ghi |
| Scope throttle `cskh_search` | `customer_search` | 3 / 3f | `settings.py:216`, `common/throttling.py:89` | Đổi cùng lúc với env |
| Lệnh quản trị `process_cskh_deadlines`, `check_cskh_job_health` | `process_confirmation_deadlines`, `check_confirmation_job_health` | 2 file + Cloud Run Job/Scheduler (theo kế hoạch ở `doc/ke-hoach-tong.md:37`) | `delivery/management/commands/` | Giữ file lệnh cũ gọi lại lệnh mới trong 1 bản, cập nhật args của Job rồi mới xoá |
| Tên logger `cangca.delivery.cskh` | `cangca.delivery.confirmation` | 3 / 3f | `delivery/cskh/services.py:21`, `check_cskh_job_health.py:16` | Cập nhật bộ lọc log hoặc cảnh báo trên GCP nếu có |
| Nhóm lệnh AI trong API (`group`): `thu_mua`, `ban_hang`, `cskh` | `purchasing`, `sales`, `customer_care` | prod 11 / 6f, test 20 / 8f | `ai/registry/spec.py`, `ai/registry/discovery.py:46-66`, `ai/settings/services.py:96`, `erp-console/features/ai/types.ts:61` | Có lưu trong DB (M3-b), nên đổi cùng migration |
| Mức nhạy cảm lệnh AI `sensitivity`: `cao`, `trung_binh`, `thap` | `high`, `medium`, `low` | prod 10 / 4f, test 4 / 2f | `ai/registry/spec.py:24`, `discovery.py:266,333`, `inventory/batches/api.py:24`, `erp-console/features/ai/types.ts` | Không lưu DB. BE và FE đổi cùng commit |
| Keyword AI dạng snake không dấu: `tra_ton`, `tra_don`, `chot_lo`, `tra_ncc`, `nhap_lo`, `tao_phieu_hoan`, `xac_nhan_hoan`, `tra_hang`, `bao_cao_ton_kho` | **Xoá hẳn**, không dịch | prod 10 / 6f, test 12 / 4f | `inventory/batches/api.py`, `sales/refunds/api.py`, `catalog/items/api.py`… | Keyword là từ vựng để khớp câu người dùng gõ, không phải định danh. Tokenizer BM25 (`features/ai/commands/search.ts`) đã bỏ dấu và tách theo `_`, nên `"tra_ton"` trùng hẳn với `"tra tồn"`. Test DW-15-AC3 vẫn qua nếu giữ phần có dấu |
| Tên Group trong contract (`me.groups`, `PUT /api/staff/<id>/groups/`, `GroupCode` ở `features/auth/types.ts`) | Theo M3-a | xem M3-a | | Đi cùng M3-a |

### M3 — Dữ liệu và quyền (cần data migration, ảnh hưởng staging/production và tài liệu nghiệp vụ)

#### M3-a. Tên Group (bảng `auth_group`)

| Hiện tại | Đề xuất | Chuỗi literal: prod / test / mig | File prod tiêu biểu |
|---|---|---|---|
| `chu` | `owner` | 34 / 193 / 11 | `accounts/staff/services.py`, `sales/payments/auto_confirm.py`, `ai/actions/services.py`, `ai/management/commands/run_due_ai_actions.py`, `common/api.py:111` |
| `quan_ly` | `manager` | 16 / 140 / 9 | `accounts/auth/services.py`, `purchasing/receipts/services.py:170`, `ai/actions/services.py` |
| `nv_kho` | `warehouse_staff` | 10 / 167 / 4 | `accounts/auth/services.py`, `common/api.py:111` |
| `nv_giao` | `delivery_staff` | 9 / 143 / 2 | `accounts/auth/services.py:89` |
| `cskh` | `customer_care` | 13 / 47 / 3 | `delivery/cskh/scope.py:16`, `accounts/auth/services.py:91` |
| **Cộng** | | **82 / 690 / 29** | Phía FE: `nav.ts`, `groups.ts`, `auth/types.ts`, `content/edit/page.tsx:88`, `AiAssistantPanel.tsx:260` |

Tên Group cũng xuất hiện rất nhiều trong tài liệu: khoảng 300–800 dòng mỗi tên, rải trên 40–90 file trong `doc/`, `.claude/skills/`
và `AGENTS.md` (đếm thô, có lẫn chữ thường). Riêng `doc/decisions.md` dòng 123 và 149 **ghi đích danh** 4 tên Group.

#### M3-b. Dữ liệu AI lưu trong DB

| Chỗ lưu | Giá trị cũ | Giá trị mới | Ghi chú |
|---|---|---|---|
| `AiAction.assignee_group` (CharField) | `chu`, `quan_ly`, `nv_kho`… | tên Group mới | Việc AI đang chờ hoặc đã lên lịch đọc cột này để giao việc (`run_due_ai_actions.py`), nên phải đổi giá trị cùng migration đổi Group |
| `AiAction.command` | `purchasing.purchasereceipt.nhap_lo` | `…receive_batches` | Việc đang chờ hoặc hẹn giờ tra spec theo id. Nếu không đổi, việc cũ sẽ lỗi "không tìm thấy lệnh" |
| `AiConfigVersion.group_levels` (JSON key) | `thu_mua`, `ban_hang`, `cskh` | `purchasing`, `sales`, `customer_care` | `ai/policy/effective.py:112-122` đọc theo key. Nếu không migrate, cấu hình AI của từng người sẽ về mặc định mà không báo gì |
| `AiConfigVersion.overrides` / `limits`, `AiPolicyVersion.caps` / `red_zone_open` (JSON key là id lệnh) | `…nhap_lo` | `…receive_batches` | Trần kg, VND và số lần/ngày của Chủ cho lệnh nhập lô (`AiPolicyScreen`) sẽ mất tác dụng nếu không đổi key, tức là **nới an toàn mà không ai biết** |
| `AuditLog.action` | `execute_purchasing.purchasereceipt.nhap_lo`, `propose_nhap_lo` (chỉ có trong test) | **Không đổi** | `AuditLog` là append-only (bất biến 4). Màn Nhật ký hoặc báo cáo cần bảng ánh xạ tên cũ → nhãn nếu có lọc theo action |

#### M3-c. Permission codename, model, bảng, choices

**Không có mục nào cần đổi.** Toàn bộ codename (`view_costprice`, `view_profitreport`, `close_batch`, `cancel_expired_batch`,
`confirm_with_customer`, `decide_unconfirmed`, `change_recipient`, `print_label`, `pack_deliverynote`, `manage_ai_policy`…),
46 model, `TextChoices` và `*_CHOICES` đều đã là tiếng Anh. Không có `db_table` tuỳ biến.

---

## 2. Glossary đề xuất (dùng thống nhất cho code mới và khi đổi tên)

Nguyên tắc: **ưu tiên từ đã phổ biến trong code**. Tên đặt theo việc mà module hoặc hàm làm, không theo tên phòng ban hay theo
lô giao việc.

| Tiếng Việt | Tên chuẩn trong code | Đã dùng sẵn ở đâu | Ghi chú |
|---|---|---|---|
| Chủ (vai) | `owner` | `actor_is_owner` | Lưu ý `AiAction.owner` là "người tạo việc", không phải Group Chủ. Khi viết `assignee_group="owner"` cần đọc kỹ |
| Quản lý | `manager` | `CSKH_MANAGER_DECISION_MINUTES` | |
| NV kho | `warehouse_staff` | `Warehouse` | |
| NV giao | `delivery_staff` (vai), `courier` (người giao trên một phiếu) | `my-deliveries`, `DeliveryNote.assigned_to`, `courierName` (mock) | Vai `delivery_staff` đi đôi với `warehouse_staff` |
| CSKH (vai) | `customer_care` | — | Phương án khác: `customer_service`. **Cần Duy chốt** (câu Q1) |
| Gọi xác nhận đơn (tính năng hay module của CSKH) | `confirmation` | `ConfirmationTask`, `CustomerCall`, `confirm_with_customer`, `ConfirmCallNotice` | Module đặt theo việc (`confirmation`), còn Group đặt theo vai (`customer_care`) |
| Nhóm lệnh AI "Thu mua / Bán hàng / CSKH" | `purchasing` / `sales` / `customer_care` | trùng tên app `purchasing`, `sales` | |
| Lô hàng | `batch` | `Batch`, `publish_batch`, `close_batch` | |
| Lô giao việc (P8 Lô 7…) | **không đưa vào tên code** | — | Chữ "lo" trong `test_p8_lo7_*` trùng nghĩa với lô hàng, dễ nhầm. Mã lô và story ghi trong docstring |
| Nhập lô (form hoặc action) | `receive_batches` | service `create_and_submit_receipt` | |
| Phiếu nhập | `purchase_receipt` | `PurchaseReceipt` | |
| NCC | `supplier` | `Supplier` | |
| Trả NCC | `supplier_return` (danh từ), `return_to_supplier` (hành động) | `BatchSupplierReturn`, action `return-to-supplier` | |
| Giá vốn | `landed_unit_cost` (field), `cost` (khái niệm), quyền `view_costprice` | có sẵn | Không đổi tên field hay quyền |
| Giá mua | `purchase_rate` | `Batch.purchase_rate` | |
| Lãi lỗ | `profit` / `pnl` | `ProfitReport`, `batch_pnl` | |
| Chốt lô | `close_batch` | có sẵn | |
| Huỷ | `cancel` | có sẵn | |
| Hoàn tiền / phiếu hoàn | `refund` | `Refund` | |
| Phiếu giảm trừ | `credit_note` | `SalesCreditNote` | |
| Kiểm kê | `stocktake` (module), `stock_reconciliation` (chứng từ) | có sẵn | |
| Tra (tồn, đơn) | `lookup` / `list` | | |
| Tem | `label` | `LabelPrint` | |
| Khách | `customer` | `Customer` | |
| Đơn | `order` | `SalesOrder` | |
| Tiền | `amount` | `amount` | |
| Rà soát (bản review QA) | `review` | — | **Không** dùng `audit`, vì dễ nhầm với `AuditLog` hay "nhật ký". Coordinator gợi ý `audit`, Tech Lead đề xuất `review` (câu Q2) |
| Bổ sung | `extra` / `followup` | | |
| Mức nhạy cảm cao/TB/thấp | `high` / `medium` / `low` | | |
| Bài viết / Trang (CMS) | `post` / `page` | `kind="post"`, `"page"` | URL công khai giữ nguyên `/bai-viet/`, `/trang/` (mục 3.3) |
| Kho lạnh | `cold_storage` | | |
| Mật khẩu | `password` | có sẵn | |

---

## 3. Kế hoạch đổi tên theo lô

**Điều kiện bắt đầu:** P8 Lô 7 đã QA APPROVED và commit xong. Lý do: 3 agent đang sửa đúng những file có trong danh sách
(`delivery/cskh/services.py`, `features/cskh/*`, `purchasing/*`, `CskhNotice.tsx`). Nếu đổi tên song song sẽ conflict nặng.

**Luật chung cho mọi lô:**
- Mỗi lô là một commit riêng, **chỉ đổi tên, không đổi hành vi**.
- Số test trước và sau phải bằng nhau.
- Phải chạy đủ: `manage.py test`, `makemigrations --check --dry-run` sạch, `adapter pytest`, `erp-console tsc` + `vitest` +
  `build`, `frontend build`, và `check-no-mock` / `check-ai-chunks`.
- Dùng `git mv` để giữ lịch sử file.

### Lô 0 — Chốt quy ước và chặn phát sinh mới (làm ngay, rủi ro 0, khoảng 0,5 ngày)
1. Duy duyệt glossary ở mục 2 và trả lời Q1–Q4.
2. Ghi luật đặt tên vào `.claude/skills/django-drf-patterns`, `nextjs-shop-patterns`, `caveve-domain` và `AGENTS.md`, để
   Gemini/Antigravity cũng theo.
3. Thêm script `scripts/check-naming` (hoặc 1 test Django và 1 script `.mjs` trong FE) để **fail khi file mới hoặc file đổi có
   token trong danh sách chặn**. Danh sách chặn gồm `cskh`, `nv_kho`, `nv_giao`, `quan_ly`, `nhap_lo`, `ra_soat`, `_lo\d`…
   Tạm miễn cho các chỗ đã liệt kê ở mục 1, cho tới khi lô tương ứng làm xong.
4. Báo cho các agent của Lô 7 biết: code mới (vd `CskhNotice.tsx`) đặt theo glossary ngay từ đầu.

### Lô 1 — M1 code chạy thật + tập trung hằng Group (khoảng 1–1,5 ngày, rủi ro thấp)
- **BE:** thêm `apps/accounts/roles.py` với hằng `OWNER`, `MANAGER`, `WAREHOUSE_STAFF`, `DELIVERY_STAFF`, `CUSTOMER_CARE`.
  **Giá trị vẫn là tên cũ** (`"chu"`…). Thay toàn bộ 82 chuỗi literal trong code chạy thật bằng hằng này, và bỏ kiểu ghép chuỗi
  `"".join(["cs","kh"])`.
- **FE:** làm tương tự. `shared/lib/nav.ts` dùng `ROLE = { owner: "chu", … }`, và `GroupCode` lấy kiểu từ `ROLE`.
- Việc này làm Lô 4 chỉ còn đổi **1 chỗ mỗi phía**.
- Chuyển module `apps/delivery/cskh/` → `apps/delivery/confirmation/` và `features/cskh/` → `features/confirmation/`. Đổi tên các
  class, hàm và type ở M1-b. **Giữ nguyên** route, khoá JSON, env và id lệnh (những thứ đó thuộc Lô 3).
- **Kiểm tra bắt buộc:** snapshot chỉ mục AI (`/api/ai/commands/index/`) trước và sau phải giống hệt nhau. Lý do là
  `discovery._get_group` phân nhóm lệnh theo **chuỗi con trong tên module** (`"return"`, `"delivery"`, `"guidance"`…), nên đổi tên
  module có thể làm một lệnh đổi nhóm mà không báo gì.

### Lô 2 — M1 test (khoảng 1 ngày cho file, class và biến; tên hàm test làm riêng)
- Đổi tên 33 file test BE, 15 script e2e, class base, hàm hỗ trợ và biến theo vai (khoảng 3.000 chỗ, gần như thay thế cơ học).
  Test chạy lại phải cho **đúng số test cũ**.
- Tên 959 hàm `test_*`: không dịch máy được, vì mỗi tên phải dịch theo nghĩa. Có 2 phương án (câu Q3):
  - (a) Dịch dần theo kiểu "boy-scout": sửa file nào thì đổi tên test của file đó. Test mới bắt buộc tiếng Anh.
  - (b) Làm 1 lô riêng khoảng 1,5–2 ngày, có AI hỗ trợ, và kiểm bằng `--collect-only` hoặc so danh sách test.

  Tech Lead đề xuất **(a)**. Tên test không lộ ra ngoài, còn đổi cả loạt thì làm `git blame` và hồ sơ QA (các `04-qa-report.md`
  có trích tên test) khó tra hơn.

### Lô 3 — M2 contract (khoảng 1,5–2 ngày + QA E2E, rủi ro trung bình, BE và FE chung 1 commit)
- Theo cột "Cách giữ tương thích" ở bảng M2. Thứ tự deploy là **BE trước** (trả cả tên cũ và mới), **FE sau** (dùng tên mới).
  Bản kế tiếp mới gỡ alias.
- **Bắt buộc**, xem R1: thêm `/api/confirmation/` vào `FORBIDDEN_PREFIXES`, và thêm test "không route nào mang dữ liệu cá nhân
  lọt vào chỉ mục AI" cho cả prefix cũ lẫn mới.
- Đổi id lệnh AI `nhap_lo` đi cùng migration M3-b (JSON key). Có thể gộp phần này sang Lô 4 nếu muốn chỉ có 1 lần migration AI.
- Ops: kiểm env `CSKH_*` trên Cloud Run staging và prod, và args của Cloud Run Job `process_cskh_deadlines` (nếu đã tạo). Cập nhật
  `doc/ops/moi-truong.md`.

### Lô 4 — M3 dữ liệu và quyền (khoảng 1,5 ngày + nghiệm thu staging, rủi ro trung bình–cao)
- Migration `accounts/0012_rename_groups` (RunPython): `Group.objects.filter(name=old).update(name=new)`.
  - Làm vậy **giữ nguyên id**, nên quyền gán cho Group và thành viên Group không đổi.
  - Có hàm reverse đổi ngược lại.
  - Idempotent: nếu tên mới đã tồn tại thì bỏ qua và báo.
- Cùng migration (hoặc `ai/0003`), đổi:
  - `AiAction.assignee_group`;
  - `AiAction.command` từ `…nhap_lo` sang `…receive_batches`;
  - khoá JSON trong `AiConfigVersion.group_levels`, `overrides`, `limits` và `AiPolicyVersion.caps`, `red_zone_open`.

  Không đụng `AuditLog`.
- Đổi giá trị hằng trong `roles.py` và `ROLE` (FE) sang tên mới. Migration cũ (`0002_seed_permission_groups`,
  `0011_seed_group_cskh`, `content/0002`, `reports/0002`…) **giữ nguyên**, vì DB mới vẫn chạy chúng trước migration đổi tên nên
  kết quả cuối cùng vẫn đúng.
- **Thứ tự deploy (quan trọng):**
  1. FE phát hành trước với lớp chuẩn hoá `normalizeGroup()` chấp nhận cả tên cũ và mới. Nếu thiếu lớp này, trong khoảng thời gian
     giữa hai lần deploy menu sẽ bị ẩn hoặc hiện sai.
  2. Deploy BE kèm migration lên **staging**, chạy E2E với 5 vai.
  3. Duy duyệt, rồi làm lại với production.
  4. Bản kế tiếp gỡ tên cũ khỏi `normalizeGroup()`.
- Tài liệu: Duy cần chấp thuận sửa tên Group trong `doc/decisions.md`. Chỉ đổi mã định danh, không đổi nội dung quyết định là
  "4+1 Group cộng dồn". Sau đó cập nhật §1.5 `business-process-spec.md`, skill `caveve-domain` (bất biến 2 và 9), `AGENTS.md`, và
  mẫu test trong `django-drf-patterns`.
- Nếu có tài khoản hoặc kịch bản ngoài code nhắc tên Group (ví dụ tài liệu hướng dẫn gửi Lộc), cần báo trước khi đổi.

### 3.1. Rủi ro và cơ chế chặn

| # | Rủi ro | Cơ chế chặn | Test bắt lỗi |
|---|---|---|---|
| R1 | Đổi `/api/cskh/` mà quên danh sách cấm của AI, làm route có tên/SĐT khách lọt vào chỉ mục lệnh AI (**Critical**, bất biến 9) | Thêm prefix mới vào `FORBIDDEN_PREFIXES` ngay trong commit đổi route | Test quét registry: không spec nào có path bắt đầu bằng prefix cấm, cả cũ lẫn mới. Có thể mở rộng `ai/registry/tests/test_default_safety.py` |
| R2 | Đổi tên Group mà quyền không theo, dẫn tới người dùng mất quyền hoặc leo quyền | Đổi bằng `update(name=…)`, giữ id. Không xoá rồi tạo lại Group | Test migration: trước và sau, `Group.permissions` và `user.groups` của từng vai giống nhau. Chạy lại `test_permissions_matrix`, `test_dashboard_cost_leak`, `test_l3_cost_redaction` |
| R3 | Lọt giá vốn khi đổi tên Group. `FULL_SCOPE_GROUPS` (`common/api.py:111`) và `is_owner` đều so theo tên | Dùng hằng `roles.py` từ Lô 1, nên chỉ còn 1 chỗ đổi | Các test chống rò giá vốn hiện có, chạy với fixture dùng hằng mới |
| R4 | Nháp "Nhập lô" cũ có giá mua còn nằm trong trình duyệt sau khi đổi khoá | `clearAllDrafts()` xoá cả prefix cũ, vĩnh viễn | `draftStorage.test.ts`, và e2e `sr07_*` có thêm ca "khoá cũ bị xoá khi đăng xuất" |
| R5 | Cấu hình hoặc trần AI mất hiệu lực không báo gì khi đổi key (nới an toàn) | Migration JSON key trong cùng lần deploy với code | Test: sau migration, `effective.py` trả đúng trần kg/VND/lần của lệnh mới giống lệnh cũ |
| R6 | Việc AI đang chờ hoặc hẹn giờ trỏ id lệnh cũ và bị lỗi | Migration `AiAction.command` và `assignee_group` | Test `run_due_ai_actions` với 1 việc được tạo bằng id cũ trước migration |
| R7 | FE và BE lệch nhau trong khoảng thời gian giữa hai lần deploy (static export không deploy cùng lúc được) | BE trả cả 2 tên, FE `normalizeGroup()` | E2E staging với 5 vai sau từng bước deploy |
| R8 | Đổi tên module làm lệnh AI đổi nhóm mà không báo | So snapshot chỉ mục AI trước và sau | Test snapshot mới (Lô 1) |
| R9 | Không đụng chứng từ hay xoá dữ liệu | Chỉ `UPDATE` tên Group và key JSON AI. Không đụng `AuditLog`, `StockLedgerEntry` hay `*LineBatch` | Review migration |

### 3.2. Ước lượng tổng

| Lô | Công | Rủi ro | Cần Duy |
|---|---|---|---|
| 0 | 0,5 ngày | Không | Duyệt glossary, Q1–Q4 |
| 1 | 1–1,5 ngày | Thấp | — |
| 2 | 1 ngày (+1,5–2 ngày nếu chọn Q3-b) | Thấp | Chọn Q3 |
| 3 | 1,5–2 ngày + QA E2E | Trung bình | Duyệt deploy staging và prod |
| 4 | 1,5 ngày + nghiệm thu staging | Trung bình–cao | Chấp thuận sửa `decisions.md`, duyệt deploy |

### 3.3. Những thứ KHÔNG nên đổi

- **Migration đã chạy** (`0011_seed_group_cskh.py`, `delivery/0004_cskh_confirmation.py`…): không đổi tên file, không sửa nội dung.
  Nếu làm, bảng `django_migrations` trên staging và prod sẽ lệch.
- **Bảng DB và tên model:** vốn đã là tiếng Anh, không có việc gì phải làm. Nếu sau này muốn đổi tên model, giữ `db_table` cũ để
  khỏi phải đổi tên bảng.
- **`AuditLog.action` đã ghi** (append-only).
- **URL công khai của Shop** `/bai-viet/`, `/trang/` và `?chuyen-muc=`: đây là chữ khách nhìn thấy, tốt cho SEO tiếng Việt và đã
  nằm trong link hoặc QR phát ra ngoài. Coi như "chữ hiển thị". `public_path` do serializer tự tính, không lưu DB.
- **Dữ liệu nghiệp vụ và demo:** slug bài viết, mã hàng (`TOM-SU-1`), username demo (`kho1`, `giao1`, `ql1`), placeholder trong
  `.env.example`.
- **Keyword AI có dấu** (`"tra tồn"`, `"chốt lô"`…): đây là từ vựng để khớp câu người dùng gõ. Chỉ xoá bản snake không dấu thừa.
- `utm_medium=bai_viet` (`frontend/features/content/components/ItemCard.tsx:22`): giá trị analytics. Chỉ đổi thành `article` nếu
  Duy chưa cần số liệu liên tục (câu Q4).
- Chuỗi `cangca` trong hạ tầng và logger: nằm ngoài phạm vi rà soát này.

### 3.4. Câu hỏi cần Duy chốt

- **Q1.** Vai CSKH đặt là `customer_care` (dịch sát nghĩa "chăm sóc khách hàng") hay `customer_service` (cách gọi phổ biến hơn
  trong tiếng Anh)? Tech Lead nghiêng về `customer_care`.
- **Q2.** Các bản rà soát QA đặt là `review_*` (Tech Lead đề xuất) hay `audit_*`? `audit` dễ nhầm với `AuditLog`.
- **Q3.** Tên 959 hàm test: (a) đổi dần khi sửa file (đề xuất) hay (b) làm 1 lô riêng đổi hết?
- **Q4.** Có đổi tên Group (M3, Lô 4) không? Đây là mục đắt nhất: phải sửa `decisions.md`, migrate staging và prod, và có khoảng
  thời gian FE/BE lệch nhau. Nếu Duy thấy chưa cần thì có thể dừng ở Lô 3, vì sau Lô 1 tên Group chỉ còn nằm ở 1 file hằng mỗi
  phía. Kèm theo: có đổi `utm_medium=bai_viet` không?

---

## 4. Tóm tắt cho Duy

- **Tin tốt:** bảng DB, model, quyền và trạng thái đều đã là tiếng Anh. Không phải đổi tên bảng, đây vốn là phần đắt nhất.
- **Nợ chính nằm ở 3 cụm tên.** Cụm "CSKH" có 1 module BE, 1 module FE, 2 route API, 12 biến env và khoảng 180 định danh `Cskh*`.
  Cụm "Nhập lô" có 1 route, 1 id lệnh AI, 1 khoá nháp và khoảng 75 định danh. Cụm tên 5 nhóm quyền (`chu`, `quan_ly`, `nv_kho`,
  `nv_giao`, `cskh`) có 82 chỗ trong code chạy thật và 690 chỗ trong test.
- **Theo mức:**
  - M1 nội bộ: khoảng 300 chỗ trong code chạy thật (khoảng 45 file, 2 thư mục module), khoảng 3.000 biến test, 48 file test/e2e,
    và 959 tên hàm test.
  - M2 contract: 16 hạng mục (route, khoá JSON, env, khoá lưu trình duyệt, id lệnh AI, lệnh chạy định kỳ), khoảng 180 chỗ trong
    code chạy thật.
  - M3 dữ liệu: 5 tên Group và 4 chỗ dữ liệu AI lưu DB. Permission, model và choices: 0 chỗ.
- **Đề xuất làm theo thứ tự:**
  1. **Ngay bây giờ (Lô 0):** Duy duyệt bảng thuật ngữ, và thêm luật cùng script chặn tên tiếng Việt mới. Hiện Lô 7 vẫn đang sinh
     thêm tên `Cskh*`.
  2. **Sau khi Lô 7 commit:** làm Lô 1 (đổi nội bộ và gom tên nhóm quyền về 1 chỗ), rồi Lô 3 (contract có alias).
  3. **Lô 4 (đổi tên Group trong DB):** chỉ làm khi Duy đồng ý sửa `decisions.md`, đi qua staging trước.
  4. **Tên hàm test:** đổi dần.
- **Rủi ro phải canh:**
  - Đổi route `/api/cskh/` mà quên thêm route mới vào danh sách cấm của AI thì lộ dữ liệu cá nhân khách. Mức Critical.
  - Đổi key cấu hình AI mà không migrate thì trần an toàn nhập lô bị mất.
  - Nháp "Nhập lô" cũ có giá mua phải tiếp tục bị xoá khi đăng xuất.

---
## Quyết định Duy 30/09
- Q1: CSKH → **`customer_service`** (không dùng `customer_care`). Group `cskh` → `customer_service` cho thống nhất.
- Q2: bản rà soát QA → `review_*` (theo đề xuất techlead, tránh nhầm `AuditLog`).
- Q3: 959 hàm test tiếng Việt → **đổi dần khi sửa file**; test mới đặt tiếng Anh ngay.
- Q4: **đổi tên 5 Group** ở lô cuối (giữ id, FE nhận cả tên cũ/mới trước), được phép sửa `doc/decisions.md` dòng liên quan.
- Thứ tự: **sau P8, trước P9** (code AI local mới viết trên tên chuẩn).
