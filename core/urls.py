from django.urls import include, path 
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework.routers import DefaultRouter
from .views import AppSettingsView, DashboardStatsView, DependentViewSet, DisabilityTypeViewSet, GuardianViewSet, PhoneLoginAPIView, PhonePasswordLoginAPIView, RequestGuardianPinResetView, ResetGuardianPinCodeView, SetGuardianPinCodeView, VerifyGuardianPinCodeView, VerifyOTPAPIView, UserProfileAPIView, DeleteAccountAPIView

# Create a router and register our viewsets with it 
router = DefaultRouter()
router.register('guardians', GuardianViewSet, basename='guardians')
router.register('disability-types', DisabilityTypeViewSet, basename='disability-types')
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
    path('set-guardian-pin-code/', SetGuardianPinCodeView.as_view(), name='set_guardian_pin_code'),
    path('request-guardian-pin-code/', RequestGuardianPinResetView.as_view(), name='request_guardian_pin_code'),
    path('reset-guardian-pin-code/', ResetGuardianPinCodeView.as_view(), name='reset_guardian_pin_code'),
    path('verify-guardian-pin-code/', VerifyGuardianPinCodeView.as_view(), name='verify_guardian_pin_code'),
    path('app-settings/', AppSettingsView.as_view(), name='app-settings'),
    path('dashboard-statistics/', DashboardStatsView.as_view(), name='dashboard')

]
