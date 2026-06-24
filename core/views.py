import os
import json
import traceback
import pandas as pd
import psycopg2
from rest_framework_simplejwt.exceptions import TokenError
from django.conf import settings
from django.http import HttpResponse
from django.db import connections
from django.db.models import Q
from django.db.utils import OperationalError
from django.core.management import call_command

from rest_framework import generics, status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from core.models import Client
from core.serializers import ClientSerializer
from core.permissions import IsSuperAdmin
from core.utils import (
    migrate_client_db,
    log_audit,
    get_client_ip,
)

from users.serializers import CustomTokenObtainPairSerializer

from .models import AuditLog, UserActivityLog, ErrorLog, Client
from .serializers import (
    ClientSelectSerializer,
    ClientLoginSerializer,
    ClientSerializer,
)
from .utils import (
    decrypt_value,
    inject_tenant_db_config,
    test_db_connection,
    log_activity,
    log_error,
)



class ClientListCreateUpdateAPIView(generics.ListCreateAPIView, generics.UpdateAPIView):
    queryset = Client.objects.filter(is_active=True)
    serializer_class = ClientSerializer
    permission_classes = [IsAuthenticated, IsSuperAdmin]   # ✅ Require JWT + super_admin

    @swagger_auto_schema(operation_description="List all active clients or create a new one.")
    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    @swagger_auto_schema(operation_description="Update an existing client.")
    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

class ClientDeleteAPIView(generics.DestroyAPIView):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    permission_classes = [IsAuthenticated, IsSuperAdmin]   # ✅ Require JWT + super_admin

    @swagger_auto_schema(
        operation_description="Soft delete a client by setting is_active to False.",
        responses={200: openapi.Response(description="Client deleted successfully")}
    )
    def delete(self, request, *args, **kwargs):
        client = self.get_object()
        client.is_active = False
        client.save()
        return Response({"message": "Client deleted successfully"}, status=status.HTTP_200_OK)

class ClientSearchAPIView(generics.ListAPIView):
    serializer_class = ClientSerializer
    permission_classes = [IsAuthenticated, IsSuperAdmin]   # ✅ Require JWT + super_admin

    @swagger_auto_schema(
        operation_description="Search clients by name or code and filter by active status.",
        manual_parameters=[
            openapi.Parameter('search', openapi.IN_QUERY, description="Search term for name or code", type=openapi.TYPE_STRING),
            openapi.Parameter('is_active', openapi.IN_QUERY, description="Filter by active status (true/false)", type=openapi.TYPE_BOOLEAN),
        ]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    def get_queryset(self):
        qs = Client.objects.all()
        search_term = self.request.query_params.get("search")
        is_active = self.request.query_params.get("is_active", "true").lower() == "true"

        if search_term:
            qs = qs.filter(client_name__icontains=search_term) | qs.filter(client_code__icontains=search_term)

        qs = qs.filter(is_active=is_active)
        return qs

class ClientExportAPIView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsSuperAdmin]   # ✅ Require JWT + super_admin

    @swagger_auto_schema(
        operation_description="Export all active clients to an Excel file.",
        responses={200: "Binary excel file (application/vnd.ms-excel)"}
    )
    def get(self, request, *args, **kwargs):
        clients = Client.objects.filter(is_active=True).values()
        df = pd.DataFrame(clients)

        # ✅ Convert timezone-aware datetimes to naive
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col] = df[col].dt.tz_localize(None)

        # ✅ Save Excel to server
        export_path = os.path.join(settings.BASE_DIR, "exports")  # folder 'exports' in project root
        os.makedirs(export_path, exist_ok=True)
        file_path = os.path.join(export_path, "clients.xlsx")
        df.to_excel(file_path, index=False)

        response = HttpResponse(content_type="application/vnd.ms-excel")
        response["Content-Disposition"] = "attachment; filename=clients.xlsx"
        df.to_excel(response, index=False)
        return response

class ClientRetrieveAPIView(generics.RetrieveAPIView):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    permission_classes = [IsAuthenticated, IsSuperAdmin]   # ✅ Require JWT + super_admin
    lookup_field = "pk" 

    @swagger_auto_schema(operation_description="Retrieve a specific client by ID.")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

