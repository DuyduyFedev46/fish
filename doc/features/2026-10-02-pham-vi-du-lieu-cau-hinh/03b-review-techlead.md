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

## Review Lô F1 FE (07/10)

Phạm vi: PV-11, PV-09 phần FE, PV-10 phần FE. Nhánh `feat/pham-vi-fe` @ dd84536 (tách từ 9509453), diff `git diff 9509453..HEAD`,
18 file, chỉ trong `erp-console/features/permissions/**`, `erp-console/e2e/ed_batch14_permissions.py` và `03-dev-notes.md`. Đúng
danh sách file của 02b §6, không đụng `shared/ui/**`, `features/{overview,ai,audit,auth}/**` hay `backend/**`.
Theo yêu cầu điều phối viên, lượt này không build và không chạy lại test. Kết luận dựa trên đọc code, đối chiếu với BE thật ở
base (`accounts/data_scopes/{catalog,services}.py`, `accounts/capabilities/api.py`, `accounts/auth/services.py`, migration nhóm)
và số kiểm chứng fe-dev ghi ở 03-dev-notes.

### Kết luận: **CHANGES REQUESTED**

Không có lỗi Critical hay High. Không rò giá vốn, không rò dữ liệu khách, không vượt quyền, vì BE vẫn là lớp chặn và FE chỉ ẩn
hoặc hiện nút. Phải sửa 3 lỗi Medium trước khi duyệt. M1 nằm ở mock, mà mock chính là contract Lô 5 BE phải khớp. M2 và M3 là
hành vi sai hoặc thiếu so với AC. Các mục Low sửa luôn trong vòng này nếu tiện, không chặn duyệt.

### Đối chiếu mock với luật BE 02b §2.3

| Luật | Mock (`mock.ts`) | Kết quả |
|---|---|---|
| Thứ tự kiểm 1→12, lỗi đầu tiên thắng | `put()` gồm gate → `parseBody` (4–7) → CAS (8) → `checkFinalState` (9, 10) → `impactOf` (11) → áp (12) | Đúng |
| CAS: so `version` trong cùng bước, 409 `GROUP_CHANGED`, không đổi gì | `mock.ts:303-305` | Đúng |
| Không có thay đổi thật thì 200, không sự kiện, không tăng `version`, nhưng vẫn qua bước 8 | `mock.ts:314-340` | Đúng |
| PO-Q1 (bước 10) xét trạng thái **cuối** | `mock.ts:283-285`, áp cho cả PUT lẫn preview | Đúng |
| 400 `CUSTOMER_DATA_WIDENING_UNCONFIRMED` kèm `impact` cùng dạng preview | `mock.ts:311-313` | Đúng |
| §2.5: mở rộng khi cổng mở **và** (rank tăng **hoặc** cổng vừa mở với rank > 0) | `mockScopes.ts:220-224` | Công thức đúng, nhưng đầu vào sai ở D7 (xem M1) |
| Preview: "thân như PUT, không cần `version`/`confirm`" | `mock.ts:216` trả `INPUT_NOT_ALLOWED` khi có `version`, lại nhận `confirm_…` | Lệch nhẹ (L1) |
| Bước 1 (403) đứng trước bước 2 (404) | `mock.ts:371` trả 404 nhóm lạ trước khi gọi `gate()` | Lệch nhẹ (L2) |

### Lỗi phải sửa

**M1 (Medium, contract Lô 5): mock tính "tầm với" D7 sai so với resolver BE (luật H1 06/10) và GET thật của Lô 2.**
`erp-console/features/permissions/mockScopes.ts:182-184` coi D7 chỉ đủ điều kiện khi `view_customers` bật, hoặc nhóm là NV giao.
`mockScopes.ts:245-246` lấy rank theo giá trị **đã lưu**. BE thật (`catalog.py` `CUSTOMERS.gate_perms` + `full_perm`/`capped_value`)
thì khác ở hai điểm:
- Nhóm có `sales.view_customer` (Tầng 1, ngoài registry) luôn đủ điều kiện. Theo migration `0002` và `0012`, đó là **Quản lý**
  và **NV giao**. Vì vậy GET thật của Quản lý khi tắt "Xem khách hàng" trả `inactive_reason: null` (ô không mờ), còn mock lại làm mờ.
