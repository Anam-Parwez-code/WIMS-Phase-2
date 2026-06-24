from rest_framework import serializers
from .models import Enquiry, EnquiryFollowUp, Registration
from master.models import Organization, Branch
from django.db import transaction
from settings_app.models import CodePrefix
from django.db.models.functions import Lower


class EnquirySerializer(serializers.ModelSerializer):

    # =========================================
    # FOREIGN KEY NAME FIELDS
    # =========================================

    followup_medium_name = serializers.ReadOnlyField(
        source='followup_medium.name'
    )

    enquiry_source_name = serializers.ReadOnlyField(
        source='enquiry_source.name'
    )

    assigned_to_name = serializers.ReadOnlyField(
        source='assigned_to.name'
    )

    status_name = serializers.ReadOnlyField(
        source='status.name'
    )

    nationality_name = serializers.ReadOnlyField(
        source='nationality.name'
    )

    demo_course_name = serializers.ReadOnlyField(
        source='demo_course.course_name'
    )

    demo_batch_name = serializers.ReadOnlyField(
        source='demo_batch.batch_name'
    )

    demo_faculty_name = serializers.ReadOnlyField(
        source='demo_faculty.name'
    )

    created_by_name = serializers.SerializerMethodField()

    updated_by_name = serializers.SerializerMethodField()

    # =========================================
    # COURSES DETAILS
    # =========================================

    courses_details = serializers.SerializerMethodField()

    class Meta:
        model = Enquiry

        fields = '__all__'

        read_only_fields = [
            'enquiry_code',
            'created_by',
            'created_at',
            'updated_by',
            'updated_at',
            'is_active'
        ]

    # =========================================
    # EXTRA RESPONSE DATA
    # =========================================

    def get_created_by_name(self, obj):

        if obj.created_by:

            return (
                getattr(obj.created_by, "email", None)
                or getattr(obj.created_by, "username", None)
            )

        return None

    def get_updated_by_name(self, obj):

        if obj.updated_by:

            return (
                getattr(obj.updated_by, "email", None)
                or getattr(obj.updated_by, "username", None)
            )

        return None

    def get_courses_details(self, obj):

        data = []

        for course in obj.courses.all():

            data.append({
                "id": course.id,
                "course_name": course.course_name,
                "course_code": getattr(course, "course_code", None),
                "total_course_fee": getattr(course, "total_course_fee", None)
            })

        return data

    # ---------------------------------------
    # FIELD VALIDATIONS
    # ---------------------------------------

    def validate_assigned_to(self, value):

        if (
            value.designation
            and value.designation.name.lower() != 'counsellor'
        ):

            raise serializers.ValidationError(
                "Selected employee is not a counsellor."
            )

        return value

    def validate_demo_faculty(self, value):

        if (
            value
            and value.designation
            and value.designation.name.lower() != 'trainer'
        ):

            raise serializers.ValidationError(
                "Selected employee is not a trainer."
            )

        return value

    def validate(self, data):

        branch_id = self.context.get("branch_id")

        # Ensure the record is forced to the user's branch if available
        if branch_id:

            branch_obj = Branch.objects.filter(
                id=branch_id
            ).first()

            if branch_obj:
                data['branch'] = branch_obj

        return data

    # ---------------------------------------
    # CREATE WITH AUTO-GENERATED CODE
    # ---------------------------------------

    def create(self, validated_data):

        request = self.context.get("request")

        user = request.user if request else None

        branch_id = self.context.get("branch_id")

        with transaction.atomic():

            # 🔐 Generate Enquiry Code using CodePrefix logic
            prefix_obj = CodePrefix.objects.select_for_update().filter(
                module__iexact="student_details",
                form__iexact="Enquiry",
                is_active=True
            ).first()

            if prefix_obj:

                prefix_obj.current_number += 1

                prefix_obj.save(
                    update_fields=["current_number"]
                )

                enquiry_code = (
                    f"{prefix_obj.prefix}"
                    f"{str(prefix_obj.current_number).zfill(5)}"
                )

            else:

                # Fallback if no prefix is configured
                last = Enquiry.objects.order_by("-id").first()

                next_id = (
                    (last.id + 1)
                    if last else 1
                )

                enquiry_code = f"ENQ{str(next_id).zfill(5)}"

            # Assign generated values
            validated_data["enquiry_code"] = enquiry_code

            if user:
                validated_data["created_by"] = user

            # Use branch from context if not already set
            if branch_id and "branch" not in validated_data:

                try:

                    validated_data["branch"] = Branch.objects.get(
                        id=branch_id
                    )

                except Branch.DoesNotExist:
                    pass

            return super().create(validated_data)

    # ---------------------------------------
    # UPDATE
    # ---------------------------------------

    def update(self, instance, validated_data):

        request = self.context.get("request")

        user = request.user if request else None

        if user:
            validated_data["updated_by"] = user

        return super().update(instance, validated_data)


# serializers.py

