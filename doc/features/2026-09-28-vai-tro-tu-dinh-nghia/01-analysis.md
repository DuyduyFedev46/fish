# Vai trò tự định nghĩa (Chủ tự tạo vai, tự chọn quyền tính năng, một người kiêm nhiều vai) — Phân tích nghiệp vụ
> BA · 2026-09-28 · Trạng thái: **CHỜ DUYỆT**
>
> **Đụng quyết định đã chốt.** decisions.md 2026-09-10 "Phân quyền 3 tầng…" mục 2 chốt **bốn Group cố định**,
> và spec §13 E-17 ghi "gán nhiều Group, **không tạo role mới**". Yêu cầu này lật một phần mục đó: cơ chế 3 tầng,
> cộng dồn và ranh giới Chủ ↔ Quản lý được giữ, còn danh sách vai thì không cố định nữa. BA không sửa
> `decisions.md`. Duy tự ghi quyết định sau khi trả lời các câu 🔴 ở §10.

## 1. Yêu cầu gốc

> "việc phân quyền trên tính năng cũng do con người tự define, giống tự tạo profile vậy đó, có thể 1 user nhưng
> kiêm nhiệm, trong case này em chia ra nhưng case khác anh có thể yêu cầu gộp lại"

Nguồn: Duy (PO), 2026-09-28. Bối cảnh cùng ngày (hồ sơ `2026-09-28-ai-digital-worker`, dòng M-scope): Duy chọn
"Tách 2 hồ sơ mới". Hồ sơ này là một trong hai. Hồ sơ kia là luồng CSKH (gọi khách xác nhận địa chỉ, in tem, lấy
hàng). Nền của yêu cầu là việc đang chia hệ thống thành ba mảng **Thu mua · Bán hàng · CSKH** (research
`01-mcp-per-function.md` §8).

## 2. Tóm tắt

**Chủ** cần **tự tạo vai trò, tự chọn vai đó được làm những tính năng nào, rồi gán một hoặc nhiều vai cho mỗi
nhân viên**, để **tổ chức người theo cách vựa đang chạy** (tách Thu mua / Bán hàng / CSKH, hoặc gộp khi ít người)
mà không phải nhờ dev sửa code hay migration mỗi lần đổi. Ba giới hạn đi kèm:
1. Chủ **chọn theo tính năng**, không tick từng permission Django.
2. Có một **sàn cứng**: một số quyền không vai tự tạo nào được chứa, và một số luật tách người trên cùng chứng từ
   không cấu hình nào tắt được.
3. **Không thay đổi quyền của ai** tại thời điểm chuyển đổi. Bốn Group hiện có trở thành bốn vai sẵn có, quyền giữ
   nguyên.

## 3. Bối cảnh trong hệ thống

- **Quy trình**: §1 Phân quyền (không phải P-0x). Gián tiếp đụng mọi P-0x vì mọi thao tác đều kiểm quyền.
- **Rule hiện có**: BR-PQ-01…13 (spec §1.9–1.11). BR-PQ-14…19 có trong code và dev notes
  (`2026-09-24-erp-console-noi-that/03-dev-notes.md`) nhưng **chưa vào spec** (dev notes dòng 501 đã nhắc). Liên quan
  thêm BR-KK-02 (người nhập ≠ người duyệt kiểm kê), BR-HV-02 (NV không tự nhập lại hàng hoàn), BR-GH-08 (còn
  phiếu Đang giao thì không cho nghỉ), bất biến 1 (giá vốn) và bất biến 9 (dữ liệu cá nhân).
- **Quyết định ràng buộc**:
  - decisions 2026-09-10 "Phân quyền 3 tầng": ba tầng (giữ), Group cộng dồn không bậc thang (giữ), **bốn Group cố
    định (lật một phần)**, ranh giới Chủ ↔ Quản lý (giữ, xem §6 sàn cứng), SalesOrder/SalesInvoice không ai tạo
    tay (giữ), AuditLog cho mọi hành động Tầng 2 (giữ). Chính quyết định này ghi "Mặc định Quản lý không xem giá
    vốn (PA, rẻ để lật)". Tức là một phần ranh giới vốn đã được coi là cấu hình.
  - decisions 2026-09-10 (mặc định PA): kiểm kê người nhập ≠ người duyệt.
  - Hồ sơ `2026-09-28-ai-digital-worker` §4.2 và sàn H1: **quyền AI = quyền hiện hành của người ∩ cấu hình AI**,
    kiểm tại lúc thực thi. Vai tự định nghĩa vì vậy trở thành **trần quyền của AI** (xem §7.5).

### 3.1 Hiện trạng code (kiểm tra 2026-09-28)

Tầng 1 và Tầng 2 đã gắn theo **permission** nên đổi được mà không sửa code. **Tầng 3, menu và các luật tài khoản
thì đang gắn theo tên Group.** Đây là phần phải gỡ trước tiên.

