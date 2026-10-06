# Lô dọn chữ AI — review của Tech Lead

## Review FE (07/10)

Phạm vi: nhánh `feat/don-chu-ai-fe`, commit `84a7346`, diff `7fa314d..HEAD` (53 file). So với `02b-tech-design.md` mục 1, 2.4, 2.5, 3, 4 và 5 (phần FE).
Đã chạy: `python3 scripts/check_naming.py` cho kết quả OK, không phát sinh vi phạm mới. Không chạy vitest, tsc hay build vì worktree chưa có `node_modules` và điều phối viên đang build. Số `check-no-mock` / `check-ai-chunks` lấy theo lượt build của điều phối viên.

**Kết luận: APPROVED.** Không có lỗi Critical/High/Medium. Có 3 việc Low nên dọn ở lô sau hoặc làm kèm khi sửa lại (không chặn merge).

### Đối chiếu từng điểm

| Điểm soát | Kết quả |
|---|---|
| `aiVisible(me)` | `shared/lib/features.ts:16-18` có `AI_FEATURES_ENABLED && me?.ai_features_enabled === true`, nên cờ build đứng đầu. `me` null, undefined hoặc thiếu key đều cho `false`. Kiểu tối thiểu `AiVisibleMe` khai ở `shared/`, đúng 02b mục 1. Test 4 tổ hợp cùng `me=null` có ở `features.test.ts`. |
| Không còn import cờ rời rạc | Grep cả `erp-console`: ngoài `features.ts`, chỉ còn 2 file test (`aiFeatures.on/off.test.ts`) nhắc tới `AI_FEATURES_ENABLED`. Test grep ở `features.test.ts:43-49` khoá luật này và bỏ qua `*.test.ts`, `e2e/`. Đạt. |
| 12 file đọc cờ | Đủ 12 file. Ở `AiDocBlockGate` và `ConfirmationAiBlock`, effect phụ thuộc `[visible]`, khi tắt thì không gọi `/api/ai/status/`. `escalatableStep(data, me)` đổi chữ ký. `BatchDetailScreen`, `OrderDetailScreen` là chỗ gọi, đã sửa theo (tsc bắt nếu sót). `nav.ts` cả 4 mục AI đều qua `aiVisible`. |
| Màn Nội dung | `ContentListScreen.tsx:118` bỏ cột "AI" khi tắt. `entryNote(row, aiOn)` (`contentModel.ts:372-377`) có test nhánh tắt. Đúng A9–A11. |
| Timeline / GuidancePanel | Đã bỏ chip "AI" lặp (`Timeline.tsx`, `GuidancePanel.tsx` dòng thời gian). Hai badge "AI (mức)" ở bước tiếp theo và "Để AI làm" vẫn còn và nằm sau `aiVisible`. `DetailPage` có aria-label "Lịch sử" khi không có khe AI. Khe AI bị bỏ ở `DetailPage` khi tắt, đúng ý: `aiSlot` là một element nên `Boolean()` luôn true dù bên trong trả null. |
| Xoá 4 file chết | Đã xoá `RightRail.tsx`, `AiBar.tsx`, `StatusChip.tsx`, `status.ts`. Grep lại không còn import hay nhắc tên ở code, CSS hay README. Harness batch1 đã sửa (`aiBar={null}`). Các file này không có `.module.css` riêng. |
| Ghi chú huỷ BR-GH-19 | `CANCEL_NOTE_MAX = 200` (`orders/labels.ts`) cùng `counter`. 400 kèm `code === "BR-GH-19"` thì lỗi hiện dưới ô, `setStep("form")`, chữ đã gõ còn nguyên (state `note` không bị reset). Lỗi khác vẫn `throw` về luồng `useSubmit` cũ. `onSuccess` bỏ qua `null`. |
| Lý do quyết định BR-GH-19 | `DecideModal.tsx:51-71` dùng cùng cách: `errors.reason` + `setConfirmingCancel(false)` rồi trả `null`. |
| Hiện `cancel_note` / `decision_note` | Chỉ vẽ khi `trim() !== ""` (`OrderDetailScreen.tsx:305`, `ConfirmationDetailScreen.tsx:315`). Chữ đi qua `InfoField` (text node), không dùng `dangerouslySetInnerHTML`. Mock che theo `piiHidden` / `in_scope` giống BE. |
| Shop `status_label` | `OrderLookup.tsx:231` in `delivery.status_label || "Đang cập nhật"`. Không còn chỗ nào render `status` thô. Mock: bảng nhãn khớp 02b mục 2.4, mã lạ cho "Đang cập nhật", đơn DH-DEMO005..009 dùng SĐT giả. |
| Đổi id `seller-info` | Hai chỗ dùng (`ContactButton.tsx:6`, `SiteLegalFooter.tsx:60`) đều đã đổi. Không còn `href="#thong-tin-nguoi-ban"` nào trong code. Slug trang `thong-tin-nguoi-ban` ở `content/mock.ts` là URL nội dung, không phải id, giữ nguyên là đúng. |
| Mock không lọt bản thật | Khoá `caveve_mock_be_ai` chỉ nằm trong `features/auth/mock.ts`. `features.ts` không đọc storage. Bản thật lấy cờ từ `/api/auth/me/`. Lượt build của điều phối viên vẫn phải cho `check-no-mock` xanh. |
| Không đụng `features/permissions/**` | Diff không có file nào trong `features/permissions/`. Nợ `ai_policy` ở `features/permissions/mock.ts` đã ghi trong dev-notes, E1 bản mock in dòng "NỢ" rồi bỏ qua. |
| Dữ liệu cá nhân | Không thêm `console.*`. Không đưa ghi chú vào URL hay localStorage. Khoá `localStorage` mock Shop đổi `v2` thành `v3`, chỉ chứa đơn giả. SĐT trong e2e và mock là số giả (`0901234567`, `09090050xx`). Không thêm field cá nhân. Đạt bất biến 9. |
| Giá vốn / phân quyền | Không đụng serializer, không đổi luật quyền. `permissions` không bị lọc ở FE. |

