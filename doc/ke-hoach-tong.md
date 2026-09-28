# Kế hoạch tổng — đợt 2026-09-28
> Điều phối: Claude (phân tích) · Người hiện thực: Gemini CLI / Antigravity (`AGENTS.md`) · Duy duyệt từng phase.
> Scope Duy chốt 28/09: sửa lỗi + AI + CSKH + CMS + khung go-live. **Không** làm đợt này: vai trò tự định nghĩa
> (hồ sơ `2026-09-28-vai-tro-tu-dinh-nghia` để sau), in tem tự động, AI cho khách.

## Cách chạy
- Gemini/Antigravity làm **đúng thứ tự bảng dưới**, một phase một lúc: `/lam-tiep` (tự chọn phase kế tiếp) hoặc
  `/lam-tinh-nang <slug>`.
- Một phase chỉ được bắt đầu khi `02c-giao-viec.md` của nó ở trạng thái **SẴN SÀNG CODE** — Duy đổi trạng thái
  này. Chưa đổi → dừng, báo Duy.
- Không chạy hai phase song song: các hồ sơ cùng sửa `backend/apps/common/api.py`, `config/settings.py`,
  `config/api_urls.py`, migration `accounts` — chạy tuần tự để tránh xung đột migration.
- Xong mỗi lô: QA APPROVED → commit + push; đánh dấu ☑ trong 02c của hồ sơ và ☑ ở bảng dưới.

## Thứ tự phase

| ☐/☑ | Phase | Hồ sơ (`doc/features/…`) | Lô | Trạng thái 02c | Điều kiện bắt đầu | Ghi chú |
|---|---|---|---|---|---|---|
| ☑ | **P1** Sửa lỗi bảo mật + lãi lỗ | `2026-09-28-sua-loi-bao-mat` | 1 → 2 → (merge `wip/autosave` → `main`) → 3 | XONG | — | Lô 1: Nhật ký lộ giá vốn, tra đơn dò được, throttle. Lô 2: chốt lô đủ điều kiện, noindex staging, **merge main** (xung đột → dừng hỏi Duy). Lô 3: lãi lỗ tính hai lần (S06) + doanh thu hoá đơn huỷ (S07) |
| ☑ | **P2** Tiếp theo · Đã làm | `2026-09-28-ai-digital-worker` | 0 (spike, song song) + 1a → 1b → 1c | XONG | P1 xong + merge main | Lô 1c sau P1 Lô 3 (cùng sửa `batch_pnl`). Spike DW-02: phần đo trên máy Android/Windows ≥ 8GB do **Duy chạy** |
| ☑ | **P3** Lệnh AI tự sinh + AI của tôi | `2026-09-28-ai-digital-worker` | 2 → 3a → 3b → 3c → 4 | XONG | P2 xong; kết quả spike Lô 0 đạt | Mọi môi trường `AI_WRITE_LEVELS_ALLOWED=C` (AI chỉ soạn nháp). Lô 2 có sẵn danh sách cấm `/api/public/`, `/api/cskh/`, `…/label/` |
| ☐ | **P4** CSKH xác nhận + in tem | `2026-09-28-cskh-xac-nhan-in-tem` | 1 → 2 → 3 → 4 (5 là Could) | SẴN SÀNG CODE (Duy duyệt 28/09) | P3 xong | Lô 2 chỉ staging. Lô 3 (tự huỷ) lên production **sau khi legal-vn duyệt câu thông báo** và Duy bật cờ `CSKH_AUTO_CANCEL_ENABLED` |
| ☐ | **P5** CMS viết bài | `2026-09-28-cms-viet-bai` | 1 → 2 → … → 7 | SẴN SÀNG CODE (Duy duyệt 28/09) | P4 xong | Thư viện mới duy nhất: Tiptap 2 (erp-console). CMS-16 đã làm ở P1 |
| ☐ | **P6** Khung go-live | `2026-09-28-khung-go-live` | 1 → 2 → 3 | SẴN SÀNG CODE (Duy duyệt 28/09) | CMS Lô 5 (Lô 1–2), CMS Lô 7 (Lô 3) | Cờ `PRIVACY_CONSENT_REQUIRED` bật: chưa đăng chính sách thì Shop không nhận đơn |
| ☐ | **P7** AI tự ghi + vùng đỏ | `2026-09-28-ai-digital-worker` | 5a → 5b → 5c → 6a → 6b | SẴN SÀNG CODE (Duy duyệt 28/09) | P6 xong | **Chỉ staging** tới khi xong S-L1…S-L4 (pháp lý) |

