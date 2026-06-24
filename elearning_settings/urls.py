# elearning_settings/urls.py
from django.urls import path
from .views import *

urlpatterns = urlpatterns = [
    # Modules
    path('modules/', ModuleListCreateView.as_view(), name='module-list-create'),
    path('modules/<int:pk>/', ModuleRetrieveUpdateDeleteAPIView.as_view(), name='module-detail'),

    # Forms
    path('forms/', FormListCreateView.as_view(), name='form-list-create'),
    path('forms/<int:pk>/', FormRetrieveUpdateDeleteAPIView.as_view(), name='form-detail'),
    
    path("client/modules/",ClientModuleListAPIView.as_view(),name="client-modules-list"),
    path("client/modules/<int:pk>/", ClientModuleRetrieveAPIView.as_view()),

    # ✅ Client Permission Control
    path('client-permissions/', ClientPermissionControlAPIView.as_view()), #SA
    # ✅ UPDATE BY ID
    path('client-permissions/<int:pk>/', ClientPermissionUpdateAPIView.as_view()), #SA

    path("client-permissions/bulk/", BulkClientPermissionAPIView.as_view()), #SA
    # ✅ single delete
    path("client-permissions/<str:client_code>/delete/", BulkClientPermissionAPIView.as_view()), #SA

    path('client-own-permission/', ClientPermissionViewAPIView.as_view()), #CA

    # ✅ Module Form Permissions
    path('module-form-permissions/', ModuleFormPermissionAPIView.as_view()),
    
    # Permissions
    path('menu/<int:role_id>/', RoleBasedMenuView.as_view(), name='role-menu'),
    path('permissions/', RolePermissionUpdateView.as_view(), name='role-permission'),
]

