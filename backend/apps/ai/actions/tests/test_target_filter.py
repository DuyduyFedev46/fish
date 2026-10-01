"""
Lô 2 (R1, 02b §3.8): lọc việc AI theo chứng từ + đếm theo màn.

  GET /api/ai/actions/?target_model=&target_id=&status=PENDING,ESCALATED
  GET /api/ai/actions/counts/?status=PENDING,ESCALATED

Bộ lọc chỉ THU HẸP tập "mine" sẵn có (chủ việc, hoặc việc ESCALATED giao cho nhóm của người xem); không bao giờ
mở rộng. Dữ liệu giả.
"""
import datetime

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts import roles
from apps.ai.models import AiAction
from apps.common.tests.fixtures import client_for, make_user


def make_action(owner, *, target_model="purchasereceipt", target_id="7", status="PENDING", assignee_group="",
                command="purchasing.purchasereceipt.submit"):
    return AiAction.objects.create(
        command=command, kind="write", level="C", status=status, owner=owner,
        target_model=target_model, target_id=target_id, assignee_group=assignee_group,
        expires_at=timezone.now() + datetime.timedelta(minutes=15),
    )


@override_settings(AI_ENABLED=True)
class TargetFilterTests(TestCase):
    URL = "/api/ai/actions/"

    def setUp(self):
        self.owner = make_user("r1_owner", roles.OWNER)
        self.manager = make_user("r1_manager", roles.MANAGER)
        self.warehouse = make_user("r1_kho", roles.WAREHOUSE_STAFF)
        self.courier = make_user("r1_giao", roles.DELIVERY_STAFF)
        self.c_owner = client_for(self.owner)
        self.c_manager = client_for(self.manager)
        self.c_warehouse = client_for(self.warehouse)
        self.c_courier = client_for(self.courier)

    def ids(self, res):
        self.assertEqual(res.status_code, 200, res.content)
        return {row["id"] for row in res.json()["results"]}

    def test_r1_filters_by_target_model_and_target_id(self):
        mine = make_action(self.manager, target_id="7")
        make_action(self.manager, target_id="8")
        make_action(self.manager, target_model="batch", target_id="7")
        res = self.c_manager.get(self.URL, {"target_model": "purchasereceipt", "target_id": "7"})
        self.assertEqual(self.ids(res), {str(mine.id)})

    def test_r1_target_id_accepts_comma_separated_ids(self):
        a = make_action(self.manager, target_id="7")
        b = make_action(self.manager, target_id="9")
        make_action(self.manager, target_id="8")
        res = self.c_manager.get(self.URL, {"target_model": "purchasereceipt", "target_id": "7, 9"})
        self.assertEqual(self.ids(res), {str(a.id), str(b.id)})

    def test_r1_multiple_statuses_combine_with_target_filter(self):
        pending = make_action(self.manager, status="PENDING")
        escalated = make_action(self.manager, status="ESCALATED", assignee_group=roles.OWNER)
        make_action(self.manager, status="DONE")
        res = self.c_manager.get(self.URL, {"target_model": "purchasereceipt", "target_id": "7",
                                            "status": "PENDING,ESCALATED"})
        self.assertEqual(self.ids(res), {str(pending.id), str(escalated.id)})

    def test_r1_accepts_app_label_model_form_from_02b(self):
        a = make_action(self.manager, target_model="purchasereceipt")
        res = self.c_manager.get(self.URL, {"target_model": "purchasing.purchasereceipt"})
        self.assertEqual(self.ids(res), {str(a.id)})

    def test_r1_matches_escalation_doc_type_and_pipeline_model_name(self):
        by_pipeline = make_action(self.manager, target_model="batch", target_id="5")
        by_escalate = make_action(self.manager, target_model="Batch", target_id="5")
        res = self.c_manager.get(self.URL, {"target_model": "inventory.batch", "target_id": "5"})
        self.assertEqual(self.ids(res), {str(by_pipeline.id), str(by_escalate.id)})

    def test_r1_does_not_leak_other_peoples_ai_actions(self):
        make_action(self.warehouse, target_id="7")  # việc của nv_kho trên cùng chứng từ
        make_action(self.owner, target_id="7")
        mine = make_action(self.manager, target_id="7")
        res = self.c_manager.get(self.URL, {"target_model": "purchasereceipt", "target_id": "7"})
        self.assertEqual(self.ids(res), {str(mine.id)})
        # nv_giao không có việc nào trên chứng từ này -> rỗng, không 403/404.
        res = self.c_courier.get(self.URL, {"target_model": "purchasereceipt", "target_id": "7"})
        self.assertEqual(self.ids(res), set())

    def test_r1_escalated_to_my_group_visible_other_groups_not(self):
        for_manager = make_action(self.warehouse, status="ESCALATED", assignee_group=roles.MANAGER)
        make_action(self.warehouse, status="ESCALATED", assignee_group=roles.OWNER)
        res = self.c_manager.get(self.URL, {"target_model": "purchasereceipt", "target_id": "7",
                                            "status": "ESCALATED"})
        self.assertEqual(self.ids(res), {str(for_manager.id)})

    def test_r1_scope_all_still_requires_ai_policy_permission(self):
        make_action(self.warehouse, target_id="7")
        res = self.c_manager.get(self.URL, {"scope": "all", "target_model": "purchasereceipt"})
        self.assertEqual(res.status_code, 403)
        self.assertEqual(len(self.ids(self.c_owner.get(self.URL, {"scope": "all", "target_model": "purchasereceipt"}))), 1)

    def test_r1_unknown_target_model_returns_400_without_echo(self):
        res = self.c_manager.get(self.URL, {"target_model": "KhongCoModelNay0900000123"})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()["code"], "INVALID_TARGET_MODEL")
        self.assertNotIn("0900000123", res.content.decode())

    def test_r1_too_many_target_ids_returns_400(self):
        ids = ",".join(str(i) for i in range(101))
        res = self.c_manager.get(self.URL, {"target_model": "purchasereceipt", "target_id": ids})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()["code"], "INVALID_TARGET_ID")

    def test_r1_target_id_without_target_model_returns_400(self):
        make_action(self.manager, target_model="purchasereceipt", target_id="12")
        make_action(self.manager, target_model="batch", target_id="12")
        res = self.c_manager.get(self.URL, {"target_id": "12"})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()["code"], "TARGET_MODEL_REQUIRED")
        self.assertNotIn("12", res.json()["detail"])  # không lặp lại giá trị gửi lên
        self.assertEqual(self.c_manager.get("/api/ai/actions/counts/", {"target_id": "12"}).status_code, 400)

    def test_r1_anonymous_gets_401(self):
        self.assertEqual(client_for(None).get(self.URL, {"target_model": "purchasereceipt"}).status_code, 401)

    def test_r1_without_filters_behaviour_unchanged(self):
        a = make_action(self.manager, target_model="batch")
        b = make_action(self.manager, target_model="purchasereceipt")
        self.assertEqual(self.ids(self.c_manager.get(self.URL)), {str(a.id), str(b.id)})

    def test_r1_target_has_only_type_and_code_no_personal_data(self):
        make_action(self.manager, target_model="salesorder", target_id="SO-R1-001")
        res = self.c_manager.get(self.URL, {"target_model": "sales.salesorder", "target_id": "SO-R1-001"})
        row = res.json()["results"][0]
        self.assertEqual(row["target"], {"type": "salesorder", "code": "SO-R1-001"})


