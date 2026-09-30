---
name: tdd-workflow
description: Quy trình Red-Green-Refactor và cổng "chứng cứ trước khi tuyên bố xong" cho Cá Về. Dùng khi viết tính năng mới, sửa bug, hay refactor ở backend/adapter — và trước khi báo bất kỳ việc gì là "xong", "đã sửa", "test xanh".
---

# TDD + xác minh trước khi báo xong

Nguồn: `test-driven-development`, `verification-before-completion`,
`systematic-debugging` (obra/superpowers). Rút gọn, giữ nguyên tinh thần.

## Luật sắt

```
KHÔNG CÓ CODE NGHIỆP VỤ NẾU CHƯA CÓ TEST ĐỎ TRƯỚC
KHÔNG TUYÊN BỐ "XONG" NẾU CHƯA CHẠY LỆNH KIỂM CHỨNG TRONG CHÍNH LƯỢT NÀY
```

## Vòng lặp

1. **RED** — viết 1 test nhỏ nhất mô tả hành vi mong muốn (lấy từ một AC, đặt tên test có
   mã AC/BR, vd `test_s1_ac2_nv_giao_khong_xem_gia_von`). Chạy → **phải đỏ, đỏ đúng lý do**
   (assert sai, không phải lỗi import/typo). Xanh ngay = test không kiểm gì → viết lại.
2. **GREEN** — code tối thiểu để xanh. Không thêm tính năng "tiện thể".
3. **REFACTOR** — dọn trùng lặp, đặt tên lại; chạy lại, vẫn xanh.
4. Lặp cho AC tiếp theo. Cuối cùng chạy **toàn bộ** test suite của app, rồi của cả backend.

Ngoại lệ (phải nói rõ với Duy): file cấu hình, migration sinh tự động, prototype vứt đi.

## Sửa bug

1. Tái hiện bằng một test đỏ trước khi đọc code để sửa.
2. Tìm nguyên nhân gốc (đọc lỗi đầy đủ, khoanh vùng, so với code chạy đúng) — không vá triệu chứng.
3. Tối đa 3 giả thuyết sai liên tiếp → dừng, báo lại tình trạng thay vì đoán tiếp.

## Cổng kiểm chứng

| Tuyên bố | Bằng chứng cần có |
|---|---|
| Test xanh | Output `manage.py test` / `pytest` của lượt này: 0 failure |
| FE ổn | `npm run build` exit 0 (+ `npx tsc --noEmit`) |
| Không rò giá vốn | Test API với nv_kho/nv_giao chạy xanh |
| Migration ổn | `makemigrations --check --dry-run` không sinh gì mới |
| Bug đã sửa | Test tái hiện bug giờ xanh, trước đó đỏ |
| Subagent làm xong | Tự xem diff/chạy test — không tin báo cáo suông |

Cấm dùng "chắc là", "có lẽ đã", "sẽ chạy" khi báo cáo. Nếu chưa chạy được (thiếu môi
trường…), nói thẳng là **chưa kiểm chứng** và vì sao.

## Đặt tên (P8b, Duy chốt 01/10)

Định danh trong code (hàm, biến, class, module, thư mục, file, test, script, route API, khoá JSON, biến env, Group,
`data-testid`, id lệnh AI, khoá lưu trình duyệt) là **tiếng Anh chuẩn, không viết tắt tiếng Việt**. Chữ hiển thị cho người
dùng, comment, docstring và tài liệu vẫn tiếng Việt. Viết tắt chỉ dùng khi là chuẩn quốc tế: `VN`, `VND`, `pnl`, `id`, `url`.
Không đưa mã lô giao việc (`lo7`, `l8`, `p8_lo5`) vào tên; mã lô/story ghi trong docstring.

