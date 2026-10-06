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
| B9 `sales/orders/timeline.py` | Đạt. Đủ P4 ("Duyệt hàng hoàn: …"), P5 ("Huỷ phiếu hàng hoàn"), P6 ("Lập phiếu trừ doanh thu"), P7 ("Lập phiếu hoàn tiền", "Thử hoàn tiền lại"), C3 ("Phiếu hoàn tiền … chuyển thất bại", "Đã hoàn tiền …"), T2 ("Hết giờ giữ chỗ, đã nhả hàng giữ"), T25 ("(Đang soạn hàng)"). Logic gộp mốc giao của W37 L3 (`merged_note_ids`, dòng chuyển bù) và bộ lọc dòng AI giữ nguyên. Chỉ đổi chuỗi f-string, không ghép thêm dữ liệu, nên bất biến 9 không đổi |
| Low 1 | Đạt. Note mới "Huỷ đơn: <nhãn>" (`sales/orders/services.py:341`) hết lặp chữ. `_cancel_note_ok` thử cả hai tiền tố "Huỷ đơn" và "Lý do", với cả nhãn mới lẫn nhãn cũ. Không còn code nào khác (BE hay FE) phân tích tiền tố "Lý do:" của note này |
| Low 2 | Đạt. Note mới "Hoàn tiền theo phiếu hoàn tiền #N". Regex `phiếu hoàn( tiền)? #\d+` vẫn `fullmatch`, nên chữ tự do theo sau bị che. Có test cho trường hợp có SĐT |
| Test mới | `OrderTimelineWordingTests` chạy đường thật qua API: giao thất bại, mang hàng về, duyệt huỷ hàng, phiếu hoàn tiền thất bại rồi thử lại, huỷ đơn đã trả tiền kèm phiếu trừ doanh thu, đơn hết giờ giữ chỗ. Có danh sách chữ cấm và assert dương cho từng nhãn mới. SĐT trong test là số giả |
| Test cũ (5 file) | Chỉ đổi chuỗi mong đợi |
| Giá vốn / dữ liệu cá nhân / quyền | Không đổi field, serializer hay quyền |

Không còn việc BE nào của lô.
