
from django.utils import timezone

from rest_framework import serializers
from staff.models import Employee
from course.models import Batch, Course
from master.models import Branch
from admission.models import Admission
from .models import Assignment
from core.helper_function import get_branch_id


class TeacherSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = ['id', 'name']

class BatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Batch
        fields = ['id', 'batch_name', 'batch_code']

class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ['id', 'course_name', 'course_code']

from rest_framework import serializers
from django.db import transaction
from django.shortcuts import get_object_or_404


# serializers.py

from rest_framework import serializers
from django.db.models import Q

from .models import (
    Assignment,
    AssignmentSubmission
)

from admission.models import (
    Admission,
    AdmissionCourseBatch
)

from master.models import Branch


# =========================================================
# ASSIGNMENT SERIALIZER
# =========================================================

class AssignmentSerializer(serializers.ModelSerializer):

    teacher_name = serializers.ReadOnlyField(
        source="teacher.name"
    )

    batch_name = serializers.ReadOnlyField(
        source="batch.batch_name"
    )

    batch_code = serializers.ReadOnlyField(
        source="batch.batch_code"
    )

    course_name = serializers.ReadOnlyField(
        source="course.course_name"
    )

    course_code = serializers.ReadOnlyField(
        source="course.course_code"
    )

    branch_name = serializers.ReadOnlyField(
        source="branch.name"
    )

    created_by_name = serializers.SerializerMethodField()

    class Meta:

        model = Assignment

        fields = [
            "id",

            "teacher",
            "teacher_name",

            "course",
            "course_name",
            "course_code",

            "batch",
            "batch_name",
            "batch_code",

            "branch",
            "branch_name",

             # =============================
            # NEW FIELD
            # =============================

            "created_by",
            "created_by_name",
            "assignment_start_date",
            "submission_last_date",

            "title",
            "description",
            "file",

            "is_active",
            "created_at"
        ]

        read_only_fields = [
            "branch",
            "created_by",
            "is_active",
            "created_at"
        ]

    # =====================================================
    # FILE VALIDATION
    # =====================================================

    def validate_file(self, value):

        if value:

            if not value.name.lower().endswith(".pdf"):

                raise serializers.ValidationError(
                    "Only PDF files are allowed."
                )

        return value

    # =====================================================
    # MAIN VALIDATION
    # =====================================================

    def validate(self, data):

        request = self.context.get("request")

        branch_id = get_branch_id(request)

        if not branch_id:
            branch_id = request.data.get("branch")

        teacher = data.get("teacher")
        batch = data.get("batch")

        # -----------------------------------------
        # TEACHER VALIDATION
        # -----------------------------------------

        if teacher and branch_id:

            if teacher.branch_id != int(branch_id):

                raise serializers.ValidationError({
                    "teacher":
                    "Teacher does not belong to this branch."
                })

        # -----------------------------------------
        # BATCH VALIDATION
        # -----------------------------------------

        if batch and branch_id:

            if batch.branch_id != int(branch_id):

                raise serializers.ValidationError({
                    "batch":
                    "Batch does not belong to this branch."
                })

        return data
    
    # =====================================
    # CREATED BY NAME
    # =====================================

    def get_created_by_name(self, obj):

        if obj.created_by:

            return (
                getattr(obj.created_by, "email", None)
                or getattr(obj.created_by, "username", None)
            )

        return None

    # =====================================
    # VALIDATION
    # =====================================

    def validate(self, data):

        start_date = data.get(
            "assignment_start_date"
        )

        last_date = data.get(
            "submission_last_date"
        )

        if (
            start_date
            and last_date
            and last_date < start_date
        ):

            raise serializers.ValidationError({

                "submission_last_date":
                "Submission last date "
                "cannot be before assignment start date."
            })

        return data

    # =====================================================
    # CREATE
    # =====================================================

    def create(self, validated_data):

        request = self.context.get("request")

        # =====================================
        # SET CREATED BY
        # =====================================

        if request and request.user.is_authenticated:

            validated_data["created_by"] = request.user

        # =====================================
        # BRANCH LOGIC
        # =====================================

        branch_id = get_branch_id(request)

        if not branch_id and request:

            branch_id = (
                request.data.get("branch")
                or request.data.get("branch_id")
            )

        if not branch_id:

            raise serializers.ValidationError({
                "branch": "Branch is required."
            })

        try:

            branch = Branch.objects.get(
                id=branch_id
            )

        except Branch.DoesNotExist:

            raise serializers.ValidationError({
                "branch": "Invalid branch."
            })

        validated_data["branch"] = branch

        return super().create(validated_data)

    # =====================================================
    # UPDATE
    # =====================================================

    def update(self, instance, validated_data):

        validated_data.pop("branch", None)

        return super().update(instance, validated_data)


