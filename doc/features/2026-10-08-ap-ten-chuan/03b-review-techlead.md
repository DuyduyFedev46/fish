# 03b — Review Tech Lead: lô áp tên chuẩn (FE)

## Review FE Pha A (08/10)

> Tech Lead · `feat/ten-chuan-fe` @ `3ea03dd`, diff `9b1238c..3ea03dd` (94 file) · đối chiếu `02b-tech-design.md` mục 1.2, 3.2, 3.3
> và `03-dev-notes.md` mục FE Pha A.

**Kết luận: APPROVED cho Pha A, kèm điều kiện gộp.** Pha A **không được gộp riêng vào main**. Phải gộp cùng FE Pha B, và Pha B phải xong M1 và M2
dưới đây. Lý do: riêng Pha A làm lộ hai chỗ sai mà Pha A chưa xử lý.

### Lệnh đã tự chạy
- `tsc --noEmit`: sạch.
- `npx vitest run shared/lib`: 18 file, 273 test xanh.
- Worktree đang có thay đổi Pha B chưa commit (`features/audit/**`, e2e), nên hai lệnh trên chạy trên HEAD cộng phần Pha B đó. Tôi không
  reset worktree của dev. Kết quả vitest 1133 và e2e của dev chưa được tôi chạy lại.

# 03b — Review Tech Lead: lô áp tên chuẩn

## Review BE Pha A (08/10)

> Tech Lead · nhánh `feat/ten-chuan-be` @ `b343707`, diff `9b1238c..HEAD` (67 file) · đối chiếu `02b-tech-design.md` mục 1.1–3.1
> và `03-dev-notes.md` mục BE Pha A.

**Kết luận: APPROVED.** Không có lỗi chặn. Có 2 ghi chú mức Thấp, xử lý ở Pha B, không cần sửa trước khi gộp.

### Lệnh đã tự chạy
- `sqlmigrate` 9 migration mới (`accounts` 0016 và 0017, `catalog` 0004, `content` 0003, `delivery` 0011, `inventory` 0010,
  `purchasing` 0004, `reports` 0003, `sales` 0017): **không ra câu SQL nào**. Kể cả `AlterField` của FK `refund.payment_transaction`
  (chỉ đổi `verbose_name`) cũng không drop hay tạo lại constraint.
- `makemigrations --check --dry-run`: No changes detected.
- `manage.py test apps.common.tests.test_standard_names apps.accounts.audit`: 77 test, OK. Toàn bộ suite do điều phối viên chạy lại.
- `python3 scripts/check_naming.py`: OK, không phát sinh vi phạm mới.

