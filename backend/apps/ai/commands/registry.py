"""
Command registry — danh mục lệnh nghiệp vụ dùng chung (S01).

Registry bằng code, không bảng DB (ADR 2.5 / V4 — 02b-tech-design mục 2.1). Mọi kênh
(UI/Admin/AI) dùng chung một bộ mô tả; catalog lọc theo `min_permissions` (BR-AI-04).

Danh mục 14 lệnh khởi đầu theo 02b Phụ lục B (+ 02-stories S01 ghi chú kỹ thuật):
- 12 lệnh active (đã có service tương ứng), 2 draft (`kiem_ke`, `cap_nhat_giao` — chờ
  S34/S17 của hồ sơ khác hoàn thành).
- Lệch D8: `xac_nhan_hoan`/`xac_nhan_thanh_toan_tay` nhãn `local`, vẫn `forbidden_channel="ai"`
  (S01-AC4 — BR-AI-07).
- Lệch D6: mọi lệnh có `description` tiếng Việt cho intent-classify + hiển thị.
- `handler` nối service hiện có ở S02 (Lô 2) — Lô 1 chỉ khai danh mục + catalog.
"""
from dataclasses import dataclass
from typing import Optional

# Khoá cấm tuyệt đối trong context_fields (BR-AI-09, bất biến 9) — dữ liệu cá nhân khách.
PII_FORBIDDEN_KEYS = frozenset({
    "customer_name", "customer", "phone", "delivery_address", "address", "email",
})

CHANNEL_LOCAL = "local"
CHANNEL_CLOUD = "cloud"

SENSITIVITY_CAO = "cao"
SENSITIVITY_TRUNG_BINH = "trung_binh"
SENSITIVITY_THAP = "thap"

STATUS_ACTIVE = "active"
STATUS_DRAFT = "draft"

FORBIDDEN_AI = "ai"


@dataclass(frozen=True)
class CommandSpec:
    """Mô tả một lệnh nghiệp vụ (6 trường ADR 2.5 + trường mở rộng — 02b mục 2.1)."""

    name: str
    channel: str                     # "local" | "cloud" — router tĩnh (BR-AI-02)
    sensitivity: str                 # "cao" | "trung_binh" | "thap" (BR-AI-03)
    min_permissions: tuple           # app_label.codename — user phải có TẤT CẢ (AND)
    input_schema: dict               # JSON Schema validate args (BR-AI-01)
    output_schema: dict              # JSON Schema mô tả result
    description: str = ""            # tiếng Việt, 1–2 dòng (lệch D6)
    status: str = STATUS_DRAFT       # mặc định an toàn: draft chưa lộ ra catalog
    needs_confirmation: bool = False
    forbidden_channel: Optional[str] = None   # "ai" | None (BR-AI-07)
    context_fields: Optional[dict] = None     # allowlist cho context builder (S06)
    handler: Optional[callable] = None        # nối service ở S02


def _line(item_id="integer", quantity="number", rate="number"):
    return {
        "type": "object",
        "required": ["item_id", "quantity", "purchase_rate"],
        "properties": {
            "item_id": {"type": item_id},
            "quantity": {"type": quantity, "exclusiveMinimum": 0},
            "unit": {"type": "string"},
            "purchase_rate": {"type": rate, "minimum": 0},
            "batch_no": {"type": ["string", "null"]},
            "shelf_life_days": {"type": ["integer", "null"]},
            "expiry_date": {"type": ["string", "null"]},
        },
    }


def _object_schema(*, required=(), **props):
    schema = {"type": "object", "properties": props}
    if required:
        schema["required"] = list(required)
    return schema


# Context fields (chỉ lệnh tra cứu — 02b mục 5.1): allowlist default-deny, không PII (BR-AI-09).
_TRA_TON_CONTEXT = {
    "item": ["code", "name", "unit"],
    "batches": ["code", "status", "qty", "unit", "expiry_date", "warehouse"],
}
# tra_lo = tra_ton + giá vốn — nhưng builder chỉ trả 2 field này khi user có view_costprice (S06).
_TRA_LO_CONTEXT = {
    "item": ["code", "name", "unit"],
    "batches": ["code", "status", "qty", "unit", "expiry_date", "warehouse",
                "purchase_rate", "landed_unit_cost"],
}
# tra_don: chỉ mã đơn, ngày, trạng thái, tổng tiền, dòng hàng — KHÔNG tên/SĐT/địa chỉ.
_TRA_DON_CONTEXT = {
    "order": ["code", "created_at", "status", "total_amount"],
    "lines": ["item_code", "item_name", "quantity", "unit"],
}


