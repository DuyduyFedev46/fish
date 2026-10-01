# Q1-PII: xác minh phạm vi dữ liệu cá nhân khách theo Group

Người làm: Tech Lead, ngày 01/10/2026. Phạm vi: chỉ đọc code và chạy test tạm ở scratchpad. Không sửa code, không để test trong repo.
Nguồn phát hiện: QA P8b Lô 1, dòng Q1-PII ở cuối `bao-cao-tong.md`.

## 1. Kết luận ngắn

| Phần của Q1-PII | Kết luận | Mức |
|---|---|---|
| `nv_giao` thấy SĐT/tên/địa chỉ của khách **ngoài** phiếu được giao (orders, customers) | **Bác bỏ.** Chạy thật: `nv_giao` X chỉ thấy khách A (phiếu của X). Khách B (phiếu chưa gán) và khách C (phiếu gán Y) trả 404 ở chi tiết và không có trong danh sách | Không phải lỗi |
| `nv_giao` vẫn thấy khách sau khi phiếu đã giao xong, không giới hạn thời gian | **Xác nhận**, đúng chữ spec nhưng rộng hơn tinh thần "thu tối thiểu" | Low, chờ Duy (🔴 Q-3) |
| `nv_kho` thấy tên, **SĐT đầy đủ**, địa chỉ của **mọi** khách ở `/api/sales/orders/` và `/api/sales/customers/`, cùng tên và địa chỉ ở `/api/delivery/notes/` | **Xác nhận hành vi, nhưng đây là đúng thiết kế đã chốt** (spec §1.4: `nv_kho` có R trên Customer và SalesOrder; 02b CSKH mục 7: "Chủ/Quản lý/NV kho giữ phạm vi đầy đủ như hiện nay"). Thiết kế này lệch với bất biến 9 ("chỉ lộ cho ai cần"), vì bất biến 9 được thêm sau | **Medium** (lộ quá mức cho nhân viên nội bộ có tài khoản, không lộ ra ngoài). Không phải Critical. Cần Duy quyết (🔴 Q-1, Q-2) |

Không thấy đường nào để người ngoài hệ thống hoặc Group không có quyền lấy được dữ liệu cá nhân. Tầng 3 của `nv_giao` và `cskh` chạy đúng.

## 2. Phân quyền thật trong code

| Group | `view_customer` | `view_salesorder` | `view_deliverynote` | Phạm vi dòng (Tầng 3) | Nguồn |
|---|---|---|---|---|---|
| `chu` | có | có | có | toàn bộ | `accounts/migrations/0002` (mọi perm của app nghiệp vụ) |
| `quan_ly` | có (cru) | có | có (cru) | toàn bộ | `0002` QUAN_LY |
| `nv_kho` | có (r) | có | có (cru) | **toàn bộ** (`FULL_SCOPE_GROUPS`, `backend/apps/common/api.py:112`) | `0002` NV_KHO |
| `nv_giao` | có (r) | có | có (ru) | chỉ phiếu `assigned_to = user` | `0002` NV_GIAO |
| `cskh` | **không** | có | **không** | đơn của phiếu CONFIRMING đang mở, hoặc phiếu mình gọi trong 7 ngày (BR-GH-18) | `0011_seed_group_cskh` |

Chỗ lọc dòng:
- `backend/apps/sales/orders/scope.py:19-35` (`scope_orders_for`): nhóm full scope thì trả hết. `nv_giao` lọc `invoice__delivery_notes__assigned_to=user`, `cskh` lọc thêm `customer_service_note_q`.
- `backend/apps/sales/customers/api.py:15-22`: nhóm full scope thì trả hết, còn lại lọc `orders__invoice__delivery_notes__assigned_to=user`.
- `backend/apps/delivery/api.py:53-58`: nhóm full scope thì trả hết, còn lại lọc `assigned_to=user`.