### Theo từng điểm soát
| Điểm | Kết quả |
|---|---|
| Chỉ đổi chữ | Đạt. Giá trị DB của mọi `choices` đã sửa giữ nguyên (test `test_bt2_*` đóng băng danh sách). Diff không sửa chuỗi nào trong `record_audit(...)`/`action =`, không sửa codename, `path(...)`, `router.register` hay `url_path`. Khoá JSON mới duy nhất là `auto_cancel_blocked_label`, đúng 02b |
| 8 migration tự sinh | Đạt. Chỉ có `AlterField` (đổi choices hoặc verbose_name) và `AlterModelOptions`; `sqlmigrate` rỗng |
| `accounts/0017` | Đạt. `RunPython(rename_forward, rename_backward)` chỉ `filter(app_label, codename).update(name=…)`, nên idempotent. Không đụng codename hay gán Group. `dependencies` gồm migration mới nhất của 8 app cùng `auth` và `contenttypes`. Trên DB mới, migration này không cập nhật dòng nào và `post_migrate` tạo quyền với tên mới; trên staging/production nó đổi tên 9 dòng. Test dựng lại tên cũ, chạy hai lần, chạy chiều ngược, và kiểm gán Group không đổi |
| `_cancel_note_ok` | Đạt. `_LEGACY_CANCEL_LABELS` nhận 3 nhãn cũ (`accounts/audit/serializers.py:32`). AuditLog cũ ở production vẫn hiện đúng. Chữ tự do theo sau nhãn vẫn bị che (`test_free_text_after_label_is_still_masked`) |
| `auto_cancel_blocked_label` | Đạt. Lấy từ bảng hằng `AUTO_CANCEL_BLOCKED_LABELS`, mã lạ trả `None`, khoá cũ giữ mã thô. Test API có cả hai nhánh |
| `escalation_label` WANT_CHANGE | Đạt. Bỏ hết nhánh chép tay, dùng `get_escalation_reason_display()`. Câu hướng dẫn xử lý chuyển cho FE F10 |
| Lỗi `item_image_add` | Đạt. Khoá ở `catalog/items/next_steps.py` khớp `catalog/images/services.py:148`. Test qua `/api/guidance/item/` thấy nhãn, không thấy "Có thay đổi" |
| `test_standard_names.py` | Đủ chặt cho Pha A. Có đủ 9 dòng C, các dòng T có choices ở BE (T2–T13, T14–T19, T20–T38, T44–T52, T54–T57), cột Shop (T1, T2, T24–T30), các dòng P liên quan BE, cộng bẫy `Permission.name`. Mỗi dòng dùng `subTest` nên lỗi in đúng mã dòng |
| Test cũ | Đạt. Đã đọc từng dòng `-/+` của các file test cũ: chỉ đổi chuỗi mong đợi hoặc docstring, không nới hay bỏ assert nào |
| Giá vốn / dữ liệu cá nhân | Không có field mới. Nhãn đều là hằng, không ghép `reason`, `note` hay SĐT. Serializer không đổi tập field, ngoài khoá T43 là chuỗi hằng |
| 5 chỗ lệch trong dev-notes | Chấp nhận cả 5. Mục 4 (`payment_transaction`) là lỗi tên field trong 02b, sửa theo code thật |

### Ghi chú mức Thấp (không chặn, đưa vào Pha B)
1. `sales/orders/services.py:341` nay ghi note mới dạng "Lý do: **Lý do khác** · …", lặp chữ "Lý do" ở Nhật ký. Đề xuất cho Pha B: tách tiền
   tố, ví dụ ghi "Lý do huỷ: …", hoặc để FE bỏ tiền tố khi hiện. Nếu đổi tiền tố thì `_cancel_note_ok` phải nhận cả mẫu cũ lẫn mẫu mới,
   vì dòng cũ không sửa.
2. Note của `resolve_payment` vẫn ghi "Hoàn tiền theo phiếu hoàn #N", lệch C3. Dev-notes mục 5 giữ chữ này vì regex che dữ liệu khớp chuỗi đã
   ghi. Đề xuất cho Pha B: ghi mẫu mới "…phiếu hoàn tiền #N" và để regex ở `accounts/audit/serializers.py` nhận cả hai mẫu, theo cách làm của
   `_LEGACY_CANCEL_LABELS`.

### Pha B còn nợ (không thuộc lần review này)
B9 `sales/orders/timeline.py` và test B-timeline, chờ W37 L3 BE gộp.

## Review BE Pha B (08/10)

> Tech Lead · `feat/ten-chuan-be` @ `fdf79e5`, sau merge main `07e8d15` (đã có W37 L3) · soát bằng `git show fdf79e5` (12 file).

**Kết luận: APPROVED.**

### Lệnh đã tự chạy
- `manage.py test apps.common.tests.test_standard_names apps.sales.orders apps.accounts.audit`: chỉ 1 lỗi,
  `test_p8_lo7_privacy_gl03.ConsentEvidenceTests.test_f5b_gl03_ac10_admin_post_khong_doi_2_field_consent`, báo
  `ValueError: Missing staticfiles manifest entry for 'admin/css/base.css'`. Đây là lỗi **môi trường của worktree** (chưa có `.env`,
  chưa `collectstatic`): chạy đúng test đó ở checkout chính thì OK. Lỗi không liên quan tới lô. Lượt chạy toàn bộ của dev là 3261 OK.
- `makemigrations --check --dry-run`: No changes detected. Pha B không thêm migration.

