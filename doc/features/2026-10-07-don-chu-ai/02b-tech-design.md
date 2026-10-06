# Lô dọn chữ AI và nhãn lệch khách thấy — thiết kế kỹ thuật (02b)

> Luồng NHANH. Duy chốt tối 06/10. Viết trên main `efa76cc`, sau khi đã có TL-D3-L4 (`exclude_ai_rows` ở `/api/audit-logs/`).
> Nguồn: `doc/thuat-ngu-va-trang-thai.md` mục 3 (A1–A17), mục 2.10 (W1, W2, W39), mục 4 (T2, T24–T30, **chưa duyệt**, chỉ dùng tạm cột "Shop").
> BR liên quan: BR-AI-17 (AI tắt không tải gì), BR-PQ-04/05 (vết kiểm toán), BR-GH-19 (ghi chú không chứa SĐT/số TK), BR-BH-03 (giữ chỗ TTL).

## 0. Hiện trạng đã kiểm trên main

| Việc | Hiện trạng |
|---|---|
| Cờ BE | `settings.AI_ENABLED` (`config/settings.py:266`). `apps/ai/status/services.py:is_ai_enabled()` = cờ env **và** Chủ chưa tắt khẩn (`global_mode != off`) |
| Cờ FE | `erp-console/shared/lib/features.ts` `AI_FEATURES_ENABLED` (build). 12 file đọc trực tiếp (GuidancePanel, escalation.ts, GuidanceEscalate, ConfirmationAiBlock, AuditLogScreen, AiDocBlockGate, AiProposalsRow, Shell, AiBlockFrame, DetailPage, AiFeatureGuard, nav.ts) |
| Bước guidance "AI soạn nháp…" | BE **đã** trả `step.ai = null` khi `AI_ENABLED=False` (`common/guidance/steps.py:47`). Chữ chỉ lộ khi BE bật mà FE tắt. FE đã chặn bằng cờ build. Lô này chỉ thêm test BE khoá hành vi |
| Dòng AI ở dòng thời gian | 7 nơi dựng từ `AuditLog` mà **không** lọc: `common/guidance/audit_timeline.py:164`, `sales/orders/timeline.py:93`, `sales/payments/timeline.py:40`, `sales/refunds/timeline.py:42`, `inventory/batches/timeline.py:84`, `inventory/stocktake/services.py:111`, cộng cột "người sửa gần nhất" ở `inventory/stocktake/queries.py:34-35` + `serializers.py:176` |
| W1 | Shop lấy `order.get_status_display()` ở `sales/orders/shop_api.py:85` → "Tự huỷ (quá TTL)" từ choices model |
| W2 | BE đã gửi `delivery.status_label` (`shop_api.py:89-97`), FE `frontend/app/shop/orders/OrderLookup.tsx:231` in `delivery.status` |
| `cancel_note` / `decision_note` | BE đã trả (`SalesOrderDetailSerializer.cancel_note`, che theo `pii_hidden`; `confirmation/serializers.py:237` theo `in_scope`). FE chưa hiện |
| Code chết | `shared/ui/StatusChip.tsx` + `shared/lib/status.ts` (chỉ StatusChip import), `shared/ui/RightRail.tsx`, `shared/ui/AiBar.tsx`: không file sản phẩm nào import. **Ngoại lệ**: `erp-console/e2e/qa_harness_ed_batch1/main.tsx:9` import `AiBar` và nằm trong `tsconfig include` → xoá AiBar mà không sửa harness thì `tsc --noEmit` đỏ |

## 1. Kiến trúc: một cờ AI (W39)

**Nguồn thật:** `settings.AI_ENABLED` (cờ môi trường). **Không** dùng `is_ai_enabled()`: nó gồm cả công tắc tắt khẩn của Chủ;
nếu dùng nó để ẩn giao diện thì Chủ tắt khẩn xong sẽ mất luôn màn cài đặt AI để bật lại. Tắt khẩn giữ hành vi cũ (qua `/api/ai/status/`).

