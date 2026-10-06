# Review Tech Lead — CSKH gọi xác nhận, in tem

## Review Lô 5 BE (06/10)

- **Phạm vi:** nhánh `feat/cskh-lo5`, commit `ccb0f10`, `git diff main...HEAD` (13 file). Story CS-16 (không có API mới),
  CS-17 (`GET /api/delivery/notes/lookup/`), CS-18 (`CallScript`, `/api/confirmation/scripts/`, khoá `scripts` trong chi tiết hàng chờ).
- **Đối chiếu:** `02-stories.md` CS-16…CS-18, `02b-tech-design.md` §2.6, §2.7, §3.1, §4.1, §4.6, §6, §8, §10; `03-dev-notes.md` mục Lô 5 BE.

### Kết luận: **CHANGES REQUESTED**

Không có lỗi Critical hay High. Không rò dữ liệu cá nhân, không rò giá vốn. Phân quyền 5 vai khớp bảng §3.1. Phải sửa
1 lỗi Medium (lệnh AI) và 2 lỗi Low (phạm vi dòng của `lookup`, body JSON không phải object), rồi chạy lại kiểm chứng.

### Lệnh kiểm chứng techlead tự chạy (worktree `cskh-lo5`, `DJANGO_DEBUG=1`, venv của checkout chính)

| Lệnh | Kết quả |
|---|---|
| `manage.py makemigrations --check --dry-run` | No changes detected |
| `manage.py test apps.delivery apps.ai` | Ran 647, OK |
| `manage.py test apps.accounts apps.sales apps.common` | Ran 1130, 24 errors. Cả 24 là `ValueError: Missing staticfiles manifest entry for 'admin/css/base.css'` (worktree không có `backend/staticfiles`, đúng như dev ghi). Không lỗi nào do Lô 5 |
| `python3 scripts/check_naming.py` | OK, không phát sinh vi phạm mới |

Bộ đầy đủ có symlink `staticfiles` do điều phối viên chạy lại ở bước 3.

### Lỗi phải sửa

| # | Mức | File:dòng | Lỗi | Cách sửa |
|---|---|---|---|---|
| M1 | **Medium** | `backend/apps/ai/registry/tests/snapshots/commands_index_snapshot.json:47`; `backend/apps/ai/policy/rules.py:8-22` | `delivery.deliverynote.lookup` tự lọt vào chỉ mục lệnh AI. Như vậy lệch 02b §4.1, nơi cột AI của dòng `lookup` ghi **cấm**. Dev đã cập nhật snapshot cho khớp thay vì chặn. | **Quyết định: cấm.** Thêm `"/api/delivery/notes/lookup/"` vào `FORBIDDEN_PREFIXES`, kèm comment `# tra mã tem (CS-17): thuộc nghiệp vụ tem, cấm như …/label/`. Gỡ dòng 47 khỏi snapshot. Thêm test ở `apps/ai/registry/tests/test_discovery.py`: `is_url_forbidden("/api/delivery/notes/lookup/")` là True và `delivery.deliverynote.lookup` không có trong registry. Giữ số `@action` = 30 ở `test_discipline.py`, vì test này đếm action trên viewset chứ không đếm lệnh AI. |
| L1 | Low | `backend/apps/delivery/confirmation/call_scripts.py:107`; `backend/apps/delivery/api.py:214-219` | `lookup_label` tìm bằng `DeliveryNote.objects` nên **bỏ qua Tầng 3** (`get_queryset`: NV giao chỉ thấy phiếu của mình). Endpoint cũng không kiểm `view_deliverynote`, dù 02b §4.1 ghi T1 `view_deliverynote → print_label`. Hiện chưa khai thác được vì cả ba vai có `print_label` đều xem được mọi phiếu. Nhưng phân quyền V2 cho superuser ghi quyền nhóm, nên nếu ai đó cấp `print_label` cho vai có phạm vi hẹp thì endpoint lộ id và trạng thái phiếu ngoài phạm vi. Action anh em `label` thì đi qua `get_object()`. | Truyền queryset vào service: `lookup_label(code, queryset=self.get_queryset())` và dùng `queryset.filter(code=…)`. Thêm kiểm `view_deliverynote` (403) trước `print_label`. Thêm test: user chỉ có `delivery_staff` + `print_label` tra tem của phiếu không giao cho mình → 404. |
| L2 | Low | `backend/apps/delivery/confirmation/scripts_api.py:47`, `:61` | Body JSON là mảng không rỗng (ví dụ `[1]`) thì `data.get` ném `AttributeError` → **500**. | Nếu `request.data` không phải `dict` thì raise `BusinessError("Dữ liệu gửi lên không hợp lệ.", code="INVALID_INPUT")` → 400. Thêm test cho POST và PATCH với body `[1]`. |

### Nên sửa cùng đợt (không chặn)

