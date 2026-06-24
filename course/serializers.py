from rest_framework import serializers
from .models import Course, Batch, Module, Topic, CourseTracker
from decimal import Decimal
from django.db.models.functions import Lower
from .models import Course
from settings_app.utils import generate_code
from settings_app.models import CodePrefix
from django.db import transaction

class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = "__all__"
        read_only_fields = [
            "course_code",
            "gst_amount",
            "total_course_fee",
            "is_active"
        ]

    def validate(self, data):
        course_name = data.get("course_name") or (
            self.instance.course_name if self.instance else None
        )
        organization = data.get("organization") or (
            self.instance.organization if self.instance else None
        )
        branch = data.get("branch") or (
            self.instance.branch if self.instance else None
        )

        if not course_name:
            raise serializers.ValidationError({
                "course_name": "Course name is required."
            })

        if not organization:
            raise serializers.ValidationError({
                "organization": "Organization is required."
            })

        if branch and branch.organization_id != organization.id:
            raise serializers.ValidationError({
                "branch": "Branch does not belong to selected organization."
            })
        
        # Prefix Validation (Only for new records)
        if not self.instance:
            prefix_exists = CodePrefix.objects.filter(
                module__iexact="course",
                form__iexact="Course",
                is_active=True
            ).exists()

            if not prefix_exists:
                raise serializers.ValidationError({
                    "detail": "Course code prefix is not configured. Please configure the prefix in settings before creating a course."
                })

        qs = Course.objects.annotate(
            name_l=Lower("course_name")
        ).filter(
            name_l=course_name.lower(),
            organization=organization,
            is_active=True
        )

        if self.instance:
            qs = qs.exclude(id=self.instance.id)

        if qs.exists():
            raise serializers.ValidationError({
                "course_name": "Course name must be unique within this organization."
            })

        return data

    def create(self, validated_data):
        with transaction.atomic():
            prefix_obj = CodePrefix.objects.select_for_update().filter(
                module__iexact="course",
                form__iexact="Course",
                is_active=True
            ).first()

            if not prefix_obj:
                raise serializers.ValidationError({
                    "detail": "Course code prefix is not configured. Please configure the prefix in settings before creating a course."
                })

            prefix_obj.current_number += 1
            prefix_obj.save(update_fields=["current_number"])

            course_code = (
                f"{prefix_obj.prefix}"
                f"{str(prefix_obj.current_number).zfill(5)}"
            )

            basic_fee = validated_data["basic_course_fee"]
            gst_pct = validated_data.get("gst_percentage", Decimal("18"))

            gst_amount = (basic_fee * gst_pct) / Decimal("100")
            total_fee = basic_fee + gst_amount

            validated_data.update({
                "course_code": course_code,
                "gst_amount": gst_amount,
                "total_course_fee": total_fee
            })

            return super().create(validated_data)

    def update(self, instance, validated_data):
        basic_fee = validated_data.get(
            "basic_course_fee",
            instance.basic_course_fee
        )
        gst_percent = validated_data.get(
            "gst_percentage",
            instance.gst_percentage
        )

        gst_amount = (basic_fee * gst_percent) / Decimal("100")
        total_fee = basic_fee + gst_amount

        validated_data["gst_amount"] = gst_amount
        validated_data["total_course_fee"] = total_fee

        return super().update(instance, validated_data)

class BatchSerializer(serializers.ModelSerializer):
    course_name = serializers.ReadOnlyField(source='course.course_name')
    trainer_name = serializers.ReadOnlyField(source='trainer.name')
    organization_name = serializers.ReadOnlyField(source='organization.name')
    branch_name = serializers.ReadOnlyField(source='branch.name')

    class Meta:
        model = Batch
        fields = [
            "id", "batch_name", "batch_code", "batch_status",
            "batch_size", "batch_time", "start_date",
            "completion_date", "remark", "is_active",
            "course", "course_name",
            "trainer", "trainer_name",
            "organization", "organization_name",
            "branch", "branch_name"
        ]
        read_only_fields = ["batch_code", "is_active"]

    def validate_trainer(self, value):
        if value and value.designation.name.lower() != "trainer":
            raise serializers.ValidationError(
                "Selected employee is not a trainer."
            )
        return value

    def validate(self, data):
        batch_name = data.get("batch_name") or (
            self.instance.batch_name if self.instance else None
        )
        course = data.get("course") or (
            self.instance.course if self.instance else None
        )
        organization = data.get("organization") or (
            self.instance.organization if self.instance else None
        )
        branch = data.get("branch") or (
            self.instance.branch if self.instance else None
        )

        if not batch_name:
            raise serializers.ValidationError({"batch_name": "Batch name is required."})

        if not course:
            raise serializers.ValidationError({"course": "Course is required."})

        if branch and branch.organization_id != organization.id:
            raise serializers.ValidationError({
                "branch": "Branch does not belong to selected organization."
            })

        qs = Batch.objects.annotate(
            name_l=Lower("batch_name")
        ).filter(
            name_l=batch_name.lower(),
            course=course,
            is_active=True
        )

        if self.instance:
            qs = qs.exclude(id=self.instance.id)

        if qs.exists():
            raise serializers.ValidationError({
                "batch_name": "Batch name must be unique per course."
            })

        return data

    def create(self, validated_data):
        with transaction.atomic():
            prefix_obj = CodePrefix.objects.select_for_update().filter(
                module__iexact="course",
                form__iexact="Batch",
                is_active=True
            ).first()

            prefix_obj.current_number += 1
            prefix_obj.save(update_fields=["current_number"])

            validated_data["batch_code"] = (
                f"{prefix_obj.prefix}"
                f"{str(prefix_obj.current_number).zfill(5)}"
            )

            return super().create(validated_data)

