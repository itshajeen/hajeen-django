from django.urls import path, include 
from rest_framework.routers import DefaultRouter
from .views import MessageTypeViewSet, GuardianMessageTypeViewSet

router = DefaultRouter()
router.register('message-types', MessageTypeViewSet, basename='message-types') 
router.register('guardian-message-type', GuardianMessageTypeViewSet, basename='guardian-message-type')


# URL patterns for the message app
urlpatterns = [
    path('', include(router.urls)),  # Include the router URLs
]
