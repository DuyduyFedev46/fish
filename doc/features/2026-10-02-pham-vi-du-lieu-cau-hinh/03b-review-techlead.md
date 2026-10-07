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
