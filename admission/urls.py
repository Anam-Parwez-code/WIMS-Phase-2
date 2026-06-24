from django.urls import path
from .views import *

urlpatterns = [
    # =====================================
    # Admission Management
    # =====================================
    path('admissions/', AdmissionAPIView.as_view(), name='admission-list-create'),
    path('admissions/<int:pk>/', AdmissionAPIView.as_view(), name='admission-detail-update-delete'),
    path('admissions/<int:pk>/download-id/', StudentIDCardDataAPIView.as_view(), name='student-id-download'),
    path("admission/course-batch/",AdmissionByCourseBatchAPIView.as_view(),name="admission-course-batch"),
    
    # For listing all or creating new
    path('attendance/', AttendanceAPIView.as_view(), name='attendance-list'),
    
    # For operations on a specific record (Update/Delete/Single Get)
    path('attendance/<int:pk>/', AttendanceAPIView.as_view(), name='attendance-detail'),
    # =====================================
    # STUDENT ATTENDANCE
    # =====================================

    path("student-attendance/",StudentAttendanceAPIView.as_view()),

    path("student-attendance/<int:admission_id>/",StudentAttendanceAPIView.as_view()),

    # =====================================
    # ATTENDANCE RECORD
    # =====================================

    path("attendance-record/",AttendanceRecordAPIView.as_view()),

    path("attendance-record/<int:pk>/",AttendanceRecordAPIView.as_view()),

    # =====================================
    # Certificate Approval Workflow
    # =====================================
    path('approval/students/', CertificateApprovalStudentSearchAPIView.as_view(), name='approval-student-search'),
    path('approval/student/<str:admissionNo>/', CertificateApprovalStudentDetailAPIView.as_view(), name='approval-student-detail'),
    path('approval/save/', CertificateApprovalSaveAPIView.as_view(), name='approval-save'), #Approval POST
    path('approval/list/', CertificateApprovalListAPIView.as_view(), name='approval-list'), #Approval GET
    path("certificate-approval/delete/<int:approval_id>/", CertificateApprovalDeleteAPIView.as_view(),name="certificate-approval-delete"), #DEL Not Required
    path("approval/detail/<int:approval_id>/",CertificateApprovalDetailAPIView.as_view(),name="certificate-approval-detail"), #Approval Detailed GET
    
    # =====================================
    # Certificate Issuance Workflow
    # =====================================
    path('issue/students/', CertificateIssueStudentListAPIView.as_view(), name='issue-student-list'), #All Student List
    path("students/fully-paid/", FullyPaidStudentsAPIView.as_view(), name="fully-paid-students"), #Fully Paid Student List
    path("students/pending-fees/", PendingFeeStudentsAPIView.as_view(), name="pending-fee-students"), #Partially Paid Student List
    path("fully-paid-pending-certificate/",FullyPaidPendingCertificateAPIView.as_view(),name="fully-paid-pending-certificate"),
    path("certificate-template/",CertificateTemplateListAPIView.as_view(),name="certificate-template-list-create"), #Certificate name POST,GET
    path("certificate-template/<int:pk>/",CertificateTemplateDetailAPIView.as_view(),name="certificate-template-detail"), #Certificate name PUT, DEL, GET

    path("certificate-template/preview/",CertificateTemplatePreviewAPIView.as_view(),name="certificate-template-preview"),
    path("certificate-template/branch/<int:branch_id>/",BranchCertificateTemplateAPIView.as_view(),name="branch-certificate-template"),
    path("certificate-template/current/",CurrentBranchCertificateTemplateAPIView.as_view(),name="current-certificate-template"),
    path("certificate/download/<int:certificate_id>/",DownloadCertificateAPIView.as_view(),name="download-certificate"),


    #path('issue/templates/', CertificateTemplateListAPIView.as_view(), name='issue-template-list'),
    #path('issue/templates/<int:pk>/', CertificateTemplateDetailAPIView.as_view()),
    path('issue/list/', CertificateIssueListAPIView.as_view(), name='issue-list'), #Issue GET
    path('issue/save/', CertificateIssueSaveAPIView.as_view(), name='issue-save'), #Issue POST
    path('issue/get/<int:certificateId>/', CertificateIssueDetailAPIView.as_view(), name='issue-get'), #Issue PUT, GET
    path('issue/delete/<int:certificateId>/', CertificateIssueDeleteAPIView.as_view(), name='issue-delete'), #Issue DEL
    path('issue/pending-certificates/',PendingCertificateIssueListAPIView.as_view(),name='pending-certificate-issue-list'), #Pending Certificates GET
    
    path('issue/print/<int:certificate_id>/', CertificateDataAPIView.as_view(), name='issue-print'), #Prints Certificate

    path("admission/dashboard-count/",AdmissionDashboardCountAPIView.as_view(),name="admission-dashboard-count"),
    path("certificate-approval/dashboard-count/",CertificateApprovalDashboardAPIView.as_view(),name="certificate-approval-dashboard-count"),
    path("certificate-issue/dashboard-count/",CertificateIssueDashboardAPIView.as_view(),name="certificate-issue-dashboard-count"),
    path("attendance/dashboard-count/",AttendanceDashboardAPIView.as_view(),name="attendance-dashboard-count"),
]