| Chỗ | Đang gắn theo | Nguồn | Hệ quả khi có vai tự tạo |
|---|---|---|---|
| Ma trận Tầng 1 + Tầng 2 | Data migration gán permission cho 4 Group có tên cố định | `accounts/migrations/0002`, `0003`, `0006`, `0007` | Mỗi quyền mới sau này đang được gán theo **tên** Group. Vai tự tạo sẽ không bao giờ nhận quyền mới, trừ khi có luật (BR-PQ-28). |
| Phạm vi dòng Tầng 3 (đơn, khách, phiếu giao) | `FULL_SCOPE_GROUPS = {"chu","quan_ly","nv_kho"}`: thuộc một trong ba nhóm thì thấy hết, còn lại chỉ thấy theo phiếu giao được gán | `common/api.py::has_full_delivery_scope`; dùng ở `sales/customers/api.py`, `sales/orders/api.py`, `delivery/api.py` | Vai tự tạo (vd "CSKH") có `view_customer` sẽ **không thấy khách nào**. Lỗi này an toàn (đóng) nhưng làm tính năng hỏng. Nếu sửa vội bằng cách thêm tên vai vào danh sách thì phạm vi mở toang (§8 R2). |
| Phạm vi cột Tầng 3 (giá vốn) | `user.has_perm("inventory.view_costprice")` | `common/api.py::CostFieldSerializerMixin`, `reports/dashboard_api.py` | **Không phụ thuộc tên Group.** Vẫn đúng nếu `view_costprice` không lọt vào vai tự tạo. |
| Trang mặc định sau đăng nhập | `home_for`: chỉ thuộc `nv_giao` thì vào "Việc giao của tôi" | `accounts/auth/services.py` | Vai giao hàng tự tạo sẽ bị đưa về Tổng quan hoặc "không có vai". |
| Nhãn vai, thứ tự vai | `ROLE_ORDER`, `GROUP_LABELS` cố định 4 mã | `accounts/auth/services.py`; FE `shared/lib/groups.ts` (`GROUP_LABEL`, `GROUP_HINT`) | Vai mới hiện mã thô. Nhãn và mô tả phải lấy từ dữ liệu. |
| Menu console | Đa số theo permission. Riêng `onlyDelivery` và "Việc giao của tôi" (`inGroup(nvGiao)`) theo tên nhóm | `erp-console/shared/lib/nav.ts` | Phải đổi sang theo quyền tính năng. |
| Luật tài khoản Chủ | BR-PQ-17 và BR-PQ-18 tính "là Chủ" theo Group `chu` | `accounts/staff/services.py` | Giữ nguyên: `chu` vẫn là vai hệ thống, có mã cố định (BR-PQ-22). |
| Chọn nhóm khi tạo hoặc sửa nhân viên | `_resolve_groups` nhận mọi Group có trong DB. Thông báo lỗi liệt kê 4 mã. Màn `GroupPicker` hiện 4 nhóm cố định | `accounts/staff/services.py`, `erp-console/features/staff/components/GroupPicker.tsx` | Phần backend đã nhận được vai mới. Phần FE phải lấy danh sách vai từ API. |
| Sửa quyền của Group | **Chỉ superuser** sửa được trong Django Admin (S41-AC8). Chủ không có màn nào | dev notes 2026-09-24 dòng 480 | Hiện chưa ai ngoài Duy (superuser) đổi được quyền. Tính năng này mở việc đó cho Chủ qua console. |
| Kiểm kê: người nhập ≠ người duyệt | Kiểm **theo chứng từ** trong service (`created_by` ≠ người duyệt) | `inventory/stocktake/services.py` (BR-KK-02) | Kiêm nhiệm vẫn an toàn. Đây là mẫu cần nhân rộng. |
| Hàng hoàn: người tạo phiếu vs người duyệt | **Chỉ tách bằng quyền** (NV giao không có `approve_returntostock`). Service `apply_return` **không** kiểm người duyệt ≠ người tạo | `inventory/returns/services.py` | Khi kiêm nhiệm "giao + duyệt hàng hoàn" (đã làm được hôm nay bằng `quan_ly` + `nv_giao`) thì một người tự tạo và tự duyệt được. §6 H-SoD-2. |
| Phạm vi "NV kho chỉ sửa phiếu nhập của mình, trong ngày" (spec §1.6) | **Không thấy trong code** (`purchasing/receipts/api.py` không có `get_queryset` lọc) | grep 2026-09-28 | Luật spec chưa thực thi. Cần Tech Lead xác nhận trước khi đưa vào danh mục phạm vi (🟢 Q12). |

### 3.2 Phát hiện ngoài phạm vi, cần xử lý ngay (Critical, bất biến 1)

