---
description: Làm phase kế tiếp trong doc/ke-hoach-tong.md — tìm phase đầu tiên chưa ☑ có 02c SẴN SÀNG CODE rồi chạy như /lam-tinh-nang
---

1. `git pull`. Đọc `AGENTS.md` và `doc/ke-hoach-tong.md`.
2. Tìm phase **đầu tiên** trong bảng "Thứ tự phase" chưa ☑. Kiểm "Điều kiện bắt đầu" của phase đó đã đạt
   (phase trước ☑, lô phụ thuộc ☑) và `02c-giao-viec.md` của hồ sơ ở trạng thái `SẴN SÀNG CODE`.
   - Chưa đạt → báo Duy một dòng: phase nào, thiếu gì (vd "P2 chờ Duy đổi 02c sang SẴN SÀNG CODE"). Dừng.
   - Không nhảy cóc sang phase sau dù phase sau đã sẵn sàng.
3. Đạt → làm đúng quy trình `.agents/workflows/lam-tinh-nang.md` với slug hồ sơ đó, **chỉ các lô thuộc phase này**
   (cột "Lô" của bảng; với hồ sơ AI, lọc theo cột Phase trong 02c).
4. Xong phase: đánh ☑ ở bảng `doc/ke-hoach-tong.md`, commit + push, báo Duy phase kế tiếp và việc Duy cần làm
   trước phase đó (mục "Việc của Duy").