**BE** thêm `backend/apps/common/ai_visibility.py` (một chỗ duy nhất):
- `ai_features_enabled() -> bool` = `bool(getattr(settings, "AI_ENABLED", False))`.
- `exclude_ai_audit_rows(qs)` = chuyển nguyên thân `exclude_ai_rows` hiện có sang đây (cùng điều kiện: ẩn `actor_kind="ai"` và `actor_kind="system"` có `proposal_ref`). `accounts/audit/serializers.py` giữ tên `exclude_ai_rows` = import lại từ đây (không đổi test TL-D3-L4).
- Mọi chỗ khác trong BE muốn ẩn/hiện theo AI **chỉ** gọi hai hàm này, không đọc `settings.AI_ENABLED` rải rác (code mới).

**FE ERP:** hiện AI khi và chỉ khi **cờ build bật VÀ BE báo bật**:
```
aiVisible(me) = AI_FEATURES_ENABLED && me?.ai_features_enabled === true
```
- Đặt ở `shared/lib/features.ts`, nhận kiểu tối thiểu `{ ai_features_enabled?: boolean } | null` (giống cách `nav.ts` khai `NavMe`, để `shared/` không phụ thuộc `features/auth`).
- `AI_FEATURES_ENABLED` **phải đứng đầu** biểu thức `&&` để bundler gấp hằng `false` và bỏ chunk AI → `scripts/check-ai-chunks.mjs` vẫn xanh.
- Chưa tải xong `me` → `false` (không nháy giao diện AI).
- 12 file nêu ở mục 0 đổi từ `AI_FEATURES_ENABLED` sang `aiVisible(me)` (lấy `me` từ `useAuth()` hoặc từ tham số `visible(me)` sẵn có ở `nav.ts`). Sau lô, chỉ `features.ts` được import `AI_FEATURES_ENABLED` (test grep ở mục 5).
- Mock (`features/auth/mock.ts`): `ai_features_enabled: true` để bản mock vẫn chỉ phụ thuộc cờ build như trước (không phá các script QA cũ).

Shop (`frontend/`) không có chữ AI, không đổi cờ.

## 2. Contract BE ↔ FE

### 2.1 `GET /api/auth/me/` (authenticated, mọi user đăng nhập) — chỉ THÊM key
```json
{
  "...": "các key S6/S47/S48 giữ nguyên",
  "ai_features_enabled": false,
  "capabilities": [ {"code": "accounts.manage_staff", "label": "Quản lý nhân viên"} ]
}
```
- `ai_features_enabled` = `ai_features_enabled()`. Không lộ thông tin nhạy cảm (một boolean cấu hình).
- Khi `false`: `capabilities` bỏ mọi code bắt đầu `ai.` (A2: "Quản lý chính sách AI"). `permissions` (mã thô, FE không hiển thị) **giữ nguyên** — không đổi dữ liệu phân quyền Tầng 1/2.
- Khi `true`: như hiện tại.

Lý do không dùng `/api/ai/status/`: nghĩa khác (gồm tắt khẩn), thêm một request mỗi lần vào console, và nằm trong `apps/ai` mà FE tắt cờ không được gọi.

### 2.2 Ma trận phân quyền (A1) — `GET /api/staff/groups/`, `GET /api/staff/groups/<code>/`, `PUT /api/staff/groups/<code>/capabilities/` (quyền như cũ: chỉ Chủ ghi)
Khi `ai_features_enabled()` = false:
- `registry` (chi tiết nhóm) không có phần tử `key="ai_policy"`.
- `capabilities` (dict trạng thái ở danh sách và chi tiết) không có khoá `ai_policy`.
- `timeline` của nhóm bỏ sự kiện `change_group_capabilities` mà **mọi** khoá đổi đều là việc AI; sự kiện có lẫn khoá khác thì đếm/nhãn chỉ tính khoá không AI.
- `PUT` có khoá `ai_policy` → 400 `INPUT_NOT_ALLOWED` ("Có việc không nằm trong danh sách phân quyền."), dữ liệu không đổi.
Khi bật: như hiện tại.

