"""
API công khai nội dung (§8.6 02b-tech-design).
- Quyền: AllowAny (chỉ GET, HEAD, OPTIONS). Mọi method khác tự động trả 405.
- Throttle: PublicContentThrottle (scope: public_content, mặc định 120/min).
- Cache-Control: public, max-age=CONTENT_PUBLIC_CACHE_SECONDS.
- Tuyệt đối không rò rỉ giá vốn hay dữ liệu khách (Bất biến 1, 9).
"""

from django.conf import settings
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.throttling import PublicContentThrottle
from apps.content.models.categories import Category
from apps.content.models.entries import Entry
from apps.content.public.serializers import (
    PublicCategorySerializer,
    PublicEntryDetailSerializer,
    PublicEntryListSerializer,
)


def _cache_control_seconds() -> int:
    return getattr(settings, "CONTENT_PUBLIC_CACHE_SECONDS", 60)


class PublicEntryListView(APIView):
    """
    GET /api/public/content/entries/?kind=post&category=cong-thuc&page=1
    Danh sách bài viết công khai (không trả thân bài body).
    """

    permission_classes = [AllowAny]
    throttle_classes = [PublicContentThrottle]
    http_method_names = ["get", "head", "options"]

    def get(self, request):
        kind = request.query_params.get("kind", "post")
        category_slug = request.query_params.get("category")
        page_param = request.query_params.get("page", 1)

        qs = (
            Entry.objects.filter(status="published")
            .select_related("category", "cover_image", "published_version", "published_version__category", "published_version__cover_image")
        )

        if kind:
            qs = qs.filter(kind=kind)
        if category_slug:
            qs = qs.filter(published_version__category__slug=category_slug)

        qs = qs.order_by("-published_version__published_at", "-id")

        page_size = getattr(settings, "CONTENT_LIST_PAGE_SIZE", 12)
        paginator = Paginator(qs, page_size)

        try:
            page_num = int(page_param)
            if page_num < 1:
                raise NotFound("Trang không hợp lệ.")
            page_obj = paginator.page(page_num)
        except (PageNotAnInteger, ValueError):
            page_obj = paginator.page(1)
            page_num = 1
        except EmptyPage:
            raise NotFound("Không tìm thấy trang này.")

        results = [
            PublicEntryListSerializer.to_representation(entry, entry.published_version)
            for entry in page_obj.object_list
            if entry.published_version is not None
        ]

        # Xây dựng link next / previous
        next_url = None
        if page_obj.has_next():
            next_url = f"?page={page_num + 1}"
            if kind:
                next_url += f"&kind={kind}"
            if category_slug:
                next_url += f"&category={category_slug}"

        prev_url = None
        if page_obj.has_previous():
            prev_url = f"?page={page_num - 1}"
            if kind:
                prev_url += f"&kind={kind}"
            if category_slug:
                prev_url += f"&category={category_slug}"

        res = Response({
            "count": paginator.count,
            "next": next_url,
            "previous": prev_url,
            "results": results,
        })
        res["Cache-Control"] = f"public, max-age={_cache_control_seconds()}"
        return res


class PublicEntryDetailView(APIView):
    """
    GET /api/public/content/entries/<slug>/
    Chi tiết bài viết hoặc trang công khai.
    - Không tồn tại hoặc draft/pending_review -> 404 NOT_FOUND ("Không tìm thấy bài.")
    - Unpublished -> 410 GONE ("Bài này không còn trên web.")
    - Published -> 200
    """

    permission_classes = [AllowAny]
    throttle_classes = [PublicContentThrottle]
    http_method_names = ["get", "head", "options"]

    def get(self, request, slug):
        clean_slug = (slug or "").strip().lower()

        try:
            entry = (
                Entry.objects.select_related(
                    "category",
                    "cover_image",
                    "published_version",
                    "published_version__category",
                    "published_version__cover_image",
                )
                .get(slug=clean_slug)
            )
        except Entry.DoesNotExist:
            return Response(
                {"detail": "Không tìm thấy bài.", "code": "NOT_FOUND"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Bài đã gỡ -> 410 GONE
        if entry.status == "unpublished":
            return Response(
                {"detail": "Bài này không còn trên web.", "code": "GONE"},
                status=status.HTTP_410_GONE,
            )

        # Bài ở trạng thái nháp hoặc chờ duyệt hoặc chưa từng đăng -> trả 404 giống hệt không tồn tại (CMS-13-AC4)
        if entry.status in ("draft", "pending_review") or entry.published_version is None:
            return Response(
                {"detail": "Không tìm thấy bài.", "code": "NOT_FOUND"},
                status=status.HTTP_404_NOT_FOUND,
            )

        version = entry.published_version
        data = PublicEntryDetailSerializer.to_representation(entry, version)
        res = Response(data, status=status.HTTP_200_OK)
        res["Cache-Control"] = f"public, max-age={_cache_control_seconds()}"
        return res


class PublicCategoryListView(APIView):
    """
    GET /api/public/content/categories/
    Danh sách chuyên mục đang hoạt động và có ít nhất 1 bài đã đăng.
    """

    permission_classes = [AllowAny]
    throttle_classes = [PublicContentThrottle]
    http_method_names = ["get", "head", "options"]

    def get(self, request):
        qs = (
            Category.objects.filter(is_active=True, entries__status="published")
            .distinct()
            .order_by("order", "id")
        )
        data = [PublicCategorySerializer.to_representation(cat) for cat in qs]
        res = Response(data, status=status.HTTP_200_OK)
        res["Cache-Control"] = f"public, max-age={_cache_control_seconds()}"
        return res


class PublicPageByRoleView(APIView):
    """
    GET /api/public/content/pages/by-role/<role>/
    Tra cứu trang chính sách theo vai trò (privacy, terms, refund, seller_info).
    """

    permission_classes = [AllowAny]
    throttle_classes = [PublicContentThrottle]
    http_method_names = ["get", "head", "options"]

    def get(self, request, role):
        clean_role = (role or "").strip().lower()
        try:
            entry = (
                Entry.objects.select_related("published_version")
                .filter(page_role=clean_role, status="published")
                .first()
            )
            if not entry or not entry.published_version:
                return Response(
                    {"detail": "Không tìm thấy trang chính sách.", "code": "NOT_FOUND"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            version = entry.published_version
            return Response({
                "slug": entry.slug,
                "title": version.title,
                "version": version.version,
                "version_id": version.pk,
                "effective_from": version.published_at.isoformat(),
            })
        except Exception:
            return Response(
                {"detail": "Không tìm thấy trang chính sách.", "code": "NOT_FOUND"},
                status=status.HTTP_404_NOT_FOUND,
            )


class PublicFooterLinksView(APIView):
    """
    GET /api/public/content/footer-links/
    Danh sách link footer của các trang chính sách đã xuất bản.
    """

    permission_classes = [AllowAny]
    throttle_classes = [PublicContentThrottle]
    http_method_names = ["get", "head", "options"]

    def get(self, request):
        qs = (
            Entry.objects.filter(status="published", show_in_footer=True)
            .select_related("published_version")
            .order_by("footer_order", "id")
        )
        links = []
        for p in qs:
            if p.published_version:
                links.append({
                    "title": p.published_version.title,
                    "slug": p.slug,
                })
        res = Response(links, status=status.HTTP_200_OK)
        res["Cache-Control"] = f"public, max-age={_cache_control_seconds()}"
        return res
