from rest_framework import serializers
from .models import *
from django.db.models import Q
from django.db.models.functions import Lower

import re
from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.contrib.auth import get_user_model

from core.models import ClientUser

User = get_user_model()


class CountrySerializer(serializers.ModelSerializer):

    class Meta:
        model = Country
        fields = "__all__"

    def validate_country_code(self, value):
        if not value:
            return value

        qs = Country.objects.annotate(
            code_lower=Lower('country_code')
        ).filter(
            code_lower=value.lower(),
            is_active=True
        )

        if self.instance:
            qs = qs.exclude(id=self.instance.id)

        if qs.exists():
            raise serializers.ValidationError(
                "Country code must be unique."
            )

        return value

class StateSerializer(serializers.ModelSerializer):
    country_name = serializers.ReadOnlyField(source="country.name")

    class Meta:
        model = State
        fields = [
            "id",
            "name",
            "country",
            "country_name",
            "is_active",
        ]

    def validate(self, data):
        country = data.get("country") or getattr(self.instance, "country", None)
        name = data.get("name") or getattr(self.instance, "name", None)

        if not country:
            raise serializers.ValidationError({"country": "Country is required."})

        if not name:
            raise serializers.ValidationError({"name": "State name is required."})

        # ❌ Cannot assign under inactive country
        if not country.is_active:
            raise serializers.ValidationError(
                {"country": "Cannot assign a state under an inactive country."}
            )

        # ✅ Unique state name within country (case-insensitive, active only)
        qs = State.objects.annotate(
            name_lower=Lower("name")
        ).filter(
            name_lower=name.lower(),
            country=country,
            is_active=True
        )

        if self.instance:
            qs = qs.exclude(id=self.instance.id)

        if qs.exists():
            raise serializers.ValidationError(
                {"name": "State name must be unique within this country."}
            )

        return data

class CitySerializer(serializers.ModelSerializer):
    state_name = serializers.ReadOnlyField(source="state.name")
    country_name = serializers.ReadOnlyField(source="country.name")

    class Meta:
        model = City
        fields = [
            "id",
            "name",
            "country",
            "country_name",
            "state",
            "state_name",
            "is_active",
        ]

    def validate(self, data):
        country = data.get("country") or getattr(self.instance, "country", None)
        state = data.get("state") or getattr(self.instance, "state", None)
        name = data.get("name") or getattr(self.instance, "name", None)

        if not country:
            raise serializers.ValidationError({"country": "Country is required."})

        if not state:
            raise serializers.ValidationError({"state": "State is required."})

        if not name:
            raise serializers.ValidationError({"name": "City name is required."})

        # ❌ Cannot assign under inactive country
        if not country.is_active:
            raise serializers.ValidationError(
                {"country": "Cannot assign a city under an inactive country."}
            )

        # ❌ Cannot assign under inactive state
        if not state.is_active:
            raise serializers.ValidationError(
                {"state": "Cannot assign a city under an inactive state."}
            )

        # ❌ Ensure state belongs to country
        if state.country_id != country.id:
            raise serializers.ValidationError(
                {"state": "Selected state does not belong to the selected country."}
            )

        # ✅ Unique city name within state (case-insensitive, active only)
        qs = City.objects.annotate(
            name_lower=Lower("name")
        ).filter(
            name_lower=name.lower(),
            state=state,
            is_active=True
        )

        if self.instance:
            qs = qs.exclude(id=self.instance.id)

        if qs.exists():
            raise serializers.ValidationError(
                {"name": "City name must be unique within this state."}
            )

        return data

class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = "__all__"

    def validate(self, data):
        name = data.get("name") or getattr(self.instance, "name", None)

        if not name:
            raise serializers.ValidationError({"name": "Department name is required."})

        qs = Department.objects.annotate(
            name_lower=Lower("name")
        ).filter(
            name_lower=name.lower(),
            is_active=True
        )

        if self.instance:
            qs = qs.exclude(id=self.instance.id)

        if qs.exists():
            raise serializers.ValidationError(
                {"name": "Department name must be unique."}
            )

        return data

