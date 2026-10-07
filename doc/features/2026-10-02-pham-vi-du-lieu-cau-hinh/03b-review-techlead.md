# Phạm vi dữ liệu cấu hình — Review Tech Lead (03b)

## Review Lô 1–2 BE (06/10)

> Tech Lead · 2026-10-06 · nhánh `feat/pham-vi-du-lieu`, diff `fa2368f..bbc0e38` (bc32ebc Lô 1 PV-01, bbc0e38 Lô 2 PV-02).
> Đối chiếu `02b-tech-design.md` §1.3, §2.1–2.2, §3, §4 và `03-dev-notes.md`. Duy chốt D-1 ngày 06/10: V2 giữ bật, Chủ tự tắt.

### Kết luận: **CHANGES REQUESTED**

Một lỗi High (H1) phải sửa trước khi Lô 3 bắt đầu nối resolver. Lỗi này nằm trong luật phân giải D7. Nó chưa khai thác được
hôm nay vì chưa đường đọc nào gọi resolver, nhưng thành rò dữ liệu khách (Critical) ngay khi Lô 4 nối `scope_customers_for`.
Nguồn lỗi là thiết kế 02b §1.3 luật 4 của tôi, không phải do be-dev làm sai. Tôi đã sửa 02b cùng commit với bản review này.
Các mục còn lại là Medium hoặc Low, có hạn xử lý ghi ở từng mục.

### Kiểm chứng đã chạy trong lượt review (worktree, HEAD bbc0e38)

- `manage.py test apps.accounts`: 406 test, OK. Điều phối viên đã chạy toàn bộ: 2918 test, OK.
- `makemigrations --check --dry-run`: `No changes detected`.
- `python3 scripts/check_naming.py`: OK, không phát sinh vi phạm mới.
- Grep tệp mốc `scope_snapshot_baseline.json` tìm `[0-9]{9,}`, `Giả`, `Đường`, `Khách`: không có kết quả nào.
- In quyền của 5 nhóm trên DB test (test tạm, đã xoá). `delivery_staff` có `sales.view_customer` (Tầng 1) và không có
  `view_customer_list`. `manager` có cả hai. `customer_service` và `warehouse_staff` không có quyền nào trong hai quyền này.
- Tái hiện H1 bằng test tạm (đã xoá). Đặt D7 của `delivery_staff` = `all` rồi gọi `resolve_data_scopes(user)["customers"]`
  cho một người G không có `view_customer_list`. Kết quả là `Resolved(value='all', via_group='delivery_staff')`.

### Lỗi

| # | Mức | File:dòng | Vấn đề | Sửa |
|---|---|---|---|---|
| H1 | **High** (thành Critical từ Lô 4) | `backend/apps/accounts/data_scopes/catalog.py:118`, `resolver.py:74-89`, `tests/test_resolver.py:141-144` | `CUSTOMERS.gate_perms` gồm cả `sales.view_customer` (Tầng 1, nằm ngoài registry, Chủ không tắt được). Vì vậy nhóm G luôn đủ điều kiện D7. Kịch bản: Chủ bật "Xem khách hàng" cho G, chọn D7 = `all`, rồi tắt việc. Theo Q-7, giá trị `all` vẫn được giữ. Resolver lúc đó vẫn trả `all`, nên từ Lô 4 G thấy **mọi khách** ở `/api/sales/customers/` và trên dòng thời gian khách, dù việc "Xem khách hàng" đã tắt. Hôm nay G chỉ thấy khách trên phiếu của mình. Lỗi này phá đúng điều R1b muốn chặn. Test `test_pv02_customers_follow_stored_value_when_group_eligible` đang khẳng định hành vi sai này, áp vào trường hợp Quản lý. | Đổi luật D7 (02b §1.3 luật 4, đã sửa). Một nhóm chỉ đóng góp `all` khi chính nhóm đó có `sales.view_customer_list`. Nhóm chỉ có `sales.view_customer` đóng góp tối đa `assigned_deliveries`, tức `min(giá trị lưu, assigned_deliveries)`. Nhóm không có quyền nào trong hai quyền thì không đủ điều kiện. Sửa test ở dòng 141–144: Quản lý mất `view_customer_list` thì nhận `assigned_deliveries`. Thêm test tái hiện: G có D7 = `all` nhưng không có `view_customer_list` thì nhận `assigned_deliveries`; bật lại `view_customer_list` cho G thì nhận `all`. Thêm ca K+G: K có list và D7 = `none`, G có D7 = `all` nhưng không có list, kết quả là `assigned_deliveries`. Ma trận mặc định không đổi, vì Q có list và G lưu `assigned_deliveries`, nên mốc PV-01 phải giữ xanh. |
| M1 | Medium | `backend/apps/accounts/data_scopes/tests/snapshot.py:133-195` | Mốc chỉ ghi đường **GET**. Lô 4 sẽ đổi các đường ghi hoặc hành động sau, và chúng chưa có mốc: gọi xác nhận (claim, ghi cuộc gọi, huỷ, đổi người nhận; 6 chỗ `note_in_customer_service_scope`), tạo hàng hoàn (queryset chọn phiếu giao ở `returns/serializers.py:52`), sửa, gửi ghi nhận và huỷ phiếu nhập (PV-06-AC5/6), `assign`/`set_status`/tem của phiếu giao. | **Trước khi Lô 4 sửa các đường này**, thêm vào mốc sự kiện `status:<nhãn>=<mã>` của từng hành động. Mỗi hành động thử với một dòng trong phạm vi và một dòng ngoài phạm vi, cho mọi tài khoản. Gói mỗi lần gọi trong `transaction.atomic()` rồi rollback bằng savepoint để dữ liệu không đổi. Mốc sinh trên HEAD hiện tại được, vì Lô 2 đã chứng minh không đổi hành vi (mốc Lô 1 vẫn xanh nguyên). Nên làm luôn trong vòng sửa H1. |
| M2 | Medium | `backend/apps/accounts/migrations/0015_seed_group_data_scopes.py:241-243` | Cách tính D7 từ `view_customer_list` lúc migrate là **an toàn** (xem mục Migration). Còn hai điều kiện triển khai. (a) Từ Lô 2 đến Lô 5, PUT của B4 chưa ghi D7. Nếu Lô 4 lên production trước Lô 5, Chủ bật "Xem khách hàng" cho K thì K qua được cổng nhưng danh bạ rỗng (lỗi chức năng, không rò). (b) Hôm nay `/api/sales/customers/` cho Quản lý thấy hết theo **thành viên nhóm** (`sees_customer_directory`), không theo quyền. Nếu trên production Chủ đã tắt `view_customer_list` của Quản lý, seed ra D7 = `none`, và từ Lô 4 Quản lý mất API khách cũ. Đây là thu hẹp, không phải rò. | (a) Ghi vào 02c: Lô 4 và Lô 5 lên production **cùng lượt**, không deploy Lô 4 riêng. (b) Lệnh đếm D-2 phải in riêng cờ "manager có `sales.view_customer_list`". Nếu không có thì hỏi Duy trước khi migrate. |
| L1 | Low | `snapshot.py:216-229` | Dashboard chỉ ghi `revenue_today` **có hay không**, không ghi giá trị. 02b §1.5 chuyển `revenue_today` sang `scope_invoices_for`. Tài khoản `direct_permissions` có `view_dashboard` và nhận D2 rank 0 (R9), nên số doanh thu của người này sẽ đổi mà mốc không bắt được. | Ghi thêm `extra:kpis.revenue_today=<giá trị>`. Đây là doanh thu, không phải giá vốn hay dữ liệu cá nhân. Làm cùng M1. |
| L2 | Low | `resolver.py:98-111` | Bộ nhớ tạm trên `user` an toàn **giữa** các request, vì TokenAuthentication nạp user mới mỗi request. Trong **một** request thì có thể cũ. (a) Lô 5 tính `rows_losing_access` cho thành viên: nếu bước "trước" gọi không kèm `overrides` thì đối tượng thành viên bị nhớ. (b) Service đổi nhóm của một user rồi phân giải lại trên cùng đối tượng đó. (c) Test dùng `force_authenticate(user)` nhiều lần với cùng đối tượng (bộ thu mốc làm vậy). | Lô 5: bước "trước" gọi `resolve_data_scopes(member, overrides={})`. `{}` khác `None` nên không bị nhớ. Thêm `resolver.forget(user)` (xoá `_data_scope_cache`) và gọi ở nơi đổi nhóm của user trong cùng request. Test Lô 3+ đổi cấu hình thì dùng `User.objects.get(pk=…)` mới, như với quyền. |
| L3 | Low | `erp-console/features/permissions/mock.ts:67` | Mock FE còn chữ cũ "Trong phạm vi gọi" cho CSKH. BE nay trả "Được gán hoặc trong phạm vi gọi xác nhận" (orders) và "Được gán" (deliveries). | Lô F1 sửa mock cho khớp BE. FE phải xử lý `gate_capability: null` (xem lệch 2): lúc đó chỉ dựa vào `inactive_reason`. |
| L4 | Low | `backend/apps/accounts/data_scopes/services.py:92-112` | Sau khi sửa H1, nhóm lưu D7 = `all` mà thiếu `view_customer_list` sẽ hiện `value: "all"` trên W3i, trong khi giá trị có hiệu lực là `assigned_deliveries`. | Lô 5 thêm `note` cho dòng D7 trong trường hợp này, ví dụ "Bật Xem khách hàng để thấy tất cả khách". Không chặn Lô 2. |

### Mốc Lô 1 (PV-01)

- **Độ phủ đường đọc:** đủ cho các đường GET trong 02b §1.5. Gồm đơn (list, detail, `?q=` theo SĐT và theo tên,
  `?customer=`), hoá đơn (list kèm tổng, detail), phiếu hoàn tiền, phiếu giao (list, `me`, người khác, detail), hàng hoàn,
  phiếu nhập (có ba mốc quanh nửa đêm giờ VN), hàng chờ gọi (3 trạng thái, detail, tìm), danh bạ mới và `/customers/` cũ,
  guidance của 5 loại chứng từ, dashboard, AI list và detail. Có 11 tài khoản, gồm K+G, người không nhóm có quyền gán trực
  tiếp, superuser và ẩn danh. Còn thiếu các đường ghi hoặc hành động (M1) và giá trị doanh thu dashboard (L1). AI list bị cắt
  12/16 đơn, chấp nhận được vì `ai.orders_detail` phủ từng đơn.
- **Dữ liệu cá nhân trong mốc:** không có. Mốc chỉ ghi nhãn fixture và đường dẫn ô (`pii:<nhãn>:<path>`), không ghi giá trị.
  Fixture toàn dữ liệu giả ("Khách Giả NN", `09000001NN`, "Số NN Đường Giả"). Có test AC4 grep chuỗi giả trong mốc, và grep
  độc lập của tôi cũng sạch. Mốc không có pk, nên tất định.
