"""
Sinh JSON schema từ DRF Serializer (Spike DW-01, 02b §2.4, §13 S-4).
"""
import json
from decimal import Decimal
from rest_framework import serializers


def serializer_to_schema(serializer_cls_or_instance):
    """
    Chuyển đổi một serializer DRF thành JSON schema đơn giản cho LLM.
    Trả về (schema_dict, unsupported_fields).
    """
    if serializer_cls_or_instance is None:
        return None, []

    if isinstance(serializer_cls_or_instance, type) and issubclass(serializer_cls_or_instance, serializers.BaseSerializer):
        instance = serializer_cls_or_instance()
    elif isinstance(serializer_cls_or_instance, serializers.BaseSerializer):
        instance = serializer_cls_or_instance
    else:
        return None, []

    unsupported = []
    properties = {}
    required_fields = []

    fields = getattr(instance, "fields", {})
    for name, field in fields.items():
        if field.read_only:
            continue

        if field.required:
            required_fields.append(name)

        field_schema, is_supported = _field_to_schema(field)
        if not is_supported:
            unsupported.append(f"{name} ({field.__class__.__name__})")
        properties[name] = field_schema

    schema = {
        "type": "object",
        "properties": properties,
    }
    if required_fields:
        schema["required"] = required_fields

    return schema, unsupported


def _field_to_schema(field):
    """Chuyển đổi 1 field DRF sang schema."""
    desc = field.help_text or getattr(field, "label", "") or ""
    schema = {}
    if desc:
        schema["description"] = str(desc)

    if isinstance(field, serializers.BooleanField):
        schema["type"] = "boolean"
        return schema, True

    if isinstance(field, serializers.IntegerField):
        schema["type"] = "integer"
        if getattr(field, "min_value", None) is not None:
            schema["minimum"] = field.min_value
        if getattr(field, "max_value", None) is not None:
            schema["maximum"] = field.max_value
        return schema, True

    if isinstance(field, (serializers.FloatField, serializers.DecimalField)):
        schema["type"] = "number"
        if getattr(field, "min_value", None) is not None:
            val = field.min_value
            schema["minimum"] = float(val) if isinstance(val, Decimal) else val
        if getattr(field, "max_value", None) is not None:
            val = field.max_value
            schema["maximum"] = float(val) if isinstance(val, Decimal) else val
        return schema, True

    if isinstance(field, serializers.ChoiceField):
        schema["type"] = "string"
        schema["enum"] = list(field.choices.keys())
        return schema, True

    if isinstance(field, (serializers.CharField, serializers.SlugRelatedField, serializers.PrimaryKeyRelatedField, serializers.EmailField, serializers.URLField, serializers.UUIDField)):
        schema["type"] = "string"
        if getattr(field, "max_length", None) is not None:
            schema["maxLength"] = field.max_length
        return schema, True

    if isinstance(field, (serializers.DateField, serializers.DateTimeField)):
        schema["type"] = "string"
        schema["format"] = "date" if isinstance(field, serializers.DateField) else "date-time"
        return schema, True

    if isinstance(field, serializers.ListSerializer):
        sub_schema, supported = serializer_to_schema(field.child)
        schema["type"] = "array"
        schema["items"] = sub_schema or {"type": "object"}
        return schema, supported

    if isinstance(field, serializers.ListField):
        schema["type"] = "array"
        child_schema, supported = _field_to_schema(field.child) if getattr(field, "child", None) else ({"type": "string"}, True)
        schema["items"] = child_schema
        return schema, supported

    if isinstance(field, serializers.BaseSerializer):
        sub_schema, supported = serializer_to_schema(field)
        return sub_schema, supported

    # Fallback cho các field khác
    schema["type"] = "string"
    return schema, False


def estimate_schema_tokens(schema_dict):
    """
    Ước lượng số token của một schema dictionary.
    Theo quy ước: 1 token ~ 4 ký tự JSON minified hoặc 0.75 từ.
    """
    if not schema_dict:
        return 0
    raw_json = json.dumps(schema_dict, ensure_ascii=False, separators=(",", ":"))
    # Ước tính số token: khoảng 3.5 ký tự mỗi token cho JSON cấu trúc
    return max(1, len(raw_json) // 3)
