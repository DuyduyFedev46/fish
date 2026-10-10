# Thiết kế bổ sung — Quyết định Duy 08/10 (superuser, D-3, phiếu giao, nhãn CSKH, AI trong nhật ký)

> Tech Lead · 2026-10-08 · Nguồn: `doc/decisions.md` mục "2026-10-08 — Trả lời 13 câu chờ Duy", câu hỏi gốc
> `doc/features/2026-10-01-erp-theo-design/06-cho-duy-08-10.md`. Bổ sung cho `02b-tech-design.md` của hồ sơ này, không thay nó.
> Số dòng ghi theo `main` `69cdef7` và nhánh `feat/pham-vi-du-lieu` `e373713`.
>
> Câu 3, 4, 10, 11 không phát sinh code. Câu 5 (đua Huỷ ∥ Giao xong) và câu 12 (đợt 2 giao diện) không thuộc file này.

## 0. Tóm tắt chốt kỹ thuật

| Câu | Chốt | Nhánh làm |
|---|---|---|
| 1 | Superuser (kể cả không nhóm) vào ERP như Chủ: `me.home = "dashboard"` và `me.is_superuser = true`. `groups` vẫn trả nhóm thật | `main`, Lô QĐ |
| 6 (D-3) | **Cổng chung ở lớp xác thực BE**: người không nhóm và không phải superuser bị 403 `AUTH_NO_ROLE` ở mọi API ERP. API công khai (Shop, public, internal) không đổi. FE giữ `/no-role/`, đổi chữ thành báo lỗi không có quyền | `main`, Lô QĐ (đổi so với gợi ý ban đầu, lý do ở §B.1) |
| 6 (hệ quả) | `PENDING_DUY_DIFFS` rỗng. Mục của `direct_permissions` và `warehouse_service` chuyển sang `APPROVED_DIFFS` | `feat/pham-vi-du-lieu`, Lô PV-QĐ |
| 7 | V2 không áp cho phiếu giao. Gỡ phần V2 trong `delivery/serializers.py` của nhánh phạm vi. Nhãn V2 đổi thành "Xem thông tin khách trên đơn, hoá đơn, phiếu hoàn tiền" | gỡ: nhánh phạm vi · nhãn: `main` |
| 9 | Người kiêm NV kho + CSKH: chấp nhận thu hẹp (Duy duyệt 08/10 D-3) | nhánh phạm vi |
| 2 | Tắt AI thì ẩn cả `ai_config_*`, `ai_policy_*`, `downgrade_*` ở một hàm `exclude_ai_audit_rows` | `main`, Lô QĐ |
| 13 | Nhãn vai `customer_service` là "Nhân viên gọi xác nhận". Mã nhóm giữ | `main`, Lô QĐ |

---

## A. Câu 1 — superuser vào ERP như Chủ

### A.1 Hiện trạng (main)
- `backend/apps/accounts/auth/services.py:92` `home_for(groups)`: không nhóm thì `"no-role"`. Superuser không nhóm cũng rơi vào đây.
- `describe_user` (`:103`) trả `permissions = user.get_all_permissions()`. Với superuser, đây là **mọi** quyền.
  Menu FE lọc theo quyền (`erp-console/shared/lib/nav.ts`), nên khi bỏ cổng `home` thì superuser thấy đủ menu.
- Phía BE, superuser đã được coi là Chủ ở các chỗ cần: `resolver.py:109` (phạm vi rộng nhất), `staff/services.py:55`
  `actor_is_owner`, `capabilities/services.py:326`, `ai/actions/api.py:48`, `common/api.py:121,132`. **BE nghiệp vụ không cần đổi.**
- Phía FE, có 3 chỗ cổng: `ConsoleGate.tsx` (`me.home === "no-role"` → `/no-role/`), `nav.ts` `visibleNav`/`canView`/`homePath`.
  Các chỗ kiểm nhóm `owner` trực tiếp: `features/permissions/components/{PermissionMatrixScreen.tsx:49,GroupDetailScreen.tsx:87}`.
  Nhánh F1 (`feat/pham-vi-fe`) **đã thay** hai chỗ này bằng `isGroupWriter(me)` (đọc `me.is_superuser`), nên Lô QĐ **không đụng** `features/permissions/**`.
  `features/purchasing/receiptView.ts:60` không cần sửa vì superuser có `deletePurchaseReceipt`.

### A.2 Contract `GET /api/auth/me/` (authenticated, mọi người đã đăng nhập)
Thêm một khoá. Không đổi khoá cũ.
```json
{ "groups": [], "home": "dashboard", "is_superuser": true, "group_labels": [], "permissions": ["...mọi quyền..."], "...": "..." }
```
- `is_superuser`: `bool(user.is_superuser)`. **Viết đúng dòng như nhánh phạm vi** (`5457c2d`): đặt ngay sau `"must_change_password"`, kèm comment
  `# PV-14 (review 07/10) + Duy 08/10 câu 1: FE phân biệt superuser không nhóm.`. Khi gộp chỉ giữ một dòng.