Cách làm BE: `registry.py` thêm `AI_CAPABILITY_KEYS = frozenset({"ai_policy"})` và `visible_capabilities()` (lọc theo `ai_features_enabled()`); `services.py` dùng `visible_capabilities()` ở `capability_states`, `describe_group.registry`, `_validate_changes`, `_capability_events`/`capability_change_label`. `CAPABILITIES`/`BY_KEY` giữ nguyên (test "perms rời nhau" và `_check_requires` không đổi). **Không** đổi permission đang gán của nhóm nào.

FE không cần sửa `features/permissions/**`: màn đã vẽ theo `registry` từ BE.

### 2.3 Dòng thời gian chi tiết (A6–A8) — các endpoint chi tiết sẵn có, không đổi shape
Khi tắt: mọi `timeline[]` không còn phần tử có `actor.kind == "ai"` và không còn dòng Hệ thống có `proposal_ref`. Lọc **trên queryset trước khi cắt `limit`** (để `truncated` và số dòng vẫn đúng). Áp ở 6 builder + cột "người sửa gần nhất" của kiểm kê:
- `stocktake/queries.py`: subquery `latest` dùng cùng bộ lọc → khi tắt, "người sửa gần nhất" là dòng không-AI gần nhất.
- `stocktake/serializers.py:176`: nhánh "AI của …" chỉ chạy khi bật; khi tắt mà vẫn rơi vào nhánh (dữ liệu lệch) thì trả `SYSTEM_NAME`.
Khi bật: như hiện tại (FE bỏ chip "AI" lặp, xem 3.2).

### 2.4 Shop tra đơn `GET /api/shop/orders/<order_code>/?phone_last4=` (AllowAny, throttle như cũ) — W1, W2
Chỉ đổi chuỗi `status_label` / `delivery.status_label`; không thêm field, không đổi xác minh, không thêm dữ liệu cá nhân.

| Mã | `status_label` (Shop) |
|---|---|
| `SalesOrder` AUTO_CANCELLED (T2) | Đã huỷ vì quá giờ thanh toán |
| Các trạng thái đơn khác | giữ như hiện tại (gồm "Đã thanh toán – chờ vựa gọi xác nhận") |

| `delivery.status` (T24–T30, cột Shop) | `delivery.status_label` |
|---|---|
| CONFIRMING | Chờ vựa gọi xác nhận |
| PREPARING | Đang soạn hàng |
| READY | Đã soạn xong, chờ giao |
| DELIVERING | Đang giao |
| COMPLETED | Đã giao |
| FAILED | Giao chưa thành công, vựa sẽ liên hệ lại |
| CANCELLED | Đã huỷ |
| mã lạ (tương lai) | "Đang cập nhật" (không bao giờ trả mã thô) |

BE đặt hai bảng hằng `SHOP_ORDER_STATUS_LABELS` (chỉ ghi đè AUTO_CANCELLED) và `SHOP_DELIVERY_STATUS_LABELS` trong `sales/orders/shop_api.py` (hoặc file `shop_labels.py` cạnh nó). **Không** sửa `choices` của model: tránh migration, và tên chuẩn ERP (T2 "Hết giờ giữ chỗ") còn chờ Duy duyệt mục 4 Q-2. Khi Duy duyệt mục 4, chỉ sửa hai bảng này.

FE Shop: `OrderLookup.tsx:231` in `result.delivery.status_label`; không có thì "Đang cập nhật". Không render `status` thô ở bất cứ đâu trên trang tra đơn.

### 2.5 Ghi chú huỷ đơn và lý do quyết định (nợ TL-D3-L4) — endpoint sẵn có, BE không đổi
- `POST /api/orders/<id>/cancel/` (`cancel_paid_order`): `note` ≤ 200, không chuỗi số dài. Lỗi: 400 `{"detail": "...", "code": "BR-GH-19"}`.
- Quyết định CSKH CANCEL (`DecideModal`): lý do ≤ 200, lỗi 400 `code: "BR-GH-19"` như trên.
- Đọc: `GET /api/orders/<id>/` → `cancel_note: string` (rỗng khi không có hoặc bị che `pii_hidden`); chi tiết hàng chờ xác nhận → `decision_note: string` (rỗng khi ngoài phạm vi).