| # | Mức | File:dòng | Ghi chú |
|---|---|---|---|
| L3 | Low | `backend/apps/delivery/confirmation/call_scripts.py:39-41` | Kiểm `exists()` rồi `create()` thì hai request đồng thời cùng `situation` sẽ một cái vướng `IntegrityError` → 500. Bắt `IntegrityError` (trong `transaction.atomic` lồng) và đổi thành `BusinessError` có cùng thông điệp "đã có kịch bản". Chỉ Chủ ghi nên khả năng xảy ra thấp. |
| L4 | Low | `backend/apps/delivery/confirmation/call_scripts.py:98-125` | `lookup_label` là nghiệp vụ tem (BR-GH-16/07), không thuộc kịch bản gọi. Chuyển sang `apps/delivery/labels/services.py`, cạnh `get_label_data`, để dùng chung cách xác định "lần in còn hiệu lực" (`superseded_at`/`voided_at` null). `api.py` import từ `labels.services` như các action `label*`. Làm khi sửa L1, vì cùng hàm. |
| N1 | Nit | `backend/apps/delivery/confirmation/call_scripts.py:91` | `order.lines.all()` nạp toàn bộ dòng (kể cả đơn giá) chỉ để xét `bundle_snapshot`. Đủ dùng vì là endpoint chi tiết một đơn. Có thể đổi thành một truy vấn `exists()`. |
| N2 | Nit | `backend/apps/delivery/tests/test_call_scripts_and_lookup.py:125-127` | `setUp` rỗng thừa và thiếu dòng trống trước `_create`. |

### Trả lời các điểm điều phối viên hỏi

**1. Dữ liệu cá nhân: ĐẠT.**
- `lookup` trả đúng 5 khoá `note_id, status, print_no, valid_print_no, warning`, không có tên, SĐT, địa chỉ, người nhận hộ, mã đơn
  hay giá. Lỗi 400/404 không lặp lại giá trị đã gửi. Có `Cache-Control: no-store`. Có test `test_cs17_no_personal_data_no_price`,
  kể cả trường hợp gửi SĐT vào `code`.
- `scripts` trong chi tiết hàng chờ và `/api/confirmation/scripts/` chỉ có `situation`, `situation_label`, `content` (và `is_active` ở
  API kịch bản). Người không có `view_callscript` nhận `[]`. Chi tiết hàng chờ vẫn giữ chặn Tầng 3 sẵn có
  (`note_in_customer_service_scope` → 404) trước khi tới serializer.
- `_clean_content` chặn chuỗi từ 9 chữ số trở lên qua `has_long_digit_run`. Hàm này bỏ khoảng trắng, `.`, `-`, `_`, `/` trước khi
  đếm, nên chặn được cả `0901.000.111`, `0901 000 111` và `+84…`. Mã lỗi là `BR-GH-19`.
- Code mới không gọi `logger` hay `print`. AuditLog `create_callscript`/`update_callscript` chỉ ghi `situation`, cờ `is_active` và
  `content_changed: true`, không chép nội dung. `__str__` là `Kịch bản <SITUATION>`. Có test `test_cs18_audit_log_on_create_and_update`.
- `CallScript` không đăng ký Admin, không có đường xoá (DELETE/PUT → 405).

**2. Phân quyền theo 5 vai: ĐẠT, khớp 02b §3.1.**

| Endpoint | owner | manager | warehouse_staff | delivery_staff | customer_service | chưa đăng nhập |
|---|---|---|---|---|---|---|
| `GET lookup` | 200 | 200 | 200 | 403 | 403 | 401 |
| `GET scripts` | 200 (thấy cả kịch bản tắt) | 200 (chỉ đang dùng) | 403 | 403 | 200 (chỉ đang dùng) | 401 |
| `POST`/`PATCH scripts` | 201/200 | 403 | 403 | 403 | 403 | 401 |

Trong test có đủ các ô trên. Vai không có quyền gọi thì dữ liệu không đổi.

Data migration `delivery/0009_grant_callscript` cũng **ĐẠT**:
- Phụ thuộc `accounts/0013_rename_groups_to_english` nên tên nhóm tiếng Anh khớp, và `delivery/0008` tạo model trước.
- `create_permissions` đi theo đúng mẫu `delivery/0006`. Dùng `permissions.add` nên chạy lại không đổi gì. Nhóm không tồn tại thì bỏ qua.
- `revoke` gỡ đúng các quyền đã cấp nên chạy lùi được.
- Không trùng số migration với nhánh nào: `main` và mọi worktree, gồm `pham-vi`, chỉ tới `delivery/0007`; `pham-vi` thêm
  `accounts/0014` nên không đụng nhau.
- Đặt ở app `delivery` thay vì `accounts/00xx` như 02b §2.7: **chấp nhận** (tránh đụng số với việc phạm vi dữ liệu).
- `default_permissions = (view, add, change)`, không có `delete_callscript`. Có test `test_cs18_permissions_seeded_per_matrix`.

**3. Lệnh `delivery.deliverynote.lookup` trong registry AI: cấm.** Lý do:
- 02b §4.1 đã ghi cấm.
- Mọi đường thuộc nghiệp vụ tem (`…/label/`, `…/label/print/`, `…/label/void/`) đều đã nằm trong `FORBIDDEN_SUFFIXES`.
- Tra mã tem là thao tác quét tại kho, AI không có tình huống dùng.