class EnquiryFollowUpSerializer(serializers.ModelSerializer):

    # =========================================
    # ENQUIRY DETAILS (READ ONLY)
    # =========================================

    enquiry_code = serializers.ReadOnlyField(
        source='enquiry.enquiry_code'
    )

    enquiry_date = serializers.ReadOnlyField(
        source='enquiry.enquiry_date'
    )

    client_name = serializers.ReadOnlyField(
        source='enquiry.candidate_name'
    )

    email = serializers.ReadOnlyField(
        source='enquiry.email'
    )

    mobile_no = serializers.ReadOnlyField(
        source='enquiry.mobile_no'
    )

    address = serializers.ReadOnlyField(
        source='enquiry.address'
    )

    # =========================================
    # DISPLAY NAMES
    # =========================================

    followup_medium_name = serializers.ReadOnlyField(
        source='followup_medium.name'
    )

    interest_level_name = serializers.ReadOnlyField(
        source='interest_level.name'
    )

    status_name = serializers.ReadOnlyField(
        source='status.name'
    )

    assigned_to_name = serializers.ReadOnlyField(
        source='assigned_to.name'
    )

    demo_course_name = serializers.ReadOnlyField(
        source='demo_course.course_name'
    )

    demo_batch_name = serializers.ReadOnlyField(
        source='demo_batch.batch_name'
    )

    demo_faculty_name = serializers.ReadOnlyField(
        source='demo_faculty.name'
    )

    class Meta:

        model = EnquiryFollowUp

        fields = "__all__"

        read_only_fields = [
            'created_by',
            'created_at',
            'updated_by',
            'updated_at',
            'is_active'
        ]

    # =========================================
    # VALIDATIONS
    # =========================================

    # def validate_assigned_to(self, value):

    #     if (
    #         value
    #         and value.designation
    #         and value.designation.name.lower() != "counsellor"
    #     ):

    #         raise serializers.ValidationError(
    #             "Assigned employee must be counsellor."
    #         )

    #     return value

    def validate_demo_faculty(self, value):

        if (
            value
            and value.designation
            and value.designation.name.lower() != "trainer"
        ):

            raise serializers.ValidationError(
                "Demo faculty must be trainer."
            )

        return value

    def validate(self, data):

        demo_attended = data.get(
            "demo_attended"
        )

        schedule_demo_class = data.get(
            "schedule_demo_class"
        )

        # =====================================
        # DEMO ATTENDED VALIDATION
        # =====================================

        if demo_attended:

            if not data.get("demo_date"):

                raise serializers.ValidationError({
                    "demo_date":
                    "Demo date is required."
                })

        # =====================================
        # SCHEDULE DEMO VALIDATION
        # =====================================

        if schedule_demo_class:

            required_fields = [
                "demo_course",
                "demo_batch",
                "demo_faculty",
                "demo_date",
                "demo_time"
            ]

            errors = {}

            for field in required_fields:

                if not data.get(field):

                    errors[field] = (
                        f"{field} is required."
                    )

            if errors:
                raise serializers.ValidationError(errors)

        return data

    # =========================================
    # CREATE
    # =========================================

    def create(self, validated_data):

        request = self.context.get("request")

        if request and request.user:

            validated_data["created_by"] = request.user

        return super().create(validated_data)

    # =========================================
    # UPDATE
    # =========================================

    def update(self, instance, validated_data):

        request = self.context.get("request")

        if request and request.user:

            validated_data["updated_by"] = request.user

        return super().update(
            instance,
            validated_data
        )

class RegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Registration
        fields = '__all__'
        read_only_fields = ['registration_code', 'created_by', 'created_at', 'updated_by', 'updated_at', 'is_active']

    def validate_aadhar_no(self, value):
        if value and not (value.isdigit() and len(value) == 12):
            raise serializers.ValidationError("Aadhar number must be exactly 12 digits.")
        return value

    def validate_mobile_no(self, value):
        if not value.isdigit() or len(value) < 10 or len(value) > 15:
            raise serializers.ValidationError("Invalid mobile number format.")
        return value

    def validate_dob(self, value):
        from django.utils import timezone
        if value >= timezone.now().date():
            raise serializers.ValidationError("Date of birth must be in the past.")
        return value

    def validate(self, data):
        # Additional cross-field validations can go here
        return data

    def create(self, validated_data):
        request = self.context.get("request")
        user = request.user if request else None
        courses_data = validated_data.pop('courses', [])
        # client_key logic (assuming it's used for prefix filtering)
        client_key = None
        if user:
            client_key = None if getattr(user, 'role', None) == "super_admin" else getattr(user, 'client_code', None)

        with transaction.atomic():
            try:
                
                # Assuming module="admission" and form="Registration" based on requirements
                prefix_obj = CodePrefix.objects.select_for_update().get(
                    module__iexact="student_details",
                    form__iexact="Registration",
                    is_active=True
                )
                
            except CodePrefix.DoesNotExist:
                raise serializers.ValidationError("Registration prefix configuration missing.")

            if prefix_obj:
                prefix_obj.current_number += 1
                prefix_obj.save()
                registration_code = f"{prefix_obj.prefix}{str(prefix_obj.current_number).zfill(5)}"
                print(registration_code)
            else:
                # Default fallback
                last_reg = Registration.objects.filter(registration_code__startswith="REG").order_by('-id').first()
                if last_reg and last_reg.registration_code.startswith("REG") and last_reg.registration_code[3:].isdigit():
                    num = int(last_reg.registration_code[3:]) + 1
                else:
                    num = 1
                registration_code = f"REG{str(num).zfill(5)}"

            validated_data["registration_code"] = registration_code
            if user:
                validated_data["created_by"] = user
                
                # Auto-assign organization based on client_code
                # client_code = getattr(user, 'client_code', None)
                # if client_code:
                #     org = Organization.objects.filter(client=client_code, is_active=True).first()
                #     if org:
                #         validated_data["organization"] = org
            # Create the instance without the M2M data
        instance = Registration.objects.create(**validated_data)
        
        # Now set the M2M data
        if courses_data:
            instance.courses.set(courses_data)
        

        return instance

    def update(self, instance, validated_data):
        request = self.context.get("request")
        user = request.user if request else None
        if user:
            validated_data["updated_by"] = user
        return super().update(instance, validated_data)