FE:
- `CancelOrderModal.tsx:78` `maxLength` 500 → 200 (hằng `CANCEL_NOTE_MAX = 200` trong `features/orders`, có `counter`).
- Lỗi 400 `code === "BR-GH-19"`: hiện `detail` **dưới ô ghi chú**, giữ hộp mở, quay về bước form (bỏ bước xác nhận), giữ nguyên chữ đã gõ. Lỗi khác giữ luồng cũ.
- `DecideModal` (CANCEL và mọi quyết định có lý do): cùng cách xử lý `BR-GH-19` → `errors.reason`, `setConfirmingCancel(false)`.
- Chi tiết đơn: dòng "Ghi chú huỷ" khi `cancel_note.trim() !== ""`. Chi tiết hàng chờ: dòng "Lý do quyết định" khi `decision_note.trim() !== ""`. Rỗng thì không vẽ dòng. Chữ hiển thị qua text node (không `dangerouslySetInnerHTML`).

## 3. Phạm vi ẩn chữ AI ở FE (khi `!aiVisible(me)`)

### 3.1 Theo bảng A
| # | File | Việc |
|---|---|---|
| A1, A2 | — | BE lo (2.1, 2.2). FE không sửa |
| A3–A5 | — | Đã xong ở TL-D3-L4 cho dòng do AI làm. Dòng `ai_config_*`/`ai_policy_*`/`confirm_*` do **người** làm vẫn giữ theo TL-D3-L4 (vết kiểm toán). Xem câu hỏi Q1 |
| A6–A8 | — | BE lo (2.3) |
| A9 | `features/content/components/ContentListScreen.tsx:116` | bỏ cột "AI" khỏi mảng cột |
| A10 | cùng file | chip `entrySource.ai` không vẽ (hệ quả của A9); `enums.ts` giữ nguyên |
| A11 | `features/content/contentModel.ts:374` | nhận `aiOn` (tham số) — tắt thì không trả `noteAiDraft` |
| A12 | `shared/ui/detail/DetailPage.tsx:30` | `aria-label` = "Trợ lý và lịch sử" khi có `aiSlot`, ngược lại "Lịch sử" |
| A13, A14, A17 | — | để nguyên (Django admin superuser; dev-patterns 404 ở bản thật) |
| A15 | `shared/lib/nav.ts:441` | đổi `summary` thành "Mọi thay đổi trong hệ thống." |
| A16 | xoá `shared/ui/RightRail.tsx`, `shared/ui/AiBar.tsx`, `shared/ui/StatusChip.tsx`, `shared/lib/status.ts` | **Chỉ xoá sau khi `grep -rn` lại không còn import** (ngoài comment). Sửa kèm: `e2e/qa_harness_ed_batch1/main.tsx` (bỏ `AiBar`, truyền `aiBar={null}`), comment ở `shared/ui/list/ListPage.tsx:3,19`, `features/ai/components/AiAssistantGate.tsx:5`, `erp-console/README.md:46-47`. Nếu có `.module.css` riêng của 4 file thì xoá cùng |
| Guidance | `GuidancePanel.tsx:44,165,180`, `GuidanceEscalate.tsx`, `escalation.ts` | đổi sang `aiVisible(me)`. BE đã trả `ai=null` khi tắt |
| Nhật ký | `AuditLogScreen.tsx:95,128,165` | đổi sang `aiVisible(me)` (lựa chọn lọc "AI", thao tác AI, cột "Đề xuất") |

### 3.2 Khi bật (dọn chữ lặp)
`shared/ui/detail/Timeline.tsx:51` và `GuidancePanel.tsx:260`: bỏ chip "AI" riêng vì `who` từ BE đã là "AI của <tên>" (hết "AI AI của …"). Không đổi BE.

## 4. Danh sách file — tách để chạy song song

