# Kế hoạch tổng — đợt 2026-09-28
> Điều phối: Claude · Người hiện thực: P1–P7 Gemini CLI / Antigravity; **từ P8 là đội Claude** (Duy chốt 30/09, quy trình ở
> `CLAUDE.md` mục "Người hiện thực"; AGY tạm dừng) · Duy duyệt từng phase.
> Scope Duy chốt 28/09: sửa lỗi + AI + CSKH + CMS + khung go-live. **Không** làm đợt này: vai trò tự định nghĩa
> (hồ sơ `2026-09-28-vai-tro-tu-dinh-nghia` để sau), in tem tự động, AI cho khách.

## Cách chạy
- Người hiện thực (từ P8 là đội Claude) làm **đúng thứ tự bảng dưới**, một phase một lúc: `/lam-tiep` (tự chọn phase kế tiếp) hoặc
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
| ☑ | **P4** CSKH xác nhận + in tem | `2026-09-28-cskh-xac-nhan-in-tem` | 1 → 2 → 3 → 4 (5 là Could) | XONG | P3 xong | Lô 2 chỉ staging. Lô 3 (tự huỷ) lên production **sau khi legal-vn duyệt câu thông báo** và Duy bật cờ `CSKH_AUTO_CANCEL_ENABLED` |
| ☑ | **P5** CMS viết bài | `2026-09-28-cms-viet-bai` | 1 → 2 → … → 7 | XONG | P4 xong | Thư viện mới duy nhất: Tiptap 2 (erp-console). CMS-16 đã làm ở P1 |
| ☑ | **P6** Khung go-live | `2026-09-28-khung-go-live` | 1 → 2 → 3 | XONG | CMS Lô 5 (Lô 1–2), CMS Lô 7 (Lô 3) | Cờ `PRIVACY_CONSENT_REQUIRED` bật: chưa đăng chính sách thì Shop không nhận đơn |
| ☑ | **P7** AI tự ghi + vùng đỏ | `2026-09-28-ai-digital-worker` | 5a → 5b → 5c → 6a → 6b | XONG | P6 xong | **Chỉ staging** tới khi xong S-L1…S-L4 (pháp lý) |
| ☐ | **P8a** Rà lại toàn bộ phần AGY làm | `2026-09-30-ra-soat-agy` (tạo khi chạy) | A1 ∥ A2–A5 → A6 | theo `02d` | — | Kiểm mọi AC P1–P7 bằng chạy thật + rà code; lỗi mới **không tự sửa**, đề xuất P9 chờ Duy. Kế hoạch + prompt: `2026-09-30-sua-loi-review/02d-ke-hoach-doi-claude.md` |
| ☐ | **P8** Sửa lỗi review | `2026-09-30-sua-loi-review` | 1 → 2 → 3 → 4 → 5 → 6 → 7 | SẴN SÀNG CODE | P7 xong | Sửa lỗi 3 báo cáo review 30/09 (`2026-09-30-review-p1-p7`). **Chặn deploy staging tới khi P8 Lô 1–5 xong.** Lô 4 (chứng từ đảo doanh thu) và Lô 5 (trả NCC) có migration. Nhánh `main` |

