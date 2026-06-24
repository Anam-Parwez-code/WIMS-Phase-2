# elearning_settings/views.py
from core.models import Client
from elearning_settings.helper import get_client_and_db
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import ClientPermissionControl, ModuleELearning, FormELearning, ModuleFormPermission, RolePermission
from .serializers import ClientPermissionControlSerializer, ModuleFormPermissionSerializer, ModuleSerializer, FormSerializer, RolePermissionSerializer
from core.permissions import IsSuperAdminOrClientAdmin, IsSuperAdmin
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.db import IntegrityError
from django.db import transaction
from rest_framework.exceptions import PermissionDenied, ValidationError


class ModuleListCreateView(APIView):

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), IsSuperAdmin()]  # ✅ only super_admin
        return [IsAuthenticated()]  # ✅ everyone can view

    def get(self, request):
        modules = ModuleELearning.objects.filter(is_active=True).order_by("order")
        serializer = ModuleSerializer(modules, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = ModuleSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()  # ✅ saved in default DB
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ModuleRetrieveUpdateDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get_object(self, pk):
        try:
            return ModuleELearning.objects.get(pk=pk, is_active=True)
        except ModuleELearning.DoesNotExist:
            return None
        
    # ✅ ADD THIS
    def get(self, request, pk):
        module = self.get_object(pk)
        if not module:
            return Response({"error": "Module not found"}, status=404)

        serializer = ModuleSerializer(module)
        return Response(serializer.data)

    def put(self, request, pk):
        module = self.get_object(pk)
        if not module:
            return Response({"error": "Module not found"}, status=404)

        serializer = ModuleSerializer(module, data=request.data)

        if serializer.is_valid():
            serializer.save()  # validation already handles case-insensitive uniqueness
            return Response(serializer.data)

        return Response(serializer.errors, status=400)


    

    def delete(self, request, pk):
        module = self.get_object(pk)
        if not module:
            return Response({"error": "Module not found"}, status=404)

        # ✅ Soft delete
        # module.is_active = False
        # module.save()
        

        # ✅ Optional: also deactivate forms under it
        # FormELearning.objects.filter(module=module).update(is_active=False)

        # return Response({"message": "Module deleted successfully"})
        with transaction.atomic():
            # ✅ Step 1: Delete all forms under module
            FormELearning.objects.filter(module=module).delete()

            # ✅ Step 2: Delete module
            module.delete()

        return Response({"message": "Module and its forms deleted successfully"})





class FormListCreateView(APIView):

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), IsSuperAdmin()]  # ✅ only super_admin
        return [IsAuthenticated()]  # ✅ all users can view

    def get(self, request):
        forms = FormELearning.objects.filter(is_active=True).order_by("order")
        serializer = FormSerializer(forms, many=True)
        return Response(serializer.data)

    def post(self, request):
        data = request.data.copy()

        form_name = data.get("form_name", "").strip().lower()
        module = data.get("module")

        existing = FormELearning.objects.filter(
            form_name__iexact=form_name,
            module_id=module
        ).first()

        if existing:
            if not existing.is_active:
                existing.delete()  # ✅ remove old record
            else:
                return Response(
                    {"error": "Form already exists"},
                    status=400
                )

        serializer = FormSerializer(data=data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)

        return Response(serializer.errors, status=400)


class FormRetrieveUpdateDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get_object(self, pk):
        try:
            return FormELearning.objects.get(pk=pk, is_active=True)
        except FormELearning.DoesNotExist:
            return None
        
    # ✅ ADD THIS
    def get(self, request, pk):
        form = self.get_object(pk)
        if not form:
            return Response({"error": "Form not found"}, status=404)

        serializer = FormSerializer(form)
        return Response(serializer.data)

    def put(self, request, pk):
        form = self.get_object(pk)

        serializer = FormSerializer(form, data=request.data)

        if serializer.is_valid():
            try:
                serializer.save()
                return Response(serializer.data)

            except IntegrityError:
                return Response(
                    {"error": "Form with this name already exists in this module."},
                    status=400
                )

        return Response(serializer.errors, status=400)

    def delete(self, request, pk):
        form = self.get_object(pk)
        if not form:
            return Response({"error": "Form not found"}, status=404)

        # ✅ Soft delete
        #form.is_active = False
        #form.save()
        form.delete()

        return Response({"message": "Form deleted successfully"})


class ClientModuleListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # ✅ FORCE default DB (super_admin data)
        modules = ModuleELearning.objects.using('default').all().order_by("order")

        serializer = ModuleSerializer(modules, many=True)
        return Response(serializer.data)

class ClientModuleRetrieveAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            # ✅ Always fetch from default DB
            module = ModuleELearning.objects.using('default').get(pk=pk)
        except ModuleELearning.DoesNotExist:
            return Response({"error": "Module not found"}, status=404)

        serializer = ModuleSerializer(module)
        return Response(serializer.data)
    

from rest_framework.exceptions import ValidationError

#Multiple
class ClientPermissionControlAPIView(APIView):
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def post(self, request):
        data = request.data

        # ✅ HANDLE BULK
        if isinstance(data, list):
            results = []

            for item in data:
                client_id = item.get("client")

                if not client_id:
                    results.append({
                        "client": None,
                        "status": "failed",
                        "error": "client is required"
                    })
                    continue

                instance = ClientPermissionControl.objects.filter(client_id=client_id).first()

                if instance:
                    serializer = ClientPermissionControlSerializer(
                        instance,
                        data=item,
                        partial=True
                    )
                    action = "updated"
                else:
                    serializer = ClientPermissionControlSerializer(data=item)
                    action = "created"

                if serializer.is_valid():
                    serializer.save()
                    results.append({
                        "client": client_id,
                        "status": action
                    })
                else:
                    results.append({
                        "client": client_id,
                        "status": "failed",
                        "error": serializer.errors
                    })

            return Response(results, status=200)

        # ✅ SINGLE OBJECT (existing logic)
        client_id = data.get("client")

        if not client_id:
            return Response({"error": "client is required"}, status=400)

        instance = ClientPermissionControl.objects.filter(client_id=client_id).first()

        if instance:
            serializer = ClientPermissionControlSerializer(instance, data=data, partial=True)
            action = "updated"
        else:
            serializer = ClientPermissionControlSerializer(data=data)
            action = "created"

        if serializer.is_valid():
            serializer.save()
            return Response({"message": f"Client permissions {action} successfully"})

        return Response(serializer.errors, status=400)

    def get(self, request):
        data = ClientPermissionControl.objects.all()
        return Response(ClientPermissionControlSerializer(data, many=True).data)
    
    def put(self, request):
        data = request.data

        if not isinstance(data, list):
            return Response({"error": "Expected a list"}, status=400)

        results = []

        for item in data:
            pk = item.get("id")

            if not pk:
                results.append({
                    "id": None,
                    "status": "failed",
                    "error": "id is required"
                })
                continue

            try:
                instance = ClientPermissionControl.objects.get(pk=pk)
            except ClientPermissionControl.DoesNotExist:
                results.append({
                    "id": pk,
                    "status": "failed",
                    "error": "Not found"
                })
                continue

            serializer = ClientPermissionControlSerializer(
                instance,
                data=item,
                partial=True
            )

            if serializer.is_valid():
                serializer.save()
                results.append({
                    "id": pk,
                    "status": "updated"
                })
            else:
                results.append({
                    "id": pk,
                    "status": "failed",
                    "error": serializer.errors
                })

        return Response(results, status=200)
    
    def delete(self, request):
        data = request.data

        if not isinstance(data, list):
            return Response({"error": "Expected a list of ids"}, status=400)

        results = []

        for item in data:
            pk = item.get("id")

            if not pk:
                results.append({
                    "id": None,
                    "status": "failed",
                    "error": "id is required"
                })
                continue

            try:
                instance = ClientPermissionControl.objects.get(pk=pk)
                instance.delete()
                results.append({
                    "id": pk,
                    "status": "deleted"
                })
            except ClientPermissionControl.DoesNotExist:
                results.append({
                    "id": pk,
                    "status": "failed",
                    "error": "Not found"
                })

        return Response(results, status=200)


#Single

