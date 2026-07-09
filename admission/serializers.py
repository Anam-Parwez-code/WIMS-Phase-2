from datetime import datetime
from rest_framework import serializers
from django.db.models import Sum
from django.db import models
from .models import *
from fee_details.models import FeeGeneration, FeeDeposit
from course.models import Course, Batch
from master.models import Organization
from django.db import transaction
from settings_app.models import CodePrefix
from decimal import Decimal
from core.helper_function import get_branch_id
from admission.models import Admission
from rest_framework import serializers
from .models import CertificateTemplate

class AdmissionCourseBatchSerializer(serializers.ModelSerializer):
    course_name = serializers.ReadOnlyField(source="course.course_name")
    course_code = serializers.ReadOnlyField(source="course.course_code")
    total_course_fee = serializers.ReadOnlyField(source="course.total_course_fee")

    batch_name = serializers.ReadOnlyField(source="batch.batch_name")
    batch_code = serializers.ReadOnlyField(source="batch.batch_code")

    class Meta:
        model = AdmissionCourseBatch
        fields = [
            "course",
            "course_name",
            "course_code",
            "total_course_fee",
            "batch",
            "batch_name",
            "batch_code",
        ]

class AdmissionSerializer(serializers.ModelSerializer):
    course_batches = AdmissionCourseBatchSerializer(many=True)

    class Meta:
        model = Admission
        fields = "__all__"
        read_only_fields = [
            "admission_code",
            "created_by",
            "created_at",
            "updated_by",
            "updated_at",
            "is_active",
        ]

    # ---------------------------------------
    # OUTPUT (GROUP COURSE → BATCH)
    # ---------------------------------------
    def to_representation(self, instance):
        data = super().to_representation(instance)

        course_map = {}

        for cb in instance.course_batches.all():
            course_id = cb.course.id

            if course_id not in course_map:
                course_map[course_id] = {
                    "course_id": cb.course.id,
                    "course_name": cb.course.course_name,
                    "course_code": cb.course.course_code,
                    "total_course_fee": cb.course.total_course_fee,
                    "batches": []
                }

            course_map[course_id]["batches"].append({
                "batch_id": cb.batch.id,
                "batch_name": cb.batch.batch_name,
                "batch_code": cb.batch.batch_code
            })

        data["courses"] = list(course_map.values())

        # ❌ Remove raw course_batches from response (optional cleanup)
        data.pop("course_batches", None)

        return data

    # ---------------------------------------
    # VALIDATIONS
    # ---------------------------------------
    def validate_aadhaar_no(self, value):
        if value and not (value.isdigit() and len(value) == 12):
            raise serializers.ValidationError(
                "Aadhaar number must be exactly 12 digits."
            )
        return value

    def validate_mobile_no(self, value):
        if not value.isdigit() or not (10 <= len(value) <= 15):
            raise serializers.ValidationError(
                "Invalid mobile number format."
            )
        return value
    
    def validate_email(self, value):

        if not value:
            return value

        qs = Admission.objects.filter(
            email__iexact=value,
            is_active=True
        )

        if self.instance:
            qs = qs.exclude(id=self.instance.id)

        if qs.exists():
            raise serializers.ValidationError(
                "This email is already used for another admission."
            )

        return value

    # def validate(self, data):
    #     branch_id = self.context.get("branch_id")

    #     if branch_id:
    #         branch_obj = Branch.objects.filter(id=branch_id).first()
    #         if branch_obj:
    #             data["branch"] = branch_obj

    #     return data

    def validate(self, data):

        branch = data.get("branch") or getattr(self.instance, "branch", None)
        organization = data.get("organization") or getattr(self.instance, "organization", None)

        if organization and not organization.is_active:
            raise serializers.ValidationError({
                "organization": "Organization is inactive."
            })

        if branch:

            if not branch.is_active:
                raise serializers.ValidationError({
                    "branch": "Selected branch is inactive."
                })

            if organization and branch.organization_id != organization.id:
                raise serializers.ValidationError({
                    "branch": "Selected branch does not belong to the selected organization."
                })

        return data

    # ---------------------------------------
    # CREATE
    # ---------------------------------------
    def create(self, validated_data):
        request = self.context.get("request")
        user = request.user if request else None
        branch_id = self.context.get("branch_id")

        course_batches_data = validated_data.pop("course_batches", [])

        with transaction.atomic():

            # 🔐 Admission Code
            prefix_obj = CodePrefix.objects.select_for_update().filter(
                module__iexact="admission",
                form__iexact="Admission",
                is_active=True
            ).first()

            if prefix_obj:
                prefix_obj.current_number += 1
                prefix_obj.save(update_fields=["current_number"])
                admission_code = (
                    f"{prefix_obj.prefix}"
                    f"{str(prefix_obj.current_number).zfill(5)}"
                )
            else:
                last = Admission.objects.order_by("-id").first()
                next_id = (last.id + 1) if last else 1
                admission_code = f"ADM{str(next_id).zfill(5)}"

            validated_data["admission_code"] = admission_code

            if user:
                validated_data["created_by"] = user

            # if branch_id:
            #     try:
            #         validated_data["branch"] = Branch.objects.get(id=branch_id)
            #     except Branch.DoesNotExist:
            #         pass

            admission = super().create(validated_data)

            # 🔥 Create mapping
            for item in course_batches_data:
                AdmissionCourseBatch.objects.create(
                    admission=admission,
                    course=item["course"],
                    batch=item["batch"]
                )

        return admission

    # ---------------------------------------
    # UPDATE
    # ---------------------------------------
    def update(self, instance, validated_data):
        request = self.context.get("request")
        user = request.user if request else None

        course_batches_data = validated_data.pop("course_batches", None)

        if user:
            validated_data["updated_by"] = user

        admission = super().update(instance, validated_data)

        # 🔥 Replace mapping
        if course_batches_data is not None:
            instance.course_batches.all().delete()

            for item in course_batches_data:
                AdmissionCourseBatch.objects.create(
                    admission=instance,
                    course=item["course"],
                    batch=item["batch"]
                )

        return admission



