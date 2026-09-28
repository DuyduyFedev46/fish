# Báo cáo Nghiên cứu — Spike DW-01: Sinh Schema từ Serializer và Gọi Lại View trong Tiến Trình

> Người thực hiện: be-dev (Antigravity) · Ngày: 2026-09-28 · Môi trường: Django DRF (Local macOS)

## 1. Mục tiêu và Tiêu chí Đạt
Kiểm chứng tính khả thi của cơ chế tự động khám phá lệnh từ URL resolver, sinh JSON Schema từ Serializer và gọi lại ViewSet/APIView trong cùng một tiến trình (in-process dispatch) với định danh `request.user` thật trước khi triển khai Lô 2.

### Tiêu chí nghiệm thu (DW-01-AC1..AC6):
- **DW-01-AC1 (Khám phá và Schema)**: 100% lệnh đọc có schema; báo cáo đầy đủ số lượng lệnh, số `form_only`, phân bố token. 👉 **ĐẠT**
- **DW-01-AC2 (Dispatch đồng nhất)**: Dispatch trong tiến trình cho cùng mã HTTP, cùng JSON payload và cùng hành vi phân quyền như `APIClient`. 👉 **ĐẠT**
- **DW-01-AC3 (Bảo mật giá vốn)**: Token `nv_kho` gọi qua dispatch không thấy `purchase_rate`, `landed_unit_cost` ở mọi độ sâu. 👉 **ĐẠT**
- **DW-01-AC4 (Chặn user vô hiệu)**: User `is_active=False` (BR-PQ-19) bị chặn cùng mã HTTP (401/403). 👉 **ĐẠT**
- **DW-01-AC5 (Ngân sách token)**: Schema của lệnh phức tạp nhất và `nhap_lo` mẫu ≤ 450 token. 👉 **ĐẠT**
- **DW-01-AC6 (Không rò PII)**: Báo cáo và fixture hoàn toàn dùng dữ liệu giả. 👉 **ĐẠT**

---

## 2. Số liệu Thống kê Khám phá Lệnh (DW-01-AC1)
Duyệt toàn bộ URL resolver dưới `/api/` sau khi áp dụng danh sách chặn tất định theo 02b §3:
- **Tổng số lệnh hợp lệ sau lọc**: **114 lệnh** (khớp với dự báo 110–150 trong thiết kế)
- **Số lệnh đọc (`read`)**: **50 lệnh** (100% lệnh đọc có JSON Schema hợp lệ)
- **Số lệnh ghi (`write`)**: **64 lệnh**
- **Số lệnh ghi dạng `form_only` (chưa có serializer đầu vào)**: **8 lệnh**
  - Danh sách nợ kỹ thuật: các custom action hiện tại đang đọc trực tiếp từ `request.data` (sẽ được chuẩn hoá khai báo `input_serializer` ở Lô 2).
- **Kiểu field chưa hỗ trợ**: **0** (100% các kiểu field DRF thông dụng như Char, Integer, Decimal, Boolean, Choice, SlugRelated, PrimaryKeyRelated, Date, DateTime, List đều được hỗ trợ chuyển đổi).

### Phân bố kích thước Token (`schema_tokens_est`):
- **Tối thiểu**: 11 token (schema rỗng của lệnh đọc không tham số)
- **Tối đa**: 279 token (các action quản lý bảng giá `pricingrule`)
- **Trung bình**: 106.9 token/lệnh
- **Đánh giá**: 100% lệnh có schema nằm dưới trần cứng **450 token** (`AI_SCHEMA_MAX_TOKENS`).

### Schema lệnh `nhap_lo` thử nghiệm:
- Dựng theo serializer mẫu ở 02b §2.5 (`supplier`, `received_date`, `warehouse`, `lines` gồm `item_code`, `qty`, `rate`, `shelf_life_days`):
- Ước lượng kích thước schema: **138 token** (đạt tiêu chí ≤ 450 token).

---

## 3. Đối chiếu ID Lệnh với Phụ lục B
| Lệnh cũ | Lệnh tự sinh phát hiện | Trạng thái / Ghi chú |
|---|---|---|
| `tra_ton` | `inventory.batch.list` | Đã có, schema sẵn sàng (cần thêm `BatchListQuery` ở Lô 2 để lọc) |
| `tra_lo` | `inventory.batch.retrieve` | Đã có, lọc giá vốn tự động theo quyền qua serializer |
| `tra_hang` | `catalog.item.list` / `.retrieve` | Đã có |
| `nhap_lo` | `purchasing.purchasereceipt.nhap_lo` | Cần bổ sung custom action `nhap-lo` ở Lô 4 |

---

## 4. Kết quả Thử nghiệm In-Process Dispatch (DW-01-AC2, AC3, AC4)
Đã chạy bộ test tự động tại `backend/spikes/dw01/spike_test_dw01.py`:
- `test_dw01_ac2_dispatch_matches_apiclient`: Kết quả trả về qua `dispatch_in_process` trên `BatchViewSet` (list và retrieve) hoàn toàn trùng khớp với `APIClient` về mã HTTP (200 OK) và dữ liệu JSON.
- `test_dw01_ac3_cost_redaction_through_dispatch`: Khi gọi với user thuộc nhóm `nv_kho`, response qua dispatch hoàn toàn loại bỏ `purchase_rate` và `landed_unit_cost` (Bất biến 1 được bảo toàn nguyên vẹn).
- `test_dw01_ac4_inactive_user_blocked`: User `is_active=False` bị từ chối truy cập ngay lập tức với mã lỗi HTTP tương ứng (BR-PQ-19).

---

## 5. Kết luận & Đề xuất cho Lô 2
- Hướng tiếp cận "Lệnh tự sinh từ API" và "Gọi lại View trong tiến trình" **hoàn toàn khả thi và an toàn**.
- Đã xuất file chỉ mục lệnh rút gọn `dw01-index.json` gồm 114 lệnh với đầy đủ `id, title, kind, group, keywords` để phục vụ spike FE (DW-02).
- Không có bất kỳ thay đổi nào làm ảnh hưởng đến mã nguồn production hay bộ test hiện có (723 test backend giữ nguyên xanh 100%).
