"""Test `apps.common.slugs` — slug đường dẫn nhóm hàng (SHOP-2-01 AC5, 02b §2.1)."""
from django.test import TestCase

from apps.catalog.models import ItemGroup
from apps.common.slugs import SLUG_MAX_LENGTH, slugify_vi, unique_slug


class SlugifyViTests(TestCase):
    def test_removes_accents_and_lowercases(self):
        self.assertEqual(slugify_vi("Mực"), "muc")
        self.assertEqual(slugify_vi("Cá Thu"), "ca-thu")
        self.assertEqual(slugify_vi("Tôm sú loại 1"), "tom-su-loai-1")

    def test_d_with_stroke_becomes_d(self):
        self.assertEqual(slugify_vi("Đặc sản Đà Nẵng"), "dac-san-da-nang")

    def test_collapses_symbols_and_trims_dashes(self):
        self.assertEqual(slugify_vi("  Cá -- & tôm!! "), "ca-tom")

    def test_empty_or_symbols_only_falls_back(self):
        self.assertEqual(slugify_vi(""), "group")
        self.assertEqual(slugify_vi("***"), "group")

    def test_truncated_to_max_length_without_trailing_dash(self):
        slug = slugify_vi("a " * 100)
        self.assertLessEqual(len(slug), SLUG_MAX_LENGTH)
        self.assertFalse(slug.endswith("-"))


class UniqueSlugTests(TestCase):
    def test_free_base_is_returned_as_is(self):
        self.assertEqual(unique_slug(ItemGroup, "muc"), "muc")

    def test_collision_adds_numeric_suffix(self):
        ItemGroup.objects.create(name="Cá thu", slug="ca-thu")
        ItemGroup.objects.create(name="Cá Thu 2", slug="ca-thu-2")
        self.assertEqual(unique_slug(ItemGroup, "ca-thu"), "ca-thu-3")

    def test_exclude_pk_lets_a_row_keep_its_own_slug(self):
        group = ItemGroup.objects.create(name="Mực", slug="muc")
        self.assertEqual(unique_slug(ItemGroup, "muc", exclude_pk=group.pk), "muc")

    def test_suffix_keeps_total_length_within_limit(self):
        long_base = "x" * SLUG_MAX_LENGTH
        ItemGroup.objects.create(name="Dài", slug=long_base)
        result = unique_slug(ItemGroup, long_base)
        self.assertLessEqual(len(result), SLUG_MAX_LENGTH)
        self.assertTrue(result.endswith("-2"))


class ItemGroupAutoSlugTests(TestCase):
    """Nhóm tạo bằng ORM không truyền slug vẫn có slug duy nhất (model.save tự sinh)."""

    def test_save_generates_slug_from_name(self):
        self.assertEqual(ItemGroup.objects.create(name="Mực").slug, "muc")

    def test_two_names_same_after_folding_get_distinct_slugs(self):
        first = ItemGroup.objects.create(name="Cá thu")
        second = ItemGroup.objects.create(name="Ca thu")
        self.assertEqual((first.slug, second.slug), ("ca-thu", "ca-thu-2"))

    def test_explicit_slug_is_kept(self):
        self.assertEqual(ItemGroup.objects.create(name="Mực", slug="muc-tuoi").slug, "muc-tuoi")

    def test_renaming_does_not_change_existing_slug(self):
        group = ItemGroup.objects.create(name="Mực")
        group.name = "Mực ống"
        group.save()
        group.refresh_from_db()
        self.assertEqual(group.slug, "muc")
