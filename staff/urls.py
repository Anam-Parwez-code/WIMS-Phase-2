from django.urls import path
from .views import *

urlpatterns = [
    # Employee
    path('employees/', EmployeeListCreateAPIView.as_view(), name='employee-list-create'),
    path('employees/<int:pk>/', EmployeeDetailAPIView.as_view(), name='employee-detail'),
    path("employees/filter/",EmployeeFilterAPIView.as_view(),name="employee-filter"),

    # User Role
    path('user-roles/', UserRoleListCreateAPIView.as_view(), name='user-role-list-create'),
    path('user-roles/<int:pk>/', UserRoleDetailAPIView.as_view(), name='user-role-detail'),
# --- The New API Path ---
    path('user-roles/<int:pk>/members/', UserRoleMembersAPIView.as_view(), name='user-role-members'),
    
    # Staff User
    path('users/', StaffUserListCreateAPIView.as_view(), name='staffuser-list-create'),
    path('users/<int:pk>/', StaffUserDetailAPIView.as_view(), name='staffuser-detail'),

    # Attendance
    path('attendance/', AttendanceListCreateAPIView.as_view(), name='attendance-list-create'),
    path('attendance/<int:pk>/', AttendanceDetailAPIView.as_view(), name='attendance-detail'),
    path('attendance/employee/<int:employee_id>/', EmployeeAttendanceHistoryAPIView.as_view(), name='employee-attendance-history'),

    # Role based search
    path('employees/by-role/', GetEmployeesByRoleAPIView.as_view(), name='employees-by-role'),
    path('get-employees-by-designation/', GetEmployeesByDesignationAPIView.as_view(), name='get_employees_by_designation'),

    path("employee/dashboard-count/",EmployeeDashboardCountAPIView.as_view(),name="employee-dashboard-count"),
    path("staff-attendance/dashboard-count/",StaffAttendanceDashboardAPIView.as_view(),name="staff-attendance-dashboard-count"),

]