class MigrateTenantsAPIView(APIView):
    permission_classes = [IsAuthenticated, IsSuperAdmin]   # ✅ Require JWT + super_admin

    @swagger_auto_schema(
        operation_description="Trigger the 'migrate_tenants' management command via API.",
        manual_parameters=[
            openapi.Parameter('client_code', openapi.IN_PATH, description="Client code", type=openapi.TYPE_STRING),
        ]
    )
    def post(self, request, client_code=None):
        """
        Trigger the 'migrate_tenants' management command via API.
        If client_code is provided, runs for that client only.
        """

        if client_code:
            try:
                client = Client.objects.get(client_code=client_code, is_active=True)
            except Client.DoesNotExist:
                return Response({"error": "Client not found."}, status=404)

            db_key = f"tenant_{client.client_code}"


            # ✅ Inject tenant DB into settings if not present
            if db_key not in settings.DATABASES:
                settings.DATABASES[db_key] = {
                    "ENGINE": "django.db.backends.postgresql",
                    "NAME": client.database_name,  # Must match PGAdmin DB
                    "USER": client.db_user,
                    "PASSWORD": client.db_password,
                    "HOST": client.db_host,
                    "PORT": client.db_port,
                }



            # ✅ Check if DB connection exists in settings
            if db_key not in settings.DATABASES:
                return Response(
                    {"error": f"Database for client '{client.client_code}' is not configured/created."},
                    status=400
                )

            # Optionally: check if connection can be established
            try:
                connections[db_key].ensure_connection()
            except OperationalError:
                return Response(
                    {"error": f"Database '{client.database_name}' cannot be connected."},
                    status=400
                )

            # Call your existing management command for this tenant
            try:
                call_command("migrate_tenants", client_code)
                return Response({"success": f"Migrations applied for tenant '{client_code}'."})
            except Exception as e:
                return Response({"error": str(e)}, status=500)

        else:
            # For all tenants, optionally you can skip ones without DB configured
            try:
                call_command("migrate_tenants")
                return Response({"success": "Migrations applied for all tenants."})
            except Exception as e:
                return Response({"error": str(e)}, status=500)
            
