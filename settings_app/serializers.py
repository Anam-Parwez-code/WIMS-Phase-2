from rest_framework import serializers
from django.db.models.functions import Lower
from django.apps import apps   # ✅ REQUIRED IMPORT
from .models import CodePrefix



class CodePrefixSerializer(serializers.ModelSerializer):
    class Meta:
        model = CodePrefix
        fields = "__all__"
        read_only_fields = ["client", "current_number", "is_active"]

    def validate(self, data):
        request = self.context["request"]
        user = request.user

        module = data.get("module") or getattr(self.instance, "module", None)
        form = data.get("form") or getattr(self.instance, "form", None)
        prefix = data.get("prefix") or getattr(self.instance, "prefix", None)

        if not module or not form or not prefix:
            raise serializers.ValidationError(
                "module, form and prefix are required."
            )

        # 🔥 Normalize (CASE-INSENSITIVE CORE)
        module = module.lower().strip()
        form = form.strip()

        client_key = None if user.role == "super_admin" else user.client_code

        # ✅ 1. Validate module exists (case-insensitive)
        try:
            app_config = apps.get_app_config(module)
        except LookupError:
            raise serializers.ValidationError({
                "module": "Invalid module (app name)."
            })

        # ✅ 2. Validate form belongs to module (case-insensitive)
        model_names = [m.__name__.lower() for m in app_config.get_models()]
        if form.lower() not in model_names:
            raise serializers.ValidationError({
                "form": f"{form} does not belong to module {module}."
            })

        # ✅ 3. Case-insensitive uniqueness (ACTIVE ONLY)
        qs = CodePrefix.objects.annotate(
            module_l=Lower("module"),
            form_l=Lower("form")
        ).filter(
            module_l=module,
            form_l=form.lower(),
            client=client_key,
            is_active=True
        )

        if self.instance:
            qs = qs.exclude(id=self.instance.id)

        if qs.exists():
            raise serializers.ValidationError(
                "Prefix already exists for this module and form under this client."
            )

        # 🔥 Save normalized values back
        data["module"] = module
        data["form"] = form

        return data

    def create(self, validated_data):
        user = self.context["request"].user
        client_key = None if user.role == "super_admin" else user.client_code

        module = validated_data["module"]
        form = validated_data["form"]

        # 🔁 Revive soft-deleted prefix (case-insensitive)
        existing = CodePrefix.objects.filter(
            module__iexact=module,
            form__iexact=form,
            client=client_key,
            is_active=False
        ).first()

        if existing:
            existing.prefix = validated_data["prefix"].upper()
            existing.is_active = True
            existing.current_number = 0
            existing.save()
            return existing

        validated_data["client"] = client_key
        validated_data["prefix"] = validated_data["prefix"].upper()
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if "prefix" in validated_data:
            validated_data["prefix"] = validated_data["prefix"].upper()

        if "module" in validated_data:
            validated_data["module"] = validated_data["module"].lower().strip()

        if "form" in validated_data:
            validated_data["form"] = validated_data["form"].strip()

        return super().update(instance, validated_data)