### BE (`be-dev`)
Được sửa:
- MỚI `backend/apps/common/ai_visibility.py` (+ `apps/common/tests/test_ai_visibility.py`)
- `backend/apps/accounts/audit/serializers.py` (chỉ chuyển thân `exclude_ai_rows` sang `ai_visibility`, giữ tên export)
- `backend/apps/accounts/auth/services.py` (`describe_user`)
- `backend/apps/accounts/capabilities/registry.py`, `backend/apps/accounts/capabilities/services.py` (chỉ các hàm nêu ở 2.2)
- `backend/apps/common/guidance/audit_timeline.py`
- `backend/apps/sales/orders/timeline.py`, `backend/apps/sales/payments/timeline.py`, `backend/apps/sales/refunds/timeline.py`
- `backend/apps/inventory/batches/timeline.py`, `backend/apps/inventory/stocktake/services.py`, `backend/apps/inventory/stocktake/queries.py`, `backend/apps/inventory/stocktake/serializers.py`
- `backend/apps/sales/orders/shop_api.py` (+ có thể MỚI `backend/apps/sales/orders/shop_labels.py`)
- test trong `tests/` của các module trên; README module nếu mô tả hành vi đổi
Không được đụng: `apps/*/models/**`, mọi `migrations/`, `apps/ai/**`, `config/settings.py`, `apps/common/guidance/steps.py` (chỉ thêm test), `apps/accounts/capabilities/scope*`/phần phạm vi dữ liệu (Lô F1).

### FE (`fe-dev`)
Được sửa — `erp-console/`:
- `shared/lib/features.ts`, `features/auth/types.ts`, `features/auth/mock.ts`
- 12 file đọc cờ: `features/guidance/components/GuidancePanel.tsx`, `features/guidance/escalation.ts`, `features/guidance/components/GuidanceEscalate.tsx`, `features/confirmation/components/ConfirmationAiBlock.tsx`, `features/audit/components/AuditLogScreen.tsx`, `features/ai/components/AiDocBlockGate.tsx`, `features/overview/components/AiProposalsRow.tsx`, `shared/ui/shell/Shell.tsx`, `shared/ui/detail/AiBlockFrame.tsx`, `shared/ui/detail/DetailPage.tsx`, `shared/ui/states/AiFeatureGuard.tsx`, `shared/lib/nav.ts`
- `features/content/components/ContentListScreen.tsx`, `features/content/contentModel.ts`
- `shared/ui/detail/Timeline.tsx`
- xoá 4 file A16 + `e2e/qa_harness_ed_batch1/main.tsx`, `shared/ui/list/ListPage.tsx` (comment), `features/ai/components/AiAssistantGate.tsx` (comment), `README.md`
- `features/orders/components/CancelOrderModal.tsx`, màn chi tiết đơn trong `features/orders/components/`, `features/orders/types.ts`, `features/orders/mock.ts`
- `features/confirmation/components/DecideModal.tsx`, `features/confirmation/components/ConfirmationDetailScreen.tsx`, `features/confirmation/types.ts`, `features/confirmation/mock.ts`
- test vitest tương ứng (`*.test.ts`)

Được sửa — `frontend/`: `app/shop/orders/OrderLookup.tsx`, `lib/types.ts`, `lib/mock.ts` (nhánh `fix/shop-lien-he` cũng sửa `lib/mock.ts` — ai merge sau thì rebase, khác vùng).

Không được đụng: `erp-console/features/permissions/**` (Lô F1). Hệ quả: `features/permissions/mock.ts:57` vẫn có `ai_policy` ở **bản mock** — chấp nhận, ghi nợ, dọn sau khi F1 merge. E2E chạy BE thật nên không bị ảnh hưởng. Không đụng `features/ai/**` ngoài 2 file nêu trên, `shared/lib/enums.ts`, `features/audit/auditModel.ts`.

FE mock theo contract 2.1 (thêm `ai_features_enabled`) và 2.4 (bảng nhãn) — không chờ BE.

## 5. Test bắt buộc

