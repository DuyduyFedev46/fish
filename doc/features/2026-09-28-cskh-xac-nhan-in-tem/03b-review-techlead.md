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

## Re-review sau 09672be (06/10)

- **Phạm vi:** `git show 09672be`, gồm 8 file code/test và 3 file doc. Soát từng mục M1, L1–L4, N1, N2 của bản review trên.

### Kết luận: **APPROVED**

Tất cả lỗi đã sửa đúng cách đề ra, có test đi kèm. Không phát sinh lỗi mới về dữ liệu cá nhân, giá vốn, phân quyền hay migration.

### Lệnh kiểm chứng techlead tự chạy (worktree `cskh-lo5`, `DJANGO_DEBUG=1`, symlink tạm `backend/staticfiles`, đã gỡ sau khi chạy)

| Lệnh | Kết quả |
|---|---|
| `manage.py makemigrations --check --dry-run` | No changes detected |
| `manage.py test` (toàn bộ) | **Ran 2887, OK** (thêm 4 test so với `ccb0f10`) |
| `python3 scripts/check_naming.py` | OK, không phát sinh vi phạm mới |

### Soát từng mục

| # | Kết quả | Căn cứ |
|---|---|---|
| M1 | Đạt | `apps/ai/policy/rules.py:20` thêm `"/api/delivery/notes/lookup/"` vào `FORBIDDEN_PREFIXES`, có comment lý do. Snapshot đã gỡ dòng `delivery.deliverynote.lookup`. Test `test_cs17_lookup_label_forbidden_for_ai` (`test_discovery.py`) kiểm cả `is_url_forbidden` lẫn registry. `test_discipline.py` vẫn đếm 30 action. |
| L1 | Đạt | `delivery/api.py:216-221` kiểm `print_label` rồi đến `view_deliverynote` (403), sau đó gọi `lookup_label(..., queryset=self.get_queryset())`. Như vậy lookup đi qua phạm vi Tầng 3 giống action `label`. Test `test_cs17_l1_out_of_scope_note_404_and_needs_view_perm` kiểm 3 trường hợp: NV giao có thêm `print_label` tra phiếu không phải của mình (404), tra phiếu được giao cho mình (200), có `print_label` nhưng thiếu `view_deliverynote` (403). |
| L2 | Đạt | `_body_dict` (`scripts_api.py:29-35`) nhận JSON object hoặc QueryDict. Mảng hay chuỗi trả 400 `INVALID_INPUT`. Body rỗng hoặc `null` được coi là `{}`, rồi service trả 400 vì thiếu dữ liệu. Test `test_cs18_l2_non_object_body_400` cover cả POST lẫn PATCH. |
| L3 | Đạt | `create` nằm trong `transaction.atomic()` lồng (savepoint) bên trong service atomic. Khi gặp `IntegrityError`, savepoint rollback rồi ném `BusinessError` 400, nên giao dịch ngoài không bị hỏng và không ghi AuditLog. Test giả lập `IntegrityError` bằng mock. |
| L4 | Đạt | `lookup_label` và `LABEL_CODE_RE` đã chuyển sang `delivery/labels/services.py:207-236`. `call_scripts.py` không còn import `re`/`LabelPrint`, không để lại code chết. Phần trả về giữ nguyên 5 khoá, không có dữ liệu cá nhân hay giá. |
| N1 | Đạt | `order.lines.exclude(bundle_snapshot={}).exists()` đúng, vì `SalesOrderLine.bundle_snapshot` là `JSONField(default=dict)` không null, và hàng thường được ghi `{}` (`sales/orders/services.py:241`). |
| N2 | Đạt | Đã bỏ `setUp` rỗng. |

Phần doc: 02b §4.6 đã thêm dòng RETURNING. `03-dev-notes.md` §6 và §8 ghi đúng những gì đã sửa. Contract FE không đổi, chỉ thêm
400 `INVALID_INPUT` khi body không phải object.

### Còn mở (không chặn, chuyển lô FE)

