from rest_framework import serializers
from .models import FeeGeneration, FeeDeposit, FeeInstallment, FeeMonthlyDetail
from django.utils import timezone

def get_current_date():
    return timezone.now().date()

class FeeMonthlyDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeeMonthlyDetail
        fields = ["month", "year", "due_date"]

class FeeInstallmentSerializer(serializers.ModelSerializer):
    # Helpful for the frontend to calculate remaining per row
    remaining_amount = serializers.ReadOnlyField() 

    class Meta:
        model = FeeInstallment
        fields = "__all__"


class FeeGenerationSerializer(serializers.ModelSerializer):
    # FIX: Change candidate to admission
    candidate_name = serializers.ReadOnlyField(source='admission.candidate_name')
    monthly_details = FeeMonthlyDetailSerializer(many=True, read_only=True)
    installments = FeeInstallmentSerializer(many=True, read_only=True)

    class Meta:
        model = FeeGeneration
        fields = "__all__"
        # Note: Ensure these actually exist in model if you list them in read_only
        read_only_fields = ("billing_before_gst", "total_fee", "balance_amount") 

    def validate(self, data):

        advance_amount = data.get("advance_amount", 0)
        payment_mode_obj = data.get("payment_mode")

        if payment_mode_obj:

            mode_name = payment_mode_obj.name.lower()

            # =========================
            # BANK VALIDATION
            # =========================
            if "bank" in mode_name:

                required_fields = [
                    "ledger",
                    "reference_no",
                    "reference_date",
                    "bank_name"
                ]

                for field in required_fields:
                    if not data.get(field):
                        raise serializers.ValidationError({
                            field: f"{field} is required for bank payments."
                        })

        return data



class FeeDepositSerializer(serializers.ModelSerializer):
    payment_mode_name = serializers.ReadOnlyField(source='payment_mode.name')
    # Adding installment info can be helpful for receipts
    student_name = serializers.ReadOnlyField(source='installment.fee_generation.admission.candidate_name')
    admission_code = serializers.ReadOnlyField(
        source='installment.fee_generation.admission.admission_code'
    )
    installment_no = serializers.ReadOnlyField(source='installment.installment_no')

    class Meta:
        model = FeeDeposit
        fields = ["id", "installment", "paid_amount", "payment_mode", "bank_name", "reference_no", "payment_mode_name", "student_name", "admission_code", "installment_no", "payment_date", "reference_date", "bank_name", "send_email", "is_active", "created_at"] # "__all__" + "payment_mode_name" + "student_name" + "installment_no"

    def validate(self, data):
        # payment_mode is now a PaymentMethod instance
        payment_mode_obj = data.get("payment_mode")
        
        if payment_mode_obj:
            mode_name = payment_mode_obj.name.upper() # Standardize to uppercase for comparison
            
            if "BANK" in mode_name:
                if not data.get("bank_name") or not data.get("reference_no"):
                    raise serializers.ValidationError("bank_name and reference_no are required for Bank payments.")
            
            if "UPI" in mode_name and not data.get("reference_no"):
                raise serializers.ValidationError("reference_no is required for UPI.")
            
        return data
  


  
class DuesListSerializer(serializers.ModelSerializer):

    admission_no = serializers.ReadOnlyField(
        source="fee_generation.admission.admission_code"
    )

    student_name = serializers.ReadOnlyField(
        source="fee_generation.admission.candidate_name"
    )

    mobile_no = serializers.ReadOnlyField(
        source="fee_generation.admission.mobile_no"
    )

    installment_date = serializers.DateField(source="due_date")

    installment_amount = serializers.DecimalField(
        source="amount",
        max_digits=18,
        decimal_places=2
    )

    payment_status = serializers.SerializerMethodField()

    class Meta:
        model = FeeInstallment
        fields = [
            "id",  # used internally (row id)
            "admission_no",
            "student_name",
            "mobile_no",
            "installment_date",
            "installment_amount",
            "payment_status",
        ]

    def get_payment_status(self, obj):
        return "Paid" if obj.is_paid else "Unpaid"

class DuesExportSerializer(serializers.ModelSerializer):

    admission_no = serializers.CharField(
        source="fee_generation.admission.admission_code"
    )

    student_name = serializers.CharField(
        source="fee_generation.admission.candidate_name"
    )

    mobile_no = serializers.CharField(
        source="fee_generation.admission.mobile_no"
    )

    installment_date = serializers.DateField(source="due_date")
    installment_amount = serializers.DecimalField(
        source="amount",
        max_digits=18,
        decimal_places=2
    )

    payment_status = serializers.SerializerMethodField()

    class Meta:
        model = FeeInstallment
        fields = [
            "admission_no",
            "student_name",
            "mobile_no",
            "installment_date",
            "installment_amount",
            "payment_status",
        ]

    def get_payment_status(self, obj):
        return "Paid" if obj.is_paid else "Unpaid"
 