## Việc của Duy (không phải code)
| Khi nào | Việc |
|---|---|
| Trước P2 | Đổi 02c AI sang SẴN SÀNG CODE (ghi rõ "P2"); chạy spike DW-02 trên máy Android/Windows ≥ 8GB |
| Trước P4 | Ghi 3 quyết định vào `doc/decisions.md`: trạng thái "Chờ xác nhận", Group `cskh`, luật tự huỷ đơn không liên lạc được. Gán nhân viên vào `cskh` |
| Trước P4 Lô 3 lên production | `legal-vn` duyệt câu thông báo huỷ, câu báo trước ở checkout, quy định ghi nhãn trên tem. Tạo Cloud Run Job + lịch 5 phút cho `process_cskh_deadlines`, đặt `SHOP_HOTLINE` |
| Trước P6 lên production | Chốt chủ thể pháp lý của Lộc, đặt biến `SELLER_*` (không đưa vào repo); soạn nội dung các trang chính sách trong CMS; checklist D1–D11 trong `2026-09-28-khung-go-live/01-analysis.md` §6 |
| Trước P7 | Hoàn tất S-L1…S-L4: hồ sơ phân loại rủi ro AI, thông báo Bộ KH&CN, hợp đồng không-huấn-luyện với nhà cung cấp cloud, thoả thuận Duy–Lộc |
| Mỗi phase | Đổi trạng thái 02c → SẴN SÀNG CODE; duyệt kết quả QA; quyết định deploy (Gemini không deploy) |

## Mặc định đã áp (Duy lật được — ghi ở từng hồ sơ)
- AI: lệnh đọc chạy ngay có lọc, lệnh ghi mặc định nháp; chỉ Chủ huỷ lô quá hạn; "tắt AI của tôi" = lệnh ghi về nháp.
- CSKH: gọi 3 lần trong 30' → Quản lý → 30' không xử lý thì tự huỷ + hệ thống lập phiếu hoàn chờ Chủ xác nhận;
  tính giờ thật; khách tự muốn huỷ/đổi thì không tự huỷ; không sửa đơn cũ; in tem tay 100×150.
- CMS: đơn giản, trang bài tải lúc chạy (không SEO nâng cao); CMS tự thành lệnh AI (chỉ soạn nháp).
- Go-live: thông tin người bán qua biến môi trường; câu "vựa sẽ gọi xác nhận" tắt tới khi CSKH chạy thật.

## Để sau (không trong đợt này)
Vai trò tự định nghĩa (ma trận CRUD) · in tem tự động/trạm in · huỷ lô quá hạn đã có ở P2 (DW-06) · throttle dùng
cache chung (Redis) · SEO nâng cao cho bài viết · hoàn kho/hoàn tiền một phần theo dòng · S18/S20/S21 giao hàng.

## Nhật ký chạy đêm
| Thời gian | Phase | Lô | Kết quả QA | Commit | Số test BE | Ghi chú / Vấn đề |
|---|---|---|---|---|---|---|
| 2026-09-28 21:00 | P1 | Lô 1 | APPROVED | `91a9fc3` | 692 | S01 lọc giá vốn nhật ký, S02 tra đơn, S03 throttle |
| 2026-09-28 21:50 | P1 | Lô 2 | APPROVED | `9ef26e1` | 712 | S04 chốt lô BR-LO-04/BR-KK-05, S05 noindex staging |
| 2026-09-28 22:12 | — | Merge | — | `85c0b36` | 712 | Hợp nhất lịch sử main cũ vào wip/autosave và fast-forward main |
| 2026-09-28 22:20 | P1 | Lô 3 | APPROVED | `9f39fe9` | 723 | S06 lãi lỗ không tính 2 lần hao hụt/hỏng, S07 bỏ hoá đơn huỷ |
| 2026-09-28 22:32 | P2 | Lô 0 | PASS | `cd74f0f` | 723 | Spike DW-01 (114 lệnh, dispatch 100%), DW-02 (recall@5 98%) |
| 2026-09-28 22:58 | P2 | Lô 1a | APPROVED | `5ef773b` | 732 | DW-03 khung Tiếp theo · Đã làm trên đơn (+L-4 dòng AI) |
| 2026-09-29 00:04 | P2 | Lô 1b | APPROVED | `ea6f2da` | 749 | DW-04 phiếu hoàn + GD lệch, DW-05 lô (tách check_close_batch) |
| 2026-09-29 00:38 | P2 | Lô 1c | APPROVED | `c0c4272` | 757 | DW-06 Chủ huỷ lô quá hạn (EXPIRED->CANCELLED, PnL TL-4) |
| 2026-09-29 02:20 | P3 | Lô 2 | APPROVED | `c427bf8` | 775 | DW-07 registry tự sinh + chỉ mục, DW-08 required_perms, DW-09 chọn lệnh 2 bước |
| 2026-09-29 03:15 | P3 | Lô 3a | APPROVED | `f0f32e9` | 785 | DW-10 lệnh đọc mức A, DW-11 nháp C + Việc AI (lọc PII, 3s đếm ngược, H6 kiểm kê) |
| 2026-09-29 03:50 | P3 | Lô 3b | APPROVED | `eda18d3` | 805 | DW-12 AI của tôi (bản ghi, kill=C), DW-13 chính sách + tắt khẩn cấp (Chủ) |
| 2026-09-29 04:55 | P3 | Lô 3c | APPROVED | `55f78f9` | 798 | DW-14 chat qua call + Để AI làm, DW-15 gỡ catalog cũ (404), DW-16 tóm tắt timeline |
| 2026-09-29 05:34 | P3 | Lô 4 | APPROVED | `18c4a13` | 806 | DW-17 nhập lô mua tại cảng trên ERP, sinh batch DRAFT, chống trùng idempotency |