- Nhóm thiếu `sales.view_customer_list` bị chặn trần ở `assigned_deliveries` (rank 1).

Hậu quả: với NV giao đang lưu D7 = `all` và "Xem khách hàng" tắt, bật việc này lên **là mở rộng** (rank hiệu lực đi từ 1 lên 2),
nhưng mock trả không mở rộng nên không đòi xác nhận. Ngược lại, khi Chủ đổi D7 của NV giao từ `assigned_deliveries` sang `all`
lúc việc còn tắt, mock đòi xác nhận dù rank hiệu lực không đổi. Nếu Lô 5 BE chép đúng mock thì lỗ R1 mở ra.
Sửa:
- (a) Trong `isEligible`, cho `customers` đủ điều kiện khi `view_customers` bật **hoặc** nhóm thuộc `[manager, delivery_staff]`
  (danh sách chép cứng từ migration, giống `HAS_INVOICE_VIEW`).
- (b) Rank của D7 trong `buildPreview` = `min(rank đã lưu, 1)` khi `view_customers` tắt. Áp cho cả `already_wider_elsewhere`.
- (c) Thêm vitest cho hai ca trên, cộng một ca Quản lý tắt rồi bật lại "Xem khách hàng" khi D7 = `all`, ca này phải mở rộng.

Tech Lead đã ghi thêm vào 02b §2.5 câu "rank = rank **hiệu lực** sau §1.3, gồm trần D7", để Lô 5 BE bám theo.

**M2 (Medium): nút "Hoàn tác" ở W3h hỏng khi việc hoàn tác là mở rộng, và không trả lại phạm vi đã tự đặt.**
`useCapabilityToggle.ts:76-85` gửi `{version, capabilities: undo}` mà không có xác nhận và không có `scopes`.
- Ví dụ: tắt "Xem đơn" của Quản lý rồi bấm Hoàn tác, tức bật lại "Xem đơn" trên nhóm đang lưu D1 = `all`. Theo §2.5 đây là mở
  rộng, nên BE (và cả mock) trả 400 `CUSTOMER_DATA_WIDENING_UNCONFIRMED`. Nhánh `catch` chỉ hiện toast lỗi, không mở hộp cảnh báo.
  Người dùng chỉ đọc được câu lỗi, không hoàn tác được.
- Ví dụ: bật "Xem khách hàng" khi D7 = `none` thì FE gửi kèm `scopes.customers = "all"`. Hoàn tác chỉ tắt việc nên D7 vẫn là
  `all`, không về như cũ.

Sửa: cho Hoàn tác đi qua cùng đường `send` bằng một `TogglePlan` đảo ngược, để 400 có `impact` mở `pendingWiden` như lần bấm
thường. Với hoàn tác của ca PO-Q1, gửi kèm `scopes.customers = "none"`. Thêm e2e: tắt "Xem đơn" của Quản lý, Hoàn tác, thấy hộp
cảnh báo, bấm "Tôi hiểu, lưu", ô bật lại.

**M3 (Medium, PV-11-AC5): chuyển trang trong app khi còn bản nháp thì mất nháp mà không hỏi.**
AC5 ghi "rời trang → hỏi xác nhận". `useGroupDraft.ts:55-64` mới chặn đóng tab và tải lại (`beforeunload`). Bấm "← Phân quyền",
bấm mục sidebar hay tên nhân viên trong bảng Thành viên thì bản nháp mất ngay. Chuỗi `M.draftLeave` (`messages.ts:96`) đã viết
sẵn mà chưa được dùng. Sửa trong `features/permissions/` (không đụng `shared/ui/**`):
- Khi `size > 0`, gắn listener `click` ở pha capture trên `document`. Bắt `<a href>` cùng origin, khác trang hiện tại, không có
  phím bổ trợ (ctrl, meta, shift, nút giữa). Gặp thì `preventDefault`, hỏi `window.confirm(M.draftLeave)`, đồng ý mới
  `router.push(href)`.
- Nút Back của trình duyệt (`popstate`) chấp nhận chưa chặn. Ghi vào 03-dev-notes để QA biết.
- Thêm e2e: đổi một ô, bấm "← Phân quyền", thấy hộp hỏi; huỷ thì vẫn ở trang và nháp còn; đồng ý thì sang trang.

### Low (không chặn duyệt)

