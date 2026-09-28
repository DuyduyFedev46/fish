# Vai trò tự định nghĩa (Chủ tự tạo vai bằng ma trận CRUD, một người kiêm nhiều vai) — Phân tích nghiệp vụ
> BA · 2026-09-28 (sửa cùng ngày theo chỉnh của Duy: bỏ danh mục "quyền tính năng", chuyển sang ma trận CRUD) ·
> Trạng thái: **CHỜ DUYỆT**
>
> **Đụng quyết định đã chốt.** decisions.md 2026-09-10 "Phân quyền 3 tầng…" mục 2 chốt **bốn Group cố định**,
> và spec §13 E-17 ghi "gán nhiều Group, **không tạo role mới**". Yêu cầu này lật một phần mục đó: cơ chế 3 tầng,
> cộng dồn và ranh giới Chủ ↔ Quản lý được giữ, còn danh sách vai thì không cố định nữa. BA không sửa
> `decisions.md`. Duy tự ghi quyết định sau khi trả lời các câu 🔴 ở §10.

## Câu trả lời / chỉnh của Duy

| Ngày | Nguyên văn | Hệ quả áp vào bản phân tích |
|---|---|---|
| 2026-09-28 | **"người dùng ko quan tâm chọn feature đâu nha, cho chọn CRUD là oke rồi"** | Bỏ danh mục khoảng 30 "quyền tính năng" của bản trước. Màn tạo vai là **ma trận CRUD**: mỗi dòng là một đối tượng nghiệp vụ người dùng hiểu (Phiếu nhập, Lô, Đơn, Phiếu giao…), các cột là Xem · Thêm · Sửa · Duyệt · Huỷ/Xoá (§4.1). Tầng 2, phạm vi Tầng 3, quyền khoá Chủ và các quyền tự nó là giá vốn vẫn được xử lý **ở hậu trường**, theo quy ước ở §4.2–4.6, nên màn hình không phức tạp thêm. |

## 1. Yêu cầu gốc

> "việc phân quyền trên tính năng cũng do con người tự define, giống tự tạo profile vậy đó, có thể 1 user nhưng
> kiêm nhiệm, trong case này em chia ra nhưng case khác anh có thể yêu cầu gộp lại"

Nguồn: Duy (PO), 2026-09-28. Bối cảnh cùng ngày (hồ sơ `2026-09-28-ai-digital-worker`, dòng M-scope): Duy chọn
"Tách 2 hồ sơ mới". Hồ sơ này là một trong hai. Hồ sơ kia là luồng CSKH (gọi khách xác nhận địa chỉ, in tem, lấy
hàng). Nền của yêu cầu là việc đang chia hệ thống thành ba mảng **Thu mua · Bán hàng · CSKH** (research
`01-mcp-per-function.md` §8).

## 2. Tóm tắt

**Chủ** cần **tự tạo vai trò bằng cách tick ma trận Xem / Thêm / Sửa / Duyệt / Huỷ trên từng loại giấy tờ, rồi gán
một hoặc nhiều vai cho mỗi nhân viên**, để **tổ chức người theo cách vựa đang chạy** (tách Thu mua / Bán hàng /
CSKH, hoặc gộp khi ít người) mà không phải nhờ dev sửa code hay migration mỗi lần đổi. Ba giới hạn đi kèm:
1. Chủ **tick CRUD trên đối tượng nghiệp vụ** (Duy chỉnh 28/09), không tick permission Django thô. Một ô trong
   ma trận có thể ứng với nhiều permission ở hậu trường.
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
| Menu console | Đa số theo permission. Riêng `onlyDelivery` và "Việc giao của tôi" (`inGroup(nvGiao)`) theo tên nhóm | `erp-console/shared/lib/nav.ts` | Phải đổi sang theo ô quyền (ô Xem, phạm vi). |
| Luật tài khoản Chủ | BR-PQ-17 và BR-PQ-18 tính "là Chủ" theo Group `chu` | `accounts/staff/services.py` | Giữ nguyên: `chu` vẫn là vai hệ thống, có mã cố định (BR-PQ-22). |
| Chọn nhóm khi tạo hoặc sửa nhân viên | `_resolve_groups` nhận mọi Group có trong DB. Thông báo lỗi liệt kê 4 mã. Màn `GroupPicker` hiện 4 nhóm cố định | `accounts/staff/services.py`, `erp-console/features/staff/components/GroupPicker.tsx` | Phần backend đã nhận được vai mới. Phần FE phải lấy danh sách vai từ API. |
| Sửa quyền của Group | **Chỉ superuser** sửa được trong Django Admin (S41-AC8). Chủ không có màn nào | dev notes 2026-09-24 dòng 480 | Hiện chưa ai ngoài Duy (superuser) đổi được quyền. Tính năng này mở việc đó cho Chủ qua console. |
| Kiểm kê: người nhập ≠ người duyệt | Kiểm **theo chứng từ** trong service (`created_by` ≠ người duyệt) | `inventory/stocktake/services.py` (BR-KK-02) | Kiêm nhiệm vẫn an toàn. Đây là mẫu cần nhân rộng. |
| Hàng hoàn: người tạo phiếu vs người duyệt | **Chỉ tách bằng quyền** (NV giao không có `approve_returntostock`). Service `apply_return` **không** kiểm người duyệt ≠ người tạo | `inventory/returns/services.py` | Khi kiêm nhiệm "giao + duyệt hàng hoàn" (đã làm được hôm nay bằng `quan_ly` + `nv_giao`) thì một người tự tạo và tự duyệt được. §6 H-SoD-2. |
| Phạm vi "NV kho chỉ sửa phiếu nhập của mình, trong ngày" (spec §1.6) | **Không thấy trong code** (`purchasing/receipts/api.py` không có `get_queryset` lọc) | grep 2026-09-28 | Luật spec chưa thực thi. Cần Tech Lead xác nhận trước khi cho dòng Phiếu nhập chọn phạm vi "Của tôi" (🟢 Q12). |

### 3.2 Phát hiện ngoài phạm vi, cần xử lý ngay (Critical, bất biến 1)

