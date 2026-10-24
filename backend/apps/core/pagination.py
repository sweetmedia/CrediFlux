"""Paginación por defecto de la API."""
from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    """20 por página; el cliente puede pedir `?page_size=` hasta 500."""

    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 500