- **L1:** `mock.ts:216`: preview chốt nhận cả 4 khoá như PUT, **bỏ qua** `version` và `confirm_customer_data_widening`. Khoá lạ
  khác thì 400 `INPUT_NOT_ALLOWED`. Mock phải nhận `version`. Đã ghi vào 02b §2.4.
- **L2:** `mock.ts:371`: với người không phải Chủ hay superuser, PUT hoặc POST vào nhóm lạ phải trả 403 trước (bước 1). Hiện mock
  trả 404 trước. GET nhóm lạ thì giữ 404.
- **L3:** đổi base ngầm. Sau khi thêm hoặc bỏ thành viên, `detail.reload()` (`GroupDetailScreen.tsx:109-113`) nạp `version` mới
  trong lúc bản nháp còn giữ. Lần Lưu sau gửi `version` mới (`useGroupDraft.ts:95`), nên thay đổi của người khác chen vào giữa
  không gây 409. Sửa: nếu `version` đổi khi `size > 0` thì đặt `conflict = true`, hoặc khoá thêm/bỏ người khi còn nháp.
- **L4:** chuỗi hiển thị viết cứng trong component: "Chưa lưu" (`GroupDetailScreen.tsx:394`, `:499`) và "Một phần" (`:478`, có từ
  trước). Đưa vào `messages.ts`. `M.scopeReadOnlyHint` (`messages.ts:81`) không có chỗ dùng nên xoá.
- **L5:** e2e `ed_batch14_permissions.py:492` gọi `ok("PV-11-AC2: gate_capability null …", True)` mà phía trước không có `expect`.
  Đây là điểm đếm khống, vì ca thật nằm ở dòng AC7 ngay sau. Gộp vào dòng đó hoặc xoá. Các `ok(..., True)` khác đều đứng sau một
  `expect`, chấp nhận.
- **L6 (UI-RULES §5.3, §1.1):** lý do ô mờ (`inactive_reason`) đang nằm **dưới** ô chọn (`.scopeNote`, cột 2). Luật yêu cầu "lý do
  ngắn nằm cạnh". Ở 1280 px, đặt lý do thành cột thứ ba của `.scopeItem` (nhãn | ô chọn | lý do). Ở 360 px giữ xếp dọc. Để UI
  review quyết nếu thấy cần.
- **L7 (Lô 5 BE, ghi để không quên):** câu `message` của preview phải viết "số điện thoại", không viết "SĐT" (UI-RULES §3.2; mock
  `mockScopes.ts:262-263` và ví dụ trong story đang dùng "SĐT"). Nhãn D4 trong `catalog.py` đang hiện nguyên chữ "trong N ngày"
  lên màn. Lô 5 thay `N` bằng số ngày lấy từ setting của cửa sổ gọi xác nhận. Mock chép lại cho khớp.
- **L8 (Lô 3/5):** mock chưa có V1 (`view_sales_invoices`, D2 lấy rank theo D1) và V2 (`view_order_customer_info`) trong phép tính
  mở rộng §2.5. Thêm khi registry có hai việc này (Lô 3). FE không cần đổi gì, vì hộp cảnh báo dựa vào `widened`/`impact` của BE.
- **L9 (contract Lô 5):** W3i luôn gửi `confirm_customer_data_widening: true` khi người dùng bấm xác nhận ở hộp, kể cả hộp chỉ có
  ghi chú thu hẹp (`useGroupDraft.ts` `confirmSave` → `commit(true)`). BE Lô 5 phải **chấp nhận** cờ này khi không có mở rộng, và
  không ghi `customer_data_widening_confirmed` vào AuditLog trong trường hợp đó.

### Câu hỏi của điều phối viên

**1. `isGroupWriter` suy superuser từ 5 quyền chỉ-Chủ.** Chấp nhận **tạm** tới Lô 6. Lý do:
- Đây chỉ là gợi ý giao diện. Chặn thật nằm ở `actor_is_owner` phía BE.
- Nếu suy sai theo hướng mở, tức một người có đủ 5 quyền gán trực tiếp mà không ở nhóm Chủ, người đó chỉ thấy công tắc rồi nhận
  403 với câu BE. Không lộ dữ liệu, không ghi được gì.
