# QA — AI Native ERP · 2026-09-27

> File này là nơi ghi số đo hiệu năng của các lô (cổng 02b Phụ lục C.4, BR-AI-17).
> **KHÔNG XOÁ baseline động bên dưới** — các lô sau ghi thêm số đo mới vào mục kế tiếp, đối chiếu với mốc này.

## Baseline động (trước AI — chụp 2026-09-27)

Kết luận: **BASELINE ĐÃ CHỤP — các ngưỡng đo được đều ĐẠT** (C.4 #5, #6). Lưu ý: console đo trên
trang **Đăng nhập** chứ chưa phải màn Tổng quan — **bị chặn đăng nhập** (staging chưa có tài khoản thử;
xem mục "Điều kiện đo"). Code AI chưa merge (0 lần `wllama/vosk/whisper` trong repo — baseline tĩnh C.1 vẫn đúng).

### Bảng số đo (Lighthouse 13.5.0, mô phỏng throttling, trung vị của 3 lượt; ngoặc = khoảng min–max)

| Trang (staging) | Cấu hình | TTI | TBT | LCP | FCP | Ghi chú |
|---|---|---|---|---|---|---|
| Console `/login/` | desktop | **1018,6 ms** (980,7–1062,8) | 0 ms | 1018,6 ms | 1018,6 ms | Bị chặn đăng nhập → đo trang Đăng nhập thay Tổng quan |
| Console `/login/` | mobile (slow 4G) | 2829,2 ms (2108,0–2860,0) | **0 ms** (0–0) | 2829,2 ms | 2679,2 ms | LCP mobile cao do Google Fonts render-blocking (xem ghi chú) |
| Shop `/shop/` | desktop | **275,3 ms** (275,1–388,0) | 0 ms | 275,3 ms | 275,1 ms | Tham khảo (Shop không có ngưỡng TTI) |
| Shop `/shop/` | mobile (slow 4G) | 1117,1 ms (959,3–1301,4) | 0 ms (0–166) | **1117,1 ms** (959,3–1301,4) | 832,3 ms | |
| Landing `/` | mobile (slow 4G) | 956,2 ms (869,0–1043,4) | 17,8 ms (0–35,5) | **913,9 ms** (857,4–970,4) | 882,4 ms | |

### Mốc so ngưỡng C.4 (02b-tech-design.md)

| # | Chỉ số | Ngưỡng | Số đo baseline | Kết quả |
|---|---|---|---|---|
| 5 | TTI console desktop | < 2000 ms | 1018,6 ms (trang Đăng nhập) | **ĐẠT** — nhưng chưa đo được màn Tổng quan (thiếu tài khoản thử) |
| 5 | TBT console mobile | < 200 ms | 0 ms (trang Đăng nhập) | **ĐẠT** |
| 6 | LCP Landing mobile (slow 4G) | < 2500 ms | 913,9 ms | **ĐẠT** |
| — | LCP Shop mobile (slow 4G) | (tham khảo) | 1117,1 ms | Dưới 2500 ms |
| — | TTI Shop desktop | (tham khảo) | 275,3 ms | Dưới 2000 ms |

Ghi chú đáng theo dõi (không phải ngưỡng của C.4, không chặn):
- **Console mobile LCP 2829 ms** (> 2500 ms) ngay trên trang Đăng nhập: do 2 stylesheet Google Fonts
  render-blocking (`erp-console/app/layout.tsx` — Inter/JetBrains Mono `display=swap` + Material Symbols
  `display=block`), trang login tải **4,15 MB** (chủ yếu font woff2). Đã được ghi nhận ở 02b C.1 và K8
  (việc perf độc lập, đề xuất làm ở Lô 1). Màn Tổng quan dùng chung layout nên khả năng cao cùng mức LCP mobile.

### Điều kiện đo

| Yếu tố | Giá trị |
|---|---|
| Thiết bị | MacBook Pro, Apple M1, **8 GB RAM**, macOS (Darwin 25.6.0) |
| Chrome | **154.0.8037.57** (chế độ headless=new, cùng bản Chrome cài trên máy) |
| Lighthouse | 13.5.0 (CLI, `--only-categories=performance`, `throttling-method=simulate` mặc định) |
| Cấu hình mô phỏng | desktop: RTT 40 ms / 10240 kbps / CPU 1×; mobile: RTT 150 ms / 1638,4 kbps (**slow 4G**) / CPU 4× |
| Mạng đo | **Wi-Fi** (en0, 802.11ac, 5 GHz, gateway 192.168.2.253), egress Viettel AS7552 (TP.HCM), RTT tới 8.8.8.8 ≈ **89 ms** |
| Mạng so với quy ước | C.4 #5 lấy **Wi-Fi văn phòng làm ngưỡng chặn**. Mạng đo hiện tại KHÔNG xác định được có phải Wi-Fi văn phòng không (egress dân dụng Viettel, RTT 89 ms khá cao so với cáp quang văn phòng) → coi là mốc **THAM KHẢO**; lô sau nên đo lại trên Wi-Fi văn phòng để so khớp điều kiện. Không đo được mạng 4G từ máy này (MacBook không có modem) |
| Cache | Mỗi lượt đo chạy trên **profile Chrome mới** (cache trình duyệt lạnh — đúng ngữ nghĩa "lượt truy cập đầu"); server Cloud Run staging làm ấm trước bằng curl `/api/shop/catalog/` (lần đầu 1,8 s cold start → 0,37 s) để loại nhiễu cold start khỏi phép đo FE |
| Số lượt | 3 lượt mỗi cấu hình (Landing 2 lượt), lấy trung vị; JSON kết quả lưu ở `scratchpad/qa-perf-baseline/runs-cold/` |

### Về "bị chặn đăng nhập" (console)

- Staging **không có tài khoản thử** được dùng: không thấy tài khoản nào trong hồ sơ/ops doc; tài khoản
  QA của lô trước (`loc` / mật khẩu QA, chỉ tồn tại ở DB QA local `qa2.sqlite3`) thử đăng nhập staging
  → API trả `400 "Không thể đăng nhập với thông tin đã nhập."` → **đo trang Đăng nhập thay cho màn Tổng quan**.
- Lô 1 QA khi có tài khoản thử staging: đo lại TTI desktop + TBT mobile trên **màn Tổng quan**
  (`/overview/`) và ghi tiếp vào file này, đối chiếu với số đo trang Đăng nhập ở trên.

### Lệnh đã chạy (tóm tắt)

```bash
# chuẩn bị công cụ đo (scratchpad/qa-perf-baseline/, cache npm riêng trong /tmp)
npm install lighthouse            # 13.5.0
# warm-up server staging
curl "https://cangca-api-staging-675411800433.asia-southeast1.run.app/api/shop/catalog/"   # 200
# mỗi lượt: Chrome headless profile mới trên CDP :9224 → lighthouse --port=9224
#   console login:  --preset=desktop ×3 ; --form-factor=mobile ×3   (LH 13 đã bỏ --preset=mobile)
#   shop /shop/:   --preset=desktop ×3 ; --form-factor=mobile ×3
#   landing /:     --form-factor=mobile ×2
```

Ràng buộc tuân thủ: không sửa code sản phẩm, không commit/push, không chạy test suite/E2E,
không ghi dữ liệu cá nhân thật vào báo cáo (chỉ trang công khai + trang Đăng nhập, tài khoản thử giả).

---

## Các lô sau ghi tiếp vào đây
<!-- Lô 1: điền bảng delta JS (#1-#4), TTI/TBT console Tổng quan (#5), LCP Landing (#6)… đối chiếu mốc baseline trên. -->
