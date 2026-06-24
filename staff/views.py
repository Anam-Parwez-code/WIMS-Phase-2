from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import RetrieveAPIView
from rest_framework import status
from .models import Employee, UserRole, StaffUser, Attendance
from .serializers import (
    BulkAttendanceSerializer, EmployeeSerializer, UserRoleSerializer,
    StaffUserSerializer, AttendanceSerializer, RoleMembersListSerializer, EmployeeByRoleSerializer, EmployeeDropdownSerializer
)
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from core import permissions
from rest_framework import permissions
from core.permissions import IsSuperAdmin, IsSuperAdminOrClientAdmin, IsClientAdminOnly   # Import IsSuperAdmin
from core.models import Client, ClientUser
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from core.dbrouter import get_client_db
from django.db import connection
from core.helper_function import get_branch_id
from django.contrib.auth import get_user_model
from django.db.models import Q

# EMPLOYEE
class EmployeeListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        
        employees = Employee.objects.filter(is_active=True)
        serializer = EmployeeSerializer(employees, many=True)
        return Response(serializer.data)

    def post(self, request):
        branch_id = get_branch_id(request)
        serializer = EmployeeSerializer(
            data=request.data,
            context={"request": request, "branch_id": branch_id}
        )
        if serializer.is_valid():
            emp = serializer.save()
            return Response(
                EmployeeSerializer(emp).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class EmployeeDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        return get_object_or_404(
            Employee.objects.select_related(
                'organization', 'department', 'designation'
            ),
            pk=pk,
            is_active=True
        )

    def get(self, request, pk):
        instance = self.get_object(pk)
        return Response(EmployeeSerializer(instance).data)

    def put(self, request, pk):
        instance = self.get_object(pk)
        branch_id = get_branch_id(request)
        if not branch_id:
            branch_id = request.data.get("branch")
            

        serializer = EmployeeSerializer(
            instance,
            data=request.data,
            context={"request": request, "branch_id": branch_id}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        instance = self.get_object(pk)

        # Soft delete
        instance.is_active = False
        instance.save(update_fields=["is_active"])

        return Response(
            {"message": "Employee soft deleted successfully."},
            status=status.HTTP_204_NO_CONTENT
        )


# STAFF USER

class StaffUserListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="List Staff Users",
        operation_description="Returns active staff users.",
        responses={200: StaffUserSerializer(many=True)}
    )
    def get(self, request):

        organization_id = request.query_params.get("organization")
        branch_id = request.query_params.get("branch")
        search = request.query_params.get("search")

        users = StaffUser.objects.filter(
            is_active=True
        ).select_related(
            "employee",
            "employee__organization",
            "employee__branch",
            "admission",
            "admission__organization",
            "admission__branch",
            "role"
        )

        # =====================================
        # ORGANIZATION FILTER
        # =====================================

        if organization_id:
            users = users.filter(
                Q(employee__organization_id=organization_id) |
                Q(admission__organization_id=organization_id)
            )

        # =====================================
        # BRANCH FILTER
        # =====================================

        if branch_id:
            users = users.filter(
                Q(employee__branch_id=branch_id) |
                Q(admission__branch_id=branch_id)
            )

        # =====================================
        # SEARCH FILTER
        # =====================================

        if search:
            users = users.filter(
                Q(username__icontains=search) |
                Q(employee__name__icontains=search) |
                Q(admission__candidate_name__icontains=search) |
                Q(admission__admission_code__icontains=search)
            )

        serializer = StaffUserSerializer(
            users.distinct(),
            many=True
        )

        return Response(serializer.data)


    @swagger_auto_schema(
        operation_summary="Create Staff User",
        operation_description="Creates a new staff user. Returns credentials ONLY on creation.",
        request_body=StaffUserSerializer,
        responses={
            201: StaffUserSerializer,
            400: "Invalid data"
        }
    )
    def post(self, request):
        serializer = StaffUserSerializer(
            data=request.data,
            context={"request": request}
        )

        if serializer.is_valid():
            staff_user = serializer.save()
            response_data = StaffUserSerializer(staff_user).data

            # ✅ Return raw password ONCE
            response_data["credentials"] = {
                "username": staff_user.username,
                "password": request.data.get("password"),
            }

            return Response(
                response_data,
                status=status.HTTP_201_CREATED
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class StaffUserDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        return get_object_or_404(
            StaffUser,
            pk=pk,
            is_active=True
        )

    def get(self, request, pk):
        instance = self.get_object(pk)
        return Response(StaffUserSerializer(instance).data)

    def put(self, request, pk):
        instance = self.get_object(pk)

        serializer = StaffUserSerializer(
            instance,
            data=request.data,
            context={"request": request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):

        instance = self.get_object(pk)

        # Soft delete StaffUser
        instance.is_active = False
        instance.save(update_fields=["is_active"])

        # Soft delete Django User
        User = get_user_model()

        User.objects.filter(
            email=instance.username
        ).update(is_active=False)

        # Soft delete ClientUser
        ClientUser.objects.filter(
            user_id=instance.username
        ).update(is_active=False)

        return Response(
            {
                "message": "Staff user deleted successfully."
            },
            status=status.HTTP_200_OK
        )

# USER ROLE
class UserRoleListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        roles = UserRole.objects.filter(is_active=True)
        serializer = UserRoleSerializer(roles, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = UserRoleSerializer(
            data=request.data,
            context={"request": request}
        )
        if serializer.is_valid():
            role = serializer.save()
            return Response(
                UserRoleSerializer(role).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserRoleDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        return get_object_or_404(
            UserRole,
            pk=pk,
            is_active=True
        )

    def get(self, request, pk):
        role = self.get_object(pk)
        return Response(UserRoleSerializer(role).data)

    def put(self, request, pk):
        role = self.get_object(pk)

        serializer = UserRoleSerializer(
            role,
            data=request.data,
            context={"request": request}
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        role = self.get_object(pk)

        # 🔥 Soft delete
        role.is_active = False
        role.save(update_fields=["is_active"])

        return Response(
            {"message": "User role deleted successfully."},
            status=status.HTTP_204_NO_CONTENT
        )


# ATTENDANCE
class AttendanceListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        records = Attendance.objects.filter(
            is_active=True
        ).select_related(
            "employee"
        )

        # =====================================
        # ORGANIZATION FILTER
        # =====================================

        organization_id = request.query_params.get(
            "organization"
        )

        if organization_id:

            records = records.filter(
                employee__organization_id=organization_id
            )

        # =====================================
        # BRANCH FILTER
        # =====================================

        branch_id = request.query_params.get(
            "branch"
        )

        if branch_id:

            records = records.filter(
                employee__branch_id=branch_id
            )

        serializer = AttendanceSerializer(
            records,
            many=True
        )

        return Response(serializer.data)

    def post(self, request):
        # BULK attendance
        if "records" in request.data:
            serializer = BulkAttendanceSerializer(
                data=request.data,
                context={"request": request}
            )
            serializer.is_valid(raise_exception=True)

            date = serializer.validated_data["date"]
            created = []

            for record in serializer.validated_data["records"]:
                emp_id = record["employee"]
                present = record.get("present", False)

                employee = get_object_or_404(Employee, id=emp_id, is_active=True)

                attendance, _ = Attendance.objects.update_or_create(
                    employee=employee,
                    date=date,
                    defaults={
                        "present": present,
                        "is_active": True
                    }
                )
                created.append(attendance)

            return Response(
                AttendanceSerializer(created, many=True).data,
                status=status.HTTP_201_CREATED
            )

        # SINGLE attendance
        serializer = AttendanceSerializer(
            data=request.data,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        attendance = serializer.save()

        return Response(
            AttendanceSerializer(attendance).data,
            status=status.HTTP_201_CREATED
        )

class AttendanceDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        return get_object_or_404(
            Attendance,
            pk=pk,
            is_active=True
        )

    def get(self, request, pk):
        record = self.get_object(pk)
        return Response(AttendanceSerializer(record).data)

    def put(self, request, pk):
        record = self.get_object(pk)

        serializer = AttendanceSerializer(
            record,
            data=request.data,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        record = self.get_object(pk)

        record.is_active = False
        record.save(update_fields=["is_active"])

        return Response(
            {"message": "Attendance soft deleted successfully."},
            status=status.HTTP_204_NO_CONTENT
        )

class EmployeeAttendanceHistoryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, employee_id):
        try:
            # 1️⃣ Verify employee exists
            employee = get_object_or_404(
                Employee,
                id=employee_id,
                is_active=True
            )

            # 2️⃣ Fetch attendance records
            records = Attendance.objects.filter(
                employee=employee,
                is_active=True
            ).order_by('-date')

            # 3️⃣ Optional date filtering
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')

            if start_date and end_date:
                records = records.filter(date__range=[start_date, end_date])

            serializer = AttendanceSerializer(records, many=True)

            return Response({
                "employee": {
                    "id": employee.id,
                    "name": getattr(employee, 'name', 'N/A'),
                },
                "history": serializer.data
            })

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class UserRoleMembersAPIView(RetrieveAPIView):
    """
    Returns all staff and students associated with a specific role ID.
    URL: /user-roles/<pk>/members/
    """
    queryset = UserRole.objects.filter(is_active=True)
    serializer_class = RoleMembersListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Since client field is removed,
        # just return active roles
        return UserRole.objects.filter(is_active=True)

# role based serach

class GetEmployeesByRoleAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        role_id = request.query_params.get('role_id')
        
        if not role_id:
            return Response({"error": "role_id query parameter is required."}, status=400)

        # Filter StaffUser by the provided role and ensure both staff and employee are active
        staff_members = StaffUser.objects.filter(
            role_id=role_id, 
            is_active=True, 
            employee__is_active=True
        ).select_related('employee', 'role')

        serializer = EmployeeByRoleSerializer(staff_members, many=True)
        return Response(serializer.data, status=200)

class GetEmployeesByDesignationAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        designation_id = request.query_params.get('designation_id')
        department_id = request.query_params.get('department_id')
        
        # Start with all active employees
        queryset = Employee.objects.filter(is_active=True)

        if designation_id:
            queryset = queryset.filter(designation_id=designation_id)
        
        if department_id:
            queryset = queryset.filter(department_id=department_id)

        # Optimization: Pull related names in one go
        queryset = queryset.select_related('designation', 'department')

        serializer = EmployeeDropdownSerializer(queryset, many=True)
        return Response(serializer.data, status=200)

        
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from .models import Employee
from .serializers import EmployeeSerializer


class EmployeeFilterAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Query Params:
        - organization_id (required)
        - branch_id (required)
        - designation_id (optional)
        """

        organization_id = request.query_params.get("organization_id")
        branch_id = request.query_params.get("branch_id")
        designation_id = request.query_params.get("designation_id")

        # Required validations
        if not organization_id:
            return Response(
                {"organization_id": "This field is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not branch_id:
            return Response(
                {"branch_id": "This field is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Base queryset
        employees = Employee.objects.filter(
            is_active=True,
            organization_id=organization_id,
            branch_id=branch_id
        ).select_related(
            "organization",
            "branch",
            "department",
            "designation",
            "country",
            "state",
            "city"
        )

        # Optional designation filter
        if designation_id:
            employees = employees.filter(
                designation_id=designation_id
            )

        serializer = EmployeeSerializer(employees, many=True)

        return Response(
            {
                "count": employees.count(),
                "results": serializer.data
            },
            status=status.HTTP_200_OK
        )
    

from datetime import timedelta

from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Employee


class EmployeeDashboardCountAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        organization_id = request.query_params.get(
            "organization_id"
        )

        branch_id = request.query_params.get(
            "branch_id"
        )

        queryset = Employee.objects.filter(
            is_active=True
        )

        # =====================================
        # ORGANIZATION FILTER
        # =====================================

        if organization_id:

            queryset = queryset.filter(
                organization_id=organization_id
            )

        # =====================================
        # BRANCH FILTER
        # =====================================

        if branch_id:

            queryset = queryset.filter(
                branch_id=branch_id
            )

        # =====================================
        # DATE CALCULATIONS
        # =====================================

        today = timezone.localdate()

        # Sunday → Saturday

        days_from_sunday = (
            today.weekday() + 1
        ) % 7

        week_start = today - timedelta(
            days=days_from_sunday
        )

        week_end = week_start + timedelta(
            days=6
        )

        month_start = today.replace(
            day=1
        )

        # =====================================
        # COUNTS
        # Using created_at__date
        # =====================================

        total_count = queryset.count()

        today_count = queryset.filter(
            created_at__date=today
        ).count()

        week_count = queryset.filter(
            created_at__date__range=[
                week_start,
                week_end
            ]
        ).count()

        month_count = queryset.filter(
            created_at__date__gte=month_start
        ).count()

        return Response({

            "success": True,

            "filters": {

                "organization_id":
                    organization_id,

                "branch_id":
                    branch_id
            },

            "counts": {

                "total_employees":
                    total_count,

                "today_employees":
                    today_count,

                "week_employees":
                    week_count,

                "month_employees":
                    month_count
            },

            "date_range": {

                "today":
                    today,

                "week_start":
                    week_start,

                "week_end":
                    week_end,

                "month_start":
                    month_start
            }
        })


from datetime import timedelta

from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Attendance
from staff.models import Employee


class StaffAttendanceDashboardAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        organization_id = request.query_params.get(
            "organization_id"
        )

        branch_id = request.query_params.get(
            "branch_id"
        )

        employee_id = request.query_params.get(
            "employee_id"
        )

        # =====================================
        # ATTENDANCE QUERYSET
        # =====================================

        queryset = Attendance.objects.select_related(
            "employee"
        ).filter(
            is_active=True,
            employee__is_active=True
        )

        # =====================================
        # EMPLOYEE QUERYSET
        # =====================================

        employee_queryset = Employee.objects.filter(
            is_active=True
        )

        # =====================================
        # ORGANIZATION FILTER
        # =====================================

        if organization_id:

            queryset = queryset.filter(
                employee__organization_id=
                organization_id
            )

            employee_queryset = employee_queryset.filter(
                organization_id=organization_id
            )

        # =====================================
        # BRANCH FILTER
        # =====================================

        if branch_id:

            queryset = queryset.filter(
                employee__branch_id=
                branch_id
            )

            employee_queryset = employee_queryset.filter(
                branch_id=branch_id
            )

        # =====================================
        # EMPLOYEE FILTER
        # =====================================

        if employee_id:

            queryset = queryset.filter(
                employee_id=employee_id
            )

            employee_queryset = employee_queryset.filter(
                id=employee_id
            )

        # =====================================
        # DATE RANGE
        # =====================================

        today = timezone.localdate()

        days_from_sunday = (
            today.weekday() + 1
        ) % 7

        week_start = today - timedelta(
            days=days_from_sunday
        )

        week_end = week_start + timedelta(
            days=6
        )

        month_start = today.replace(
            day=1
        )

        # =====================================
        # EMPLOYEE COUNTS
        # =====================================

        total_employees = employee_queryset.count()

        employees_present_today = employee_queryset.filter(
            attendance__date=today,
            attendance__present=True,
            attendance__is_active=True
        ).distinct().count()

        employees_absent_today = (
            total_employees -
            employees_present_today
        )

        # =====================================
        # OVERALL ATTENDANCE COUNTS
        # =====================================

        total_records = queryset.count()

        total_present = queryset.filter(
            present=True
        ).count()

        total_absent = queryset.filter(
            present=False
        ).count()

        attendance_percentage = 0

        if total_records > 0:

            attendance_percentage = round(
                (
                    total_present /
                    total_records
                ) * 100,
                2
            )

        # =====================================
        # TODAY
        # =====================================

        today_queryset = queryset.filter(
            date=today
        )

        # =====================================
        # WEEK
        # =====================================

        week_queryset = queryset.filter(
            date__range=[
                week_start,
                week_end
            ]
        )

        # =====================================
        # MONTH
        # =====================================

        month_queryset = queryset.filter(
            date__gte=month_start
        )

        return Response({

            "success": True,

            "filters": {

                "organization_id":
                    organization_id,

                "branch_id":
                    branch_id,

                "employee_id":
                    employee_id
            },

            # =====================================
            # EMPLOYEE SUMMARY
            # =====================================

            "employee_summary": {

                "total_employees":
                    total_employees,

                "present_today":
                    employees_present_today,

                "absent_today":
                    employees_absent_today
            },

            # =====================================
            # OVERALL ATTENDANCE
            # =====================================

            "overall": {

                "total_records":
                    total_records,

                "present":
                    total_present,

                "absent":
                    total_absent,

                "attendance_percentage":
                    attendance_percentage
            },

            # =====================================
            # TODAY
            # =====================================

            "today": {

                "total":
                    today_queryset.count(),

                "present":
                    today_queryset.filter(
                        present=True
                    ).count(),

                "absent":
                    today_queryset.filter(
                        present=False
                    ).count()
            },

            # =====================================
            # WEEK
            # =====================================

            "week": {

                "total":
                    week_queryset.count(),

                "present":
                    week_queryset.filter(
                        present=True
                    ).count(),

                "absent":
                    week_queryset.filter(
                        present=False
                    ).count()
            },

            # =====================================
            # MONTH
            # =====================================

            "month": {

                "total":
                    month_queryset.count(),

                "present":
                    month_queryset.filter(
                        present=True
                    ).count(),

                "absent":
                    month_queryset.filter(
                        present=False
                    ).count()
            },

            # =====================================
            # DATE RANGE
            # =====================================

            "date_range": {

                "today":
                    today,

                "week_start":
                    week_start,

                "week_end":
                    week_end,

                "month_start":
                    month_start
            }
        })





        