class CertificateApprovalSerializer(serializers.ModelSerializer):

    # =========================
    # STUDENT DETAILS
    # =========================
    candidate_name = serializers.CharField(
        source='admission.candidate_name',
        read_only=True
    )

    admission_code = serializers.CharField(
        source='admission.admission_code',
        read_only=True
    )

    email = serializers.CharField(
        source='admission.email',
        read_only=True
    )

    mobile_no = serializers.CharField(
        source='admission.mobile_no',
        read_only=True
    )

    # =========================
    # ORG / BRANCH
    # =========================
    organization_name = serializers.CharField(
        source='organization.name',
        read_only=True
    )

    branch_name = serializers.CharField(
        source='branch.name',
        read_only=True
    )

    # =========================
    # FEE DETAILS
    # =========================
    total_fee = serializers.SerializerMethodField()
    pending_fee = serializers.SerializerMethodField()
    amount_paid = serializers.SerializerMethodField()

    # =========================
    # COURSE + BATCH
    # =========================
    course_batch_details = serializers.SerializerMethodField()

    class Meta:
        model = CertificateApproval
        fields = '__all__'

        read_only_fields = [
            'approved_by',
            'created_at'
        ]

    # =========================
    # TOTAL FEES
    # =========================
    def get_total_fee(self, obj):

        total = FeeGeneration.objects.filter(
            admission=obj.admission,
            is_active=True
        ).aggregate(
            total=Sum("total_fee")
        )["total"] or 0

        return float(total)

    # =========================
    # PENDING FEES
    # =========================
    def get_pending_fee(self, obj):

        pending = FeeGeneration.objects.filter(
            admission=obj.admission,
            is_active=True
        ).aggregate(
            total=Sum("balance_amount")
        )["total"] or 0

        return float(pending)

    # =========================
    # AMOUNT PAID
    # =========================
    def get_amount_paid(self, obj):

        total_fee = self.get_total_fee(obj)
        pending = self.get_pending_fee(obj)

        return float(total_fee - pending)

    # =========================
    # COURSE + BATCH DETAILS
    # =========================
    def get_course_batch_details(self, obj):

        mappings = AdmissionCourseBatch.objects.filter(
            admission=obj.admission,
            is_active=True
        ).select_related("course", "batch")

        return [
            {
                "course_id": m.course.id,
                "course_name": m.course.course_name,

                "batch_id": m.batch.id,
                "batch_name": m.batch.batch_name,
            }
            for m in mappings
        ]

    # =========================
    # VALIDATION
    # =========================
    def validate_admission(self, value):

        fee_qs = FeeGeneration.objects.filter(
            admission=value,
            is_active=True
        )

        if not fee_qs.exists():
            raise serializers.ValidationError(
                "No fee record found for this student."
            )

        pending = fee_qs.aggregate(
            total=Sum("balance_amount")
        )["total"] or 0

        if pending > 0:
            raise serializers.ValidationError(
                f"Cannot approve. Student has a pending balance of {pending}"
            )

        return value

    def create(self, validated_data):

        request = self.context.get("request")

        if request and request.user:
            validated_data['approved_by'] = request.user

        return super().create(validated_data)