## Việc của Duy (không phải code)
| Khi nào | Việc |
|---|---|
| Sau P8 Lô 4 lên staging/production | Chạy `manage.py backfill_credit_notes` (dry-run), xem lô đã chốt bị đổi số, rồi mới `--apply` |
| Trước P2 | Đổi 02c AI sang SẴN SÀNG CODE (ghi rõ "P2"); chạy spike DW-02 trên máy Android/Windows ≥ 8GB |
| Trước P4 | Ghi 3 quyết định vào `doc/decisions.md`: trạng thái "Chờ xác nhận", Group `cskh`, luật tự huỷ đơn không liên lạc được. Gán nhân viên vào `cskh` |
| Trước P4 Lô 3 lên production | `legal-vn` duyệt câu thông báo huỷ, câu báo trước ở checkout, quy định ghi nhãn trên tem. Tạo Cloud Run Job + lịch 5 phút cho `process_cskh_deadlines`, đặt `SHOP_HOTLINE` |
| Trước P6 lên production | Chốt chủ thể pháp lý của Lộc, đặt biến `SELLER_*` (không đưa vào repo); soạn nội dung các trang chính sách trong CMS; checklist D1–D11 trong `2026-09-28-khung-go-live/01-analysis.md` §6 |
| Trước P7 | Hoàn tất S-L1…S-L4: hồ sơ phân loại rủi ro AI, thông báo Bộ KH&CN, hợp đồng không-huấn-luyện với nhà cung cấp cloud, thoả thuận Duy–Lộc |
| Mỗi phase | Đổi trạng thái 02c → SẴN SÀNG CODE; duyệt kết quả QA; quyết định deploy (đội hiện thực không tự deploy) |

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
| 2026-09-29 06:45 | P4 | Lô 1 | APPROVED | `e874966` | 824 | CS-01 nhóm cskh + phạm vi PII, CS-02 bảng phiếu giao, CS-03 soạn hàng |
| 2026-09-29 12:30 | P4 | Lô 2 | APPROVED | `8415ce0` | 843 | CS-04 chờ xác nhận, CS-05 hàng chờ gọi, CS-06 ghi kết quả, CS-11 tem 100x150 |
| 2026-09-29 13:10 | P4 | Lô 3 | APPROVED | `fd515a5` | 880 | CS-07 chuyển Quản lý, CS-08 tự huỷ (cờ tắt), CS-09 nhắc gọi báo hoàn, CS-10 báo khách |
| 2026-09-29 13:52 | P4 | Lô 4 | APPROVED | `02babc5` | 907 | CS-12 đổi người nhận, CS-13 khách muốn huỷ/đổi, CS-14 in lại/huỷ tem, CS-15 cần chú ý |
| 2026-09-29 14:30 | P5 | Lô 1 | APPROVED | `69f6c3b` | 920 | CMS-01 phân quyền 8 quyền content, CMS-02 chuyên mục, BusinessError.extra |
| 2026-09-29 15:40 | P5 | Lô 2 | APPROVED | `e312e5c` | 948 | CMS-03 soạn & lưu nháp, CMS-05 ảnh 3 cỡ WebP giữ 4:3, không EXIF |
| 2026-09-29 16:30 | P5 | Lô 3 | APPROVED | `9c03606` | 967 | CMS-07 đăng bài checklist, CMS-08 quét SĐT/giá vốn, CMS-13 bài viết công khai |
| 2026-09-29 17:15 | P5 | Lô 4 | APPROVED | `cb8befb` | 974 | CMS-12 gỡ bài (410, lý do), CMS-10 sửa nháp bài đang đăng & huỷ thay đổi |
| 2026-09-29 17:50 | P5 | Lô 5 | APPROVED | `adb66b9` | 980 | CMS-15 trang go-live (privacy/terms/refund/seller_info), golive-status, footer-links |
| 2026-09-29 18:20 | P5 | Lô 6 | APPROVED | `91318b4` | 987 | CMS-06 thẻ mặt hàng live catalog, CMS-14 danh sách bài & khối Bài mới Landing |
| 2026-09-29 19:05 | P5 | Lô 7 | APPROVED | `38dc277` | 997 | CMS-09 gửi duyệt & trả về, CMS-11 lịch sử phiên bản & khôi phục, CMS-04 tự lưu nháp |
| 2026-09-29 19:35 | P6 | Lô 1 | APPROVED | `3667428` | 1002 | GL-01 footer thông tin người bán từ env, GL-02 footer link các trang chính sách |
| 2026-09-29 19:50 | P6 | Lô 2 | APPROVED | `9fe0954` | 1012 | GL-03 ô đồng ý xử lý dữ liệu ở checkout, consent timestamp & policy version |
| 2026-09-29 20:35 | P6 | Lô 3 | APPROVED | `10cf61e` | 1019 | GL-05 bằng chứng đồng ý trên ERP, GL-04 thông báo gọi xác nhận kèm 4 số cuối |
| 2026-09-29 22:15 | P7 | Lô 5a | APPROVED | `1ff0b3f` | 1032 | DW-18 huỷ phiếu nhập (BR-MH-07, V-DW2), DW-20 trần của Chủ (caps) |
| 2026-09-29 23:00 | P7 | Lô 5b | APPROVED | `9da8661` | 1032 | DW-19 mức B hoàn tác 10m, DW-21 trì hoãn ghi + management command |
| 2026-09-29 23:45 | P7 | Lô 5c | APPROVED | `2a9f4de` | 1044 | DW-22 báo cáo AI cuối ngày cho Chủ, DW-23 chuyển việc + nút Nhờ |
| 2026-09-30 00:30 | P7 | Lô 6a | APPROVED | `3676bf4` | 1051 | DW-24 công tắc vùng đỏ của Chủ, DW-25 AI chốt lô trì hoãn 30 phút |
| 2026-09-30 01:10 | P7 | Lô 6b | APPROVED | `f8df5f7` | 1058 | DW-27 xác nhận hoàn luôn chuyển Chủ, DW-26 khớp tuyệt đối job Hệ thống |

