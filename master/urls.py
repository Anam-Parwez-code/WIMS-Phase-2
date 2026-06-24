from django.urls import path
from .views import (
    BranchDropdownAPIView, DepartmentListCreateAPIView, DepartmentDetailAPIView,
    DesignationListCreateAPIView, DesignationDetailAPIView,
    CountryListCreateAPIView, CountryDetailAPIView, EmailConfigurationDetailAPIView, 
    EmailConfigurationListCreateAPIView, MasterDashboardAPIView, OrganizationBranchListAPIView, 
    SMSConfigurationDetailAPIView, SMSConfigurationListCreateAPIView,
    StateListCreateAPIView, StateDetailAPIView,
    CityListCreateAPIView, CityDetailAPIView,
    FollowUpMediumListCreateAPIView, FollowUpMediumDetailAPIView,
    InterestLevelListCreateAPIView, InterestLevelDetailAPIView,
    OrganizationListCreateAPIView, OrganizationDetailAPIView,
    BranchListCreateAPIView, BranchDetailAPIView,
    SourceListCreateAPIView, SourceDetailAPIView,
    StatusListCreateAPIView, StatusDetailAPIView,
    NationalityListCreateAPIView, NationalityDetailAPIView,
    FormDesignListCreateAPIView, FormDesignDetailAPIView,
    PaymentMethodListCreateAPIView, PaymentMethodDetailAPIView,
    
)

urlpatterns = [
    # Department
    path('departments/', DepartmentListCreateAPIView.as_view(), name='department-list-create'),
    path('departments/<int:pk>/', DepartmentDetailAPIView.as_view(), name='department-detail'),

    # Designation
    path('designations/', DesignationListCreateAPIView.as_view(), name='designation-list-create'),
    path('designations/<int:pk>/', DesignationDetailAPIView.as_view(), name='designation-detail'),

    path('countries/', CountryListCreateAPIView.as_view(), name='country-list-create'),
    path('countries/<int:pk>/', CountryDetailAPIView.as_view(), name='country-detail'),

    path('states/', StateListCreateAPIView.as_view(), name='state-list-create'),
    path('states/<int:pk>/', StateDetailAPIView.as_view(), name='state-detail'),

    path('cities/', CityListCreateAPIView.as_view(), name='city-list-create'),
    path('cities/<int:pk>/', CityDetailAPIView.as_view(), name='city-detail'),

    # FollowUpMedium endpoints
    path('followup-mediums/', FollowUpMediumListCreateAPIView.as_view(), name='followupmedium-list-create'),
    path('followup-mediums/<int:pk>/', FollowUpMediumDetailAPIView.as_view(), name='followupmedium-detail'),

    # InterestLevel endpoints
    path('interest-levels/', InterestLevelListCreateAPIView.as_view(), name='interestlevel-list-create'),
    path('interest-levels/<int:pk>/', InterestLevelDetailAPIView.as_view(), name='interestlevel-detail'),

    # Organization endpoints
    path('organizations/', OrganizationListCreateAPIView.as_view(), name='organization-list-create'),
    path('organizations/<int:pk>/', OrganizationDetailAPIView.as_view(), name='organization-detail'),
    path("organization/<int:organization_id>/branches/",OrganizationBranchListAPIView.as_view(),name="organization-branches"),
    
    # Branch
    path('branch/', BranchListCreateAPIView.as_view(), name='branch-list-create'),
    path('branch/<int:pk>/', BranchDetailAPIView.as_view(), name='branch-detail'),
    path("branches/dropdown/",BranchDropdownAPIView.as_view()),

    # Source
    path('source/', SourceListCreateAPIView.as_view(), name='source-list-create'),
    path('source/<int:pk>/', SourceDetailAPIView.as_view(), name='source-detail'),

    # Status
    path('status/', StatusListCreateAPIView.as_view(), name='status-list-create'),
    path('status/<int:pk>/', StatusDetailAPIView.as_view(), name='status-detail'),

    # Nationality URLs
    path('nationalities/', NationalityListCreateAPIView.as_view(), name='nationality-list-create'),
    path('nationalities/<int:pk>/', NationalityDetailAPIView.as_view(), name='nationality-detail'),

    # FormDesign URLs
    path('form-designs/', FormDesignListCreateAPIView.as_view(), name='formdesign-list-create'),
    path('form-designs/<int:pk>/', FormDesignDetailAPIView.as_view(), name='formdesign-detail'),

    # Email Configurations
    path('email-configurations/', EmailConfigurationListCreateAPIView.as_view(), name='emailconfigurations-list-create'),
    path('email-configurations/<int:pk>/', EmailConfigurationDetailAPIView.as_view(), name='emailconfigurations-detail'),

    # SMS Configurations
    path(
        "sms-configurations/",
        SMSConfigurationListCreateAPIView.as_view(),
        name="sms-config-list-create"
    ),
    path(
        "sms-configurations/<int:pk>/",
        SMSConfigurationDetailAPIView.as_view(),
        name="sms-config-detail"
    ),

    path('payment-methods/', PaymentMethodListCreateAPIView.as_view(), name='payment-method-list'),
    path('payment-methods/<int:pk>/', PaymentMethodDetailAPIView.as_view(), name='payment-method-detail'),
    path("dashboard/master-count/",MasterDashboardAPIView.as_view(),name="master-dashboard"),
]