- CS-16-AC4: trang `/print/pick-sheet/` phải chặn theo quyền `delivery.print_label` hoặc `pack_deliverynote` (xem ghi chú lô FE ở trên).
- Trường hợp biên RETURNING khi khách mới đặt hai đơn gần nhau: giữ như hiện tại trừ khi Duy muốn siết.

## Review Lô 5 FE (06/10)

- **Phạm vi:** worktree `cskh-lo5-fe`, nhánh `feat/cskh-lo5-fe`, `git diff 0b3e4d5..50058f3` (33 file, chỉ `erp-console/` và 03-dev-notes).
  Đối chiếu với 02-stories (CS-16, CS-17, CS-18), 02b §4.6 và §6, contract BE thật (`delivery/api.py:208-221`,
  `delivery/labels/services.py:19,208-236`, `delivery/confirmation/scripts_api.py`, `call_scripts.py`, `serializers.py:293-299`,
  `delivery/migrations/0009_grant_callscript.py`, `accounts/migrations/0011`).

### Kết luận: **APPROVED**

Không có lỗi Critical, High hay Medium. Có 3 điểm Low, không chặn merge (ghi ở cuối).

### Lệnh kiểm chứng techlead tự chạy

| Lệnh | Kết quả |
|---|---|
| `python3 scripts/check_naming.py` (trong worktree) | OK, không phát sinh vi phạm mới |
| grep `console.` / `localStorage` / `sessionStorage` / `/api/ai` trên các file code mới hoặc đã sửa (trừ e2e) | Không có lời gọi nào. Chỉ có comment, và phần `localStorage` có sẵn của `auth/mock.ts` (người dùng mock, không phải khách) |

Không chạy `tsc`, `vitest`, build hay e2e vì worktree không có `node_modules` và điều phối viên đang build. Số liệu 945 test,
`check-no-mock`, e2e 92/92 lấy từ 03-dev-notes. Điều phối viên tự chạy lại theo quy trình bước 3.

### Soát theo mục được giao

**1. Phiếu soạn (CS-16): ĐẠT.**
- *Dữ liệu cá nhân và giá:* `toPickSheet` (`features/deliveries/pickSheet.ts:14-21`) chỉ chép `code`, `status`, `total_kg` và
  đúng 4 khoá của dòng hàng. Hàm chạy ngay trong `.then` (`PickSheetScreen.tsx:52-56`). Đối tượng chi tiết gốc chỉ nằm trong
  closure, không vào state hay DOM. Kiểu `PickSheetData` không có chỗ cho tên, SĐT hay địa chỉ, nên TypeScript chặn được
  trường hợp ai đó lỡ thêm vào sau này. Test `pickSheet.test.ts` kiểm cả danh sách khoá. E2e đọc DOM thật để kiểm AC2 và AC3.
  Trang không hiện `status`, ghi chú hay mã đơn.
- *Chặn quyền trước mọi request:* effect kiểm `canOpenPickSheet` (cần `print_label` hoặc `pack_deliverynote`) trước khi gọi
  `fetchDeliveryNoteDetail` (`PickSheetScreen.tsx:41-44`). Chưa đăng nhập thì chuyển sang `/login/?next=`, tham số chỉ mang `?note=<id>`.
  Cách làm này đúng ghi chú cho lô FE ở trên: API chi tiết trả 200 cho NV giao với phiếu của chính họ. Theo migration 0011,
  `delivery_staff` và `customer_service` không có quyền nào trong hai quyền đó, nên `giao1` và `cs1` không gọi được chi tiết. Đã
  có test đơn vị và e2e đếm request.
- Nếu API vẫn trả 403 hoặc 404 thì trang hiện màn lỗi riêng, không lộ chi tiết. Chỉ in khi phiếu ở trạng thái PREPARING. Phiếu
  huỷ báo đỏ, các trạng thái khác báo vàng, đúng CS-16-AC1.
- `@page 100mm 150mm` đặt trong `<style>` giống trang tem (02b §6). Giấy luôn đen trên nền trắng nhờ `Canvas/CanvasText`.

