# QA — TEM-01 (tem 4 số cuối SĐT) + L2 · lần 1 · 10/10/2026

## Kết luận: APPROVED — AC1–AC6 và L2 đều có bằng chứng chạy thật trên BE thật + trình duyệt; e2e đỏ trước đó là lỗi môi trường, không phải lỗi nhánh.
## Tổng: 53 ca · ✅ 53 · ❌ 0 · ⏸ 0
(13 dạng SĐT qua API + 4 ca quyền + 3 ca hồi quy API + 10 kiểm tra DOM tem + 16 ca L2 + 6 lượt ed_batch4 (3 nhánh, 3 main) + 1 lượt permissions_real_backend 33/33.)

Môi trường: HEAD `db99007`, BE `runserver` SQLite tạm + `seed_qa` (dữ liệu giả, `DJANGO_DEBUG=1`), FE build `USE_MOCK=0` trỏ BE local, server tĩnh `ThreadingHTTPServer`.

## Theo AC
| Mã AC | Kết quả | Bằng chứng |
|---|---|---|
| AC1 `0901234567` → `xxxxxx4567` | ✅ | API `GET /api/delivery/notes/2/label/` bằng token `qa_warehouse`: 200, `xxxxxx4567`; không chữ số nào khác ngoài `4567`; JSON toàn phần không chứa số đủ/phần đầu số |
| AC2 chuẩn hoá `+84 901 234 567`, `84901234567`, `090.123.4567`, `0901 234 567`, `(090) 123-4567`, `+84-90-123.45.67` | ✅ | cả 6 dạng → `xxxxxx4567` (API) |
| AC3 rỗng / `   ` / `abc` / `12` / `123` | ✅ | cả 5 → 200 `***`, không lỗi. Biên đúng 4 chữ số `1234` → `xxxxxx1234` |
| AC4 hàng chờ gọi xác nhận, content scan, AI không đổi | ✅ | `GET /api/confirmation/queue/` (`qa_cs1`) vẫn `09xx xxx 004`, không có `xxxxxx…`; `manage.py test apps.common apps.content.body` Ran 284 OK; diff chỉ đụng `labels/services.py` (không đổi `mask_phone`); grep FE/e2e: mọi `09xx xxx` còn lại thuộc hàng chờ/content |
| AC5 mock + màn in tem | ✅ | Màn `/print/label/?note=2` build `USE_MOCK=0` trỏ BE local: hiện `xxxxxx4567` (390px, 1280px), `***` với `12` và rỗng; DOM, localStorage, sessionStorage, URL, console không chứa số đủ (10/10). Mock: `ed_batch4_delivery.py` ca "Tem: SĐT chỉ 4 số cuối" PASS 3/3 lượt |
| AC6 không API khác trả thêm chữ số; log không SĐT | ✅ | Diff chỉ 1 file service BE; log `runserver` của cả phiên (có gọi tem, hàng chờ, phiếu giao) grep `0\d{9}`, `+84`, `xxxxxx` = 0 dòng. Phiếu giao của NV giao (`qa_courier1`, phiếu 3) vẫn trả `phone` đủ như trước (hành vi cũ, không đổi); phiếu của người khác 404 |
| L2 bảng Thành viên | ✅ | `e2e/permissions_real_backend.py` 33/33; kịch bản riêng `l2_real.py` 16/16 (dưới) |

## Ngoại lệ & biên
- SĐT rỗng ở cả phiếu lẫn đơn (không còn gì để rơi về) → `***`. SĐT chỉ chữ cái → `***`. Đúng 4 chữ số → `xxxxxx1234`.
- Tem huỷ/chưa xác nhận: không thuộc phạm vi đổi, test BE đầy đủ do điều phối chạy.
- L2, tên đăng nhập 52 và 150 ký tự (tài khoản giả `qa_aaa…`/`qa_bbb…`, tạo bằng ORM trên DB tạm, đã xoá cùng DB) ở `/permissions/detail/?group=warehouse_staff`, đăng nhập `qa_owner`:
  - 360px: không cuộn ngang trang, không cuộn ngang khung (khung 326px, bảng 340px nằm trong khung), tên 150 ký tự xuống 6 dòng, cả 5 nút "Bỏ khỏi nhóm" nằm trong khung và nhận được click (`elementFromPoint`), bấm nút của người 150 ký tự mở hộp "Bỏ … khỏi nhóm…" với "Quay lại"/"Bỏ khỏi nhóm". Cột "Nhóm khác"/"Vào nhóm lúc" ẩn ở 360px theo thiết kế sẵn (`lt-hb-720`, nhãn nhóm khác hiện dạng thẻ dưới tên), không phải bị che.
  - 1280px: cùng các kiểm tra, đạt; ảnh cho thấy tên 150 ký tự xuống 3 dòng, nút nằm cột phải.
  - Ảnh: scratchpad `t4/l2real_360.png`, `l2real_1280.png`, `l2real_360_click.png`, `label_390.png`.
