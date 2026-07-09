from django.urls import path
from .views import (
    AttendanceReportAPIView,
    CourseTrackerReportAPIView,
    ExportAdmissionReportExcelAPIView,
    ExportAdmissionReportPDFAPIView,
    ExportAttendanceReportExcelAPIView,
    ExportAttendanceReportPDFAPIView,
    ExportCertificateApprovalExcelAPIView,
    ExportCertificateApprovalPDFAPIView,
    ExportCourseTrackerExcelAPIView,
    ExportCourseTrackerPDFAPIView,
    ExportCourseWiseAdmissionExcelAPIView,
    ExportCourseWiseAdmissionPDFAPIView,
    ExportEnquiryReportExcelAPIView,
    ExportEnquiryReportPDFAPIView,
    ExportFeeDepositReportExcelAPIView,
    ExportFeeDepositReportPDFAPIView,
    ExportFollowUpReportExcelAPIView,
    ExportFollowUpReportPDFAPIView,
    ExportOutstandingFeeReportExcelAPIView,
    ExportOutstandingFeeReportPDFAPIView,
    ExportRegistrationReportExcelAPIView,
    ExportRegistrationReportPDFAPIView,
    ExportStudentAttendanceReportExcelAPIView,
    ExportStudentAttendanceReportPDFAPIView,
    GenerateAdmissionReportAPIView,
    FeeDepositReportAPIView,
    OutstandingFeeReportAPIView,
    CourseWiseAdmissionReportAPIView,
    RegistrationReportAPIView,
    CertificateApprovalReportAPIView,
    EnquiryReportAPIView,
    FollowUpReportAPIView,
    StudentAttendanceReportAPIView,
    
    
)

urlpatterns = [
    # Admission Reports
    path('admission-report/', GenerateAdmissionReportAPIView.as_view(), name='admission-report'),
    path("admission/report/export/excel/",ExportAdmissionReportExcelAPIView.as_view()),
    path("admission/report/export/pdf/",ExportAdmissionReportPDFAPIView.as_view()),


    path('course-wise-admission/', CourseWiseAdmissionReportAPIView.as_view(), name='course-wise-admission'),
    path("reports/course-wise-admission/export/excel/",ExportCourseWiseAdmissionExcelAPIView.as_view()),
    path("reports/course-wise-admission/export/pdf/",ExportCourseWiseAdmissionPDFAPIView.as_view()),

    # Fee Reports
    path('fee-deposit-report/', FeeDepositReportAPIView.as_view(), name='fee-deposit-report'),
    path("reports/fee/export/excel/", ExportFeeDepositReportExcelAPIView.as_view()),
    path("reports/fee/export/pdf/",ExportFeeDepositReportPDFAPIView.as_view()),


    path('outstanding-fee-report/', OutstandingFeeReportAPIView.as_view(), name='outstanding-fee-report'),
    path("reports/outstanding-fee-report/export/excel/",ExportOutstandingFeeReportExcelAPIView.as_view()),
    path("reports/outstanding-fee-report/export/pdf/",ExportOutstandingFeeReportPDFAPIView.as_view()),
    
    # Registration Reports
    path('registration-report/', RegistrationReportAPIView.as_view(), name='registration-report'),
    path("registration-report/export/excel/",ExportRegistrationReportExcelAPIView.as_view(),name="registration-report-export-excel"),
    path("registration-report/export/pdf/",ExportRegistrationReportPDFAPIView.as_view(),name="registration-report-export-pdf"),

    # Certificate Reports
    path('certificate-approval-report/', CertificateApprovalReportAPIView.as_view(), name='certificate-approval-report'),
    path("reports/certificate-approval-report/export/excel/",ExportCertificateApprovalExcelAPIView.as_view()),
    path("reports/certificate-approval-report/export/pdf/",ExportCertificateApprovalPDFAPIView.as_view()),


    path('enquiry/', EnquiryReportAPIView.as_view(), name='enquiry-report'),
    path("reports/enquiry-report/export/excel/",ExportEnquiryReportExcelAPIView.as_view()),
    path("reports/enquiry-report/export/pdf/",ExportEnquiryReportPDFAPIView.as_view()),


    path('followup/', FollowUpReportAPIView.as_view(), name='followup-report'),
    path("followup-report/export/excel/",ExportFollowUpReportExcelAPIView.as_view(),name="followup-report-export-excel"),
    path("followup-report/export/pdf/",ExportFollowUpReportPDFAPIView.as_view(),name="followup-report-export-pdf"),



    path('attendance-report/', AttendanceReportAPIView.as_view(), name='attendance-report'),
    path("attendance-report/export/excel/",ExportAttendanceReportExcelAPIView.as_view(),name="attendance-report-export-excel",),
    path("attendance-report/export/pdf/",ExportAttendanceReportPDFAPIView.as_view(),name="attendance-report-export-pdf",),


    path('course-report/', CourseTrackerReportAPIView.as_view(), name='course-report'),
    path("reports/course-tracker/export/excel/",ExportCourseTrackerExcelAPIView.as_view()),
    path("reports/course-tracker/export/pdf/",ExportCourseTrackerPDFAPIView.as_view()),


    path("student-attendance-report/",StudentAttendanceReportAPIView.as_view()),
    path("student-attendance-report/export/excel/",ExportStudentAttendanceReportExcelAPIView.as_view()),
    path("student-attendance-report/export/pdf/",ExportStudentAttendanceReportPDFAPIView.as_view())
    
]