- **Cơ chế bắt R9:** `direct_permissions` đã có trong mốc. Khi Lô 3/4 nối resolver, hành vi của người này đổi (D1, D6, D7
  hẹp lại) và test mốc sẽ **đỏ**. Lô 3/4 **không được** thêm `APPROVED_DIFFS` cho `direct_permissions` khi Duy chưa trả lời
  D-3. Nếu được duyệt thì ghi mỗi mục kèm "Duy duyệt <ngày> D-3".

### Migration 0014/0015

- **Không đổi quyền của 5 nhóm:** 0015 chỉ đọc `group.permissions` và không ghi vào đó. Có test
  `test_pv02_ac1_seed_does_not_touch_group_permissions` chạy seed, unseed rồi seed và so quyền trước sau. Đạt.
- **Idempotent:** dùng `get_or_create` và không ghi đè `row_version` hay giá trị đã có. Có test chạy hai lần, và test chỉ bù
  dòng thiếu. Đạt.
- **Chạy lùi:** 0015 lùi bằng cách xoá dòng của 5 nhóm, 0014 lùi bằng cách xoá bảng. Dev đã chạy thật tiến, lùi về 0013 rồi
  tiến lại trên SQLite. Code cũ không đọc hai bảng này, nên rollback ứng dụng không cần migrate lùi. Đạt.
- **D7 tính từ `view_customer_list` lúc migrate trên production:** an toàn về rò rỉ. Lý do:
  1. Hôm nay danh bạ mới (`directory_api`) mở theo đúng quyền `view_customer_list`, không có phạm vi dòng. Nhóm nào có quyền
     này thì hôm nay đã thấy mọi khách, nên seed `all` không mở thêm gì.
  2. Nhóm không có quyền này nhận `none`, riêng G nhận `assigned_deliveries`. Đó là hẹp nhất hoặc bằng hôm nay.
  3. Chủ đổi quyền qua B4 trước ngày migrate thì seed đọc đúng trạng thái lúc đó, và test
     `test_pv02_ac1_customers_scope_follows_view_customers_permission_at_migrate_time` có phủ trường hợp này.

  Hai điều kiện triển khai nằm ở M2.
- Phụ thuộc đúng `accounts/0014` và `sales/0013`. Giá trị chép cứng, không import catalog. Có test so seed với
  `catalog.defaults`.

### Resolver

- **Chỉ xét nhóm đủ điều kiện:** đúng 02b với D1–D6 và D8 (`_resolve_object`, `resolver.py:76-78`). Test R1b đạt. D7 sai do
  thiết kế (H1).
- **Lấy rộng nhất:** dùng `rank` lớn hơn hẳn. Khi hoà thì giữ nhóm đứng trước theo thứ tự vai (có test). D2 lấy D1 **của
  chính nhóm** có quyền xem hoá đơn (có test). Owner và superuser nhận rộng nhất. Ẩn danh nhận rank 0 và không có truy vấn nào.
- **Cache:** an toàn giữa các request. Trong cùng một request có rủi ro dữ liệu cũ, xem L2. `overrides` không ghi vào bộ nhớ
  (có test).
- **Số truy vấn:** tối đa 3 (có test). Truy vấn permission lọc theo `codename` thôi nhưng ghép lại `app_label.codename` trước khi
  so, nên trùng codename giữa các app không gây sai. Đạt.
- **R9/D-3, rank 0 cho nhóm không đủ điều kiện:** đúng PV-02-AC4 đã duyệt. Với nhóm thật (K: D4 và D7; G và C: D2 và D6),
  mọi đối tượng rank 0 đều nằm sau cổng Tầng 1 mà nhóm không có, nên không mở đường mới. Người không nhóm có quyền gán trực tiếp
  sẽ đổi hành vi. Mốc bắt được, D-3 đếm trên production. Chấp nhận.

### Năm chỗ lệch 02b

| # | Lệch | Quyết định |
|---|---|---|
| 1 | `default_permissions = ()` cho cả `GroupAccessConfig` | **Duyệt.** Cấu hình chỉ sửa qua service. Không sinh permission vô chủ, nên ma trận B4 và Admin không thấy hai model này. Đã ghi vào 02b §3. |
| 2 | `gate_capability: null` khi mã việc chưa có ở registry (D2 tới Lô 3) | **Duyệt.** Contract 02b §2.2 đã cho phép `null`. Không trỏ FE tới việc không tồn tại. Từ Lô 3 tự thành `"view_sales_invoices"`. Lô 3 phải thêm test khẳng định dòng `invoices` có `gate_capability == "view_sales_invoices"`. |
| 3 | Nhãn `scopes` cũ: CSKH `orders` = "Được gán hoặc trong phạm vi gọi xác nhận", `deliveries` = "Được gán" | **Duyệt.** 02b đã đòi bỏ chữ sai "Trong phạm vi gọi". Ví dụ "Phiếu gán cho tôi" trong 02b §2.2 chỉ để minh hoạ. Giữ "Được gán" thì ít đổi FE hơn. Chỉ có mock FE dùng chuỗi cũ (L3). `scopes` bỏ hẳn ở Lô 6. |
| 4 | D2 của owner hiện `follows_orders`, có `note` của Chủ | **Duyệt.** D2 không có giá trị riêng. Dòng này `editable: false` và có note, FE hiển thị nhất quán. |
| 5 | Thêm hàm phụ `valid_or_narrowest`, `rank_of`, `widest_value`, `narrowest_value`, `ranked_options`, `stored_objects` | **Duyệt.** Đây là hàm dữ liệu thuần, có test catalog, và không trùng hàm nào sẵn có. |

### Giá vốn và dữ liệu cá nhân ở GET groups

- `GET /api/staff/groups/` và `GET /api/staff/groups/<code>/` chỉ thêm `version`, `data_scope_values` và `data_scopes`.
  Ba khoá này chỉ chứa mã và nhãn cố định trong catalog. Không có giá vốn hay dữ liệu khách. `members` không đổi (tên nhân viên
  đã có từ trước). Quyền đọc giữ `CanManageStaff` (401/403 có test). Đường `/api/staff/` đã nằm trong `FORBIDDEN_PREFIXES` của AI.
  Đạt.
- Truy vấn thêm: `list_groups` thêm 2 truy vấn cho cả danh sách (không N+1), `describe_group` thêm 2.

### Việc giao lại be-dev (vòng sửa)

1. **H1** (bắt buộc): sửa luật D7 trong `resolver.py` theo 02b §1.3 luật 4 mới, sửa test `test_resolver.py:141-144` và thêm
   3 test tái hiện như mô tả. Mốc PV-01 phải xanh và không được sinh lại.
2. **M1, L1** (nên làm luôn, bắt buộc trước Lô 4): mở rộng mốc với đường hành động và giá trị `revenue_today`. Sinh lại mốc
   bằng `UPDATE_SCOPE_SNAPSHOT=1` **trên HEAD trước khi sửa H1** (H1 không đổi hành vi hiện tại vì resolver chưa được gọi,
   nhưng tách riêng thì dễ soát hơn). Commit mốc riêng.
3. M2, L2, L3, L4 ghi vào 02c hoặc lô tương ứng, không cần sửa ở vòng này.

Lệnh kiểm chứng khi nộp lại: `manage.py test`, `makemigrations --check --dry-run`, `python3 scripts/check_naming.py`.

### Re-review sau d50d082 (06/10)

> Soát `fed7443..d50d082`: `adc9ba9` (M1 + L1, mốc mở rộng) và `d50d082` (H1 + L2).

**Kết luận: APPROVED.** Lô 1–2 BE đạt. Lô 3 bắt đầu được.

**Kiểm chứng đã chạy trong lượt re-review:**
- Toàn bộ `manage.py test` (`DJANGO_DEBUG=1`, symlink `backend/staticfiles` tạm, đã gỡ sau khi chạy): **2927 test, OK**.
- `makemigrations --check --dry-run`: `No changes detected`.
- `python3 scripts/check_naming.py`: OK, không phát sinh vi phạm mới.
- **Mốc mới chạy trên code gốc.** Tôi dựng worktree tạm ở `fa2368f` (trước mọi sửa code sản phẩm) và chép `data_scopes/tests`
  của HEAD vào, chỉ giữ test mốc. Kết quả `test_scope_snapshot` 10 test, OK. Vậy mốc mở rộng ghi đúng hành vi trước tính năng.
  Worktree tạm đã xoá.
- **So mốc cũ với mốc mới.** Mọi sự kiện cũ còn nguyên, không mục nào mất. Phần thêm gồm 15 nhóm `actions.*` và
  `extra:kpis.revenue_today=…`. Fixture đặt `issued` = NOW cho 2 hoá đơn nên doanh thu khác 0, và việc này không đổi sự kiện
  cũ nào. Không có sự kiện `EXC`. Mã ghi được gồm 200, 201, 400, 401, 403, 404, 409, tức có cả ca trong và ngoài phạm vi.

| Mục | Kết quả |
|---|---|
| H1 | **Đạt.** `catalog.py` thêm `full_perm` và `capped_value` cho `CUSTOMERS`. `resolver.py` chặn trần ở `assigned_deliveries` khi nhóm thiếu `view_customer_list`, đúng 02b §1.3 luật 4 mới, và không đụng D1–D6 hay D8. Có đủ 6 test: Quản lý mất list, G lưu `all` không có list, G có lại list, lưu `none` vẫn `none`, K+G không mượn `all`, nhóm không có quyền nào thì không đủ điều kiện. Test sai cũ đã được thay. Ma trận mặc định và mốc PV-01 xanh mà không phải sinh lại. |
| M1 | **Đạt.** Mốc thêm 15 nhóm hành động: gọi xác nhận (claim, gọi, huỷ xác nhận, đổi người nhận), hàng hoàn (tạo kèm ca không phiếu, huỷ, sửa), phiếu nhập (sửa, gửi, huỷ), phiếu giao (giao người, đổi trạng thái, xem/in/huỷ tem). Mỗi lần gọi bọc trong savepoint rồi rollback. Có test khẳng định số dòng không đổi. Body đổi người nhận dùng chuỗi giả, và mốc chỉ ghi mã HTTP. |
| L1 | **Đạt.** Mốc có `extra:kpis.revenue_today`. Đây là doanh thu, không phải giá vốn. |
| L2 | **Đạt.** `resolver.forget(user)` có test. |

**File ngoài danh sách 02b là `backend/apps/accounts/staff/services.py`. Tôi duyệt.** Lý do:
- Bản review đầu (L2) đã yêu cầu gọi `forget` ở nơi đổi nhóm. Đây là service duy nhất đổi nhóm của user.
- Phần sửa chỉ thêm import và 3 lời gọi. Không đổi luật, không đổi AuditLog.
- Không tạo vòng import, vì `resolver` chỉ phụ thuộc `models`, `roles` và `catalog`.
- `set_groups` quên cả đối tượng người gọi lẫn bản nạp mới. Đúng, vì `_lock_target_and_owners` trả về một đối tượng khác.
- Lời gọi trong `create_staff` thật ra không làm gì, vì user vừa tạo chưa có bộ nhớ tạm. Chấp nhận giữ lại cho đối xứng.

