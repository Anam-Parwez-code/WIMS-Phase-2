from django.urls import path
from .views import (
    GenerateAdmissionReportAPIView,
    FeeDepositReportAPIView,
    OutstandingFeeReportAPIView,
    CourseWiseAdmissionReportAPIView,
    RegistrationReportAPIView,
    CertificateApprovalReportAPIView,
    EnquiryReportAPIView,
    FollowUpReportAPIView,
    AttendanceReportView,
    CourseTrackerReportView,
)

urlpatterns = [
    # Admission Reports
    path('admission-report/', GenerateAdmissionReportAPIView.as_view(), name='admission-report'),
    path('course-wise-admission/', CourseWiseAdmissionReportAPIView.as_view(), name='course-wise-admission'),
    
    # Fee Reports
    path('fee-deposit-report/', FeeDepositReportAPIView.as_view(), name='fee-deposit-report'),
    path('outstanding-fee-report/', OutstandingFeeReportAPIView.as_view(), name='outstanding-fee-report'),
    
    # Registration Reports
    path('registration-report/', RegistrationReportAPIView.as_view(), name='registration-report'),
    
    # Certificate Reports
    path('certificate-approval-report/', CertificateApprovalReportAPIView.as_view(), name='certificate-approval-report'),

    path('enquiry/', EnquiryReportAPIView.as_view(), name='enquiry-report'),
    path('followup/', FollowUpReportAPIView.as_view(), name='followup-report'),
    path('attendance-report/', AttendanceReportView.as_view(), name='attendance-report'),
    path('course-report/', CourseTrackerReportView.as_view(), name='course-report'),
    
]