# =========================================================
# STUDENT ASSIGNMENT LIST SERIALIZER
# =========================================================

class StudentAssignmentListSerializer(serializers.ModelSerializer):

    teacher_name = serializers.ReadOnlyField(
        source="teacher.name"
    )

    batch_name = serializers.ReadOnlyField(
        source="batch.batch_name"
    )

    batch_code = serializers.ReadOnlyField(
        source="batch.batch_code"
    )

    course_name = serializers.ReadOnlyField(
        source="course.course_name"
    )

    course_code = serializers.ReadOnlyField(
        source="course.course_code"
    )

    created_by_name = serializers.SerializerMethodField()

    class Meta:

        model = Assignment

        fields = [

            "id",

            "title",

            "description",

            "file",

            # =====================================
            # NEW DATE FIELDS
            # =====================================

            "assignment_start_date",

            "submission_last_date",

            # =====================================
            # TEACHER
            # =====================================

            "teacher",

            "teacher_name",

            # =====================================
            # COURSE
            # =====================================

            "course",

            "course_name",

            "course_code",

            # =====================================
            # BATCH
            # =====================================

            "batch",

            "batch_name",

            "batch_code",

            # =====================================
            # CREATED BY
            # =====================================

            "created_by",

            "created_by_name",

            # =====================================
            # COMMON
            # =====================================

            "created_at"
        ]

    # =========================================
    # CREATED BY NAME
    # =========================================

    def get_created_by_name(self, obj):

        if obj.created_by:

            return (
                getattr(obj.created_by, "email", None)
                or getattr(obj.created_by, "username", None)
            )

        return None


# =========================================================
# ASSIGNMENT SUBMISSION SERIALIZER
# =========================================================

# class AssignmentSubmissionSerializer(serializers.ModelSerializer):

#     assignment_title = serializers.ReadOnlyField(
#         source="assignment.title"
#     )

#     admission_code = serializers.ReadOnlyField(
#         source="admission.admission_code"
#     )

#     candidate_name = serializers.ReadOnlyField(
#         source="admission.candidate_name"
#     )

#     assignment_start_date = serializers.ReadOnlyField(
#         source="assignment.assignment_start_date"
#     )

#     submission_last_date = serializers.ReadOnlyField(
#         source="assignment.submission_last_date"
#     )

#     class Meta:

#         model = AssignmentSubmission

#         fields = [
#             "id",

#             "assignment",
#             "assignment_title",

#             "admission",
#             "admission_code",
#             "candidate_name",

#             "assignment_start_date",
#             "submission_last_date",

#             "answer_text",
#             "answer_file",

#             "submitted_at"
#         ]

#         read_only_fields = [
#             "submitted_at"
#         ]

#     # =====================================================
#     # FILE VALIDATION
#     # =====================================================

#     def validate_answer_file(self, value):

#         if value:

#             allowed_extensions = [
#                 ".pdf",
#                 ".doc",
#                 ".docx",
#                 ".jpg",
#                 ".jpeg",
#                 ".png"
#             ]

#             filename = value.name.lower()

#             if not any(
#                 filename.endswith(ext)
#                 for ext in allowed_extensions
#             ):

#                 raise serializers.ValidationError(
#                     "Only PDF/DOC/DOCX/JPG/PNG allowed."
#                 )

