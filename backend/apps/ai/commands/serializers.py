"""
Serialize CommandSpec cho catalog — field tường minh theo contract 02b mục 3 (S01).

`context_fields` và `handler` là nội bộ BE, KHÔNG trả ra catalog (giảm mặt lộ thông tin).
"""
from .registry import CommandSpec


def command_item(spec: CommandSpec) -> dict:
    return {
        "name": spec.name,
        "channel": spec.channel,
        "sensitivity": spec.sensitivity,
        "min_permissions": list(spec.min_permissions),
        "input_schema": spec.input_schema,
        "output_schema": spec.output_schema,
        "status": spec.status,
        "description": spec.description,
        "needs_confirmation": spec.needs_confirmation,
        "forbidden_channel": spec.forbidden_channel,
    }