- Nếu suy sai theo hướng đóng thì không xảy ra: superuser có mọi permission, và cả 5 codename đã có thật (`ai.manage_ai_policy`,
  `accounts.manage_staff`, `inventory.close_batch`, `sales.confirm_refund`, `sales.confirm_payment_manual`).

Không đợi Lô 7. Thêm `is_superuser` vào `/api/auth/me/` ở **Lô 5 BE** (cùng chỗ sửa ở mục 2), rồi ở **Lô 6 FE** bỏ phép suy và
chỉ dùng `me.groups.includes(owner) || me.is_superuser`.

**2. Superuser không nhóm bị đưa về `/no-role/`.** Gốc nằm ở BE chứ không ở `AuthGate`: `accounts/auth/services.py::home_for(groups)`
trả `no-role` khi không có nhóm. `ConsoleGate.tsx:41,57`, `NoRoleScreen.tsx` và `shared/lib/nav.ts:514,539,549` chỉ đọc `me.home`.
Sửa:
- **Lô 5 BE.** Thêm `backend/apps/accounts/auth/services.py` vào danh sách file của Lô 5. `home_for` nhận thêm `is_superuser`:
  superuser không nhóm → `dashboard`. `describe_user` thêm khoá `is_superuser`. Có test cho `/me/` của superuser không nhóm. Lô 7
  sau đó chỉ thêm `data_scopes` vào cùng file.
- **Lô 6 FE.** `features/auth/types.ts` thêm `is_superuser?: boolean` vào kiểu Me (cả kiểu ở `shared/lib/nav.ts:14`).
  `features/auth/mock.ts:277` cho `admin` có `home: "dashboard"`. `permissionsModel.isGroupWriter` bỏ phép suy. e2e đổi từ `sa1`
  sang `admin`.
- **Điểm dừng 🟡 hỏi Duy.** Việc này đổi AC đã nghiệm thu: S6-AC4 và S47-AC5 ghi rõ superuser không nhóm vào `/no-role/`. Quyết
  định 06/10 mới nói superuser *được ghi* phân quyền, chưa nói superuser không nhóm *được vào* console. Đề xuất: Duy đồng ý đổi
  S6-AC4, vì superuser là tài khoản của Duy và Lộc, và menu vẫn hiện theo quyền (superuser có đủ quyền). Nếu Duy không đồng ý thì
  giữ nguyên, và superuser muốn ghi phân quyền phải thuộc ít nhất một nhóm.

**3. Dữ liệu cá nhân trong storage và URL, mock lọt vào bản build thật.** Đạt.
- Bản nháp chỉ nằm trong React state (`useGroupDraft`). Không `localStorage`, không query string. URL chỉ có `?group=<mã nhóm>`.
- Kho tạm của mock (`sessionStorage`, khoá `cave_erp_mock_group_*`) chỉ chứa mã việc, mã đối tượng, mã giá trị, số phiên bản và
  tên đăng nhập nhân viên mock. Không có dữ liệu khách.
- Preview và hộp cảnh báo chỉ hiện tên **nhân viên** (`affected_members`, `already_wider_elsewhere`). Không có `console.*` mới,
  không log body.
- `api.ts` gọi mock qua `process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockPermissionsApi : undefined`, cùng cách các module khác.
  Khối `window.__caveMock` trong `mock.ts:95` cũng bọc trong cùng điều kiện. `mockScopes.ts` chỉ được `mock.ts` và test import.
  fe-dev ghi `check-no-mock.mjs` XANH với `NEXT_PUBLIC_USE_MOCK=0`. QA chạy lại ở vòng sau.
- Lưu ý thêm, không phải lỗi: `check-no-mock.mjs` chỉ quét khoá storage dạng `cangcaloc_*`, nên khoá `cave_erp_mock_*` không được
  quét. Hiện tree-shaking đã đủ chặn. Nếu muốn chắc thì thêm mẫu này vào script ở lô có quyền sửa `erp-console/scripts/`.

