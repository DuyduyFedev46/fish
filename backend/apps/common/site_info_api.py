"""
API công khai cung cấp thông tin chung cho Shop web (CS-10, GL-01, 02b §4.4).
- AllowAny, chỉ GET
- Cache-Control: public, max-age=300
- Không rò giá vốn hay bất kỳ dữ liệu nội bộ
"""
from apps.content.site.api import SiteInfoView

PublicSiteInfoView = SiteInfoView