Ghi chú 02b §6, Lô 2: thêm `accounts/staff/services.py` vào danh sách file được sửa.

**Còn mở, không chặn duyệt, chuyển sang lô sau:**
- M2: Lô 4 và Lô 5 deploy cùng lượt; lệnh đếm D-2 in riêng cờ Quản lý có `view_customer_list`. Ghi vào 02c.
- L3: mock FE trong Lô F1.
- L4: `note` cho dòng D7 trong Lô 5.
- L2(a): bước "trước" khi xem trước ở Lô 5 dùng `overrides={}`.
- R9/D-3: không thêm `APPROVED_DIFFS` cho `direct_permissions` khi Duy chưa trả lời D-3.
- Thẩm mỹ: `snapshot.py` có 2 dòng trống thừa trước mục "đường hành động". Không cần sửa riêng.

## Review Lô 3 BE (07/10)

> Tech Lead · 2026-10-07 · commit `30bbc87` (PV-03, PV-07) trên `feat/pham-vi-du-lieu`, diff `7110254..30bbc87`. Nhánh đã
> merge main `7110254`.

### Kết luận: **APPROVED**, kèm 2 điều kiện cho lô sau (C1, C2)

Đơn và hoá đơn đã đọc phạm vi từ cấu hình qua một hàm duy nhất, V1 và V2 đã vào registry. Tôi không thấy chỗ rò dữ liệu cá
nhân hay giá vốn. Ngoài phạm vi trả 404. Số truy vấn trong ngân sách.

### Kiểm chứng đã chạy trong lượt review (HEAD `30bbc87`)

- Toàn bộ `manage.py test` (`DJANGO_DEBUG=1`, symlink `backend/staticfiles` tạm, đã gỡ): **OK**. Điều phối viên đếm được 3057 test.
- `makemigrations --check --dry-run`: `No changes detected`.
- `git merge-tree` giữa `feat/w37-l1-be` và `30bbc87`: merge sạch. Nhánh W37 L1 chưa có commit, phần sửa còn nằm trong worktree
  `w37-be` nên tôi soát tay (xem mục W37).

### Sáu câu hỏi của điều phối viên

| # | Việc | Quyết định |
|---|---|---|
| 1 | Hoãn D1 cho phiếu hoàn tiền và dashboard | **Duyệt hoãn, nhưng có hạn (C1).** Hoãn an toàn tới Lô 5: trước Lô 5 không có đường nào ghi được D1 (PUT phạm vi là việc của Lô 5; `GroupDataScope` không đăng ký Admin và không có permission), nên D1 của mọi nhóm vẫn là mặc định. Nhóm có `view_refund`/`view_dashboard` lúc này đều đang `all`, nên hành vi không đổi. Khi Lô 5 cho Chủ thu hẹp D1, phiếu hoàn và dashboard **phải** theo D1. Nếu không, Quản lý bị thu hẹp vẫn thấy mọi phiếu hoàn kèm tên/SĐT khách. Vì vậy **Lô 5 không được duyệt nếu thiếu phần này**. Để làm được thì cần Duy trả lời D-3. Điều phối viên nên hỏi Duy ngay, không đợi tới Lô 5. Không chấp nhận code lửng, và be-dev đã gỡ sạch (đúng). |
| 2 | `APPROVED_DIFFS` thêm `warehouse_courier invoices.list` | **Duyệt.** Người kiêm nhiệm có V2 và D2 = `all` nhờ nhóm NV kho, nên đây là cùng một ngoại lệ Q-4 chứ không phải ngoại lệ mới. Test AC3 khoá đúng hai mục và không có mục nào cho `direct_permissions`. |
| 3 | `ai/policy/rules.py` thêm `customer_hidden_reason` vào `SCRUB_PII_KEYS` | **Duyệt.** Bản thân cờ này không phải dữ liệu cá nhân. Bỏ nó khỏi đầu ra AI để kết quả AI không đổi: không bị cắt mất dòng ở `AI_RESULT_MAX_CHARS`, mốc `ai.orders_list` giữ nguyên. Sửa này chỉ thu hẹp đầu ra, không mở thêm gì. Nên ghi một dòng vào 02b §6 Lô 3. |
| 4 | Phiếu hoàn tiền khi bị che trả `null` thay vì `""` | **Duyệt.** Khớp 02b §2.7 ("ô khách vẫn `null`") và cùng cách với đơn, hoá đơn. Khi phiếu không có đơn mà không bị che thì vẫn trả `""` như cũ. FE Lô 7 phải chịu được `null` ở hai ô này. Mock F1 cũng phải có ca `null`. |
| 5 | Sửa 5 test cũ | **Duyệt cả 5.** Mỗi test đổi vì hợp đồng đổi có chủ ý: thêm khoá (`test_s10_api`, `test_invoice_list`); V2 thay `view_customer_list` làm cổng tên trên hoá đơn, kèm ngoại lệ Q-4 (`test_invoice_list`); V2 cấp cho 5 nhóm (`test_s47_me_labels`, `test_confirmation_role_scope`); serializer không có người gọi thì mặc định che, hướng an toàn (`test_auditlog_note_no_free_text`). Không test nào bị nới để che lỗi. Test M1 cũ được viết lại thành test V2, vẫn kiểm `customer_name` null và không có chuỗi tên giả trong body. |
| 6 | V2 = `sales.view_order_customer_info`; migration `sales/0015`, `0016`; người không nhóm mất V2 (R9) | **Duyệt.** Đánh số 0015/0016 đúng vì main đã có `0014_salesorder_cancel_note`. `0015` là AlterModelOptions tự sinh. `0016` theo mẫu `sales/0013`, cấp cho 5 nhóm, lùi bằng cách gỡ khỏi 5 nhóm. V2 không `owner_only`, perms tách khỏi V1 và khỏi `view_customer_list`. Khoá việc `view_order_customer_info` lấy theo tên permission, chấp nhận. **Về R9:** fixture PV-01 cấp V2 trực tiếp cho `direct_permissions`, nên mốc **không** bắt được việc người không nhóm mất tên khách. Chấp nhận, vì mốc dùng để chứng minh không đổi hành vi với cấu hình thật, và chỗ đổi này đã được ghi rõ. Nhưng câu hỏi D-3 gửi Duy phải nêu thẳng: "người không nhóm sẽ mất tên/SĐT/địa chỉ trên đơn, hoá đơn, phiếu hoàn cho tới khi được cấp V2 trực tiếp" (C2). |

### Soát thêm

- **Dữ liệu cá nhân.** Ô khách trên đơn (danh sách: `customer_name`, `customer_phone`; chi tiết: `customer{name,phone,address}`),
  danh sách hoá đơn (`customer_name`) và phiếu hoàn (`customer_name`, `customer_phone`) đều đi qua **một** hàm
  `customer_hidden_reason`. Thiếu V2 thì che, rồi mới xét quá cửa sổ. Chi tiết đơn không còn nhánh nào khác chứa dữ liệu khách:
  `delivery` chỉ có người giao (nhân viên); `payments` chỉ mã giao dịch và số tiền; `refunds` lồng không có tên; `invoice` chỉ
  mã. Chi tiết hoá đơn (`SalesInvoiceSerializer`) chỉ có `customer` dạng id, có test `test_pv07_invoice_detail_has_no_personal_data_keys`.
  Tìm `?q=` khi thiếu V2 chỉ khớp mã đơn, nên không dò được SĐT hay tên (có 2 test). Tra đơn công khai Shop không đổi (có test).
  Serializer không có `request` thì mặc định che.
- **`cancel_note`.** Bị che theo V2 lẫn cửa sổ (`orders/serializers.py`, `get_cancel_note`), trả `""` như luật cũ, có test
  `test_pv07_cancel_note_stays_empty_when_customer_hidden`. Đạt.
- **Giá vốn.** Không đụng `CostFieldSerializerMixin` hay `sensitive_fields`. Test `test_pv03_ac8_no_cost_fields_for_user_without_view_cost`
  kiểm với NV kho và NV giao. Đạt.
- **404 ngoài phạm vi.** `get_queryset` lọc theo D1, nên chi tiết, hành động `get_object` và AI đều trả 404. Có test AC4 và AC5. Cổng
  Tầng 1 vẫn đứng trước: tắt `view_orders` thì 403 dù D1 = `all` (test AC7). Đạt.
- **Số truy vấn.** Phân giải nhớ trên user, nên danh sách đơn (NV giao) và danh sách hoá đơn (NV kho) chỉ tăng tối đa 3 truy vấn
  (`QueryBudgetTests`). `customer_hidden_reason` gọi `has_perm` cho từng dòng nhưng dùng `_perm_cache`, không thêm truy vấn. Đạt R8.
- **Rò chéo nhóm.** `test_pv03_cross_group_leak_is_closed` có; D2 theo D1 của nhóm có quyền xem hoá đơn (Q-7, test PV-07-AC6). Đạt.
- **Code chết.** Đường đơn và hoá đơn không còn `has_full_delivery_scope` hay `is_customer_service`; `pii_hidden` đã bỏ, không còn
  chỗ gọi. Hàm cũ trong `common/api.py` bỏ ở Lô 6 theo kế hoạch.

### Va chạm với W37

- **W37 L1** (worktree `w37-be`, chưa commit): sửa `delivery/api.py`, `delivery/services.py`, `sales/orders/services.py`, `completion.py`
  mới và test `cancel_paid_order`. **Không trùng file** với Lô 3, và không dùng hàm Lô 3 đã đổi chữ ký (`scope_orders_for`,
  `annotate_order_pii_visible`) hay đã bỏ (`pii_hidden`). Lô 3 merge vào main trước hay sau W37 L1 đều được. **Lô 4** thì sẽ sửa đúng
  `delivery/api.py` (`get_serializer_context`, `get_queryset`, lọc `assigned_to`), cùng file W37 L1 đang sửa. Đề nghị: bắt đầu Lô 4 sau
  khi W37 L1 đã vào main, rồi `git merge main` trước khi code.
- **W37 L2** (`refund_summary` trong `sales/orders/serializers.py`): trùng file với Lô 3. Merge sau thì sửa phần xung đột bằng tay; khu
  vực gần `get_refunds` và `get_cancel_note`. **Luật cho W37 L2:** nếu `refund_summary` có bất kỳ ô nào là dữ liệu khách (tên, SĐT, ghi
  chú tự do) thì phải che bằng `hidden_reason(self, order)` như `customer` và `cancel_note`. Tốt nhất là chỉ trả số tiền và trạng thái.
  Techlead sẽ soát điểm này khi review W37 L2.

### Điều kiện chuyển lô

- **C1 (chặn duyệt Lô 5):** phạm vi D1 cho `sales/refunds/api.py::get_queryset` và cho `reports/dashboard_api.py` (`recent_orders`,
  `pending_orders`, `booked_soon` qua `scope_orders_for`; `revenue_today` qua `scope_invoices_for`) phải vào trước hoặc cùng Lô 5. Lệch
  mốc của `direct_permissions` chỉ được ghi vào `APPROVED_DIFFS` sau khi Duy trả lời D-3, kèm "Duy duyệt <ngày> D-3".
