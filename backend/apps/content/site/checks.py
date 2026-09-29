from django.conf import settings
from django.core.checks import Warning


SELLER_FIELDS = (
    "SELLER_NAME",
    "SELLER_BUSINESS_TYPE",
    "SELLER_REG_NO",
    "SELLER_TAX_CODE",
    "SELLER_ADDRESS",
    "SELLER_PHONE",
    "SELLER_EMAIL",
)


def check_seller_info(app_configs=None, **kwargs) -> list[Warning]:
    """
    System check kiểm tra các biến cấu hình người bán SELLER_* (GL-01-AC4).
    Chỉ in tên biến bị thiếu, tuyệt đối không in giá trị của bất kỳ biến nào khác.
    """
    missing = []
    for var_name in SELLER_FIELDS:
        val = getattr(settings, var_name, "")
        if not val or not str(val).strip():
            missing.append(var_name)

    if missing:
        return [
            Warning(
                f"Thiếu cấu hình người bán: {', '.join(missing)}",
                hint="Đặt các biến SELLER_* trong môi trường hoặc .env trước khi go-live.",
                id="content.W001",
            )
        ]
    return []
