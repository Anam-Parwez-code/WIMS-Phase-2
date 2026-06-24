from datetime import timedelta
from decimal import Decimal
from .models import FeeInstallment

# def generate_installments(fee_generation):
#     installment_amount = (
#         fee_generation.balance_amount / fee_generation.installment_count
#     ).quantize(Decimal("0.01"))

#     installments = []
#     due_date = fee_generation.generated_date

#     for i in range(1, fee_generation.installment_count + 1):
#         due_date += timedelta(days=30)

#         installments.append(
#             FeeInstallment(
#                 fee_generation=fee_generation,
#                 installment_no=i,
#                 due_date=due_date,
#                 amount=installment_amount,
#             )
#         )

#     FeeInstallment.objects.bulk_create(installments)

def generate_installments(fee_generation):
    count = fee_generation.installment_count
    balance = fee_generation.balance_amount
    
    # Calculate base amount
    installment_amount = (balance / count).quantize(Decimal("0.01"))
    
    installments = []
    due_date = fee_generation.generated_date
    accumulated_amount = Decimal("0.00")

    for i in range(1, count + 1):
        due_date += timedelta(days=30)
        
        # If it's the last one, take the remaining balance instead of a fixed split
        if i == count:
            current_amount = balance - accumulated_amount
        else:
            current_amount = installment_amount
            accumulated_amount += current_amount

        installments.append(
            FeeInstallment(
                fee_generation=fee_generation,
                installment_no=i,
                due_date=due_date,
                amount=current_amount,
            )
        )

    FeeInstallment.objects.bulk_create(installments)