Cách sửa ghi ở **M1**. AI đang ẩn (`NEXT_PUBLIC_AI_FEATURES` tắt) nên chưa có rò thực tế, vì vậy chỉ xếp Medium.

**4. Cách chọn `RETURNING`: chấp nhận.**
- Quy tắc của dev là phần bù của quy tắc FIRST_ORDER trong 02b §4.6: khách có đơn khác ở trạng thái `PROCESSING`/`COMPLETED` thì
  dùng `RETURNING`. Cách này hợp nghiệp vụ: đơn đã trả tiền và đã trừ kho mới tính là "khách quen", còn đơn huỷ hay hết giữ chỗ
  không tính.
- Khách nhận diện bằng `customer_id`, mà `Customer` là khoá tự nhiên theo SĐT (`get_or_create_by_phone`) và `SalesOrder.customer` không
  null. Vì vậy không có chuyện mọi khách vãng lai gộp làm một.
- Truy vấn: mỗi lần xem chi tiết tốn thêm 3 query cố định (`exists` đơn khác, dòng đơn, `CallScript`). Không N+1, vì khoá `scripts` chỉ
  có ở serializer chi tiết, danh sách hàng chờ không có.
- Về rò dữ liệu: CSKH chỉ suy ra được "khách này đã từng mua". Người đó vốn đã ở trong phạm vi xem đủ tên và SĐT của chính đơn này,
  và không lộ đơn nào khác. Chấp nhận.
- Trường hợp biên (không chặn): khách mới đặt hai đơn gần nhau, cả hai cùng `PROCESSING`, thì cả hai sẽ thấy `RETURNING`. Nếu Duy
  muốn chặt hơn thì thêm `created_at__lt=order.created_at`.
- 02b §4.6 cần ghi bổ sung dòng RETURNING (xem mục ghi nhận lệch bên dưới).

**5. Marker `naming: allow` ở `test_call_scripts_and_lookup.py:41`: duyệt.** Marker có lý do đúng cú pháp
(`ALLOW_WITH_REASON`). Dòng này chỉ đặt bí danh tiếng Anh cho fixture cũ của `ConfirmationL2BaseTestCase` (`chu`, `ql`, `kho`, `giao`),
còn đổi tên fixture gốc thì nằm ngoài phạm vi lô. Đã có tiền lệ giống hệt ở `purchasing/receipts/tests/test_nhap_lo.py:131`.
Phần còn lại của file mới dùng tên tiếng Anh.

**6. Giá vốn: ĐẠT.** `lookup` không có khoá tiền hay giá. API kịch bản và khoá `scripts` không có tiền. Test
`test_cs18_response_has_no_personal_data` quét đệ quy, có cả `total_amount`, `rate`, `amount`, `unit_cost`. `scripts_for_note` có
đọc dòng đơn nhưng chỉ xét `bundle_snapshot`, không serialize gì từ dòng.

### Lệch so với 02b: chấp nhận, Tech Lead ghi nhận

| Chỗ | 02b | Code | Quyết định |
|---|---|---|---|
| Đường dẫn kịch bản | `/api/cskh/scripts/` | `/api/confirmation/scripts/` | Chấp nhận, theo đợt đặt tên tiếng Anh. Tiền tố đã nằm trong `FORBIDDEN_PREFIXES` |
| Migration cấp quyền | `accounts/00xx_grant_callscript` | `delivery/0009_grant_callscript` | Chấp nhận |
| 404 `lookup` | `{"detail"}` | `{"detail","code":"NOT_FOUND"}` | Chấp nhận, vì có thêm khoá `code` |
| Chọn `RETURNING` | chưa nói | phần bù của FIRST_ORDER | Chấp nhận, sẽ cập nhật 02b §4.6 |

FE bám contract ở `03-dev-notes.md` mục Lô 5 BE §2. Sau khi sửa M1, L1, L2, contract không đổi, chỉ thêm 400 `INVALID_INPUT`
khi body không phải object.

### Ghi chú cho lô FE (CS-16)

CS-16-AC4 yêu cầu `giao1` thấy màn "Không có quyền". Tuy nhiên `GET /api/delivery/notes/{id}/` vẫn trả **200** cho NV giao khi
phiếu được giao cho chính họ. Vì vậy FE phải chặn trang `/print/pick-sheet/` theo quyền `delivery.print_label` (hoặc
`pack_deliverynote`), không dựa vào mã 403 của API.

### Việc tiếp theo

1. `be-dev` sửa M1, L1, L2 (L3, L4 nên làm cùng), thêm test như cột "Cách sửa".
2. Điều phối viên chạy lại toàn bộ suite có symlink `staticfiles`, `makemigrations --check`, `check_naming.py`.
3. Techlead review lại phần diff sửa. Nếu đạt thì đổi kết luận thành APPROVED.
