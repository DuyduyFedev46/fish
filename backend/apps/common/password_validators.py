"""Validator mật khẩu dùng thông điệp tiếng Việt cố định.

Django 5.2.x đổi msgid của MinimumLengthValidator sang `%d` nhưng bản dịch `vi` vẫn dùng
`%(min_length)d`, nên thông điệp rơi về tiếng Anh. Ghi đè ở đây để UI luôn nhận tiếng Việt
(rà soát bảo mật 15/11, nâng Django 5.1 → 5.2). Bỏ lớp này khi Django sửa bản dịch.
"""
from django.contrib.auth.password_validation import MinimumLengthValidator


class VietnameseMinimumLengthValidator(MinimumLengthValidator):
    def get_error_message(self):
        return f"Mật khẩu quá ngắn. Mật khẩu phải có ít nhất {self.min_length} ký tự."
