# Test tái hiện review 30/09 (R1–R6)

Các test này **đỏ** trên code trước P8 (chứng minh lỗi có thật). Vì vậy chúng không nằm trong `backend/`, để
suite chính vẫn xanh. Dữ liệu trong test đều là dữ liệu giả.

| Mã | Lỗi | Story P8 |
|---|---|---|
| R1 | AI chốt lô đã từng bán: `safety.py` văng FieldError, job `run_due_ai_actions` kẹt | SR-03 (Lô 1) |
| R2 | CSKH xác nhận được phiếu gọi hoàn sau khi đơn đã tự huỷ | SR-10 (Lô 3) |
| R3 | Mở bán được lô sau khi phiếu nhập đã huỷ | SR-09 (Lô 3) |
| R4 | Nhắc Chủ lặp lại mỗi lần quét | SR-11 (Lô 3) |
| R5 | Huỷ lô quá hạn trong khi còn đơn giữ hàng | SR-08 (Lô 3) |
| R6 | Lãi lỗ sai sau khi tự huỷ đơn đã trả tiền | SR-12/13 (Lô 4) |

Chạy (từ thư mục `backend/`, dùng scratchpad làm gói tạm):
```bash
S=<scratchpad>; mkdir -p $S/review_repro && touch $S/review_repro/__init__.py
cp ../doc/features/2026-09-30-sua-loi-review/repro/review_repro_tests.py $S/review_repro/tests.py
PYTHONPATH=$S DJANGO_DEBUG=1 env -u DATABASE_URL .venv/bin/python manage.py test review_repro.tests
```
Khi sửa một story, `be-dev` chuyển test tương ứng vào `backend/apps/<app>/tests/` (sửa assert theo hành vi đúng),
để nó thành test hồi quy thật.