### Hai bổ sung ngoài contract

1. **FE tự lọc dòng AI ở Nhật ký** (`AuditLogScreen.tsx:83-87`): **chấp nhận.**
   - Chỉ khác kết quả trong cấu hình BE `AI_ENABLED=1` và FE build không có `NEXT_PUBLIC_AI_FEATURES`. Theo `doc/ops/moi-truong.md`, cả staging và production hiện đều tắt hai cờ. Khi đó BE đã lọc (`exclude_ai_rows`), nên bộ lọc FE không có tác dụng gì.
   - Ở cấu hình lệch: `count` và phân trang vẫn tính cả dòng AI. Phần tóm tắt ghi "Đang hiện n / N", nút "Tải thêm" vẫn theo `hasMore`. Cách này giống hệt cách lọc cục bộ đang có (`matchesLocal`), nên người dùng không bị mất dữ liệu người làm. Con số N chỉ lộ số lượng dòng, không lộ nội dung AI.
   - Nếu không lọc ở FE thì trong cấu hình đó, chữ "AI của …" sẽ hiện ra, trái mục tiêu W39. Lỗi nhỏ về đếm là cái giá chấp nhận được.
   - Cách sạch hơn để sau (không làm ở lô này): FE gửi thêm tham số `exclude_ai=1` để BE lọc trước khi phân trang. Việc này cần đổi contract `/api/audit-logs/`, chỉ làm khi Duy định bật AI ở BE trước FE.
2. **Tiêu đề topbar `/ai/*`** (`Shell.tsx:91-93`): **chấp nhận.**
   - Khi AI tắt, `AiFeatureGuard` hiện "Không tìm thấy trang này", nhưng topbar vẫn lấy tên mục từ `navMatch(pathname)`, chẳng hạn "Chính sách AI". Như vậy là lộ chữ AI và trái AC của E1.
   - Điều kiện `key.startsWith("ai-")` khớp đúng 4 mục (`ai-policy`, `ai-report`, `ai-settings`, `ai-actions`), không có mục nào khác bắt đầu bằng `ai-`.
   - Góp ý (không bắt buộc): thêm cờ `ai: true` vào 4 `NavItem` thay cho so tiền tố chuỗi, để sau này đặt key mới không vô tình bị khớp.

### Việc Low (không chặn, dọn ở lô sau)