Field dữ liệu cá nhân mà serializer trả ra (đều khai tường minh, không dùng `__all__`, nhưng **không tách theo Group**):
- `SalesOrderListSerializer` (`backend/apps/sales/orders/serializers.py:35-36`): `customer_name`, `customer_phone` (SĐT đầy đủ).
- `SalesOrderDetailSerializer.get_customer` (`serializers.py:106-110`): `name`, `phone`, `address`.
- `CustomerSerializer` (`backend/apps/sales/customers/serializers.py:10`): `phone`, `name`, `default_address`, `note`.
- `DeliveryNoteSerializer` (`backend/apps/delivery/serializers.py:25-26, 110-122`): `customer_name`, `address`. Không có SĐT.
- Tem giao hàng (`backend/apps/delivery/labels/services.py:62-65`) in tên, **SĐT đã che** (`mask_phone`) và địa chỉ. Nghĩa là thiết kế tem đã coi NV kho không cần SĐT đầy đủ, nhưng API đơn và khách vẫn đưa SĐT đầy đủ cho NV kho.

## 3. Kết quả chạy thật

Dữ liệu giả: khách A (đơn DH-A, phiếu gán `nv_giao` X), khách B (đơn DH-B, phiếu chưa gán, địa chỉ riêng), khách C (đơn DH-C, phiếu gán `nv_giao` Y). Fixture `apps/common/tests/fixtures.py::make_order_with_note`, SQLite test DB. File probe nằm ở scratchpad (`q1-pii/q1_pii_probe.py`), không nằm trong repo. Lệnh chạy: `PYTHONPATH=<scratchpad>/q1-pii .venv/bin/python manage.py test q1_pii_probe`, kết quả 1 test OK.

"Thấy" nghĩa là chuỗi SĐT/tên/địa chỉ giả xuất hiện trong body response.

| Người gọi | `GET /api/sales/orders/` | `/orders/<B>/` | `GET /api/sales/customers/` | `/customers/<B>/` | `GET /api/delivery/notes/` | `/notes/<B>/` |
|---|---|---|---|---|---|---|
| `nv_giao` X | 200, chỉ A (tên, SĐT) | **404** | 200, chỉ A | **404** | 200, chỉ A (tên) | **404** |
| `nv_kho` | 200, A, B, C (tên, SĐT) | 200 (tên, SĐT, địa chỉ B) | 200, A, B, C (SĐT, tên, địa chỉ) | 200 | 200, A, B (tên, địa chỉ) | 200 |
| `nv_kho` + `nv_giao` | như `nv_kho` (hợp quyền, BR-PQ-09) | 200 | như `nv_kho` | 200 | như `nv_kho` | 200 |
| `cskh` | 200, rỗng (không có phiếu CONFIRMING) | 404 | **403** | 403 | **403** | 403 |
| `quan_ly` | 200, A, B, C | 200 | 200, A, B, C | 200 | 200, A, B | 200 |
| `chu` | 200, A, B, C | 200 | 200, A, B, C | 200 | 200, A, B | 200 |

Kiểm thêm:
- `nv_giao` X gọi `?q=<SĐT của B>` trên orders: 200, rỗng. Tìm theo SĐT không vượt được phạm vi.
- `nv_giao` X gọi `PATCH /api/sales/customers/<C>/`: 403.
- Phiếu A chuyển sang Y: X không còn thấy đơn A. Phạm vi đi theo người đang được gán.
- Phiếu A đã `DELIVERED`: X **vẫn** thấy khách A (SĐT, tên) mãi mãi.
- `nv_giao` gọi `/api/dashboard/summary/`: 403. Với `nv_kho` thì dashboard vẫn trả tên khách và 4 số cuối SĐT, đây là lỗi đã ghi ở BM-02 và `review-bao-mat-du-lieu.md` dòng 79, không tính lại ở đây.
- `/api/sales/customers/` bỏ qua `?search=`, trả cả danh bạ khách (phân trang mặc định 50 dòng).

Test hiện có trong repo đã phủ phạm vi `nv_giao`: `apps/common/tests/test_s5_scope_nv_giao.py`, `apps/sales/orders/tests/test_p8_scope.py`, `test_s10_api.py:299`. Chưa có test nào khẳng định `nv_kho` **không** thấy SĐT đầy đủ, vì thiết kế hiện tại cho phép.

