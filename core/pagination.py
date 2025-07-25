from rest_framework.pagination import PageNumberPagination


# Default Pagination 
class DefaultPagination(PageNumberPagination):
    page_size = 20  # Number of items per page
    page_size_query_param = 'page_size'  # Allow clients to set the page size