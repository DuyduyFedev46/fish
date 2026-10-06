# QA — Lô dọn chữ AI

## QA lô dọn chữ AI (08/10)

### Kết luận: REJECTED — ca W39 (BE bật AI, FE build tắt) vẫn lộ chữ AI ở dòng thời gian và nhãn quyền (B1, Medium). Mọi ca khác đạt
### Tổng: 42 ca · ✅ 39 · ❌ 1 · ⏸ 2

Nhánh `feat/don-chu-ai-fe`, HEAD 71b46f1. BE thật (runserver từ worktree này, SQLite tạm, `AI_ENABLED` đổi bằng cách khởi động lại), `erp-console` và `frontend` build `NEXT_PUBLIC_USE_MOCK=0` trỏ vào BE đó; build ERP riêng cho cờ FE tắt (mặc định) và bật (`NEXT_PUBLIC_AI_FEATURES=1`). Dữ liệu giả (SĐT 0900xxxxxx, "Khách Giả n"). Seed có 5 vai (Chủ, Quản lý, NV kho, NV giao, CSKH), dòng AuditLog `actor_kind=ai`, Hệ thống có `proposal_ref`, dòng do người (`confirm_proposal`, `ai_config_update`, `ai_policy_update`) trên đơn, khoản tiền, phiếu hoàn, lô, mặt hàng, phiếu kiểm kê, và 1 bài `source=ai`.

### Theo yêu cầu
| # | Kiểm | Kết quả | Bằng chứng |
|---|---|---|---|
| 1 | E1: BE tắt, FE tắt, 5 vai x 44 route (220 lượt), gồm `/permissions/`, `/account/`, `/audit-logs/`, `/content/`, `/ai/*`, mọi chi tiết đơn/tiền/hoàn/lô/kiểm kê/mặt hàng | ✅ | 0 lượt có `/\bAI\b/` hoặc "Trợ lý" ở text, `aria-label`, `title`, `placeholder`, `alt`, `option`; 0 request `/api/ai/`; `/api/staff/groups/*` của BE thật không chứa `ai_policy`; `/me` cả 5 vai `ai_features_enabled=false` |
| 2 | W39: BE `AI_ENABLED=1`, FE build tắt | ❌ | Xem B1: 18 lượt lộ chữ AI |
| 3 | Đối chứng: BE bật, FE bật | ✅ | 90/220 lượt có chữ AI, 72 request `/api/ai/`, `ai_policy` có trong ma trận quyền: script quét không rỗng |
| 4a | Nhật ký khi tắt (API `/api/audit-logs/`) | ✅ | Tắt: 13 dòng, 0 dòng `actor_kind=ai`, 0 dòng Hệ thống có `proposal_ref`; dòng người `confirm_proposal`, `ai_config_update`, `ai_policy_update` vẫn hiện (đúng Q1 mặc định, chờ Duy). Bật: 20 dòng, đủ dòng AI |
| 4b | Dòng thời gian chi tiết đơn, lô, thanh toán, phiếu hoàn, kiểm kê, mặt hàng khi tắt | ✅ | Nằm trong E1 (mục 1): không còn "AI của …" |
| 4c | `/me` có `ai_features_enabled` | ✅ | Tắt: `false`, `capabilities` không có `ai.manage_ai_policy`, `permissions` giữ nguyên mã thô; bật: `true`, có cả hai |
| 5 | Shop tra đơn (BE thật, 390px và 1280px) | ✅ | 53 kiểm: 9 đơn (7 trạng thái phiếu, 1 tự huỷ, 1 chờ xác nhận) không có mã thô hay "TTL"; nhãn đúng T24–T30; đơn tự huỷ = "Đã huỷ vì quá giờ thanh toán"; không lộ tên/SĐT/địa chỉ; không cuộn ngang. 52/53 ở lần chạy đầu: ca "sai 4 số cuối" lỗi do dữ liệu thử của QA (SĐT đơn mẫu tình cờ kết thúc bằng 0000), không phải lỗi sản phẩm; chạy lại bằng số khác, 404 đúng |
| 5b | Tra đơn có giới hạn tần suất | ✅ | 10 lần sai liên tiếp 404, từ lần 11 trả 429; đúng số cuối sau đó vẫn 429 |
| 6a | Huỷ đơn có ghi chú SĐT (BE thật, 360px) | ✅ | Gõ 250 ký tự chỉ còn 200 (`maxlength=200`); ghi chú có số 0901234567 → lỗi hiện dưới ô, hộp vẫn mở, chữ còn nguyên, đơn vẫn `PROCESSING` (API); sửa lại → huỷ được |
| 6b | Chi tiết đơn hiện "Ghi chú huỷ" | ✅ | Có dòng và nội dung; đơn huỷ không ghi chú thì KHÔNG có dòng (ngoài đường thuận) |
| 6c | Hàng chờ xác nhận: "Lý do quyết định" (360px, 1280px) | ✅ | Chưa quyết định: không dòng; số dài → hộp mở, lỗi dưới ô, chữ còn nguyên; sửa → hiện "Lý do quyết định" + nội dung. BE trực tiếp: lý do có dãy số dài → 400 `BR-GH-19`; quá 200 ký tự → 400; phiếu vẫn `ESCALATED` |
| 6d | Huỷ đơn ở 1280px | ⏸ | Hết đơn để huỷ trong seed; chỉ chụp 360px (đường logic dùng chung với 360px) |
| 7 | Hồi quy | ✅ | `tsc --noEmit` exit 0; `check-ai-chunks` XANH (48 màn + 2 layout); build mock=0 và mock=1 exit 0; `ed_batch3_orders` 143/143; `ed_batch13_catalog` 128/128; `ed_batch1_shell` 56/56 (bản build bật AI, vì kịch bản đòi menu có mục AI; bản build tắt AI cho 54/56, 2 ca đòi "Chính sách AI", "AI của tôi" trong menu, khác biệt có chủ ý của cờ); `note_br_gh_19` mock 10/10. Shop đặt hàng thật: 10/12, 2 ca còn lại là `console.error` của 1 request 404 `/api/public/content/pages/by-role/privacy/` (DB tạm chưa có trang Chính sách riêng tư, không liên quan lô); bấm đúp nút đặt hàng chỉ tạo 1 đơn |
| 7b | `npm ci` sạch | ⏸ | Không chạy: `node_modules` là symlink tới repo chính, `npm ci` sẽ xoá nó. Điều phối viên đã báo build sạch |
| 8 | 360px và 1280px | ✅ | Không cuộn ngang và không `console.error` (trừ 400/404 có chủ ý) ở các màn đã chụp |