## 4. Đối chiếu tài liệu nghiệp vụ

| Nguồn | Nội dung | Nhận xét |
|---|---|---|
| spec §1.3 (PA) | `nv_kho` làm việc "Nhập lô, soạn hàng, kiểm kê". `nv_giao` "chỉ thấy đơn được gán cho mình" | Việc của NV kho không cần gọi khách |
| spec §1.4 (PA) | `nv_kho`: Customer **R**, SalesOrder **R**, DeliveryNote CRU. `nv_giao`: Customer R\*, SalesOrder R\* | Code làm đúng bảng này. Đây là giả định thiết kế (PA), được phép đề xuất đổi |
| spec §1.6 | `nv_giao` trên SalesOrder/Customer: "chỉ đơn/khách thuộc phiếu giao được gán". Không nói giới hạn thời gian | Code đúng |
| decisions.md dòng 123, 149 | Chỉ chốt "4 Group cộng dồn, 3 tầng". Không chốt NV kho được xem dữ liệu cá nhân | Đổi phạm vi của NV kho **không** lật quyết định nào |
| 02b CSKH (28/09) mục 7 | "Chủ/Quản lý/NV kho giữ phạm vi đầy đủ như hiện nay" | Giữ nguyên hiện trạng, không phải quyết định mới có cân nhắc dữ liệu cá nhân |
| 01-analysis CSKH dòng 95, UC-CS-8 | NV kho: "xem phiếu giao, in lại tem", cầm tem vào kho lấy hàng | NV kho cần mã phiếu, dòng hàng, có thể cần tên và địa chỉ (trùng nội dung tem). **Không** thấy chỗ nào cần SĐT đầy đủ hoặc danh bạ khách |
| Bất biến 9 (skill) | "Trong ERP, chỉ lộ cho ai cần (Tầng 3)" | Hiện trạng NV kho lệch với bất biến này |
| ERP console | Không có màn "Khách hàng", nên `/api/sales/customers/` không được FE gọi. AI cấm `sales.customer` (`apps/ai/policy/rules.py:42`). Màn "Đơn & tiền" hiện với NV kho (`erp-console/shared/lib/nav.ts:133`) và hiển thị SĐT đầy đủ | Bỏ `view_customer` của NV kho không làm hỏng màn nào |

## 5. Đề xuất sửa (chưa làm, chờ Duy trả lời mục 6)

Đề xuất A, rẻ và không đổi màn hình nào. Có thể làm ngay nếu Duy đồng ý Q-1:
1. Data migration mới `backend/apps/accounts/migrations/0012_revoke_customer_view_warehouse_staff.py`: `permissions.remove(sales.view_customer)` khỏi Group `nv_kho`. Làm theo mẫu `0011`, gọi `.remove` chứ không `.set`, có hàm `reverse`.
2. `backend/apps/sales/customers/api.py:15-22`: lọc theo quyền thật, không theo `has_full_delivery_scope`. `nv_kho` + `nv_giao` kiêm nhiệm vẫn thấy khách của phiếu mình nhờ perm của `nv_giao`.
3. Test mới (chuyển probe thành test thật) `backend/apps/common/tests/test_pii_scope_matrix.py`: ma trận 5 Group × 3 endpoint, gồm cả kiêm nhiệm `nv_kho+nv_giao`. Assert từng chuỗi dữ liệu cá nhân giả có hoặc không có. Test này đáp ứng BR-PQ-13 cho dữ liệu cá nhân.