- `home_for(groups, *, is_superuser=False)`: `is_superuser` thì trả `"dashboard"` trước mọi luật khác (kể cả superuser chỉ thuộc
  `delivery_staff`). Luật không nhóm thì `no-role` dùng chung hàm `has_erp_access` của §B.2, không viết lại điều kiện.
- `groups` và `group_labels` vẫn là nhóm thật, không bịa `owner`. Lý do: màn Nhân viên và Phân quyền đếm thành viên nhóm theo dữ liệu thật,
  và luật "còn ít nhất một Chủ" (`staff/services.py:342`) không được tính superuser là Chủ.

### A.3 FE
| File | Việc |
|---|---|
| `features/auth/types.ts` | `Me.is_superuser?: boolean` |
| `shared/lib/nav.ts` | `Viewer.is_superuser?: boolean`. Logic menu không đổi. `my-deliveries` vẫn chỉ cho thành viên `delivery_staff`, nên superuser không thấy mục này |
| `shared/lib/groups.ts` | Thêm `SUPERUSER_LABEL = "Quản trị hệ thống"` |
| `features/auth/components/ConsoleGate.tsx` `roleText` | Không có nhóm mà `is_superuser` thì hiện `SUPERUSER_LABEL` |
| `features/auth/components/AccountScreen.tsx:53` | Cùng luật: không nhóm mà superuser thì hiện một dòng "Quản trị hệ thống (toàn quyền)" |
| `features/auth/mock.ts` `buildMe` (`:280`) | Superuser → `home: "dashboard"`, thêm `is_superuser`. Sửa comment `:14`. Thêm user mock **`nogroup1`** (id 13, không nhóm, không superuser, `extra_perms: ["sales.view_salesorder", "sales.view_refund"]`) làm ca "không nhóm" thay cho `admin` |

### A.4 Test đổi (lật S6-AC4, S47-AC5; ghi "Duy 08/10 câu 1" trong docstring)
- BE `apps/accounts/auth/tests/test_s6_me.py:93` → `test_s6_ac4_superuser_without_group_goes_to_dashboard`: `home == "dashboard"`,
  `is_superuser is True`, `groups == []`. Test `:87` (người thường không nhóm thì `no-role`) giữ nguyên.
- BE `test_s6_me.py:~50` và `test_s47_me_labels.py:166`: tập khoá thêm `"is_superuser"`.
- BE `apps/accounts/auth/tests/test_s47_me_labels.py:157` → `test_s47_ac5_superuser_without_group_has_dashboard_and_all_capabilities`.
- BE thêm: superuser chỉ thuộc `delivery_staff` thì `home == "dashboard"`.
- e2e mock: `e2e/s7_shell.py:106-116`, `e2e/qa_ed_batch1_roles.py:194`, `e2e/ed_batch15_overview_ai_account.py:637-643` đổi `admin` → `nogroup1`
  cho ca `/no-role/`. Thêm ca `admin` vào thẳng `/overview/`, menu có "Phân quyền" và không có "Việc giao của tôi".
  `e2e/s48_password.py:291` (superuser không bị ép đổi mật khẩu) đổi đích chờ từ `/no-role/` sang `/overview/`.
- vitest `shared/lib/nav.test.ts` không đổi (nó dựng `viewer` bằng tay).

---

## B. Câu 6 (D-3) — người không nhóm không vào được ERP

### B.1 Vì sao chặn ở lớp xác thực BE và làm ngay trên main
- FE đã chặn: `home_for` trả `no-role` cho người không nhóm, rồi `ConsoleGate` đưa về `/no-role/`. Nhưng BE vẫn trả dữ liệu nếu họ gọi API
  bằng token (họ có quyền gán trực tiếp). D-3 đòi chặn thật, nên phải chặn ở BE.
- Chỗ chặn dùng lại đúng mẫu S48 (`apps/accounts/auth/authentication.py`, BR-PQ-19). Lớp xác thực là nơi **mọi** view DRF đều đi qua.
  Permission class mặc định thì không đủ, vì nhiều view tự khai `permission_classes`. Repo cũng không có view nào tự khai
  `authentication_classes` (đã grep).
- A và B cùng đụng `auth/services.py` (`home_for`), `auth/api.py`, `features/auth/**` và các e2e `admin`. Gộp vào một lô trên main thì
  không xung đột. Nhánh phạm vi chỉ còn phần hệ quả (§B.4).