### Ngoài đường thuận đã chạy
1. W39 (cấu hình lệch BE/FE).
2. Huỷ không ghi chú và ghi chú quá dài (200 ký tự), gõ SĐT.
3. Bấm đúp "Đặt hàng" (1 đơn).
4. 10 lần tra đơn sai → 429.
5. Người ngoài phạm vi: CSKH nhận 404 cho đơn của phiếu nằm ngoài phạm vi (không thấy `cancel_note`/`decision_note`).

### Rò dữ liệu
- Giá vốn: không có field giá vốn trong response Shop; ảnh và HTML Shop không chứa `purchase_rate`, `landed_unit_cost`, `unit_cost`.
- Dữ liệu cá nhân: Shop tra đơn và HTML Shop không trả tên/SĐT/địa chỉ; `localStorage` và URL của Shop sau đặt hàng không chứa tên, SĐT, địa chỉ; ghi chú huỷ không nhận dãy số dài (BR-GH-19).
- Ghi nhận (không do lô này): `cancel_note` trong chi tiết đơn trả cho cả NV kho và NV giao được gán (cùng phạm vi họ vốn đã thấy đơn). Nội dung đã bị chặn SĐT/số dài bởi BR-GH-19 nên không rò dữ liệu cá nhân.

### Lỗi
#### B1 — W39: BE bật AI, FE build tắt, vẫn hiện chữ AI · Medium · yêu cầu W39 (02b mục 1 và mục 5 E1)
Bước tái hiện: chạy BE với `AI_ENABLED=1`; ERP build `NEXT_PUBLIC_USE_MOCK=0` KHÔNG đặt `NEXT_PUBLIC_AI_FEATURES`; đăng nhập Quản lý (hoặc Chủ, NV kho); mở `/orders/detail/?id=<đơn có dòng AI>`.
Mong đợi: không có chữ "AI" ở bất kỳ đâu (02b mục 5 E1 ma trận (BE bật, FE tắt), yêu cầu W39).
Thực tế: 18 lượt lộ chữ AI:
- Dòng thời gian "… · AI của owner1" ở chi tiết đơn (2 đơn), lô, kiểm kê, mặt hàng, cho Chủ, Quản lý, NV kho (BE trả dòng AI vì BE bật; FE tắt không lọc, khác với `/audit-logs/` đã được FE lọc).
- Chủ: "Quản lý chính sách AI" ở `/account/`; "Cài đặt chính sách AI" ở `/permissions/` và `/permissions/detail/`.
Nguyên nhân: FE tắt chỉ chặn khối AI theo cờ, chưa lọc dòng AI của `timeline[]` do BE trả khi BE bật, và nhãn quyền AI trong `capabilities`/ma trận. E1 mock không bắt được vì mock không có dòng AI trong dòng thời gian.
Ảnh hưởng: ca cấu hình lệch (BE bật, FE tắt) vẫn lộ chữ AI, trái cam kết W39 "một cờ". Không rò giá vốn hay dữ liệu cá nhân.
Gợi ý sửa (FE): khi `!aiVisible(me)` lọc khỏi `timeline[]` các phần tử `actor.kind === "ai"` hoặc Hệ thống có `proposal_ref` (như đã làm ở Nhật ký), ẩn `capabilities` mã `ai.*` ở màn Tài khoản, ẩn khoá `ai_policy` ở `/permissions/`. Sau khi sửa, chạy lại E1 ma trận (BE bật, FE tắt) trên BE thật.

