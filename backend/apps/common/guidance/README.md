# Khối Hướng dẫn: Tiếp theo · Đã làm (Guidance)

Nằm trong `backend/apps/common/guidance/`, cung cấp khung tất định cho endpoint `GET /api/guidance/<loại>/<id>/` (02b §6.7, DW-03).

## Nguyên tắc:
1. **Không phụ thuộc AI**: Chạy khi `AI_ENABLED=False`, không bao giờ trả 410.
2. **Quyền & Scope**: T1 `view_<model>` + T3 scope giống hệt API chi tiết của chứng từ tương ứng.
3. **Bảo mật**:
   - Bất biến 1: Không rò giá vốn ở bất kỳ trường nào khi người xem thiếu `view_costprice`.
   - Bất biến 9: Không rò PII (tên, SĐT, địa chỉ khách, nội dung chuyển khoản).
   - L-4: Dòng AI trong AuditLog hiện "AI của <tên hiển thị>" kèm mức; trường `config_version` chỉ trả khi người xem có quyền `ai.manage_ai_policy`.
4. **Một nguồn cho ba nơi**:
   - `check_*` trong service layer.
   - `next_steps` của guidance.
   - `available_actions` của serializer tính lại từ `[s.key for s in next_steps if s.allowed]`.
