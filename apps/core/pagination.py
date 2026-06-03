"""
Standard pagination class used across all list endpoints.
Returns the Omarina envelope format.
"""
from drf_spectacular.utils import OpenApiParameter
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

# Reusable query-parameter descriptors for drf-spectacular.
# Add to any paginated list endpoint's @extend_schema(parameters=[...]).
PAGINATION_PARAMS = [
    OpenApiParameter(
        name="page",
        type=int,
        location=OpenApiParameter.QUERY,
        required=False,
        description="Page number (default: 1).",
    ),
    OpenApiParameter(
        name="page_size",
        type=int,
        location=OpenApiParameter.QUERY,
        required=False,
        description="Number of results per page (default: 20, max: 100).",
    ),
]


class StandardResultsPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

    def _get_next_pages(self):
        """Return the number of pages remaining after the current page, or None on the last page."""
        remaining = self.page.paginator.num_pages - self.page.number
        return remaining if remaining > 0 else None

    def get_paginated_response(self, data):
        return Response(
            {
                "status": True,
                "message": "Data retrieved successfully",
                "data": {
                    "count": self.page.paginator.count,
                    "next": self.get_next_link(),
                    "previous": self.get_previous_link(),
                    "next_pages": self._get_next_pages(),
                    "results": data,
                },
            }
        )

    def get_paginated_response_with_message(self, data, message):
        return Response(
            {
                "status": True,
                "message": message,
                "data": {
                    "count": self.page.paginator.count,
                    "next": self.get_next_link(),
                    "previous": self.get_previous_link(),
                    "next_pages": self._get_next_pages(),
                    "results": data,
                },
            }
        )

    def get_paginated_response_schema(self, schema):
        return {
            "type": "object",
            "properties": {
                "status": {"type": "boolean"},
                "message": {"type": "string"},
                "data": {
                    "type": "object",
                    "properties": {
                        "count": {"type": "integer"},
                        "next": {"type": "string", "nullable": True},
                        "previous": {"type": "string", "nullable": True},
                        "next_pages": {
                            "type": "integer",
                            "nullable": True,
                            "description": "Number of pages remaining after the current page. Null on the last page.",
                        },
                        "results": schema,
                    },
                },
            },
        }


class PaginationMixin:
    """
    Mixin for APIView subclasses that adds pagination to list endpoints.

    Usage:
        class MyListView(PaginationMixin, APIView):
            def get(self, request):
                items = service.list_items()
                return self.paginate_and_respond(items, MySerializer, request, "Items retrieved successfully")
    """
    pagination_class = StandardResultsPagination

    def paginate_and_respond(self, queryset, serializer_class, request, message, context=None):
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
        ctx = context if context is not None else {"request": request}
        if page is not None:
            data = serializer_class(page, many=True, context=ctx).data
            return paginator.get_paginated_response_with_message(data, message)
        from apps.core.responses import success_response
        return success_response(
            data=serializer_class(queryset, many=True, context=ctx).data,
            message=message,
        )
