from django.db import models
from master.models import Branch, Organization
from staff.models import Employee
from django.db.models.functions import Lower
from rest_framework import serializers
from decimal import Decimal
from django.db import transaction

# -------------------------------
# 1. Course Model
# -------------------------------

class Course(models.Model):
    is_active = models.BooleanField(default=True)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )

    course_code = models.CharField(max_length=30)
    course_name = models.CharField(max_length=100)
    course_duration = models.CharField(max_length=50)
    course_description = models.TextField(blank=True)


    # 💰 Fee fields
    basic_course_fee = models.DecimalField(max_digits=10, decimal_places=2)
    gst_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=18.00
    )
    gst_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        editable=False
    )
    total_course_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        editable=False
    )

    # NEW
    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        indexes = [
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return f"{self.course_name} ({self.course_code})"



# -------------------------------
# 2. Batch Model
# -------------------------------

class Batch(models.Model):
    BATCH_STATUS_CHOICES = [
        ('to start', 'To Start'),
        ('on hold', 'On Hold'),
        ('completed', 'Completed'),
    ]

    # 🔐 Multi-tenant
    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )

    is_active = models.BooleanField(default=True)

    # 🔢 Auto-generated
    batch_code = models.CharField(max_length=20)

    batch_name = models.CharField(max_length=100)
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="batches"
    )

    trainer = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    start_date = models.DateField()
    completion_date = models.DateField()
    batch_time = models.CharField(max_length=50)
    batch_size = models.PositiveIntegerField()
    batch_status = models.CharField(
        max_length=20,
        choices=BATCH_STATUS_CHOICES
    )
    remark = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return f"{self.batch_name} ({self.batch_code})"


# -------------------------------
# 3. Module Model
# -------------------------------

class Module(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )
    is_active = models.BooleanField(default=True)

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="modules"
    )
    module_name = models.CharField(max_length=100)
    module_description = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=[ "is_active"]),
        ]

    def __str__(self):
        return f"{self.module_name} - {self.course.course_name}"


# -------------------------------
# 4. Topic Model
# -------------------------------

class Topic(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )
    is_active = models.BooleanField(default=True)

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="topics"
    )
    module = models.ForeignKey(
        Module,
        on_delete=models.CASCADE,
        related_name="topics"
    )

    topic_name = models.CharField(max_length=100)
    topic_content = models.TextField()
    pdf_file = models.FileField(
        upload_to="topics_pdfs/",
        null=True,
        blank=True
    )

    class Meta:
        indexes = [
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return self.topic_name


# -------------------------------
# 5. CourseTracker Model
# -------------------------------

class CourseTracker(models.Model):
    is_active = models.BooleanField(default=True)

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="course_trackers",
        null=True,
        blank=True
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        related_name="course_trackers",
        null=True,
        blank=True
    )

    trainer = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    batch = models.ForeignKey(
        Batch,
        on_delete=models.CASCADE,
        related_name="course_trackers"
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="course_trackers"
    )
    date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=50, null=True, blank=True)
    remark = models.TextField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return f"{self.course.course_name} - {self.batch.batch_name}"
