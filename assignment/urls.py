from django.urls import path
from .views import *

urlpatterns = [
    path("teachers/", AssignmentTeachersAPIView.as_view()),
    path("batches/<int:trainer_id>/", AssignmentBatchesAPIView.as_view()),
    path("courses/<int:trainer_id>/<int:batch_id>/", AssignmentCoursesAPIView.as_view()),
    path("list/", AssignmentListAPIView.as_view()),
    path("save/", AssignmentSaveAPIView.as_view()),
    path("assignment/<int:pk>/",AssignmentDetailAPIView.as_view(),name="assignment-detail"),
    path("delete/<int:assignmentId>/", AssignmentDeleteAPIView.as_view()),
    path("download/<int:assignmentId>/", AssignmentDownloadAPIView.as_view()),

    # ==========================================
    # STUDENT ASSIGNMENTS
    # ==========================================

    path("student/assignments/",StudentAssignmentListAPIView.as_view()),

    # ==========================================
    # ASSIGNMENT SUBMISSION
    # ==========================================

    path("assignment/submission/save/",AssignmentSubmissionSaveAPIView.as_view()),
    path("assignment/submissions/",AssignmentSubmissionListAPIView.as_view()),
    path("assignment/submission/<int:submission_id>/",AssignmentSubmissionDetailAPIView.as_view()),
    path("course-batch/assignments/",CourseBatchAssignmentListAPIView.as_view()),
    path("assignment/submission/student-list/",AssignmentSubmissionStudentListAPIView.as_view()),
    path("student/assignments/course-batch/",StudentAssignmentsByCourseBatchAPIView.as_view()),
    path("submission/delete/<int:pk>/",AssignmentSubmissionDeleteAPIView.as_view()),
    path("submission/review/<int:pk>/",AssignmentReviewAPIView.as_view()),
    path("assignment-review/dashboard-count/",AssignmentReviewDashboardAPIView.as_view(),name="assignment-review-dashboard-count"),
    

]