`GET /api/audit-logs/` trả nguyên văn `changes` (`accounts/audit/serializers.py`: "`changes`/`note` trả nguyên
văn"). Quyền `view_auditlog` đang cấp cho **`chu` và `quan_ly`** (migration 0007). Trong khi đó
`inventory/batches/services.py` ghi AuditLog có giá vốn:
- `close_batch`: `changes={"landed_unit_cost": {"final": …}}` (dòng 166–169),
- `recompute_landed_cost`: `changes={"landed_unit_cost": {"from": …, "to": …}}` (dòng 189–192).

**Vậy hiện nay Quản lý (không có `view_costprice`) đọc được giá vốn lô qua màn Nhật ký hoạt động.** Lỗi này có từ
trước và không do hồ sơ này gây ra. Nhưng vai tự định nghĩa sẽ nhân nó lên: mọi vai được tick "Xem nhật ký" đều thấy
giá vốn. BA đề nghị điều phối viên mở luồng **NHANH** sửa riêng (lọc `changes` theo quyền người xem, có test quét
khoá nhạy cảm) và **không chờ** hồ sơ này. Quyền "Xem nhật ký" được xếp nhạy cảm (§4.2) cho tới khi lỗi được sửa.

## 4. Tác nhân & quyền

| Tác nhân | Vai | Làm được gì trong tính năng này | Quyền cần |
|---|---|---|---|
| Chủ (Lộc) | `chu` (vai hệ thống) | Tạo, sửa, nhân bản, ngừng dùng vai. Gán vai cho người. Xem ai đang giữ vai nào | `manage_roles` (mới, khoá Chủ) + `manage_staff` |
| Duy | superuser | Đường cứu hộ qua Admin, như hiện nay (S41-AC8) | superuser |
| Quản lý / người được uỷ `manage_staff` | vai bất kỳ có `manage_staff` | Theo §10 Q4. Mặc định **không** sửa vai. Nếu được uỷ gán vai thì chỉ gán vai không chứa quyền mình không có | theo Q4 |
| Mọi nhân viên | vai bất kỳ | Xem "Quyền của tôi" (S47) dạng: tên các vai, danh sách tính năng, phạm vi | đăng nhập |
| Hệ thống | — | Chuyển 4 Group thành 4 vai sẵn có (một lần). Kiểm quyền mỗi request theo vai hiện hành. Chặn tách người trên chứng từ | — |

### 4.1 Đơn vị quyền: "quyền tính năng"

Chủ **không** tick trên khoảng 200 permission Django (add/change/delete/view × model). Làm vậy vô nghĩa với người
dùng và dễ ra tổ hợp hỏng (có `change` mà thiếu `view`, có `approve` mà không xem được chứng từ). Chủ chọn trên
**danh mục quyền tính năng** do dự án định nghĩa sẵn (PA, 🟡 Q5). Mỗi quyền tính năng:

- có **tên lời thường** và **một câu mô tả**, xếp theo **mảng** (Thu mua · Kho · Bán hàng & tiền · Giao hàng · CSKH ·
  Danh mục & giá · Báo cáo · Quản trị). Mảng khớp ba nhóm tool AI (Thu mua · Bán hàng · CSKH, M1 28/09) và menu
  console;
- **gói** các permission Tầng 1 và Tầng 2 cần thiết, kể cả các quyền xem kèm theo để màn hình chạy được (vd "Nhập
  lô" gồm xem mặt hàng, xem kho, xem nhà cung cấp);
- nếu có **phạm vi Tầng 3** thì cho chọn phạm vi ngay trên quyền đó (vd "Xem đơn: tất cả / chỉ đơn thuộc phiếu giao
  của tôi");
- có **mức nhạy cảm**: Thường · Nhạy cảm (Chủ gán được, có cảnh báo) · **Khoá Chủ** (không vai tự tạo nào chứa
  được).

Danh mục là **dữ liệu do dự án quản lý, đi theo code**. Chủ không tạo quyền tính năng mới. Chủ chỉ tạo **vai** (tập
quyền tính năng + phạm vi). Khi thêm tính năng mới, dev thêm quyền tính năng vào danh mục trong hồ sơ tính năng đó.

### 4.2 Danh mục quyền tính năng đề xuất (PA, đối chiếu ma trận spec §1.4–1.5 và migration 0002/0003/0006/0007)

Ký hiệu mức: **T** thường · **N** nhạy cảm · **K** khoá Chủ. Cột "Vai mẫu hiện có" giúp kiểm chuyển đổi không làm
mất quyền (Q = quan_ly, K = nv_kho, G = nv_giao; `chu` có tất cả).

| Mảng | Mã (PA) | Quyền tính năng | Gói (Tầng 1 / Tầng 2) | Phạm vi Tầng 3 | Mức | Vai mẫu hiện có |
|---|---|---|---|---|---|---|
| Thu mua | TM-01 | Xem nhà cung cấp | view supplier | — | T | Q K |
| | TM-02 | Quản lý nhà cung cấp | add/change supplier | — | T | Q |
| | TM-03 | Nhập lô (phiếu nhập) | view/add/change purchasereceipt(+line); xem item, warehouse, supplier, batch | Mọi phiếu / chỉ phiếu của tôi trong ngày (spec §1.6, code chưa có) | T | Q K |
| | TM-04 | Xem hoá đơn mua | view purchaseinvoice | — | **N** (có số tiền mua, cần xác minh field) | Q |
| | TM-05 | Nhập hoá đơn mua | add/change purchaseinvoice | — | N | — |
| | TM-06 | Nhập chi phí mua (landed cost) | `add_purchasecost`, CRU purchasecost | — | **K** | — |
| Kho | KH-01 | Xem tồn & lô | view batch, stockledgerentry, warehouse | cột giá vốn theo BC-02 | T | Q K |
| | KH-02 | Mở bán lô | `publish_batch` | — | T | Q |
| | KH-03 | Chốt lô | `close_batch` | — | **K** | — |
| | KH-04 | Chuyển kho / điều chỉnh | CRU stockentry | — | T | Q K |
| | KH-05 | Nhập số kiểm kê | CRU stockreconciliation(+line) | — | T | Q K |
| | KH-06 | Duyệt kiểm kê | `approve_stockreconciliation` | Không duyệt phiếu mình nhập (BR-KK-02) | T | Q |
| | KH-07 | Duyệt hàng hoàn | `approve_returntostock`, view returntostock | Không duyệt phiếu mình tạo (BR-HV-05 mới) | T | Q |
| Bán hàng & tiền | BH-01 | Xem đơn | view salesorder(+line), salesinvoice(+line) | Tất cả / chỉ đơn thuộc phiếu giao của tôi | T | Q K G* |
| | BH-02 | Huỷ đơn đã thanh toán | `cancel_paid_order` | — | T | Q |
| | BH-03 | Tạo phiếu hoàn | `create_refund`, CRU refund | — | T | Q |
| | BH-04 | Xác nhận đã hoàn tiền | `confirm_refund` | — | **K** | — |
| | BH-05 | Xác nhận thanh toán tay, xử lý hàng chờ thanh toán | `confirm_payment_manual` | — | **K** | — |
| | BH-06 | Xem giao dịch thanh toán | view paymenttransaction | — | N (có `raw_payload` chứa tên người chuyển, bất biến 9) | Q |
| Giao hàng | GH-01 | Soạn hàng & điều phối giao | CRU deliverynote, gán người giao | Tất cả phiếu | T | Q K |
| | GH-02 | Giao phiếu được gán | view/change deliverynote (chỉ trạng thái), CR returntostock | **Chỉ phiếu gán cho tôi** (cố định) | T | G |
| CSKH | CS-01 | Xem thông tin khách | view customer | Tất cả / chỉ khách của phiếu giao của tôi | **N** (tên, SĐT, địa chỉ: bất biến 9) | Q K G* |
| | CS-02 | Sửa thông tin khách | add/change customer | — | N | Q |
| Danh mục & giá | DM-01 | Xem danh mục | view item, itemgroup, bundleline | — | T | Q K |
| | DM-02 | Sửa ảnh mặt hàng | `change_item_image` | — | T | Q |
| | DM-03 | Quản lý mặt hàng, combo | CRUD item, itemgroup, bundleline | — | N | — |
| | DM-04 | Xem giá bán, ưu đãi | view pricelist, itemprice, pricingrule | — | T | Q |
| | DM-05 | Đổi giá bán, ưu đãi | CRU pricelist, itemprice; CRUD pricingrule | — | **N** (đổi doanh thu) | — |
| Báo cáo | BC-01 | Xem Tổng quan | `view_dashboard` | cột giá vốn theo BC-02 | T | Q K |
| | BC-02 | Xem giá vốn | `view_costprice` (+ view salesinvoicelinebatch) | — | **K** | — |
| | BC-03 | Xem báo cáo lãi lỗ | `view_profitreport` | — | **K** | — |
| Quản trị | QT-01 | Xem nhật ký hoạt động | `view_auditlog` | — | **N** (xem §3.2) | Q |
| | QT-02 | Quản lý nhân viên | `manage_staff`, CRU user/staffprofile | — | **K** | — |
| | QT-03 | Quản lý vai trò | `manage_roles` (mới) | — | **K** | — |
| Luôn có | — | Hồ sơ của tôi, đổi mật khẩu, Quyền của tôi | view staffprofile (của mình), view user | Chỉ của tôi | — | Q K G |

`*` G hiện có quyền này nhưng phạm vi hẹp (theo phiếu giao được gán).

Mức **K** ở trên là mặc định BA đề xuất, giữ đúng 7 quyền mà decisions 10/09 đặt cho Chủ, cộng `manage_roles`.
Duy có muốn chuyển một số quyền từ K sang N hay không là câu 🔴 Q1.

**Không có trong danh mục, không ai được cấp (kể cả vai Chủ qua màn này):** tạo SalesOrder/SalesInvoice
(BR-PQ-11); mọi `delete_*` trên chứng từ (BR-PQ-10); thêm/sửa/xoá AuditLog, StockLedgerEntry, `*LineBatch`
(BR-PQ-06, bất biến 4); sửa trực tiếp field khoá (BR-PQ-14); `change_batch` thô (hiện chỉ `chu` có, và nó mở đường
sửa `item`/`warehouse` của lô, dev notes 2026-09-24 dòng 145).

## 5. Use case

### UC-VT-01 Chủ tạo vai trò mới
- **Tiền điều kiện**: đăng nhập, có `manage_roles` (Chủ).
- **Luồng chính**:
  1. Chủ mở Quản trị → Vai trò → "Tạo vai". Chọn bắt đầu từ trống, hoặc **nhân bản** một vai có sẵn (vd nhân bản
     "Nhân viên kho").
  2. Nhập tên vai (duy nhất, vd "Thu mua"), mô tả một dòng (tuỳ chọn).
  3. Chọn quyền tính năng theo mảng. Với quyền có phạm vi thì chọn phạm vi. Quyền mức K hiện mờ kèm dòng "Chỉ vai Chủ
     có". Quyền mức N hiện cảnh báo đỏ và nêu lý do (giá vốn, dữ liệu khách, doanh thu).
  4. Hệ thống hiện **tóm tắt** trước khi lưu: danh sách tính năng, phạm vi, cảnh báo tổ hợp (§6.2) nếu có.
  5. Chủ lưu. Hệ thống ghi AuditLog `role_create` (tên vai + danh sách mã quyền tính năng + phạm vi).
- **Luồng thay thế**: 1a. Nhân bản vai → mọi quyền của vai gốc được tick sẵn, trừ quyền K (nếu vai gốc là `chu`).
- **Ngoại lệ**:
  - Tên trùng → từ chối, giữ nguyên form.
  - Gọi API gửi kèm quyền K, quyền không có trong danh mục, hoặc permission thô → 400 kèm mã BR-PQ-21, không lưu gì.
  - Người thiếu `manage_roles` gọi API → 403.
  - Vai rỗng (không tick quyền nào) → cho lưu (🟡 Q9), người giữ vai rỗng về màn "no-role" như hiện nay.
- **Hậu điều kiện**: vai tồn tại, chưa ai giữ. Không quyền của ai thay đổi.

### UC-VT-02 Chủ sửa quyền của vai đang có người giữ
- **Tiền điều kiện**: vai không phải `chu`; người sửa có `manage_roles`.
- **Luồng chính**:
  1. Chủ mở vai, thêm/bớt quyền tính năng hoặc đổi phạm vi.
  2. Hệ thống hiện **xem trước ảnh hưởng**: "N người đang giữ vai này" (tên hiển thị nhân viên, không có dữ liệu
     khách), quyền được thêm, quyền bị bớt. Nếu bớt quyền khiến ai đó mất quyền hoàn toàn (không vai nào khác bù) thì
     nêu rõ người đó.
  3. Chủ xác nhận. Hệ thống lưu và ghi AuditLog `role_update` (trước → sau, số người bị ảnh hưởng).
  4. **Hiệu lực ngay** từ request kế tiếp của mọi người giữ vai (BR-PQ-25). Không cần đăng nhập lại. Menu console cập
     nhật khi màn tải lại thông tin "tôi là ai". Menu cũ còn hiện thì cũng vô hại vì backend chặn (BR-PQ-12).
- **Luồng thay thế**: 2a. Bớt quyền "Giao phiếu được gán" (GH-02) khi có người giữ vai đang có phiếu **Đang giao** mà
  không vai nào khác bù → **chặn**, liệt kê mã phiếu (mở rộng BR-GH-08) (🟡 Q10).
- **Ngoại lệ**:
  - Hai Chủ sửa cùng vai cùng lúc → người lưu sau nhận thông báo "vai đã đổi, tải lại" và không ghi đè (🟡 Q11).
  - Sửa vai `chu` → 400 BR-PQ-22.
- **Hậu điều kiện**: chứng từ đã tạo giữ nguyên người thực hiện (BR-PQ-03). Việc AI đã ghi không bị đảo. Việc AI đang
  chờ (mức B trì hoãn) được kiểm lại quyền lúc thực thi và rơi về C nếu mất quyền (hồ sơ AI §4.2, §4.5).

### UC-VT-03 Chủ gán nhiều vai cho một người (kiêm nhiệm) hoặc gộp vai
- **Tiền điều kiện**: có `manage_staff`; người được gán không phải chính mình (BR-PQ-17).
- **Luồng chính**:
  1. Chủ mở hồ sơ nhân viên → "Vai" → tick một hoặc nhiều vai (thay cho 4 ô nhóm hiện nay).
  2. Hệ thống hiện **quyền hiệu lực** = hợp các vai. Với cùng một quyền có hai phạm vi thì lấy phạm vi rộng hơn, và
     ghi rõ phạm vi đó đến từ vai nào.
  3. Nếu tổ hợp có cặp "tạo – duyệt" (§6.2) thì hiện cảnh báo **không chặn**: "Người này sẽ không duyệt được phiếu
     kiểm kê do chính họ nhập".
  4. Lưu → AuditLog `staff_groups_change` (giữ tên action hiện có), trước → sau là **tên vai**.
- **Luồng thay thế**: "Gộp" theo ý Duy thực hiện theo hai cách, không cần tính năng riêng: (a) gán nhiều vai cho một
  người; (b) tạo một vai mới gồm quyền của nhiều vai (nhân bản rồi tick thêm).
- **Ngoại lệ**: như hiện nay: gán hoặc bỏ `chu` khi mình không phải Chủ → 403 BR-PQ-17; bỏ Chủ cuối cùng → 400
  BR-PQ-18; vai đã ngừng dùng → 400; tự đổi vai của mình → 400 BR-PQ-17.
- **Hậu điều kiện**: quyền đổi ngay. Chứng từ cũ không đổi.

### UC-VT-04 Chủ ngừng dùng một vai
- **Luồng chính**: Chủ bấm "Ngừng dùng". Nếu còn người **đang làm** giữ vai thì chặn, liệt kê họ. Nếu không, vai
  chuyển sang trạng thái ngừng dùng: không gán mới được, vẫn hiện trong nhật ký và trong hồ sơ người đã nghỉ.
- **Ngoại lệ**: vai `chu` hoặc vai sẵn có (theo Q2) → không ngừng được.
- **Hậu điều kiện**: không xoá cứng (BR-PQ-27). AuditLog `role_archive`. Cho dùng lại được (🟡 Q9).

### UC-VT-05 Nhân viên làm việc với nhiều vai
- **Luồng chính**:
  1. Đăng nhập. Hệ thống chọn trang đầu theo quyền, không theo tên vai: có "Xem Tổng quan" thì vào Tổng quan; chỉ có
     "Giao phiếu được gán" thì vào "Việc giao của tôi"; còn lại vào mục menu đầu tiên; không có quyền nào thì vào
     no-role.
  2. Menu hiện theo quyền tính năng (hợp các vai).
  3. Màn "Quyền của tôi" (S47) hiện tên các vai, danh sách tính năng theo mảng, phạm vi. **Không** hiện quyền mình
     không có. Người thiếu BC-02 không thấy dòng "Xem giá vốn" (BR-PQ-15).
- **Ngoại lệ**: gọi thẳng API ngoài quyền → 403. Ngoài phạm vi dòng → 404 (không lộ bản ghi có tồn tại), như S5.

### UC-VT-06 Hệ thống chặn một người tự tạo và tự duyệt trên cùng chứng từ
- **Luồng chính**: người có cả KH-05 và KH-06 duyệt phiếu kiểm kê → service kiểm `created_by ≠ người duyệt` → nếu
  trùng thì từ chối (BR-KK-02, đã có). Áp tương tự cho hàng hoàn (BR-HV-05 mới).
- **Ngoại lệ**: vựa chỉ có một người có quyền duyệt và người đó là người nhập → phiếu nằm chờ. Đây là **chủ ý**. Hệ
  thống hiện lý do ở khối "Tiếp theo" (hồ sơ AI §4.7): "Cần người khác duyệt".
- **Hậu điều kiện**: không đổi tồn khi bị chặn. Không ghi AuditLog cho lần bị chặn (như hiện nay).

### UC-VT-07 Chuyển đổi một lần từ 4 Group (Hệ thống)
- **Luồng chính**:
  1. Tạo danh mục quyền tính năng.
  2. Biến `chu`, `quan_ly`, `nv_kho`, `nv_giao` thành 4 vai sẵn có, giữ **mã** cũ và nhãn cũ ("Chủ", "Quản lý",
     "Nhân viên kho", "Nhân viên giao").
  3. Gắn quyền tính năng và phạm vi cho từng vai sao cho **tập permission hiệu lực của mọi user trước và sau là như
     nhau**.
  4. Người đang giữ Group nào thì giữ vai đó.
- **Ngoại lệ**: một permission đang có trong Group mà không khớp quyền tính năng nào (vd `view_user` của nv_kho,
  `view_customer` của nv_kho) → **dừng chuyển đổi** và báo danh sách. Dev bổ sung danh mục rồi chạy lại, không được
  lặng lẽ bỏ quyền.
- **Hậu điều kiện**: test so sánh ảnh chụp quyền trước và sau cho từng user mẫu. Không ai mất hay được thêm quyền.
  Nếu Duy chọn tạo sẵn vai "Thu mua / Bán hàng / CSKH" (Q2) thì các vai đó được tạo **nhưng chưa gán cho ai**.

## 6. Business rule

### 6.1 Bảng rule

| Mã | Nội dung | Nhãn | Mới / Sửa / Giữ |
|---|---|---|---|
| BR-PQ-08 | Quyền gán qua **vai trò** (thay chữ "Group"), không gán trực tiếp cho user. Ngoại lệ phải có ghi chú lý do. | D (10/09) | **Sửa** câu chữ |
| BR-PQ-09 | Một người giữ **nhiều vai**. Quyền hiệu lực là hợp của các vai. | D (10/09), Duy 28/09 | Giữ |
| BR-PQ-13 | Thay "mỗi Group có một bài test token" bằng: (a) mỗi **vai sẵn có** có test token như hiện nay; (b) test **"vai tối đa không nhạy cảm"**, tức một vai chứa mọi quyền tính năng mức T, gọi mọi endpoint và quét JSON đệ quy, không có khoá giá vốn và không có PII ngoài phạm vi; (c) test API từ chối lưu vai chứa quyền K. Vai do Chủ tạo lúc chạy không cần test riêng vì chúng là tổ hợp của các quyền tính năng đã có test. | PA | **Sửa** |
| BR-PQ-20 | **Vai trò** là tập quyền tính năng (kèm phạm vi) do Chủ đặt tên. **Quyền tính năng** là đơn vị nhỏ nhất người dùng chọn, gói sẵn Tầng 1 + Tầng 2 (+ phạm vi Tầng 3). Người dùng không chọn permission thô. Danh mục quyền tính năng do dự án định nghĩa và đi theo code. | Duy 28/09 + PA | **Mới** |
| BR-PQ-21 | Quyền **khoá Chủ** không được nằm trong vai tự tạo nào. API từ chối lưu. Danh sách mặc định: `close_batch`, `add_purchasecost`, `confirm_refund`, `confirm_payment_manual`, `view_costprice`, `view_profitreport`, `manage_staff`, `manage_roles`. Danh sách cuối cùng theo Q1. | D (10/09) + PA | **Mới** |
| BR-PQ-22 | Vai `chu` là **vai hệ thống**: có mọi quyền, kể cả quyền mới thêm sau này. Không sửa quyền, không đổi mã, không ngừng dùng. BR-PQ-17 và BR-PQ-18 giữ nguyên, tính theo vai này. | D (10/09) | **Mới** |
| BR-PQ-23 | Chỉ người có `manage_roles` (mặc định chỉ Chủ) tạo, sửa, ngừng dùng vai. Người gán vai (`manage_staff`) **không gán được vai chứa quyền mà chính mình không có** (chống leo quyền). | PA | **Mới** |
| BR-PQ-24 | Kiêm nhiệm lấy hợp: cùng một quyền mà hai phạm vi khác nhau thì lấy phạm vi rộng hơn. **Tách người trên chứng từ** (người duyệt ≠ người tạo) được kiểm trong service theo từng chứng từ, không kiểm lúc gán vai. Lúc gán vai chỉ **cảnh báo**. | PA (theo mẫu BR-KK-02) | **Mới** |
| BR-PQ-25 | Sửa vai hoặc sửa việc gán vai có hiệu lực **ngay từ request kế tiếp** của người bị ảnh hưởng. Không hồi tố chứng từ đã tạo (mở rộng BR-PQ-03). Việc AI đang chờ được kiểm lại quyền lúc thực thi. | PA | **Mới** |
| BR-PQ-26 | Mọi thao tác tạo/sửa/ngừng vai và mọi thao tác gán vai ghi AuditLog: ai, lúc nào, tên vai, danh sách mã quyền tính năng và phạm vi trước → sau, số người bị ảnh hưởng. Không ghi dữ liệu cá nhân khách. Không ghi được log thì không lưu (theo mẫu BR-PQ-05). | PA | **Mới** |
| BR-PQ-27 | Vai đã từng được gán thì **không xoá cứng**, chỉ ngừng dùng. Chỉ ngừng dùng được khi không còn người **đang làm** giữ vai. AuditLog lưu **tên** vai tại thời điểm ghi, nên đổi tên vai sau này không làm sai nhật ký cũ. | PA (theo tinh thần BR-PQ-10) | **Mới** |
| BR-PQ-28 | Permission mới thêm vào hệ thống: tự vào vai `chu`. Vai sẵn có nhận theo migration của tính năng đó (như hiện nay). Vai tự tạo nhận **qua quyền tính năng**: nếu permission mới được gói vào một quyền tính năng mức T mà vai đã có thì vai nhận luôn. **Quyền mức N hoặc K mới không bao giờ tự vào vai tự tạo.** Hồ sơ tính năng nào thêm permission phải ghi nó thuộc quyền tính năng nào. | PA | **Mới** |
| BR-PQ-29 | Phạm vi dòng/cột (Tầng 3) tính theo **quyền tính năng và phạm vi đã chọn**, không theo tên vai. Người không có quyền phạm vi rộng thì nhận **phạm vi hẹp nhất** (đóng khi nghi ngờ). Trang mặc định và menu cũng tính theo quyền. | PA | **Mới** (thay `FULL_SCOPE_GROUPS`, `home_for`, `onlyDelivery`) |
| BR-PQ-30 | Quyền tính năng cho xem **dữ liệu cá nhân khách** (tên, SĐT, địa chỉ: CS-01, CS-02, BH-06) là mức N. Chủ gán phải xác nhận cảnh báo. Phạm vi mặc định khi tạo vai mới là **hẹp nhất** (bất biến 9: chỉ lộ cho ai cần). | Bất biến 9 + PA | **Mới** |
| BR-HV-05 | Người **duyệt** phiếu hàng hoàn phải khác người **tạo** phiếu đó. Kiểm trong service, cùng kiểu BR-KK-02. | PA (vì kiêm nhiệm sẽ phổ biến) | **Mới** |
| BR-KK-02 | Người duyệt kiểm kê ≠ người nhập số, kiểm theo chứng từ. | D (10/09) | Giữ (đã có trong code) |
| BR-PQ-10, 11, 14 | Không xoá chứng từ; không ai tạo tay SalesOrder/SalesInvoice; field khoá. Các quyền này không có trong danh mục (§4.2). | D | Giữ |
| E-17 (spec §13) | "Một người kiêm hai việc: gán nhiều Group, **không tạo role mới**" → "gán nhiều vai; Chủ tự tạo vai mới khi cần". | Duy 28/09 | **Sửa** |

### 6.2 Sàn cứng: cấu hình vai không vượt được

| # | Sàn | Nguồn |
|---|---|---|
| H-1 | Quyền K không vào vai tự tạo (BR-PQ-21). | decisions 10/09 |
| H-2 | Không ai tạo tay SalesOrder/SalesInvoice, không ai xoá chứng từ, không ai sửa AuditLog. Các quyền này không có trong danh mục. | BR-PQ-06/10/11 |
| H-3 | Giá vốn chỉ lộ khi có BC-02; lãi lỗ chỉ lộ khi có BC-03. **Mọi** đường đọc (serializer, dashboard, nhật ký, dòng thời gian, AI, thông báo) đều lọc theo quyền của người nhận. | Bất biến 1 |
| H-4 | Dữ liệu cá nhân khách chỉ lộ theo CS-01 và phạm vi của nó. | Bất biến 9 |
| H-SoD-1 | Kiểm kê: người nhập ≠ người duyệt trên cùng phiếu. | BR-KK-02 |
| H-SoD-2 | Hàng hoàn: người tạo ≠ người duyệt trên cùng phiếu. | BR-HV-05 (mới) |
| H-SoD-3 | Hoàn tiền: nếu sau này `confirm_refund` được mở khỏi K (Q1) thì bắt buộc **người xác nhận ≠ người tạo phiếu hoàn**, trừ vai `chu`. | PA |
| H-5 | Không tự đổi vai của mình; không ai ngoài Chủ đụng vai `chu`; luôn còn ít nhất một Chủ đang làm. | BR-PQ-17/18 |
| H-6 | Không leo quyền qua việc gán vai (BR-PQ-23). | PA |
| H-7 | Quyền AI không vượt quyền hiện hành của người (tức vai). | Hồ sơ AI H1 |

**Cảnh báo tổ hợp (không chặn, hiện lúc lưu vai hoặc gán vai):** KH-05 + KH-06; GH-02 + KH-07; BH-03 + BH-04 (nếu
mở); một vai tự tạo có nhiều quyền N cùng lúc (vd CS-01 + BH-06 + TM-04).

## 7. Tác động dữ liệu & tích hợp

Chỉ nêu cái gì đổi. Cách làm là việc của Tech Lead (02b).

### 7.1 Dữ liệu
- **Danh mục quyền tính năng**: dữ liệu mới đi theo code (mã, tên, mảng, mô tả, gói permission, phạm vi cho phép,
  mức). Lý do: BR-PQ-20.
- **Vai trò**: có thể dựng trên `auth.Group` hiện có (tên hiển thị, mô tả, trạng thái ngừng dùng, cờ vai hệ thống/sẵn
  có, quyền tính năng đã chọn, phạm vi đã chọn). Việc có thêm model hay field nào phải được lý giải trong 02b
  (bất biến 8).
- **Phạm vi Tầng 3** cần một cách biểu diễn không dựa vào tên nhóm (BR-PQ-29).
- **Permission mới**: `manage_roles`. Có thể thêm permission phạm vi (vd "xem mọi đơn/khách/phiếu giao") để thay
  `FULL_SCOPE_GROUPS`.
- **AuditLog**: không đổi schema. Thêm action `role_create`, `role_update`, `role_archive`.
- **Không đổi**: FK chứng từ → User (decisions 10/09 "cái đắt duy nhất"), `StaffProfile`.

### 7.2 API / màn hình
- **Backend**: API vai trò (danh sách, chi tiết, tạo, sửa, ngừng dùng; kèm xem trước ảnh hưởng); API danh mục quyền
  tính năng. `/api/auth/me/` giữ key cũ (`groups`, `group_labels`, `permissions`, `capabilities`, `home`) và có thể
  thêm key (quy ước S47: "chỉ THÊM key"). API nhân viên nhận và trả vai, gồm cả vai tự tạo.
- **Console**: màn mới "Vai trò" trong mục Quản trị (chỉ ai có QT-03 mới thấy). `GroupPicker` thành chọn vai lấy từ
  API. `GROUP_LABEL`/`GROUP_HINT` lấy từ dữ liệu. `nav.ts` bỏ `onlyDelivery`/`inGroup(nvGiao)`, chuyển sang theo quyền.
  Màn "Quyền của tôi" nhóm theo mảng.
- **Django Admin**: giữ S41-AC8 (trang Group chỉ superuser). Nếu không, Admin thành cửa sau vượt BR-PQ-21.

### 7.3 Test hiện có phụ thuộc tên Group
Khoảng 16 chỗ trong 10 file test tra Group theo tên (`common/tests/fixtures.py`, `delivery/tests/test_api.py`,
`inventory/batches/tests/test_api.py`, `test_f1_fefo.py`, `accounts/.../test_s41_admin.py`, `test_s47_me_labels.py`,
`test_s03_auditlog.py`, `catalog/images/tests/test_api.py`, …). Nếu 4 vai sẵn có giữ nguyên mã (UC-VT-07) thì các test
này vẫn đúng và đóng vai **test hồi quy của việc chuyển đổi**. Test mới theo BR-PQ-13 (sửa).

### 7.4 Bên thứ ba
Không có.

### 7.5 Liên kết hồ sơ "AI của tôi" (`2026-09-28-ai-digital-worker`)
- Trần quyền AI (§4.2 bên đó) tự động bằng **quyền hiện hành theo vai**. Sửa vai thì trần AI co hoặc giãn ngay
  (BR-PQ-25). Không cần cơ chế riêng.
- §4.3 bên đó giả định "ba lệnh vùng đỏ chỉ `chu` có, nên hai lớp cấp là cùng một người (Lộc)". Giả định này **chỉ
  còn đúng nếu Q1 giữ K** cho `close_batch`, `confirm_refund`, `confirm_payment_manual`. Nếu Duy mở một trong ba ra
  vai tự tạo thì AI của người không phải Chủ có thể được giao lệnh vùng đỏ. Khi đó hồ sơ AI phải xét lại công tắc
  vùng đỏ.
- §8 bên đó "chuyển việc tới **Group** có quyền (`chu`, `quan_ly`…)" phải đổi thành "chuyển tới **người có quyền
  tính năng** tương ứng".
- Màn "AI của tôi" chia tab theo mảng. Dùng **cùng bộ mảng** với danh mục quyền tính năng (§4.1) để người dùng thấy
  một cách phân loại duy nhất.

## 8. Rủi ro Cá Về

| # | Rủi ro | Mức | Giảm thiểu |
|---|---|---|---|
| R1 | **Rò giá vốn qua vai tự tạo.** Một số permission Tầng 1 **tự bản thân đã là dữ liệu giá vốn** chứ không chỉ là cột: `view_purchasecost` (toàn bộ chứng từ chi phí), `view_salesinvoicelinebatch`, có thể cả `view_purchaseinvoice`. Và `view_auditlog` đang lộ `landed_unit_cost` (§3.2). Nếu Chủ tick thô được các quyền này thì bất biến 1 vỡ mà không cần `view_costprice`. | **Critical** | Chỉ chọn qua quyền tính năng. Các permission trên chỉ nằm trong quyền K/N (§4.2). Sửa §3.2 ngay. Test "vai tối đa không nhạy cảm" (BR-PQ-13b). |
| R2 | Phạm vi Tầng 3 viết theo tên Group. Vá vội bằng cách thêm tên vai mới vào `FULL_SCOPE_GROUPS` thì vai đó thấy **mọi** khách và đơn. | Cao | BR-PQ-29, đóng khi nghi ngờ. Làm ở Đ0 trước khi mở màn tạo vai. |
| R3 | Leo quyền: người có `manage_staff` hoặc `manage_roles` tự cấp cho mình hoặc cho đồng bọn. | Cao | `manage_roles` là K. BR-PQ-17 (không tự đổi vai của mình). BR-PQ-23. Admin chỉ superuser. |
| R4 | Rò dữ liệu cá nhân khách: vai "CSKH" hoặc "Bán hàng" được tick xem khách toàn bộ mà không cần. | Cao (bất biến 9) | CS-01 mức N, phạm vi mặc định hẹp (BR-PQ-30). Hồ sơ CSKH quyết phạm vi thật. |
| R5 | Kiêm nhiệm làm gãy tách người: luật hiện chỉ tách bằng quyền (hàng hoàn). | Trung bình | BR-HV-05, H-SoD-3, cảnh báo tổ hợp. |
| R6 | Chuyển đổi làm lệch quyền (ai đó mất quyền hôm sau không làm được việc, hoặc được thêm quyền). | Trung bình | UC-VT-07: dừng nếu không khớp; test ảnh chụp trước = sau. |
| R7 | Quyền mới sau này rơi vào vai tự tạo ngoài ý muốn, hoặc ngược lại không ai nhận nên tính năng mới "biến mất". | Trung bình | BR-PQ-28; mỗi hồ sơ tính năng ghi quyền tính năng. |
| R8 | Chủ cấu hình quá tay: nhiều vai, nhiều ô, khó hiểu, gán nhầm. | Trung bình | Vai sẵn có + nhân bản; xem trước ảnh hưởng; mô tả lời thường; "Quyền của tôi". |
| R9 | Vai rỗng hoặc vai bị bớt hết quyền → nhân viên đăng nhập vào no-role giữa ca. | Thấp | Xem trước ảnh hưởng nêu tên người mất hết quyền. |
| R10 | Tiền và chứng từ: tính năng này không trực tiếp đổi tiền, tồn hay FEFO. Rủi ro tiền chỉ phát sinh nếu Q1 mở quyền K. | — | Q1. |

## 9. Ngoài phạm vi

- **Nhiều vựa trên một hệ thống (multi-tenant).** "Case khác anh có thể yêu cầu gộp lại" được hiểu là cùng một vựa
  (hoặc một bản cài riêng cho vựa khác) tự tổ chức lại vai, không phải nhiều vựa dùng chung dữ liệu (🟡 Q6).
- Chủ tự tạo **quyền tính năng** mới hoặc tick permission thô.
- Phân quyền theo thời gian (ca, giờ), theo kho, theo mặt hàng. Hiện chỉ có một kho thực tế (🟢 Q13).
- Uỷ quyền tạm thời có hạn ("Quản lý thay Chủ 3 ngày") (🟢 Q14).
- Luồng CSKH (gọi khách, in tem, lấy hàng) và các quyền tính năng CSKH mới: hồ sơ riêng. Hồ sơ này chỉ đặt chỗ mảng
  CSKH trong danh mục.
- Sửa lỗi rò giá vốn qua nhật ký (§3.2): nên đi luồng NHANH riêng, ngay.
- Thực thi phạm vi "NV kho chỉ sửa phiếu nhập của mình trong ngày" (spec §1.6, code chưa có): xác minh riêng
  (🟢 Q12).

## 10. Câu hỏi mở

| # | Mức | Câu hỏi | Phương án | Mặc định PA đề xuất |
|---|---|---|---|---|
| Q1 | 🔴 | **Trong 7 quyền decisions 10/09 dành cho Chủ, quyền nào được phép đưa vào vai tự tạo?** (`view_costprice`, `view_profitreport`, `close_batch`, `add_purchasecost`, `confirm_refund`, `confirm_payment_manual`, `manage_staff`) | **(a)** Không quyền nào: cả 7 (+ `manage_roles`) khoá cho vai Chủ; muốn ai có thì gán thêm vai Chủ cho người đó. Không lật 10/09. **(b)** Mở 4 quyền "đổi số lời lỗ" (`view_costprice`, `view_profitreport`, `close_batch`, `add_purchasecost`) thành mức N: Chủ gán được vào vai tự tạo, có cảnh báo và AuditLog. Giữ khoá 3 quyền "tiền rời túi / nhân sự" (`confirm_refund`, `confirm_payment_manual`, `manage_staff`) + `manage_roles`. Lật một phần 10/09; hồ sơ AI phải xét lại §4.3 nếu mở `close_batch`. **(c)** Mở hết thành N trừ `manage_roles`. | **(a)** cho V1. Lý do: `confirm_payment_manual` gắn với việc chỉ Lộc xem được sao kê, đây là sự thật vật lý chứ không phải cấu hình. Giá mua là lợi thế đàm phán (spec §1.7). Cách (a) vẫn cho Lộc "gộp" bằng cách gán vai Chủ cho người tin cậy. |
| Q2 | 🔴 | **Bốn Group hiện có sẽ thế nào, và có tạo sẵn vai "Thu mua / Bán hàng / CSKH" không?** | **(a)** `chu` là vai hệ thống; `quan_ly`, `nv_kho`, `nv_giao` thành **vai sẵn có, Chủ sửa được** nhưng không ngừng dùng được. Không tạo sẵn vai mới; Chủ tự tạo "Thu mua / Bán hàng / CSKH" bằng nhân bản. **(b)** Ba vai cũ **khoá làm mẫu** (chỉ nhân bản, không sửa); Chủ làm việc trên vai tự tạo. **(c)** Như (a) và tạo sẵn 3 vai "Thu mua", "Bán hàng", "CSKH" theo bảng quyền BA đề xuất (chưa gán ai). | **(b) + tạo sẵn 3 vai như (c)**. Mẫu khoá giữ cho test hồi quy và tên nhóm cũ có nghĩa ổn định; ba vai mới cho Lộc điểm xuất phát đúng cách vựa đang chia việc. Nếu Duy muốn đơn giản hơn thì chọn (a). |
| Q3 | 🟡 | Tên hiển thị: "Vai trò" hay "Hồ sơ quyền" (Duy nói "giống tự tạo profile")? | — | "**Vai trò**". Tránh nhầm với "Hồ sơ nhân viên" (`StaffProfile`) đã có. |
| Q4 | 🟡 | Ai được tạo/sửa vai? | (a) Chỉ Chủ; (b) Chủ uỷ `manage_roles` cho Quản lý với trần "không cấp quyền mình không có". | **(a)**. `manage_roles` là K. |
| Q5 | 🟡 | Đơn vị quyền là "quyền tính năng" gói sẵn (§4.1, §4.2), không tick permission thô. Danh mục §4.2 có đúng cách Lộc nghĩ về công việc không? | — | Dùng danh mục §4.2. Duy/Lộc góp ý tên và cách gom trong lúc duyệt. |
| Q6 | 🟡 | "Case khác gộp lại" có nghĩa là bán Cá Về cho vựa khác (nhiều vựa) không? | — | Không. Hiểu là cùng vựa đổi tổ chức, hoặc bản cài riêng. Multi-tenant ngoài phạm vi. |
| Q7 | 🟡 | Người không phải Chủ có `manage_staff` (nếu Q1 mở) gán được những vai nào? | — | Chỉ vai mà mọi quyền trong đó mình cũng có (BR-PQ-23); không đụng vai `chu`. |
| Q8 | 🟡 | Hàng hoàn: người tạo ≠ người duyệt (BR-HV-05). Có ngoại lệ cho Chủ không? | — | Không ngoại lệ cho người thường. Vai `chu` được tự duyệt (Chủ là người chịu lỗ cuối cùng), có ghi AuditLog. |
| Q9 | 🟡 | Có cho lưu vai rỗng không? Vai đã ngừng dùng có được dùng lại không? | — | Cho lưu vai rỗng (để dựng dần). Cho dùng lại vai đã ngừng, có AuditLog. |
| Q10 | 🟡 | Bớt quyền "Giao phiếu được gán" khi người giữ vai còn phiếu Đang giao? | — | Chặn, liệt kê mã phiếu (mở rộng BR-GH-08). |
| Q11 | 🟡 | Hai người sửa cùng vai cùng lúc? | — | Người lưu sau bị từ chối, "vai đã đổi, tải lại". |
| Q12 | 🟢 | Phạm vi "NV kho chỉ sửa phiếu nhập của mình trong ngày" (spec §1.6) chưa có trong code. Làm, hay bỏ khỏi spec? | — | Tech Lead xác minh. Tạm thời TM-03 chỉ có phạm vi "mọi phiếu". |
| Q13 | 🟢 | Phạm vi theo kho, theo ca. | — | Để sau. |
| Q14 | 🟢 | Uỷ quyền tạm thời có hạn. | — | Để sau; hiện làm bằng gán vai rồi bỏ vai (có AuditLog). |

## 11. Phân đoạn đề xuất (để PO cắt story)

| Đoạn | Nội dung | Điều kiện xong |
|---|---|---|
| **Đ-NHANH (tách riêng, ngay)** | Sửa rò giá vốn qua `/api/audit-logs/` (§3.2) | Test quét `changes` theo quyền người xem |
| **Đ0: tiền đề, không đổi hành vi** | Gỡ phụ thuộc tên Group: phạm vi Tầng 3, trang mặc định, menu tính theo quyền (BR-PQ-29); thêm `manage_roles`; danh mục quyền tính năng + chuyển 4 Group thành vai sẵn có (UC-VT-07) | Test ảnh chụp quyền trước = sau; toàn bộ test hiện có xanh |
| **Đ1: vai tự tạo** | Màn và API Vai trò (UC-VT-01, 02, 04), chọn nhiều vai cho nhân viên (UC-VT-03), "Quyền của tôi" theo mảng (UC-VT-05), AuditLog (BR-PQ-26), sàn K (BR-PQ-21) | Test BR-PQ-13 (sửa); Chủ tạo được vai "Thu mua" và gán cho một người |
| **Đ2: tách người & cảnh báo** | BR-HV-05, cảnh báo tổ hợp, xem trước ảnh hưởng, chặn bớt quyền giao khi còn phiếu Đang giao | Test tự tạo – tự duyệt bị chặn |
| **Đ3: nối AI** | Hồ sơ AI: chuyển việc theo quyền tính năng; tab mảng trong "AI của tôi"; nếu Q1 ≠ (a) thì xét lại công tắc vùng đỏ | Theo hồ sơ AI |