- Lưu ý đo: lần đo đầu báo "nút bị che" do `elementFromPoint` ngoài khung nhìn (lỗi kịch bản QA, không phải lỗi sản phẩm); đã sửa kịch bản cuộn từng nút vào giữa rồi mới đo.

## Phân quyền (API tem)
| Người | Kết quả |
|---|---|
| `qa_warehouse` (có `print_label`) | 200 |
| `qa_courier1`, `qa_cs1`, `qa_nogroup` | 403 |
| Chưa đăng nhập | 401 |

## Rò giá vốn
Nhánh không đụng field tiền. JSON tem không có khoá giá vốn (kiểm khoá `recipient_phone_masked` + toàn JSON không chứa số đủ).

## Rò dữ liệu cá nhân
- Tem: chỉ 4 số cuối. DOM trang in không chứa SĐT đủ hay phần đầu; localStorage/sessionStorage/URL/console sạch.
- Log BE không chứa SĐT. Dữ liệu dùng toàn bộ là giả (`seed_qa`, SĐT giả `0900000xxx`, số thử `0901234567`).
- Ghi nhận ngoài phạm vi (không phải lỗi của nhánh): tem vẫn in tên và địa chỉ người nhận (cần cho giao hàng, hành vi cũ); hàng chờ gọi xác nhận trả `phone` đủ cho người trong phạm vi như trước (AC4 yêu cầu không đổi).

## Hồi quy
| Hạng mục | Kết quả |
|---|---|
| `e2e/ed_batch4_delivery.py` chạy 3 lần trên nhánh (server `ThreadingHTTPServer`, cổng riêng) | 70/70 PASS ×3 |
| Cùng kịch bản (bản của `main` `3d2a3ca`, build mock từ `git archive`) 3 lần | 70/70 PASS ×3 |
| `e2e/permissions_real_backend.py` (BE thật) | 33/33 PASS |
| `manage.py test apps.common apps.content.body` | Ran 284 OK |
| Số liệu điều phối (không chạy lại): BE 3572 OK, vitest 1330 PASS, tsc sạch | tham chiếu |

Kết luận mục 4: đỏ do fe-dev thấy (timeout, `ERR_SOCKET_NOT_CONNECTED`, ED-17-AC7/G5/AC2) là **lỗi môi trường** — `http.server` đơn luồng của Python rớt kết nối khi trình duyệt mở nhiều kết nối song song. Với `ThreadingHTTPServer` (`request_queue_size=256`), cả nhánh lẫn `main` đều 70/70 ở cả 3 lượt; nhánh không gây lỗi. Đề xuất: sửa header kịch bản (dòng 2) dùng server đa luồng thay `python3 -m http.server`.

## Lỗi
Không có lỗi chặn. Không có lỗi Low.

## Lệnh đã chạy (tóm tắt)
- `migrate` + `seed_qa` trên SQLite tạm; `runserver 8741 --noreload`.
- `api_label.py`: 13 dạng SĐT → 13/13; quyền 403/403/403/401.
- `api_reg.py`: hàng chờ `09xx xxx nnn`; NV giao thấy `phone` đủ ở phiếu mình, 404 phiếu người khác.
- `manage.py test apps.common apps.content.body` → Ran 284 OK.
- `NEXT_PUBLIC_USE_MOCK=0 NEXT_PUBLIC_API_BASE=http://127.0.0.1:8741 npm run build` (exit 0) → `label_e2e.py` 10/10; `permissions_real_backend.py` 33/33; `l2_real.py` 16/16.
- Build mock nhánh + build mock `main` (git archive) → `ed_batch4_delivery.py` 3 lượt mỗi bên, đều 70/70.
- Dọn: tắt BE + 4 server tĩnh, xoá DB tạm, tài khoản giả, bản sao `out`, thư mục `main`.
- Cuối lượt: `NEXT_PUBLIC_USE_MOCK=0 NEXT_PUBLIC_API_BASE=https://cangca-api-staging-675411800433.asia-southeast1.run.app npm run build` exit 0; `out/` chứa URL staging, không còn `127.0.0.1:8741`.