### Theo từng điểm
| Điểm | Kết quả |
|---|---|
| `enums.ts` đúng bảng mục 4 | Đạt. Đã đối chiếu từng dòng T2–T66 có ở ERP. Thêm `paymentEnvironment` (T12, T13) và `confirmQueueTab` (T39). `cancelReason` có đủ 6 mã. Ô chọn huỷ tay chỉ lấy 4 mã người dùng được chọn (`orders/labels.ts`) và hộp quyết định lấy 3 mã (`confirmationUi.ts`), đúng hành vi cũ. Nhóm lọc "Đã huỷ" vẫn gộp `CANCELLED,AUTO_CANCELLED` (Q-2) |
| Xoá 6 bản chép | Đạt, kèm các bản chép phụ (`confirmation/types.ts` tab và kết quả gọi, `deliveries/types.ts`, `deliveryUi.ts`, `RefundQueueScreen.tsx`, `returnsModel.ts`, `catalog/messages.ts`). File mới chỉ import thêm `ENUMS`, không file nào import mock |
| `noLabelCopies.test.ts` | Đủ chặt cho mục tiêu "không còn chữ cũ". Quét `features/`, `shared/`, `app/` kể cả mock, bỏ comment, có kiểm sàn > 100 file. Có 4 file Pha B được miễn tạm (`PHASE_B_FILES`), phải gỡ ở Pha B. Giới hạn: test chỉ chặn chữ **cũ**, không chặn việc chép lại chữ **mới** ngoài `enums.ts`. Chấp nhận, vì mock có quyền mô phỏng nhãn BE |
| Lệch 1: regex `— chờ Chủ(?! hoặc)` | **Chấp nhận.** Thứ cần cấm là đuôi nhãn "— chờ Chủ" (T3–T7). Câu "chờ Chủ hoặc Quản lý duyệt" là lời văn đúng nghiệp vụ |
| Lệch 2–5 | Chấp nhận. F11 không có ô chọn nên không phải sửa. `reportView.ts` đã đúng C2. Toast "Phiếu giao chuyển sang Đang soạn hàng" đúng T25 |
| e2e `standard_names_all_routes.py` | Đủ cho Pha A: nhóm A trên `innerText` cùng `aria-label`/`title`/`placeholder`, nhóm B theo `.stat-chip` từng route, đối chứng dương ("Hết giờ giữ chỗ", chip phiếu giao, chip phiếu hoàn tiền, menu), chạy hai vai. Còn nợ ở Pha B: gỡ `PENDING_ROUTES`, thêm Shop `/shop/orders/`, thêm cột Thao tác của Nhật ký, chạy lần hai trên BE thật |
| F10 (T43) | Đạt. Hiện một dòng `alert-box warn role="status"` khi `auto_cancel_blocked_label` khác null. Khoá để optional nên BE cũ vẫn chạy |
| Mock lọt bản build | Đạt. Không có import mock mới ngoài file mock. Dev chạy `check-no-mock` trên bản `USE_MOCK=0`: xanh. Phiếu M5-1b đã quét cả `*.mock.ts` (sửa ở W37 L3) |
| Dữ liệu cá nhân / giá vốn | Không thêm field, nhãn đều là hằng. Không ghi log hay storage |

### Bắt buộc ở Pha B (điều kiện gộp)
- **M1, mất hướng dẫn xử lý WANT_CHANGE (T37).** BE Pha A đã bỏ đuôi "– huỷ + hoàn + đặt lại" khỏi `escalation_label`. Theo ghi chú T37 của
  mục 4, phần hướng dẫn chuyển thành dòng gợi ý dưới chip. FE Pha A chưa thêm dòng này: `ConfirmationDetailScreen.tsx:320` chỉ in "Lý do: Khách
  muốn đổi món". Nếu BE gộp trước thì nhân viên CSKH không còn thấy cách xử lý. Cần thêm một dòng gợi ý (chữ đặt ở `confirmation/messages.ts`)
  khi `escalation_reason === "WANT_CHANGE"`, ví dụ "Huỷ đơn, hoàn tiền, rồi nhờ khách đặt lại", kèm vitest.
  (Lỗi do 02b mục F10 chỉ ghi T43, sót phần này. Tech Lead nhận.)
