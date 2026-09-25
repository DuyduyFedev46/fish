---
name: django-drf-patterns
description: Pattern code backend Cá Về — Django model/migration, service layer, DRF viewset + serializer ẩn giá vốn, custom action Tầng 2, AuditLog, test APITestCase theo từng Group, và FastAPI adapter. Dùng khi viết hoặc sửa bất cứ gì trong backend/ hoặc adapter/.
---

# Django + DRF theo cách của Cá Về

Nguồn tham khảo: `django-expert`, `fastapi-expert` (Jeffallan/claude-skills),
`django-pro`, `fastapi-pro`, `backend-security-coder` (wshobson/agents). Đã rút gọn về
đúng pattern repo đang dùng — **bắt chước code có sẵn trước khi phát minh cái mới**.

## Cấu trúc thư mục — chia theo MODULE TÍNH NĂNG (Duy yêu cầu 2026-09-24)

```
backend/
  README.md                     sơ đồ module + giải thích từng file cấu hình (settings, urls, Dockerfile, requirements…) 1 dòng/file
  config/                       cấu hình Django (settings, urls, api_urls) — không chứa nghiệp vụ
  apps/<domain>/                1 Django app = 1 miền nghiệp vụ (giữ app_label → không đổi migration)
    README.md                   miền này làm gì, quy trình P-0x, BR chính, danh sách module con
    models/                     package: <tinh_nang>.py + __init__.py re-export (Django yêu cầu)
    <tinh_nang>/                module tính năng: services.py · api.py · serializers.py · tests/ · README.md
    migrations/ admin.py apps.py
```
Ví dụ `apps/sales/orders/`, `apps/sales/payments/`, `apps/sales/refunds/`;
`apps/accounts/staff/`, `apps/accounts/auth/`; `apps/inventory/batches/`, `.../stocktake/`.
- App nhỏ (1 tính năng) có thể giữ file phẳng, nhưng vẫn phải có README.
- Module tính năng gọi module khác **qua services** của module đó, không đụng thẳng model nội bộ để đổi trạng thái.
- Route tập trung ở `config/api_urls.py`, import view từ `apps/<domain>/<tinh_nang>/api.py`.
- Tách/di chuyển code **không đổi hành vi**: test phải xanh y nguyên trước & sau, `makemigrations --check` sạch.

## Tầng nào làm gì

| Tầng | File | Được làm | Không được làm |
|---|---|---|---|
| Model | `apps/<domain>/models/<tinh_nang>.py` (app nhỏ: `models.py`) | field, `Meta.permissions`, constraint, index | logic nghiệp vụ nhiều bước |
| Service | `apps/<domain>/<tinh_nang>/services.py` | toàn bộ nghiệp vụ, `transaction.atomic`, `select_for_update`, `record_audit`, raise `BusinessError` | đọc `request`, trả `Response` |
| API | `api.py` / `shop_api.py` / `internal_api.py` | parse input, kiểm quyền, gọi service, serialize | viết logic nghiệp vụ |
| Serializer | `serializers.py` | khai field tường minh, `sensitive_fields` | `fields = "__all__"` |
| Route | `config/api_urls.py` | router / path | |

## Service

```python
from django.db import transaction
from apps.common.audit import record_audit
from apps.common.exceptions import BusinessError

@transaction.atomic
def close_batch(*, batch, actor):
    batch = Batch.objects.select_for_update().get(pk=batch.pk)   # khoá dòng khi đổi tồn/trạng thái
    if batch.status != Batch.Status.PUBLISHED:
        raise BusinessError("Chỉ đóng được lô đang bán (BR-LO-0x).")
    old = batch.status
    batch.status = Batch.Status.CLOSED
    batch.save(update_fields=["status"])
    record_audit("close_batch", actor=actor, obj=batch, changes={"status": [old, batch.status]})
    return batch
```
- Tham số keyword-only, `actor=None` = Hệ thống.
- Đụng tồn kho / tiền → `atomic` + `select_for_update`; tiền là `Decimal`.
- Job nền (vd `cancel_expired_orders`) phải **idempotent** — chạy 2 lần không đổi kết quả.

## API + phân quyền 3 tầng

```python
class BatchViewSet(viewsets.ModelViewSet):
    queryset = Batch.objects.select_related("item", "supplier", "warehouse")   # tránh N+1
    serializer_class = BatchSerializer
    permission_classes = [BusinessModelPermissions]      # Tầng 1
    custom_perm_actions = ("publish", "close")

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        require_perm(request.user, "inventory.close_batch")   # Tầng 2
        return Response(self.get_serializer(services.close_batch(batch=self.get_object(), actor=request.user)).data)

    def get_queryset(self):                               # Tầng 3 dòng (khi cần)
        qs = super().get_queryset()
        return qs if self.request.user.has_perm("...") else qs.filter(...)
```

Serializer đụng giá vốn:
```python
class BatchSerializer(CostFieldSerializerMixin, serializers.ModelSerializer):
    sensitive_fields = ("purchase_rate", "landed_unit_cost")
    class Meta:
        model = Batch
        fields = ["id", "item", "qty", "status", "purchase_rate", "landed_unit_cost"]
```
Endpoint Shop công khai (`shop_api.py`) **không bao giờ** dùng serializer back-office.

Quyền Tầng 2 mới → thêm vào `Meta.permissions` + data migration gán Group (theo mẫu
`accounts/migrations/0002`) + cập nhật bảng §1.5 trong spec.

## Migration
- `manage.py makemigrations <app>` rồi **đọc file sinh ra**; không sửa migration đã deploy.
- Không xoá field/model đang có dữ liệu production khi chưa có kế hoạch — hỏi Duy.
- Kiểm `manage.py makemigrations --check --dry-run` sạch trước khi báo xong.

## Test (Django `TestCase` + `APIClient`)

Mỗi endpoint mới cần tối thiểu:
1. Happy path với Group đúng quyền.
2. **403** với Group thiếu quyền (và 401 khi chưa đăng nhập) — dữ liệu không đổi.
3. **Không rò giá vốn**: gọi bằng `nv_kho`/`nv_giao`, assert field nhạy cảm *không có* trong JSON.
4. Lỗi nghiệp vụ → 400 với thông điệp `BusinessError`.
5. Nếu đụng tồn/tiền: trường hợp biên (0, âm, vượt tồn, lô cuối, hai đơn tranh nhau).

```python
self.kho = User.objects.create_user("kho", password="x")
self.kho.groups.add(Group.objects.get(name="nv_kho"))   # Group seed sẵn bởi migration
client = APIClient(); client.force_authenticate(self.kho)
```
Mẫu thật: `apps/inventory/batches/tests/test_api.py` (chống rò giá vốn), `apps/sales/orders/tests/test_services.py`, fixture user theo Group: `apps/common/tests/fixtures.py`.

## FastAPI adapter (`adapter/`)
- Chỉ nhận webhook/bên thứ 3, xác thực chữ ký/token, rồi gọi `/api/internal/...` của
  Django bằng `INTERNAL_SERVICE_TOKEN`. **Không** kết nối DB, không chứa nghiệp vụ.
- Pydantic model cho payload, trả nhanh 2xx sau khi chuyển tiếp; idempotent theo mã giao dịch.
- Test bằng `pytest` (xem `adapter/tests/`).

## Bảo mật (luôn kiểm)
Secret lấy từ env · không `DEBUG=True` ở prod · không raw SQL ghép chuỗi · validate mọi
input · CORS/CSRF chỉ thêm origin cụ thể trong `settings.py`.
