# Review bảo mật dữ liệu P1–P7 (giá vốn · dữ liệu cá nhân khách · phân quyền · cờ an toàn)

- Người review: Tech Lead (Claude), 2026-09-30. Phạm vi: `main` @ `75e5dd3`, diff từ `85c0b36` (merge P1) tới HEAD.
- Cách kiểm: đọc code và chạy thử bằng test tạm (đặt ở scratchpad, **không** thêm vào repo; `DJANGO_DEBUG=1`, SQLite, dữ liệu
  `seed_demo` cộng SĐT, tên, địa chỉ và giá vốn **giả** như `0977111222`, `81234`). Không sửa code sản phẩm.
- Đối chiếu: 02b của `2026-09-28-sua-loi-bao-mat`, `-ai-digital-worker`, `-cskh-xac-nhan-in-tem`, `-cms-viet-bai`, `-khung-go-live`.

**Kết luận: REVIEW FAIL.** Có 1 lỗi Critical (lộ giá vốn qua Nhật ký) và 1 lỗi High (lớp lọc PII của AI để lọt tên khách).
Cả hai đã tái hiện được bằng test.

## 1. Bảng phát hiện (đã xác minh)

| Mã | Mức | File:dòng | Mô tả | Cách tái hiện | Đề xuất sửa |
|---|---|---|---|---|---|
| BM-01 | **Critical** (bất biến 1) | `backend/apps/inventory/batches/services.py:283-291`; `backend/apps/common/cost_keys.py:12-16`; `backend/apps/accounts/audit/serializers.py:22-24` | `cancel_expired_batch` ghi `changes={"loss_amount": qty × landed_unit_cost, "qty": qty}`. `COST_KEYS` thiếu `loss_amount` nên `redact_cost` không lọc. Quản lý (có `view_auditlog`, không có `view_costprice`) gọi `GET /api/audit-logs/` sẽ thấy `loss_amount` cùng `qty`, rồi chia ra được giá vốn/kg. Dòng thời gian lô vẫn che đúng ("Chủ đã huỷ lô"). Lỗi chỉ nằm ở Nhật ký. | Tạo lô 10 kg, giá 81.234, chuyển EXPIRED. Chủ gọi `cancel_expired_batch`. Quản lý gọi `GET /api/audit-logs/?action=cancel_expired_batch`. Kết quả: `{"loss_amount": "812340.0000000", "qty": "10.000"}` | Thêm `loss_amount` vào `COST_KEYS`. Kèm theo, thêm test "mọi khoá tiền trong `changes` của mọi `record_audit` đã biết đều thuộc `COST_KEYS` hoặc là giá bán": quản lý gọi `/api/audit-logs/` sau khi chạy `cancel_expired_batch`, `close_batch` và `recompute_landed_cost`, rồi assert không còn khoá nào suy ra được giá vốn. Cân nhắc thêm vào `COST_KEYS` các khoá `loss`, `inventory_value`, `margin`, `gross_profit` để phòng trước |
| BM-02 | **High** (bất biến 9, H2 của 02b AI) | `backend/apps/ai/policy/rules.py:83-98` (`SCRUB_PII_KEYS`); `backend/apps/reports/dashboard_api.py:79-87`; `backend/apps/sales/orders/serializers.py:106-110` | Lớp lọc PII của AI (`scrub_data`) lọc theo **tên khoá**. Hai khoá sau không có trong danh sách: `customer` (trong dashboard là chuỗi tên khách) và `customer.name` (trong chi tiết đơn là dict `{"name","phone","address"}`, nên `phone`/`address` bị lọc còn `name` thì lọt). Hậu quả: lệnh AI `reports.dashboard_summary` trả **tên khách** cho Chủ, Quản lý và NV kho. 02b §3 H2 yêu cầu lọc PII "kể cả với Chủ". Lệnh `sales.salesorder.retrieve` cũng lộ tên khách cho mọi nhóm, kể cả `nv_giao` và `cskh`, ngay khi lỗi BM-06 được sửa. Test "quét toàn registry" hiện vẫn xanh chỉ vì mọi lệnh `retrieve` đang trả 502 | Gọi `POST /api/ai/commands/reports.dashboard_summary/call/` bằng `nv_kho`, với `AI_ENABLED=True` và tên khách giả "Trần Thị Bí Mật". Chuỗi tên xuất hiện trong `result.rows[0].recent_orders[].customer`. Nếu vá tạm `spec.detail=True` rồi gọi `sales.salesorder.retrieve`, tên lộ cho cả 5 nhóm | Thêm vào `SCRUB_PII_KEYS` các khoá `customer`, `recipient_phone`, `phone_last4`, `phone_masked` (lọc nguyên nhánh `customer`). Tốt hơn nữa là chuyển sang **allowlist** field đầu ra cho lệnh AI, hoặc đưa `/api/dashboard/summary/` vào danh sách cấm. Sửa test quét toàn registry: phải gọi được cả lệnh `retrieve` (sau BM-06) với fixture PII giả, và assert không chuỗi PII nào xuất hiện |
| BM-03 | **Medium** (Tầng 3, BR-GH-18) | `backend/apps/sales/orders/next_steps.py:179-182`; `backend/apps/ai/actions/services.py:299-302` | Hàm cung cấp guidance cho đơn chỉ lọc phạm vi khi user thuộc Group `nv_giao`. `SalesOrderViewSet.get_queryset` thì lọc thêm phạm vi `cskh` (`cskh_note_q`) và dùng `has_full_delivery_scope`. Hệ quả: CSKH nhận 404 ở `/api/sales/orders/<id>/` nhưng vẫn nhận 200 ở `/api/guidance/order/<mã>/` với đơn ngoài phạm vi. Response gồm trạng thái, dòng thời gian (số tiền, mã GD ngân hàng, lý do huỷ/hoàn là chữ tự do có thể chứa tên khách) và mã phiếu liên quan. Đường `POST /api/ai/actions/escalate/` gọi cùng provider nên cũng bị | Tạo user `cskh` và đơn `DH-OUT-1` đã xác nhận (ngoài phạm vi). `GET /api/sales/orders/1/` trả **404**, còn `GET /api/guidance/order/DH-OUT-1/` trả **200** kèm timeline | Tách hàm dùng chung `scope_orders_for(user, qs)` từ `SalesOrderViewSet.get_queryset` (dựa trên `has_full_delivery_scope`, phạm vi `assigned`, phạm vi `cskh`), rồi dùng cho guidance order. Thêm test theo từng Group (`cskh`, `nv_giao`, và user có `view_salesorder` nhưng không thuộc Group) |
| BM-04 | **Medium** (bất biến 1, phía FE) | `erp-console/features/purchasing/components/NhapLoForm.tsx:12, 55-75, 96-108` | Nháp form "Nhập lô" được lưu vào `localStorage` dưới một khoá cố định `cave_draft_nhap_lo`, gồm cả `lines[].rate` (giá mua). Khoá không gắn theo user và không bị xoá khi đăng xuất. Người đăng nhập sau trên cùng trình duyệt (ví dụ NV kho sau Chủ) mở form sẽ thấy nguyên giá mua người trước đã gõ. Idempotency key cũng bị dùng lại | Đọc code: effect ở dòng 96-108 ghi nháp sau mỗi lần sửa, effect ở dòng 63-75 nạp lại nháp vô điều kiện. Chưa chạy trên trình duyệt | Không lưu `rate` vào nháp. Nếu vẫn cần lưu, khoá nháp theo `user.id`, xoá khi đăng xuất và dùng `sessionStorage`. Thêm test FE: đăng xuất rồi đăng nhập user khác thì form rỗng |
| BM-05 | Low (IDOR) | `backend/apps/ai/actions/services.py:147-170` (reject), `:17-83` (confirm) | `reject_ai_action` và `confirm_ai_action` không kiểm người gọi có phải owner hoặc thuộc `assignee_group` không, trong khi `retrieve` có kiểm. Bất kỳ user đã đăng nhập nào biết UUID đều từ chối được đề xuất của người khác. Confirm chạy bằng quyền của chính người duyệt nên không leo quyền được. Rủi ro thấp vì id là UUID4 | User `nv_giao` gọi `POST /api/ai/actions/<uuid của Chủ>/reject/`. Kết quả **200**, trạng thái đổi thành REJECTED, `decided_by=nv_giao`, dù `GET` cùng id trả 404 | Dùng chung bộ lọc của `retrieve` (owner, hoặc ESCALATED cùng `assignee_group`, hoặc có `manage_ai_policy`). Ngoài bộ lọc thì trả 404 |
| BM-06 | Low (fail-closed, nhưng chặn test PII) | `backend/apps/ai/registry/discovery.py:212`; `backend/apps/ai/execution/pipeline.py:155-181` | Các action chuẩn `retrieve` và `partial_update` được sinh ra với `detail=False`, vì chỉ đọc `action_func.detail`. Hệ quả: (a) mọi lệnh AI `*.retrieve` trả 502 `AI_DISPATCH_FAILED`; (b) bước kiểm phạm vi `target_id` (bước 6) bị bỏ qua, nên đề xuất mức C `partial_update` lưu được `target_id` nằm ngoài phạm vi của người đề xuất; (c) `reports.batch_pnl` có `detail=True` nhưng `BatchPnlView` không có `get_object`, gọi kèm `target_id` thì văng **500 AttributeError** (chỉ Chủ gọi được) | Gọi `POST /api/ai/commands/inventory.batch.retrieve/call/` với `{"target_id": "<pk>"}` thì nhận 502. Log ghi `Expected view BatchViewSet to be called with a URL keyword argument named "pk"`. Với `reports.batch_pnl` kèm `target_id` thì nhận 500 | Sửa suy luận `detail` theo pattern `<pk>` khi action là `retrieve`/`partial_update`. Bước 6 cần xử lý riêng APIView không có `get_object`. **Phải sửa BM-02 trước hoặc cùng lúc**, vì sửa BM-06 sẽ mở đường lộ tên khách ở BM-02 |
| BM-07 | Low (hardening) | `backend/apps/ai/execution/scrub.py:14-23` | `_is_cost_authorized` coi `reports.view_profitreport` (hoặc một quyền không tồn tại là `accounts.view_costprice`) là đủ để thấy khoá giá vốn. Phần còn lại của hệ thống chỉ dùng `inventory.view_costprice` (`can_view_cost`). Hiện chỉ Chủ có hai quyền này nên chưa lộ. Nếu sau này gán `view_profitreport` riêng cho ai đó, lưới thứ hai của AI sẽ mở, dù serializer (lưới thứ nhất) vẫn chặn | Đọc code, đối chiếu với ma trận Group đã dump | Dùng `apps.common.cost_keys.can_view_cost` cho thống nhất |