`GET /api/audit-logs/` trả nguyên văn `changes` (`accounts/audit/serializers.py`: "`changes`/`note` trả nguyên
văn"). Quyền `view_auditlog` đang cấp cho **`chu` và `quan_ly`** (migration 0007). Trong khi đó
`inventory/batches/services.py` ghi AuditLog có giá vốn:
- `close_batch`: `changes={"landed_unit_cost": {"final": …}}` (dòng 166–169),
- `recompute_landed_cost`: `changes={"landed_unit_cost": {"from": …, "to": …}}` (dòng 189–192).

**Vậy hiện nay Quản lý (không có `view_costprice`) đọc được giá vốn lô qua màn Nhật ký hoạt động.** Lỗi này có từ
trước và không do hồ sơ này gây ra. Nhưng vai tự định nghĩa sẽ nhân nó lên: mọi vai được tick "Xem nhật ký" đều thấy
giá vốn. BA đề nghị điều phối viên mở luồng **NHANH** sửa riêng (lọc `changes` theo quyền người xem, có test quét
khoá nhạy cảm) và **không chờ** hồ sơ này. Ô "Xem" của dòng "Nhật ký hoạt động" được xếp nhạy cảm (§4.1) cho tới khi
lỗi được sửa.

## 4. Tác nhân & quyền

| Tác nhân | Vai | Làm được gì trong tính năng này | Quyền cần |
|---|---|---|---|
| Chủ (Lộc) | `chu` (vai hệ thống) | Tạo, sửa, nhân bản, ngừng dùng vai. Gán vai cho người. Xem ai đang giữ vai nào | `manage_roles` (mới, khoá Chủ) + `manage_staff` |
| Duy | superuser | Đường cứu hộ qua Admin, như hiện nay (S41-AC8) | superuser |
| Quản lý / người được uỷ `manage_staff` | vai bất kỳ có `manage_staff` | Theo §10 Q4. Mặc định **không** sửa vai. Nếu được uỷ gán vai thì chỉ gán vai không chứa quyền mình không có | theo Q4 |
| Mọi nhân viên | vai bất kỳ | Xem "Quyền của tôi" (S47) dạng: tên các vai và ma trận CRUD hiệu lực (chỉ các dòng mình có quyền), kèm phạm vi | đăng nhập |
| Hệ thống | — | Chuyển 4 Group thành 4 vai sẵn có (một lần). Kiểm quyền mỗi request theo vai hiện hành. Chặn tách người trên chứng từ | — |

### 4.1 Màn tạo vai: ma trận CRUD (Duy chỉnh 28/09)

**Nguyên tắc**: Chủ chỉ thấy **một bảng**. Mỗi dòng là một **đối tượng nghiệp vụ** mà người ở vựa gọi tên được. Có
**5 cột cố định**: **Xem · Thêm · Sửa · Duyệt · Huỷ/Xoá**. Ô nào không có nghĩa với dòng đó thì **để trống** (không
có ô tick). Ô nào chỉ vai Chủ có thì **hiện ổ khoá, không tick được**. Mọi thứ khác (permission thô, bảng con, quyền
xem kèm, phạm vi dòng, cột giá vốn) nằm ở hậu trường theo các quy ước §4.2–4.5.

Ký hiệu trong bảng: ☐ tick được · **🔒** chỉ vai Chủ (hiện khoá) · **⚠** tick được nhưng có cảnh báo đỏ (nhạy cảm) ·
**—** không có ô · *(phạm vi)* có ô chọn "Của tôi / Tất cả" (§4.3). Cột cuối cho biết ai trong 4 vai hiện có đang giữ ô
đó (Q = Quản lý, K = NV kho, G = NV giao; Chủ có hết), để kiểm việc chuyển đổi không làm mất quyền (UC-VT-07).

| Nhóm | Đối tượng (nhãn trên màn) | Xem | Thêm | Sửa | Duyệt (nghĩa của dòng) | Huỷ/Xoá | Hiện có |
|---|---|---|---|---|---|---|---|
| Thu mua | Nhà cung cấp | ☐ | ☐ | ☐ | — | Xoá ☐ (chỉ khi chưa có giao dịch) | Xem: Q K · Thêm/Sửa: Q |
| | Phiếu nhập hàng | ☐ *(phạm vi)* | ☐ | ☐ | — (gửi phiếu = Sửa) | — | Q K |
| | Hoá đơn mua | ⚠ | ⚠ | ⚠ | — | — | Xem: Q |
| | Chi phí mua (đá, xe, bốc vác) | 🔒 | 🔒 | 🔒 | — | — | — |
| Kho | Lô hàng | ☐ | — (lô sinh từ phiếu nhập) | 🔒 | ☐ **Mở bán lô** · 🔒 Chốt lô | 🔒 Huỷ lô hết hạn | Xem: Q K · Mở bán: Q |
| | Chuyển kho / điều chỉnh | ☐ | ☐ | ☐ | — | — | Q K |
| | Phiếu kiểm kê | ☐ | ☐ | ☐ | ☐ **Duyệt kiểm kê** | — | Xem/Thêm/Sửa: Q K · Duyệt: Q |
| | Hàng hoàn về kho | ☐ | ☐ | — | ☐ **Duyệt hàng hoàn** | — | Xem: Q K G · Thêm: K G · Duyệt: Q |
| Bán hàng & tiền | Đơn hàng | ☐ *(phạm vi)* | — (chỉ Hệ thống tạo) | — | 🔒 Xác nhận thanh toán tay | ☐ **Huỷ đơn đã thanh toán** | Xem: Q K G(của tôi) · Huỷ: Q |
| | Phiếu hoàn tiền | ☐ | ☐ (tạo phiếu hoàn) | ☐ | 🔒 Xác nhận đã chuyển tiền | — | Q |
| | Giao dịch thanh toán | ⚠ | — | — | 🔒 Xử lý tiền lệch | — | Xem: Q |
| Giao hàng | Phiếu giao | ☐ *(phạm vi)* | ☐ | ☐ | — | — | Q K: tất cả · G: của tôi, chỉ sửa trạng thái |
| Khách hàng | Khách hàng | ⚠ *(phạm vi)* | ⚠ | ⚠ | — | — | Xem: Q K G(của tôi) · Thêm/Sửa: Q |
| Danh mục & giá | Mặt hàng & combo | ☐ | ⚠ | ⚠ | — | Xoá ⚠ (chỉ khi chưa có giao dịch) | Xem: Q K |
| | Ảnh mặt hàng | — | — | ☐ | — | — | Q |
| | Nhóm hàng | ☐ | ⚠ | ⚠ | — | Xoá ⚠ | Xem: Q K |
| | Giá bán & ưu đãi | ☐ | ⚠ | ⚠ | — | Xoá ⚠ (ưu đãi) | Xem: Q |
| | Kho (địa điểm) | ☐ | 🔒 | 🔒 | — | — | Xem: Q K |
| Báo cáo | Tổng quan | ☐ | — | — | — | — | Q K |
| | Giá vốn (đơn giá mua, giá vốn lô) | 🔒 | — | — | — | — | — |
| | Báo cáo lãi lỗ | 🔒 | — | — | — | — | — |
| Quản trị | Nhật ký hoạt động | ⚠ (xem §3.2) | — | — | — | — | Q |
| | Nhân viên | 🔒 | 🔒 | 🔒 | — | 🔒 Cho nghỉ | — |
| | Vai trò | 🔒 | 🔒 | 🔒 | — | 🔒 Ngừng dùng | — |

Khoảng **24 dòng × 5 cột**. Chủ thường chỉ tick 10–20 ô cho một vai. Các nhóm thu gọn hoặc mở ra được. Bảng này
thay cho danh mục khoảng 30 "quyền tính năng" của bản trước.

"**Bài viết**" (Duy lấy làm ví dụ) **chưa có trong hệ thống**: grep ngày 28/09 không có model bài viết hay blog. Khi
tính năng đó ra đời, nó thêm một dòng vào ma trận (BR-PQ-28).

Không xuất hiện ở bất kỳ ô nào, không ai được cấp (kể cả vai Chủ qua màn này): tạo tay SalesOrder/SalesInvoice
(BR-PQ-11); xoá cứng chứng từ (BR-PQ-10); thêm/sửa/xoá AuditLog, StockLedgerEntry, `*LineBatch` (BR-PQ-06, bất
biến 4); sửa trực tiếp field khoá (BR-PQ-14).

### 4.2 Hậu trường (1): thao tác Tầng 2 (duyệt, chốt, xác nhận, huỷ)

Có ba cách đưa Tầng 2 vào ma trận:

| Cách | Mô tả | Đánh giá |
|---|---|---|
| (A) Gộp vào cột "Sửa" | Tick Sửa phiếu kiểm kê thì được duyệt luôn | **Loại.** Chính đây là chỗ NV kho và Quản lý khác nhau (spec §1.5). Gộp lại thì mất tách vai nhập/duyệt: người đếm tự duyệt được mọi phiếu của người khác mà không ai soát, và ranh giới "khách phải chờ" của 10/09 không còn diễn đạt được. |
| (B) **Một cột "Duyệt" duy nhất**, nghĩa theo từng dòng | Ô Duyệt của dòng "Phiếu kiểm kê" là duyệt kiểm kê, của dòng "Lô hàng" là mở bán lô, của dòng "Hàng hoàn" là duyệt hàng hoàn. Cột "Huỷ" của dòng "Đơn hàng" là huỷ đơn đã thanh toán | **Đề xuất (PA, 🟡 Q5).** Thêm đúng một cột. Khi rê chuột hoặc chạm vào ô thì hiện nghĩa cụ thể của ô. |
| (C) Tự suy từ CRUD | Có Sửa + Xem thì tự được duyệt | **Loại**, cùng lý do như (A), và người dùng không nhìn thấy mình vừa cấp gì. |

Ánh xạ ô sang Tầng 2 theo cách (B), ở hậu trường:

| Dòng | Ô | Permission hậu trường |
|---|---|---|
| Lô hàng | Duyệt: Mở bán lô | `publish_batch` |
| Lô hàng | Duyệt: Chốt lô (🔒) | `close_batch` |
| Phiếu kiểm kê | Duyệt | `approve_stockreconciliation` (người duyệt ≠ người nhập, BR-KK-02) |
| Hàng hoàn về kho | Duyệt | `approve_returntostock` (người duyệt ≠ người tạo, BR-HV-05 mới) |
| Đơn hàng | Huỷ | `cancel_paid_order` |
| Đơn hàng | Duyệt: Xác nhận thanh toán tay (🔒) | `confirm_payment_manual` |
| Phiếu hoàn tiền | Thêm | `create_refund` + add/change refund |
| Phiếu hoàn tiền | Duyệt: Xác nhận đã chuyển tiền (🔒) | `confirm_refund` |
| Giao dịch thanh toán | Duyệt: Xử lý tiền lệch (🔒) | `confirm_payment_manual` |
| Chi phí mua | cả dòng (🔒) | `add_purchasecost` + CRU purchasecost |
| Ảnh mặt hàng | Sửa | `change_item_image` (không mở `change_item`) |
| Nhân viên | cả dòng (🔒) | `manage_staff` + CRU user/staffprofile |
| Vai trò | cả dòng (🔒) | `manage_roles` (mới) |

Một dòng có **hai** thao tác Tầng 2 cùng cột (Lô hàng: Mở bán ☐, Chốt 🔒) thì hiện thành hai ô nhỏ trong cùng cột.
Không thêm cột mới.

### 4.3 Hậu trường (2): phạm vi Tầng 3 (của tôi / tất cả)

- Chỉ **4 dòng** có ô chọn phạm vi, đặt cạnh ô Xem: **Phiếu nhập hàng**, **Đơn hàng**, **Phiếu giao**, **Khách
  hàng**. Các dòng khác không có ô phạm vi.
- **Mặc định là "Của tôi"** (hẹp nhất) khi vừa tick Xem (BR-PQ-29, BR-PQ-30). Muốn "Tất cả" thì Chủ phải chọn.
- Nghĩa của "Của tôi":
  - Phiếu giao: phiếu **gán cho tôi**. Khi đó ô Sửa chỉ cho **đổi trạng thái giao**, không sửa dòng hàng (spec §1.6).
  - Đơn hàng, Khách hàng: đơn và khách **thuộc phiếu giao gán cho tôi** (như S5 hiện nay).
  - Phiếu nhập hàng: phiếu **tôi tạo, trong ngày** (spec §1.6). Code **chưa thực thi** luật này (§3.1). Cho tới khi
    Tech Lead xác minh (🟢 Q12), dòng này chỉ có "Tất cả".
- Phạm vi áp cho **mọi** cột của dòng đó. Không có kiểu "xem tất cả nhưng sửa của tôi".
- Cột giá vốn (đơn giá mua, giá vốn lô, `unit_cost` phân bổ) **không có ô riêng trên từng dòng**. Nó chỉ phụ thuộc dòng
  khoá "Giá vốn" (🔒). Vai tự tạo vì vậy không bao giờ thấy cột giá vốn trên Lô, Phiếu nhập, Đơn, Tổng quan.

### 4.4 Hậu trường (3): quyền khoá Chủ và các quyền tự nó là giá vốn

- **Hiện khoá (🔒)**, không ẩn: Chủ thấy vai tự tạo **không** làm được gì, giúp tránh hiểu nhầm "sao Quản lý không
  chốt lô được". Các ô 🔒 mặc định theo decisions 10/09: chốt lô, chi phí mua, xác nhận đã chuyển tiền hoàn, xác nhận
  thanh toán tay / xử lý tiền lệch, giá vốn, lãi lỗ, nhân viên, cộng thêm vai trò. Q1 quyết ô nào được mở thành ⚠.
- **Permission tự nó là giá vốn**, không bao giờ thành ô riêng mà chỉ đi theo dòng 🔒:
  - `view_costprice`, `view_salesinvoicelinebatch` → dòng "Giá vốn";
  - `view_profitreport` → dòng "Báo cáo lãi lỗ";
  - `view_purchasecost`, `add/change_purchasecost` → dòng "Chi phí mua".
- `change_batch` thô **không** ánh xạ vào ô Sửa lô cho vai tự tạo. Ô Sửa của dòng Lô hàng là 🔒, vì sửa lô đổi được
  mặt hàng hay kho của lô đang có tồn mà không có AuditLog (dev notes 2026-09-24 dòng 145).
- Kho (địa điểm): Thêm/Sửa 🔒, giữ như ma trận spec §1.4 (chỉ Chủ).
- Ô **⚠** (tick được, cảnh báo đỏ, AuditLog): Hoá đơn mua (có số tiền mua); Khách hàng và Giao dịch thanh toán (dữ liệu
  cá nhân, bất biến 9; giao dịch có `raw_payload` chứa tên người chuyển); Thêm/Sửa/Xoá Mặt hàng, Nhóm hàng, Giá bán &
  ưu đãi (đổi doanh thu; hiện chỉ Chủ có); Xem Nhật ký hoạt động (cho tới khi sửa §3.2).

### 4.5 Hậu trường (4): cột Xoá và Huỷ

- **Chứng từ không xoá cứng** (BR-PQ-10). Trên dòng chứng từ, cột này hiện chữ **"Huỷ"** và chỉ có ô khi chứng từ
  đó **có** thao tác huỷ bằng trạng thái trong code. Hiện chỉ có "Huỷ đơn đã thanh toán". Các chứng từ khác (phiếu
  nhập, kiểm kê, phiếu giao, phiếu hoàn) để **trống** vì code chưa có đường huỷ. Khi có thì thêm ô.
- **Danh mục** (Nhà cung cấp, Mặt hàng, Nhóm hàng, Ưu đãi) hiện chữ **"Xoá"**. Hệ thống vẫn chặn xoá khi đã phát
  sinh giao dịch (BR-PQ-10). Khi bị chặn, thông báo nói rõ lý do.
- Nhân viên: "Cho nghỉ" (🔒), không xoá (BR-PQ-01). Vai trò: "Ngừng dùng" (🔒), không xoá (BR-PQ-27).

### 4.6 Hậu trường (5): quyền kéo theo, để màn hình chạy được

- Tick bất kỳ ô nào trên một dòng thì **Xem của dòng đó tự bật**. Bỏ Xem thì cả dòng tắt.
- Bảng con đi theo dòng cha: dòng phiếu nhập, dòng đơn, dòng kiểm kê, thành phần combo, hoá đơn bán (theo Đơn hàng),
  sổ kho (theo Lô hàng).
- Quyền xem tối thiểu để dùng một dòng được bật kèm (vd Phiếu nhập kéo theo xem tên mặt hàng, kho, nhà cung cấp;
  Phiếu giao kéo theo xem đơn trong cùng phạm vi). Các quyền kéo theo **chỉ gồm tên và mã**, không kéo theo ô ⚠ hay
  🔒, và được liệt kê trong phần xem trước khi lưu vai.
- Luôn có, không hiện trong ma trận: hồ sơ của tôi, đổi mật khẩu, "Quyền của tôi", danh sách tên nhân viên
  (`view_user`) để hiện "người giao", "người tạo".
- Menu console tự suy từ ô Xem (như `nav.ts` hiện nay, bỏ phần dựa theo tên nhóm).

### 4.7 Ô tick gợi ý cho ba vai "Thu mua · Bán hàng · CSKH" (chỉ dùng nếu Q2 chọn tạo sẵn)

| Vai | Ô tick gợi ý (PA) | Không tick |
|---|---|---|
| Thu mua | Nhà cung cấp: Xem/Thêm/Sửa · Phiếu nhập hàng: Xem/Thêm/Sửa · Lô hàng: Xem · Mặt hàng & combo: Xem · Kho: Xem | Hoá đơn mua (⚠, để Chủ quyết) · Giá vốn, Chi phí mua (🔒) |
| Bán hàng | Đơn hàng: Xem (Tất cả) · Phiếu giao: Xem/Thêm/Sửa (Tất cả) · Lô hàng: Xem, Duyệt (Mở bán) · Mặt hàng: Xem · Giá bán & ưu đãi: Xem · Tổng quan: Xem | Huỷ đơn đã thanh toán, Phiếu hoàn tiền (để Chủ quyết) · Giá bán: Sửa (⚠) |
| CSKH | Đơn hàng: Xem (Tất cả) · Khách hàng: Xem ⚠ (phạm vi theo hồ sơ CSKH) · Phiếu giao: Xem · Phiếu hoàn tiền: Xem/Thêm · Hàng hoàn: Xem | Giao dịch thanh toán (⚠, `raw_payload`) · Khách hàng: Sửa (chờ hồ sơ CSKH) |

## 5. Use case

### UC-VT-01 Chủ tạo vai trò mới
- **Tiền điều kiện**: đăng nhập, có `manage_roles` (Chủ).
- **Luồng chính**:
  1. Chủ mở Quản trị → Vai trò → "Tạo vai". Chọn bắt đầu từ trống, hoặc **nhân bản** một vai có sẵn (vd nhân bản
     "Nhân viên kho").
  2. Nhập tên vai (duy nhất, vd "Thu mua"), mô tả một dòng (tuỳ chọn).
  3. Tick ô trong **ma trận CRUD** (§4.1). Tick Thêm, Sửa, Duyệt hoặc Huỷ thì Xem của dòng tự bật (§4.6). Dòng có
     phạm vi thì mặc định "Của tôi" (§4.3). Ô 🔒 hiện khoá kèm chú thích "Chỉ vai Chủ". Ô ⚠ hiện cảnh báo đỏ và nêu lý
     do (dữ liệu khách, số tiền mua, doanh thu).
  4. Hệ thống hiện **tóm tắt** trước khi lưu: các ô đã tick, phạm vi, quyền kéo theo (§4.6), cảnh báo tổ hợp (§6.2)
     nếu có.
  5. Chủ lưu. Hệ thống ghi AuditLog `role_create` (tên vai, các ô đã tick theo dạng `đối tượng.cột`, phạm vi).
- **Luồng thay thế**: 1a. Nhân bản vai → mọi ô của vai gốc được tick sẵn, trừ ô 🔒 (khi vai gốc là `chu`).
- **Ngoại lệ**:
  - Tên trùng → từ chối, giữ nguyên form.
  - Gọi API gửi kèm ô 🔒, ô không có trong ma trận, hoặc permission thô → 400 kèm mã BR-PQ-21, không lưu gì.
  - Người thiếu `manage_roles` gọi API → 403.
  - Vai rỗng (không tick quyền nào) → cho lưu (🟡 Q9), người giữ vai rỗng về màn "no-role" như hiện nay.
- **Hậu điều kiện**: vai tồn tại, chưa ai giữ. Không quyền của ai thay đổi.

### UC-VT-02 Chủ sửa quyền của vai đang có người giữ
- **Tiền điều kiện**: vai không phải `chu`; người sửa có `manage_roles`.
- **Luồng chính**:
  1. Chủ mở vai, tick hoặc bỏ tick ô trong ma trận, hoặc đổi phạm vi.
  2. Hệ thống hiện **xem trước ảnh hưởng**: "N người đang giữ vai này" (tên hiển thị nhân viên, không có dữ liệu
     khách), quyền được thêm, quyền bị bớt. Nếu bớt quyền khiến ai đó mất quyền hoàn toàn (không vai nào khác bù) thì
     nêu rõ người đó.
  3. Chủ xác nhận. Hệ thống lưu và ghi AuditLog `role_update` (trước → sau, số người bị ảnh hưởng).
  4. **Hiệu lực ngay** từ request kế tiếp của mọi người giữ vai (BR-PQ-25). Không cần đăng nhập lại. Menu console cập
     nhật khi màn tải lại thông tin "tôi là ai". Menu cũ còn hiện thì cũng vô hại vì backend chặn (BR-PQ-12).
- **Luồng thay thế**: 2a. Bỏ tick Sửa (hoặc Xem) của dòng "Phiếu giao" khi có người giữ vai đang có phiếu **Đang giao** mà
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
  2. Hệ thống hiện **ma trận hiệu lực** = hợp các vai (một ô được tick ở bất kỳ vai nào thì có). Cùng một dòng mà hai
     vai có hai phạm vi thì lấy phạm vi rộng hơn, và ghi rõ phạm vi đó đến từ vai nào.
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
  1. Đăng nhập. Hệ thống chọn trang đầu theo quyền, không theo tên vai: có Xem "Tổng quan" thì vào Tổng quan; chỉ có
     "Phiếu giao" phạm vi "Của tôi" thì vào "Việc giao của tôi"; còn lại vào mục menu đầu tiên; không có ô nào thì vào
     no-role.
  2. Menu hiện theo các ô Xem (hợp các vai).
  3. Màn "Quyền của tôi" (S47) hiện tên các vai và ma trận hiệu lực, **chỉ các dòng mình có**, kèm phạm vi. Người
     không có dòng "Giá vốn" không thấy dòng đó (BR-PQ-15).
- **Ngoại lệ**: gọi thẳng API ngoài quyền → 403. Ngoài phạm vi dòng → 404 (không lộ bản ghi có tồn tại), như S5.

### UC-VT-06 Hệ thống chặn một người tự tạo và tự duyệt trên cùng chứng từ
- **Luồng chính**: người có cả Thêm và Duyệt ở dòng "Phiếu kiểm kê" duyệt phiếu kiểm kê → service kiểm `created_by ≠ người duyệt` → nếu
  trùng thì từ chối (BR-KK-02, đã có). Áp tương tự cho hàng hoàn (BR-HV-05 mới).
- **Ngoại lệ**: vựa chỉ có một người có quyền duyệt và người đó là người nhập → phiếu nằm chờ. Đây là **chủ ý**. Hệ
  thống hiện lý do ở khối "Tiếp theo" (hồ sơ AI §4.7): "Cần người khác duyệt".
- **Hậu điều kiện**: không đổi tồn khi bị chặn. Không ghi AuditLog cho lần bị chặn (như hiện nay).

### UC-VT-07 Chuyển đổi một lần từ 4 Group (Hệ thống)
- **Luồng chính**:
  1. Tạo bảng ánh xạ ô ma trận → permission (§4.1–4.6).
  2. Biến `chu`, `quan_ly`, `nv_kho`, `nv_giao` thành 4 vai sẵn có, giữ **mã** cũ và nhãn cũ ("Chủ", "Quản lý",
     "Nhân viên kho", "Nhân viên giao").
  3. Tick ô và phạm vi cho từng vai theo cột "Hiện có" ở §4.1, sao cho **tập permission hiệu lực của mọi user trước
     và sau là như nhau**.
  4. Người đang giữ Group nào thì giữ vai đó.
- **Ngoại lệ**: một permission đang có trong Group mà không nằm trong ô nào và cũng không thuộc nhóm "luôn có"/"kéo
  theo" (§4.6) → **dừng chuyển đổi** và báo danh sách. Dev bổ sung ánh xạ rồi chạy lại, không được lặng lẽ bỏ quyền.
  Ví dụ cần soát: nv_kho có xem khách (ô ⚠ Khách hàng), `view_user` của mọi nhóm (luôn có).
- **Hậu điều kiện**: test so sánh ảnh chụp quyền trước và sau cho từng user mẫu. Không ai mất hay được thêm quyền.
  Nếu Duy chọn tạo sẵn vai "Thu mua / Bán hàng / CSKH" (Q2) thì các vai đó được tạo **nhưng chưa gán cho ai**.

## 6. Business rule

### 6.1 Bảng rule

| Mã | Nội dung | Nhãn | Mới / Sửa / Giữ |
|---|---|---|---|
| BR-PQ-08 | Quyền gán qua **vai trò** (thay chữ "Group"), không gán trực tiếp cho user. Ngoại lệ phải có ghi chú lý do. | D (10/09) | **Sửa** câu chữ |
| BR-PQ-09 | Một người giữ **nhiều vai**. Quyền hiệu lực là hợp của các vai. | D (10/09), Duy 28/09 | Giữ |
| BR-PQ-13 | Thay "mỗi Group có một bài test token" bằng: (a) mỗi **vai sẵn có** có test token như hiện nay; (b) test **"vai tối đa không nhạy cảm"**, tức một vai tick **mọi ô ☐** (không ⚠, không 🔒) với phạm vi "Tất cả", gọi mọi endpoint và quét JSON đệ quy, không có khoá giá vốn; (b') như (b) nhưng phạm vi "Của tôi", không thấy khách hay đơn ngoài phiếu được gán; (c) test API từ chối lưu vai chứa ô 🔒 hoặc permission thô. Vai do Chủ tạo lúc chạy không cần test riêng vì chúng là tổ hợp của các ô đã có test. | PA | **Sửa** |
| BR-PQ-20 | **Vai trò** là một **ma trận CRUD** do Chủ đặt tên: dòng là đối tượng nghiệp vụ, cột là Xem · Thêm · Sửa · Duyệt · Huỷ/Xoá (§4.1). Mỗi ô ứng với một hoặc nhiều permission ở hậu trường. Bảng ánh xạ do dự án định nghĩa và đi theo code. Người dùng không chọn permission thô. | **(D) Duy 28/09**: "cho chọn CRUD là oke rồi" | **Mới** |
| BR-PQ-20a | **Tầng 2 nằm ở cột "Duyệt"** (và cột "Huỷ" với huỷ bằng trạng thái). Nghĩa của ô phụ thuộc dòng (§4.2). Không suy Tầng 2 từ Thêm/Sửa. | PA | **Mới** |
| BR-PQ-20b | Tick bất kỳ ô nào trên một dòng thì Xem của dòng đó tự bật. Bỏ Xem thì cả dòng tắt. Quyền kéo theo (§4.6) chỉ gồm tên và mã, không bao giờ kéo theo ô ⚠ hay 🔒. | PA | **Mới** |
| BR-PQ-20c | Cột "Huỷ/Xoá": trên chứng từ là **Huỷ bằng trạng thái**, chỉ có ô khi code có thao tác huỷ đó. Trên danh mục là **Xoá**, và hệ thống vẫn chặn xoá khi đã phát sinh giao dịch. | BR-PQ-10 | **Mới** |
| BR-PQ-21 | Ô **khoá Chủ (🔒)** hiện trên ma trận nhưng không tick được, và API từ chối lưu. Mặc định gồm: Chi phí mua (cả dòng), Lô hàng: Sửa · Chốt lô · Huỷ lô hết hạn, Phiếu hoàn: xác nhận đã chuyển tiền, Đơn/Giao dịch thanh toán: xác nhận thanh toán tay, Giá vốn, Báo cáo lãi lỗ, Nhân viên, Vai trò, Kho: Thêm/Sửa. Các permission tự nó là giá vốn (`view_costprice`, `view_salesinvoicelinebatch`, `view_profitreport`, `*_purchasecost`) chỉ đi theo các dòng 🔒 này, không bao giờ thành ô riêng. Danh sách cuối cùng theo Q1. | D (10/09) + PA | **Mới** |
| BR-PQ-22 | Vai `chu` là **vai hệ thống**: có mọi quyền, kể cả quyền mới thêm sau này. Không sửa quyền, không đổi mã, không ngừng dùng. BR-PQ-17 và BR-PQ-18 giữ nguyên, tính theo vai này. | D (10/09) | **Mới** |
| BR-PQ-23 | Chỉ người có `manage_roles` (mặc định chỉ Chủ) tạo, sửa, ngừng dùng vai. Người gán vai (`manage_staff`) **không gán được vai chứa quyền mà chính mình không có** (chống leo quyền). | PA | **Mới** |
| BR-PQ-24 | Kiêm nhiệm lấy hợp: một ô được tick ở bất kỳ vai nào thì có; cùng một dòng mà hai phạm vi khác nhau thì lấy phạm vi rộng hơn. **Tách người trên chứng từ** (người duyệt ≠ người tạo) được kiểm trong service theo từng chứng từ, không kiểm lúc gán vai. Lúc gán vai chỉ **cảnh báo**. | PA (theo mẫu BR-KK-02) | **Mới** |
| BR-PQ-25 | Sửa vai hoặc sửa việc gán vai có hiệu lực **ngay từ request kế tiếp** của người bị ảnh hưởng. Không hồi tố chứng từ đã tạo (mở rộng BR-PQ-03). Việc AI đang chờ được kiểm lại quyền lúc thực thi. | PA | **Mới** |
| BR-PQ-26 | Mọi thao tác tạo/sửa/ngừng vai và mọi thao tác gán vai ghi AuditLog: ai, lúc nào, tên vai, các ô (`đối tượng.cột`) và phạm vi trước → sau, số người bị ảnh hưởng. Không ghi dữ liệu cá nhân khách. Không ghi được log thì không lưu (theo mẫu BR-PQ-05). | PA | **Mới** |
| BR-PQ-27 | Vai đã từng được gán thì **không xoá cứng**, chỉ ngừng dùng. Chỉ ngừng dùng được khi không còn người **đang làm** giữ vai. AuditLog lưu **tên** vai tại thời điểm ghi, nên đổi tên vai sau này không làm sai nhật ký cũ. | PA (theo tinh thần BR-PQ-10) | **Mới** |
| BR-PQ-28 | Permission mới thêm vào hệ thống: tự vào vai `chu`. Vai sẵn có nhận theo migration của tính năng đó (như hiện nay). Hồ sơ tính năng nào thêm permission phải ghi nó thuộc **ô nào** của ma trận (dòng có sẵn, hoặc dòng mới như "Bài viết"). Vai tự tạo đã tick ô ☐ đó thì nhận luôn. Ô mới, dòng mới, hoặc ô ⚠/🔒 thì **không bao giờ tự bật** cho vai tự tạo; Chủ phải tick. | PA | **Mới** |
| BR-PQ-29 | Phạm vi dòng/cột (Tầng 3) tính theo **ô và phạm vi đã chọn**, không theo tên vai. Khi vừa tick Xem, phạm vi mặc định là "Của tôi". Người không có quyền phạm vi rộng thì nhận **phạm vi hẹp nhất** (đóng khi nghi ngờ). Trang mặc định và menu cũng tính theo quyền. | PA | **Mới** (thay `FULL_SCOPE_GROUPS`, `home_for`, `onlyDelivery`) |
| BR-PQ-30 | Các ô cho xem hoặc sửa **dữ liệu cá nhân khách** (dòng Khách hàng; Xem Giao dịch thanh toán vì có `raw_payload`) là ô ⚠. Chủ gán phải xác nhận cảnh báo. Phạm vi mặc định khi tạo vai mới là **hẹp nhất** (bất biến 9: chỉ lộ cho ai cần). | Bất biến 9 + PA | **Mới** |
| BR-HV-05 | Người **duyệt** phiếu hàng hoàn phải khác người **tạo** phiếu đó. Kiểm trong service, cùng kiểu BR-KK-02. | PA (vì kiêm nhiệm sẽ phổ biến) | **Mới** |
| BR-KK-02 | Người duyệt kiểm kê ≠ người nhập số, kiểm theo chứng từ. | D (10/09) | Giữ (đã có trong code) |
| BR-PQ-10, 11, 14 | Không xoá chứng từ; không ai tạo tay SalesOrder/SalesInvoice; field khoá. Các quyền này không có ô nào trong ma trận (§4.1). | D | Giữ |
| E-17 (spec §13) | "Một người kiêm hai việc: gán nhiều Group, **không tạo role mới**" → "gán nhiều vai; Chủ tự tạo vai mới khi cần". | Duy 28/09 | **Sửa** |

### 6.2 Sàn cứng: cấu hình vai không vượt được

| # | Sàn | Nguồn |
|---|---|---|
| H-1 | Ô 🔒 không vào vai tự tạo (BR-PQ-21). | decisions 10/09 |
| H-2 | Không ai tạo tay SalesOrder/SalesInvoice, không ai xoá chứng từ, không ai sửa AuditLog. Các quyền này không có ô nào trong ma trận. | BR-PQ-06/10/11 |
| H-3 | Giá vốn chỉ lộ khi có dòng "Giá vốn"; lãi lỗ chỉ lộ khi có dòng "Báo cáo lãi lỗ". **Mọi** đường đọc (serializer, dashboard, nhật ký, dòng thời gian, AI, thông báo) đều lọc theo quyền của người nhận. | Bất biến 1 |
| H-4 | Dữ liệu cá nhân khách chỉ lộ theo ô Xem của dòng "Khách hàng" và phạm vi của nó. | Bất biến 9 |
| H-SoD-1 | Kiểm kê: người nhập ≠ người duyệt trên cùng phiếu. | BR-KK-02 |
| H-SoD-2 | Hàng hoàn: người tạo ≠ người duyệt trên cùng phiếu. | BR-HV-05 (mới) |
| H-SoD-3 | Hoàn tiền: nếu sau này `confirm_refund` được mở khỏi 🔒 (Q1) thì bắt buộc **người xác nhận ≠ người tạo phiếu hoàn**, trừ vai `chu`. | PA |
| H-5 | Không tự đổi vai của mình; không ai ngoài Chủ đụng vai `chu`; luôn còn ít nhất một Chủ đang làm. | BR-PQ-17/18 |
| H-6 | Không leo quyền qua việc gán vai (BR-PQ-23). | PA |
| H-7 | Quyền AI không vượt quyền hiện hành của người (tức vai). | Hồ sơ AI H1 |

**Cảnh báo tổ hợp (không chặn, hiện lúc lưu vai hoặc gán vai):** Phiếu kiểm kê có cả Thêm và Duyệt; Hàng hoàn có cả
Thêm và Duyệt; Phiếu hoàn có cả Thêm và xác nhận chuyển tiền (nếu Q1 mở); một vai tự tạo có nhiều ô ⚠ cùng lúc (vd
Khách hàng + Giao dịch thanh toán + Hoá đơn mua).

## 7. Tác động dữ liệu & tích hợp

Chỉ nêu cái gì đổi. Cách làm là việc của Tech Lead (02b).

### 7.1 Dữ liệu
- **Bảng ánh xạ ma trận**: dữ liệu đi theo code. Gồm các dòng (đối tượng, nhãn, nhóm), các ô (cột, nghĩa của ô,
  permission hậu trường, mức ☐/⚠/🔒), quyền kéo theo, dòng nào có phạm vi. Lý do: BR-PQ-20.
- **Vai trò**: có thể dựng trên `auth.Group` hiện có, vì một vai là một tập permission. Cần thêm tên hiển thị, mô tả,
  trạng thái ngừng dùng, cờ vai hệ thống/sẵn có và phạm vi đã chọn. Tech Lead cân nhắc lưu **ô đã tick** hay chỉ lưu
  permission rồi suy ngược ra ô. Việc có thêm model hay field nào phải được lý giải trong 02b
  (bất biến 8).
- **Phạm vi Tầng 3** cần một cách biểu diễn không dựa vào tên nhóm (BR-PQ-29).
- **Permission mới**: `manage_roles`. Có thể thêm permission phạm vi (vd "xem mọi đơn/khách/phiếu giao") để thay
  `FULL_SCOPE_GROUPS`.
- **AuditLog**: không đổi schema. Thêm action `role_create`, `role_update`, `role_archive`.
- **Không đổi**: FK chứng từ → User (decisions 10/09 "cái đắt duy nhất"), `StaffProfile`.

### 7.2 API / màn hình
- **Backend**: API vai trò (danh sách, chi tiết, tạo, sửa, ngừng dùng; kèm xem trước ảnh hưởng); API trả **khung ma
  trận** (dòng, cột, ô nào tick được, ô nào ⚠/🔒, dòng nào có phạm vi) để FE vẽ, không để FE tự giữ luật. `/api/auth/me/` giữ key cũ (`groups`, `group_labels`, `permissions`, `capabilities`, `home`) và có thể
  thêm key (quy ước S47: "chỉ THÊM key"). API nhân viên nhận và trả vai, gồm cả vai tự tạo.
- **Console**: màn mới "Vai trò" trong mục Quản trị (chỉ vai Chủ thấy). Màn chính là **ma trận CRUD** với các nhóm
  thu gọn được. Trên điện thoại hiện mỗi dòng thành một thẻ có 5 ô, không cuộn ngang. `GroupPicker` thành chọn vai
  lấy từ API. `GROUP_LABEL`/`GROUP_HINT` lấy từ dữ liệu. `nav.ts` bỏ `onlyDelivery`/`inGroup(nvGiao)`, chuyển sang
  theo quyền. Màn "Quyền của tôi" hiện ma trận hiệu lực chỉ đọc.
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
  còn đúng nếu Q1 giữ 🔒** cho `close_batch`, `confirm_refund`, `confirm_payment_manual`. Nếu Duy mở một trong ba ra
  vai tự tạo thì AI của người không phải Chủ có thể được giao lệnh vùng đỏ. Khi đó hồ sơ AI phải xét lại công tắc
  vùng đỏ.
- §8 bên đó "chuyển việc tới **Group** có quyền (`chu`, `quan_ly`…)" phải đổi thành "chuyển tới **người có ô quyền**
  tương ứng" (vd người có Duyệt ở dòng Phiếu kiểm kê).
- Màn "AI của tôi" chia tab Thu mua / Bán hàng / CSKH. Nên dùng **cùng cách gom nhóm** với các nhóm dòng của ma trận
  (§4.1) để người dùng chỉ phải quen một cách phân loại.

## 8. Rủi ro Cá Về

| # | Rủi ro | Mức | Giảm thiểu |
|---|---|---|---|
| R1 | **Rò giá vốn qua vai tự tạo.** Một số permission Tầng 1 **tự bản thân đã là dữ liệu giá vốn** chứ không chỉ là cột: `view_purchasecost` (toàn bộ chứng từ chi phí), `view_salesinvoicelinebatch`, có thể cả `view_purchaseinvoice`. Và `view_auditlog` đang lộ `landed_unit_cost` (§3.2). Ma trận CRUD làm rủi ro này **dễ xảy ra hơn** bản danh mục: nếu cài thô kiểu "mỗi model một dòng" thì sẽ có dòng "Chi phí mua" với ô Xem tick được, hoặc dòng "Phân bổ lô hoá đơn". Khi đó bất biến 1 vỡ mà không cần `view_costprice`. | **Critical** | Dòng ma trận là **đối tượng nghiệp vụ**, không phải model. Các permission trên chỉ đi theo dòng 🔒 (§4.4, BR-PQ-21). Hoá đơn mua là ⚠. Sửa §3.2 ngay. Test BR-PQ-13(b) và (c). Test tĩnh: mọi permission của app nghiệp vụ phải có trong bảng ánh xạ (ô, kéo theo, hoặc "không cấp"). Permission không được phân loại thì test đỏ. |
| R1b | Ô "Sửa" dễ bị hiểu là "sửa mọi thứ". Vd tick Sửa ở dòng Lô hàng tưởng là sửa hạn dùng, nhưng thật ra là `change_batch`, đổi được mặt hàng hay kho của lô mà không có AuditLog. | Cao | Ô Sửa Lô hàng là 🔒 (§4.4). Mỗi ô có chú thích nghĩa cụ thể khi rê chuột. |
| R1c | Tầng 2 bị gộp nhầm vào Sửa (cách A/C ở §4.2), làm mất tách vai nhập/duyệt. | Cao | Cột Duyệt riêng (BR-PQ-20a). |
| R2 | Phạm vi Tầng 3 viết theo tên Group. Vá vội bằng cách thêm tên vai mới vào `FULL_SCOPE_GROUPS` thì vai đó thấy **mọi** khách và đơn. | Cao | BR-PQ-29, đóng khi nghi ngờ. Làm ở Đ0 trước khi mở màn tạo vai. |
| R3 | Leo quyền: người có `manage_staff` hoặc `manage_roles` tự cấp cho mình hoặc cho đồng bọn. | Cao | Dòng "Vai trò" và "Nhân viên" là 🔒. BR-PQ-17 (không tự đổi vai của mình). BR-PQ-23. Admin chỉ superuser. |
| R4 | Rò dữ liệu cá nhân khách: vai "CSKH" hoặc "Bán hàng" được tick xem khách toàn bộ mà không cần. | Cao (bất biến 9) | Dòng Khách hàng là ⚠, phạm vi mặc định "Của tôi" (BR-PQ-30). Hồ sơ CSKH quyết phạm vi thật. |
| R5 | Kiêm nhiệm làm gãy tách người: luật hiện chỉ tách bằng quyền (hàng hoàn). | Trung bình | BR-HV-05, H-SoD-3, cảnh báo tổ hợp. |
| R6 | Chuyển đổi làm lệch quyền (ai đó mất quyền hôm sau không làm được việc, hoặc được thêm quyền). | Trung bình | UC-VT-07: dừng nếu không khớp; test ảnh chụp trước = sau. |
| R7 | Quyền mới sau này rơi vào vai tự tạo ngoài ý muốn, hoặc ngược lại không ai nhận nên tính năng mới "biến mất". | Trung bình | BR-PQ-28; mỗi hồ sơ tính năng ghi permission mới thuộc ô nào; test tĩnh ở R1. |
| R8 | Chủ cấu hình quá tay: khoảng 24 dòng × 5 cột, gán nhầm. | Trung bình | Vai sẵn có + nhân bản; ô không có nghĩa thì để trống; nhóm thu gọn; xem trước ảnh hưởng; "Quyền của tôi". |
| R9 | Vai rỗng hoặc vai bị bớt hết quyền → nhân viên đăng nhập vào no-role giữa ca. | Thấp | Xem trước ảnh hưởng nêu tên người mất hết quyền. |
| R10 | Tiền và chứng từ: tính năng này không trực tiếp đổi tiền, tồn hay FEFO. Rủi ro tiền chỉ phát sinh nếu Q1 mở ô 🔒. | — | Q1. |

## 9. Ngoài phạm vi

- **Nhiều vựa trên một hệ thống (multi-tenant).** "Case khác anh có thể yêu cầu gộp lại" được hiểu là cùng một vựa
  (hoặc một bản cài riêng cho vựa khác) tự tổ chức lại vai, không phải nhiều vựa dùng chung dữ liệu (🟡 Q6).
- Chủ tự thêm **dòng hoặc cột** vào ma trận, hoặc tick permission thô. Dòng mới (vd "Bài viết") do tính năng mới
  thêm vào.
- Phân quyền theo từng field trên màn (ngoài cột giá vốn và dữ liệu khách vốn đã khoá).
- Phân quyền theo thời gian (ca, giờ), theo kho, theo mặt hàng. Hiện chỉ có một kho thực tế (🟢 Q13).
- Uỷ quyền tạm thời có hạn ("Quản lý thay Chủ 3 ngày") (🟢 Q14).
- Luồng CSKH (gọi khách, in tem, lấy hàng) và các dòng ma trận mới của nó (vd "Tem giao hàng", "Cuộc gọi xác
  nhận"): hồ sơ riêng.
- Sửa lỗi rò giá vốn qua nhật ký (§3.2): nên đi luồng NHANH riêng, ngay.
- Thực thi phạm vi "NV kho chỉ sửa phiếu nhập của mình trong ngày" (spec §1.6, code chưa có): xác minh riêng
  (🟢 Q12).

## 10. Câu hỏi mở

| # | Mức | Câu hỏi | Phương án | Mặc định PA đề xuất |
|---|---|---|---|---|
| Q1 | 🔴 | **Trong ma trận, các ô khoá Chủ (🔒) có ô nào Chủ được phép mở cho vai tự tạo không?** (Giá vốn · Báo cáo lãi lỗ · Chốt lô · Chi phí mua · Xác nhận đã chuyển tiền hoàn · Xác nhận thanh toán tay · Nhân viên) | **(a)** Không ô nào: tất cả (cộng dòng Vai trò) chỉ vai Chủ có; muốn ai có thì gán thêm vai Chủ cho người đó. Không lật 10/09. **(b)** Mở 4 ô "đổi số lời lỗ" (Giá vốn, Lãi lỗ, Chốt lô, Chi phí mua) thành ⚠: Chủ tick được, có cảnh báo và AuditLog. Giữ 🔒 cho 3 ô "tiền rời túi / nhân sự" (Xác nhận chuyển tiền hoàn, Xác nhận thanh toán tay, Nhân viên) + Vai trò. Lật một phần 10/09; hồ sơ AI phải xét lại §4.3 nếu mở Chốt lô. **(c)** Mở hết thành ⚠ trừ Vai trò. | **(a)** cho V1. Lý do: `confirm_payment_manual` gắn với việc chỉ Lộc xem được sao kê, đây là sự thật vật lý chứ không phải cấu hình. Giá mua là lợi thế đàm phán (spec §1.7). Cách (a) vẫn cho Lộc "gộp" bằng cách gán vai Chủ cho người tin cậy. |
| Q2 | 🔴 | **Bốn Group hiện có sẽ thế nào, và có tạo sẵn vai "Thu mua / Bán hàng / CSKH" không?** | **(a)** `chu` là vai hệ thống; `quan_ly`, `nv_kho`, `nv_giao` thành **vai sẵn có, Chủ sửa được** nhưng không ngừng dùng được. Không tạo sẵn vai mới; Chủ tự tạo "Thu mua / Bán hàng / CSKH" bằng nhân bản. **(b)** Ba vai cũ **khoá làm mẫu** (chỉ nhân bản, không sửa); Chủ làm việc trên vai tự tạo. **(c)** Như (a) và tạo sẵn 3 vai "Thu mua", "Bán hàng", "CSKH" với ô tick BA đề xuất ở §4.7 (chưa gán ai). | **(b) + tạo sẵn 3 vai như (c)**. Mẫu khoá giữ cho test hồi quy và tên nhóm cũ có nghĩa ổn định; ba vai mới cho Lộc điểm xuất phát đúng cách vựa đang chia việc. Nếu Duy muốn đơn giản hơn thì chọn (a). |
| Q3 | 🟡 | Tên hiển thị: "Vai trò" hay "Hồ sơ quyền" (Duy nói "giống tự tạo profile")? | — | "**Vai trò**". Tránh nhầm với "Hồ sơ nhân viên" (`StaffProfile`) đã có. |
| Q4 | 🟡 | Ai được tạo/sửa vai? | (a) Chỉ Chủ; (b) Chủ uỷ `manage_roles` cho Quản lý với trần "không cấp quyền mình không có". | **(a)**. Dòng Vai trò là 🔒. |
| Q5 | 🟡 | Tầng 2 (duyệt, chốt, xác nhận) đặt ở đâu trong ma trận CRUD? | (A) gộp vào Sửa · (B) một cột "Duyệt" riêng, nghĩa theo từng dòng · (C) tự suy từ CRUD | **(B)** (§4.2). (A) và (C) làm mất tách vai nhập/duyệt kiểm kê và ranh giới Chủ ↔ Quản lý. |
| Q5b | 🟡 | 24 dòng và nhãn ở §4.1 có đúng cách Lộc gọi tên giấy tờ không? | — | Dùng §4.1. Duy/Lộc sửa nhãn khi duyệt. |
| Q5c | 🟡 | Ô ⚠ Khách hàng: phạm vi mặc định khi vừa tick Xem? | — | "Của tôi" (hẹp). Vai CSKH phải chủ động chọn "Tất cả". |
| Q6 | 🟡 | "Case khác gộp lại" có nghĩa là bán Cá Về cho vựa khác (nhiều vựa) không? | — | Không. Hiểu là cùng vựa đổi tổ chức, hoặc bản cài riêng. Multi-tenant ngoài phạm vi. |
| Q7 | 🟡 | Người không phải Chủ có `manage_staff` (nếu Q1 mở) gán được những vai nào? | — | Chỉ vai mà mọi quyền trong đó mình cũng có (BR-PQ-23); không đụng vai `chu`. |
| Q8 | 🟡 | Hàng hoàn: người tạo ≠ người duyệt (BR-HV-05). Có ngoại lệ cho Chủ không? | — | Không ngoại lệ cho người thường. Vai `chu` được tự duyệt (Chủ là người chịu lỗ cuối cùng), có ghi AuditLog. |
| Q9 | 🟡 | Có cho lưu vai rỗng không? Vai đã ngừng dùng có được dùng lại không? | — | Cho lưu vai rỗng (để dựng dần). Cho dùng lại vai đã ngừng, có AuditLog. |
| Q10 | 🟡 | Bỏ tick Sửa/Xem dòng Phiếu giao khi người giữ vai còn phiếu Đang giao? | — | Chặn, liệt kê mã phiếu (mở rộng BR-GH-08). |
| Q11 | 🟡 | Hai người sửa cùng vai cùng lúc? | — | Người lưu sau bị từ chối, "vai đã đổi, tải lại". |
| Q12 | 🟢 | Phạm vi "NV kho chỉ sửa phiếu nhập của mình trong ngày" (spec §1.6) chưa có trong code. Làm, hay bỏ khỏi spec? | — | Tech Lead xác minh. Tạm thời dòng Phiếu nhập hàng chỉ có phạm vi "Tất cả". |
| Q13 | 🟢 | Phạm vi theo kho, theo ca. | — | Để sau. |
| Q14 | 🟢 | Uỷ quyền tạm thời có hạn. | — | Để sau; hiện làm bằng gán vai rồi bỏ vai (có AuditLog). |

## 11. Phân đoạn đề xuất (để PO cắt story)

| Đoạn | Nội dung | Điều kiện xong |
|---|---|---|
| **Đ-NHANH (tách riêng, ngay)** | Sửa rò giá vốn qua `/api/audit-logs/` (§3.2) | Test quét `changes` theo quyền người xem |
| **Đ0: tiền đề, không đổi hành vi** | Gỡ phụ thuộc tên Group: phạm vi Tầng 3, trang mặc định, menu tính theo quyền (BR-PQ-29); thêm `manage_roles`; bảng ánh xạ ma trận (ô → permission, kéo theo, phạm vi) + test tĩnh "mọi permission đã được phân loại" (R1); chuyển 4 Group thành vai sẵn có (UC-VT-07) | Test ảnh chụp quyền trước = sau; toàn bộ test hiện có xanh |
| **Đ1: vai tự tạo** | Màn ma trận CRUD và API Vai trò (UC-VT-01, 02, 04), chọn nhiều vai cho nhân viên (UC-VT-03), "Quyền của tôi" dạng ma trận chỉ đọc (UC-VT-05), AuditLog (BR-PQ-26), ô 🔒 (BR-PQ-21), Xem tự bật (BR-PQ-20b) | Test BR-PQ-13 (sửa); Chủ tạo được vai "Thu mua" và gán cho một người |
| **Đ2: tách người & cảnh báo** | BR-HV-05, cảnh báo tổ hợp, xem trước ảnh hưởng, chặn bớt quyền giao khi còn phiếu Đang giao | Test tự tạo – tự duyệt bị chặn |
| **Đ3: nối AI** | Hồ sơ AI: chuyển việc theo ô quyền; tab mảng trong "AI của tôi"; nếu Q1 ≠ (a) thì xét lại công tắc vùng đỏ | Theo hồ sơ AI |
