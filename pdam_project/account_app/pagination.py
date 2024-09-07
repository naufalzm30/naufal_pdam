from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from rest_framework import status

class ItemPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

    def paginate_queryset(self, queryset, request, view=None):
        try:
            return super().paginate_queryset(queryset, request, view=view)
        except NotFound:
            # Custom behavior for invalid page number
            self.display_page_controls = False
            return []

    def get_paginated_response(self, data):
        if not data and not self.display_page_controls:
            return Response({"message": "Data not found"},status=status.HTTP_404_NOT_FOUND)
        
        return Response({
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            "max_per_page":self.page_size,
            'previous': self.get_previous_link(),
            'results': data,
        },status=status.HTTP_200_OK)