## 2. Đã kiểm, ổn

**Cờ an toàn (settings, `backend/config/settings.py:264-333`)**, khớp 02b/02c:
- `AI_ENABLED` mặc định `0`. `AI_WRITE_LEVELS_ALLOWED` mặc định `"C"`. `AI_PRODUCTION_READY` mặc định `0`.
- `CSKH_AUTO_CANCEL_ENABLED` mặc định `0`. Chỉ `cskh/services.py:705` dùng cờ này để tự huỷ.
- `PRIVACY_CONSENT_REQUIRED` mặc định `1` ngoài `TESTING`/`DEBUG`. `SHOP_CONFIRM_CALL_NOTICE` mặc định `0`.
- `effective_level` lấy min với `env_max`. PUT policy và my-config đều kiểm `AI_PRODUCTION_READY`/`AI_WRITE_LEVELS_ALLOWED`.
- Job DW-26 (`auto_confirm.py`) không chạy nếu thiếu một trong ba điều kiện: `AI_PRODUCTION_READY`, `AI_ENABLED`, công tắc của Chủ.
- Ghi chú: `backend/.env.example` đặt `PRIVACY_CONSENT_REQUIRED=0` vì là mẫu cho dev. Không copy file này lên staging.

**Registry AI và danh sách cấm.** Đã dump toàn bộ registry. Không có lệnh nào thuộc các nhóm sau:
- đường dẫn `/api/public/`, `/api/shop/`, `/api/cskh/`, `/api/auth/`, `/api/staff/`, `/api/audit-logs/`, `/api/internal/`, `/api/ai/`, `/api/dashboard/attention/`;
- đường dẫn `…/label…`;
- phương thức `DELETE`/`PUT`;
- `sales.customer`.