| Khái niệm | Dùng | Không dùng |
|---|---|---|
| Vai (Group) | `owner` `manager` `warehouse_staff` `delivery_staff` `customer_service` | `chu` `quan_ly` `nv_kho` `nv_giao` `cskh` |
| Người giao trên một phiếu | `courier` | `nv_giao` |
| Việc gọi xác nhận đơn | `confirmation` | `cskh` (module, route, khoá JSON, env) |
| Nhập lô | `receive_batches`, `ReceiveBatches*` | `nhap_lo`, `NhapLo*` |
| Lệnh AI: nhóm / mức nhạy cảm | `purchasing` `sales` `customer_service` / `high` `medium` `low` | `thu_mua` `ban_hang` / `cao` `trung_binh` `thap` |
| Giờ Việt Nam | `VN_TIME_ZONE`, `todayInVietnam()`, `today_in_vietnam()` | `VN_TZ`, `todayVn`, `vn_today` |
| Bản rà soát QA / bổ sung | `review_*` / `extra`, `followup` | `ra_soat_*` / `bosung` |

Giữ nguyên (không đổi): migration đã chạy, `AuditLog.action` đã ghi, dòng phiên bản cấu hình AI cũ, URL công khai Shop
`/bai-viet/` `/trang/` `?chuyen-muc=`, dữ liệu demo (username `kho1`, `chu_vua`..., slug, mã hàng), keyword AI có dấu, chuỗi `cangca`.
Bảng đầy đủ: `doc/features/2026-09-30-dat-ten-tieng-anh/02c-giao-viec.md` mục 1.

**Kiểm bằng máy** (Python 3 stdlib, chạy từ gốc repo, dưới 10 giây, không cần venv):
`python3 scripts/check_naming.py`. Exit 1 khi file MỚI có định danh tiếng Việt, hoặc số vi phạm của một file TĂNG so với
`scripts/naming_baseline.json`; in file, dòng, token. Script không xét chuỗi hiển thị, comment, docstring. Danh sách từ chặn và
allowlist ở `scripts/naming_blocklist.txt`. Chạy lệnh này trước khi báo xong mọi việc có sửa code.

**Test và kịch bản**: tên file, class, hàm test theo hành vi và viết tiếng Anh (`test_undo_window.py`,
`test_unpaid_order_cannot_ship`, `self.owner`, `warehouse_client`). Tên test vẫn mang mã AC/BR trong docstring hoặc hậu tố
khi cần truy vết, nhưng không đặt mã lô (`lo7`, `l8`, `p8_lo5`) vào tên file hay hàm. Bản rà soát của QA đặt tên `review_*`.
Test cũ tên tiếng Việt đổi dần khi chạm vào file đó, không đổi hàng loạt.

**Cổng kiểm chứng thêm**: `python3 scripts/check_naming.py` phải exit 0 trước khi báo xong. Chi tiết dùng script:
- `--update` ghi lại baseline và chỉ cho phép GIẢM; từ chối nếu có file tăng. Sau khi đổi tên dần một file, chạy `--update` để khoá thành quả.
- Đổi tên file thì dùng `git mv`; file mới kế thừa baseline của file cũ (script so với commit gần nhất sửa baseline, nên kể cả đã commit mà chưa `--update` vẫn đúng). Nên chạy `--update` trong cùng commit để khoá thành quả.
- `--report` liệt kê mọi vi phạm cũ; `--words` đếm theo từ bị chặn; `--self-test` kiểm bộ quét (chạy sau khi sửa script).
- Dòng cần giữ tên tiếng Việt vì là dữ liệu hoặc hợp đồng ngoài: thêm `# naming: allow - <lý do>` (Python) hoặc `// naming: allow - <lý do>` (TS) cuối CHÍNH dòng đó. Thiếu lý do thì không được miễn; cần techlead duyệt; `--report` in danh sách dòng đang dùng marker.
- Muốn miễn thêm một từ vào allowlist mà code sản phẩm dùng làm định danh chính thức: dừng và hỏi Duy.