- **L1. Harness QA batch2 sẽ sập lúc chạy.** `shared/ui/detail/DetailPage.tsx:22` giờ gọi `useAuth()`. Hàm này throw khi không có `<AuthProvider>` (`features/auth/components/AuthProvider.tsx:272`). Trong khi đó `e2e/qa_harness_ed_batch2/main.tsx:61,90,109,119` render `DetailPage` mà không bọc provider, và vite config không alias stub auth. tsc không bắt được lỗi này. Sửa: bọc harness bằng một provider giả có `me = { ai_features_enabled: true }`, hoặc thêm alias stub `AuthProvider` vào `e2e/qa_harness_ed_batch2/vite.config.mjs`. Sản phẩm không bị ảnh hưởng vì `app/layout.tsx:51` bọc toàn app.
- **L2. Code chết sau khi bỏ chip AI.** Còn sót:
  - prop `byAi` cùng comment cũ "AI làm → nhãn AI cạnh tên" ở `shared/ui/detail/Timeline.tsx:13-15`
  - class `.ai` ở `shared/ui/detail/Timeline.module.css:9`
  - `byAi` vẫn được gán ở `features/guidance/detailAdapters.ts:14`, kèm test `detailAdapters.test.ts:17-18`

  Không còn nơi nào đọc các chỗ này, nên bỏ cả ba.
- **L3. `OrderDetailScreen.tsx:126` đọc cờ trực tiếp.** Dòng này đọc thẳng `me?.ai_features_enabled` và đặt tên biến là `aiOn`. Kết quả vẫn đúng vì `escalatableStep` gọi `aiVisible`, nhưng tên biến dễ hiểu nhầm thành "AI đang hiện". Đề xuất đổi tên thành `beAiEnabled`, hoặc truyền `me` rồi để effect phụ thuộc `me?.ai_features_enabled`.

### Ghi nhận (không phải lỗi của lô)

- `DetailPage` và `AiBlockFrame` trong `shared/ui/detail/` giờ import `features/auth`, tức `shared` phụ thuộc vào một module. Đã có tiền lệ là `shared/ui/states/AiFeatureGuard.tsx`. Chấp nhận, vì truyền `me` qua props cho hơn 15 màn chi tiết thì tốn công hơn nhiều.
- Lô này không mount `features/ai/components/AiAssistantGate.tsx` ở đâu (đã như vậy từ trước). Thư mục `features/ai/**` nằm ngoài phạm vi lô, nên chưa xử lý ở đây.
- E1 và E3 mới chạy trên mock. E1 trên BE thật, có ma trận (BE tắt, FE bật) và `/permissions/` phải sạch, là việc của QA sau khi merge BE.

---

# Lô dọn chữ AI: review của Tech Lead

## Review BE (07/10)

Phạm vi: nhánh `feat/don-chu-ai-be`, commit `2ba0df9`, diff `7fa314d..2ba0df9` (28 file, chỉ `backend/` và `03-dev-notes.md`).
Đối chiếu với `02b-tech-design.md` mục 1, 2.1 đến 2.4, 4, 5 và 6.

**Kết luận: APPROVED.** Không có lỗi chặn. Có 3 việc nợ mức Low (N1 đến N3), sửa cùng nhánh trước QA hoặc ghi nợ đều được.

### Lệnh kiểm chứng đã chạy (trong worktree, lượt này)

| Lệnh | Kết quả |
|---|---|
| `manage.py test` (toàn bộ, dùng `.env` dev của repo chính, đã `collectstatic` vào `backend/staticfiles/` vốn đã nằm trong gitignore) | **3054 test OK** |
| `manage.py makemigrations --check --dry-run` | `No changes detected` |
| `git diff 7fa314d..HEAD --stat -- backend/apps/ai backend/apps/*/models backend/apps/*/migrations backend/config` | rỗng: không đụng models, migrations, `apps/ai/**`, settings |
| `python3 scripts/check_naming.py` | 0 vi phạm ở `backend/`. Exit 1 do `frontend/components/ContactButton.tsx` và `SiteLegalFooter.tsx` (`thong-tin-nguoi-ban`). Lỗi này có sẵn trên main từ nhánh `fix/shop-lien-he`, không thuộc lô này. Điều phối viên cần ghi nợ riêng |
| Test tạm (đã xoá, không commit) trên `/api/guidance/group/<id>/` khi AI tắt | tái hiện N1 |

Lần chạy đầu ra 33 lỗi, toàn ở test Django admin, do worktree thiếu manifest static (`Missing staticfiles manifest entry`). Đây là lỗi môi trường. Chạy `collectstatic` xong thì xanh hết.

### Soát theo yêu cầu