### B.2 BE
`apps/accounts/auth/authentication.py`:
```python
NO_ROLE_CODE = "AUTH_NO_ROLE"
NO_ROLE_DETAIL = "Tài khoản của bạn chưa thuộc nhóm nào nên không có quyền vào hệ thống vận hành. Nhờ Chủ vựa xếp nhóm."

def has_erp_access(user) -> bool:
    """D-3 (Duy 08/10): superuser, hoặc thuộc ít nhất một Group. Quyền gán trực tiếp không tính. Cache trên đối tượng user."""

class NoRole(PermissionDenied):  # 403 {"detail", "code": "AUTH_NO_ROLE"}, render_code = True như MustChangePassword
```
Trong `_EnforcePasswordChangeMixin.authenticate` (nên đổi tên thành `_EnforceAccessMixin`), **sau** kiểm mật khẩu tạm, khi đã có user:
- Miễn chặn nếu view khai `allow_without_group = True`, **hoặc** mọi phần tử của `view.permission_classes` là `AllowAny`.
  Trường hợp thứ hai phủ Shop, `public/*` và internal (internal tự kiểm token dịch vụ, không đi qua DRF auth).
- Còn lại, nếu `not has_erp_access(user)` thì `raise NoRole()`.

`apps/accounts/auth/api.py`: bốn view `LoginTokenView`, `MeView`, `LogoutView`, `ChangePasswordView` thêm `allow_without_group = True`
cạnh `allow_must_change_password`. Người không nhóm vẫn đăng nhập được, đọc được `me` (để FE hiện màn báo lỗi), đổi mật khẩu và đăng xuất được.

`auth/services.py`: `home_for` gọi `has_erp_access`. Import một chiều từ `services` sang `authentication` như `must_change_password`
hiện nay, nên không vòng import.

Ảnh hưởng ngoài ERP:
- **Shop**: khách là guest, `frontend/` không gửi token (đã grep). View Shop đều `AllowAny`, nên không bị cổng chặn kể cả khi có token lạ.
- **Adapter/internal**: `AllowAny` cộng token dịch vụ, không đổi.
- **Django admin** không qua DRF, và chỉ superuser vào được (`accounts/admin.py:32`). Không đổi.
- Tốn thêm **một truy vấn** `groups.exists()` cho mỗi request của người không phải superuser. Có cache trên user. Test ngân sách truy vấn
  của nhánh phạm vi (`test_query_budget_and_race.py`) dùng `force_authenticate` nên không đổi.

Seed QA (`apps/accounts/qa_fixture/build.py:73`): cấp cho `qa_nogroup` hai quyền trực tiếp `sales.view_salesorder` và `sales.view_refund`,
để e2e BE thật bắt được ca "có quyền gán trực tiếp vẫn bị chặn". Nếu bước dựng seed không hỗ trợ quyền trực tiếp thì thêm cột `perms`
vào bộ `USERS` (giữ idempotent).

### B.3 FE
- `features/auth/components/NoRoleScreen.tsx`: tiêu đề "Bạn không có quyền vào hệ thống vận hành". Thân: "Tài khoản **{username}** chưa
  thuộc nhóm nào. Nhờ Chủ vựa xếp bạn vào một nhóm rồi đăng nhập lại." Đổi icon sang `block` (vẫn `aria-hidden`).
  Sửa comment dòng 3 (S47-AC5 đã lật).
- Không cần handler mới. 403 lạ đã có nhánh chung `setForbiddenHandler`: gọi `loadMe(true)`, `me.home` thành `no-role`, rồi `ConsoleGate`
  đưa về `/no-role/` (`AuthProvider.tsx:131-142`). Ca này là người đang mở console thì bị Chủ gỡ hết nhóm.
- Thêm `NO_ROLE_CODE = "AUTH_NO_ROLE"` vào `features/auth/types.ts`.
- `features/auth/mock.ts:385` `setMockGate`: chặn bằng `beError("AUTH_NO_ROLE")` cho user mock không nhóm và không superuser. Dùng
  danh sách đường mở `MUST_CHANGE_ALLOWED`.