# class CertificateTemplateSerializer(serializers.ModelSerializer):

#     course_name = serializers.CharField(
#         source="course.course_name",
#         read_only=True
#     )

#     class Meta:
#         model = CertificateTemplate

#         fields = [
#             "id",
#             "course",
#             "course_name",
#             "template_name",
#             "template_path",
#             "is_active"
#         ]




class CertificateTemplateSerializer(serializers.ModelSerializer):

    course_name = serializers.CharField(
        source="course.course_name",
        read_only=True
    )

    institute_logo_url = serializers.SerializerMethodField()
    signature_image_url = serializers.SerializerMethodField()
    stamp_image_url = serializers.SerializerMethodField()
    background_image_url = serializers.SerializerMethodField()

    class Meta:
        model = CertificateTemplate

        fields = [
            "id",

            "course",
            "course_name",

            "template_name",

            # ===================================
            # LOGO
            # ===================================
            "institute_logo",
            "institute_logo_url",
            "logo_position",

            # ===================================
            # INSTITUTE NAME
            # ===================================
            "institute_name",
            "institute_name_font_size",
            "institute_name_bold",
            "institute_name_italic",
            "institute_name_color",
            "institute_name_alignment",

            # ===================================
            # TITLE
            # ===================================
            "certificate_title",
            "title_font_size",
            "title_bold",
            "title_italic",
            "title_color",
            "title_alignment",

            # ===================================
            # BODY
            # ===================================
            "body_text",
            "body_font_size",
            "body_color",

            # ===================================
            # SIGNATURE
            # ===================================
            "signature_image",
            "signature_image_url",
            "signature_label",

            # ===================================
            # STAMP
            # ===================================
            "stamp_image",
            "stamp_image_url",
            "stamp_position",

            # ===================================
            # BORDER
            # ===================================
            "border_style",
            "border_color",

            # ===================================
            # BACKGROUND
            # ===================================
            "background_type",
            "background_color",
            "background_image",
            "background_image_url",

            "is_active",
            "created_at"
        ]

        read_only_fields = [
            "id",
            "created_at"
        ]

    # ===================================
    # FILE URLS
    # ===================================

    def get_institute_logo_url(self, obj):

        request = self.context.get("request")

        if obj.institute_logo:
            if request:
                return request.build_absolute_uri(
                    obj.institute_logo.url
                )
            return obj.institute_logo.url

        return None

    def get_signature_image_url(self, obj):

        request = self.context.get("request")

        if obj.signature_image:
            if request:
                return request.build_absolute_uri(
                    obj.signature_image.url
                )
            return obj.signature_image.url

        return None

    def get_stamp_image_url(self, obj):

        request = self.context.get("request")

        if obj.stamp_image:
            if request:
                return request.build_absolute_uri(
                    obj.stamp_image.url
                )
            return obj.stamp_image.url

        return None

    def get_background_image_url(self, obj):

        request = self.context.get("request")

        if obj.background_image:
            if request:
                return request.build_absolute_uri(
                    obj.background_image.url
                )
            return obj.background_image.url

        return None

    # ===================================
    # VALIDATIONS
    # ===================================

    def validate(self, data):

        background_type = data.get(
            "background_type",
            getattr(
                self.instance,
                "background_type",
                None
            )
        )

        background_image = data.get(
            "background_image"
        )

        if (
            background_type == "image"
            and
            not background_image
            and
            not getattr(self.instance, "background_image", None)
        ):
            raise serializers.ValidationError({
                "background_image":
                    "Background image required."
            })

        return data




