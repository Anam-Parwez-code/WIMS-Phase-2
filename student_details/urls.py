from django.urls import path
from .views import (
    EnquiryAPIView, EnquiryDashboardCountAPIView, EnquiryFollowUpDetailAPIView, EnquiryFollowUpListAPIView, EnquiryFollowUpSaveAPIView, FollowUpDashboardCountAPIView, RegistrationAPIView,
    RegistrationBulkImportView, RegistrationExportView, PublicRegistrationAPIView
)

urlpatterns = [
    path('enquiries/', EnquiryAPIView.as_view()),
    path('enquiries/<int:pk>/', EnquiryAPIView.as_view()),

    # =====================================
    # FETCH ENQUIRY DETAILS
    # =====================================

    path("enquiry/followup/details/<int:enquiry_id>/",EnquiryFollowUpDetailAPIView.as_view()),

    # =====================================
    # SAVE FOLLOWUP
    # =====================================

    path("enquiry/followup/save/",EnquiryFollowUpSaveAPIView.as_view()),

    # =====================================
    # FOLLOWUP LIST
    # =====================================

    path("enquiry/followups/",EnquiryFollowUpListAPIView.as_view()),


    path("enquiry/dashboard-count/",EnquiryDashboardCountAPIView.as_view(),name="enquiry-dashboard-count"),
    path("followup/dashboard-count/",FollowUpDashboardCountAPIView.as_view(),name="followup-dashboard-count"),



    path('registrations/', RegistrationAPIView.as_view()),
    path('registrations/<int:pk>/', RegistrationAPIView.as_view()),
    path('registrations/bulk-import/', RegistrationBulkImportView.as_view()),
    path('registrations/export/', RegistrationExportView.as_view()),
    path('public-register/', PublicRegistrationAPIView.as_view()),
]