- **M2, W11 nặng thêm khi đổi chữ.** `auditModel.ts` `statusLabel` vẫn dò lần lượt `STATUS_TABLES` (salesOrder → refund → delivery…). Sau Pha A,
  `FAILED` của phiếu giao hiện thành "Hoàn thất bại" (trước là "Thất bại"), và `COMPLETED` của phiếu giao hiện thành "Hoàn tất" (đúng phải là
  "Đã giao"). F9 ở Pha B phải chọn bảng theo `model_name` như 02b mô tả. Test trong `auditModel.test.ts` phải có cả hai ca này.

### Ghi chú thêm (không chặn)
- Khi gỡ `PHASE_B_FILES` và `PENDING_ROUTES`, ghi lại trong dev-notes số route và số file thực quét, để QA so được.
- `features/permissions/mock.ts:37,40` còn chữ cũ thuộc nhánh F1. Sau khi F1 gộp thì gỡ `features/permissions/` khỏi `SKIP_PREFIXES`.

| B9 `sales/orders/timeline.py` | Đạt. Đủ P4 ("Duyệt hàng hoàn: …"), P5 ("Huỷ phiếu hàng hoàn"), P6 ("Lập phiếu trừ doanh thu"), P7 ("Lập phiếu hoàn tiền", "Thử hoàn tiền lại"), C3 ("Phiếu hoàn tiền … chuyển thất bại", "Đã hoàn tiền …"), T2 ("Hết giờ giữ chỗ, đã nhả hàng giữ"), T25 ("(Đang soạn hàng)"). Logic gộp mốc giao của W37 L3 (`merged_note_ids`, dòng chuyển bù) và bộ lọc dòng AI giữ nguyên. Chỉ đổi chuỗi f-string, không ghép thêm dữ liệu, nên bất biến 9 không đổi |
| Low 1 | Đạt. Note mới "Huỷ đơn: <nhãn>" (`sales/orders/services.py:341`) hết lặp chữ. `_cancel_note_ok` thử cả hai tiền tố "Huỷ đơn" và "Lý do", với cả nhãn mới lẫn nhãn cũ. Không còn code nào khác (BE hay FE) phân tích tiền tố "Lý do:" của note này |
| Low 2 | Đạt. Note mới "Hoàn tiền theo phiếu hoàn tiền #N". Regex `phiếu hoàn( tiền)? #\d+` vẫn `fullmatch`, nên chữ tự do theo sau bị che. Có test cho trường hợp có SĐT |
| Test mới | `OrderTimelineWordingTests` chạy đường thật qua API: giao thất bại, mang hàng về, duyệt huỷ hàng, phiếu hoàn tiền thất bại rồi thử lại, huỷ đơn đã trả tiền kèm phiếu trừ doanh thu, đơn hết giờ giữ chỗ. Có danh sách chữ cấm và assert dương cho từng nhãn mới. SĐT trong test là số giả |
| Test cũ (5 file) | Chỉ đổi chuỗi mong đợi |
| Giá vốn / dữ liệu cá nhân / quyền | Không đổi field, serializer hay quyền |

Không còn việc BE nào của lô.

## Review FE Pha B (08/10)

> Tech Lead · `feat/ten-chuan-fe` @ `fe7642d` (21 file), xét cùng HEAD `b572525` (đã gộp BE Pha A và B).

**Kết luận: APPROVED.** M1 và M2 của review Pha A đã đóng. Có một việc tồn ở **BE** (B-P7 dưới đây), không chặn FE. Tech Lead đề xuất sửa
trước khi gộp main.

### Lệnh đã tự chạy
- `npx vitest run features/audit features/confirmation features/orders shared/lib`: 34 file, 463 test xanh. Worktree sạch.
- Đối chiếu khoá của `AUDIT_ACTION_LABELS` (90 mã) với chuỗi `action` trong BE (không tính tests và migrations). Chỉ còn 4 mã AI
  (`execute_command`, `propose`, `confirm_proposal`, `reject_proposal`) không thấy ở dạng chuỗi cố định. Đây là phần AI, ngoài lô (02b mục 0).