SPECS = [
    CommandSpec(
        name="nhap_lo",
        channel=CHANNEL_LOCAL, sensitivity=SENSITIVITY_CAO,
        min_permissions=("purchasing.add_purchasereceipt",),
        input_schema=_object_schema(
            supplier_id={"type": "integer"},
            received_date={"type": ["string", "null"]},
            warehouse_id={"type": ["integer", "null"]},
            lines={"type": "array", "minItems": 1, "items": _line()},
        ),
        output_schema=_object_schema(
            receipt_id={"type": "integer"},
            status={"type": "string"},
            batches={"type": "array"},
        ),
        description="Nhập lô mua tại cảng — mỗi dòng sinh một lô.",
        status=STATUS_ACTIVE, needs_confirmation=True,
    ),
    CommandSpec(
        name="tra_ton",
        channel=CHANNEL_LOCAL, sensitivity=SENSITIVITY_TRUNG_BINH,
        min_permissions=("inventory.view_batch",),
        input_schema=_object_schema(ma_hang={"type": "string"}),
        output_schema=_object_schema(ma_hang={"type": "string"}, batches={"type": "array"}),
        description="Tra cứu tồn kho một mặt hàng theo lô (số kg, hạn dùng, kho).",
        status=STATUS_ACTIVE,
        context_fields=_TRA_TON_CONTEXT,
    ),
    CommandSpec(
        name="tra_lo",
        channel=CHANNEL_LOCAL, sensitivity=SENSITIVITY_CAO,
        min_permissions=("inventory.view_batch",),
        input_schema=_object_schema(ma_lo={"type": "string"}),
        output_schema=_object_schema(ma_lo={"type": "string"}, batch={"type": "object"}),
        description="Tra cứu chi tiết một lô — kèm giá vốn khi người dùng có quyền xem.",
        status=STATUS_ACTIVE,
        context_fields=_TRA_LO_CONTEXT,
    ),
    CommandSpec(
        name="tra_hang",
        channel=CHANNEL_LOCAL, sensitivity=SENSITIVITY_THAP,
        min_permissions=("catalog.view_item",),
        input_schema=_object_schema(ma_hang={"type": "string"}),
        output_schema=_object_schema(ma_hang={"type": "string"}, item={"type": "object"}),
        description="Tra cứu mặt hàng (mã, tên, đơn vị, giá bán hiện hành).",
        status=STATUS_ACTIVE,
        context_fields={"item": ["code", "name", "unit", "current_price"]},
    ),
    CommandSpec(
        name="tra_don",
        channel=CHANNEL_LOCAL, sensitivity=SENSITIVITY_TRUNG_BINH,
        min_permissions=("sales.view_salesorder",),
        input_schema=_object_schema(ma_don={"type": "string"}),
        output_schema=_object_schema(ma_don={"type": "string"}, order={"type": "object"}),
        description="Tra cứu đơn hàng theo mã — không bao giờ kèm tên/SĐT/địa chỉ khách.",
        status=STATUS_ACTIVE,
        context_fields=_TRA_DON_CONTEXT,
    ),
    CommandSpec(
        name="bao_cao_ton_kho",
        channel=CHANNEL_CLOUD, sensitivity=SENSITIVITY_THAP,
        min_permissions=("reports.view_dashboard",),
        input_schema=_object_schema(),
        output_schema=_object_schema(text={"type": "string"}),
        description="Báo cáo tồn kho tổng hợp (dữ liệu gộp) — chạy trên cloud.",
        status=STATUS_ACTIVE,
    ),
    CommandSpec(
        name="bao_cao_lo",
        channel=CHANNEL_CLOUD, sensitivity=SENSITIVITY_CAO,
        min_permissions=("reports.view_profitreport",),
        input_schema=_object_schema(ma_lo={"type": "string"}),
        output_schema=_object_schema(text={"type": "string"}),
        description="Báo cáo lãi lỗ theo lô (giá vốn) — chỉ Chủ có quyền.",
        status=STATUS_ACTIVE,
    ),
    CommandSpec(
        name="bao_cao_ky",
        channel=CHANNEL_CLOUD, sensitivity=SENSITIVITY_CAO,
        min_permissions=("reports.view_profitreport",),
        input_schema=_object_schema(
            tu_ngay={"type": "string"}, den_ngay={"type": "string"},
        ),
        output_schema=_object_schema(text={"type": "string"}),
        description="Báo cáo lãi lỗ theo kỳ — chỉ Chủ có quyền.",
        status=STATUS_ACTIVE,
    ),
    CommandSpec(
        name="chot_lo",
        channel=CHANNEL_LOCAL, sensitivity=SENSITIVITY_CAO,
        min_permissions=("inventory.close_batch",),
        input_schema=_object_schema(
            batch_id={"type": "integer"},
            required=["batch_id"],
        ),
        output_schema=_object_schema(status={"type": "string"}),
        description="Chốt lô (đông cứng lãi/lỗ) — cấm kênh AI.",
        status=STATUS_ACTIVE,
        forbidden_channel=FORBIDDEN_AI,
    ),
    CommandSpec(
        name="tao_phieu_hoan",
        channel=CHANNEL_LOCAL, sensitivity=SENSITIVITY_CAO,
        min_permissions=("sales.create_refund",),
        input_schema=_object_schema(
            invoice_id={"type": "integer"},
            amount={"type": "number", "exclusiveMinimum": 0},
            reason={"type": "string"},
            required=["invoice_id", "amount"],
        ),
        output_schema=_object_schema(refund_id={"type": "integer"}, status={"type": "string"}),
        description="Tạo phiếu hoàn tiền cho đơn đã thanh toán.",
        status=STATUS_ACTIVE, needs_confirmation=True,
    ),
    CommandSpec(
        name="xac_nhan_hoan",
        channel=CHANNEL_LOCAL, sensitivity=SENSITIVITY_CAO,  # D8: local, vẫn cấm kênh AI
        min_permissions=("sales.confirm_refund",),
        input_schema=_object_schema(
            refund_id={"type": "integer"},
            bank_txn_ref={"type": "string"},
            required=["refund_id", "bank_txn_ref"],
        ),
        output_schema=_object_schema(status={"type": "string"}),
        description="Xác nhận đã chuyển khoản hoàn tiền — cấm kênh AI.",
        status=STATUS_ACTIVE,
        forbidden_channel=FORBIDDEN_AI,
    ),
    CommandSpec(
        name="xac_nhan_thanh_toan_tay",
        channel=CHANNEL_LOCAL, sensitivity=SENSITIVITY_CAO,  # D8: local, vẫn cấm kênh AI
        min_permissions=("sales.confirm_payment_manual",),
        input_schema=_object_schema(
            order_id={"type": "integer"},
            bank_txn_id={"type": "string"},
            required=["order_id"],
        ),
        output_schema=_object_schema(status={"type": "string"}),
        description="Xác nhận khách đã chuyển khoản (khớp giao dịch tay) — cấm kênh AI.",
        status=STATUS_ACTIVE,
        forbidden_channel=FORBIDDEN_AI,
    ),
    CommandSpec(
        name="kiem_ke",
        channel=CHANNEL_LOCAL, sensitivity=SENSITIVITY_TRUNG_BINH,
        min_permissions=("inventory.add_stockreconciliation",),
        input_schema=_object_schema(),
        output_schema=_object_schema(),
        description="Kiểm kê kho (S34 của hồ sơ khác) — chưa có màn hình, đang bản nháp.",
        status=STATUS_DRAFT, needs_confirmation=True,
    ),
    CommandSpec(
        name="cap_nhat_giao",
        channel=CHANNEL_LOCAL, sensitivity=SENSITIVITY_TRUNG_BINH,
        min_permissions=("delivery.change_deliverynote",),
        input_schema=_object_schema(),
        output_schema=_object_schema(),
        description="Cập nhật trạng thái giao hàng (S17 giao hàng) — chưa có màn hình, đang bản nháp.",
        status=STATUS_DRAFT,
    ),
]

# name là khoá duy nhất (test bất biến: S01 tên lệnh duy nhất).
COMMANDS: dict = {spec.name: spec for spec in SPECS}


def active_commands_for(user):
    """Lệnh active mà `user` có đủ mọi quyền tối thiểu (AND — BR-AI-04)."""
    return [
        spec for spec in COMMANDS.values()
        if spec.status == STATUS_ACTIVE
        and all(user.has_perm(perm) for perm in spec.min_permissions)
    ]