**2. Tra mã tem (CS-17): ĐẠT.**
- `TAG_CODE_RE` (`tagCode.ts:8`) giống hệt `LABEL_CODE_RE` của BE. `checkTagCode` chạy trước `lookupDeliveryTag`
  (`TagLookupScreen.tsx:57-63`), nên SĐT hay tên gõ nhầm không bao giờ thành query string, kể cả chuỗi lấy từ camera. Hàm
  chuyển chữ hoa an toàn: mã phiếu BE sinh ra là `GH-{INV…}-{hex.upper()}` (`delivery/services.py:74`), và QR trên tem là
  `barcode_value = f"{note.code}.{print_no}"`, khớp regex.
- Câu lỗi là hằng `TAG_MESSAGES`, không chèn input vào. 400, 403, 404 và lỗi mạng đều dùng câu của FE, không hiện `detail` của BE.
  Test `tagCode.test.ts` kiểm câu lỗi không chứa input.
- Không ghi input vào URL, `localStorage` hay console. Mở phiếu bằng `/deliveries/detail/?id=<số>`. Camera chỉ dùng
  `BarcodeDetector` có sẵn trong trình duyệt, không thêm thư viện, không gửi hình đi đâu, và tắt stream khi unmount.
- Nút "Quét mã tem" và ViewGuard `delivery-lookup` yêu cầu `print_label` + `view_deliverynote`, trừ người chỉ làm giao hàng.
  Điều kiện này khớp với 2 lần kiểm 403 của BE (L1 ở review BE).

**3. Kịch bản gọi (CS-18): ĐẠT.**
- Quyền theo vai: ViewGuard và nút ở màn Gọi xác nhận yêu cầu `view_callscript`. Nút Sửa và Bật/Tắt yêu cầu `change_callscript`,
  nút Soạn yêu cầu `add_callscript`. Quyền mock của owner, manager và customer_service khớp `delivery/0009`. Không có nút xoá,
  vì BE trả 405 cho DELETE.
- BR-GH-19: `scriptError` dùng `hasLongDigitRun`, giống hệt `apps/common/pii.has_long_digit_run` (bỏ `\s.-_/`, từ 9 chữ số).
  Giới hạn rỗng và 2000 ký tự cũng khớp `_clean_content`. BE vẫn chặn lại, và lỗi BE hiện qua `useSubmit`.
- Khối "Kịch bản gọi" ở chi tiết hàng chờ đọc khoá `scripts` (BE chỉ trả kịch bản đang bật, không có `is_active`), đặt dưới thanh
  trạng thái, tức là dưới nút kết quả ở header (AC1). Cấp heading h3 rồi h4 là đúng.
- Không có `/api/ai/` ở cả ba màn. E2e đã kiểm điều này trên mọi màn mới.

**4. Mock: ĐẠT.**
- `mockLookupDeliveryTag` khớp contract: kiểm 2 quyền, phạm vi NV giao (`inCourierScope`), 404 khi chưa in hoặc chưa từng in
  lần đó, `valid_print_no` null cùng `BR-GH-07` khi phiếu huỷ. Thân 400 không lặp lại input.
- `mockScripts.ts` khớp `scripts_api.py`: người đọc chỉ thấy kịch bản đang bật, POST trả 201, PATCH trả 404 khi chưa có, mã
  `BR-GH-19`. Hai chỗ lệch nhỏ không ảnh hưởng FE: (a) BE sắp theo `situation` theo thứ tự chữ cái, mock sắp theo thứ tự màn hình,
  nhưng `slotsOf` sắp lại nên kết quả hiện ra như nhau; (b) PATCH `is_active` không phải bool thì BE trả 400, còn mock bỏ qua.
- Mock không lọt vào bản thật: cả 4 hàm API mới viết `process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mock : undefined` trực tiếp,
  giống các hàm có sẵn. Dev ghi là `check-no-mock` đã bắt được lần bọc hàm đầu tiên và đã sửa. Không file thật nào import
  `mockScripts` ngoài nhánh này. Dữ liệu mock là chữ bịa ("Khách Thử R/S", "Đường Thử").

