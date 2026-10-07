"""Mixin dùng chung cho các test đua trên PostgreSQL (TransactionTestCase + serialized_rollback)."""
from django.contrib.contenttypes.models import ContentType


class PostgresRaceFixtureMixin:
    """Dọn ContentType trước khi nạp lại bản serialize.

    Khi chạy chung suite, một TransactionTestCase khác (không serialized_rollback) đã flush rồi `post_migrate` tạo lại
    ContentType/Permission với id mới; nạp lại bản serialize sẽ đụng khoá duy nhất (admin, logentry). Xoá bản tạo lại
    trước (kéo theo Permission) để bản serialize nạp về đúng id gốc, sau đó xoá cache ContentType.

    Đặt mixin đứng TRƯỚC `TransactionTestCase` trong danh sách lớp cha.
    """

    serialized_rollback = True

    def _fixture_setup(self):
        ContentType.objects.all().delete()
        super()._fixture_setup()
        ContentType.objects.clear_cache()
