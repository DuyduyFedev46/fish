"""
P8b Lô 4a (R2, R3): ma trận quyền theo vai KHÔNG đổi sau khi đổi tên Group sang tiếng Anh.

Mã trạng thái dưới đây chụp trên HEAD TRƯỚC khi đổi tên Group (tên cũ `chu`, `quan_ly`, `nv_kho`, `nv_giao`, `cskh`),
bằng đúng các request này. Sau khi đổi tên, mọi ô phải giống hệt: chỉ có tên Group trong `/api/auth/me/` và
trang chủ `home` là khác (kiểm ở test riêng bên dưới). Test dùng hằng `roles.*` nên không phụ thuộc giá trị tên.

Khách ở đây gồm hai loại không thuộc Group nào: người đã đăng nhập không có Group, và ẩn danh (401).
"""
from django.contrib.auth.models import Group
from django.test import TestCase

from apps.accounts import roles
from apps.common.tests.fixtures import client_for, make_user

ROLE_GROUPS = {
    "owner": [roles.OWNER],
    "manager": [roles.MANAGER],
    "warehouse_staff": [roles.WAREHOUSE_STAFF],
    "delivery_staff": [roles.DELIVERY_STAFF],
    "customer_service": [roles.CUSTOMER_SERVICE],
    "no_group": [],
}

# Chụp trước khi đổi tên Group: {"METHOD url": {vai: mã trạng thái}}.
EXPECTED = {
    "GET /api/ai/actions/": {"owner": 200, "manager": 200, "warehouse_staff": 200, "delivery_staff": 200, "customer_service": 200, "no_group": 200, "anonymous": 401},
    "GET /api/ai/my-config/": {"owner": 200, "manager": 200, "warehouse_staff": 200, "delivery_staff": 200, "customer_service": 200, "no_group": 200, "anonymous": 401},
    "GET /api/ai/policy/": {"owner": 200, "manager": 403, "warehouse_staff": 403, "delivery_staff": 403, "customer_service": 403, "no_group": 403, "anonymous": 401},
    "GET /api/audit-logs/": {"owner": 200, "manager": 200, "warehouse_staff": 403, "delivery_staff": 403, "customer_service": 403, "no_group": 403, "anonymous": 401},
    "GET /api/auth/me/": {"owner": 200, "manager": 200, "warehouse_staff": 200, "delivery_staff": 200, "customer_service": 200, "no_group": 200, "anonymous": 401},
    "GET /api/catalog/items/": {"owner": 200, "manager": 200, "warehouse_staff": 200, "delivery_staff": 403, "customer_service": 403, "no_group": 403, "anonymous": 401},
    "GET /api/confirmation/queue/": {"owner": 200, "manager": 200, "warehouse_staff": 403, "delivery_staff": 403, "customer_service": 200, "no_group": 403, "anonymous": 401},
    "GET /api/dashboard/attention/": {"owner": 200, "manager": 200, "warehouse_staff": 200, "delivery_staff": 403, "customer_service": 200, "no_group": 403, "anonymous": 401},
    "GET /api/dashboard/summary/": {"owner": 200, "manager": 200, "warehouse_staff": 200, "delivery_staff": 403, "customer_service": 403, "no_group": 403, "anonymous": 401},
    "GET /api/delivery/notes/": {"owner": 200, "manager": 200, "warehouse_staff": 200, "delivery_staff": 200, "customer_service": 403, "no_group": 403, "anonymous": 401},
    "GET /api/inventory/batches/": {"owner": 200, "manager": 200, "warehouse_staff": 200, "delivery_staff": 403, "customer_service": 403, "no_group": 403, "anonymous": 401},
    "GET /api/inventory/ledger/": {"owner": 200, "manager": 200, "warehouse_staff": 200, "delivery_staff": 403, "customer_service": 403, "no_group": 403, "anonymous": 401},
    "GET /api/purchasing/costs/": {"owner": 200, "manager": 403, "warehouse_staff": 403, "delivery_staff": 403, "customer_service": 403, "no_group": 403, "anonymous": 401},
    "GET /api/purchasing/receipts/": {"owner": 200, "manager": 200, "warehouse_staff": 200, "delivery_staff": 403, "customer_service": 403, "no_group": 403, "anonymous": 401},
    "GET /api/sales/customers/": {"owner": 200, "manager": 200, "warehouse_staff": 403, "delivery_staff": 200, "customer_service": 403, "no_group": 403, "anonymous": 401},
    "GET /api/sales/orders/": {"owner": 200, "manager": 200, "warehouse_staff": 200, "delivery_staff": 200, "customer_service": 200, "no_group": 403, "anonymous": 401},
    "GET /api/sales/refunds/": {"owner": 200, "manager": 200, "warehouse_staff": 403, "delivery_staff": 403, "customer_service": 403, "no_group": 403, "anonymous": 401},
    "GET /api/staff/": {"owner": 200, "manager": 403, "warehouse_staff": 403, "delivery_staff": 403, "customer_service": 403, "no_group": 403, "anonymous": 401},
    "POST /api/confirmation/search/": {"owner": 400, "manager": 400, "warehouse_staff": 403, "delivery_staff": 403, "customer_service": 400, "no_group": 403, "anonymous": 401},
    "POST /api/purchasing/receipts/nhap-lo/": {"owner": 400, "manager": 400, "warehouse_staff": 400, "delivery_staff": 403, "customer_service": 403, "no_group": 403, "anonymous": 401},
    "POST /api/purchasing/receipts/receive-batches/": {"owner": 400, "manager": 400, "warehouse_staff": 400, "delivery_staff": 403, "customer_service": 403, "no_group": 403, "anonymous": 401},
}


