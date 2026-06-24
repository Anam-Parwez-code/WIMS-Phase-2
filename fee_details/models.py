from django.utils import timezone
from django.db import models
from decimal import Decimal
from admission.models import Admission
from django.db.models import Sum
from master.models import Organization, Branch
from django.conf import settings

def get_current_date():
    return timezone.now().date()


class FeeGeneration(models.Model):

    admission = models.ForeignKey(
        "admission.Admission",
        on_delete=models.PROTECT,
        related_name="fee_generations"
    )

    course = models.ForeignKey(
        "course.Course", # Adjust the app name to your course model's app
        on_delete=models.PROTECT,
        related_name="fee_generations",
        null=True, # Initially null for migration, then make it false
        blank=True
    )

    generated_date = models.DateField()

    fee_type = models.CharField(
        max_length=20,
        choices=[("Monthly", "Monthly"), ("Installment", "Installment")]
    )

    course_fee = models.DecimalField(max_digits=18, decimal_places=2)
    extra_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    billing_before_gst = models.DecimalField(max_digits=18, decimal_places=2)

    gst_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    gst_amount = models.DecimalField(max_digits=18, decimal_places=2)

    kit_charges = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    total_fee = models.DecimalField(max_digits=18, decimal_places=2)


    payment_mode = models.ForeignKey(
        "master.PaymentMethod",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    # =========================
    # BANK PAYMENT DETAILS
    # =========================

    ledger = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    reference_no = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    reference_date = models.DateField(
        null=True,
        blank=True
    )

    bank_name = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    advance_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    balance_amount = models.DecimalField(max_digits=18, decimal_places=2)

    installment_count = models.PositiveIntegerField(null=True, blank=True)

    remarks = models.TextField(blank=True, null=True)

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.PROTECT
    )

    is_active = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="fees_created"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="fees_updated"
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["organization", "branch"]),
            models.Index(fields=["is_active"]),
        ]




class FeeMonthlyDetail(models.Model):
    fee_generation = models.ForeignKey(
        FeeGeneration,
        on_delete=models.CASCADE,
        related_name="monthly_details"
    )
    due_date = models.DateField(null=True, blank=True)
    month = models.CharField(max_length=10)   # Jan, Feb, etc
    year = models.IntegerField()

    class Meta:
        unique_together = ("fee_generation", "month", "year")

    def __str__(self):
        return f"{self.month}-{self.year}"


class FeeInstallment(models.Model):

    fee_generation = models.ForeignKey(
        FeeGeneration,
        on_delete=models.CASCADE,
        related_name="installments"
    )

    installment_no = models.PositiveIntegerField()

    amount = models.DecimalField(max_digits=18, decimal_places=2)

    total_paid = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0
    )

    due_date = models.DateField(db_index=True)

    is_paid = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def remaining_amount(self):
        return self.amount - self.total_paid





class FeeDeposit(models.Model):

    installment = models.ForeignKey(
        FeeInstallment,
        on_delete=models.PROTECT,
        related_name="deposits"
    )

    payment_date = models.DateField()
    payment_mode = models.ForeignKey(
        "master.PaymentMethod",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    paid_amount = models.DecimalField(max_digits=18, decimal_places=2)

    ledger = models.CharField(max_length=100, null=True, blank=True)
    reference_no = models.CharField(max_length=100, null=True, blank=True)
    reference_date = models.DateField(null=True, blank=True)
    bank_name = models.CharField(max_length=100, null=True, blank=True)

    send_email = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    

 


