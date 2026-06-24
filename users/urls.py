from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import ClientSessionHistoryAPIView, SessionHistoryAPIView, SuperAdminCreateAPIView, CustomTokenObtainPairView
from .views import LogoutView   # ✅ your custom logout

urlpatterns = [
    path("create-superadmin/", SuperAdminCreateAPIView.as_view(), name="create-superadmin"),
    # 🔑 JWT Login
    path("login/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    # Logout → blacklist refresh token
    path("logout/", LogoutView.as_view(), name="auth_logout"),
    path("session-history/", SessionHistoryAPIView.as_view(), name="session_history"),  # New endpoint
    path("client/session-history/", ClientSessionHistoryAPIView.as_view(), name="client-session-history"),
]