**5. UI: ĐẠT.**
- Dùng component chung: `DetailPage`, `DetailHeader`, `Section`, `Field`, `FormAlert`, `SummaryBlock`, `Chip`, `Modal` cùng
  `useSubmit` (nút đổi thành "Thử lại" khi lỗi, đúng §6.6), `ResourceView` cùng skeleton, `NoPermission`, toast. Không có mã màu
  viết tay. Câu chữ không chứa mã luật (§3).
- **Quyết định "không có dòng menu riêng": chấp nhận.** UI-RULES §2.1 cố định danh mục menu Bán hàng. Hai màn này là việc con
  của "Giao hàng" và "Gọi xác nhận", giống tiền lệ `menu: false` có sẵn (tab Đơn & tiền, nút trong Nội dung). Nhờ `parent`, mục
  cha vẫn sáng (`nav.test.ts`). NV kho vào được bằng nút ở màn Giao hàng, vì NV kho thấy menu này. Nếu Duy muốn một dòng
  riêng cho NV kho quét nhanh thì chỉ cần đổi cờ, nhưng đó là đổi UI-RULES §2.1 nên phải hỏi Duy, Tech Lead không tự đổi.
- Chấp nhận các lệch khác trong 03-dev-notes: tên file e2e theo `check_naming`, `/api/confirmation/scripts/` (đã chấp nhận ở
  review BE), trang `/print/pick-sheet/?note=` thay cho `/deliveries/31/pick-sheet` của story (02b dòng 60 đã chốt do static export).

**6. Chất lượng và test: ĐẠT.** Code nghiệp vụ nằm ở các hàm thuần (`pickSheet.ts`, `tagCode.ts`, `callScripts.ts`) có vitest. Mock
có test theo contract. `nav.test.ts` có thêm ca quyền cho 5 vai. E2e phủ được các ca ngoài đường thuận: SĐT gõ nhầm, 404, tem cũ,
phiếu huỷ, không có BarcodeDetector, 360px. Không có code chết hay code lặp. `hasLongDigitRun` dùng lại hàm có sẵn, không viết lại.

### Low (không chặn, gom vào đợt sửa sau)

| # | Chỗ | Vấn đề | Đề xuất |
|---|---|---|---|
| L1 | `features/deliveries/components/TagLookupScreen.tsx:104` | Ô mã tem có `name="tag-code"` và không có `autoComplete="off"`. Trình duyệt có thể lưu chuỗi đã gõ vào lịch sử gợi ý của form. Nếu NV gõ nhầm SĐT trên máy dùng chung ở kho, số đó sẽ hiện lại trong gợi ý. `Field` hiện chưa nhận prop `autoComplete`. Ô "Tìm khách gọi lại" có thể cũng bị như vậy | Thêm prop `autoComplete` vào `Field` rồi đặt `"off"` cho ô này và các ô tìm theo SĐT. Làm một lần cho cả nhóm ô tra cứu |
| L2 | `features/deliveries/components/PickSheetScreen.tsx:95` | Khi `AuthProvider` ở trạng thái `"error"` (không tải được `me`), trang vẫn hiện "Đang nạp phiếu soạn…" mãi. Trang tem `app/print/label/page.tsx` cũng bị như vậy | Nhánh `status === "error"` thì hiện màn lỗi có nút thử lại. Sửa cả hai trang in cùng lúc |
| L3 | `e2e/confirmation_scripts_tag_lookup.py:60` | Bộ nghe console chỉ ghi `type == "error"`, nên kiểm tra "không log dữ liệu khách" (dòng 376) không bắt được `console.log` hay `console.warn`. Grep cho thấy code không có lời gọi nào, nên rủi ro thực tế bằng 0 | Ghi mọi loại message rồi lọc PII trên toàn bộ |

### Việc tiếp theo

1. Điều phối viên tự chạy lại `tsc`, `vitest`, build `NEXT_PUBLIC_USE_MOCK=0` + `check-no-mock`, `check-ai-chunks`, rồi giao `qa-tester`.
2. Hỏi Duy có muốn dòng menu riêng "Quét mã tem" cho NV kho không. Mặc định giữ như hiện tại.
3. L1 đến L3 ghi vào nợ kỹ thuật của hồ sơ, không chặn lô này.
