from django.db import models
from staff.models import Employee
from course.models import Batch, Course
from admission.models import Admission

# models.py

from django.conf import settings

class Assignment(models.Model):

    teacher = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE
    )

    batch = models.ForeignKey(
        Batch,
        on_delete=models.CASCADE
    )

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE
    )

    branch = models.ForeignKey(
        'master.Branch',
        on_delete=models.CASCADE
    )

    # =====================================
    # NEW FIELD
    # =====================================

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assignments_created"
    )

    title = models.CharField(
        max_length=255
    )

    description = models.TextField()

    file = models.FileField(
        upload_to="assignments/",
        null=True,
        blank=True
    )

    assignment_start_date = models.DateField(
        null=True,
        blank=True
    )

    submission_last_date = models.DateField(
        null=True,
        blank=True
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):

        return self.title




# =========================================================
# ASSIGNMENT SUBMISSION
# =========================================================

# models.py

from django.conf import settings


class AssignmentSubmission(models.Model):

    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE
    )

    admission = models.ForeignKey(
        Admission,
        on_delete=models.CASCADE
    )

    answer_text = models.TextField(
        null=True,
        blank=True
    )

    answer_file = models.FileField(
        upload_to="assignment_answers/",
        null=True,
        blank=True
    )

    submitted_at = models.DateTimeField(
        auto_now_add=True
    )

    # =====================================
    # TEACHER REVIEW
    # =====================================

    score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )

    teacher_comment = models.TextField(
        null=True,
        blank=True
    )

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_assignment_submissions"
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    is_reviewed = models.BooleanField(
        default=False
    )

    is_active = models.BooleanField(
        default=True
    )

    class Meta:

        unique_together = (
            "assignment",
            "admission"
        )

    def __str__(self):

        return (
            f"{self.assignment.title} - "
            f"{self.admission.candidate_name}"
        )










