"""
SHOP-2b-01 / SHOP-2b-02 (BE) — thông tin món hiện công khai trên Shop + slug nhóm hàng trong ERP.
BR-DM-25 (chữ công khai không chứa giá, nhà cung cấp, tên tàu, ngày nhập, mã lô, SĐT), BR-PQ-04, bất biến 1 và 9.
Dữ liệu giả (SĐT 0900000001).
"""
import json

from apps.accounts.models import AuditLog
from apps.catalog.models import Item, ItemGroup

from .api_base import CatalogApiBase

ITEMS = "/api/catalog/items/"
GROUPS = "/api/catalog/item-groups/"
SHOP_DETAIL = "/api/shop/catalog/{}/"

INFO = {
    "short_note": "Cắt khúc dày 2–3 cm",
    "spec": "Khúc 300–400 g",
    "storage": "Giữ đông -18°C, rã đông ngăn mát 8 giờ",
    "origin": "Vùng biển Phú Quốc",
    "description": "Cá thu tươi đánh bắt trong ngày.",
}
SENSITIVE_PUBLIC_KEYS = {
    "supplier", "supplier_name", "vessel", "received_date", "batch_code", "batch", "phone",
    "purchase_rate", "landed_unit_cost", "unit_cost", "qty_available", "qty_reserved", "image_id",
}


class ShopInfoBase(CatalogApiBase):
    def setUp(self):
        super().setUp()
        self.add_price(self.item_a)

    def patch_item(self, user, data):
        return self.send(user, "patch", f"{ITEMS}{self.item_a.pk}/", data)


class ItemShopInfoTests(ShopInfoBase):
    def test_2b01_ac1_owner_saves_five_fields_and_shop_detail_shows_them(self):
        res = self.patch_item(self.owner, INFO)
        self.assertEqual(res.status_code, 200, res.content)
        for key, value in INFO.items():
            self.assertEqual(res.json()[key], value)
        public = self.get(None, SHOP_DETAIL.format("CA01")).json()
        for key, value in INFO.items():
            self.assertEqual(public[key], value)

    def test_2b01_ac1_public_detail_has_no_sensitive_field(self):
        self.patch_item(self.owner, INFO)
        self.add_costed_batch(self.item_a)
        body = self.get(None, SHOP_DETAIL.format("CA01")).json()
        self.assertFalse(SENSITIVE_PUBLIC_KEYS & set(body))
        blob = json.dumps(body, ensure_ascii=False)
        self.assertNotIn("80000", blob)
        self.assertNotIn("Đầu mối A", blob)

    def test_2b01_public_catalog_list_short_note_comes_from_item(self):
        self.patch_item(self.owner, INFO)
        row = self.get(None, "/api/shop/catalog/").json()["items"][0]
        self.assertEqual(row["short_note"], INFO["short_note"])
        self.assertNotIn("spec", row)

    def test_2b01_defaults_are_empty_strings(self):
        body = self.get(None, SHOP_DETAIL.format("CA01")).json()
        for key in ("description", "spec", "storage", "origin"):
            self.assertEqual(body[key], "")
        self.assertEqual(body["short_note"], "")

    def test_2b01_ac2_phone_rejected_with_clear_message(self):
        for field in INFO:
            res = self.patch_item(self.owner, {field: "Gọi 0900000001 để hỏi"})
            self.assertEqual(res.status_code, 400, field)
            self.assertEqual(res.json()[field], ["Không ghi số điện thoại trong thông tin món."])
        self.item_a.refresh_from_db()
        self.assertEqual(self.item_a.description, "")

    def test_2b01_ac2_phone_with_separators_rejected(self):
        res = self.patch_item(self.owner, {"description": "Liên hệ 0900 000 001"})
        self.assertEqual(res.status_code, 400)

    def test_2b01_ac3_price_rejected(self):
        for text in ("Giá 250.000đ", "chỉ 250k/kg", "250,000 VND", "120 nghìn", "2 triệu", "250.000 ₫", "99K"):
            res = self.patch_item(self.owner, {"spec": text})
            self.assertEqual(res.status_code, 400, text)
            self.assertEqual(res.json()["spec"], ["Không ghi giá trong thông tin món. Giá lấy từ bảng giá."], text)

    def test_2b01_ac3_batch_code_rejected(self):
        res = self.patch_item(self.owner, {"origin": "Lô CA01-261010-A1B2C"})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()["origin"], ["Không ghi mã lô trong thông tin món."])

    def test_br_dm_25_supplier_vessel_import_date_phrases_rejected(self):
        for text in ("Nhà cung cấp Hải Long", "Tàu: tên tàu BV-1234", "Ngày nhập 10/10", "nhập lô sáng nay"):
            res = self.patch_item(self.owner, {"origin": text})
            self.assertEqual(res.status_code, 400, text)
            self.assertEqual(
                res.json()["origin"],
                ["Không ghi nhà cung cấp, tên tàu hay ngày nhập lô trong thông tin món."],
                text,
            )

    def test_2b01_normal_text_with_small_numbers_is_accepted(self):
        res = self.patch_item(self.owner, {"spec": "Khúc 300-400 g, 2 khúc/túi", "storage": "Rã đông 8 giờ"})
        self.assertEqual(res.status_code, 200, res.content)

    def test_2b01_ac4_length_limits(self):
        cases = {"short_note": (60, "Tối đa 60 ký tự."), "spec": (500, "Tối đa 500 ký tự."),
                 "storage": (500, "Tối đa 500 ký tự."), "origin": (500, "Tối đa 500 ký tự."),
                 "description": (2000, "Tối đa 2000 ký tự.")}
        for field, (limit, msg) in cases.items():
            self.assertEqual(self.patch_item(self.owner, {field: "a" * limit}).status_code, 200, field)
            res = self.patch_item(self.owner, {field: "a" * (limit + 1)})
            self.assertEqual(res.status_code, 400, field)
            self.assertEqual(res.json()[field], [msg])

    def test_2b01_ac5_only_owner_may_patch_other_groups_403_and_data_unchanged(self):
        for user in (self.manager, self.warehouse_staff, self.courier, self.customer_service, self.no_group):
            res = self.patch_item(user, INFO)
            self.assertEqual(res.status_code, 403, user.username)
        self.assertEqual(self.patch_item(None, INFO).status_code, 401)
        self.item_a.refresh_from_db()
        self.assertEqual(self.item_a.short_note, "")
        self.assertEqual(self.item_a.description, "")

    def test_2b01_ac6_audit_update_item_records_field_names_only(self):
        self.patch_item(self.owner, {"short_note": "Ghi chú an toàn", "description": "Mô tả an toàn"})
        log = AuditLog.objects.get(action="update_item")
        self.assertEqual(log.actor, self.owner)
        self.assertEqual(log.object_id, str(self.item_a.pk))
        blob = json.dumps(log.changes, ensure_ascii=False) + log.note
        self.assertEqual(sorted(log.changes["fields"]), ["description", "short_note"])
        self.assertNotIn("Ghi chú an toàn", blob)
        self.assertNotIn("Mô tả an toàn", blob)

    def test_2b01_ac6_audit_not_written_when_nothing_changed_or_rejected(self):
        self.patch_item(self.owner, {"description": "Gọi 0900000001"})
        self.assertFalse(AuditLog.objects.filter(action="update_item").exists())
        self.patch_item(self.owner, {"description": ""})  # không đổi
        self.assertFalse(AuditLog.objects.filter(action="update_item").exists())

    def test_2b01_ac7_erp_item_json_has_five_fields_and_no_cost(self):
        self.add_costed_batch(self.item_a)
        for user in (self.owner, self.warehouse_staff):
            body = self.get(user, f"{ITEMS}{self.item_a.pk}/").json()
            for key in INFO:
                self.assertIn(key, body)
            self.assertNotIn("80000", json.dumps(body))
        self.assertNotIn("current_price", self.get(self.warehouse_staff, f"{ITEMS}{self.item_a.pk}/").json())

    def test_2b01_create_item_with_info_validated(self):
        payload = {"code": "MUC01", "name": "Mực thử", "item_group": self.group_fish.pk, "spec": "Giá 10k"}
        self.assertEqual(self.send(self.owner, "post", ITEMS, payload).status_code, 400)
        payload["spec"] = "Khúc 300 g"
        self.assertEqual(self.send(self.owner, "post", ITEMS, payload).status_code, 201)


