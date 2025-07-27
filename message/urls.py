from django.urls import path, include 
from rest_framework.routers import DefaultRouter
from .views import MessageTypeViewSet  


router = DefaultRouter()
router.register('message-types', MessageTypeViewSet, basename='message-types') 


# URL patterns for the message app
urlpatterns = [
    path('', include(router.urls)),  # Include the router URLs
]
