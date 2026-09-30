# P8 — kế hoạch chạy bằng đội Claude
> Claude (điều phối) · 2026-09-30 · Thay AGY theo yêu cầu Duy 30/09. Phiếu giao việc từng lô vẫn là `02c-giao-viec.md`;
> file này ghi **ai làm gì, theo thứ tự nào, kiểm ở đâu**.

## Đội
| Vai | Agent | Model | Việc trong P8 |
|---|---|---|---|
| Điều phối | phiên chính | Opus 5.5 | giao việc, **tự chạy lại lệnh kiểm chứng**, đọc migration, commit + push |
| BE | `be-dev` | Sonnet 5.5 | story BE theo TDD, bắt đầu từ test tái hiện đỏ |
| FE | `fe-dev` | Sonnet 5.5 | story FE (SR-02, SR-07, SR-09, Lô 5–7), kèm spec Playwright |
| Tech Lead | `techlead` | Opus | review diff từng lô trước QA; chốt lệch contract |
| QA | `qa-tester` | Sonnet 5.5 | theo luật siết 30/09; viết `04-qa-report.md` theo lô |
| Pháp lý | `legal-vn` | Opus | chỉ khi lô đụng văn bản cho khách (không dự kiến trong P8) |

## Vòng một lô
```
git pull → kiểm chứng gốc → be-dev ∥ fe-dev → điều phối chạy lại kiểm chứng
→ techlead review → qa-tester → (REJECTED: giao lại dev) → APPROVED → commit + push main → ☑ 02c
```
Điều phối không đánh "xong" khi chưa dán output lệnh kiểm chứng trong lượt đó.

## Thứ tự và điểm kiểm riêng
| Lô | Song song | Test tái hiện giao kèm | Điều phối tự kiểm thêm | Dừng hỏi Duy khi |
|---|---|---|---|---|
| 1 | be-dev (SR-01, SR-03) ∥ fe-dev (SR-02) | R1 (AI chốt lô bán rồi, job kẹt); SR-01 chưa có repro → be-dev viết test quét trước | `npm ci` sạch ở cả hai FE; quét AuditLog không còn khoá tiền lọt | `@types/node ^22` kéo > 5 file sửa type |
| 2 | be-dev (SR-04+05 cùng commit, SR-06) ∥ fe-dev (SR-07) | — | test quét PII thấy retrieve chạy > 0 lần; `sessionStorage` không có giá mua | quét thấy PII ngoài `customer`/dashboard |
| 3 | be-dev; fe-dev nhỏ (SR-09) | R2 (CSKH xác nhận sau tự huỷ), R3 (mở bán sau huỷ phiếu nhập), R4 (nhắc Chủ lặp), R5 (huỷ lô quá hạn còn giữ hàng) | chạy lại repro 2 lần (job chạy lặp) | — |
| 4 | be-dev | R6 (P&L sau tự huỷ đơn đã trả) | đọc file migration (chỉ `CreateModel`); `backfill_credit_notes` dry-run trên DB test | migration có thay đổi ngoài 2 model mới; lệch làm tròn BR-BH-15 |
| 5 | be-dev ∥ fe-dev | — | đọc migration; dashboard không còn tên/4 số cuối SĐT với mọi Group | test cũ ngoài S04 đỏ vì bỏ ngoại lệ EXPIRED |
| — | **Báo Duy: đã mở chặn deploy staging** (chỉ deploy khi Duy yêu cầu) | | | |
| 6 | be-dev ∥ fe-dev ∥ qa-tester (Playwright bù) | — | `check-ai-chunks.mjs` exit 0 | — |
| 7 | be-dev ∥ fe-dev | — | build hai FE sau khi xoá spike | — |
| Cuối | `techlead` rà lại toàn bộ mã lỗi BM/F trong 3 báo cáo review → bảng "đã sửa / còn" | | | |

## Không làm
Không deploy, không chạy `backfill_credit_notes --apply` (chỉ Duy), không sửa `doc/decisions.md`, `02*.md`,
không force-push. AGY tạm dừng (`AGENTS.md`), nên hai bên không cùng push.

## Chi phí dự kiến
Code và test chạy bằng Sonnet 5.5 ($2/$10 mỗi triệu token), còn Opus chỉ dùng cho điều phối và review. Mỗi lô
thường có 3–4 lượt subagent; lô bị REJECTED thêm 1–2 lượt.