### B.4 Hệ quả trên nhánh `feat/pham-vi-du-lieu`
1. **Tệp mốc PV-01** (`apps/accounts/data_scopes/tests/snapshot.py:42-78`). `Collector` dùng `force_authenticate` (`snapshot.py:115`),
   nên lớp xác thực bị bỏ qua và mốc vẫn ghi hành vi lớp phạm vi. Giữ như vậy: phạm vi thu hẹp của người không nhóm là lớp phòng thủ
   thứ hai, phía sau cổng D-3.
   - Chuyển nguyên các mục `direct_permissions` (D6, D7, `refunds.*`, `dashboard.summary` cùng hai mục `+` của dashboard) sang
     `APPROVED_DIFFS`, mỗi dòng ghi comment `# Duy duyệt 08/10 D-3`.
   - Chuyển các mục `warehouse_service` (`confirmation.*`, `actions.confirmation_*`) sang `APPROVED_DIFFS` với comment
     `# Duy duyệt 08/10 D-3 (câu 9)`.
   - `PENDING_DUY_DIFFS = ()`, giữ tên hằng để `is_approved` không đổi chữ ký. Bỏ `PENDING_DUY_USERS`, hoặc đổi thành `D3_USERS`.
   - Không sinh lại `scope_snapshot_baseline.json` (mốc vẫn là hành vi cũ, các lệch nằm ở danh sách được duyệt).
   - `test_scope_snapshot.py`:
     - Sửa docstring `:11-14`.
     - Bỏ khẳng định `:147` ("APPROVED_DIFFS không có direct_permissions") và thêm `assertIn("Duy duyệt 08/10 D-3", source)`.
     - Viết lại `test_pv01_pending_duy_diffs_...` (`:151`) thành `test_pv01_d3_approved_diffs_are_narrowing_only`, giữ nguyên các
       khẳng định "chỉ thu hẹp" nhưng áp cho các mục D-3 trong `APPROVED_DIFFS`, và thêm `assertEqual(PENDING_DUY_DIFFS, ())`.
     - Hai khẳng định `:165-166` (một dòng `+` lạ của `direct_permissions` không được miễn) giữ nguyên.
2. **Test cổng thật** (mới, trên main ở Lô QĐ): `apps/accounts/auth/tests/test_no_role_gate.py`, dùng **token thật** (không dùng
   `force_authenticate`):
   - Người không nhóm có đủ quyền trực tiếp (bộ quyền như `DIRECT_PERMISSIONS` của fixture phạm vi, chép ra, không import chéo) gọi
     `GET /api/sales/orders/`, `/api/sales/refunds/`, `/api/sales/invoices/`, `/api/delivery/notes/`, `/api/dashboard/summary/`,
     `/api/sales/customer-directory/`, `/api/audit-logs/`. Mỗi đường trả 403 `code=AUTH_NO_ROLE`, thân không chứa tên hay SĐT giả.
   - Duyệt mọi `router.registry` của `config/api_urls.py` (GET list): không đường nào trả 200 cho người này.
   - `POST` một hành động (vd huỷ đơn) cũng 403, dữ liệu không đổi.
   - Miễn chặn: `me` (200, `home=no-role`), `logout`, `change-password`, `token`.
   - Công khai không đổi: `GET /api/shop/catalog/` có kèm token của người này vẫn 200. Ẩn danh vẫn 200.
   - Superuser không nhóm: 200. Người thuộc một nhóm: 200. Session auth cũng bị chặn.
   - Ca cả hai cờ: không nhóm mà còn mật khẩu tạm thì trả `AUTH_MUST_CHANGE_PASSWORD` (đứng trước), để FE đưa sang màn đặt mật khẩu.
3. **C1** (D1 cho phiếu hoàn tiền và dashboard) **đã code** ở `5fd4032` (review APPROVED-chờ-Duy). Không phải làm lại, chỉ cần bước 1 để
   gỡ trạng thái chờ. Kiểm lại sau khi gộp main vì `reports/dashboard_api.py` và `sales/refunds/api.py` có xung đột (§G).
4. Sửa doc của nhánh: `02b-tech-design.md` dòng R9 (`:267`) và D-3 (`:315`) ghi "Duy chốt 08/10: chặn hẳn ở cổng xác thực".
   `03-dev-notes.md` ghi dòng "đã gỡ PENDING".
5. **Việc vận hành trước khi deploy production** (không phải code): điều phối viên đếm số tài khoản `is_active`, không superuser, không
   nhóm trên production, chỉ in username. Nếu có người đang làm việc thì báo Duy danh sách để xếp nhóm **trước** khi deploy, vì sau deploy
   họ mất quyền vào ERP ngay.

---

## C. Câu 7 — phiếu giao luôn đủ tên, SĐT, địa chỉ cho người xem được phiếu

### C.1 Chỗ đang che (chỉ có trên nhánh phạm vi, main chưa có)
`feat/pham-vi-du-lieu` `backend/apps/delivery/serializers.py`:
- `:11` import `can_view_order_customer_info`.
- `:56-66` `_customer_data_hidden`: luật 1 "không có V2 thì ẩn" (thêm ở `d861021`, QA W37 N2). Hàm này quyết định `customer_name`,
  `address`, `phone`, `recipient_name`, `failure_note`, `note` (`:69, :75, :155, :165, :249, :254`).

