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
