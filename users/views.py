from rest_framework import generics, status, permissions
from rest_framework.response import Response
from core.permissions import IsClientAdminOnly, IsSuperAdmin, IsSuperAdminOrClientAdmin
from users.authentication import JWTWithSessionAuthentication
from core.utils import log_audit
from django.db.models import F, ExpressionWrapper, DurationField
from core.models import AuditLog  # Add for IP address
from users.authentication import JWTWithSessionAuthentication
from .models import User, UserSession
from .serializers import SuperAdminSerializer, CustomTokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from datetime import datetime, timezone  # Add for expired_at
from core.utils import get_client_ip, log_audit, get_ip, get_ua  # Add for logging
from django.db.models import F, ExpressionWrapper, DurationField, Q
from core.models import AuditLog, Client, ErrorLog, UserActivityLog  # Add Client

class SuperAdminCreateAPIView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = SuperAdminSerializer
    permission_classes = []

    @swagger_auto_schema(
        operation_description="Create the initial SuperAdmin. Only allowed if no SuperAdmin exists.",
        responses={201: SuperAdminSerializer, 400: "SuperAdmin already exists"}
    )
    def post(self, request, *args, **kwargs):
        if User.objects.filter(role="super_admin").exists():
            return Response(
                {"error": "SuperAdmin already exists. Only one allowed."},
                status=status.HTTP_400_BAD_REQUEST
            )

        data = request.data.copy()
        data["role"] = "super_admin"
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

    @swagger_auto_schema(operation_description="Obtain a JWT token pair with custom claims.")
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

class LogoutView(APIView):
    authentication_classes = [JWTWithSessionAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Logout and deactivate the current session.",
        responses={200: openapi.Response(description="Logged out successfully.")}
    )
    def post(self, request):
        session_id = getattr(request.auth, "get", lambda x: None)("session_id")

        if session_id:
            UserSession.objects.filter(session_id=session_id).update(
                is_active=False,
                expired_at=datetime.now(timezone.utc)
            )
            log_audit(
                request,
                action="AdminLogout",
                details=f"User {request.user.email} logged out, session_id: {session_id}",
            )
        return Response({"detail": "Logged out successfully."})

class SessionHistoryAPIView(APIView):
    authentication_classes = [JWTWithSessionAuthentication]
    permission_classes = [IsSuperAdminOrClientAdmin]

    @swagger_auto_schema(
        operation_description="Retrieve session history. SuperAdmins see all; ClientAdmins see only their client.",
        manual_parameters=[
            openapi.Parameter('email', openapi.IN_QUERY, description="Filter by user email", type=openapi.TYPE_STRING),
            openapi.Parameter('client_code', openapi.IN_QUERY, description="Filter by client code", type=openapi.TYPE_STRING),
        ],
        responses={200: "List of session data with activities and error logs"}
    )
    def get(self, request):
        sessions = UserSession.objects.all()

        if request.user.role == "super_admin":
            sessions = sessions.exclude(user__role="super_admin")
        elif request.user.role == "client_admin":
            if not request.user.client_code:
                return Response({"success": False, "message": "Client admin has no client_code"}, status=400)
            sessions = sessions.filter(client_code=request.user.client_code)
        else:
            return Response({"success": False, "message": "Unauthorized"}, status=403)

        email = request.query_params.get("email")
        client_code = request.query_params.get("client_code")

        if email:
            sessions = sessions.filter(Q(user__email__iexact=email) | Q(client_user_id__iexact=email))

        if client_code:
            if request.user.role == "client_admin" and client_code != request.user.client_code:
                return Response({"success": False, "message": "Forbidden"}, status=403)
            sessions = sessions.filter(client_code=client_code)

        session_data = []
        now = datetime.now(timezone.utc)

        for session in sessions:
            if session.user:
                email = session.user.email
                role = session.user.role
                code = session.user.client_code
            else:
                email = session.client_user_id
                code = session.client_code
                role = "client_user" # Logic for role determination...

            login_audit = AuditLog.objects.filter(
                action__in=["AdminLoginSuccess", "ClientLogin"],
                details__contains=session.session_id,
            ).first()
            
            client = Client.objects.filter(client_code=code).first()
            end_time = session.expired_at or now
            duration = (end_time - session.created_at).total_seconds() / 60 if session.created_at else None

            user_activities = UserActivityLog.objects.filter(metadata__icontains=session.session_id)
            error_logs = ErrorLog.objects.filter(request_body__icontains=session.session_id)

            session_data.append({
                "session_id": session.session_id,
                "user_email": email,
                "user_role": role,
                "client_code": code,
                "client_name": client.client_name if client else None,
                "ip_address": login_audit.ip_address if login_audit else None,
                "login_time": session.created_at,
                "logout_time": session.expired_at,
                "duration_minutes": round(duration, 2) if duration else None,
                "user_activities": list(user_activities.values("activity", "metadata", "ip_address", "user_agent", "created_at")),
                "error_logs": list(error_logs.values("location", "message", "stack_trace", "request_body", "ip_address", "user_agent", "created_at")),
            })

        return Response({"success": True, "data": session_data}, status=status.HTTP_200_OK)

class ClientSessionHistoryAPIView(APIView):
    authentication_classes = [JWTWithSessionAuthentication]
    permission_classes = [IsClientAdminOnly]

    @swagger_auto_schema(
        operation_description="Client Admin view for their own client's session history.",
        manual_parameters=[
            openapi.Parameter('email', openapi.IN_QUERY, description="Filter by client user email", type=openapi.TYPE_STRING),
        ],
        responses={200: "Client-specific session data"}
    )
    def get(self, request):
        client_code = request.user.client_code
        if not client_code:
            return Response({"success": False, "message": "Missing client_code"}, status=400)

        sessions = UserSession.objects.filter(client_code=client_code)
        email = request.query_params.get("email")
        if email:
            sessions = sessions.filter(client_user_id__iexact=email)

        now = datetime.now(timezone.utc)
        session_data = []
        skipped = 0

        for session in sessions:
            try:
                # ... Identity and Log Logic as per your snippet ...
                session_data.append({
                    "session_id": session.session_id,
                    "user_email": session.client_user_id, # or user.email
                    "login_time": session.created_at,
                    # ... other fields ...
                })
            except Exception as e:
                skipped += 1
                continue

        return Response({"success": True, "data": session_data, "skipped_sessions": skipped}, status=status.HTTP_200_OK)