class ItemGroupSlugTests(CatalogApiBase):
    def setUp(self):
        super().setUp()
        self.group_fish.refresh_from_db()

    def url(self, group):
        return f"{GROUPS}{group.pk}/"

    def test_2b02_ac1_owner_changes_slug_and_audit_records_from_to(self):
        old = self.group_fish.slug
        res = self.send(self.owner, "patch", self.url(self.group_fish), {"slug": "ca-thu-dong"})
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.json()["slug"], "ca-thu-dong")
        log = AuditLog.objects.get(action="update_itemgroup")
        self.assertEqual(log.changes["slug"], {"from": old, "to": "ca-thu-dong"})

    def test_2b02_slug_visible_in_list(self):
        res = self.get(self.owner, GROUPS)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(all("slug" in row for row in res.json()["results"]))

    def test_2b02_ac1_shop_filter_uses_new_slug(self):
        self.add_price(self.item_a)
        self.send(self.owner, "patch", self.url(self.group_fish), {"slug": "ca-thu-dong"})
        slugs = [g["slug"] for g in self.get(None, "/api/shop/catalog/").json()["groups"]]
        self.assertIn("ca-thu-dong", slugs)

    def test_2b02_ac2_duplicate_slug_rejected(self):
        res = self.send(self.owner, "patch", self.url(self.group_fish), {"slug": self.group_shrimp.slug})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()["slug"], ["Đường dẫn đã dùng cho nhóm khác."])

    def test_2b02_ac2_invalid_format_rejected(self):
        for bad in ("Ca-Thu", "cá-thu", "ca thu", "-ca", "ca-", "ca--thu", "ca_thu", "a" * 81):
            res = self.send(self.owner, "patch", self.url(self.group_fish), {"slug": bad})
            self.assertEqual(res.status_code, 400, bad)
            self.assertIn("slug", res.json(), bad)
        res = self.send(self.owner, "patch", self.url(self.group_fish), {"slug": "Ca-Thu"})
        self.assertEqual(res.json()["slug"], ["Chỉ dùng chữ thường không dấu, số và dấu gạch ngang."])

    def test_2b02_ac2_empty_slug_rejected_on_update(self):
        for empty in ("", "   "):
            res = self.send(self.owner, "patch", self.url(self.group_fish), {"slug": empty})
            self.assertEqual(res.status_code, 400)
            self.assertEqual(res.json()["slug"], ["Không được để trống."])

    def test_2b02_slug_is_trimmed_before_check(self):
        res = self.send(self.owner, "patch", self.url(self.group_fish), {"slug": "  ca-thu-dong "})
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.json()["slug"], "ca-thu-dong")

    def test_2b02_same_slug_on_same_group_is_ok_and_no_audit(self):
        res = self.send(self.owner, "patch", self.url(self.group_fish), {"slug": self.group_fish.slug})
        self.assertEqual(res.status_code, 200)
        self.assertFalse(AuditLog.objects.filter(action="update_itemgroup").exists())

    def test_2b02_create_without_slug_autogenerates(self):
        res = self.send(self.owner, "post", GROUPS, {"name": "Đặc sản Cá Thu"})
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(res.json()["slug"], "dac-san-ca-thu")
        res = self.send(self.owner, "post", GROUPS, {"name": "Đặc sản Cá-Thu"})
        self.assertEqual(res.json()["slug"], "dac-san-ca-thu-2")

    def test_2b02_create_with_explicit_slug(self):
        res = self.send(self.owner, "post", GROUPS, {"name": "Ghẹ", "slug": "ghe-xanh"})
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()["slug"], "ghe-xanh")

    def test_2b02_ac3_only_owner_changes_slug(self):
        old = self.group_fish.slug
        for user in (self.manager, self.warehouse_staff, self.courier, self.customer_service, self.no_group):
            res = self.send(user, "patch", self.url(self.group_fish), {"slug": "x-y"})
            self.assertEqual(res.status_code, 403, user.username)
        self.group_fish.refresh_from_db()
        self.assertEqual(self.group_fish.slug, old)
        self.assertFalse(AuditLog.objects.filter(action="update_itemgroup").exists())