- **C2 (D-3, trước deploy production):** lệnh đếm người không nhóm có quyền gán trực tiếp phải liệt kê thêm ai đang có
  `sales.view_salesorder`/`view_salesinvoice`/`view_refund`. Câu hỏi gửi Duy nêu rõ họ sẽ mất tên khách cho tới khi được cấp V2.
- Ghi 02b §6 Lô 3: thêm `ai/policy/rules.py` (điểm 3) vào danh sách file đã sửa; số migration sales là 0015/0016.
- Chưa tự chạy migrate lùi `sales 0016 → 0014` trên DB thật. Hàm `revoke` là bản chép mẫu `sales/0013` đã chạy trên production. QA
  nên chạy tiến/lùi trên SQLite tạm khi nghiệm thu.

## Review Lô 4 BE (08/10)

> Tech Lead · 2026-10-08 · commit `d861021` (PV-04, PV-05, PV-06) trên `feat/pham-vi-du-lieu`, diff `151b56e..d861021`. Nhánh đã
> merge main có W37 L1.

### Kết luận: **APPROVED-chờ-Duy**

Code sản phẩm đạt. Tôi không thấy rò dữ liệu cá nhân hay giá vốn. Phạm vi D3–D7 đọc từ cấu hình qua một hàm cho mỗi đối tượng.
**Chưa merge main** khi chưa đủ hai việc sau:
- **(a) M1:** sửa tệp test mốc theo mục 1 dưới đây. Chỉ đụng test, techlead soát lại tệp đó, không cần review lại code sản phẩm.
- **(b) Duy trả lời D-3:** người không nhóm bị thu hẹp D6/D7. Lô 4 vẫn ở trên nhánh. Lô 5 làm tiếp được song song.

### Kiểm chứng đã chạy trong lượt review (HEAD `d861021`)

- `manage.py test apps.accounts apps.delivery apps.purchasing apps.sales apps.inventory.returns apps.common`, chạy với `DJANGO_DEBUG=1`
  và symlink `staticfiles` tạm (đã gỡ): **2006 test, OK (skipped=2)**. Điều phối viên đang chạy lại toàn bộ.
- Grep `apps/` (trừ `tests/`) tìm `has_full_delivery_scope`, `sees_customer_directory`, `FULL_SCOPE_GROUPS`,
  `CUSTOMER_DIRECTORY_GROUPS`, `is_customer_service`: không còn.
- So mốc `151b56e` với `d861021` bằng script: **chỉ** `direct_permissions` đổi, ở `receipts.list/detail`, `guidance.receipt`,
  `directory.list/detail/search`, `customers.list/detail`, `guidance.customer`. Mọi chỗ đổi đều là **thu hẹp**: dòng biến mất, hoặc
  200 thành 404. Không có dòng thấy thêm, không có ô `pii` thêm. Mọi tài khoản khác và hai mục Q-4 giữ nguyên. Nghĩa là phần V2
  áp lên phiếu giao (mục 3) không đổi gì với cấu hình mặc định.
- `TIME_ZONE = "Asia/Ho_Chi_Minh"`, `USE_TZ = True`, và không có chỗ nào gọi `timezone.activate` ngoài test.

### Năm điểm lệch

| # | Điểm | Quyết định |
|---|---|---|
| 1 | Người không nhóm (R9/D-3): sinh lại mốc cho `direct_permissions` thay vì thêm `APPROVED_DIFFS` | **Đúng là lách luật, về hình thức.** Luật "không thêm `APPROVED_DIFFS` cho `direct_permissions` khi Duy chưa trả lời D-3" nhằm giữ mọi thay đổi hành vi **hiện rõ** cho tới khi Duy duyệt. Sinh lại mốc cho kết quả y như thêm ngoại lệ, mà còn tệ hơn: tệp mốc mới không còn ghi lại "trước đây thế nào", và test không còn nơi nào nói "đang chờ Duy". Không có ý gian: dev-notes ghi rõ. Về nội dung thì **chấp nhận hướng thu hẹp**: không rò, đúng luật PV-02-AC4 đã duyệt, đúng 02b §7 D-3 đã tiên liệu. Giữ hành vi cũ riêng cho người không nhóm sẽ phải thêm nhánh `if not groups` ở ba hàm phạm vi, tức là code chết sau D-3 và lặp lại đúng kiểu gắn cứng tên nhóm mà tính năng này bỏ đi. **Bác cách đó.** **Sửa M1 (bắt buộc trước merge main, chỉ tệp test):** (i) trả các dòng `direct_permissions` trong `scope_snapshot_baseline.json` về như ở `151b56e`; (ii) thêm `PENDING_DUY_DIFFS` trong `snapshot.py`, mỗi mục là `(user, endpoint, sign, glob)` kèm chú thích `"CHỜ Duy D-3"`, và cho `is_approved` chấp nhận; (iii) thêm test: mọi mục `PENDING_DUY_DIFFS` có `user == "direct_permissions"` và chỉ là thu hẹp, tức dấu `-`, hoặc dấu `+` với sự kiện dạng `status:*=404`; (iv) khi Duy trả lời D-3, chuyển các mục sang `APPROVED_DIFFS` kèm "Duy duyệt <ngày> D-3", hoặc sửa code nếu Duy chọn khác. Điều phối viên ghi vào 02c: **không merge main khi `PENDING_DUY_DIFFS` còn mục.** |
| 2 | D4 của người không nhóm là `none`, thay cho "rank 0" của 02b | **Duyệt. 02b sai ở điểm này.** Rank 0 của D4 (`pending_or_called_recently`) mở **thêm** mọi phiếu đang chờ gọi, kèm tên và SĐT, cho người chưa từng có phạm vi đó. Như vậy là mở rộng dữ liệu khách mà không ai xác nhận, trái nguyên tắc R1. Giữ `none` tức là giữ hành vi cũ, và mốc `confirmation.*` không đổi. Giá trị nội bộ `none` không phải lựa chọn của Chủ và không lưu xuống bảng nên chấp nhận được. PV-14 (`/api/auth/me`) hiển thị D4 = "Không xem" cho trường hợp này, khớp 02b §2.8. Đã sửa 02b §4 R9 trong commit này. |
| 3 | V2 áp cho phiếu giao (đóng N2) | **Duyệt về kỹ thuật, và phải báo Duy.** Nếu không áp, Chủ tắt V2 cho NV kho vẫn còn lộ khách qua `/delivery/notes/`, vì D3 của NV kho là `all`. Khi đó mục tiêu của D-1 ("tắt V2 là đóng hẳn") không đạt. Mặc định không đổi gì (mốc khớp). Ba điều phải báo Duy cùng D-3: (a) nhãn V2 "trên đơn & hoá đơn" nay phủ cả phiếu giao và phiếu hoàn, nên Lô 5/F1 đổi nhãn sau khi Duy chốt chữ; (b) Chủ tắt V2 cho NV giao thì NV giao không còn thấy địa chỉ giao, nên W3i phải cảnh báo khi tắt V2 của `delivery_staff` (Lô 5/F1); (c) **tem giao hàng** (`GET /delivery/notes/<id>/label/`, `labels/services.py::get_label_data`) vẫn trả tên người nhận và địa chỉ theo quyền `print_label`, không theo V2. Đây là điều cố ý, vì đóng gói cần tem. Hàng chờ gọi xác nhận cũng theo D4 và việc "Gọi xác nhận đơn", không theo V2. Vậy nên "tắt V2 của NV kho" **không** đóng tem: muốn đóng hẳn thì Chủ tắt cả "In tem". Phải ghi điều này vào câu báo Duy, không để Duy hiểu V2 là công tắc duy nhất. |
| 4 | Danh bạ ẩn `note`/`default_address` khi D7 khác `all` | **Duyệt.** Đây là thu hẹp, giống cách `CourierCustomerSerializer` đang làm. Hôm nay nhóm không có D7 `all` nhận 403 nên không có hợp đồng cũ nào bị phá. Thiếu context cũng ẩn, hướng an toàn. Ghi chú nhỏ, không chặn: người phạm vi hẹp vẫn `PATCH` được `note`/`default_address` dù không đọc được. Hiếm, vì cần cả `view_customer_list` lẫn `change_customer`. Ghi lại để Lô 5 cân nhắc. |
| 5 | Xoá sớm 4 hàm trong `common/api.py` | **Duyệt.** Grep sạch, test PV-05-AC8 có. Để tới Lô 6 thì chỉ giữ code chết. Ghi vào 02b §6 Lô 4. |

### Soát thêm

- **Ràng buộc W37.** `scope_deliveries_for` với `assigned` chỉ lọc `assigned_to=user`, không lọc trạng thái, nên phiếu CANCELLED của
  NV giao vẫn nằm trong queryset và nhận 400 `BR-GH-24` (test `test_pv04_courier_still_sees_own_cancelled_note_for_br_gh_24`). Lô 4
  không sửa `set_status` hay `order_status`; diff `delivery/api.py` chỉ đụng `get_serializer_context`, `get_queryset` và
  `_filter_assigned_to`. Đạt.
- **D6 theo ngày lịch VN.** `vietnam_day_bounds` lấy `timezone.localtime` (múi VN theo settings), tính 00:00 đến 00:00 hôm sau rồi so với
  `created_at` UTC. Có test 10:00, 23:55, qua nửa đêm, và test chứng minh không dùng ranh ngày UTC. Huỷ phiếu: `cancel_scope_q` giữ
  luật cũ, xử lý đúng bẫy `Q() | Q(x)`, ngoài cả hai thì 404, trong D6 mà không phải người tạo thì 403. Có test AC5/AC6 và test Quản
  lý có D6 hẹp. Đạt.
- **404/403.**
  - Ngoài phạm vi trả 404 ở chi tiết, hành động `get_object` (đổi trạng thái, giao người, tem), dòng thời gian và khách.
  - `?assigned_to=<người khác>` trả 403 khi D3 khác `all`, như cũ.
  - `?customer=` ngoài D7 cho danh sách rỗng 200, sau cổng 403.
  - Cổng Tầng 1/2 vẫn đứng trước: có test 403 khi phạm vi `all` nhưng thiếu quyền, cho phiếu giao, gọi xác nhận, danh bạ và phiếu nhập.
  - Đạt.
- **Số truy vấn.** Phân giải nhớ trên user. Gọi xác nhận tính D4 một lần cho mỗi request và đưa vào context. Mỗi dòng phiếu giao chỉ
  thêm `has_perm` (dùng `_perm_cache`). D7 hẹp là một subquery `pk__in`, không `distinct`, nên annotate của danh bạ còn nguyên.
  `?customer=` thêm một truy vấn `exists`. Không thấy N+1. **Thiếu** test ngân sách truy vấn cho danh sách phiếu giao và hàng chờ
  gọi (L1).
