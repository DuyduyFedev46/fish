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

---

# Vòng 2 (SR-HIDE-AI-02) · 2026-10-05

## Kết luận: APPROVED — AC1–AC4 chạy thật đạt; L1 và L2 của vòng 1 đã hết; không lỗi chặn.
## Tổng: 164 ca Playwright (114 cờ tắt + 50 cờ bật) · ✅ 164 · ❌ 0 · ⏸ 1 (xem dưới) + vitest 78 file/912 test xanh

Cách kiểm: build mock (`NEXT_PUBLIC_USE_MOCK=1`) 2 bản trong bản sao tạm của code chưa commit (cờ tắt, và `NEXT_PUBLIC_AI_FEATURES=1`), phục vụ bằng http.server, Playwright Chromium 1280x800, vai `loc`, `kho1`, `ql1` (+ `giao1` cho nút về). Ảnh `qa-shots/r2-*` (70 ảnh, chỉ dữ liệu mock giả). Server đã tắt.

## Theo AC
| AC | Kết quả | Bằng chứng |
|---|---|---|
| AC1 cờ tắt: không điểm vào "Nhờ" | ✅ | 3 vai x tồn kho 901/902/903 và đơn 101/102/103: menu "…" không có "Nhờ", không item rỗng, không separator đầu/cuối/đôi (menu còn "Sao chép mã…", "Xem nhật ký…", "Huỷ đơn…"). `/dev-patterns/` (GuidancePanel) 3 vai: 0 nút "Nhờ". 0 request `/api/ai*` toàn phiên, console 0 lỗi. Ảnh `r2-off-menu-*`, `r2-off-devpatterns-*` |
| AC1 cờ =1 như cũ | ✅ (⏸ đơn hàng) | Tồn kho 3 vai: mục "Nhờ người xử lý" hiện lại; dev-patterns có nút Nhờ, bấm ra "Đã chuyển việc". ⏸ Mock không có bước `allowed=false` ở màn đơn hàng nên menu đơn không hiện "Nhờ" cả khi bật; chỉ có vitest (`escalatableStep` cờ bật khác null), không có ảnh trình duyệt cho đơn hàng |
| AC2 `/ai/*` khi tắt | ✅ | `/ai/policy|report|settings|actions/` x 3 vai: "Không tìm thấy trang này", nội dung vùng trang không có "quyền"/"Chủ vựa", 0 request `/api/ai`. Nút "Về Tổng quan" -> `/overview/` = đúng trang sau đăng nhập của loc/kho1/ql1; `giao1` thì nút "Về Việc giao của tôi" -> `/my-deliveries/` đúng vai. Ảnh `r2-off-ai_*` |
| AC3 câu "màn Việc của AI" | ✅ | Bật: hộp Nhờ (loc/kho1/ql1, tồn kho) còn "Họ sẽ thấy việc này ở màn Việc của AI, tab Được chuyển." Ảnh `r2-on-escalate-*`. Tắt: không mở được hộp Nhờ nên không còn chỗ nhắc |
| AC4 | ✅ | vitest `npm run test` 78 file / 912 test (vòng 1: 909, thêm 3 ca) xanh; `npm run typecheck` exit 0; `npm run build` không cờ exit 0 |

## Ngoại lệ & biên
- Cờ bật, `/ai/*` như cũ: policy/settings/actions hiện màn AI; `/ai/report/` với kho1/ql1 hiện "không có quyền xem" (phân quyền cũ của màn, đúng khi cờ bật). ✅
- Nút về đúng vai cho cả vai chỉ giao hàng. ✅
- Console 0 lỗi ở cả hai trạng thái. ✅
- Ghi nhận vòng 1 (mock không bắt được request escalate thật khi cờ tắt) nay không còn vì điểm vào đã ẩn; endpoint BE không đổi. Không còn cần xác nhận AI_ENABLED=0.

## Phân quyền / rò dữ liệu
Chỉ đổi FE ẩn/hiện; không đổi BE, không thêm field. Không rò giá vốn/dữ liệu cá nhân mới; không log, localStorage, URL mới; ảnh chỉ dữ liệu mock.

## Hồi quy
Menu "…" tồn kho/đơn hàng: các mục khác (Trả nhà cung cấp, Huỷ phần tồn, Chốt lô, Huỷ đơn, Sao chép mã, Xem nhật ký) vẫn hiện y như bản bật cờ. `python3 scripts/check_naming.py` OK, không phát sinh mới. Sau build `git status` không thêm file lạ.

## Lỗi
Không có. L1 (nhắc màn AI khi tắt) và L2 (thông báo "không có quyền" ở /ai/*) của vòng 1: ĐÃ SỬA.

## Lệnh đã chạy
- `npm run test` (erp-console): 78 passed / 912 passed · `npm run typecheck`: exit 0 · `npm run build` (không cờ): exit 0
- `NEXT_PUBLIC_USE_MOCK=1 npm run build` (tắt) và kèm `NEXT_PUBLIC_AI_FEATURES=1` (bật) trong bản sao tạm; Playwright `r2.py`: tắt 114/114 PASS, bật 50/50 PASS (không FAIL)