Lệnh vùng đỏ và lệnh ép trần C đúng như 02b §3. `required_perms` của action mới được `BusinessModelPermissions` cưỡng chế trước thân action, và `effective_level` kiểm lại cả Tầng 1 lẫn Tầng 2.

**Quét lệnh đọc AI.** Chạy mọi lệnh đọc dạng list với 5 Group (`chu`, `quan_ly`, `nv_kho`, `nv_giao`, `cskh`), fixture có SĐT, tên, địa chỉ, tên người chuyển trong `raw_payload`, giá mua, giá vốn và chi phí mua (tất cả là dữ liệu giả).
- Không nhóm nào thiếu `view_costprice` nhận được con số giá vốn.
- PII chỉ lọt ở `dashboard_summary` (đã ghi thành BM-02).
- `raw_payload` và tên người chuyển bị lọc sạch.
- `AiAction` không lưu kết quả đọc. `args_preview` được lọc theo quyền của người xem.
- Báo cáo AI cuối ngày chỉ Chủ xem được và không chứa args hay kết quả.

**Nhật ký và dòng thời gian (P1 S01, DW-03…06).**
- `/api/audit-logs/` chỉ nhóm `chu` và `quan_ly` vào được. Các khoá thuộc `COST_KEYS` bị lọc, trừ lỗi BM-01.
- Dòng thời gian lô che số tiền với Quản lý và NV kho ("Chủ đã chốt lô", "Chủ ghi nhận chi phí mua", "Chủ đã huỷ lô"). Đã kiểm bằng test.
- Dòng thời gian giao dịch không đưa `raw_payload`/nội dung CK vào. Dòng xuất kho không có thông tin khách.
- Guidance `batch` và `payment` kiểm đúng quyền Tầng 1 và Tầng 2.