- **Giá vốn.** Không đụng `CostFieldSerializerMixin`. Có test không khoá giá vốn ở phiếu giao, hàng hoàn, phiếu nhập. Đạt.
- **Dữ liệu cá nhân.**
  - Phiếu giao: ẩn theo V2 hoặc cửa sổ; phản hồi đổi trạng thái dùng cùng luật (test N2).
  - Danh bạ hẹp: không có `note`, `default_address`.
  - `/customers/` hẹp: dùng `CourierCustomerSerializer`.
  - Tìm gọi xác nhận: ngoài D4 thì SĐT bị che (test `test_pv05_search_masks_outside_scope_by_d4`).
  - Tem: xem mục 3(c).
  - Đạt.

### Mục mức thấp (không chặn)

| # | Mức | Vấn đề | Xử lý |
|---|---|---|---|
| L1 | Low | Chưa có `assertNumQueries` cho `GET /api/delivery/notes/` và `GET /api/confirmation/queue/` (R8) | Lô 5 thêm: so với lúc giả lập resolver trả hằng, tăng tối đa +3, như `QueryBudgetTests` của Lô 3 |
| L2 | Low | Người kiêm **NV kho + CSKH**: trước đây `has_full_delivery_scope` cho thấy mọi phiếu chờ gọi; nay chỉ nhóm CSKH đủ điều kiện D4 (NV kho không có `confirm_with_customer`), nên còn `pending_or_called_recently`. Đây là thu hẹp, đúng luật "nhóm đủ điều kiện". Fixture không có tổ hợp này nên mốc không bắt | Lệnh đếm D-2 liệt kê thêm người thuộc cả `warehouse_staff` lẫn `customer_service`. Có người thì báo Duy cùng D-3 |
| L3 | Low | V2 nay phủ phiếu giao nhưng phiếu giao chưa có `customer_hidden_reason`, nên FE không phân biệt được "quá 7 ngày" với "không có quyền" | Lô 7 thêm khoá này (chỉ thêm), cùng hàm với đơn |

### Gửi Duy (điều phối viên gộp vào câu hỏi D-3)

1. D-3: người không nhóm có quyền gán trực tiếp sẽ (a) chỉ thấy phiếu nhập mình tạo trong ngày, (b) không thấy danh bạ hay `/customers/`,
   (c) mất tên khách trên đơn, hoá đơn, phiếu hoàn khi chưa được cấp V2 (Lô 3). Hàng chờ gọi giữ như cũ. Kèm số người đếm được trên production.
2. V2 phủ cả phiếu giao. Tắt V2 cho NV giao thì họ mất địa chỉ giao. Tem vẫn theo "In tem", hàng chờ gọi theo "Gọi xác nhận đơn". Đề nghị
   đổi nhãn V2 thành "Xem thông tin khách trên đơn, hoá đơn, phiếu giao".

## Review Lô 4 M1 + Lô 5 + C1 (08/10)

> Tech Lead · 2026-10-08 · `f4eec0b..5fd4032`: `090e6ef` (M1), `5457c2d` (Lô 5: PV-08, PV-09 BE, PV-10 BE, `/me` `is_superuser`, L1,
> L4), `5fd4032` (C1: phiếu hoàn tiền và dashboard theo D1/D2).

### Kết luận: **APPROVED-chờ-Duy**

Code đạt: không rò giá vốn, không rò dữ liệu cá nhân. CAS, xác nhận mở rộng, AuditLog và xem trước đúng 02b §2.3–§2.5. M1 của review
Lô 4 đã làm đúng. Lý do "chờ Duy": `PENDING_DUY_DIFFS` vẫn còn mục (D-3), nên theo luật đã đặt thì **chưa merge main**. Không cần review
lại code khi Duy trả lời, chỉ cần soát lại lần chuyển `PENDING_DUY_DIFFS` sang `APPROVED_DIFFS`.

### Kiểm chứng đã chạy trong lượt review (HEAD `5fd4032`)

- `manage.py test apps.accounts apps.reports apps.sales.refunds apps.delivery` với `DJANGO_DEBUG=1` và symlink `staticfiles` tạm (đã gỡ):
  **1078 test, OK (skipped=3)**. Điều phối viên đang chạy lại toàn bộ.
- `makemigrations --check --dry-run`: `No changes detected`.

### M1 (`090e6ef`): đạt

Mốc `direct_permissions` đã trả về hành vi cũ. `PENDING_DUY_DIFFS` tách khỏi `APPROVED_DIFFS`, mỗi mục ghi "CHỜ Duy D-3". Test khẳng định ba
điều: mọi mục thuộc `direct_permissions`; mọi mục là thu hẹp; một dòng thấy **thêm**, hay một lệch ở tài khoản khác, thì **không** được miễn.
Docstring của test mốc ghi luật "không merge main khi còn mục".

### Sáu câu hỏi

| # | Điểm | Quyết định |
|---|---|---|
| 1 | PUT dùng `scopes`, không dùng `data_scope_values` | **Đúng 02b §2.3, duyệt.** `data_scope_values` là khoá của GET (trạng thái đầy đủ), còn `scopes` là phần thay đổi gửi lên. Phiếu giao việc ghi nhầm, sẽ sửa trong 02c. |
| 2 | PO-Q1 chỉ kiểm khi request đụng `view_customers` hoặc `scopes.customers` | **Duyệt.** Trạng thái "Xem khách hàng bật, D7 = `none`" không thể sinh ra qua PUT mới, vì mọi lần đụng tới đều bị kiểm. Trạng thái này chỉ có ở dữ liệu cũ, mà seed 0015 đã đặt D7 = `all` cho nhóm đang có `view_customer_list`. Nếu kiểm ở mọi lần lưu thì dữ liệu lệch sẵn sẽ chặn cả những lần lưu không liên quan. Tôi chọn hành vi BE. **Mock F1 phải sửa theo BE** ở Lô 6 FE. Chỉ khác ở ca dữ liệu lệch sẵn nên không ảnh hưởng vận hành. |
| 3 | `widened[]` có D2 và V2, mock F1 chưa có | **Duyệt BE, đúng 02b §2.5.** Lô 6 FE phải: (a) chịu được `key` ngoài `SCOPE_BY_KEY`, gồm `invoices` và `view_order_customer_info`; (b) lấy nhãn V2 theo chữ mới sau khi Duy chốt; (c) thêm 2 ca này vào mock và vitest. Đây là điều kiện nghiệm thu Lô 6, ghi vào 02c. |
| 4 | Hai mục `+` ở dashboard trong `PENDING_DUY_DIFFS` | **Chấp nhận.** Đây thật sự là thu hẹp, nhìn bề ngoài mới giống "thấy thêm": (a) `+ extra:kpis.X=<số mới>` luôn đi cùng `- extra:kpis.X=<số cũ>`, vì một con số đổi giá trị luôn hiện thành cặp `-`/`+`; (b) `visible:order_assigned_direct` là đơn **đã** nằm trong D1 của chính người này (mốc `orders.list` có sẵn). Đơn này chỉ lọt vào nhóm 8 đơn gần nhất vì các đơn khác bị lọc đi, không có dữ liệu mới nào. **L-a (Low):** glob `extra:kpis.*` rộng quá, một KPI **tăng** cũng lọt. Khi chuyển sang `APPROVED_DIFFS` sau D-3, ghi đúng giá trị (`extra:kpis.pending_orders=1`, `extra:kpis.revenue_today=0`…) thay cho `*`. |
| 5 | Phiếu hoàn không gắn đơn bị ẩn khi D1 khác `all` | **Duyệt.** Phiếu không gắn đơn thì không thuộc phạm vi nào ngoài `all`, nên ẩn là hướng an toàn. Mặc định Chủ, Quản lý ở `all` nên thấy như hôm nay. Có test `test_c1_refund_without_order_is_hidden_when_d1_is_narrow`. |
| 6 | Sửa test cũ | **Duyệt cả nhóm.** `put_caps` chỉ thêm `version` lấy từ GET, không nới kiểm. `test_api_read` và `test_api_write` gửi thêm `scopes.customers` và `confirm_…` đúng bước 10, 11; riêng ca bật lại `view_customers` cho Quản lý còn khẳng định **trước** rằng thiếu xác nhận thì nhận 400 `CUSTOMER_DATA_WIDENING_UNCONFIRMED`, tức là chặt hơn cũ. Hai test khoá `/me` chỉ thêm `is_superuser`. Test GROUP_LOCKED thêm `version`. |

### Soát thêm

- **CAS và 409.** `GroupAccessConfig` được `select_for_update().get_or_create` trong `transaction.atomic`, rồi so `str(row_version)` với
  `version`. Lệch thì trả `ConflictError` 409 `GROUP_CHANGED`. `row_version` chỉ tăng một lần bằng `F() + 1`, và chỉ khi có thay đổi thật.
  Lưu không đổi gì thì không tăng, không ghi AuditLog. Thứ tự kiểm khớp 02b: lỗi đầu vào trước 409, 409 trước `requires`, PO-Q1 và mở rộng.
  Có test version không phải số (409, không 500), test nhóm thiếu dòng cấu hình, và test đua thật trên Postgres (skip trên SQLite). **Test
  đua phải chạy trên staging hoặc CI trước khi deploy.**
- **Xác nhận mở rộng và AuditLog.**
  - BE chặn được kể cả khi FE bỏ qua. `impact` nằm trong body lỗi 400.
  - Cờ `customer_data_widening_confirmed` ghi ở dòng AuditLog phạm vi nếu có đổi phạm vi, không thì ở dòng AuditLog việc.
  - `changes` chỉ có mã (test AC9).
  - AuditLog lỗi thì rollback toàn bộ (AC6).
  - Dòng thời gian, `capability_change_label` và `scope_change_label` bỏ qua khoá không phải mã.
  - Mở rộng tính theo **rank hiệu lực** (luật H1). Bốn ca `MockParityTests`, cộng ca 3b (tắt là thu hẹp) và ca 5 (câu nhiều đối tượng),
    khớp luật mock F1.
- **Xem trước.**
  - Chỉ Chủ hoặc superuser gọi được, test AC7 phủ cả Quản lý.
  - Kiểm giống PUT (`test_pv09_preview_validates_like_put`), không ghi gì.
  - `rows_losing_access` gọi `resolve_data_scopes(member, overrides={})`, đúng L2(a), nên không ghi vào bộ nhớ tạm.
  - Đếm gộp không trùng và bỏ dòng đã kết thúc.
- **Dữ liệu cá nhân và giá vốn trong `impact`/preview.** Chỉ có mã, nhãn cố định, `id` và tên hiển thị **nhân viên**. Không tên, SĐT hay địa
  chỉ khách, không số tiền (test AC9). Thân yêu cầu không bị log.
- **`revenue_today` theo D2.**
  - Với `all`, `scope_invoices_for` trả nguyên queryset, nên tổng hoá đơn không đổi.
  - `SalesCreditNote.sales_invoice` là FK **không null**, nên `sales_invoice__in=<mọi hoá đơn>` vẫn trừ đủ mọi phiếu đảo như cũ.
  - Với phạm vi hẹp, phiếu đảo hôm nay chỉ trừ khi thuộc hoá đơn trong phạm vi, kể cả hoá đơn phát hành hôm trước. Đây đúng là phần doanh
    thu bị đảo của tập hoá đơn người đó thấy.
  - `annotate(pii_visible=Exists(...))` không nhân dòng, vì lọc dùng `sales_order_id__in`.
  - Tiền là `Decimal` qua `Coalesce(..., DecimalField())`.
  - Mốc cho thấy Chủ, Quản lý, NV kho giữ `revenue_today=200000.0`.
  - Có test `test_c1_revenue_subtracts_only_credit_notes_in_scope`.
  - Đúng.
