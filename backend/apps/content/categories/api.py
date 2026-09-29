from django.db.models import Count, Q
from rest_framework import status, viewsets
from rest_framework.response import Response

from apps.content.categories.serializers import CategorySerializer
from apps.content.categories.services import create_category, update_category
from apps.content.models.categories import Category
from apps.content.permissions import ContentPermissions


class CategoryViewSet(viewsets.GenericViewSet):
    """
    API quản lý chuyên mục (§8.2 02b-tech-design).
    Chỉ hỗ trợ GET (list), POST (create), PATCH (partial_update).
    DELETE và PUT trả về 405 MethodNotAllowed.
    """

    permission_classes = [ContentPermissions]
    serializer_class = CategorySerializer
    queryset = Category.objects.all()
    http_method_names = ["get", "post", "patch", "head", "options"]
    pagination_class = None

    def get_queryset(self):
        return (
            Category.objects.annotate(
                published_count=Count("entries", filter=Q(entries__status="published"))
            )
            .order_by("order", "id")
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        category = create_category(
            name=request.data.get("name"),
            description=request.data.get("description", ""),
            order=request.data.get("order", 0),
        )
        serializer = self.get_serializer(category)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        category = self.get_object()
        category = update_category(category=category, data=request.data)
        serializer = self.get_serializer(category)
        return Response(serializer.data, status=status.HTTP_200_OK)
