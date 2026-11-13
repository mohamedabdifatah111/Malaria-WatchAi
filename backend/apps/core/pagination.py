from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from .responses import build_meta


class StandardPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200

    def get_paginated_response(self, data):
        paginator = self.page.paginator
        pagination = {
            "count": paginator.count,
            "page": self.page.number,
            "page_size": paginator.per_page,
            "total_pages": paginator.num_pages,
            "next": self.get_next_link(),
            "previous": self.get_previous_link(),
        }
        meta = build_meta(
            {
                "pagination": pagination,
                "data_status": "available" if paginator.count else "no_data",
            }
        )
        if not paginator.count:
            meta["message"] = "No validated evidence is available for the selected filters."
        return Response({"success": True, "data": data, "meta": meta})

    def get_paginated_response_schema(self, schema):
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "data": schema,
                "meta": {"type": "object"},
            },
        }