class PublicReadTimeFilterTests(ShopInfoBase):
    """Review lô 2 H1: dữ liệu cũ (ORM/admin) chưa qua kiểm BR-DM-25 không được lộ cho khách."""

    BAD = {
        "description": "Giá vốn 180 nghìn, gọi 0901234567",
        "short_note": "Lô CA01-261010-A1B2C",
        "spec": "Nhập từ tàu BT-12345",
        "storage": "giá vốn thấp",
        "origin": "Nhà cung cấp Hải Long",
    }

    def test_h1_bad_legacy_text_returns_empty_in_list_and_detail_keys_kept(self):
        Item.objects.filter(pk=self.item_a.pk).update(**self.BAD)
        detail = self.get(None, SHOP_DETAIL.format("CA01"))
        row = self.get(None, "/api/shop/catalog/").json()["items"][0]
        for key in self.BAD:
            self.assertEqual(detail.json()[key], "", key)
        self.assertEqual(row["short_note"], "")
        blob = detail.content.decode() + json.dumps(row, ensure_ascii=False)
        for needle in ("180", "0901234567", "A1B2C", "BT-12345", "Hải Long", "giá vốn"):
            self.assertNotIn(needle, blob)

    def test_h1_one_bad_field_does_not_hide_clean_fields(self):
        Item.objects.filter(pk=self.item_a.pk).update(description="Gọi 0901234567", spec="Khúc 300 g")
        body = self.get(None, SHOP_DETAIL.format("CA01")).json()
        self.assertEqual(body["description"], "")
        self.assertEqual(body["spec"], "Khúc 300 g")

    def test_l2_vessel_number_and_cost_phrase_rejected_on_save(self):
        for text in ("Hàng về ngày 10/10 từ tàu BT-12345", "Giá vốn thấp", "tàu BT 12345"):
            res = self.patch_item(self.owner, {"origin": text})
            self.assertEqual(res.status_code, 400, text)

    def test_l2_normal_words_still_ok(self):
        res = self.patch_item(self.owner, {"origin": "Đánh bắt bằng tàu lưới vây vùng biển Kiên Giang"})
        self.assertEqual(res.status_code, 200, res.content)

    def test_l1_admin_form_rejects_bad_text(self):
        from apps.catalog.admin import ItemAdminForm

        form = ItemAdminForm(instance=self.item_a, data={
            "code": "CA01", "name": "Cá thu", "item_group": self.group_fish.pk, "item_type": "SIMPLE",
            "stock_uom": "Kg", "shelf_life_in_days": 365, "has_batch_no": "on", "has_expiry_date": "on",
            "is_active": "on", "description": "Gọi 0901234567",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("description", form.errors)