- **Ngân sách truy vấn.** L1 đã có `assertNumQueries`, tối đa +3 cho danh sách phiếu giao, hàng chờ gọi, phiếu nhập, hàng hoàn và khách.
  Preview thì không có ngân sách: số truy vấn bằng khoảng (số thành viên × số đối tượng đổi) + 5 nhóm. Chấp nhận được với quy mô vựa (L-b).

### Mục mức thấp (không chặn)

| # | Vấn đề | Xử lý |
|---|---|---|
| L-a | `PENDING_DUY_DIFFS` có `+ extra:kpis.*` (glob rộng) | Khi chuyển sang `APPROVED_DIFFS` sau D-3, ghi đúng giá trị số |
| L-b | Preview chưa có ngân sách truy vấn; `rows_losing_access` không phản ánh việc đổi **việc** trong cùng yêu cầu, vì resolver đọc quyền thật trong DB | Ghi nhận. Số dòng chỉ là thông tin cho Chủ. Nếu vựa lớn lên thì thêm ngân sách |
| L-c | `_held_after` dùng biểu thức điều kiện cho lệnh có tác dụng phụ (`after.update(...) if wanted else after.difference_update(...)`) | Đổi sang `if/else` khi có dịp sửa file này |

### Điều kiện còn mở

- **D-3 (Duy):** khi trả lời, chuyển `PENDING_DUY_DIFFS` sang `APPROVED_DIFFS` (L-a), hoặc sửa code theo lựa chọn của Duy. Sau đó mới merge main.
- **Deploy:** BE (Lô 4 và Lô 5) lên cùng lượt với ERP gửi `version` (R11, M2). Chạy test đua Postgres. Chạy lệnh đếm D-2 và D-3 (thêm người
  kiêm NV kho + CSKH, xem L2 Lô 4).
- **Lô 6 FE:** mock theo PO-Q1 của BE; chịu được `widened[].key` là `invoices` hoặc `view_order_customer_info`; nhãn V2 theo chữ Duy chốt.

## Lô QĐ-08/10 BE (08/10)

Techlead review `git diff main...HEAD` nhánh `feat/qd-0810-be` (`b802baf`), đối chiếu `02c-quyet-dinh-08-10.md` §A, B.2, B.4.2, C.4, E, F.
Kết luận: **REVIEW PASS (APPROVED)**. Không có lỗi Critical, High hay Medium. Có 4 mục Low, không chặn merge.

### Kiểm chứng đã chạy (lệnh lẻ, < 1 phút)
- `manage.py test apps.accounts.auth.tests.test_no_role_gate` + 3 test thăm dò tạm (đã xoá, không commit): session auth bị chặn
  `AUTH_NO_ROLE`; không nhóm + mật khẩu tạm trả `AUTH_MUST_CHANGE_PASSWORD` trước; `POST /api/sales/orders/1/cancel/` bị 403
  `AUTH_NO_ROLE`; `GET /api/shop/catalog/` kèm token người không nhóm vẫn 200; `POST /api/internal/payments/sepay-ipn/` kèm token
  đó không bị cổng. Kết quả `Ran 12 tests ... OK`.
- `makemigrations --check --dry-run`: No changes detected. `python3 scripts/check_naming.py`: OK, không phát sinh mới.

### 1. Cổng D-3 `AUTH_NO_ROLE` (`backend/apps/accounts/auth/authentication.py:56-81`)
- **Phủ route.** Cổng ở lớp xác thực mặc định, nên mọi view DRF dùng token hay session đều qua. Đã grep: không view nào tự khai
  `authentication_classes`, không có `get_permissions()` override hay `@action(permission_classes=...)`, không có `@api_view`. Route
  ngoài DRF chỉ có `admin/` (Django admin, chỉ superuser, không đổi) và `api-auth/` (form đăng nhập browsable). Test quét mọi route
  DRF dưới `/api/` (hơn 40 đường bị chặn) bắt được view mới quên miễn.
- **Miễn đúng.** Shop (`catalog`, `orders`, `checkout`), `public/*`, `site-info` đều `[AllowAny]`. Internal SePay webhook/IPN là
  `[AllowAny]` cộng `X-Internal-Token`. Adapter không gửi `Authorization`, nên lớp xác thực trả `None` và cổng không chạy. Login,
  me, logout, change-password có `allow_without_group = True`. `ObtainAuthToken` có `permission_classes = ()` nên không lọt vào
  nhánh "public", nhưng đã có cờ miễn.
- **Thứ tự.** `MustChangePassword` (`:76`) đứng trước `NoRole` (`:79`), đúng §B.4.2.
- **Thân 403.** Chỉ `{"detail", "code"}` qua `render_code` của `apps/common/api.py:199`. Câu chữ cố định, không có username hay
  dữ liệu khách. Có test.
- **Bỏ cache (lệch 02c).** Chấp nhận. `authenticate` chạy một lần mỗi request trên đối tượng user mới, nên cache trên user không
  tiết kiệm được gì. Chi phí là một `EXISTS` trên `auth_user_groups` (có index `user_id`) cho mỗi request của người không phải
  superuser. Lợi ích: gỡ nhóm có hiệu lực ngay (có test).
- **Hướng sai an toàn.** Nếu sau này có view tự trả quyền khác nhau theo action qua `get_permissions()`, `_is_public_view` chỉ đọc
  thuộc tính lớp. Khai `IsAuthenticated` mà trả `AllowAny` thì hỏng theo hướng đóng (an toàn). Ngược lại, lớp `AllowAny` mà trả quyền
  chặt hơn thì chỉ hở D-3 cho đúng view đó. Hiện không có view nào như vậy. Xem L3.

### 2. Superuser không nhóm (`auth/services.py:92-101`, `:123`, `:135-136`)
- Không mở rộng quyền. Superuser vốn có `has_perm` mọi quyền và trước lô đã gọi API được. Lô chỉ đổi `home` sang `dashboard`, thêm
  khoá `is_superuser` và cho qua cổng D-3. `groups`/`group_labels` vẫn là nhóm thật, không bịa `owner`, nên luật "còn ít nhất một Chủ"
  không đổi. Superuser chỉ thuộc `delivery_staff` cũng về `dashboard` (có test).
- Contract `me` chỉ thêm khoá, đúng §A.2. Vị trí và comment khớp nhánh phạm vi, nên khi gộp chỉ cần giữ một dòng.

### 3. Migration `sales/0019_alter_salesorder_view_order_customer_info_label.py`
- Chỉ có `AlterModelOptions` (đổi nhãn quyền), phụ thuộc `0018`, đúng số kế tiếp trên main. `feat/pham-vi-du-lieu` và
  `feat/pham-vi-fe` không có `sales/0019`, nên không trùng số. Không đụng schema. Nhãn `Permission.name` trên DB cập nhật qua
  `post_migrate`, như mẫu `0018`.

### 4. Ẩn dòng AI (`backend/apps/common/ai_visibility.py:12, 28-32`)
- Chỉ lọc khi `AI_ENABLED` tắt; khi bật thì trả nguyên queryset (có test cả hai chiều). Chỉ ẩn khi đọc, không xoá `AuditLog`.
- Vẫn giữ dòng nghiệp vụ do người duyệt thực thi có `proposal_ref` (có test). Lọc `?action=ai_config_update` khi tắt trả 0 (có test).
- `startswith` trên `action`: đã grep, không có action nghiệp vụ nào bắt đầu bằng `ai_config_`, `ai_policy_` hay `downgrade_`.

### 5. Seed QA `qa_nogroup` (`backend/apps/accounts/qa_fixture/build.py:77-78, 178-183`)
- Hợp lý. Hai quyền xem gán trực tiếp giúp e2e chạy BE thật bắt được ca "có quyền vẫn bị chặn". Dữ liệu giả, không có giá vốn hay
  dữ liệu cá nhân thật. `set(...)` chạy cho mọi user QA nên seed vẫn idempotent: user khác bị đặt lại về rỗng, đúng ý seed.

### 6. Giá vốn, dữ liệu cá nhân, contract
- Không serializer nào đổi field, không log mới. Khoá mới `is_superuser` chỉ trả về chính người đăng nhập.
- Nhãn V2 đổi đủ 3 chỗ, khớp 02c §C.4. Nhãn vai và nhóm lệnh AI đổi khớp bảng §F. Không đụng `delivery/serializers.py`,
  `features/permissions/**`, hay file ngoài `backend/`.
- Lệch 02c chỉ có hai chỗ, cả hai chấp nhận: bỏ cache (lý do ở mục 1) và L1 bên dưới.

### Lỗi mức Low (không chặn, nên làm ở lô sau hoặc khi gộp nhánh phạm vi)
- **L1** `backend/apps/accounts/auth/services.py:92-98`. `home_for` tự viết `if is_superuser` / `if not groups` thay vì dùng
  `has_erp_access` như §A.2. Hiện tương đương. Cách sửa: `if not has_erp_access(user): return HOME_NO_ROLE` (đổi chữ ký sang nhận
  `user`), để luật cổng và luật `home` không trôi khỏi nhau.
- **L2** `backend/apps/accounts/auth/tests/test_no_role_gate.py`. Thiếu 3 ca §B.4.2 yêu cầu: session auth bị chặn; không nhóm + mật
  khẩu tạm thì ra `AUTH_MUST_CHANGE_PASSWORD`; một `POST` hành động bị 403 và dữ liệu không đổi. Techlead đã thăm dò, cả 3 ca đều đúng.
  Cách sửa: thêm 3 test đó vào file này, nhất là ca thứ tự cờ, vì FE dựa vào nó để đưa người dùng sang màn đặt mật khẩu.
- **L3** `backend/apps/accounts/auth/authentication.py:64-66`. `_is_public_view` chỉ đọc `permission_classes` của lớp. Cách sửa
  (phòng xa): thêm một test khẳng định không view nào dưới `/api/` override `get_permissions`, hoặc ghi rõ giới hạn này trong docstring.
- **L4** `backend/apps/accounts/qa_fixture/build.py:178-183`. `.first()` trả `None` nếu codename sai, và `set([None])` sẽ ném lỗi khó
  đọc. Cách sửa: dùng `Permission.objects.get(...)` để lỗi nêu rõ quyền nào thiếu.

### Việc vận hành (nhắc lại C2 và §B.4.5)
Trước khi deploy production, điều phối viên đếm tài khoản `is_active`, không superuser, không nhóm (chỉ in username). Ngay sau khi
deploy, những người này mất quyền vào ERP.
---

## Lô QĐ-08/10 FE (08/10)

