from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from settings_app.utils import get_tenant_modules_and_forms, send_sms_to_all_users
from .models import CodePrefix
from .serializers import CodePrefixSerializer
from core.permissions import IsSuperAdminOrClientAdmin
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

class CodePrefixListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="List all code prefixes",
        operation_description="List all code prefixes",
        responses={
            200: openapi.Response(
                description="List of code prefixes",
                schema=CodePrefixSerializer(many=True)
            )
        }
    )
    def get(self, request):
        user = request.user
        client_key = None if user.role == "super_admin" else user.client_code

        prefixes = CodePrefix.objects.filter(
            is_active=True
        )

        serializer = CodePrefixSerializer(prefixes, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="Create a new code prefix",
        operation_description="Create a new code prefix",
        request_body=CodePrefixSerializer,
        responses={
            201: openapi.Response(
                description="Code prefix created successfully",
                schema=CodePrefixSerializer
            )
        }
    )
    def post(self, request):
        serializer = CodePrefixSerializer(
            data=request.data,
            context={"request": request}
        )

        if serializer.is_valid():
            prefix = serializer.save()
            return Response(
                CodePrefixSerializer(prefix).data,
                status=status.HTTP_201_CREATED
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CodePrefixDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Get a code prefix by ID",
        operation_description="Get a code prefix by ID",
        responses={
            200: openapi.Response(
                description="Code prefix details",
                schema=CodePrefixSerializer
            )
        }
    )
    def get_object(self, pk):
        return get_object_or_404(
            CodePrefix,
            pk=pk,
            is_active=True
        )

    def get(self, request, pk):
        user = request.user
        client_key = None if user.role == "super_admin" else user.client_code

        instance = self.get_object(pk, client_key)

        serializer = CodePrefixSerializer(instance)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="Update a code prefix by ID",
        operation_description="Update a code prefix by ID",
        request_body=CodePrefixSerializer,
        responses={
            200: openapi.Response(
                description="Code prefix updated successfully",
                schema=CodePrefixSerializer
            )
        }
    )
    def put(self, request, pk):
        user = request.user
        client_key = None if user.role == "super_admin" else user.client_code

        instance = self.get_object(pk, client_key)

        serializer = CodePrefixSerializer(
            instance,
            data=request.data,
            context={"request": request}
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_summary="Delete a code prefix by ID",
        operation_description="Delete a code prefix by ID",
        responses={
            204: openapi.Response(
                description="Code prefix deleted successfully"
            )
        }
    )
    def delete(self, request, pk):
        user = request.user
        client_key = None if user.role == "super_admin" else user.client_code

        instance = self.get_object(pk)
        instance.is_active = False
        instance.save()

        return Response(
            {"message": "Prefix disabled successfully."},
            status=status.HTTP_204_NO_CONTENT
        )

class ModuleFormListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="List all modules and forms",
        operation_description="List all modules and forms",
        responses={
            200: openapi.Response(
                description="List of modules and forms"
            )
        }
    )
    def get(self, request):
        data = get_tenant_modules_and_forms()
        return Response(data)

class SendSMSToAllUsers(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Send SMS to all users",
        operation_description="Send SMS to all users",
        responses={
            200: openapi.Response(
                description="SMS sent successfully"
            )
        }
    )
    def post(self, request):
        send = send_sms_to_all_users()
        return Response(
            {"message": "SMS sent to all users successfully."},
            status=status.HTTP_200_OK
        )