class SelectClientAPIView(APIView):
    """
    POST /api/core/SelectClient/
    Body: {"client_code": "client27"}
    """
    permission_classes = [permissions.AllowAny]  # selection happens pre-login

    @swagger_auto_schema(
        operation_description="Select a client code to establish a session and get a system token.",
        request_body=ClientSelectSerializer,
        responses={200: "Token and client details", 400: "Invalid client code"}
    )
    def post(self, request):
        serializer = ClientSelectSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"Success": False, "Message": serializer.errors.get("client_code", ["Invalid input"])[0]},
                status=status.HTTP_400_BAD_REQUEST
            )

        client_code = serializer.validated_data["client_code"].strip()

        try:
            # 1) Validate client (is_active=True)
            client = Client.objects.filter(
                Q(client_code__iexact=client_code),
                Q(is_active=True)
            ).first()

            if not client:
                log_audit(request, action="ClientSelectFailed", details=f"Invalid code: {client_code}")
                return Response(
                    {"Success": False, "Message": "Invalid client code, please try again."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 2) Inject DB and test connection
            db_key = inject_tenant_db_config(client)
            if not test_db_connection(db_key):
                log_audit(request, action="ClientSelectFailed", details=f"Cannot connect DB for {client_code}")
                return Response(
                    {"Success": False, "Message": "Unable to connect to the database, please try again."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 3) Generate JWT (dummy/system user)
            dummy_user = request.user if request.user.is_authenticated else None
            if not dummy_user:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                dummy_user, _ = User.objects.get_or_create(
                    email="system@wims.com",
                    defaults={
                        "first_name": "System",
                        "last_name": "User",
                        "role": "super_admin",
                        "is_active": True,
                        "is_staff": True,
                        "is_superuser": True,
                    }
                )

            token = CustomTokenObtainPairSerializer.get_token(dummy_user)
            token["client_code"] = client.client_code
            token["database_name"] = client.database_name

            # ✅ Response with only the required fields
            return Response(
                {
                    "Success": True,
                    "Message": "Client selected successfully.",
                    "client_id": str(client.id),
                    "client_name": client.client_name,
                    "client_code": client.client_code,
                    "database_name": client.database_name,
                    "client_logo": getattr(client, "client_logo", None),
                    "expiry_date": getattr(client, "expiry_date", None),
                    "email": client.email,
                    "is_active": client.is_active,
                    "token": str(token.access_token),
                },
                status=status.HTTP_200_OK
            )

        except Exception as e:
            return Response(
                {"Success": False, "Message": f"Unexpected error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ValidateClientCodeAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(
        operation_description="Validate client code.",
        manual_parameters=[
            openapi.Parameter('code', openapi.IN_QUERY, description="Client code", type=openapi.TYPE_STRING),
        ]
    )
    def get(self, request):
        code = request.query_params.get("code", "").strip()
        
        if not code:
            return Response({"valid": False, "message": "Client Code is required."}, status=400)
        exists = Client.objects.filter(client_code__iexact=code, is_active=True).exists()
        return Response({"valid": exists, "message": "OK" if exists else "Invalid client code"}, status=200)




class ClientLoginAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Process login within a specific client context.",
        request_body=ClientLoginSerializer,
        responses={200: "Login data and session info", 400: "Validation errors"}
    )

    
    def post(self, request, *args, **kwargs):
        serializer = ClientLoginSerializer(data=request.data, context={"request": request})

        if serializer.is_valid():
            data = serializer.validated_data

            ip = get_client_ip(request)   # ✅ use safe method
            ua = request.META.get("HTTP_USER_AGENT", "")

            AuditLog.objects.create(
                user=None,
                action="ClientLogin",
                details=f"User {data['user']['user_id']} logged into {data['client']['code']} (session={data['session_id']})",
                ip_address=ip,
                user_agent=ua,
            )

            UserActivityLog.objects.create(
                user=None,
                activity="ClientLogin",
                metadata=f"Client={data['client']['code']} User={data['user']['user_id']} Session={data['session_id']}",
                ip_address=ip,
                user_agent=ua,
            )

            return Response(data, status=status.HTTP_200_OK)

        ErrorLog.objects.create(
            user=None,
            location="ClientLoginAPIView",
            message="Client login failed",
            stack_trace=str(serializer.errors),
            #request_body=request.body.decode("utf-8") if request.body else "",
            request_body=str(request.data),  # <-- use request.data here
            ip_address=get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class ClientLogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if not refresh_token:
                return Response({"error": "Refresh token is required"}, status=status.HTTP_400_BAD_REQUEST)

            token = RefreshToken(refresh_token)
            token.blacklist()

            # Audit logging
            ip = get_client_ip(request)
            ua = request.META.get("HTTP_USER_AGENT", "")
            
            UserActivityLog.objects.create(
                user=None, # Changed to None if your model doesn't link User, or fix based on your model
                activity="Logout",
                metadata=f"User {request.user.id} logged out.",
                ip_address=ip,
                user_agent=ua,
            )

            return Response({"Success": True, "Message": "Successfully logged out."}, status=status.HTTP_205_RESET_CONTENT)

        except TokenError:
            # This catches "Token is blacklisted" or "Token is invalid"
            return Response({"Success": False, "Message": "Token is already invalid or blacklisted."}, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            # Fixed log_error by removing the unsupported 'user' argument
            log_error(
                location="ClientLogoutAPIView",
                message=f"Logout error for user {request.user.id}: {str(e)}",
                stack_trace=traceback.format_exc(),
                ip_address=get_client_ip(request),
                user_agent=request.META.get("HTTP_USER_AGENT", "")
            )
            return Response({"Success": False, "Message": "Unexpected error occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



from datetime import timedelta

from django.db.models import Count
from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from admission.models import AdmissionCourseBatch
from staff.models import StudentLoginHistory


class StudentLoginDashboardAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        organization_id = request.query_params.get(
            "organization_id"
        )

        branch_id = request.query_params.get(
            "branch_id"
        )

        batch_id = request.query_params.get(
            "batch_id"
        )

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

        queryset = StudentLoginHistory.objects.filter(
            is_active=True
        )

        # =====================================
        # ORGANIZATION
        # =====================================

        if organization_id:

            queryset = queryset.filter(
                organization_id=organization_id
            )

        # =====================================
        # BRANCH
        # =====================================

        if branch_id:

            queryset = queryset.filter(
                branch_id=branch_id
            )

        # =====================================
        # BATCH FILTER
        # =====================================

        if batch_id:

            admission_ids = AdmissionCourseBatch.objects.filter(
                batch_id=batch_id,
                is_active=True
            ).values_list(
                "admission_id",
                flat=True
            )

            queryset = queryset.filter(
                admission_id__in=admission_ids
            )

        # =====================================
        # COUNTS
        # =====================================

        total_count = queryset.count()

        today_count = queryset.filter(
            login_datetime__date=today
        ).count()

        week_count = queryset.filter(
            login_datetime__date__range=[
                week_start,
                week_end
            ]
        ).count()

        month_count = queryset.filter(
            login_datetime__date__gte=month_start
        ).count()

        return Response({

            "success": True,

            "filters": {

                "organization_id":
                    organization_id,

                "branch_id":
                    branch_id,

                "batch_id":
                    batch_id
            },

            "student_login_counts": {

                "total_logins":
                    total_count,

                "today_logins":
                    today_count,

                "week_logins":
                    week_count,

                "month_logins":
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




