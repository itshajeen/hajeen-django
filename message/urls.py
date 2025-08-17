from django.urls import path, include 
from rest_framework.routers import DefaultRouter
from .views import GuardianMessagesAPIView, MessageTypeViewSet, GuardianMessageTypeViewSet, MessageViewSet

router = DefaultRouter()
router.register('message-types', MessageTypeViewSet, basename='message-types') 
router.register('guardian-message-type', GuardianMessageTypeViewSet, basename='guardian-message-type')
router.register('messages', MessageViewSet, basename='messages') 


# URL patterns for the message app
urlpatterns = [
    path('', include(router.urls)),  # Include the router URLs
    path('guardian/messages/', GuardianMessagesAPIView.as_view(), name='guardian-messages'),
]
