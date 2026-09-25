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
