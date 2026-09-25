"""
Quy ước actor cho service layer.

`actor=None` nghĩa là **Hệ thống** (job huỷ TTL, webhook xác nhận) — AuditLog ghi
với actor = system, không mượn tài khoản người (BR-PQ-07).
"""

SYSTEM = None  # actor=None -> Hệ thống
