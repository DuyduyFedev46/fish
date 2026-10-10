"""
Kiểm thử lệnh nạp nội dung Shop `load_shop_content` (SHOP-1-07 AC1–AC8; 02b §3.7.6; BR-ND-03, BR-ND-21, bất biến 9).
"""
import io
import json
import re
import shutil
import tempfile
from datetime import timedelta
from pathlib import Path

from django.contrib.auth.models import Group, User
from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts import roles
from apps.catalog.models import Item, ItemGroup, ItemPrice, PriceList
from apps.content.entries.services import save_draft
from apps.content.models.categories import Category
from apps.content.models.entries import Entry, EntryVersion

SOURCE_DIR = Path(__file__).resolve().parents[1] / "management" / "shop_content"
BLOCKED_CLAIMS = ("hút chân không", "cấp đông ngay tại cảng", "cân đúng", "tươi sống", "miễn phí giao", "phí giao")
# "hoàn tiền" chỉ được nằm trong tên trang "Chính sách đổi trả và hoàn tiền" (decisions 2026-10-10, UI-RULES §2.6).
REFUND_PAGE_NAME = "chính sách đổi trả và hoàn tiền"
PHONE_LIKE = re.compile(r"(?<!\d)(?:\+?84|0)(?:[\s.\-]?\d){9,10}(?!\d)")


def _all_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for k, v in value.items():
            if not str(k).startswith("_"):  # khoá "_note" là ghi chú cho người soạn, lệnh không nạp
                yield from _all_strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from _all_strings(v)


class LoadShopContentBase(TestCase):
    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)
        override = override_settings(MEDIA_ROOT=self.media, ITEM_IMAGE_STORAGE="local", SEPAY_ENV="SANDBOX")
        override.enable()
        self.addCleanup(override.disable)
        self.author = User.objects.create_user("content_loader", password="x")
        self.author.groups.add(Group.objects.get(name=roles.OWNER))
        self.author = User.objects.get(pk=self.author.pk)

    def run_cmd(self, *args, **kwargs):
        out = io.StringIO()
        call_command("load_shop_content", "--author", "content_loader", *args, stdout=out, stderr=out, **kwargs)
        return out.getvalue()

    def entry_state(self):
        return {
            e.slug: (e.status, e.row_version, e.draft_hash, e.published_version_id)
            for e in Entry.objects.all()
        }