class CertificateApprovalSaveSerializer(serializers.ModelSerializer):
    admission_code = serializers.CharField(source='admission.admission_code', read_only=True)
    
    class Meta:
        model = CertificateApproval
        fields = ['admission', 'approval_date', 'remarks', 'admission_code']

    def validate(self, data):
        admission = data.get('admission')
        # Business Rule: Balance check
        fee_summary = FeeGeneration.objects.filter(admission=admission, is_active=True).aggregate(
            total_balance=models.Sum('balance_amount')
        )
        balance = fee_summary.get('total_balance') or Decimal('0.00')
        
        if balance > 0:
            raise serializers.ValidationError(f"Student has pending dues of ₹{balance}. Cannot approve.")
        
        return data

    
class CertificateIssueSerializer(serializers.ModelSerializer):

    student_name = serializers.ReadOnlyField(
        source='student.candidate_name'
    )

    admission_no = serializers.ReadOnlyField(
        source='student.admission_code'
    )

    template_name = serializers.ReadOnlyField(
        source='template.template_name'
    )

    course_name = serializers.ReadOnlyField(
        source='course.course_name'
    )

    batch_name = serializers.ReadOnlyField(
        source='batch.batch_name'
    )

    organization_name = serializers.ReadOnlyField(
        source='organization.name'
    )

    branch_name = serializers.ReadOnlyField(
        source='branch.name'
    )

    class Meta:
        model = CertificateIssue

        fields = '__all__'

        read_only_fields = [
            'certificate_no',
            'created_by',
            'organization',
            'branch'
        ]

    # =========================
    # VALIDATION
    # =========================
    def validate(self, data):

        student = data.get("student")
        course = data.get("course")
        template = data.get("template")

        # Check student-course mapping
        exists = AdmissionCourseBatch.objects.filter(
            admission=student,
            course=course,
            is_active=True
        ).exists()

        if not exists:
            raise serializers.ValidationError({
                "course":
                    "This course is not assigned to the student."
            })

        # Check template belongs to course
        if template.course_id != course.id:
            raise serializers.ValidationError({
                "template":
                    "Selected template does not belong to this course."
            })

        return data