@override_settings(AI_ENABLED=True)
class TargetCountsTests(TestCase):
    URL = "/api/ai/actions/counts/"

    def setUp(self):
        self.owner = make_user("r1c_owner", roles.OWNER)
        self.manager = make_user("r1c_manager", roles.MANAGER)
        self.warehouse = make_user("r1c_kho", roles.WAREHOUSE_STAFF)
        self.c_owner = client_for(self.owner)
        self.c_manager = client_for(self.manager)
        self.c_warehouse = client_for(self.warehouse)

    def test_r1_counts_by_screen_only_my_actions(self):
        make_action(self.manager, target_model="purchasereceipt", target_id="1")
        make_action(self.manager, target_model="purchasereceipt", target_id="2")
        make_action(self.manager, target_model="batch", target_id="3", status="ESCALATED", assignee_group=roles.OWNER)
        make_action(self.manager, target_model="batch", target_id="4", status="DONE")
        make_action(self.warehouse, target_model="purchasereceipt", target_id="5")
        res = self.c_manager.get(self.URL, {"status": "PENDING,ESCALATED"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {"by_target_model": {"purchasing.purchasereceipt": 2, "inventory.batch": 1}})

    def test_r1_counts_merge_pipeline_model_names_and_escalation_doc_types(self):
        make_action(self.manager, target_model="batch", target_id="1")
        make_action(self.manager, target_model="Batch", target_id="2")
        make_action(self.manager, target_model="order", target_id="3")
        make_action(self.manager, target_model="salesorder", target_id="SO-1")
        res = self.c_manager.get(self.URL)
        self.assertEqual(res.json()["by_target_model"], {"inventory.batch": 2, "sales.salesorder": 2})

    def test_r1_counts_skip_actions_without_target(self):
        make_action(self.manager, target_model="", target_id="")
        self.assertEqual(self.c_manager.get(self.URL).json(), {"by_target_model": {}})

    def test_r1_counts_other_users_do_not_see_my_numbers(self):
        make_action(self.manager, target_model="purchasereceipt")
        self.assertEqual(self.c_warehouse.get(self.URL).json(), {"by_target_model": {}})

    def test_r1_counts_scope_all_requires_ai_policy_permission(self):
        make_action(self.warehouse, target_model="purchasereceipt")
        self.assertEqual(self.c_manager.get(self.URL, {"scope": "all"}).status_code, 403)
        res = self.c_owner.get(self.URL, {"scope": "all"})
        self.assertEqual(res.json(), {"by_target_model": {"purchasing.purchasereceipt": 1}})

    def test_r1_counts_anonymous_gets_401(self):
        self.assertEqual(client_for(None).get(self.URL).status_code, 401)

    def test_r1_counts_post_not_allowed_405(self):
        self.assertEqual(self.c_manager.post(self.URL, {}, format="json").status_code, 405)


class TargetLabelMapTests(TestCase):
    def test_r1_every_doc_type_points_to_a_real_model(self):
        from apps.ai.actions.targets import DOC_TYPE_LABELS, resolve_target_label, stored_variants

        for doc_type, label in DOC_TYPE_LABELS.items():
            with self.subTest(doc_type=doc_type):
                self.assertEqual(resolve_target_label(doc_type), label)
                self.assertEqual(resolve_target_label(label), label)
                self.assertIn(doc_type, stored_variants(label))

    def test_r1_pipeline_name_and_class_name_resolve_to_same_label(self):
        from apps.ai.actions.targets import resolve_target_label

        for raw in ("purchasereceipt", "PurchaseReceipt", "purchasing.PurchaseReceipt", "receipt"):
            self.assertEqual(resolve_target_label(raw), "purchasing.purchasereceipt")
        self.assertIsNone(resolve_target_label("khong_co"))
        self.assertIsNone(resolve_target_label(""))