class ModuleSerializer(serializers.ModelSerializer):
    course_name = serializers.ReadOnlyField(source='course.course_name')

    class Meta:
        model = Module
        fields = [
            "id", "module_name", "module_description",
            "organization", "branch",
            "course", "course_name",
            "is_active"
        ]
        read_only_fields = ["is_active"]

    def validate(self, data):
        module_name = data.get("module_name") or (
            self.instance.module_name if self.instance else None
        )
        course = data.get("course") or (
            self.instance.course if self.instance else None
        )

        if not module_name:
            raise serializers.ValidationError({"module_name": "Module name is required."})

        if not course:
            raise serializers.ValidationError({"course": "Course is required."})

        qs = Module.objects.annotate(
            name_l=Lower("module_name")
        ).filter(
            name_l=module_name.lower(),
            course=course,
            is_active=True
        )

        if self.instance:
            qs = qs.exclude(id=self.instance.id)

        if qs.exists():
            raise serializers.ValidationError({
                "module_name": "Module name must be unique within this course."
            })

        return data

class TopicSerializer(serializers.ModelSerializer):
    course_name = serializers.ReadOnlyField(source='course.course_name')
    module_name = serializers.ReadOnlyField(source='module.module_name')

    class Meta:
        model = Topic
        fields = [
            "id", "topic_name", "topic_content", "pdf_file",
            "organization", "branch",
            "course", "course_name",
            "module", "module_name",
            "is_active"
        ]
        read_only_fields = ["is_active"]

    def validate(self, data):
        topic_name = data.get("topic_name") or (
            self.instance.topic_name if self.instance else None
        )
        course = data.get("course") or (
            self.instance.course if self.instance else None
        )
        module = data.get("module") or (
            self.instance.module if self.instance else None
        )

        if not topic_name:
            raise serializers.ValidationError({"topic_name": "Topic name is required."})

        if module.course_id != course.id:
            raise serializers.ValidationError({
                "module": "Module does not belong to selected course."
            })

        qs = Topic.objects.annotate(
            name_l=Lower("topic_name")
        ).filter(
            name_l=topic_name.lower(),
            module=module,
            is_active=True
        )

        if self.instance:
            qs = qs.exclude(id=self.instance.id)

        if qs.exists():
            raise serializers.ValidationError({
                "topic_name": "Topic name must be unique within this module."
            })

        return data

class CourseTrackerSerializer(serializers.ModelSerializer):
    # Custom fields for readable names
    organization_name = serializers.ReadOnlyField(source='organization.name')
    branch_name = serializers.ReadOnlyField(source='branch.name')
    trainer_name = serializers.ReadOnlyField(source='trainer.name')
    batch_name = serializers.ReadOnlyField(source='batch.batch_name')
    course_name = serializers.ReadOnlyField(source='course.course_name')

    class Meta:
        model = CourseTracker
        fields = [
            "id", "is_active", "date", "status", "remark",
            "organization", "organization_name",
            "branch", "branch_name",
            "trainer", "trainer_name",
            "batch", "batch_name",
            "course", "course_name"
        ]
        read_only_fields = ["is_active"]

    def validate(self, data):
        # We use .get() because these fields might not be in the PUT request (partial update)
        organization = data.get("organization") or (self.instance.organization if self.instance else None)
        branch = data.get("branch") or (self.instance.branch if self.instance else None)
        course = data.get("course") or (self.instance.course if self.instance else None)
        batch = data.get("batch") or (self.instance.batch if self.instance else None)

        if branch and organization and branch.organization_id != organization.id:
            raise serializers.ValidationError({"branch": "Branch does not belong to selected organization."})

        if batch and course and batch.course_id != course.id:
            raise serializers.ValidationError({"batch": "Batch does not belong to selected course."})

        return data