class RolePermissionMatrixTests(TestCase):
    def test_status_matrix_is_identical_to_before_group_rename(self):
        clients = {label: client_for(make_user(f"u_{label}", *groups)) for label, groups in ROLE_GROUPS.items()}
        clients["anonymous"] = client_for(None)

        checked = 0
        mismatches = []
        for key, per_role in EXPECTED.items():
            method, url = key.split(" ", 1)
            for label, expected_status in per_role.items():
                client = clients[label]
                response = client.get(url) if method == "GET" else client.post(url, {}, format="json")
                checked += 1
                if response.status_code != expected_status:
                    mismatches.append((key, label, expected_status, response.status_code))
        self.assertGreater(checked, 100, "ma trận phải đếm được nhiều ô kiểm")
        self.assertEqual(mismatches, [])

    def test_every_role_constant_is_an_existing_group_with_permissions(self):
        for name in roles.ALL_ROLES:
            group = Group.objects.get(name=name)
            self.assertGreater(group.permissions.count(), 0, name)

    def test_me_endpoint_reports_the_current_group_name_and_home(self):
        expected_home = {
            roles.OWNER: "dashboard",
            roles.MANAGER: "dashboard",
            roles.WAREHOUSE_STAFF: "dashboard",
            roles.DELIVERY_STAFF: "my-deliveries",
            roles.CUSTOMER_SERVICE: "confirmation-queue",
        }
        for name, home in expected_home.items():
            user = make_user(f"me_{name}", name)
            body = client_for(user).get("/api/auth/me/").json()
            self.assertEqual(body["groups"], [name])
            self.assertEqual(body["home"], home)

    def test_group_names_are_english(self):
        self.assertEqual(
            list(roles.ALL_ROLES),
            ["owner", "manager", "warehouse_staff", "delivery_staff", "customer_service"],
        )
        self.assertEqual(
            sorted(Group.objects.values_list("name", flat=True)),
            sorted(roles.ALL_ROLES),
            "DB chỉ có đúng 5 Group tên tiếng Anh, không còn Group tên cũ",
        )