### BE (Django TestCase, `override_settings(AI_ENABLED=...)` cả hai nhánh)
1. `/api/auth/me/`: Chủ, tắt → `ai_features_enabled=false`, không có `ai.manage_ai_policy` trong `capabilities` nhưng còn trong `permissions`; bật → có cả hai. 401 khi chưa đăng nhập.
2. Ma trận: tắt → list/detail không có `ai_policy` ở `registry`/`capabilities`; PUT `{"ai_policy": false}` → 400 `INPUT_NOT_ALLOWED`, permission nhóm không đổi; bật → như cũ. Manager → 403 như cũ.
3. Mỗi builder timeline (6) + `/api/audit-logs/`: seed 1 dòng người, 1 dòng `actor_kind="ai"`, 1 dòng Hệ thống có `proposal_ref` → tắt chỉ còn dòng người, không chuỗi "AI của"; bật đủ 3. Một ca `limit` nhỏ: dòng AI không chiếm chỗ của dòng người.
4. Kiểm kê: dòng mới nhất là AI → tắt thì "người sửa gần nhất" là người trước đó.
5. Guidance: tắt → mọi `next_steps[].ai` là `null` (khoá hành vi `steps.py:47`).
6. Shop lookup: AUTO_CANCELLED → "Đã huỷ vì quá giờ thanh toán"; 7 trạng thái phiếu giao → đúng bảng 2.4; với mọi ca `status_label != status` và không khớp `^[A-Z_]+$`. Không thêm key mới (so tập key response với trước).
7. `makemigrations --check --dry-run` sạch; `python3 scripts/check_naming.py` OK.

### FE
- vitest: `aiVisible` 4 tổ hợp (build × BE) + `me=null`; `contentModel` không trả "AI soạn nháp" khi tắt; xử lý `BR-GH-19` trong 2 hộp thoại; test grep: ngoài `shared/lib/features.ts` không file nào import `AI_FEATURES_ENABLED`.
- `tsc --noEmit`, `npm run build`, `node scripts/check-ai-chunks.mjs` (cờ tắt: 0 chunk AI) ở `erp-console/`; `npm run build` ở `frontend/`; `npm ci` sạch.

### E2E (QA, Playwright Python, dữ liệu giả, BE thật chạy local)
**E1 — quét chữ AI toàn bộ route ERP** (`erp-console/e2e/ai_text_hidden_all_routes.py`):
- Seed giả: 1 bài `source=ai` nháp, dòng `AuditLog` `actor_kind=ai` và Hệ thống có `proposal_ref` gắn trên đơn, khoản tiền, phiếu hoàn, lô, phiếu kiểm kê, phiếu nhập.
- Ma trận 3 cấu hình: (BE tắt, FE tắt), (**BE tắt, FE bật** — ca W39), (BE bật, FE tắt). Đăng nhập Chủ (thấy nhiều route nhất) và Quản lý.
- Duyệt mọi route trong `nav.ts` có `href` + trang chi tiết của từng loại chứng từ seed + `/account/` + `/permissions/` (chi tiết nhóm `manager`) + mở menu avatar + mở các bộ lọc Nhật ký và Nội dung.
- Assert: `document.body.innerText` và mọi `aria-label`/`title`/`placeholder` không khớp `/\bAI\b/`. Ngoại lệ duy nhất: dòng Nhật ký có `action` bắt đầu `ai_config_`/`ai_policy_` do người làm (giữ theo TL-D3-L4) — seed của E1 **không** tạo dòng này, nên thực tế 0 ngoại lệ. `/ai/*` → màn "Không tìm thấy trang này". Network: không request nào tới `/api/ai/`.
- Ca đối chứng (BE bật, FE bật): có chữ AI ở menu và dòng thời gian (chứng minh script không quét rỗng).

**E2 — Shop tra đơn không mã thô** (`frontend/e2e/`): 8 đơn giả (AUTO_CANCELLED + đơn có phiếu giao ở 7 trạng thái). Assert nhãn đúng bảng 2.4 và trang không chứa `/\b(BOOKED|PAID|PROCESSING|COMPLETED|CANCELLED|AUTO_CANCELLED|CONFIRMING|PREPARING|READY|DELIVERING|FAILED)\b/`, không chữ "TTL".

