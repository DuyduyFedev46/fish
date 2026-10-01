# Lưu cài đặt AI và CMS trên backend thật (luồng NHANH)
> Điều phối · 2026-10-01 · Trạng thái: **SẴN SÀNG CODE** · Nguồn: QA P8b Lô 4b (`doc/features/2026-09-30-dat-ten-tieng-anh/04-qa-report.md` mục Lô 4b, B1–B3). Lỗi có từ trước P8b; mock che mất.

## SR-AIS-01 — Lưu không bị mã hoá JSON hai lần (B1, High)
- **AC1.** `PUT /api/ai/policy/` (màn Chính sách AI) và `PUT /api/ai/my-config/` (màn AI của tôi) gửi body là **object JSON**, BE thật trả 200 và lưu đúng phiên bản mới (không còn 400 `Expected a dictionary, but got str`).
- **AC2.** Rà mọi chỗ gọi `apiFetch`/`http` với `body: JSON.stringify(...)` trong khi lớp http đã tự `JSON.stringify` (đã biết: `features/ai/policy/api.ts:~96`, `features/ai/settings/api.ts:~101,~123`, `features/content/api.ts:~61,~72`) — sửa một kiểu thống nhất; test vitest kiểm body gửi đi là object/chuỗi JSON một lớp.
- **AC3.** Mock phải bắt được lỗi này: mock parse body như BE thật (body là chuỗi JSON lồng → mock trả 400 giống BE).

## SR-AIS-02 — Đọc đúng dạng `limits` (B2, Medium)
- **AC1.** "AI của tôi" đọc `limits` theo đúng dạng BE trả (phẳng), ô trần hiện đúng giá trị; lưu không gửi `""` (để trống → không gửi khoá / `null` theo contract BE).

## SR-AIS-03 — Lưu "AI của tôi" không làm mất cấu hình nhóm (B3, High — nới quyền AI)
- **AC1.** Lưu "AI của tôi" giữ nguyên `groups`/`group_levels` hiện có (gửi lại đúng giá trị đọc được hoặc không gửi khoá nếu BE coi vắng = giữ nguyên — kiểm contract BE).
- **AC2.** Test: user có nhóm lệnh đặt OFF → mở "AI của tôi" → đổi 1 lệnh → lưu → `effective_level` của mọi lệnh khác **không đổi** (đặc biệt không OFF → A/C).

## Chung
- Kiểm bằng **backend thật** (Django + ERP build thật), không chỉ mock. Không đổi BE trừ khi contract BE sai (khi đó ghi rõ và báo).
- Định danh tiếng Anh; `python3 scripts/check_naming.py`.