**4. UI-RULES, bản nháp, `beforeunload`, chuyển trang trong app.**
- Đạt: một PUT cho cả bản nháp; chỉ gửi khoá đã đổi (`cleanDraft`); nút Lưu có trạng thái loading và chặn bấm đúp (`inFlight`);
  nhãn "Thử lại" sau khi lỗi; Esc hoặc Huỷ ở hộp xác nhận không gửi PUT; chip "Chưa lưu" đánh dấu ô đã đổi; vùng bấm ≥ 44px và
  360px không cuộn ngang (e2e); `select` có nhãn và `aria-describedby` trỏ tới lý do; token CSS đều có trong `tokens.css`; không
  mã luật hay thuật ngữ cấm trên màn, trừ L7 đến từ BE.
- `beforeunload`: đúng.
- Chuyển trang trong app: **cần chặn** (M3), vì AC5 ghi rõ "rời trang". Nút Back của trình duyệt chấp nhận để sau.
- Lệch UI-RULES nhỏ: L4, L6.

**5. Không deploy FE này trước Lô 5. Cách giữ an toàn.**
Đã kiểm trên BE thật ở base: `accounts/capabilities/api.py:40` trả 400 `INPUT_NOT_ALLOWED` với mọi khoá ngoài `capabilities`.
FE mới luôn gửi `version`, nên nếu ERP này lên trước Lô 5 thì **mọi** lần bật/tắt ở W3h và mọi lần Lưu ở W3i đều hỏng. Preview
còn trả 404. Lỗi đóng chứ không mở, nên không rò gì, nhưng Chủ mất khả năng sửa phân quyền. Chiều ngược lại cũng hỏng (R11): BE
Lô 5 lên với ERP cũ thì PUT không có `version` bị 400. Đề xuất:
- **Phương án A (chọn): giữ nhánh, không gộp main tới khi Lô 5 BE đã gộp.** Sau mỗi lô BE gộp main thì rebase `feat/pham-vi-fe`.
  Thứ tự gộp: Lô 5 BE → F1 (vòng sửa này) → Lô 6. Triển khai **một lượt** gồm BE Lô 4 + Lô 5 và ERP F1 (+ Lô 6 nếu kịp), đúng nợ M2
  của review 06/10. Điều phối viên ghi vào 02c, ở dòng Lô 5 và F1: "ERP chứa F1 chỉ deploy cùng hoặc sau BE Lô 5, staging trước".
- **Phương án B (chỉ khi buộc phải gộp sớm, ví dụ để tránh xung đột với đợt sửa giao diện):** thêm cờ build
  `NEXT_PUBLIC_GROUP_CONFIG_WRITE`. Thiếu hoặc khác `"1"` thì `isGroupWriter` trả `false` cho mọi người, nên W3h và W3i thành chỉ
  xem, khối phạm vi vẫn hiện (GET đã có từ Lô 2). Không giữ lại đường PUT cũ, để tránh code chết. Giá phải trả: từ lúc ERP lên tới
  khi Lô 5 lên, Chủ **không sửa được** phân quyền, nên phải hỏi Duy trước. Bật cờ trong lệnh build cùng lượt deploy BE Lô 5
  (`doc/ops/moi-truong.md`, truyền trực tiếp `NEXT_PUBLIC_*`). Bỏ cờ ở Lô 6.

### Việc giao lại fe-dev (vòng sửa F1)

1. M1 (a)(b)(c) trong `mockScopes.ts` + `mock.test.ts`.
2. M2 trong `useCapabilityToggle.ts` + e2e Hoàn tác mở rộng.
3. M3 trong `useGroupDraft.ts` (hoặc một hook mới trong `features/permissions/`) + e2e.
4. L1, L2 (mock), L3, L4, L5 nếu kịp. Không làm L6 khi UI review chưa quyết.
5. Kiểm chứng: `tsc --noEmit`, `vitest run`, build `NEXT_PUBLIC_USE_MOCK=0` + `check-no-mock.mjs` + `check-ai-chunks.mjs`, build mock +
   `ed_batch14_permissions.py`, `python3 scripts/check_naming.py`. Không đụng file ngoài danh sách F1.

### Re-review sau a1b5b31 (07/10)

Lượt này đọc `git show a1b5b31` (9 file, chỉ trong danh sách F1 + 03-dev-notes). Theo yêu cầu, không build và không chạy lại test.
Số kiểm chứng lấy từ báo cáo của fe-dev: vitest 1026 PASS, `ed_batch14` 157/157, build mock=0 + 2 check XANH. QA sẽ chạy lại.

#### Kết luận: **APPROVED**