### C.2 Cách gỡ
- Xoá luật 1 và import. `_customer_data_hidden` trở lại một luật: `pii_restricted` (phạm vi D3 khác `all`) **và** phiếu quá cửa sổ
  SR-PII-02. Như vậy ai được D3 cho xem phiếu thì thấy đủ tên, SĐT, địa chỉ khi phiếu còn trong cửa sổ.
- Viết lại docstring: "V2 không áp cho phiếu giao (Duy 08/10 câu 7). Một luật cho danh sách, chi tiết, Việc giao của tôi và phản hồi
  đổi trạng thái (W37 N2)". Phần N2 vẫn đúng: phản hồi `POST .../status/` đi qua cùng serializer và cùng luật.
- `sales/customers/permissions.py:21-22` đã ghi đúng ("V2 chỉ điều khiển ... đơn, hoá đơn bán, phiếu hoàn tiền; ... phiếu giao có luật
  riêng"). Không sửa.
- Test trên nhánh, `apps/accounts/data_scopes/tests/test_deliveries_customers_receipts_scope.py`:
  - `:177` `test_w37_n2_status_response_hides_customer_data_when_v2_is_off` → đổi thành `..._keeps_customer_data_when_v2_is_off`.
    Thu V2 của NV kho, phản hồi `status/` và chi tiết vẫn có `customer_name`, `address`, `phone`.
  - `:207` `test_w37_n2_courier_list_hides_customer_data_without_v2` → `..._keeps_customer_data_without_v2`: NV giao bị thu V2 vẫn thấy
    đủ trên phiếu của mình.
  - Thêm ca N2 cho cửa sổ: NV giao, phiếu đã quá cửa sổ SR-PII-02, phản hồi `status/` có `customer_name` và `address` là `null` (luật
    còn lại vẫn đúng cho phản hồi).
  - `:192` (`..._matches_detail_rule_when_v2_is_on`) giữ.
  - Chạy lại PV-01. Nếu mốc lệch ở `deliveries.*` thì nghĩa là fixture có người thiếu V2 mà vẫn xem phiếu. Lệch đó phải là `+` (thấy lại
    như trước Lô 4) và phải khớp mốc cũ. Mốc chụp trước Lô 4 nên lẽ ra không lệch.

### C.3 Bản in
- Tem (`delivery/labels/services.py:66-69`, `/label/`) đã in đủ tên và địa chỉ người nhận theo quyền "In tem". V2 không dính vào tem.
  Không đổi.
- SĐT trên tem hiện **che** (`recipient_phone_masked`, CS-11-AC5, BR-GH-18). Câu 7 Duy nói "in ra thì đầy đủ". Xem 🔴 Q1. Mặc định đến
  khi Duy trả lời: giữ che SĐT trên tem. NV giao vẫn có SĐT đủ trong app (chi tiết phiếu và Việc giao của tôi).
- Phiếu soạn (`PickSheetScreen`) không có dữ liệu khách. Không đổi.

### C.4 Đổi nhãn V2 (làm trên **main**, Lô QĐ)
"Xem thông tin khách trên đơn & hoá đơn" → **"Xem thông tin khách trên đơn, hoá đơn, phiếu hoàn tiền"**:
- `backend/apps/accounts/capabilities/registry.py:50`, `backend/apps/accounts/auth/services.py:79` (`CAPABILITY_LABELS`),
  `backend/apps/sales/models/orders.py:78` (`Meta.permissions`).
- Migration mới `sales/0019_alter_salesorder_view_order_customer_info_label.py` (`AlterModelOptions`, theo mẫu `0018`). Không đụng
  schema. Nhánh phạm vi không có migration `sales` mới (đã kiểm), nên không trùng số.
- Comment `sales/customers/permissions.py:21` sửa chữ trong ngoặc kép cho khớp.
- Test: `auth/tests/test_s47_me_labels.py:93`, `data_scopes/tests/test_orders_invoices_scope.py:349`.
- FE không chép nhãn này (lấy từ BE). Đã grep `erp-console/features` và `e2e` trên main và F1: không có chuỗi cũ.

---

## D. Câu 9 — người kiêm NV kho + CSKH ở Gọi xác nhận
Code giữ nguyên (nhánh phạm vi `36d9e8a`: `confirmation/scope.py` theo D4 của nhóm). Chỉ chuyển 8 cặp mục `warehouse_service` từ
`PENDING_DUY_DIFFS` sang `APPROVED_DIFFS` kèm `# Duy duyệt 08/10 D-3 (câu 9)`, như §B.4 bước 1. Chủ muốn họ thấy hết thì nới D4 của
nhóm CSKH (`all_pending`) ở màn Phân quyền. Không làm luật riêng cho người kiêm nhiệm.

---

## E. Câu 2 — tắt AI thì Nhật ký ẩn cả dòng cài đặt và chính sách AI

Một chỗ duy nhất: `backend/apps/common/ai_visibility.py:17` `exclude_ai_audit_rows`. Mọi nơi đọc nhật ký đều gọi hàm này:
`accounts/audit/api.py:97` (màn Nhật ký, cả đếm và phân trang), các timeline đơn, thanh toán, hoàn tiền, lô, kiểm kê và
`common/guidance/audit_timeline.py`.
```python
AI_ADMIN_ACTION_PREFIXES = ("ai_config_", "ai_policy_", "downgrade_")
...
return qs.exclude(
    Q(actor_kind="ai")
    | (Q(actor_kind="system") & ~Q(proposal_ref=""))
    | _startswith_any("action", AI_ADMIN_ACTION_PREFIXES)
)
```
- `ai_config_update`, `ai_config_kill` (`ai/settings/services.py:361,423`), `ai_policy_update` (`ai/policy/services.py:266`).
- `downgrade_<lệnh>` (`ai/policy/services.py:248`) là dòng "việc AI xếp lịch bị hạ về đề xuất". Dòng này mang `actor_kind="user"` nên
  hiện vẫn lọt. Nó là việc thuần AI nên ẩn cùng. Đã grep: không có `action` nghiệp vụ nào bắt đầu bằng `downgrade_`.
- **Giữ** dòng nghiệp vụ do người duyệt thực thi có `proposal_ref` (vd huỷ đơn từ đề xuất). Đó là chứng từ nghiệp vụ, không phải AI.
- Chỉ ẩn khi đọc. Không xoá `AuditLog` (bất biến 4). Bật cờ thì hiện lại đủ.
- Sửa docstring của module và hàm (bỏ câu "GIỮ ... `ai_config_*`/`ai_policy_*`").
- Test: `accounts/audit/tests/test_note_redaction_and_ai_hide.py:82-106` chuyển 3 action `ai_*` sang nhóm bị ẩn khi tắt, và thêm
  `downgrade_x`. `common/tests/test_ai_visibility.py` thêm ca cờ tắt ẩn `ai_policy_update`, cờ bật vẫn hiện. Lọc `?action=ai_config_update`
  khi cờ tắt thì trả 0 dòng.
- FE: `features/audit/auditModel.ts:142` `AI_ONLY_ACTIONS` đã ẩn hai action này khỏi ô lọc. Thêm `"ai_config_kill"` cho đủ. Mock
  `features/audit/mock.ts` không mô phỏng cờ AI, nên không sửa.

---

## F. Câu 13 — nhãn vai "CSKH" thành "Nhân viên gọi xác nhận"

Nguồn nhãn vai có hai bản chép đúng nhau: BE `backend/apps/accounts/auth/services.py:39` (`GROUP_LABELS`, dùng cho `me.group_labels` và
`capabilities/services.py:111`) và FE `erp-console/shared/lib/groups.ts:15` (`GROUP_LABEL`). Đổi cả hai. Mã `customer_service` giữ.

Chữ "CSKH" người dùng thấy (đã grep chuỗi trong `backend/apps` và `erp-console/{features,shared,app}`, bỏ comment, docstring, test):

| Chỗ | Đổi thành |
|---|---|
| `backend/apps/accounts/auth/services.py:39` | "Nhân viên gọi xác nhận" |
| `erp-console/shared/lib/groups.ts:15` | "Nhân viên gọi xác nhận" |
| `backend/apps/ai/settings/services.py:101` (nhóm **lệnh AI** `customer_service`, màn Cài đặt AI) | "Chăm sóc khách hàng". Đây là nhóm lệnh, không phải tên vai |
| `erp-console/features/ai/settings/mock.ts:29` | "Chăm sóc khách hàng" (khớp BE) |
| `erp-console/features/confirmation/mock.ts:530` câu lỗi mock "phạm vi CSKH" | chép đúng câu 404 BE đang trả (17b đã bỏ chữ CSKH ở BE) |

Giữ: comment, docstring, tên test, tên người mock "CSKH Thử" (dữ liệu demo, e2e `ed_batch5_confirmation.py:459` dựa vào), `GROUP_HINT`.

Test đổi:
- `backend/apps/accounts/capabilities/tests/test_api_read.py:34`
- `backend/apps/delivery/tests/test_confirmation_role_scope.py:135`
- `erp-console/shared/lib/englishNames.test.ts:22`
- Thêm một khẳng định vào `backend/apps/common/tests/test_standard_names.py:182` (danh sách cấm đã có "CSKH"): mọi giá trị của
  `GROUP_LABELS` không chứa "CSKH".

Chiều rộng: "Nhân viên gọi xác nhận" dài hơn "CSKH". fe-dev kiểm ô vai ở thanh đầu và menu avatar (`roleText`), thẻ nhóm màn Phân quyền
và danh sách Nhân viên ở 360px. Không cuộn ngang. Cắt bằng ellipsis kèm `title` nếu cần.

---

## G. Chia lô

### G.1 Lô QĐ-08/10 — trên `main` (BE ∥ FE). Gồm A + B (cổng) + C.4 (nhãn V2) + E + F

**BE** được sửa:
- `backend/apps/accounts/auth/{authentication,services,api}.py`
- `backend/apps/accounts/auth/tests/{test_s6_me,test_s47_me_labels}.py`, mới `test_no_role_gate.py`
- `backend/apps/accounts/capabilities/registry.py` (chỉ dòng 50), `backend/apps/accounts/capabilities/tests/test_api_read.py`
- `backend/apps/accounts/qa_fixture/build.py`
- `backend/apps/sales/models/orders.py` (chỉ nhãn), mới `backend/apps/sales/migrations/0019_*.py`,
  `backend/apps/sales/customers/permissions.py` (comment)
- `backend/apps/accounts/data_scopes/tests/test_orders_invoices_scope.py:349`
- `backend/apps/common/ai_visibility.py`, `backend/apps/common/tests/{test_ai_visibility,test_standard_names}.py`,
  `backend/apps/accounts/audit/tests/test_note_redaction_and_ai_hide.py`
- `backend/apps/ai/settings/services.py:101`
- `backend/apps/delivery/tests/test_confirmation_role_scope.py:135`

**FE** được sửa:
- `erp-console/features/auth/{types.ts,mock.ts,components/ConsoleGate.tsx,components/NoRoleScreen.tsx,components/AccountScreen.tsx}`
- `erp-console/shared/lib/{groups.ts,nav.ts,englishNames.test.ts}`
- `erp-console/features/audit/auditModel.ts`
- `erp-console/features/ai/settings/mock.ts:29`, `erp-console/features/confirmation/mock.ts:530`
- `erp-console/e2e/{s7_shell,qa_ed_batch1_roles,ed_batch15_overview_ai_account,s48_password}.py`

**Không được đụng**:
- `erp-console/features/permissions/**` (F1 sở hữu)
- `backend/apps/accounts/data_scopes/**` trừ đúng dòng test nhãn ở trên
- `backend/apps/delivery/serializers.py`, `backend/apps/{reports/dashboard_api.py,sales/orders/api.py,sales/refunds/**}`
- `backend/apps/accounts/capabilities/{services,next_steps}.py` (đang xung đột với nhánh phạm vi)
- migration đã có, `doc/decisions.md`, `frontend/`, `adapter/`

**Kiểm chứng**:
- `manage.py test` toàn bộ, chạy tuần tự, phải thấy "Ran … OK". Rủi ro: test cũ dùng **token thật** với user không nhóm sẽ thành 403.
  Sửa bằng cách cho user đó vào nhóm đúng vai, không miễn cổng.
- `makemigrations --check --dry-run` sạch.
- `tsc --noEmit`, `npm run build`, vitest, 4 e2e mock nói trên, `python3 scripts/check_naming.py`.

**Rủi ro bắt buộc**:

| Rủi ro | Cơ chế chặn | Test bắt lỗi |
|---|---|---|
| Rò dữ liệu cá nhân, vượt phân quyền | Cổng D-3 chặn người không nhóm ở mọi API ERP | `test_no_role_gate.py` (quét router, thân 403 không có tên hay SĐT giả) |
| Giá vốn | Superuser vốn đã có `view_costprice`; không đổi serializer | Test hiện có |
| Chứng từ | Không xoá chứng từ. E chỉ lọc khi đọc | Test E ở trên |

### G.2 Lô PV-QĐ — nhánh `feat/pham-vi-du-lieu` (chỉ BE). Gồm B.4 + C.1–C.2 + D, rồi merge vào main cùng F1

Thứ tự:
1. Lô QĐ đã vào main (APPROVED, đã push).
2. Trong worktree `pham-vi`: `git merge main`. Theo `git merge-tree` lúc 08/10, đã có **6 file xung đột**. Lô QĐ thêm khả năng xung đột ở
   `auth/services.py` và `capabilities/tests/test_api_read.py`. Cách giải từng file:

| File | Giải |
|---|---|
| `accounts/auth/tests/test_s6_me.py`, `test_s47_me_labels.py` | Tập khoá = main (`ai_features_enabled`, `is_superuser`). Giữ test superuser của main |
| `accounts/auth/services.py` | Một dòng `is_superuser`. Giữ `home_for` của main, nhãn V2/CSKH của main |
| `accounts/capabilities/services.py`, `next_steps.py` | Giữ CAS/version và phạm vi của nhánh, thêm thay đổi của main (đọc từng hunk) |
| `reports/dashboard_api.py` | Giữ phạm vi D1/D2 (C1) của nhánh, thêm khoá mới của main |
| `sales/orders/api.py` | Giữ lọc `?customer=` theo D7 của nhánh, thêm `POST search/` (17b) của main. Trên main `search/` đã đi qua `scope_orders_for` và `can_view_order_customer_info` (`orders/api.py:158,193`). Khi gộp phải giữ hai lời gọi này, và `scope_orders_for` phải là bản của nhánh (đọc D1) |

   Sau khi gộp: chạy toàn bộ test, `makemigrations --check`, rồi commit merge riêng.
3. Làm B.4 (bước 1, 4), C.1–C.2, D. Chạy toàn bộ test tuần tự cùng PV-01.
4. techlead review diff → QA (có ca: thu V2 của NV giao mà vẫn thấy địa chỉ, người không nhóm bị 403 bằng token thật trên seed QA) →
   merge `feat/pham-vi-du-lieu` vào main.

**Không được đụng**: `erp-console/**`, `accounts/auth/authentication.py` (cổng thuộc main), migration.

**F1 FE (`feat/pham-vi-fe`, chậm main 160)**: sau bước 4, `git merge main`. Theo `merge-tree` có 4 xung đột:
- Hai file doc của hồ sơ: giữ cả hai phía.
- `features/permissions/components/{GroupDetailScreen,PermissionMatrixScreen}.tsx`: giữ `isGroupWriter` của F1, thêm thay đổi giao diện
  của main.

Cập nhật thêm:
- `permissionsModel.ts:67-71`: bỏ nhánh đoán `OWNER_ONLY_PERMS` vì `me.is_superuser` đã có thật. Sửa README `:8`.
- Mock `features/permissions/mockScopes.ts` hoặc registry mock nếu có nhãn V2: dùng nhãn mới.

Kiểm chứng gồm `tsc`, `build`, vitest, `e2e/ed_batch14_permissions.py`. Sau đó review, QA, rồi merge.

### G.3 Lô 6–7 phạm vi còn lại (theo `02b` §6 của nhánh)
- **Lô 6, PV-12 + dọn (BE ∥ FE).**
  - BE: cổng phát hành gồm ảnh chụp sau chuyển đổi, test quét mọi endpoint đọc dữ liệu khách và sàn cứng. Bỏ `scopes` cũ. Phần lớn
    hàm của `common/api.py` đã gỡ sớm ở Lô 4, nên Lô 6 chỉ cần dọn chỗ còn sót.
  - Test quét PV-12 nên dùng token thật như `test_no_role_gate.py`, để quét luôn cả cổng D-3.
  - FE: `features/permissions/**` nối BE thật, bỏ kiểu `GroupScopes`.
- **Lô 7, PV-13 + PV-14 (Should, BE ∥ FE).**
  - BE: `accounts/auth/services.py` (`me` thêm phạm vi của mình).
  - FE: `AccountScreen.tsx`, các màn chi tiết đơn, hoá đơn, phiếu giao, hàng hoàn, phiếu nhập, khách, gọi xác nhận, cùng
    `shared/lib/{personalData,messages}.ts`.
  - Làm **sau** Lô QĐ vì cùng sửa `auth/services.py` và `AccountScreen.tsx`.
  - PV-13 ("báo rõ khi mất quyền giữa chừng") dùng lại nhánh 403 chung đã có. Không đụng ca `AUTH_NO_ROLE`, vì ca đó luôn về `/no-role/`.
  - PV-14 hiện phạm vi theo nhóm. Superuser hiện "Toàn bộ (quản trị hệ thống)".

---

## 🔴 Câu hỏi cho Duy

| # | Câu hỏi | Mặc định nếu chưa trả lời |
|---|---|---|
| Q1 | Tem dán lên thùng hàng hiện in **đủ tên và địa chỉ** nhưng **che SĐT** (`09xx xxx 123`, theo CS-11-AC5). Lý do che là tem dán ngoài thùng, ai cầm thùng cũng đọc được. NV giao vẫn có SĐT đầy đủ trong app. "In ra thì đầy đủ" có nghĩa là in **cả SĐT đầy đủ** lên tem không? | Giữ che SĐT trên tem. Phần còn lại của câu 7 vẫn làm như trên |

Các điểm khác đã tự chốt: nhãn superuser "Quản trị hệ thống", nhóm lệnh AI "Chăm sóc khách hàng", ẩn `downgrade_*` khi tắt AI, và gộp cổng
D-3 vào Lô QĐ trên main.