class AttendanceSerializer(serializers.ModelSerializer):
    candidate_name = serializers.ReadOnlyField(source='admission.candidate_name')
    admission_code = serializers.ReadOnlyField(source='admission.admission_code')

    # =====================================
    # ORGANIZATION / BRANCH
    # =====================================

    organization = serializers.SerializerMethodField()

    branch = serializers.SerializerMethodField()

    # =====================================
    # COURSE / BATCH
    # =====================================

    courses = serializers.SerializerMethodField()

    # Return formatted duration instead of Decimal
    total_hours = serializers.SerializerMethodField()

    # Return email instead of user id
    marked_by = serializers.SerializerMethodField()

    class Meta:
        model = Attendance
        fields = [
            "id",
            "admission",
            "candidate_name",
            "admission_code",

            "organization",
            "branch",

            "courses",

            "date",

            "status",
            "time_in",
            "time_out",
            "total_hours",
            "remark",

            "marked_by",

            "is_active"
        ]

        read_only_fields = (
            "total_hours",
            "marked_by",
        )

    # =====================================
    # ORGANIZATION
    # =====================================

    def get_organization(self, obj):

        if obj.admission.organization:
            return {
                "id": obj.admission.organization.id,
                "name": obj.admission.organization.name
            }

        return None

    # =====================================
    # BRANCH
    # =====================================

    def get_branch(self, obj):

        if obj.admission.branch:
            return {
                "id": obj.admission.branch.id,
                "name": obj.admission.branch.name
            }

        return None

    # =====================================
    # COURSES + BATCHES
    # =====================================

    def get_courses(self, obj):

        mappings = obj.admission.course_batches.select_related(
            "course",
            "batch"
        )

        course_map = {}

        for cb in mappings:

            course_id = cb.course.id

            if course_id not in course_map:

                course_map[course_id] = {
                    "course_id": cb.course.id,
                    "course_name": cb.course.course_name,
                    "course_code": cb.course.course_code,
                    "batches": []
                }

            course_map[course_id]["batches"].append({
                "batch_id": cb.batch.id,
                "batch_name": cb.batch.batch_name,
                "batch_code": cb.batch.batch_code
            })

        return list(course_map.values())

    # =====================================
    # TOTAL HOURS
    # =====================================

    def get_total_hours(self, obj):

        if not obj.time_in or not obj.time_out:
            return None

        start = datetime.combine(
            obj.date,
            obj.time_in
        )

        end = datetime.combine(
            obj.date,
            obj.time_out
        )

        diff = end - start

        total_seconds = int(diff.total_seconds())

        hours = total_seconds // 3600

        minutes = (total_seconds % 3600) // 60

        return f"{hours} hr {minutes} min"

    # =====================================
    # MARKED BY
    # =====================================

    def get_marked_by(self, obj):

        if obj.marked_by:

            return obj.marked_by.email

        return None


    # =====================================
    # VALIDATION
    # =====================================

    def validate(self, data):

        admission = data.get(
            "admission",
            self.instance.admission if self.instance else None
        )

        date = data.get(
            "date",
            self.instance.date if self.instance else None
        )

        qs = Attendance.objects.filter(
            admission=admission,
            date=date
        )

        if self.instance:
            qs = qs.exclude(id=self.instance.id)

        if qs.exists():

            raise serializers.ValidationError({
                "error":
                    "Attendance already exists for this student on this date."
            })
        
        status = data.get(
            "status",
            self.instance.status if self.instance else None
        )

        time_in = data.get(
            "time_in",
            self.instance.time_in if self.instance else None
        )

        time_out = data.get(
            "time_out",
            self.instance.time_out if self.instance else None
        )

        if status in ["absent", "on_leave"]:

            data["time_in"] = None
            data["time_out"] = None


        if time_in and time_out:

            if time_out <= time_in:

                raise serializers.ValidationError({

                    "time_out":
                        "Time Out must be greater than Time In."

                })   

        if status == "half_day":

            if not time_in:

                raise serializers.ValidationError({

                    "time_in":
                        "Time In is required for Half Day."

                }) 

        return data


class AttendanceRecordSerializer(serializers.ModelSerializer):

    total_hours = serializers.SerializerMethodField()

    marked_by = serializers.SerializerMethodField()

    class Meta:
        model = Attendance
        fields = [
            "id",
            "date",

            "status",

            "time_in",
            "time_out",

            "total_hours",

            "remark",
            "marked_by",

            "is_active"
        ]

    def get_total_hours(self, obj):

        if not obj.time_in or not obj.time_out:
            return None

        start = datetime.combine(
            obj.date,
            obj.time_in
        )

        end = datetime.combine(
            obj.date,
            obj.time_out
        )

        diff = end - start

        total_seconds = int(diff.total_seconds())

        hours = total_seconds // 3600

        minutes = (total_seconds % 3600) // 60

        return f"{hours} hr {minutes} min"

    def get_marked_by(self, obj):

        if obj.marked_by:
            return obj.marked_by.email

        return None


class StudentAttendanceSerializer(serializers.ModelSerializer):

    attendance = serializers.SerializerMethodField()

    class Meta:
        model = Admission
        fields = [
            "id",
            "admission_code",
            "candidate_name",
            "mobile_no",
            "email",
            "attendance"
        ]

    def get_attendance(self, obj):

        attendance_qs = obj.attendance_records.filter(
            is_active=True
        ).order_by("-date")

        return AttendanceRecordSerializer(
            attendance_qs,
            many=True
        ).data
    