class DesignationSerializer(serializers.ModelSerializer):
    department_name = serializers.ReadOnlyField(source="department.name")

    class Meta:
        model = Designation
        fields = [
            "id",
            "name",
            "department",        # Input: ID
            "department_name",   # Output: Name
            "is_active",
        ]

    def validate_department(self, value):
        if not value.is_active:
            raise serializers.ValidationError(
                "Cannot assign a designation to an inactive department."
            )
        return value

    def validate(self, data):
        name = data.get("name") or getattr(self.instance, "name", None)
        department = data.get("department") or getattr(self.instance, "department", None)

        if not name:
            raise serializers.ValidationError({"name": "Designation name is required."})

        if not department:
            raise serializers.ValidationError({"department": "Department is required."})

        qs = Designation.objects.annotate(
            name_lower=Lower("name")
        ).filter(
            name_lower=name.lower(),
            department=department,
            is_active=True
        )

        if self.instance:
            qs = qs.exclude(id=self.instance.id)

        if qs.exists():
            raise serializers.ValidationError(
                {"name": "Designation name must be unique within this department."}
            )

        return data

class FollowUpMediumSerializer(serializers.ModelSerializer):
    class Meta:
        model = FollowUpMedium
        fields = "__all__"
        read_only_fields = ["is_active"]

    def validate_name(self, value):
        qs = FollowUpMedium.objects.annotate(
            name_lower=Lower("name")
        ).filter(
            name_lower=value.lower(),
            is_active=True
        )

        if self.instance:
            qs = qs.exclude(id=self.instance.id)

        if qs.exists():
            raise serializers.ValidationError(
                "Follow-up medium name must be unique."
            )

        return value

    def create(self, validated_data):
        validated_data["is_active"] = True
        return super().create(validated_data)

class InterestLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterestLevel
        fields = "__all__"
        read_only_fields = ["is_active"]

    def validate_level(self, value):
        qs = InterestLevel.objects.annotate(
            level_lower=Lower("level")
        ).filter(
            level_lower=value.lower(),
            is_active=True
        )

        if self.instance:
            qs = qs.exclude(id=self.instance.id)

        if qs.exists():
            raise serializers.ValidationError(
                "Interest level must be unique."
            )

        return value

    def create(self, validated_data):
        validated_data["is_active"] = True
        return super().create(validated_data)

class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = "__all__"
        read_only_fields = ["is_active"]

    # --------------------------
    # VALIDATE NAME (Unique inside tenant DB)
    # --------------------------
    def validate_name(self, value):
        qs = Organization.objects.annotate(
            name_lower=Lower("name")
        ).filter(
            name_lower=value.lower(),
            is_active=True
        )

        if self.instance:
            qs = qs.exclude(id=self.instance.id)

        if qs.exists():
            raise serializers.ValidationError(
                "Organization name must be unique."
            )

        return value

    # --------------------------
    # VALIDATE LOCATION RELATIONS
    # --------------------------
    def validate(self, data):
        country = data.get("country") or (
            self.instance.country if self.instance else None
        )
        state = data.get("state") or (
            self.instance.state if self.instance else None
        )
        city = data.get("city") or (
            self.instance.city if self.instance else None
        )

        # --- COUNTRY VALIDATION ---
        if country and not country.is_active:
            raise serializers.ValidationError(
                {"country": "Selected country is inactive."}
            )

        # --- STATE VALIDATION ---
        if state:
            if not state.is_active:
                raise serializers.ValidationError(
                    {"state": "Selected state is inactive."}
                )

            if country and state.country_id != country.id:
                raise serializers.ValidationError(
                    {"state": "This state does not belong to the selected country."}
                )

        # --- CITY VALIDATION ---
        if city:
            if not city.is_active:
                raise serializers.ValidationError(
                    {"city": "Selected city is inactive."}
                )

            if state and city.state_id != state.id:
                raise serializers.ValidationError(
                    {"city": "This city does not belong to the selected state."}
                )

        return data

    # --------------------------
    # CREATE
    # --------------------------
    def create(self, validated_data):
        validated_data["is_active"] = True
        return super().create(validated_data)

