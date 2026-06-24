from django.urls import path
from .views import (
    CodePrefixListCreateAPIView,
    CodePrefixDetailAPIView,
    ModuleFormListAPIView,
    SendSMSToAllUsers
)

urlpatterns = [
    path("prefixes/", CodePrefixListCreateAPIView.as_view()),
    path("prefixes/<int:pk>/", CodePrefixDetailAPIView.as_view()),
    path("modules-forms/", ModuleFormListAPIView.as_view()),
    path("send-sms/", SendSMSToAllUsers.as_view())

]