class ClientPermissionUpdateAPIView(APIView):
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get(self, request, pk):
        try:
            instance = ClientPermissionControl.objects.get(pk=pk)
        except ClientPermissionControl.DoesNotExist:
            return Response({"error": "Not found"}, status=404)

        serializer = ClientPermissionControlSerializer(instance)
        return Response(serializer.data)
    
    # ✅ FIXED DELETE METHOD
    def delete(self, request, pk):
        try:
            instance = ClientPermissionControl.objects.get(pk=pk)
        except ClientPermissionControl.DoesNotExist:
            return Response({"error": "Not found"}, status=404)

        instance.delete()

        return Response(
            {"message": "Client permission deleted successfully"},
            status=status.HTTP_200_OK
        )

    def put(self, request, pk):
        try:
            instance = ClientPermissionControl.objects.get(pk=pk)
        except ClientPermissionControl.DoesNotExist:
            return Response({"error": "Not found"}, status=404)

        serializer = ClientPermissionControlSerializer(
            instance,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Client permissions updated successfully"})

        return Response(serializer.errors, status=400)




class BulkClientPermissionAPIView(APIView):
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def post(self, request):
        data = request.data.get("clients", [])

        if not isinstance(data, list):
            return Response({"error": "Invalid format"}, status=400)

        results = []

        for item in data:
            client_code = item.get("client_code")

            if not client_code:
                results.append({
                    "client_code": None,
                    "status": "failed",
                    "error": "client_code missing"
                })
                continue

            try:
                client = Client.objects.get(client_code=client_code)
            except Client.DoesNotExist:
                results.append({
                    "client_code": client_code,
                    "status": "failed",
                    "error": "invalid client"
                })
                continue

            # 🔥 get or create
            obj, created = ClientPermissionControl.objects.get_or_create(
                client=client,
                defaults={
                    "can_create": False,
                    "can_read": True,
                    "can_update": False,
                    "can_delete": False,
                    "is_active": True
                }
            )
            

            # 🔄 update fields
            obj.can_create = item.get("can_create", obj.can_create)
            obj.can_read = item.get("can_read", obj.can_read)
            obj.can_update = item.get("can_update", obj.can_update)
            obj.can_delete = item.get("can_delete", obj.can_delete)
            obj.is_active = item.get("is_active", obj.is_active)

            obj.save()

            results.append({
                "client_code": client_code,
                "status": "created" if created else "updated"
            })

        return Response({
            "message": "Bulk permissions processed",
            "results": results
        })
    
    def get(self, request):
        client_code = request.query_params.get("client_code")
        is_active = request.query_params.get("is_active")

        queryset = ClientPermissionControl.objects.all()

        # 🔍 Filter by client_code
        if client_code:
            queryset = queryset.filter(client__client_code=client_code)

        # 🔍 Filter by is_active
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")

        serializer = ClientPermissionControlSerializer(queryset, many=True)
        return Response(serializer.data)
    
    def delete(self, request, client_code=None):
        if client_code:
            # 🔥 single delete
            try:
                client = Client.objects.get(client_code=client_code)
            except Client.DoesNotExist:
                return Response({"error": "invalid client"}, status=404)

            deleted, _ = ClientPermissionControl.objects.filter(
                client=client
            ).delete()

            return Response({
                "message": "Deleted successfully",
                "client_code": client_code,
                "deleted": bool(deleted)
            })

        # 🔥 bulk delete (existing logic)
        client_codes = request.data.get("client_codes", [])

        if not isinstance(client_codes, list) or not client_codes:
            return Response({"error": "client_codes list required"}, status=400)

        results = []

        for code in client_codes:
            try:
                client = Client.objects.get(client_code=code)
                deleted, _ = ClientPermissionControl.objects.filter(client=client).delete()

                results.append({
                    "client_code": code,
                    "deleted": bool(deleted)
                })

            except Client.DoesNotExist:
                results.append({
                    "client_code": code,
                    "deleted": False,
                    "error": "invalid client"
                })

        return Response({
            "message": "Bulk delete processed",
            "results": results
        })
    


#GET for the client views their SA assigned permissions.

class ClientPermissionViewAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        client_code = request.auth.get("client_code")

        if not client_code:
            return Response({"error": "Client not found in token"}, status=400)

        # ✅ IMPORTANT: use same DB
        client = Client.objects.using("default").filter(
            client_code=client_code
        ).first()

        if not client:
            return Response({"error": "Invalid client"}, status=404)

        # ✅ Use client_id explicitly
        instance = ClientPermissionControl.objects.using("default").filter(
            client_id=client.id
        ).first()

        if not instance:
            return Response(
                {"error": "Permissions not configured"},
                status=404
            )

        return Response(
            ClientPermissionControlSerializer(instance).data
        )









# class ModuleFormPermissionAPIView(APIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request):
#         client, db_key, error = get_client_and_db(request)
#         print("POST DB:", db_key)

#         if error:
#             return error

#         client_permission = ClientPermissionControl.objects.filter(
#             client__client_code=client.client_code,
#             can_update=True,
#             is_active=True
#         ).first()

#         if not client_permission:
#             raise PermissionDenied("You are not allowed to configure permissions")

#         data = request.data.copy()

#         instance = ModuleFormPermission.objects.using(db_key).filter(
#             module_id=data.get("module"),
#             form_id=data.get("form"),
#             role_id=data.get("role")
#         ).first()

#         serializer = ModuleFormPermissionSerializer(
#             instance,
#             data=data,
#             partial=True,
#             context={"db_key": db_key}
#         ) if instance else ModuleFormPermissionSerializer(
#             data=data,
#             context={"db_key": db_key}
#         )

#         if serializer.is_valid():
#             serializer.save()
#             return Response({"message": "Permissions saved successfully"})

#         return Response(serializer.errors, status=400)

#     def get(self, request):
#         client, db_key, error = get_client_and_db(request)
#         print("GET DB:", db_key)

#         if error:
#             return error

#         data = ModuleFormPermission.objects.using(db_key).all()
#         print("COUNT:", data.count())
#         return Response(
#             ModuleFormPermissionSerializer(
#                 data,
#                 many=True,
#                 context={"db_key": db_key}
#             ).data
#         )



import jwt
from django.conf import settings

class ModuleFormPermissionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    # def post(self, request):
    #     client, db_key, error = get_client_and_db(request)

    #     if error:
    #         return error

    #     role_id = request.data.get("role_id")
    #     permissions = request.data.get("permissions", [])

    #     obj, created = ModuleFormPermission.objects.using(db_key).update_or_create(
    #         role_id=role_id,
    #         defaults={
    #             "permissions": permissions,
    #             "is_active": True
    #         }
    #     )

    #     return Response({
    #         "message": "Permissions saved successfully",
    #         "created": created
    #     })


    def post(self, request):
        client, db_key, error = get_client_and_db(request)

        if error:
            return error

        # 🔹 Extract token
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth_header.startswith("Bearer "):
            return Response({"error": "Missing token"}, status=401)

        token = auth_header.split(" ")[1]

        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return Response({"error": "Token expired"}, status=401)
        except jwt.InvalidTokenError:
            return Response({"error": "Invalid token"}, status=401)

        role = payload.get("role")
        is_admin = payload.get("is_admin")

        print("POST ROLE:", role)
        print("POST IS_ADMIN:", is_admin)

        # 🔴 Restrict: Only client_admin can POST
        if not (role == "client_admin" or is_admin):
            return Response(
                {"error": "Only client admin can assign permissions"},
                status=403
            )

        # 🔹 Proceed if admin
        role_id = request.data.get("role_id")
        permissions = request.data.get("permissions", [])

        obj, created = ModuleFormPermission.objects.using(db_key).update_or_create(
            role_id=role_id,
            defaults={
                "permissions": permissions,
                "is_active": True
            }
        )

        return Response({
            "message": "Permissions saved successfully",
            "created": created
        })





    # def get(self, request):
    #     client, db_key, error = get_client_and_db(request)

    #     if error:
    #         return error

    #     data = ModuleFormPermission.objects.using(db_key).all()

    #     return Response(
    #         ModuleFormPermissionSerializer(
    #             data,
    #             many=True,
    #             context={"db_key": db_key}
    #         ).data
    #     )

    

    def get(self, request):
        client, db_key, error = get_client_and_db(request)

        if error:
            return error

        # 🔹 Extract token manually
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth_header.startswith("Bearer "):
            return Response({"error": "Missing token"}, status=401)

        token = auth_header.split(" ")[1]

        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return Response({"error": "Token expired"}, status=401)
        except jwt.InvalidTokenError:
            return Response({"error": "Invalid token"}, status=401)

        role = payload.get("role")
        role_id = payload.get("role_id")

        print("ROLE:", role)
        print("ROLE_ID:", role_id)

        # 🔹 CASE 1: CLIENT ADMIN → ALL PERMISSIONS
        is_admin = payload.get("is_admin")
        print("IS_ADMIN:", is_admin)
        if role == "client_admin" or is_admin:
            queryset = ModuleFormPermission.objects.using(db_key).all()

        else:
            # 🔹 CASE 2: NORMAL USER → ONLY THEIR ROLE
            if not role_id:
                return Response({"error": "Role not found in token"}, status=400)

            queryset = ModuleFormPermission.objects.using(db_key).filter(
                role_id=role_id,
                is_active=True
            )

        return Response(
            ModuleFormPermissionSerializer(
                queryset,
                many=True,
                context={"db_key": db_key}
            ).data
        )


class RoleBasedMenuView(APIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        operation_description="Get role-based menu.",
        manual_parameters=[
            openapi.Parameter('client_code', openapi.IN_PATH, description="Client code", type=openapi.TYPE_STRING),
        ]
    )
    def get(self, request, role_id):
        # 1. Use 'form_id' (your specific PK name) or 'pk'
        allowed_form_ids = RolePermission.objects.filter(
            role_id=role_id
        ).values_list('form_id', flat=True)

        # 2. Update the lookup here to 'forms__form_id__in' or 'forms__pk__in'
        modules = ModuleELearning.objects.filter(
            forms__form_id__in=allowed_form_ids
        ).distinct().prefetch_related('forms')

        data = []
        for module in modules:
            # We use the serializer to get the base data
            module_data = ModuleSerializer(module).data
            
            # 3. Filter the nested forms to only those the user is allowed to see
            # Ensure the key matches what is in your Serializer (form_id)
            module_data['forms'] = [
                f for f in module_data['forms'] 
                if f['form_id'] in allowed_form_ids
            ]
            data.append(module_data)
            
        return Response(data)

class RolePermissionUpdateView(APIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        operation_description="Update role permissions.",
        request_body=RolePermissionSerializer,
        manual_parameters=[
            openapi.Parameter('client_code', openapi.IN_PATH, description="Client code", type=openapi.TYPE_STRING),
        ]
    )
    def post(self, request):
        # This allows you to assign permissions to a role
        serializer = RolePermissionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_description="Update role permissions.",
        request_body=RolePermissionSerializer,
        manual_parameters=[
            openapi.Parameter('client_code', openapi.IN_PATH, description="Client code", type=openapi.TYPE_STRING),
        ]
    )
    def patch(self, request):
        """Update existing permission for a specific role and form."""
        role_id = request.data.get('role')
        form_id = request.data.get('form')

        if not role_id or not form_id:
            return Response(
                {"error": "Both 'role' and 'form' IDs are required to update permissions."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Find the specific permission record
        permission_instance = get_object_or_404(RolePermission, role_id=role_id, form_id=form_id)
        
        # partial=True allows you to only send the fields you want to change
        serializer = RolePermissionSerializer(permission_instance, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_description="Delete role permissions.",
        manual_parameters=[
            openapi.Parameter('client_code', openapi.IN_PATH, description="Client code", type=openapi.TYPE_STRING),
        ]
    )
    def delete(self, request):
        """Remove a permission assignment for a specific role and form."""
        # You can get these from request.data (if sending a body) 
        # or request.query_params (if sending via URL ?role=1&form=2)
        role_id = request.data.get('role') or request.query_params.get('role')
        form_id = request.data.get('form') or request.query_params.get('form')

        if not role_id or not form_id:
            return Response(
                {"error": "Both 'role' and 'form' IDs are required to delete a permission."},
                status=status.HTTP_400_BAD_REQUEST
            )

        permission_instance = get_object_or_404(RolePermission, role_id=role_id, form_id=form_id)
        permission_instance.delete()
        
        return Response(
            {"message": "Permission successfully removed."}, 
            status=status.HTTP_204_NO_CONTENT
        )