Ghi nhận không chặn:
- N1 (Q1 chờ Duy): khi tắt, dòng do người đổi cài đặt AI vẫn hiện ở Nhật ký ("Đổi chính sách AI", "Đổi cài đặt AI", "Duyệt đề xuất AI"), đúng mặc định đã ghi. Kịch bản E1 của QA cho phép các nhãn này, và xác nhận chúng chỉ nằm ở `/audit-logs/`.
- N2: `features/permissions/mock.ts` còn khoá `ai_policy` (nợ F1, ghi trong dev notes), BE thật không ảnh hưởng.

### Lệnh đã chạy
- `manage.py migrate`, seed ORM, `runserver 8770` (`AI_ENABLED` 0/1, CORS ba cổng tĩnh).
- Build: `erp-console` mock=0 hai bản (cờ AI tắt, bật), `frontend` mock=0, `erp-console` mock=1 (hai bản).
- Playwright (Python, trong scratchpad): quét E1 thật (5 vai x 44 route x 3 cấu hình), Shop tra đơn thật, ghi chú huỷ đơn, quyết định CSKH, đặt hàng Shop, throttle tra đơn.
- `tsc --noEmit`, `check-ai-chunks.mjs`, `ed_batch1_shell`, `ed_batch3_orders`, `ed_batch13_catalog`, `note_br_gh_19`.
- Đã dọn: dừng server, gỡ symlink `node_modules`, `.env`, `staticfiles`, xoá `out/` và DB tạm.

### QA lại sau 4216e84 (08/10)

**Kết luận: APPROVED — B1 đã sửa, ma trận W39 trên BE thật không còn chữ AI. Không còn lỗi chặn.**
Tổng: 4 ca · ✅ 4 · ❌ 0 · ⏸ 0 (chỉ chạy lại phần liên quan; các mục còn lại của lần trước giữ nguyên kết quả).

Dựng lại BE thật (SQLite tạm, `AI_ENABLED` 0/1) và hai bản build ERP mock=0 (cờ FE tắt, bật), cùng seed như lần trước. `tsc --noEmit` exit 0.

| Ca | Kết quả | Bằng chứng |
|---|---|---|
| W39: BE `AI_ENABLED=1`, FE build tắt, 5 vai × 44 route (220 lượt) | ✅ | 0 lượt có `/\bAI\b/` hoặc "Trợ lý" (text, `aria-label`, `title`, `placeholder`, `alt`, `option`); 0 request `/api/ai/`. Các chỗ đã báo sạch: chi tiết đơn, lô, kiểm kê, mặt hàng, `/account/`, `/permissions/`, `/permissions/detail/`. Dữ liệu BE vẫn có `ai_policy` (BE bật) nhưng FE không hiển thị |
| Không ẩn quá tay ở W39 | ✅ | Chi tiết đơn (360px): "AI của" = 0 nhưng dòng thời gian của người vẫn còn; không cuộn ngang |
| BE tắt + FE tắt | ✅ | 220 lượt, 0 chữ AI, 0 request `/api/ai/`, `/api/staff/groups/*` không có `ai_policy`, `/me` `ai_features_enabled=false` |
| Đối chứng BE bật + FE bật | ✅ | 90/220 lượt có chữ AI, 74 request `/api/ai/`; chi tiết đơn có "AI của" = 2 |

Ghi chú: `check-ai-chunks.mjs` không chạy lại được vì `.next` bị bản build gần nhất (cờ bật) ghi đè; điều phối viên đã báo XANH ở bản tắt. Server chỉ tắt theo PID của QA; đã gỡ symlink, `out/`, DB tạm.
