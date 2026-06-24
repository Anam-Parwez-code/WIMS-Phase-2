# elearning_settings/serializers.py
from rest_framework import serializers
from .models import *

from django.db import IntegrityError, connections



class FormSerializer(serializers.ModelSerializer):
    module_name = serializers.ReadOnlyField(source='module.module_name')

    class Meta:
        model = FormELearning
        fields = '__all__'

    def validate(self, data):
        module = data.get("module") or getattr(self.instance, "module", None)
        form_name = data.get("form_name")

        # ✅ 1. Validate module existence
        if module:
            if not ModuleELearning.objects.filter(pk=module.pk, is_active=True).exists():
                raise serializers.ValidationError({
                    "module": "Invalid or inactive module."
                })

        if not module or not form_name:
            return data

        # ✅ Normalize FIRST
        form_name = form_name.strip().lower()
        data["form_name"] = form_name

        # ✅ Case-insensitive check
        qs = FormELearning.objects.filter(
            form_name__iexact=form_name,
            module=module,
            is_active=True
        )

        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise serializers.ValidationError({
                "form_name": "Form name already exists in this module."
            })

        return data

from django.db.models.functions import Lower

class ModuleSerializer(serializers.ModelSerializer):
    forms = serializers.SerializerMethodField()

    class Meta:
        model = ModuleELearning
        fields = '__all__'
        ref_name = "SettingsModuleSerializer"

    

    def get_forms(self, obj):
        forms = FormELearning.objects.using('default').filter(
            module=obj
        )
        return FormSerializer(forms, many=True).data

    def validate_module_name(self, value):
        value = value.strip().lower()

        qs = ModuleELearning.objects.filter(
            module_name__iexact=value,
            is_active=True
        )

        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise serializers.ValidationError(
                "Module name must be unique."
            )

        return value


# class ClientPermissionControlSerializer(serializers.ModelSerializer):
#     client_code = serializers.CharField(source="client.client_code", read_only=True)
#     class Meta:
#         model = ClientPermissionControl
#         fields = "__all__"

class ClientPermissionControlSerializer(serializers.ModelSerializer):
    client_code = serializers.SerializerMethodField()

    class Meta:
        model = ClientPermissionControl
        fields = "__all__"

    def get_client_code(self, obj):
        if obj.client_id:
            return Client.objects.using("default").filter(
                id=obj.client_id
            ).values_list("client_code", flat=True).first()
        return None






from rest_framework import serializers

# class ModuleFormPermissionSerializer(serializers.ModelSerializer):

#     class Meta:
#         model = ModuleFormPermission
#         fields = "__all__"

#     def create(self, validated_data):
#         print("VALIDATED DATA:", validated_data)
#         db_key = self.context.get("db_key")
#         return ModuleFormPermission.objects.using(db_key).create(**validated_data)
    
#     def validate(self, data):
#         module_id = data.get("module_id") or getattr(self.instance, "module_id", None)
#         form_id = data.get("form_id") or getattr(self.instance, "form_id", None)
#         role_id = data.get("role_id") or getattr(self.instance, "role_id", None)

#         db_key = self.context.get("db_key")

#         if not db_key:
#             raise serializers.ValidationError("Database context missing")

#         # Module validation
#         if not module_id or not ModuleELearning.objects.filter(
#             module_id=module_id,
#             is_active=True
#         ).exists():
#             raise serializers.ValidationError({
#                 "module_id": "Invalid or inactive module"
#             })

#         # Form validation
#         form = FormELearning.objects.filter(
#             form_id=form_id,
#             is_active=True
#         ).first()

#         if not form:
#             raise serializers.ValidationError({
#                 "form_id": "Invalid or inactive form"
#             })

#         if form.module_id != module_id:
#             raise serializers.ValidationError({
#                 "form_id": "This form does not belong to the selected module"
#             })

#         # Role validation
#         from staff.models import UserRole

#         if not role_id or not UserRole.objects.using(db_key).filter(
#             id=role_id,
#             is_active=True
#         ).exists():
#             raise serializers.ValidationError({
#                 "role_id": "Invalid role for this client"
#             })

#         return data


class ModuleFormPermissionSerializer(serializers.ModelSerializer):

    class Meta:
        model = ModuleFormPermission
        fields = "__all__"

    def validate(self, data):
        db_key = self.context.get("db_key")

        if not db_key:
            raise serializers.ValidationError("Database context missing")

        role_id = data.get("role_id")

        from staff.models import UserRole
        if not role_id or not UserRole.objects.using(db_key).filter(
            id=role_id,
            is_active=True
        ).exists():
            raise serializers.ValidationError({
                "role_id": "Invalid role"
            })

        # ✅ Validate each permission
        permissions = data.get("permissions", [])

        for perm in permissions:
            module_id = perm.get("module_id")
            form_id = perm.get("form_id")

            if not ModuleELearning.objects.filter(
                module_id=module_id,
                is_active=True
            ).exists():
                raise serializers.ValidationError({
                    "module_id": f"Invalid module {module_id}"
                })

            form = FormELearning.objects.filter(
                form_id=form_id,
                is_active=True
            ).first()

            if not form:
                raise serializers.ValidationError({
                    "form_id": f"Invalid form {form_id}"
                })

            if form.module_id != module_id:
                raise serializers.ValidationError({
                    "form_id": f"Form {form_id} does not belong to module {module_id}"
                })

        return data



class RolePermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RolePermission
        fields = '__all__'