#         return value

#     # =====================================================
#     # MAIN VALIDATION
#     # =====================================================

#     def validate(self, data):

#         assignment = data.get("assignment")
#         admission = data.get("admission")

#         # -----------------------------------------
#         # ASSIGNMENT ACTIVE
#         # -----------------------------------------

#         if not assignment.is_active:

#             raise serializers.ValidationError({
#                 "assignment":
#                 "Assignment is inactive."
#             })

#         # -----------------------------------------
#         # ADMISSION ACTIVE
#         # -----------------------------------------

#         if not admission.is_active:

#             raise serializers.ValidationError({
#                 "admission":
#                 "Admission is inactive."
#             })

#         # -----------------------------------------
#         # VALIDATE COURSE+BATCH MAPPING
#         # -----------------------------------------

#         valid_mapping = AdmissionCourseBatch.objects.filter(
#             admission=admission,
#             course=assignment.course,
#             batch=assignment.batch,
#             is_active=True
#         ).exists()

#         if not valid_mapping:

#             raise serializers.ValidationError({
#                 "admission":
#                 "Student does not belong "
#                 "to this course and batch."
#             })

#         return data

class AssignmentSubmissionSerializer(
    serializers.ModelSerializer
):

    # =====================================================
    # ASSIGNMENT DETAILS
    # =====================================================

    assignment_title = serializers.ReadOnlyField(
        source="assignment.title"
    )

    assignment_description = serializers.ReadOnlyField(
        source="assignment.description"
    )

    assignment_file = serializers.SerializerMethodField()

    assignment_start_date = serializers.ReadOnlyField(
        source="assignment.assignment_start_date"
    )

    submission_last_date = serializers.ReadOnlyField(
        source="assignment.submission_last_date"
    )

    # =====================================================
    # STUDENT DETAILS
    # =====================================================

    admission_code = serializers.ReadOnlyField(
        source="admission.admission_code"
    )

    candidate_name = serializers.ReadOnlyField(
        source="admission.candidate_name"
    )

    # =====================================================
    # COURSE DETAILS
    # =====================================================

    course = serializers.ReadOnlyField(
        source="assignment.course.id"
    )

    course_name = serializers.ReadOnlyField(
        source="assignment.course.course_name"
    )

    course_code = serializers.ReadOnlyField(
        source="assignment.course.course_code"
    )

    # =====================================================
    # BATCH DETAILS
    # =====================================================

    batch = serializers.ReadOnlyField(
        source="assignment.batch.id"
    )

    batch_name = serializers.ReadOnlyField(
        source="assignment.batch.batch_name"
    )

    batch_code = serializers.ReadOnlyField(
        source="assignment.batch.batch_code"
    )

    # =====================================================
    # TEACHER DETAILS
    # =====================================================

    teacher = serializers.ReadOnlyField(
        source="assignment.teacher.id"
    )

    teacher_name = serializers.ReadOnlyField(
        source="assignment.teacher.name"
    )

    # =====================================================
    # SUBMISSION FILE URL
    # =====================================================

    answer_file_url = serializers.SerializerMethodField()

    # =====================================================
    # REVIEW DETAILS
    # =====================================================

    reviewed_by_name = serializers.SerializerMethodField()

    class Meta:

        model = AssignmentSubmission

        fields = [

            # =====================================
            # COMMON
            # =====================================

            "id",

            # =====================================
            # ASSIGNMENT
            # =====================================

            "assignment",

            "assignment_title",

            "assignment_description",

            "assignment_file",

            "assignment_start_date",

            "submission_last_date",

            # =====================================
            # STUDENT
            # =====================================

            "admission",

            "admission_code",

            "candidate_name",

            # =====================================
            # COURSE
            # =====================================

            "course",

            "course_name",

            "course_code",

            # =====================================
            # BATCH
            # =====================================

            "batch",

            "batch_name",

            "batch_code",

            # =====================================
            # TEACHER
            # =====================================

            "teacher",

            "teacher_name",

            # =====================================
            # STUDENT SUBMISSION
            # =====================================

            "answer_text",

            "answer_file",

            "answer_file_url",

            "submitted_at",

            # =====================================
            # TEACHER REVIEW
            # =====================================

            "score",

            "teacher_comment",

            "is_reviewed",

            "reviewed_by",

            "reviewed_by_name",

            "reviewed_at",

            # =====================================
            # STATUS
            # =====================================

            "is_active"
        ]

        read_only_fields = [

            "submitted_at",

            "reviewed_by",

            "reviewed_at",

            "is_reviewed"
        ]

    # =====================================================
    # ASSIGNMENT FILE URL
    # =====================================================

    def get_assignment_file(self, obj):

        request = self.context.get("request")

        if obj.assignment.file and request:

            return request.build_absolute_uri(
                obj.assignment.file.url
            )

        return None

    # =====================================================
    # ANSWER FILE URL
    # =====================================================

    def get_answer_file_url(self, obj):

        request = self.context.get("request")

        if obj.answer_file and request:

            return request.build_absolute_uri(
                obj.answer_file.url
            )

        return None

    # =====================================================
    # REVIEWED BY NAME
    # =====================================================

    def get_reviewed_by_name(self, obj):

        if obj.reviewed_by:

            return (
                getattr(obj.reviewed_by, "email", None)
                or getattr(obj.reviewed_by, "username", None)
            )

        return None

    # =====================================================
    # FILE VALIDATION
    # =====================================================

    def validate_answer_file(self, value):

        if value:

            allowed_extensions = [

                ".pdf",

                ".doc",

                ".docx",

                ".jpg",

                ".jpeg",

                ".png"
            ]

            filename = value.name.lower()

            if not any(

                filename.endswith(ext)

                for ext in allowed_extensions
            ):

                raise serializers.ValidationError(

                    "Only PDF/DOC/DOCX/JPG/JPEG/PNG files are allowed."
                )

        return value

    # =====================================================
    # MAIN VALIDATION
    # =====================================================

    def validate(self, data):

        assignment = data.get(
            "assignment"
        ) or getattr(
            self.instance,
            "assignment",
            None
        )

        admission = data.get(
            "admission"
        ) or getattr(
            self.instance,
            "admission",
            None
        )

        # =====================================
        # ASSIGNMENT REQUIRED
        # =====================================

        if not assignment:

            raise serializers.ValidationError({

                "assignment":
                "Assignment is required."
            })

        # =====================================
        # ADMISSION REQUIRED
        # =====================================

        if not admission:

            raise serializers.ValidationError({

                "admission":
                "Admission is required."
            })

        # =====================================
        # ASSIGNMENT ACTIVE
        # =====================================

        if not assignment.is_active:

            raise serializers.ValidationError({

                "assignment":
                "Assignment is inactive."
            })

        # =====================================
        # ADMISSION ACTIVE
        # =====================================

        if not admission.is_active:

            raise serializers.ValidationError({

                "admission":
                "Admission is inactive."
            })

        # =====================================
        # START DATE VALIDATION
        # =====================================

        today = timezone.now().date()

        if (
            assignment.assignment_start_date
            and today
            <
            assignment.assignment_start_date
        ):

            raise serializers.ValidationError({

                "assignment":
                "Assignment submission has not started yet."
            })

        # =====================================
        # LAST DATE VALIDATION
        # =====================================

        if (
            assignment.submission_last_date
            and today
            >
            assignment.submission_last_date
        ):

            raise serializers.ValidationError({

                "assignment":
                "Submission last date exceeded."
            })

        # =====================================
        # VALIDATE COURSE+BATCH MAPPING
        # =====================================

        valid_mapping = (
            AdmissionCourseBatch.objects.filter(

                admission=admission,

                course=assignment.course,

                batch=assignment.batch,

                is_active=True

            ).exists()
        )

        if not valid_mapping:

            raise serializers.ValidationError({

                "admission":
                "Student does not belong "
                "to this course and batch."
            })

        return data