Nhánh `feat/qd-0810-fe` `52a2585`, diff `main...HEAD` (19 file). Thiết kế `02c-quyet-dinh-08-10.md` §A.3, §B.3, §E, §F. Đối chiếu contract
BE thật trên `feat/qd-0810-be` (`auth/authentication.py:41-52`, `auth/api.py` 4 view `allow_without_group`, `auth/services.py:92,136`).
Đã chạy `python3 scripts/check_naming.py`: OK, không phát sinh mới. Không build (điều phối viên chạy tsc/vitest/build).

**Kết luận: CHANGES REQUESTED** (1 Medium, 2 Low phải sửa trong lô; còn lại ghi nhận).

### Đã soát, đạt

1. **Nhánh 403 `AUTH_NO_ROLE` trong `AuthProvider.tsx:138-143` (lệch §B.3): chấp nhận, 02c §B.3 coi như được thay bằng bản này.**
   Nhánh chung không sai hẳn (lần 403 đầu vẫn tải lại `me` → `home=no-role` → ConsoleGate chuyển trang), nhưng nó bỏ qua request đã nằm
   trong `stableForbidden` 60 giây, và hiện thêm thông báo "quyền vừa đổi". Nhánh riêng thì luôn chuyển trang, nên tốt hơn.
   - Không có vòng lặp: BE miễn cổng cho `me` (200), và `loadMe` đã bỏ qua 403. Request đang bay có thể gọi `me` thêm vài lần, nhưng số
     lần có giới hạn. Khi `home=no-role`, ConsoleGate chỉ vẽ Loading và gỡ Shell, nên không còn màn nào gọi API. `NoRoleScreen` không gọi API.
   - Có thể nháy trang trong ca đua: Chủ vừa gán lại nhóm. FE đặt lạc quan `home=no-role`, rồi `me` trả `dashboard`, và `NoRoleScreen:19`
     đưa về `homePath`. Màn tự trở lại đúng, chấp nhận được.
   - Không xung đột với mật khẩu tạm. BE và mock đều kiểm `AUTH_MUST_CHANGE_PASSWORD` trước (`mock.ts:393`). ConsoleGate `:41-42` và
     NoRoleScreen `:19` đều ưu tiên `must_change_password`. Nhánh NO_ROLE không đụng cờ `forcedChange`.
2. **Superuser không nhóm.** `nav.ts` không đổi logic. `my-deliveries` vẫn dùng `inGroup(deliveryStaff)`, nên superuser không thấy mục này.
   `hasLimitedCourierScope` trả false với superuser không nhóm, khớp `resolver.py`. `receiptView.ts:60` đạt nhờ quyền `deletePurchaseReceipt`.
   `AiAssistantPanel:274` đi theo quyền. `roleText` và AccountScreen chỉ hiện nhãn "Quản trị hệ thống" khi không có nhóm, nên không che nhóm
   thật. Vitest `superuser.test.ts` có phủ. Màn Phân quyền vẫn ở chế độ chỉ đọc với superuser không thuộc `owner`
   (`PermissionMatrixScreen.tsx:49`) cho tới khi F1 vào main. Đây là việc của F1, lô này không được đụng `permissions/**`.
3. **Mock.** Đường miễn cổng (token, me, logout, change-password) và câu `detail` (`beErrors.mock.ts:74-78`) khớp nguyên văn BE
   `NO_ROLE_DETAIL`. `setMockGate` nằm trong `if (NEXT_PUBLIC_USE_MOCK === "1")`. `beErrors.mock.ts` và `mock.ts` đã có trong danh sách quét
   của `check-no-mock.mjs`. `nogroup1` dùng SĐT rỗng và tên chung, không có dữ liệu cá nhân.
4. **E2E.** Bốn file đổi `admin` thành `nogroup1` cho ca không nhóm, đúng ý. Ca `admin` mới vào `/overview/` và có kiểm menu. `s48`
   không nới lỏng: vẫn kiểm superuser không bị ép đổi mật khẩu, chỉ đổi trang đích. Các helper `nav_labels` và `logout` đều có sẵn.
5. **Phạm vi.** Không đụng `features/permissions/**`, `backend/` hay `frontend/`. Không thêm log, console, localStorage hay URL chứa dữ liệu
   cá nhân. Không có field giá vốn. Có 3 file nằm ngoài danh sách §G.1 (`AuthProvider.tsx`, `LoginScreen.tsx` chỉ là gợi ý mock,
   `beErrors.mock.ts`) và 1 file test mới. Đều hợp lý, chấp nhận.

### Lỗi

| # | Mức | Chỗ | Lỗi | Cách sửa |
|---|---|---|---|---|
| R1 | Medium | `erp-console/features/audit/auditModel.ts:142` | Thiếu hạng mục §E của lô. `AI_ONLY_ACTIONS` chưa có `"ai_config_kill"`, nên khi tắt AI thì ô lọc Nhật ký vẫn còn "Tắt trợ lý AI" | Thêm `"ai_config_kill"` vào mảng. Thêm một khẳng định vitest nếu đã có test cho `AI_ONLY_ACTIONS` |
| R2 | Low | `erp-console/features/ai/settings/mock.ts:29` | Nhãn nhóm **lệnh AI** đang là "Gọi xác nhận". §F yêu cầu "Chăm sóc khách hàng", khớp BE `ai/settings/services.py:101` | Đổi thành `"Chăm sóc khách hàng"` |
| R3 | Low | `erp-console/features/confirmation/mock.ts:530` | §F yêu cầu chép đúng câu 404 BE. Mock: "Không tìm thấy phiếu trong phạm vi gọi xác nhận của bạn." BE `delivery/confirmation/api.py:128`: "Không tìm thấy mục chờ gọi trong phạm vi của bạn." | Chép nguyên văn câu BE |
| N1 | Low (ghi nhận, nên sửa) | `erp-console/shared/lib/nav.ts:176` `onlyDelivery` | Superuser chỉ thuộc `delivery_staff`: BE trả `home=dashboard` (§A.2). FE vẫn coi là "chỉ giao" và ẩn Đơn, Phiếu giao, Hoá đơn, Nhật ký, AI, nên không "như Chủ" | `onlyDelivery = (me) => !me.is_superuser && me.groups.length > 0 && ...`. Thêm 1 ca vitest. File thuộc danh sách được sửa |
| N2 | Ghi chú QA | `AuthProvider.tsx:138` | Nhánh mới chưa có test nào chạy qua. Các e2e chỉ đăng nhập sẵn bằng `nogroup1`, vì vậy đi đường `me.home` | QA thêm hai ca. Ca 1: đăng nhập `kho1`, gọi `__caveMock.patchUser('kho1',{groups:[]})`, mở `/orders/`, kết quả phải về `/no-role/`, và log mock không có chuỗi `GET /api/auth/me/` lặp vô hạn. Ca 2: `nogroup1` + `must_change_password`, kết quả phải về `/set-password/` |
| N3 | Ghi nhận | `shared/ui/shell/AvatarMenu.tsx:111` | Nhãn vai dài ("Nhân viên gọi xác nhận · Nhân viên giao") đã có ellipsis (`globals.css:130`) nhưng thiếu `title` theo §F | Làm khi có lô đụng `shared/ui/shell`. Không chặn lô này |

R1–R3 sửa xong là đạt. Không cần review lại toàn bộ, techlead chỉ xem 3 dòng. N1 nên sửa cùng lượt.

### Re-review sau ff0c57a (08/10)

Xem hẹp diff `ff0c57a` (7 file). Đã chạy `npx vitest run shared/lib/nav.test.ts features/audit/auditModel.test.ts`: 2 file, xanh.

**Kết luận: APPROVED** (R1–R3 và N1 đã sửa đúng; còn 1 Low ghi nhận, không chặn lô).

- **R1 đạt.** `auditModel.ts:142` đã thêm `"ai_config_kill"` vào `AI_ONLY_ACTIONS`. Có vitest khẳng định.
- **R2 đạt.** `ai/settings/mock.ts:29` đổi thành "Chăm sóc khách hàng", khớp BE.
- **R3 đạt.** `confirmation/mock.ts:530` chép nguyên văn câu BE `delivery/confirmation/api.py:128` ("Không tìm thấy mục chờ gọi trong phạm vi của bạn.").
- **N1 đạt.** `nav.ts:176`: `onlyDelivery` thêm điều kiện `!me.is_superuser`, nên superuser chỉ thuộc `delivery_staff` thấy menu như Chủ.
  - Đã chạy thử để so menu: Chủ có 19 mục, superuser chỉ thuộc `delivery_staff` có 20 mục. Superuser không thiếu mục nào của Chủ. Mục dư duy nhất là
    `my-deliveries` ("Việc giao của tôi"), do `nav.ts:307` hiện mục này theo `inGroup(deliveryStaff)`.
  - Mục dư này **đúng ý**. Superuser đó thật sự thuộc nhóm NV giao, nên có thể được gán làm `courier` trên phiếu, và cần màn xem phiếu của mình.
    Superuser không nhóm thì không có mục này, giống mục 2 của lần review trước.

| # | Mức | Chỗ | Ghi nhận | Cách sửa |
|---|---|---|---|---|
| L1 | Low (không chặn) | `erp-console/shared/lib/nav.test.ts:32` | Test dùng `toBeGreaterThanOrEqual`. Nếu sau này superuser mất một mục của Chủ nhưng lại có thêm một mục khác, test vẫn xanh | Khẳng định chính xác: `expect(menuItems(su).map(i => i.key)).toEqual([...menuItems(OWNER).map(i => i.key)` chèn `"my-deliveries"` đúng vị trí trong NAV`])`. Cách đơn giản hơn: tập key của su bằng tập key của OWNER cộng `"my-deliveries"`. Làm ở lô kế tiếp có đụng `nav.test.ts` |

## Lô PV-QĐ (08/10)

Review diff `main...HEAD` của nhánh `feat/pham-vi-du-lieu` (merge `4ef5aa8` gộp main `f3a543f`, rồi `d11fa2b`), đối chiếu
`02c-quyet-dinh-08-10.md` §B.4, §C.1–C.2, §D, §G.2. Không chạy cả suite (điều phối viên chạy). Đã tự chạy:
- SQLite: `test_no_role_gate`, `test_scope_snapshot`, `test_deliveries_customers_receipts_scope`, `test_refunds_dashboard_scope`: Ran 94, OK.
- `makemigrations --check --dry-run`: No changes detected. `python3 scripts/check_naming.py`: OK, không phát sinh mới.
- Một test thăm dò tạm (đã xoá, không commit) cho `POST /api/sales/orders/search/` với `customer` trong body: kết quả ở mục 1.
- PostgreSQL 16 cục bộ (DB riêng `cangca_tlreview*`), chạy lẻ `ConcurrentSaveRaceTests`: kết quả ở mục 6.

**Kết luận: APPROVED.** Không có lỗi Critical hay High. Có 1 Medium (M1) phải làm khi gộp `fix/postgres-compat`, trước khi báo suite
Postgres xanh. M1 không chặn việc merge lô này vào main. Thêm 3 Low.