class BranchSerializer(serializers.ModelSerializer):

    # ==========================================
    # ORGANIZATION
    # ==========================================

    organization_name = serializers.ReadOnlyField(
        source="organization.name"
    )

    # ==========================================
    # COUNTRY
    # ==========================================

    country_name = serializers.ReadOnlyField(
        source="country.name"
    )

    # ==========================================
    # STATE
    # ==========================================

    state_name = serializers.ReadOnlyField(
        source="state.name"
    )

    # ==========================================
    # CITY
    # ==========================================

    city_name = serializers.ReadOnlyField(
        source="city.name"
    )

    class Meta:

        model = Branch

        fields = [

            # BASIC
            "id",
            "is_active",

            # NEW
            "is_main_branch",

            # ORGANIZATION
            "organization",
            "organization_name",

            # BRANCH
            "name",

            # LOCATION
            "country",
            "country_name",

            "state",
            "state_name",

            "city",
            "city_name",

            # ADDRESS
            "address",
            "email",
            "mobile",
            "landline",
            "zipcode",

            # EXTRA
            "tin_number",
            "affiliation_number",
            "fax",
            "website",

            # BANK
            "bank_name",
            "bank_branch",
            "account_holder",
            "account_number",
            "ifsc_code",

            # GST
            "gst_number",

            # IMAGE
            "image",
        ]

        read_only_fields = ["is_active"]

    def validate(self, data):
        # ------------------------------
        # FETCH OBJECTS SAFELY
        # ------------------------------
        org = data.get("organization") or getattr(self.instance, "organization", None)

        if isinstance(org, int):
            org = Organization.objects.filter(id=org).first()

        if not org:
            raise serializers.ValidationError(
                {"organization": "Organization does not exist."}
            )

        name = data.get("name") or getattr(self.instance, "name", None)

        country = data.get("country") or getattr(self.instance, "country", None)
        state = data.get("state") or getattr(self.instance, "state", None)
        city = data.get("city") or getattr(self.instance, "city", None)

        # ------------------------------
        # MANDATORY FIELDS
        # ------------------------------
        if not name:
            raise serializers.ValidationError({"name": "Branch name is required."})
        
        # =====================================
        # MAIN BRANCH VALIDATION
        # =====================================
            
        is_main_branch = data.get(
            "is_main_branch",
            getattr(self.instance, "is_main_branch", False)
        )

        if is_main_branch:

            existing_main = Branch.objects.filter(
                organization=org,
                is_main_branch=True,
                is_active=True
            )

            if self.instance:
                existing_main = existing_main.exclude(
                    id=self.instance.id
                )

            existing_main = existing_main.first()

            if existing_main:

                request = self.context.get("request")

                confirmed = False

                if request:
                    confirmed = str(
                        request.data.get("confirm_main_branch_change", "")
                    ).lower() == "true"

                if not confirmed:

                    raise serializers.ValidationError({
                        "confirm_main_branch_change":
                            f"You are changing the Main Branch from "
                            f"{existing_main.name} to {name}. "
                            f"Please confirm."
                    })
                

        # ------------------------------
        # ORGANIZATION VALIDATION
        # ------------------------------
        if not org.is_active:
            raise serializers.ValidationError(
                {"organization": "Cannot create a branch under an inactive organization."}
            )
        

        # ------------------------------
        # UNIQUE BRANCH NAME UNDER ORG
        # ------------------------------
        qs = Branch.objects.annotate(
            name_lower=Lower("name")
        ).filter(
            name_lower=name.lower(),
            organization=org,
            is_active=True,
        )

        if self.instance:
            qs = qs.exclude(id=self.instance.id)

        if qs.exists():
            raise serializers.ValidationError(
                {"name": "Branch name must be unique within this organization."}
            )
        
        # ------------------------------
        # UNIQUE EMAIL UNDER ORGANIZATION
        # ------------------------------
        email = data.get("email") or getattr(
            self.instance,
            "email",
            None
        )

        if email:

            email_qs = Branch.objects.annotate(
                email_lower=Lower("email")
            ).filter(
                email_lower=email.lower(),
                organization=org,
                is_active=True
            )

            if self.instance:
                email_qs = email_qs.exclude(
                    id=self.instance.id
                )

            if email_qs.exists():

                raise serializers.ValidationError({
                    "email":
                        "Branch email must be unique within this organization."
                })

        # ------------------------------
        # COUNTRY / STATE / CITY VALIDATION
        # ------------------------------
        if country:
            if not country.is_active:
                raise serializers.ValidationError(
                    {"country": "Selected country is inactive."}
                )

        if state:
            if not state.is_active:
                raise serializers.ValidationError(
                    {"state": "State is inactive."}
                )
            if country and state.country_id != country.id:
                raise serializers.ValidationError(
                    {"state": "State does not belong to this country."}
                )

        if city:
            if not city.is_active:
                raise serializers.ValidationError(
                    {"city": "City is inactive."}
                )
            if state and city.state_id != state.id:
                raise serializers.ValidationError(
                    {"city": "City does not belong to this state."}
                )
            

        return data

    # def create(self, validated_data):
    #     validated_data["is_active"] = True
    #     return super().create(validated_data)

    def create(self, validated_data):
        request = self.context["request"]

        # 1. Pehle user se client_code nikalne ki koshish karein
        client_code = getattr(request.user, "client_code", None)

        # 2. Agar user authenticated nahi hai (None mila), toh check karein ki kya Postman se raw data me bheja hai
        if not client_code and request:
            client_code = request.data.get("client_code", None)

        # 3. Safe Fallback: Agar phir bhi nahi mila, toh organization ke name/code ka short-form use kar lein
        if not client_code:
            org = validated_data.get("organization")
            if org:
                # Organization name ko lowercase aur space-free banakar code bana lijiye
                client_code = re.sub(r'[^a-zA-Z0-9]', '', org.name.lower())
            else:
                client_code = "default_client"

        validated_data["is_active"] = True

        with transaction.atomic():

            # ============================
            # CREATE BRANCH
            # ============================
            branch = Branch.objects.create(**validated_data)

            # ============================
            # GENERATE USERNAME
            # ============================
            clean_org_name = re.sub(
                r'[^a-zA-Z0-9]',
                '',
                branch.organization.name.lower()
            )

            clean_branch_name = re.sub(
                r'[^a-zA-Z0-9]',
                '',
                branch.name.lower()
            )

            username = f"admin_{clean_org_name}_{clean_branch_name}"
            password = "Admin@1234"

            # ============================
            # DJANGO USER
            # ============================
            existing_user = User.objects.filter(email=username).first()

            if existing_user:
                existing_user.password = make_password(password)
                existing_user.client_code = client_code
                existing_user.is_active = True
                existing_user.save()
            else:
                User.objects.create(
                    email=username,
                    password=make_password(password),
                    client_code=client_code,
                    is_active=True
                )

            # ============================
            # CLIENT USER
            # ============================
            existing_client_user = ClientUser.objects.filter(
                client_code=client_code,
                user_id=username
            ).first()

            if existing_client_user:
                existing_client_user.password = make_password(password)
                existing_client_user.branch = branch
                existing_client_user.role = "admin"
                existing_client_user.is_admin = True
                existing_client_user.is_branch_super_admin = True
                existing_client_user.is_main_branch_admin = branch.is_main_branch
                existing_client_user.employee_name = f"{branch.name} Branch Admin"
                existing_client_user.is_active = True
                existing_client_user.save()
            else:
                ClientUser.objects.create(
                    client_code=client_code,  # Ab yeh kabhi null nahi hoga!
                    user_id=username,
                    password=make_password(password),
                    role="admin",
                    is_admin=True,
                    is_branch_super_admin=True,
                    is_main_branch_admin=branch.is_main_branch,
                    employee_name=f"{branch.name} Branch Admin",
                    branch=branch,
                    is_active=True
                )

            # ============================
            # RETURN LOGIN DETAILS
            # ============================
            branch.generated_username = username
            branch.generated_password = password

            return branch
    def update(self, instance, validated_data):
        return super().update(instance, validated_data)



class SourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Source
        fields = "__all__"
        read_only_fields = ["is_active"]

    def validate_name(self, value):
        qs = Source.objects.annotate(
            name_lower=Lower("name")
        ).filter(
            name_lower=value.lower(),
            is_active=True
        )

        if self.instance:
            qs = qs.exclude(id=self.instance.id)

        if qs.exists():
            raise serializers.ValidationError(
                "Source name must be unique."
            )

        return value

    def create(self, validated_data):
        validated_data["is_active"] = True
        return super().create(validated_data)

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)

class StatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Status
        fields = "__all__"
        read_only_fields = ["is_active"]

    def validate_name(self, value):
        qs = Status.objects.annotate(
            name_lower=Lower("name")
        ).filter(
            name_lower=value.lower(),
            is_active=True
        )

        if self.instance:
            qs = qs.exclude(id=self.instance.id)

        if qs.exists():
            raise serializers.ValidationError(
                "Status name must be unique."
            )

        return value

    def create(self, validated_data):
        validated_data["is_active"] = True
        return super().create(validated_data)

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)

class NationalitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Nationality
        fields = "__all__"
        read_only_fields = ["is_active"]

    def validate(self, data):
        request = self.context["request"]
        user = request.user

        name = data.get("name") or (self.instance.name if self.instance else None)
        country = data.get("country") or (self.instance.country if self.instance else None)

        if not name:
            raise serializers.ValidationError({"name": "Nationality name is required."})

        if not country:
            raise serializers.ValidationError({"country": "Country is required."})

        # ✅ Country must be active
        if not country.is_active:
            raise serializers.ValidationError({"country": "Country is inactive."})

        # ✅ Case-insensitive unique nationality (within tenant DB automatically)
        qs = Nationality.objects.annotate(
            name_lower=Lower("name")
        ).filter(
            name_lower=name.lower(),
            is_active=True
        )

        if self.instance:
            qs = qs.exclude(id=self.instance.id)

        if qs.exists():
            raise serializers.ValidationError({
                "name": "Nationality name must be unique."
            })

        return data

    def create(self, validated_data):
        validated_data["is_active"] = True
        return super().create(validated_data)

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)

class FormDesignSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormDesign
        fields = "__all__"

class EmailConfigurationsSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = EmailConfigurations
        fields = "__all__"
        read_only_fields = ["is_active"]

    def validate(self, data):
        smtp_host = data.get("smtp_host") or (
            self.instance.smtp_host if self.instance else None
        )
        sender_email = data.get("sender_email") or (
            self.instance.sender_email if self.instance else None
        )

        if not smtp_host:
            raise serializers.ValidationError(
                {"smtp_host": "SMTP host is required."}
            )

        if not sender_email:
            raise serializers.ValidationError(
                {"sender_email": "Sender email is required."}
            )

        # 🔍 Unique config inside tenant DB (case-insensitive)
        qs = EmailConfigurations.objects.annotate(
            host_lower=Lower("smtp_host"),
            email_lower=Lower("sender_email")
        ).filter(
            host_lower=smtp_host.lower(),
            email_lower=sender_email.lower(),
            is_active=True
        )

        if self.instance:
            qs = qs.exclude(id=self.instance.id)

        if qs.exists():
            raise serializers.ValidationError(
                "Email configuration already exists."
            )

        return data

    def create(self, validated_data):
        validated_data["is_active"] = True
        return super().create(validated_data)

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)

class SMSConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SMSConfiguration
        fields = "__all__"
        read_only_fields = ["is_active"]

    def validate(self, data):
        provider_name = data.get("provider_name") or (
            self.instance.provider_name if self.instance else None
        )

        sender_id = data.get("sender_id") or (
            self.instance.sender_id if self.instance else None
        )

        if not provider_name:
            raise serializers.ValidationError(
                {"provider_name": "Provider name is required."}
            )

        if not sender_id:
            raise serializers.ValidationError(
                {"sender_id": "Sender ID is required."}
            )

        # 🔍 Unique configuration inside tenant DB (case-insensitive)
        qs = SMSConfiguration.objects.annotate(
            provider_lower=Lower("provider_name"),
            sender_lower=Lower("sender_id")
        ).filter(
            provider_lower=provider_name.lower(),
            sender_lower=sender_id.lower(),
            is_active=True
        )

        if self.instance:
            qs = qs.exclude(id=self.instance.id)

        if qs.exists():
            raise serializers.ValidationError(
                "SMS configuration already exists."
            )

        return data

    def create(self, validated_data):
        validated_data["is_active"] = True
        return super().create(validated_data)

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)


class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = ['id', 'name', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']
