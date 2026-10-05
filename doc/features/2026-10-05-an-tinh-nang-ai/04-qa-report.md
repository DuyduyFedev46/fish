# QA — Ẩn tính năng AI (SR-HIDE-AI-01) · lần 1 · 2026-10-05

## Kết luận: APPROVED — AC1–AC6 chạy thật đạt; có 2 lỗi Low (chữ còn nhắc màn AI khi cờ tắt), không chặn.
## Tổng: 15 ca · ✅ 14 · ❌ 0 · ⏸ 1 (khối AI trên trang chi tiết với dữ liệu thật) · ghi nhận Low: 2

Cách kiểm: build mock 3 bản trong bản sao tạm (HEAD gốc, cờ tắt, `NEXT_PUBLIC_AI_FEATURES=1`), phục vụ `out/` bằng http.server, Playwright Chromium 1280x800, vai `loc` (Chủ), `kho1`, `ql1`, `giao1`. Ảnh ở `qa-shots/` (chỉ dữ liệu mock giả). Server đã tắt, không sửa code sản phẩm.

## Theo AC
| AC | Kết quả | Bằng chứng |
|---|---|---|
| AC1 menu/avatar/tìm lệnh | ✅ | Tắt: 0 link `/ai/` trong `.nav`, không có "Chính sách AI"/"Báo cáo AI"; avatar chỉ còn "Tài khoản của tôi"+"Đăng xuất"; CommandSearch gõ "AI" không ra mục AI. Bật: nav 2 link AI, avatar có "AI của tôi", tìm lệnh ra "Chính sách AI". Ảnh `off-01/02/03`, `on-01/02/03` |
| AC2 `/ai/*` | ✅ | Tắt: `/ai/policy|report|settings|actions/` hiện khung "Bạn không có quyền xem mục này" + nút "Về Tổng quan", không nội dung AI, 0 request `/api/ai`. Ảnh `off-04-*`. (Xem L1) |
| AC3 trang chi tiết | ✅ (⏸ phần khối thật) | Tắt: 12 trang chi tiết (đơn, thanh toán, hoàn tiền, nhập hàng, tồn kho, xác nhận, khách, giao hàng, hàng hoàn, kiểm kê, NCC, danh mục) không có "Trợ lý AI"/"Để AI làm", 0 request `/api/ai`, bố cục không ô trống (ảnh `off-05-*`). ⏸ Mock không bật cổng `ai_enabled` nên khối AI không hiện cả ở bản gốc; phần này chỉ có vitest (`aiFeatures.*.test.ts`), không có bằng chứng trình duyệt |
| AC4 không Worker/model | ✅ | Tắt: toàn phiên 0 Worker, 0 request chứa wllama/.gguf/huggingface. Lưu ý chunk wllama vẫn nằm trong `out/` cả hai bản (chỉ không được tải) |
| AC5 bật lại | ✅ | So văn bản `main` + nav của bản BẬT với bản HEAD gốc ở 10 trang (nav, 5 chi tiết, dev-patterns, 4 trang /ai/*): IDENTICAL cả 10. Vitest 2 trạng thái có và xanh |
| AC6 không hồi quy | ✅ | `npm ci` sạch, `npm run typecheck` exit 0, `npm run build` không cờ exit 0, `npm run test` tại chỗ 78 file / 909 test xanh (gốc 76/900, thêm 2 file/9 test). "Nhờ" xem mục dưới |

## Ngoại lệ & biên
- Giá trị cờ lạ `"true"`, `"0"`, `""`, `"yes"`, vắng: vitest tạm (`vi.stubEnv` + import lại module) → đều false, chỉ `"1"` true. ✅ (không build lặp lại; ghi rõ là kiểm bằng vitest)
- Vai chỉ giao hàng `giao1`, nút "Nhờ" (GuidanceEscalate, `/dev-patterns/`): tắt vẫn bấm được, hiện "Đã chuyển việc cho nhóm…", không câu "màn Việc AI", 0 link `/ai/actions`, không lỗi console. Bật: có link như trước. ✅ Ảnh `off-11`, `on-11`. Ghi chú: mock không có đường nào đưa `giao1` tới nút "Nhờ" ở trang nghiệp vụ thật (chỉ trang dev-patterns).
- "Nhờ người xử lý" qua menu "…" (kho1, ql1, loc, tồn kho id=901): vẫn chạy khi tắt, 0 link `/ai/`, toast "Đã nhờ…". ✅ Ảnh `off-09/10`. (Xem L1/L2)
- Bản mock `NEXT_PUBLIC_USE_MOCK=1` tuân cờ: ✅ (cả 2 trạng thái đều build mock).
- Console: 0 lỗi mới ở cả hai trạng thái. ✅

## Phân quyền / rò dữ liệu
Không đổi BE/phân quyền; Chủ cũng không thấy mục AI khi tắt (đã kiểm với `loc`). Rò giá vốn: không thuộc phạm vi, không có thay đổi trường dữ liệu. Rò dữ liệu cá nhân: không thêm log/localStorage/URL; ảnh chụp chỉ dữ liệu mock giả. `python3 scripts/check_naming.py` OK, không phát sinh mới.

## Hồi quy
Trang chi tiết các luồng không AI giống bản gốc khi bật cờ (10/10 IDENTICAL). Cờ tắt: menu và trang chi tiết khác AI không đổi.
Ghi chú môi trường: chạy `vitest` trong bản sao tạm có 1 file fail do đường dẫn tương đối tới `doc/` (`features/ai/commands/commands.test.ts`), không phải lỗi sản phẩm; chạy tại chỗ xanh.

## Lỗi (đều Low, không chặn)
### L1 — Hộp "Nhờ người xử lý" vẫn nhắc màn AI khi tắt · Low · AC6
Bước: build cờ tắt (mock) → đăng nhập `kho1` → `/inventory/detail/?id=901` → "…" → "Nhờ người xử lý".
Mong đợi: không nhắc màn AI. Thực tế: nội dung hộp ghi "Họ sẽ thấy việc này ở màn Việc của AI, tab Được chuyển." (`ESCALATE_MSG.body` ở `features/guidance/escalation.ts`, dùng bởi EscalateModal). Không có link chết, chỉ là chữ trỏ tới màn đã ẩn. Ảnh `off-09-escalate-kho1.png`.

### L2 — Trang /ai/* tắt hiện thông báo "không có quyền" · Low · AC2
Gõ `/ai/policy/` với Chủ khi tắt → "Bạn không có quyền xem mục này… hãy nhờ Chủ vựa cấp quyền". Với Chủ thì gây hiểu nhầm (vì không phải thiếu quyền). AC cho phép "không có trang này" hoặc về trang chủ; nên đổi chữ sang "Trang không tồn tại"/chuyển hướng. Ảnh `off-04-ai-policy.png`.

### Ghi nhận (không phải lỗi)
- Khi `Nhờ` chạy thật (không mock) vẫn POST `/api/ai/actions/escalate/` kể cả cờ tắt; phù hợp DW-23-AC7 nhưng mock không bắt được request này, nên cần xác nhận khi lên staging rằng endpoint hoạt động với `AI_ENABLED=0`. ⏸
- Code AI (chunk wllama, chuỗi route) vẫn nằm trong bundle; đã nêu trong dev-notes.

## Lệnh đã chạy
- `npm ci` (bản sao tạm) OK · `npm run typecheck` exit 0 · `npm run build` (không cờ) exit 0
- `npm run test` tại chỗ: 78 file / 909 test passed
- Build mock: cờ tắt, cờ `=1`, HEAD gốc → 3 bản; Playwright `qa.py`: tắt 41 ca PASS; bật 18 ca PASS (1 "FAIL" giả do script tìm nút "Nhờ" ở `giao1` trong my-deliveries, đã thay bằng ca dev-patterns ở trên)
- Vitest giá trị cờ lạ: 6/6 passed
- `python3 scripts/check_naming.py`: OK
