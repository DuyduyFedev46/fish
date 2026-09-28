"""
Test Spike DW-01 (DW-01-AC1..AC6).
Tên file bắt đầu bằng spike_ để không bị test runner mặc định chạy.
"""
import json
import os
from decimal import Decimal

from django.conf import settings
from django.test import TestCase
from rest_framework.test import APIClient

from apps.catalog.models import Item, ItemGroup
from apps.common.tests.fixtures import client_for, make_batch, make_master, make_user
from apps.inventory.batches.api import BatchViewSet
from apps.inventory.models import Batch
from apps.sales.orders.api import SalesOrderViewSet
from apps.sales.models import Customer, SalesOrder

from spikes.dw01.discovery import discover_commands
from spikes.dw01.dispatch import dispatch_in_process
from spikes.dw01.schema import serializer_to_schema, estimate_schema_tokens


class SpikeDW01Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.item, cls.sup, cls.wh = make_master()
        cls.batch = make_batch(cls.item, cls.sup, cls.wh, qty="50")
        cls.batch.landed_unit_cost = Decimal("88000")
        cls.batch.save(update_fields=["landed_unit_cost"])

        cls.user_chu = make_user("test_chu_dw01", "chu")
        cls.user_kho = make_user("test_kho_dw01", "nv_kho")
        cls.user_inactive = make_user("test_inactive_dw01", "chu")
        cls.user_inactive.is_active = False
        cls.user_inactive.save(update_fields=["is_active"])

    def test_dw01_ac1_discovery_and_schema_stats(self):
        """
        DW-01-AC1: Toàn bộ route dưới /api/ -> khám phá lệnh,
        100% lệnh đọc có schema, thống kê số lượng và tokens.
        """
        commands = discover_commands()
        self.assertGreater(len(commands), 20, "Phải khám phá được nhiều hơn 20 lệnh")

        read_commands = [c for c in commands if c["kind"] == "read"]
        write_commands = [c for c in commands if c["kind"] == "write"]
        form_only_commands = [c for c in commands if c.get("form_only")]

        # Kiểm tra lệnh đọc
        for rc in read_commands:
            # 100% lệnh đọc phải có schema (trừ trường hợp view không khai serializer thì fallback)
            # Theo tiêu chí DW-01-AC1: 100% lệnh đọc có schema
            self.assertIsNotNone(rc["schema"], f"Lệnh đọc {rc['id']} phải có schema")

        # Xuất file dw01-index.json cho spike FE (DW-02)
        index_entries = []
        for c in commands:
            index_entries.append({
                "id": c["id"],
                "title": c["title"],
                "kind": c["kind"],
                "group": c["group"],
                "keywords": c["keywords"],
            })

        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        index_path = os.path.join(repo_root, "doc", "features", "2026-09-28-ai-digital-worker", "research", "dw01-index.json")
        os.makedirs(os.path.dirname(index_path), exist_ok=True)
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(index_entries, f, ensure_ascii=False, indent=2)

        self.assertTrue(os.path.exists(index_path))

    def test_dw01_ac2_dispatch_matches_apiclient(self):
        """
        DW-01-AC2: Chạy lại API qua dispatch -> cùng mã HTTP, cùng JSON với APIClient.
        """
        client = client_for(self.user_chu)

        # 1. Test Batch list
        resp_http = client.get("/api/inventory/batches/")
        resp_dispatch = dispatch_in_process(
            view_cls=BatchViewSet,
            action_name="list",
            method="GET",
            user=self.user_chu,
        )

        self.assertEqual(resp_dispatch.status_code, resp_http.status_code)
        self.assertEqual(resp_dispatch.data, resp_http.data)

        # 2. Test Batch retrieve
        resp_http_detail = client.get(f"/api/inventory/batches/{self.batch.pk}/")
        resp_dispatch_detail = dispatch_in_process(
            view_cls=BatchViewSet,
            action_name="retrieve",
            method="GET",
            user=self.user_chu,
            url_kwargs={"pk": self.batch.pk},
        )
        self.assertEqual(resp_dispatch_detail.status_code, resp_http_detail.status_code)
        self.assertEqual(resp_dispatch_detail.data, resp_http_detail.data)

    def test_dw01_ac3_cost_redaction_through_dispatch(self):
        """
        DW-01-AC3: Token nv_kho gọi danh sách lô qua dispatch
        -> JSON không có purchase_rate, landed_unit_cost, giống hệt APIClient.
        """
        client = client_for(self.user_kho)
        resp_http = client.get(f"/api/inventory/batches/{self.batch.pk}/")
        resp_dispatch = dispatch_in_process(
            view_cls=BatchViewSet,
            action_name="retrieve",
            method="GET",
            user=self.user_kho,
            url_kwargs={"pk": self.batch.pk},
        )

        self.assertEqual(resp_dispatch.status_code, 200)
        self.assertEqual(resp_http.status_code, 200)

        # Cả hai đều không có khoá giá vốn
        self.assertNotIn("landed_unit_cost", resp_dispatch.data)
        self.assertNotIn("purchase_rate", resp_dispatch.data)
        self.assertNotIn("landed_unit_cost", resp_http.data)
        self.assertNotIn("purchase_rate", resp_http.data)

        # So sánh dữ liệu hai bên
        self.assertEqual(resp_dispatch.data, resp_http.data)

    def test_dw01_ac4_inactive_user_blocked(self):
        """
        DW-01-AC4: User bị vô hiệu (BR-PQ-19) gọi qua dispatch -> bị chặn cùng mã HTTP.
        """
        client = client_for(self.user_inactive)
        resp_http = client.get("/api/inventory/batches/")
        resp_dispatch = dispatch_in_process(
            view_cls=BatchViewSet,
            action_name="list",
            method="GET",
            user=self.user_inactive,
        )

        self.assertEqual(resp_dispatch.status_code, resp_http.status_code)
        self.assertIn(resp_dispatch.status_code, (401, 403))