class LoadShopContentPublishTests(LoadShopContentBase):
    def test_ac1_publish_creates_categories_pages_posts_all_published(self):
        """AC1: staging --publish -> 3 chuyên mục, 10 trang, 5 bài, tất cả Đã đăng; bìa tạm có nhãn Ảnh minh hoạ."""
        self.run_cmd("--publish")
        self.assertEqual(Category.objects.count(), 3)
        self.assertEqual(Entry.objects.filter(kind="page").count(), 10)
        self.assertEqual(Entry.objects.filter(kind="post").count(), 5)
        self.assertFalse(Entry.objects.exclude(status="published").exists())
        self.assertFalse(Entry.objects.filter(slug="ca-nuc-chien-gion").exists())  # S-23
        for post in Entry.objects.filter(kind="post"):
            self.assertIsNotNone(post.cover_image)
            self.assertTrue(post.cover_image.alt.startswith("Ảnh minh hoạ"))
            self.assertEqual(post.cover_image.entry_id, post.pk)
        self.assertEqual(
            set(Entry.objects.exclude(page_role=None).values_list("page_role", flat=True)),
            {"privacy", "terms", "refund", "seller_info", "shipping", "payment", "complaints"},
        )
        self.assertEqual(Entry.objects.get(page_role="terms").title, "Điều kiện giao dịch chung")

    def test_ac1_footer_links_six_pages_in_order(self):
        """AC1 + 06-marketing B4: footer-links công khai trả 6 trang chính sách theo thứ tự 1→6."""
        self.run_cmd("--publish")
        resp = APIClient().get("/api/public/content/footer-links/")
        self.assertEqual(resp.status_code, 200)
        slugs = [row["slug"] for row in resp.json()]
        self.assertEqual(slugs, ["doi-tra", "giao-hang", "thanh-toan", "quyen-rieng-tu", "dieu-khoan", "khieu-nai"])

    def test_ac1_public_about_page_readable(self):
        """SHOP-1-08 AC1: trang gioi-thieu đọc được qua API công khai sau khi nạp."""
        self.run_cmd("--publish")
        resp = APIClient().get("/api/public/content/entries/gioi-thieu/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["kind"], "page")
        self.assertTrue(data["body"]["blocks"])

    def test_rerun_is_idempotent(self):
        """AC3: chạy lại không tạo bản trùng, không đổi row_version, không đăng thêm phiên bản."""
        self.run_cmd("--publish")
        before = self.entry_state()
        versions = EntryVersion.objects.count()
        out = self.run_cmd("--publish")
        self.assertEqual(self.entry_state(), before)
        self.assertEqual(EntryVersion.objects.count(), versions)
        self.assertEqual(Category.objects.count(), 3)
        self.assertIn("không đổi", out)

    def test_draft_then_publish_publishes_without_duplicates(self):
        """Nạp nháp rồi chạy lại với --publish: đăng đúng các bản đã nạp, không tạo bản trùng."""
        self.run_cmd()
        count = Entry.objects.count()
        self.run_cmd("--publish")
        self.assertEqual(Entry.objects.count(), count)
        self.assertFalse(Entry.objects.exclude(status="published").exists())


class LoadShopContentDraftTests(LoadShopContentBase):
    def test_ac2_default_loads_draft_only(self):
        """AC2: không cờ -> mọi trang, bài ở Nháp; không phiên bản đăng nào."""
        self.run_cmd()
        self.assertEqual(Entry.objects.count(), 15)
        self.assertFalse(Entry.objects.exclude(status="draft").exists())
        self.assertEqual(EntryVersion.objects.count(), 0)
        # Production: bài để Lộc tải ảnh thật, không gắn ảnh tạm.
        self.assertFalse(Entry.objects.filter(kind="post", cover_image__isnull=False).exists())

    def test_ac3_manual_edit_is_skipped_unless_overwrite(self):
        """AC3: Lộc sửa tay trang lien-he -> chạy lại bỏ qua (in 'bỏ qua: đã sửa'); --overwrite thì ghi đè."""
        self.run_cmd()
        loc = User.objects.create_user("owner_two", password="x")
        loc.groups.add(Group.objects.get(name=roles.OWNER))
        loc = User.objects.get(pk=loc.pk)
        page = Entry.objects.get(slug="lien-he")
        edited_body = {"type": "doc", "blocks": [{"type": "paragraph", "children": [{"text": "Bản Lộc sửa."}]}]}
        save_draft(entry=page, data={"body": edited_body}, actor=loc)

        out = self.run_cmd()
        page.refresh_from_db()
        self.assertIn("bỏ qua: đã sửa", out)
        self.assertIn("lien-he", out)
        self.assertEqual(page.body["blocks"][0]["children"][0]["text"], "Bản Lộc sửa.")

        self.run_cmd("--overwrite")
        page.refresh_from_db()
        self.assertNotEqual(page.body["blocks"][0]["children"][0]["text"], "Bản Lộc sửa.")

    def test_ac3_page_created_by_someone_else_is_not_touched(self):
        """AC3: trang cùng slug do người khác tạo trước (không do lệnh nạp) -> bỏ qua, không ghi đè."""
        other = User.objects.create_user("owner_three", password="x")
        other.groups.add(Group.objects.get(name=roles.OWNER))
        other = User.objects.get(pk=other.pk)
        body = {"type": "doc", "blocks": [{"type": "paragraph", "children": [{"text": "Trang có sẵn."}]}]}
        save_draft(data={"kind": "page", "slug": "lien-he", "title": "Liên hệ", "body": body}, actor=other)
        out = self.run_cmd()
        self.assertIn("bỏ qua: đã sửa", out)
        self.assertEqual(Entry.objects.filter(slug="lien-he").count(), 1)
        self.assertEqual(Entry.objects.get(slug="lien-he").body["blocks"][0]["children"][0]["text"], "Trang có sẵn.")


class LoadShopContentGuardTests(LoadShopContentBase):
    def _copy_source(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        for name in ("categories.json", "pages.json", "posts.json"):
            shutil.copy(SOURCE_DIR / name, tmp / name)
        return tmp

    def _patch_page(self, src, slug, line):
        data = json.loads((src / "pages.json").read_text(encoding="utf-8"))
        for page in data["pages"]:
            if page["slug"] == slug:
                page["body"].append(line)
        (src / "pages.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def test_ac4_disallowed_phone_stops_that_page_only(self):
        """AC4: thân bài có SĐT ngoài danh sách được phép -> báo slug + lý do, trang khác vẫn nạp, exit != 0."""
        src = self._copy_source()
        self._patch_page(src, "lien-he", "Gọi 0900 000 009 để hỏi.")
        out = io.StringIO()
        with self.assertRaises(CommandError):
            call_command("load_shop_content", "--author", "content_loader", "--source", str(src), stdout=out, stderr=out)
        text = out.getvalue()
        self.assertIn("lien-he", text)
        self.assertIn("số điện thoại", text)
        self.assertNotIn("0900 000 009", text)  # không in lại số (bất biến 9)
        self.assertFalse(Entry.objects.filter(slug="lien-he").exists())
        self.assertTrue(Entry.objects.filter(slug="cach-mua-hang").exists())
        self.assertEqual(Entry.objects.count(), 14)

    def test_ac4_hotline_is_allowed(self):
        """AC4 + AC8: hotline từ settings được thay vào {hotline} và không bị chặn như SĐT lạ."""
        with override_settings(SHOP_HOTLINE="0900 000 001"):
            self.run_cmd("--publish")
        seller = Entry.objects.get(page_role="seller_info")
        self.assertIn("0900 000 001", json.dumps(seller.body, ensure_ascii=False))
        self.assertEqual(seller.status, "published")

    def test_ac8_placeholder_hotline_kept_in_brackets(self):
        """AC8: hotline chưa cấu hình (không phải số) -> giữ chữ [hotline] để dễ tìm."""
        with override_settings(SHOP_HOTLINE="1900 xxxx"):
            self.run_cmd()
        seller = Entry.objects.get(page_role="seller_info")
        self.assertIn("[hotline]", json.dumps(seller.body, ensure_ascii=False))

    def test_ac5_blocked_claim_in_page_is_rejected(self):
        """AC5: dữ liệu nạp chứa cụm bị chặn -> trang đó bị từ chối."""
        src = self._copy_source()
        self._patch_page(src, "gioi-thieu", "Hàng tươi sống mỗi ngày.")
        out = io.StringIO()
        with self.assertRaises(CommandError):
            call_command("load_shop_content", "--author", "content_loader", "--source", str(src), stdout=out, stderr=out)
        self.assertIn("gioi-thieu", out.getvalue())
        self.assertFalse(Entry.objects.filter(slug="gioi-thieu").exists())

    def test_ac5_ac8_source_files_have_no_claims_or_phones(self):
        """AC5, AC8: file nguồn không có cụm bị chặn (S-18), không số giống SĐT, không bài cá nục (S-23)."""
        for name in ("categories.json", "pages.json", "posts.json"):
            data = json.loads((SOURCE_DIR / name).read_text(encoding="utf-8"))
            for text in _all_strings(data):
                lowered = text.lower()
                for claim in BLOCKED_CLAIMS:
                    self.assertNotIn(claim, lowered, f"{name}: {text}")
                self.assertIsNone(PHONE_LIKE.search(text), f"{name}: {text}")
                self.assertNotIn("cá nục", lowered)

    def test_qa_b1_loaded_content_has_no_banned_words(self):
        """QA lô 1 B1 (BR-BH-30, UI-RULES §2.3, §2.6): dữ liệu đã nạp (tiêu đề, tóm tắt, SEO, thân bài) không có
        "Phí giao", "miễn phí giao", "Cân đúng"; "hoàn tiền" chỉ có trong tên trang chính sách đổi trả."""
        self.run_cmd()
        for e in Entry.objects.all():
            text = " ".join([e.title, e.excerpt, e.seo_title, e.seo_description, json.dumps(e.body, ensure_ascii=False)]).lower()
            for banned in ("phí giao", "miễn phí giao", "cân đúng"):
                self.assertNotIn(banned, text, e.slug)
            self.assertNotIn("hoàn tiền", text.replace(REFUND_PAGE_NAME, ""), e.slug)
        cach_mua = Entry.objects.get(slug="cach-mua-hang")
        self.assertIn("Đã gồm giao hàng".lower(), json.dumps(cach_mua.body, ensure_ascii=False).lower())

    def test_qa_b1_page_with_delivery_fee_line_is_rejected(self):
        """QA lô 1 B1: trang có chữ "Phí giao" bị lệnh từ chối như cụm khẳng định cấm."""
        src = self._copy_source()
        self._patch_page(src, "cach-mua-hang", "### Phí giao bao nhiêu?")
        out = io.StringIO()
        with self.assertRaises(CommandError):
            call_command("load_shop_content", "--author", "content_loader", "--source", str(src), stdout=out, stderr=out)
        self.assertIn("cach-mua-hang", out.getvalue())
        self.assertFalse(Entry.objects.filter(slug="cach-mua-hang").exists())

    def test_seo_lengths_and_no_brackets_in_about_meta(self):
        """SHOP-1-09 AC2: seo_title <= 60, seo_description <= 160; trang gioi-thieu không có ngoặc vuông ở SEO."""
        self.run_cmd()
        for e in Entry.objects.all():
            self.assertLessEqual(len(e.seo_title), 60, e.slug)
            self.assertLessEqual(len(e.seo_description), 160, e.slug)
        page = Entry.objects.get(slug="gioi-thieu")
        self.assertNotRegex(page.seo_title + page.seo_description, r"[\[\]]")

    def test_ac6_production_requires_confirmation_flag(self):
        """AC6: SEPAY_ENV=PRODUCTION mà thiếu --environment production -> từ chối, không tạo gì."""
        with override_settings(SEPAY_ENV="PRODUCTION"):
            with self.assertRaises(CommandError):
                self.run_cmd()
            self.assertEqual(Entry.objects.count(), 0)
            with self.assertRaises(CommandError):
                self.run_cmd("--environment", "production", "--publish")
            self.assertEqual(Entry.objects.count(), 0)
            self.run_cmd("--environment", "production")
        self.assertEqual(Entry.objects.count(), 15)
        self.assertFalse(Entry.objects.exclude(status="draft").exists())

    def test_author_must_exist_and_have_publish_permission(self):
        """--author bắt buộc là tài khoản có thật, có quyền đăng nội dung."""
        with self.assertRaises(CommandError):
            call_command("load_shop_content", "--author", "khong_co_ai", stdout=io.StringIO())
        User.objects.create_user("plain_user", password="x")
        with self.assertRaises(CommandError):
            call_command("load_shop_content", "--author", "plain_user", stdout=io.StringIO())
        self.assertEqual(Entry.objects.count(), 0)

    def test_item_card_only_for_real_priced_items(self):
        """06-marketing C2.3, cms-cho-mkt §9: thẻ hàng chỉ chèn khi mã có thật, đang bán, có giá."""
        group = ItemGroup.objects.create(name="Cá biển")
        item = Item.objects.create(code="CA-THU", name="Cá thu", item_group=group, is_active=True)
        Item.objects.create(code="MUC-ONG", name="Mực ống", item_group=group, is_active=True)  # không giá
        price_list, _ = PriceList.objects.get_or_create(name="Bán lẻ", is_default=True)
        ItemPrice.objects.create(item=item, price_list=price_list, rate=165000,
                                 valid_from=timezone.localdate() - timedelta(days=1))
        self.run_cmd("--publish")
        page = Entry.objects.get(slug="gioi-thieu")
        codes = [b["item_code"] for b in page.body["blocks"] if b["type"] == "item_card"]
        self.assertEqual(codes, ["CA-THU"])
        self.assertEqual(page.status, "published")


class LoadShopContentCleanupTests(LoadShopContentBase):
    def test_publish_failure_rolls_back_and_removes_placeholder_files(self):
        """Review lô 1 L6: đăng lỗi sau khi đã tải ảnh tạm -> DB rollback, tệp ảnh tạm (kho local) bị dọn, lệnh exit != 0."""
        from unittest import mock

        from apps.common.exceptions import BusinessError

        def fail_posts(*, entry, **kwargs):
            if entry.kind == "post":
                raise BusinessError("Lỗi đăng giả lập.", code="TEST")
            return real_publish(entry=entry, **kwargs)

        from apps.content.management.commands import load_shop_content as command_module

        real_publish = command_module.publish_entry
        with mock.patch.object(command_module, "publish_entry", side_effect=fail_posts):
            with self.assertRaises(CommandError):
                self.run_cmd("--publish")
        self.assertFalse(Entry.objects.filter(kind="post").exists())
        self.assertEqual(Entry.objects.filter(kind="page", status="published").count(), 10)
        content_dir = Path(self.media) / "content"
        leftover = [p for p in content_dir.rglob("*") if p.is_file()] if content_dir.exists() else []
        self.assertEqual(leftover, [])


class LoadShopContentPageRoleTests(LoadShopContentBase):
    """SHOP-5-02 AC1: lệnh nạp gắn vai trò shipping/payment/complaints cho giao-hang, thanh-toan, khieu-nai (BR-ND-20)."""

    EXPECTED = {"giao-hang": "shipping", "thanh-toan": "payment", "khieu-nai": "complaints"}

    def roles_of(self):
        return dict(Entry.objects.filter(slug__in=self.EXPECTED).values_list("slug", "page_role"))

    def test_shop_5_02_ac1_fresh_load_sets_roles_and_footer(self):
        self.run_cmd("--publish")
        self.assertEqual(self.roles_of(), self.EXPECTED)
        resp = APIClient().get("/api/public/content/footer-links/")
        self.assertEqual(
            [row["slug"] for row in resp.json()],
            ["doi-tra", "giao-hang", "thanh-toan", "quyen-rieng-tu", "dieu-khoan", "khieu-nai"],
        )

    def _simulate_old_load(self):
        """Trạng thái staging đã nạp ở lô 1: ba trang chưa có vai trò."""
        self.run_cmd("--publish")
        Entry.objects.filter(slug__in=self.EXPECTED).update(page_role=None)

    def test_shop_5_02_rerun_assigns_roles_to_existing_pages_idempotently(self):
        """Trang đã nạp trước (chưa vai trò): chạy lại gắn vai trò, không đăng thêm phiên bản; chạy lần nữa không đổi gì."""
        self._simulate_old_load()
        versions = EntryVersion.objects.count()
        self.run_cmd("--publish")
        self.assertEqual(self.roles_of(), self.EXPECTED)
        self.assertEqual(EntryVersion.objects.count(), versions)
        self.assertEqual(Entry.objects.filter(kind="page").count(), 10)
        before = self.entry_state()
        out = self.run_cmd("--publish")
        self.assertEqual(self.entry_state(), before)
        self.assertNotIn("gắn vai trò", out)

    def test_shop_5_02_edited_page_gets_role_without_touching_content(self):
        """Lộc đã sửa giao-hang: lệnh không ghi đè nội dung nhưng vẫn gắn vai trò (trang bắt buộc phải khoá gỡ)."""
        self._simulate_old_load()
        loc = User.objects.create_user("owner_edit", password="x")
        loc.groups.add(Group.objects.get(name=roles.OWNER))
        loc = User.objects.get(pk=loc.pk)
        page = Entry.objects.get(slug="giao-hang")
        edited = {"type": "doc", "blocks": [{"type": "paragraph", "children": [{"text": "Bản Lộc sửa."}]}]}
        save_draft(entry=page, data={"body": edited}, actor=loc)

        out = self.run_cmd()
        page.refresh_from_db()
        self.assertEqual(page.page_role, "shipping")
        self.assertEqual(page.body["blocks"][0]["children"][0]["text"], "Bản Lộc sửa.")
        self.assertIn("gắn vai trò shipping", out)
        self.assertIn("bỏ qua: đã sửa", out)
        # Lần sau vẫn coi là đã sửa (không nhầm là bản lệnh nạp) và không gắn lại.
        out2 = self.run_cmd()
        self.assertIn("bỏ qua: đã sửa", out2)
        self.assertNotIn("gắn vai trò", out2)

    def test_shop_5_02_role_held_by_other_page_is_not_moved(self):
        """Vai trò shipping đã có trang khác giữ -> không chuyển vai trò, giao-hang giữ nguyên."""
        self._simulate_old_load()
        other = save_draft(
            data={"kind": "page", "slug": "giao-hang-cu", "title": "Giao hàng (cũ)", "page_role": "shipping",
                  "body": {"type": "doc", "blocks": []}},
            actor=self.author,
        )
        out = self.run_cmd("--publish")
        self.assertIn("vai trò shipping đã có trang khác giữ", out)
        self.assertEqual(Entry.objects.get(page_role="shipping").pk, other.pk)
        self.assertIsNone(Entry.objects.get(slug="giao-hang").page_role)