**CSKH (P4).**
- Ma trận Group: `cskh` chỉ có `view_salesorder`, `view_salesorderline`, `confirm_with_customer`, `change_recipient`.
- Chi tiết và mọi action dùng `note_in_cskh_scope`, ngoài phạm vi trả 404.
- Danh sách và tìm kiếm tính `in_scope` cho từng dòng. Ngoài phạm vi chỉ trả `phone_masked`, và ghi chú cuộc gọi bị xoá.
- `NoStoreMixin` có ở `/api/cskh/*` và `/api/delivery/notes/*` (gồm cả tem).
- Tìm kiếm chỉ nhận POST và có throttle theo user. Ghi chú hoặc lý do có dãy số dài bị chặn (`has_long_digit_run`).
- `AuditLog` của CSKH chỉ ghi mã, trạng thái và tên field, không ghi giá trị. Tem in SĐT đã che.
- Thông báo huỷ cho khách (`customer_notices`) không chứa PII.

**Shop, CMS và go-live (P1 S02/S03, P5, P6).**
- Tra đơn cần mã đơn cộng 4 số cuối SĐT, và có throttle theo IP (20/phút) lẫn theo mã đơn (10/giờ). Response không có tên, SĐT hay địa chỉ.
- API công khai của CMS dựng dict tường minh, `author="Cá Về"`. Bản nháp và bài chờ duyệt trả 404. Chỉ trả `published_version`.
- `site-info` chỉ trả thông tin người bán lấy từ env.
- Trường `privacy_consent` của đơn chỉ hiện khi có `view_privacy_consent` (Chủ, Quản lý).
- Serializer phiếu nhập và `nhap-lo` đánh dấu `rate`, `purchase_rate` và `landed_unit_cost` là field nhạy cảm.

**Log.** Các chỗ gọi `logger` mới chỉ ghi id lệnh, id task, mã GD và mã đơn. Không chỗ nào log `request.data` hay payload IPN.

## 3. Nghi ngờ chưa xác minh (cần kiểm tiếp, chưa tính vào kết luận)
- `erp-console` `AiAssistantPanel` in `result.rows` ra khung chat. Chưa chạy trên trình duyệt để xem tên khách ở BM-02 có hiện lên màn hình hay có bị giữ trong lịch sử chat không.
- Ảnh CMS được lưu theo đường dẫn đoán được (`content/{entry_id}/{image_id}/{size}.webp`). Chưa kiểm ACL của bucket, nên chưa biết ảnh của bài **nháp** có xem công khai được không.
- Tìm kiếm CSKH bằng SĐT đầy đủ vẫn trả dòng ngoài phạm vi (SĐT đã che, mã đơn). CSKH vì vậy dùng được nó để dò "SĐT này có phải khách không". Hành vi này đúng thiết kế và đã có throttle, nhưng nên hỏi `legal-vn` có chấp nhận không.
- `confirm_nonce` tính được từ `id` và `created_at`, và có ngay trong response danh sách. Đây chỉ là cơ chế chống bấm nhầm, không phải lớp bảo mật.

## 4. Ghi chú ngoài phạm vi P1–P7 (có từ trước)
- Không chạm dashboard này vẫn thấy tên khách: bản thân `/api/dashboard/summary/` trả `recent_orders[].customer` (tên) và `phone_last4` cho `nv_kho`. Chưa rõ NV kho có cần tên khách ở dashboard không. Nên hỏi Duy trước khi sửa.
- `SalesOrderViewSet` và `CustomerViewSet` trả SĐT và địa chỉ nhưng không có `Cache-Control: no-store`. 02b CSKH chỉ bắt buộc header này cho `/api/cskh/*` và tem. Nên áp cùng `NoStoreMixin`.

## 5. Thứ tự sửa đề xuất
1. BM-01, cần sửa trước khi deploy.
2. BM-02, rồi mới tới BM-06. Hai lỗi phải đi cùng một lô và có test quét registry gọi được `retrieve`.
3. BM-03, BM-04.
4. BM-05, BM-07.
