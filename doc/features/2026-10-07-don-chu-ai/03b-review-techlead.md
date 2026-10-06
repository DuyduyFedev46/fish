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