| Mục | Kết quả |
|---|---|
| M1 | **Đạt, khớp 02b §2.5 bản 07/10.** `mockScopes.ts` thêm `HAS_CUSTOMER_VIEW = [manager, delivery_staff]`. Hai nhóm này luôn đủ điều kiện D7, nên GET mock của Quản lý tắt "Xem khách hàng" trả `inactive_reason: null`, giống BE Lô 2. `effectiveRank` chặn trần D7 ở `assigned_deliveries` khi việc tắt. Hàm này dùng cho cả `reachBefore`/`reachAfter`, `narrowed` và `already_wider_elsewhere`. Đã thử tay các ca: NV giao đổi D7 `assigned_deliveries` → `all` khi việc tắt thì rank 1 → 1, không mở rộng, không thu hẹp. NV giao lưu `all` rồi bật việc thì 1 → 2, là mở rộng. Quản lý tắt rồi bật lại khi D7 = `all` cũng 1 → 2, là mở rộng. NV kho (không có `view_customer`) bật việc khi D7 = `none` thì PO-Q1 đặt `all`, cổng vừa mở với rank 2, là mở rộng. Cả 4 ca có test trong `mock.test.ts`. Lô 5 BE dùng đúng các ca này làm test đối chiếu. |
| M2 | **Đạt.** "Hoàn tác" dựng `SendPlan` đảo ngược rồi đi qua `send` (`sendRef`), nên 400 có `impact` mở `pendingWiden`. `saved()` với `isUndo` chỉ báo "Đã hoàn tác", không lồng thêm một nút Hoàn tác. Ca PO-Q1 hoàn tác có kèm `scopes.customers = "none"`. Có e2e tắt "Xem đơn" của Quản lý → Hoàn tác → hộp cảnh báo → "Tôi hiểu, lưu". |
| M3 | **Đạt cho phạm vi đã yêu cầu.** Listener `click` ở pha capture bắt `<a href>` cùng origin, khác trang hiện tại, bỏ qua phím bổ trợ, `target` khác `_self` và `download`; gỡ listener khi hết nháp. Có e2e cho cả Huỷ (ở lại, nháp còn) lẫn Đồng ý. |
| L1, L2 | Đạt (`mock.ts:216`, `:371-372`), có test. |
| L3 | Đạt. `baseVersion` lấy theo lúc nháp còn rỗng. `version` đổi khi đang có nháp thì đặt `conflict`. Khi tự Lưu, `onSaved` và `setDraft(EMPTY)` chạy sau `await`, React 18 gộp chung một lần render, nên lần Lưu của chính mình không bị báo xung đột nhầm. |
| L4, L5 | Đạt. |

#### Còn mở, không chặn duyệt (làm ở Lô 6, vì Lô 6 FE cũng sửa `features/permissions/**`)

- **L10 (M3 còn sót):** trong bảng Thành viên, chỉ ô đầu của mỗi dòng là `<Link>`. Bấm ô khác (tên đăng nhập, nhóm khác, trạng
  thái) thì `DataTable.onRowClick` gọi thẳng `router.push` (`shared/ui/list/DataTable.tsx:144-149`), không đi qua listener, nên mất
  nháp mà không hỏi. ⌘K (`CommandSearch.tsx:76`) và nút Back của trình duyệt cũng chưa chặn. Sửa trong `features/permissions/`:
  listener capture bắt thêm click trong `tr.lt-click`, trừ khi click vào a, button hay ô nhập, rồi lấy `href` từ `a.lt-link` của dòng
  đó. ⌘K và Back chấp nhận để sau. QA ghi nhận là hạn chế đã biết.
- **L11 (contract Lô 5):** khi cổng vừa mở, mục `widened` mang `from`/`to` là giá trị **đã lưu**, nên có ca `{"key": "customers",
  "from": "all", "to": "all"}`. FE chỉ dùng `key` nên không sao. Lô 5 BE trả đúng như vậy (giá trị lưu, không phải giá trị hiệu lực)
  để giữ khớp với mock.
- Vẫn còn: L6 (chờ UI review quyết), L7–L9 (Lô 3/5), câu hỏi superuser không nhóm (điểm dừng 🟡 hỏi Duy), quy tắc deploy theo
  phương án A ở mục trên (không gộp main hay deploy F1 trước Lô 5 BE).