### 1. Giải xung đột merge — đạt
- **`capabilities/services.py`**: giữ CAS. `set_group_capabilities` khoá `GroupAccessConfig`, so `version` và trả 409 `GROUP_CHANGED`,
  rồi tăng `row_version` đúng một lần. Giữ `_parse_body`, `_scope_events`, `scope_change_label` của nhánh. Thêm đủ phần của main:
  `_parse_body` lọc theo `registry.visible_capabilities()` nên PUT việc AI khi AI tắt vẫn 400 `INPUT_NOT_ALLOWED`;
  `_capability_events` và `capability_change_label` bỏ cờ `customer_data_widening_confirmed` (lọc `BY_KEY`) trước khi gọi `visible_keys`;
  `has_visible_capability_change` còn nguyên. `next_steps.py` có cả `scope_change_label` và `row_filter` của main. `test_ai_hidden.py`
  đổi sang `put_caps` (vì PUT bắt buộc có `version`) và giữ nguyên mọi khẳng định.
- **`reports/dashboard_api.py`**: KPI và "Đơn gần đây" đi qua `orders_in_scope` (D1), doanh thu đi qua `invoices_in_scope` (D2), phiếu đảo
  chỉ tính phần của hoá đơn trong phạm vi. Giữ `id`, `reason`, `select_related`/`prefetch_related` của 17a. Không trả tên hay SĐT (SR-17).
- **`sales/orders/api.py`**: `POST search/` đi qua `get_queryset`, nên dùng `scope_orders_for` bản D1 của nhánh và `annotate_order_pii_visible`.
  Tìm theo tên/SĐT vẫn cần V2 (`allow_customer_search=can_view_order_customer_info`). `GET ?q=` vẫn chỉ khớp mã đơn và vẫn trả
  `SEARCH_USE_POST`. Phần thêm ngoài 02c, `_customer_filter_outside_scope(request, params)` cho body: **đúng, chấp nhận**. Không có nó thì
  body `customer` là đường vòng của PV-05-AC6 (dò đơn của khách ngoài D7 khi D1 = `all`). `_filters_from_body` đã đổi mọi giá trị sang `str`,
  nên `.strip()` an toàn. Thăm dò bằng test tạm: Quản lý có D7 `assigned_deliveries` gửi `customer` (số nguyên hoặc chuỗi) của khách
  ngoài phạm vi thì nhận 200 `count=0`; gửi `"abc"` hoặc `-1` thì 400; khi D7 là `all` thì `count=1`. Không lọt dữ liệu cá nhân hay phạm vi.
  Thiếu test hồi quy cho nhánh này (L1).
- **Không mất hành vi của main.** `accounts/auth/authentication.py` (cổng `AUTH_NO_ROLE`) và `auth/tests/test_no_role_gate.py` không có
  trong diff. Endpoint mới của nhánh (`permissions-preview`) không khai `allow_without_group` và không phải `AllowAny`, nên vẫn đi qua cổng.
  Search POST 17b, `SEARCH_USE_POST`, giữ khoá `order_status` của W37 (test N2 còn khẳng định), nhãn V2/CSKH của main, AuditLog: không bị đụng.
  `common/api.py` bỏ `has_full_delivery_scope` và `sees_customer_directory`: grep không còn chỗ gọi (chỉ còn test khẳng định các tên này đã bị bỏ).

### 2. Mốc PV-01 — đạt
`snapshot.py` tách thành `_Q4_DIFFS`, `_D3_DIRECT_DIFFS` (comment "Duy duyệt 08/10 D-3") và `_D3_COMBINED_DIFFS`
(comment "Duy duyệt 08/10 D-3 (câu 9)"). `PENDING_DUY_DIFFS = ()`, đổi `D3_USERS`, không sinh lại baseline. Test vẫn chặn: hai mục đầu là Q-4,
các mục D-3 chỉ thu hẹp, và một dòng `+` lạ của `direct_permissions` vẫn không được miễn. **Lập luận về `force_authenticate`: chấp nhận.**
Cổng chặn nằm ở lớp xác thực, và `force_authenticate` bỏ qua lớp này (docstring `authentication.py` ghi rõ). Vì vậy mốc chỉ đo lớp phạm vi,
tức lớp phòng thủ thứ hai. Cổng thật đã có test dùng token thật trên main (`test_no_role_gate.py`).

### 3. Câu 7 — đạt
`delivery/serializers.py`: `_customer_data_hidden` chỉ còn luật `pii_restricted` và quá cửa sổ SR-PII-02, đã bỏ import V2. Logic giờ giống
hệt main, chỉ khác docstring. Ai được D3 cho xem phiếu thì thấy đủ tên, SĐT, địa chỉ khi phiếu còn trong cửa sổ. Tem `/label/` không đổi
(vẫn che SĐT, chờ Duy trả lời Q1). Hai test N2 lật đúng, chi tiết phiếu khẳng định có `phone`. Có thêm ca cửa sổ trên phản hồi `status/`.
Ca này giả lập `is_note_pii_expired` ở serializer, chấp nhận vì phiếu quá cửa sổ của NV giao không mở được bằng đường nào khác.
`sales/customers/permissions.py` không đổi, đúng §C.2.

### 4. C1 — đạt
`refunds/api.py` có `get_queryset` gọi `scope_refunds_for` (D1, gắn `pii_visible`). Dashboard đã nói ở mục 1. Mặc định `all` cho Chủ,
Quản lý, NV kho nên số liệu của họ không đổi. `test_refunds_dashboard_scope` xanh.

### 5. Giá vốn, dữ liệu cá nhân, migration — đạt
Không serializer nào thêm field giá vốn. Dashboard vẫn gắn `landed_unit_cost` theo `view_costprice` như cũ. Không có log hay AuditLog mới
chép dữ liệu cá nhân. Thông điệp `SEARCH_USE_POST` không lặp lại `q`. Nhánh không thêm migration (`0014`/`0015` của phạm vi đã ở main,
`sales/0019` của main giữ nguyên số), `makemigrations --check` sạch.

### 6. Log PostgreSQL (`pvqd_pg.log`, Ran 3523, failures=13, errors=55)
Đã phân loại cả 68 ca:
- **Nhóm 1 (`FOR UPDATE ... nullable side of an outer join`)**: huỷ phiếu nhập (gồm 2 ca mới của nhánh, `ReceiptScopeTests.test_pv06_*`),
  publish lô, claim việc gọi xác nhận.
- **Nhóm 2 (AI trả 502)**: `QaF10UndoRealWhenAiOffTests` (6) và `test_dw19_level_b` (2). Đây là hệ quả của nhóm 1.
- **Nhóm 6a, `test_pv01_ac1`**: đã đọc cả 71 dòng lệch. Mọi dòng `+` đều là `actions.confirmation_claim` hoặc `actions.receipts_cancel`
  với giá trị `EXC:NotSupportedError`, đi cặp với dòng `-` của mã trạng thái cũ. Phần lệch `confirmation_claim` thuộc nhóm 1, không phải
  lỗi phạm vi.
- **Các nhóm còn lại** đều có trong `doc/ops/postgres-compat-08-10.md` của `fix/postgres-compat`: `seed_qa`, `test_qa_lo4_tien`,
  `supplier_crud`, `shop_labels`, cost overflow, và `completion_race_postgres` (2 ca lỗi `admin.logentry`).
- `git merge-tree HEAD fix/postgres-compat`: không xung đột. Thay đổi `can_cancel_receipt` của nhánh không đụng dòng `select_for_update`
  mà bản sửa Postgres sửa.
- **Ngoại lệ: `test_pv10_ac5` (lỗi `content_type` unique) có cùng nguyên nhân với nhóm 7b, nhưng bản sửa ở `fix/postgres-compat` không phủ ca này.**
  Bản sửa 7b chỉ thêm `_fixture_setup` vào riêng lớp `CancelVersusCompleteRaceTests`. Chạy lẻ trên Postgres thì `ConcurrentSaveRaceTests` qua
  (Ran 1, OK). Chạy chung suite, sau một `TransactionTestCase` đã flush, thì lớp này đỏ. Xem M1.
- Ghi chú `03-dev-notes.md` có hai chỗ sai: "3 race `django_content_type` unique" thực ra là 1 ca `content_type` (pv10) cộng 2 ca `admin.logentry`
  (completion race), và pv10 không tự hết khi gộp bản sửa.

### Lỗi

| # | Mức | Chỗ | Lỗi | Cách sửa |
|---|---|---|---|---|
| M1 | Medium (không chặn merge lô này; phải xong trước khi báo suite Postgres xanh sau khi gộp `fix/postgres-compat`) | `backend/apps/accounts/data_scopes/tests/test_query_budget_and_race.py:70-73` | `ConcurrentSaveRaceTests` (`serialized_rollback = True`) thiếu bản sửa 7b. Chạy chung suite thì lỗi `IntegrityError django_content_type_app_label_model_..._uniq` khi nạp bản serialize. Chạy lẻ thì qua | Thêm đúng `_fixture_setup` như `apps/delivery/tests/test_completion_race_postgres.py` của `fix/postgres-compat` (xoá ContentType tạo lại, gọi `super()._fixture_setup()`, rồi `ContentType.objects.clear_cache()`). Nên tách thành một mixin chung trong `apps/common/tests/` để hai lớp đua dùng chung. Làm ngay trong commit gộp `fix/postgres-compat`, rồi chạy lại cả suite trên Postgres |
| L1 | Low | `backend/apps/accounts/data_scopes/tests/test_deliveries_customers_receipts_scope.py` (đặt cạnh `:361`) | `POST search/` với `customer` trong body ngoài D7 chưa có test hồi quy. Hành vi hiện tại đúng (đã thăm dò ở mục 1) | Thêm `test_pv05_ac6_search_body_customer_outside_d7_is_empty`: D7 `assigned_deliveries` cho Quản lý, gửi body `{"customer": <pk>}` dạng số nguyên và dạng chuỗi thì `count == 0`; D7 `all` thì `count == 1` |
| L2 | Low | `test_query_budget_and_race.py:87` | `close_old_connections()` không đóng kết nối của luồng phụ (chưa "cũ"). Postgres báo `database "test_..." is being accessed by other users` khi xoá DB test (đã thấy khi chạy lẻ) | Dùng `connection.close()` trong `finally`, như `test_completion_race_postgres.py:66,82` |
| L3 | Low (nit) | `backend/apps/delivery/serializers.py:11` | Dòng trống thừa giữa hai import tương đối, sót lại sau khi xoá import V2. Khiến diff so với main không rỗng | Xoá dòng trống. Sau đó `delivery/serializers.py` chỉ còn khác main ở docstring |

### Việc trước khi merge vào main / deploy
- Sửa doc `03-dev-notes.md` (phân loại pv10 như mục 6) cùng lúc với M1, hoặc ghi M1 thành nợ ghi tên trong `05-tiep-tuc.md`.
- Nhắc lại §B.4.5: trước khi deploy production, đếm tài khoản `is_active`, không superuser, không nhóm (chỉ in username) và báo Duy.
