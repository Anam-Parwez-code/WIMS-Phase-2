from django.urls import path
from .views import ClientLoginAPIView, ClientRetrieveAPIView, StudentLoginDashboardAPIView, ValidateClientCodeAPIView
from .views import ClientListCreateUpdateAPIView, ClientDeleteAPIView, ClientSearchAPIView, ClientExportAPIView
from .views import MigrateTenantsAPIView, SelectClientAPIView, ClientLogoutAPIView



urlpatterns = [
    #path('tenants/', TenantCreateView.as_view(), name='tenant-create'),
    path("InsertUpdateClient/", ClientListCreateUpdateAPIView.as_view(), name="insert_update_client"),
    path("InsertUpdateClient/<int:pk>/", ClientListCreateUpdateAPIView.as_view(), name="update_client"),  #pk is the client_id
    path("DeleteClient/<int:pk>/", ClientDeleteAPIView.as_view(), name="delete_client"),  #pk is the client_id
    path("GetClients/", ClientSearchAPIView.as_view(), name="get_clients"),
    path("GetClients/<int:pk>/", ClientRetrieveAPIView.as_view(), name="get_client_detail"),  #pk is the client_id
    path("GetClients/export/", ClientExportAPIView.as_view(), name="export_clients"),
    path('migrate-tenants/', MigrateTenantsAPIView.as_view(), name='migrate-tenants'),   # Run for all tenants
    path('migrate-tenants/<str:client_code>/', MigrateTenantsAPIView.as_view(), name='migrate-tenants-client'),   # Run for specific tenant
    path("SelectClient/", SelectClientAPIView.as_view(), name="select-client"),
    path("ValidateClient/", ValidateClientCodeAPIView.as_view(), name="validate-client"),
    path("login/", ClientLoginAPIView.as_view(), name="client-login"),
    path('logout/', ClientLogoutAPIView.as_view(), name='client_logout'),
    path("student-login/dashboard-count/",StudentLoginDashboardAPIView.as_view(),name="student-login-dashboard-count")

]



