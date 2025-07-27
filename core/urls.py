from django.urls import include, path 
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework.routers import DefaultRouter
from .views import DependentViewSet, GuardianViewSet, PhoneLoginAPIView, PhonePasswordLoginAPIView, VerifyOTPAPIView, UserProfileAPIView, DeleteAccountAPIView

# Create a router and register our viewsets with it 
router = DefaultRouter()
router.register('guardians', GuardianViewSet, basename='guardians')
router.register('dependents', DependentViewSet, basename='dependents') 


# URL patterns for the core app
urlpatterns = [
    path('', include(router.urls)),  # Include the router URLs
    path('phone-login/', PhoneLoginAPIView.as_view(), name='phone_login'),
    path('phone-password-login/', PhonePasswordLoginAPIView.as_view(), name='phone_password_login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('verify-otp/', VerifyOTPAPIView.as_view(), name='verify_otp'),
    path('profile/', UserProfileAPIView.as_view(), name='user_profile'),
    path('delete-account/', DeleteAccountAPIView.as_view(), name='delete_account'), 
]