| Hạng mục | Kết quả | Chứng cứ |
|---|---|---|
| `/me` `ai_features_enabled` lấy từ `AI_ENABLED`, không theo công tắc tắt khẩn | Đạt | `common/ai_visibility.py:12-13` chỉ đọc `settings.AI_ENABLED`; `accounts/auth/services.py:105,127` |
| `capabilities` bỏ `ai.*`, `permissions` giữ nguyên | Đạt | `auth/services.py:124`; test `test_ai_features_flag.py` (bật, tắt, 401); hai test contract key thêm đúng 1 key |
| Ma trận: `registry` và `capabilities` bỏ `ai_policy`; PUT `ai_policy` trả 400 `INPUT_NOT_ALLOWED`, dữ liệu không đổi | Đạt | `capabilities/registry.py:97-113`, `services.py:61,254,279-281`. `_check_requires` vẫn duyệt đủ `CAPABILITIES`, không rủi ro vì `ai_policy` không có `requires`. Test: 400, quyền nhóm không đổi, không ghi `AuditLog`, Manager vẫn 403 |
| Timeline nhóm (`describe_group`) | Đạt | `services.py:196-198`: sự kiện chỉ có khoá AI thì không sinh dòng nào; sự kiện lẫn khoá thì chỉ tính khoá không AI. Có test hai nhánh |
| `exclude_ai_audit_rows` áp ở 5 builder và kiểm kê | Đạt | `common/guidance/audit_timeline.py:166`, `sales/orders/timeline.py:93`, `sales/payments/timeline.py:40`, `sales/refunds/timeline.py:42`, `inventory/batches/timeline.py:84`, `inventory/stocktake/services.py:111`, `inventory/stocktake/queries.py:24`, `stocktake/serializers.py:177-178`. Đã grep lại mọi `AuditLog.objects` ngoài `apps/ai`, không sót chỗ nào dựng dòng "AI của" |
| Lọc trước khi cắt `limit` | Đạt | `audit_timeline.py:166-169`: lọc trên queryset rồi mới `[: limit + 1]`. Subquery kiểm kê lọc trước `[:1]`. Bốn builder kia không cắt. Test `test_off_limit_applies_after_filter` kiểm cả `timeline_truncated` |
| `/api/audit-logs/` (TL-D3-L4) giữ hành vi | Đạt | `audit/serializers.py:56` là alias, `audit/api.py:51` không đổi |
| Nhãn Shop: không lộ dữ liệu, không thêm key | Đạt | `sales/orders/shop_labels.py`, `shop_api.py:86-94`: chỉ thay chuỗi. Test so tập key cấp trên và `delivery`, mã lạ ra "Đang cập nhật", không có SĐT hay tên trong response. Xác minh `phone_last4` và throttle không đổi |
| Giá vốn | Không đụng | Không serializer giá vốn nào trong diff |
| Dữ liệu cá nhân | Không rò | Không log mới; test chỉ dùng dữ liệu giả (`0900000456`, fixture có sẵn) |
| Chứng từ, append-only | Không đụng | Chỉ ẩn khi đọc. Có test xác nhận dòng AI vẫn còn trong DB |

### Bảy chỗ lệch hoặc giả định trong `03-dev-notes.md`: quyết định

| # | Nội dung | Quyết định |
|---|---|---|
| 1 | Phiếu giao CANCELLED ở Shop luôn là "Đã huỷ" (trước đây là "Đã huỷ theo đơn" khi đơn huỷ) | **Duyệt.** Đúng bảng 02b 2.4 (T30) |
| 2 | "6 builder" thực tế là 5 builder cộng `_last_editor_name` của kiểm kê | **Duyệt.** 02b đếm nhầm. Dòng thời gian guidance của phiếu kiểm kê đi qua `audit_timeline` nên đã được phủ |
| 3 | Dòng thời gian chi tiết đơn không có `actor_kind`, test khoá qua `build_timeline` | **Duyệt.** `SalesOrderDetailSerializer.get_timeline` gọi `build_timeline`, nên test ở tầng builder là đủ |
| 4 | Dòng nhật ký đổi quyền cũ có khoá `ai_policy` bị ẩn khi tắt | **Duyệt.** Đúng 02b 2.2. Riêng provider guidance `group` còn sót (N1) |
| 5 | Test nhãn Shop viết cùng lúc với code, không có bước RED riêng | **Chấp nhận.** Trên base `7fa314d`, AUTO_CANCELLED trả "Tự huỷ (quá TTL)" và READY, FAILED trả nhãn model, nên các assert hiện tại sẽ đỏ nếu chạy trên base. Test có giá trị |
| 6 | Q1: giữ dòng `ai_config_*`/`ai_policy_*` do Chủ làm | **Duyệt.** Đúng mặc định ở 02b mục 8, chờ Duy |
| 7 | Test cũ ghim `AI_ENABLED=True` (`test_s47` ac1, 3 class ở `capabilities`, `test_guidance` DW-03-AC4) | **Duyệt, kèm N3.** Xem phân tích độ phủ dưới đây |