Đề xuất B, cần Duy quyết Q-2. Che SĐT với NV kho trên màn Đơn:
1. Thêm hàm `can_view_full_customer_pii(user)` vào `backend/apps/common/api.py` (cạnh `has_full_delivery_scope`, dòng 115). Trả True cho superuser, `chu`, `quan_ly`. Với các nhóm còn lại, phạm vi dòng đã giới hạn sẵn nên SĐT của phiếu được gán vẫn hiện đầy đủ.
2. `backend/apps/sales/orders/serializers.py:36` (`customer_phone`) và `:106-110` (`get_customer`): nếu user chỉ có phạm vi full nhờ `nv_kho` và đơn **không** thuộc phiếu gán cho user, thì trả `mask_phone(...)` và bỏ `address`. Dùng `apps/common/pii.py:24`, giống cách tem đang làm.
3. `backend/apps/sales/orders/api.py:124`: với NV kho, tìm theo SĐT vẫn chạy (vì lọc trên server), chỉ phần hiển thị bị che. Chấp nhận được.
4. `DeliveryNoteSerializer` (`delivery/serializers.py:25-26`): giữ tên và địa chỉ cho NV kho, vì trùng nội dung tem mà NV kho vẫn in (BR-GH-10).
5. FE `erp-console/features/orders/components/*`: hiện SĐT đã che, bỏ link `tel:` khi SĐT bị che (`RefundView.tsx:73-79` và bảng đơn).

Đề xuất C, cần Duy quyết Q-3. Giới hạn thời gian cho `nv_giao`: trong `scope.py:24` và `customers/api.py:22`, chỉ tính phiếu chưa xong hoặc `completed_at` trong N ngày. N lấy từ setting mới `DELIVERY_PII_RECENT_DAYS`, đặt mặc định 7 cho giống `CSKH_PII_RECENT_DAYS`. Thêm test cho phiếu DELIVERED quá N ngày thì trả 404.

Đề xuất D, Low, làm kèm A. `CustomerSerializer` trả `note` (ghi chú nội bộ) và `default_address` cho `nv_giao`, trong khi người giao chỉ cần SĐT và địa chỉ **của đơn** (đã có trong chi tiết đơn). Nên tách serializer: `nv_giao` chỉ nhận `id, name, phone`, hoặc bỏ luôn `view_customer` của `nv_giao` nếu FE giao hàng không gọi `/api/sales/customers/` (đã kiểm: ERP không gọi).

Sau khi sửa, phải chạy: `manage.py test apps.common apps.sales apps.delivery`, `makemigrations --check --dry-run`, `python3 scripts/check_naming.py`.

## 6. Câu hỏi cho Duy

- 🔴 **Q-1.** NV kho có cần xem **danh bạ khách** (`/api/sales/customers/`: SĐT, địa chỉ mặc định, ghi chú của mọi khách) không? ERP không có màn này. Đề xuất: **không**, thu quyền theo đề xuất A.
- 🔴 **Q-2.** NV kho có cần **SĐT đầy đủ** của mọi đơn ở màn "Đơn & tiền" không? Tem đã che SĐT, cho thấy thiết kế coi NV kho không cần. Đề xuất: che SĐT, giữ tên và địa chỉ để soạn hàng (đề xuất B). Nếu vựa thực tế để NV kho gọi khách, thì nên gán thêm Group `cskh` cho người đó, vì phạm vi của `cskh` đã giới hạn theo BR-GH-18.
- 🟡 **Q-3.** NV giao được xem dữ liệu khách của phiếu đã giao xong trong bao lâu? Hiện tại là mãi mãi. Đề xuất 7 ngày (để xử lý khiếu nại, giao lại), sau đó trả 404.
- Việc đổi phạm vi của NV kho là đổi giả định PA ở spec §1.4, **không** lật `decisions.md`. Khi Duy chốt, BA cập nhật bảng §1.4/§1.6 và thêm mã rule mới **BR-PQ-15** (phạm vi dữ liệu cá nhân theo Group).

## Quyết định Duy 01/10
- Q-1: NV kho **không cần** danh bạ khách → thu `view_customer` của `nv_kho` (migration quyền) + test ma trận.
- Q-2: NV kho **giữ SĐT đầy đủ** ở màn Đơn hàng/phiếu giao (không che).
- Q-3: NV giao xem dữ liệu khách của phiếu **đã giao xong** trong **7 ngày** (setting cấu hình được), sau đó ẩn.
- Làm thành lô sửa riêng ngay sau P8b Lô 3 (trước P8b Lô 4, vì cùng có migration `accounts/`).