**E3 — ghi chú:** hộp huỷ đơn không gõ quá 200 ký tự; ghi chú có dãy số dài → lỗi hiện dưới ô, hộp vẫn mở, chữ còn nguyên, đơn chưa huỷ; sửa lại → huỷ được và chi tiết đơn hiện "Ghi chú huỷ". Cùng kịch bản với CSKH CANCEL và `decision_note`. Ca ghi chú rỗng → không có dòng.

## 6. Rủi ro và cơ chế chặn

| Rủi ro | Chặn | Test bắt |
|---|---|---|
| Rò giá vốn | Không đụng serializer có giá vốn; timeline chỉ bỏ dòng, không thêm field | BE test 3 so tập key response trước/sau |
| Rò dữ liệu cá nhân (bất biến 9) | Shop lookup chỉ đổi chuỗi nhãn, không thêm key. `cancel_note`/`decision_note` đã được BE che theo `pii_hidden`/`in_scope` — FE chỉ hiện chuỗi BE trả, không log, không đưa vào URL/localStorage. Seed e2e dùng dữ liệu giả | BE test 6 (tập key), e2e E3 với user ngoài phạm vi thấy rỗng |
| Vượt phân quyền | Không đổi permission đang gán; `permissions` của `/me` giữ nguyên; PUT `ai_policy` khi tắt bị từ chối (không mở đường bật việc owner-only) | BE test 1, 2 |
| Mất vết kiểm toán | Chỉ **ẩn khi đọc**, không xoá `AuditLog` (append-only); bật cờ là hiện lại đủ | BE test 3 nhánh bật |
| Chủ tắt khẩn mất màn bật lại | Cờ giao diện dùng `AI_ENABLED` env, không dùng `is_ai_enabled()` | BE test 1 với `global_mode=off` + `AI_ENABLED=True` → `ai_features_enabled=true` |
| Bundle AI lọt vào bản tắt | `AI_FEATURES_ENABLED` đứng đầu `&&` | `check-ai-chunks.mjs` |
| Xoá code chết làm đỏ tsc | sửa harness e2e cùng lúc | `tsc --noEmit` |
| Timeline cắt sai khi lọc sau `limit` | lọc trên queryset trước slice | BE test 3 ca limit |
| Đụng Lô F1 | FE không sửa `features/permissions/**`; BE chỉ sửa hàm nêu ở 2.2 trong `capabilities/services.py` | điều phối viên kiểm diff path |
| Đổi tên chuẩn sau khi Duy duyệt mục 4 | Nhãn Shop gom ở 2 bảng hằng | — |

## 7. Thứ tự và lô

Một lô, BE ∥ FE chạy song song (FE mock theo 2.1, 2.4):
- **BE**: `ai_visibility` → `/me` → ma trận → 6 timeline + kiểm kê → shop lookup → test.
- **FE**: `aiVisible` + 12 file → Nội dung/aria/nav/Timeline → xoá code chết → Shop OrderLookup → nợ ghi chú.
- QA chạy E1–E3 trên BE thật sau khi cả hai xong; techlead review diff.

## 8. Câu hỏi

- 🔴 **Q1 (Duy, không chặn lô):** khi AI tắt, dòng Nhật ký do **Chủ** đổi cài đặt/chính sách AI (`ai_config_*`, `ai_policy_*`, nhãn "Đổi cài đặt AI", "Đổi chính sách AI") hiện đang **giữ** theo TL-D3-L4 vì là vết kiểm toán. Mặc định lô này giữ nguyên (chỉ hiện khi đã từng có người đổi cài đặt AI — môi trường chưa bật AI thì không có dòng nào). Nếu Duy muốn ẩn hẳn thì thêm điều kiện `action__startswith="ai_"` vào `exclude_ai_audit_rows`, một dòng.
- Không có câu hỏi kỹ thuật khác.

## 9. Review
(chờ)
