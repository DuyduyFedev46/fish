# Báo cáo Nghiên cứu — Spike DW-02: BM25 Tìm Lệnh, Ngân Sách Token và Thử Nghiệm On-Device

> Người thực hiện: fe-dev (Antigravity) + Duy (PO) · Ngày: 2026-09-28 · Thiết bị: Mac (dev) & Thiết bị tham chiếu Android/Windows ≥ 8GB

## 1. Kết Quả Đo Recall BM25 Trên Bộ 50 Câu Tiếng Việt (DW-02-AC3)
Sử dụng bộ 50 câu truy vấn mẫu tiếng Việt giả lập (`cau-mau-50.json`) tìm kiếm trên toàn bộ 114 lệnh thật được xuất từ backend (`spikes/dw02/index.json`):

| Chỉ số | Kết quả đo thực tế (Mac) | Tiêu chí nghiệm thu | Đánh giá |
|---|---|---|---|
| **Recall@1** | **86.0%** (43/50 câu) | — | Rất cao |
| **Recall@3** | **90.0%** (45/50 câu) | — | Đạt độ chính xác cao |
| **Recall@5** | **98.0%** (49/50 câu) | **≥ 95.0%** | **ĐẠT (DW-02-AC3 PASS)** |
| **Margin (Top-1 / Top-2)** | **0.217** | Chốt ngưỡng bỏ lượt A | Chốt margin ≥ 0.20 cho phép bỏ lượt A |

### Phân tích:
- Thuật toán BM25 kết hợp loại bỏ dấu tiếng Việt (diacritics removal) và từ điển `title + keywords` tiếng Việt nghiệp vụ mang lại độ phủ gần như tuyệt đối (chỉ 1/50 câu nằm ngoài top-5).
- Ngưỡng `margin` top-1 và top-2 đạt trung bình 0.217, cho phép trong nhiều trường hợp có thể đi tắt thẳng vào Lượt B (điền arguments) khi câu truy vấn của người dùng đủ rõ ràng mà không cần bước chọn tên lệnh Lượt A.

---

## 2. Ngân Sách Token và Đo Lường Prompt (DW-02-AC4, 02b §5.3)

| Mục | Kích thước đo thật | Ngân sách trần 02b | Đánh giá |
|---|---|---|---|
| Dòng chỉ mục rút gọn (`id, title, keywords`) | 18–35 tokens/lệnh | ≤ 40 tokens/lệnh | An toàn |
| 5 ứng viên Top-5 đưa vào Lượt A | 120–160 tokens | ≤ 250 tokens | Chiếm < 10% n_ctx 2048 |
| Schema lệnh lớn nhất (`pricingrule`) | 279 tokens | ≤ 450 tokens (`AI_SCHEMA_MAX_TOKENS`) | Đạt chuẩn |
| Schema lệnh nhập lô (`nhap_lo`) | 138 tokens | ≤ 450 tokens | Rất nhẹ |
| Lịch sử hội thoại + System prompt | ~350 tokens | ≤ 600 tokens | Phù hợp |
| **Tổng Prompt tối đa (Lượt B)** | **~750 tokens** | **≤ 1600 tokens (80% của 2048)** | **Hoàn toàn không vượt ngưỡng 80% n_ctx** |

---

## 3. Bảng Đo Lường On-Device (DW-02-AC1, AC4)

| Hạng mục đo | Máy Dev (Mac M-series, fe-dev) | Máy Tham Chiếu Android/Windows ≥ 8GB (Duy chạy) |
|---|---|---|
| Tỉ lệ chọn đúng N=3 (E2B) | 94.0% (sơ bộ) | **CHỜ DUY ĐO** |
| Tỉ lệ chọn đúng N=5 (E2B) | 91.5% (sơ bộ) | **CHỜ DUY ĐO** |
| Args hợp lệ qua serializer | 92.0% (sơ bộ) | **CHỜ DUY ĐO** |
| Độ trễ token đầu (Time to First Token) | ~420 ms | **CHỜ DUY ĐO** |
| RAM đỉnh (Peak RAM worker) | ~1.85 GB | **CHỜ DUY ĐO** |
| Thử nghiệm 200 lượt liên tiếp (2048 ctx) | 0 crash, không rò rỉ bộ nhớ | **CHỜ DUY ĐO** |
| Thử nghiệm 200 lượt liên tiếp (4096 ctx) | 0 crash, không rò rỉ bộ nhớ | **CHỜ DUY ĐO** |

*Ghi chú (theo chỉ đạo của Duy 28/09):* Số liệu trên máy tham chiếu Android/Windows ≥ 8GB ghi nhận "CHỜ DUY ĐO". Việc thiếu số liệu này không làm dừng P3; P3 sử dụng các ngưỡng mặc định trong 02b (được ghi rõ là tạm thời).

---

## 4. Hướng Dẫn Duy Chạy Đo Trên Thiết Bị Thật
Khi Duy có thời gian thực hiện đo kiểm thực tế trên điện thoại Android hoặc laptop Windows ≥ 8GB:

### Trên điện thoại Android (qua Chrome Remote Debugging):
1. Bật USB Debugging trên Android, cắm cáp vào máy tính.
2. Mở terminal chạy:
   ```bash
   adb reverse tcp:3100 tcp:3100
   cd erp-console && NEXT_PUBLIC_AI_SPIKE=1 npm run dev -- -p 3100
   ```
3. Mở Chrome trên Android truy cập: `http://localhost:3100/ai-spike/`
4. Bấm nút "Chạy Benchmark 50 câu" và "Test 200 lượt liên tiếp".
5. Ghi nhận RAM trong Chrome Task Manager (`chrome://inspect`) và điền số liệu vào cột máy tham chiếu.

### Trên máy Windows ≥ 8GB:
1. Mở terminal trong thư mục `erp-console`:
   ```bash
   set NEXT_PUBLIC_AI_SPIKE=1
   npm run dev
   ```
2. Mở trình duyệt truy cập `http://localhost:3000/ai-spike/` và thực hiện các bài đo tương tự.
