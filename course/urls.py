from django.urls import path
from .views import (
    BatchDashboardCountAPIView, CourseBatchesAPIView, CourseDashboardCountAPIView, CourseListCreateAPIView, CourseDetailAPIView,
    BatchListCreateAPIView, BatchDetailAPIView,
    ModuleListCreateAPIView, ModuleDetailAPIView,
    TopicListCreateAPIView, TopicDetailAPIView,
    CourseTrackerListCreateAPIView, CourseTrackerDetailAPIView,
)

urlpatterns = [
    # Course URLs
    path('courses/', CourseListCreateAPIView.as_view(), name='course-list-create'),
    path('courses/<int:pk>/', CourseDetailAPIView.as_view(), name='course-detail'),

    # Batch URLs
    path('batches/', BatchListCreateAPIView.as_view(), name='batch-list-create'),
    path('batches/<int:pk>/', BatchDetailAPIView.as_view(), name='batch-detail'),

    path("courses/<int:course_id>/batches/", CourseBatchesAPIView.as_view()),

    # Module URLs
    path('modules/', ModuleListCreateAPIView.as_view(), name='module-list-create'),
    path('modules/<int:pk>/', ModuleDetailAPIView.as_view(), name='module-detail'),

    # Topic URLs
    path('topics/', TopicListCreateAPIView.as_view(), name='topic-list-create'),
    path('topics/<int:pk>/', TopicDetailAPIView.as_view(), name='topic-detail'),

    # Course Tracker URLs
    path('course-trackers/', CourseTrackerListCreateAPIView.as_view(), name='course-tracker-list-create'),
    path('course-trackers/<int:pk>/', CourseTrackerDetailAPIView.as_view(), name='course-tracker-detail'),

    path("course/dashboard-count/",CourseDashboardCountAPIView.as_view(),name="course-dashboard-count"),
    path("batch/dashboard-count/",BatchDashboardCountAPIView.as_view(),name="batch-dashboard-count"),


]