### Ghim test cũ sang `AI_ENABLED=True`: có mất độ phủ nhánh tắt không

Mặc định `AI_ENABLED=0` (`config/settings.py:266`), và production cũng đang tắt. Trước lô này, các test kia chạy ở nhánh tắt nhưng không phụ thuộc cờ.

- `test_s47` ac1 (Chủ đủ việc) và `test_guidance` DW-03-AC4 (dòng "AI của"): nhánh tắt đã có test mới thay thế ở `test_ai_features_flag.py` và `orders/tests/test_ai_rows_hidden.py`. Không mất độ phủ.
- `GroupReadTests`, `RegistryRequiresTests`: nhánh tắt của tập khoá `capabilities` và `registry` đã có `test_ai_hidden.py`. Không mất độ phủ đáng kể.
- `PrivilegeEscalationTests`: **mất một phần.** Nhánh tắt không còn ca nào kiểm việc owner-only *không phải AI* (`view_cost`, `manage_staff`…) vẫn trả `BR-PQ-32` hoặc `GROUP_LOCKED`. Logic hiện tại không phụ thuộc cờ, nên chưa thành lỗi. Nhưng `_validate_changes` giờ có điều kiện theo cờ, nên sau này đổi thứ tự kiểm sẽ không có test bắt. Xem N3.

### Việc nợ (Low, không chặn)

**N1. Guidance nhóm hiện "Đổi quyền của nhóm (0 việc)" khi AI tắt.** `backend/apps/accounts/capabilities/services.py:265-271`.
Sự kiện `change_group_capabilities` chỉ chứa khoá `ai_policy` do người làm nên `exclude_ai_audit_rows` không bỏ. `capability_change_label` lọc xong còn 0 khoá thì rơi vào nhánh `len(changes) != 1`. Đã tái hiện: `GET /api/guidance/group/<id>/` với `AI_ENABLED=False` trả `['Đổi quyền của nhóm (0 việc)']`.
Lỗi này không lộ chữ AI và hiện chưa màn ERP nào gọi `guidance/group` (màn nhóm dùng `timeline` của `describe_group`). Dù vậy nhãn vẫn sai, và lệch với 02b 2.2 ("bỏ sự kiện mà mọi khoá đổi đều là việc AI").
Cách sửa gợi ý: cho `make_audit_timeline_provider` nhận thêm `row_filter`, hoặc lọc ở `next_steps.py` (bỏ dòng có `changes` rỗng sau `visible_keys`). Tối thiểu thì trả nhãn trung tính khi còn 0 khoá. Kèm test tái hiện ở trên.
Cùng chỗ: comprehension ở `services.py:265` gọi `registry.visible_keys(...)` một lần cho mỗi khoá. Nên tính một lần.

**N2. Test tắt khẩn không kiểm trạng thái thật.** `backend/apps/accounts/auth/tests/test_ai_features_flag.py:31-41` monkeypatch `status_services.is_ai_enabled`. `ai_visibility` không gọi hàm này nên test xanh mà không chứng minh gì. Nếu sau này ai đó viết `from apps.ai.status.services import is_ai_enabled` vào `ai_visibility`, test vẫn xanh. 02b mục 6 yêu cầu dựng `global_mode=off` thật trong DB, cùng với `AI_ENABLED=True`, rồi assert `ai_features_enabled=true`.

**N3. Thêm ca nhánh tắt cho chặn leo quyền.** Thêm một test với `AI_ENABLED=False`: mọi việc owner-only không thuộc `AI_CAPABILITY_KEYS` gán cho nhóm khác vẫn trả 400 `BR-PQ-32`, và nhóm Chủ vẫn `GROUP_LOCKED`. Có thể subclass `PrivilegeEscalationTests` với `override_settings(AI_ENABLED=False)` và lọc `owner_only` bỏ khoá AI.

Nit (không cần sửa): ở `orders/tests/test_ai_rows_hidden.py`, assert thứ hai của `test_off_audit_log_hides_ai_rows` luôn đúng vì không seed `odd_system_action`. Hàm `actor_kinds` cũng nhiều nhánh hơn cần thiết.

### Cho FE và QA

- Contract thật khớp 02b 2.1, 2.2 và 2.4. FE không cần đổi gì.
- QA E1 có thể dựa vào dòng thời gian nhóm (`describe_group`). Không cần quét `/api/guidance/group/` cho tới khi N1 được sửa hoặc có màn ERP dùng endpoint đó.