### Theo từng điểm
| Điểm | Kết quả |
|---|---|
| M1 `escalationHint` | Đóng. Chữ nằm ở `confirmation/messages.ts`, hàm thuần trong `confirmationUi.ts`. Dòng `alert-box warn role="status"` ở `ConfirmationDetailScreen.tsx` chỉ hiện khi WANT_CHANGE. Vitest có cả nhánh có gợi ý và nhánh `null` |
| M2 / W11 `statusLabel` | Đóng. `STATUS_TABLE_BY_MODEL` tra theo `model_name`, khớp `obj._meta.label` mà BE ghi (`common/audit.py:156`; mọi chỗ khác cũng lọc theo `_meta.label`). Model lạ thì không in. `AuditLogScreen` truyền `row.model_name`. Test có đủ FAILED (phiếu giao / phiếu hoàn tiền), COMPLETED (phiếu giao / đơn), DRAFT (hàng hoàn / lô) và model lạ. Mock Nhật ký đổi `model_name` sang dạng `app.Model` thật, nên e2e mock phản ánh đúng BE |
| F9 nhãn Nhật ký | Đạt. Có P1–P9, P11, T2, T67–T76 (gồm `item_image_remove`). `enums.standardNames.test.ts` khoá từng dòng theo mã. Trạng thái nhân viên lấy từ `ENUMS.staffStatus` |
| W34 | Đạt. Bỏ `confirm_payment`, `auto_cancel` và `confirm_proposal` khỏi ô lọc. Không còn nhãn chết ngoài phần AI |
| "Lập phiếu hoàn tiền" thống nhất | Đạt ở ERP (`orderDetailModel.ts`) và ở nhãn BE do lô đã sửa (registry, `CAPABILITY_LABELS`, next_steps, timeline). Còn sót ở `features/permissions/mock.ts:37` (nhánh F1, đã biết) và `features/ai/report/mock.ts:54` (phần AI). Thanh bước phiếu hoàn tiền và dòng tổng hoàn lấy từ `ENUMS.refundStatus` |
| F13 Shop | Đạt. `frontend/lib/mock.ts` dùng "Chờ thanh toán" (T1) và "Đang chờ hoàn tiền" (T21), khớp `shop_labels.py`/`customer_notices.py` của BE |
| `PHASE_B_FILES`, `PENDING_ROUTES` | Đạt. Đã bỏ `PHASE_B_FILES`. `PENDING_ROUTES` chỉ còn hai route `/permissions/` (F1). e2e thêm cột Nhật ký (không "Thao tác khác", không "Người dùng", đối chứng dương "Đang giao → Giao thất bại") và quét Shop 8 đơn |

### Việc tồn
- **B-P7 (BE, Thấp, nên sửa trước khi gộp):** `backend/apps/sales/models/refunds.py:86` `Meta.permissions` vẫn là `("create_refund", "Tạo phiếu hoàn tiền")`,
  lệch P7 "Lập phiếu hoàn tiền". Chỉ Django Admin thấy chữ này. Lỗi gốc là 02b mục 2 sót P7 trong danh sách quyền phải đổi, Tech Lead nhận.
  Cách sửa: đổi `Meta.permissions`, `makemigrations sales` (thêm 0018, chỉ `AlterModelOptions`), thêm `accounts/0018_rename_create_refund_label`
  theo đúng mẫu 0017 (idempotent, có chiều ngược), và thêm dòng P7 vào `PERMISSION_NAMES`/`OLD_PERMISSION_NAMES` của `test_standard_names.py`.
- **QA cần chạy bước Shop của e2e:** `shop_sweep` chỉ chạy khi có `SHOP_BASE`, thiếu thì báo SKIP chứ không đỏ. QA phải đặt `SHOP_BASE` và có dòng
  `[Shop …]` PASS trong báo cáo. Lần chạy trên BE thật (staging local, dữ liệu giả) vẫn là TODO của QA.
- F1 gộp xong thì gỡ `features/permissions/` khỏi `SKIP_PREFIXES` và gỡ hai route khỏi `PENDING_ROUTES`.
