import csv
from django.utils import timezone
from admission.serializers import AdmissionSerializer
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from core.permissions import IsSuperAdminOrClientAdmin
from django.db import transaction
from rest_framework.response import Response
from rest_framework import status
from .models import FeeGeneration, FeeDeposit, FeeMonthlyDetail
from .serializers import FeeGenerationSerializer, DuesListSerializer, FeeDepositSerializer
from .services import generate_installments
from core.utils import log_audit, log_activity
from .models import FeeInstallment
from admission.models import Admission, AdmissionCourseBatch
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.core.paginator import Paginator
from django.utils.dateparse import parse_date
from django.http import HttpResponse
from core.helper_function import get_branch_id
from decimal import Decimal, ROUND_HALF_UP
# reportlab imports for pdf creation
from django.db.models import Sum
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import pagesizes
from reportlab.lib.units import inch
from dateutil.relativedelta import relativedelta
from datetime import datetime
from io import BytesIO
from decimal import Decimal
from .serializers import FeeGenerationSerializer

from decimal import Decimal


#Updated

def allocate_payment_to_installments(fee_generation, amount, payment_data=None):
    """
    Automatically distribute payment across installments.

    payment_data:
        {
            "payment_date": ...,
            "payment_mode": ...,
            "ledger": ...,
            "reference_no": ...,
            "reference_date": ...,
            "bank_name": ...
        }
    """

    remaining_amount = Decimal(str(amount))

    installments = fee_generation.installments.filter(
        is_active=True
    ).order_by("installment_no")

    for installment in installments:

        if remaining_amount <= 0:
            break

        installment_balance = installment.amount - installment.total_paid

        # Skip fully paid installments
        if installment_balance <= 0:
            continue

        pay_amount = min(remaining_amount, installment_balance)

        # =========================================
        # CREATE DEPOSIT
        # =========================================

        FeeDeposit.objects.create(
            installment=installment,
            paid_amount=pay_amount,
            payment_date=payment_data.get("payment_date"),
            payment_mode_id=payment_data.get("payment_mode"),

            ledger=payment_data.get("ledger"),
            reference_no=payment_data.get("reference_no"),
            reference_date=payment_data.get("reference_date"),
            bank_name=payment_data.get("bank_name"),

            is_active=True
        )

        # =========================================
        # UPDATE INSTALLMENT
        # =========================================

        installment.total_paid += pay_amount

        installment.is_paid = (
            installment.total_paid >= installment.amount
        )

        installment.save()

        remaining_amount -= pay_amount

    # =========================================
    # UPDATE FEE GENERATION BALANCE
    # =========================================

    # fee_generation.balance_amount -= Decimal(str(amount))

    # if fee_generation.balance_amount < 0:
    #     fee_generation.balance_amount = Decimal("0")

    # fee_generation.save()

    return True


from master.models import Branch


# def can_access_fee_branch(
#     request,
#     fee_branch_id,
#     fee_org_id
# ):
#     user = request.user

#     # =================================
#     # CLIENT ADMIN
#     # =================================

#     if getattr(user, "role", None) == "client_admin":
#         return True

#     branch_id = get_branch_id(request)

#     if not branch_id:
#         return False

#     user_branch = Branch.objects.filter(
#         id=branch_id,
#         is_active=True
#     ).first()

#     if not user_branch:
#         return False

#     # =================================
#     # MAIN BRANCH
#     # =================================

#     if user_branch.is_main_branch:

#         return (
#             user_branch.organization_id
#             == fee_org_id
#         )

#     # =================================
#     # NORMAL USERS
#     # =================================

#     return int(branch_id) == int(fee_branch_id)


from master.models import Branch


def can_access_fee_branch(request, fee_branch_id):

    print("=" * 60)
    print("INSIDE can_access_fee_branch")

    print("FEE BRANCH RECEIVED:", fee_branch_id)

    user = request.user

    print("USER:", user)

    # ==========================
    # TOKEN DETAILS
    # ==========================

    token_branch_id = get_branch_id(request)

    token_org_id = None

    if request.auth:
        token_org_id = (
            request.auth.get("organization_id")
            or request.auth.get("organization")
        )

    print("TOKEN BRANCH:", token_branch_id)
    print("TOKEN ORG:", token_org_id)

    print(
        "ACTIVE BRANCHES:",
        list(
            Branch.objects.filter(
                is_active=True
            ).values_list(
                "id",
                flat=True
            )
        )
    )

    # ==========================
    # CLIENT ADMIN
    # ==========================

    if getattr(user, "role", None) == "client_admin":

        print("CLIENT ADMIN ACCESS GRANTED")

        return True, "Client admin access granted"

    # ==========================
    # TOKEN BRANCH CHECK
    # ==========================

    if not token_branch_id:

        print("NO BRANCH FOUND IN TOKEN")

        return False, (
            "No branch found in access token"
        )

    # ==========================
    # USER BRANCH
    # ==========================

    user_branch = Branch.objects.filter(
        id=token_branch_id,
        is_active=True
    ).first()

    print("USER BRANCH:", user_branch)

    if not user_branch:

        print(
            f"BRANCH {token_branch_id} "
            f"DOES NOT EXIST OR INACTIVE"
        )

        return False, (
            f"Branch {token_branch_id} "
            f"from token does not exist "
            f"or is inactive"
        )

    print(
        "USER BRANCH ORG:",
        user_branch.organization_id
    )

    print(
        "USER BRANCH IS MAIN:",
        user_branch.is_main_branch
    )

    # ==========================
    # TARGET BRANCH
    # ==========================

    target_branch = Branch.objects.filter(
        id=fee_branch_id,
        is_active=True
    ).first()

    print("TARGET BRANCH:", target_branch)

    if not target_branch:

        print(
            f"TARGET BRANCH {fee_branch_id} "
            f"NOT FOUND"
        )

        return False, (
            f"Fee branch {fee_branch_id} "
            f"does not exist"
        )

    print(
        "TARGET ORG:",
        target_branch.organization_id
    )

    # ==========================
    # MAIN BRANCH ACCESS
    # ==========================

    if user_branch.is_main_branch:

        print(
            "USER IS MAIN BRANCH"
        )

        if (
            user_branch.organization_id
            == target_branch.organization_id
        ):

            print(
                "MAIN BRANCH ACCESS GRANTED"
            )

            return True, (
                f"Main branch access granted. "
                f"Organization="
                f"{user_branch.organization_id}"
            )

        print(
            "MAIN BRANCH ORG MISMATCH"
        )

        return False, (
            f"Main branch belongs to Org "
            f"{user_branch.organization_id}, "
            f"but fee belongs to Org "
            f"{target_branch.organization_id}"
        )

    # ==========================
    # NORMAL USER ACCESS
    # ==========================

    if user_branch.id == target_branch.id:

        print(
            "OWN BRANCH ACCESS GRANTED"
        )

        return True, (
            f"Own branch access granted. "
            f"Branch={user_branch.id}"
        )

    print(
        "ACCESS DENIED"
    )

    return False, (
        f"Access denied. "
        f"Token Branch={user_branch.id}, "
        f"Fee Branch={target_branch.id}, "
        f"Main Branch={user_branch.is_main_branch}"
    )

class DuesListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        mode = request.GET.get("mode", "dues")
        search = request.GET.get("search", "")
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")

        page_number = request.GET.get("page", 1)
        page_size = int(request.GET.get("page_size", 20))

        ordering = request.GET.get(
            "ordering",
            "-due_date"
        )

        organization_id = request.GET.get(
            "organization"
        )

        branch_id = request.GET.get(
            "branch"
        )

        queryset = FeeInstallment.objects.select_related(
            "fee_generation",
            "fee_generation__admission"
        ).filter(
            is_active=True,
            fee_generation__is_active=True
        )

        # =====================================
        # ORGANIZATION FILTER
        # =====================================

        if organization_id:

            queryset = queryset.filter(
                fee_generation__admission__organization_id=
                organization_id
            )

        # =====================================
        # BRANCH FILTER
        # =====================================

        if branch_id:

            queryset = queryset.filter(
                fee_generation__admission__branch_id=
                branch_id
            )

        # -------------------------
        # MODE LOGIC
        # -------------------------

        if mode == "dues":

            queryset = queryset.filter(
                is_paid=False
            )

        elif mode == "datewise":

            if start_date and end_date:

                queryset = queryset.filter(
                    due_date__range=[
                        parse_date(start_date),
                        parse_date(end_date)
                    ]
                )

        elif mode == "search":

            if search:

                queryset = queryset.filter(
                    Q(
                        fee_generation__admission__candidate_name__icontains=
                        search
                    )
                    |
                    Q(
                        fee_generation__admission__admission_code__icontains=
                        search
                    )
                    |
                    Q(
                        fee_generation__admission__mobile_no__icontains=
                        search
                    )
                )

        # -------------------------
        # Sorting
        # -------------------------

        queryset = queryset.order_by(ordering)

        # -------------------------
        # Pagination
        # -------------------------

        paginator = Paginator(
            queryset,
            page_size
        )

        page = paginator.get_page(
            page_number
        )

        serializer = DuesListSerializer(
            page.object_list,
            many=True
        )

        return Response({
            "total_records": paginator.count,
            "total_pages": paginator.num_pages,
            "current_page": page.number,
            "results": serializer.data
        }, status=status.HTTP_200_OK)



class DuesExportAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        mode = request.GET.get(
            "mode",
            "dues"
        )

        search = request.GET.get(
            "search",
            ""
        )

        start_date = request.GET.get(
            "start_date"
        )

        end_date = request.GET.get(
            "end_date"
        )

        organization_id = request.GET.get(
            "organization"
        )

        branch_id = request.GET.get(
            "branch"
        )

        queryset = FeeInstallment.objects.select_related(
            "fee_generation",
            "fee_generation__admission"
        ).filter(
            is_active=True,
            fee_generation__is_active=True
        )

        # =====================================
        # ORGANIZATION FILTER
        # =====================================

        if organization_id:

            queryset = queryset.filter(
                fee_generation__admission__organization_id=
                organization_id
            )

        # =====================================
        # BRANCH FILTER
        # =====================================

        if branch_id:

            queryset = queryset.filter(
                fee_generation__admission__branch_id=
                branch_id
            )

        # =====================================
        # MODE LOGIC
        # =====================================

        if mode == "dues":

            queryset = queryset.filter(
                is_paid=False
            )

        elif mode == "datewise":

            if start_date and end_date:

                queryset = queryset.filter(
                    due_date__range=[
                        parse_date(start_date),
                        parse_date(end_date)
                    ]
                )

        elif mode == "search":

            if search:

                queryset = queryset.filter(
                    Q(
                        fee_generation__admission__candidate_name__icontains=
                        search
                    )
                    |
                    Q(
                        fee_generation__admission__admission_code__icontains=
                        search
                    )
                    |
                    Q(
                        fee_generation__admission__mobile_no__icontains=
                        search
                    )
                )

        queryset = queryset.order_by(
            "-due_date"
        )

        response = HttpResponse(
            content_type="text/csv"
        )

        response[
            "Content-Disposition"
        ] = 'attachment; filename="dues_list.csv"'

        writer = csv.writer(response)

        writer.writerow([
            "Admission No",
            "Student Name",
            "Mobile No",
            "Installment Date",
            "Installment Amount",
            "Payment Status"
        ])

        for obj in queryset:

            writer.writerow([
                obj.fee_generation.admission.admission_code,
                obj.fee_generation.admission.candidate_name,
                obj.fee_generation.admission.mobile_no,
                obj.due_date,
                obj.amount,
                "Paid" if obj.is_paid else "Unpaid"
            ])

        return response


#Updated




class FeeDepositInsertUpdateAPIView(APIView):
    permission_classes = [IsAuthenticated]


    def get(self, request):

        deposit_id = request.query_params.get("id")
        installment_id = request.query_params.get("installment_id")
        fee_generation_id = request.query_params.get("fee_generation_id")

        organization_id = request.query_params.get(
            "organization"
        )

        branch_id = request.query_params.get(
            "branch"
        )

        # =========================
        # 1. SINGLE DEPOSIT
        # =========================

        if deposit_id:

            deposit = get_object_or_404(
                FeeDeposit.objects.select_related(
                    "installment",
                    "installment__fee_generation",
                    "installment__fee_generation__admission",
                    "payment_mode"
                ),
                id=deposit_id,
                is_active=True
            )

            admission = (
                deposit.installment
                .fee_generation
                .admission
            )

            # =========================
            # ORGANIZATION FILTER
            # =========================

            if (
                organization_id
                and admission.organization_id != int(organization_id)
            ):
                return Response(
                    {"error": "Deposit not found"},
                    status=404
                )

            # =========================
            # BRANCH FILTER
            # =========================

            if (
                branch_id
                and admission.branch_id != int(branch_id)
            ):
                return Response(
                    {"error": "Deposit not found"},
                    status=404
                )

            return Response(
                FeeDepositSerializer(deposit).data
            )

        # =========================
        # 2. BY INSTALLMENT
        # =========================

        if installment_id:

            installment = get_object_or_404(
                FeeInstallment.objects.select_related(
                    "fee_generation",
                    "fee_generation__admission"
                ),
                id=installment_id,
                is_active=True
            )

            admission = installment.fee_generation.admission

            # =========================
            # ORGANIZATION FILTER
            # =========================

            if (
                organization_id
                and admission.organization_id != int(organization_id)
            ):
                return Response(
                    {"error": "Installment not found"},
                    status=404
                )

            # =========================
            # BRANCH FILTER
            # =========================

            if (
                branch_id
                and admission.branch_id != int(branch_id)
            ):
                return Response(
                    {"error": "Installment not found"},
                    status=404
                )

            deposits = FeeDeposit.objects.filter(
                installment_id=installment_id,
                is_active=True
            ).select_related(
                "payment_mode"
            )

            return Response(
                FeeDepositSerializer(
                    deposits,
                    many=True
                ).data
            )

        # =========================
        # 3. BY FEE GENERATION
        # =========================

        if fee_generation_id:

            fee = get_object_or_404(
                FeeGeneration.objects.select_related(
                    "admission"
                ),
                id=fee_generation_id,
                is_active=True
            )

            admission = fee.admission

            # =========================
            # ORGANIZATION FILTER
            # =========================

            if (
                organization_id
                and admission.organization_id != int(organization_id)
            ):
                return Response(
                    {"error": "Fee generation not found"},
                    status=404
                )

            # =========================
            # BRANCH FILTER
            # =========================

            if (
                branch_id
                and admission.branch_id != int(branch_id)
            ):
                return Response(
                    {"error": "Fee generation not found"},
                    status=404
                )

            deposits = FeeDeposit.objects.filter(
                installment__fee_generation=fee,
                is_active=True
            ).select_related(
                "payment_mode",
                "installment"
            )

            return Response(
                FeeDepositSerializer(
                    deposits,
                    many=True
                ).data
            )

        # =========================
        # 4. ALL DEPOSITS
        # =========================

        queryset = FeeDeposit.objects.select_related(
            "installment",
            "installment__fee_generation",
            "installment__fee_generation__admission",
            "payment_mode"
        ).filter(
            is_active=True
        ).order_by(
            "-created_at"
        )

        # =========================
        # ORGANIZATION FILTER
        # =========================

        if organization_id:

            queryset = queryset.filter(
                installment__fee_generation__admission__organization_id=
                organization_id
            )

        # =========================
        # BRANCH FILTER
        # =========================

        if branch_id:

            queryset = queryset.filter(
                installment__fee_generation__admission__branch_id=
                branch_id
            )

        serializer = FeeDepositSerializer(
            queryset,
            many=True
        )

        return Response({
            "count": queryset.count(),
            "results": serializer.data
        })

    @transaction.atomic
    def post(self, request):
        deposit_id = request.data.get("id")
        user = request.user
        branch_id = get_branch_id(request)

        paid_amount_new = Decimal(str(request.data.get("paid_amount", 0)))

        if paid_amount_new <= 0:
            return Response({"error": "Amount must be greater than 0"}, status=400)

        # =========================
        # 🔄 UPDATE CASE
        # =========================
        if deposit_id:
            deposit = get_object_or_404(FeeDeposit, id=deposit_id, is_active=True)
            installment = deposit.installment
            fee_gen = installment.fee_generation

            print("TOKEN USER:", request.user)
            print("BRANCH FROM TOKEN:", get_branch_id(request))
            print("FEE ADMISSION:", fee_gen.admission_id)
            print("FEE ORG:", fee_gen.admission.organization_id)
            print("FEE BRANCH:", fee_gen.admission.branch_id)

            # 🔐 Branch check
            # if branch_id and fee_gen.branch_id != int(branch_id):
            #     return Response({"error": "Unauthorized"}, status=403)

            # if not can_access_fee_branch(
            #     request,
            #     fee_gen.branch_id,
            #     fee_gen.organization_id
            # ):
            #     return Response(
            #         {"error": "Unauthorized"},
            #         status=403
            #     )

            print("FEE GEN ID:", fee_gen.id)
            print("FEE GEN BRANCH FIELD:", getattr(fee_gen, "branch_id", None))
            print("ADMISSION BRANCH:", fee_gen.admission.branch_id)
            print("ADMISSION ORG:", fee_gen.admission.organization_id)

            allowed, message = can_access_fee_branch(
                request,
                fee_gen.admission.branch_id
            )

            print("FEE ACCESS:", message)

           

            if not allowed:
                return Response(
                    {
                        "error": "Unauthorized",
                        "reason": message
                    },
                    status=403
                )



            old_amount = deposit.paid_amount
            diff = paid_amount_new - old_amount   # 🔥 CORE LOGIC

            # 🚨 Prevent overpayment at fee level
            if diff > 0 and diff > fee_gen.balance_amount:
                return Response({
                    "error": f"Exceeds total balance. Max allowed: {fee_gen.balance_amount}"
                }, status=400)

            # Save deposit
            serializer = FeeDepositSerializer(deposit, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()

            # 🔄 UPDATE INSTALLMENT
            installment.total_paid += diff

            # Do not lock strictly
            if installment.total_paid <= 0:
                installment.total_paid = 0

            installment.is_paid = installment.total_paid >= installment.amount
            installment.save()

            # 🔄 UPDATE FEE
            fee_gen.balance_amount -= diff
            if fee_gen.balance_amount < 0:
                fee_gen.balance_amount = 0

            fee_gen.save()

            return Response({
                "message": "Deposit updated successfully",
                "updated_diff": float(diff),
                "new_balance": float(fee_gen.balance_amount),
                "installment_paid": float(installment.total_paid)
            })

        

        # =========================
        # ➕ CREATE CASE
        # =========================

        installment_id = request.data.get("installment")

        installment = get_object_or_404(
            FeeInstallment.objects.select_related("fee_generation"),
            id=installment_id,
            is_active=True
        )

        fee_gen = installment.fee_generation

        print("TOKEN USER:", request.user)
        print("BRANCH FROM TOKEN:", get_branch_id(request))
        print(
            "FEE ADMISSION:",
            fee_gen.admission_id
        )

        print(
            "FEE ORG:",
            fee_gen.admission.organization_id
        )

        print(
            "FEE BRANCH:",
            fee_gen.admission.branch_id
        )

        allowed, message = can_access_fee_branch(
            request,
            fee_gen.admission.branch_id
        )

        print("FEE ACCESS:", message)

        # 🔐 Branch check
        # if branch_id and fee_gen.branch_id != int(branch_id):
        #     return Response({"error": "Unauthorized"}, status=403)

        # allowed, message = can_access_fee_branch(
        #     request,
        #     fee_gen.branch_id
        # )

        if not allowed:
            return Response(
                {
                    "error": "Unauthorized",
                    "reason": message
                },
                status=403
            )





        # 🚨 Prevent overpayment
        if paid_amount_new > fee_gen.balance_amount:
            return Response({
                "error": f"Exceeds total balance. Max allowed: {fee_gen.balance_amount}"
            }, status=400)

        remaining_amount = paid_amount_new

        installments = fee_gen.installments.filter(
            is_active=True
        ).order_by("installment_no")

        started = False

        for inst in installments:

            # Start allocation from selected installment
            if inst.id == installment.id:
                started = True

            if not started:
                continue

            if remaining_amount <= 0:
                break

            installment_balance = inst.amount - inst.total_paid

            if installment_balance <= 0:
                continue

            pay_amount = min(remaining_amount, installment_balance)

            FeeDeposit.objects.create(
                installment=inst,
                paid_amount=pay_amount,
                payment_date=request.data.get("payment_date"),
                payment_mode_id=request.data.get("payment_mode"),

                ledger=request.data.get("ledger"),
                reference_no=request.data.get("reference_no"),
                reference_date=request.data.get("reference_date"),
                bank_name=request.data.get("bank_name"),

                send_email=request.data.get("send_email", False),
                is_active=True
            )

            inst.total_paid += pay_amount

            inst.is_paid = inst.total_paid >= inst.amount

            inst.save()

            remaining_amount -= pay_amount

        # =========================================
        # UPDATE FEE BALANCE
        # =========================================

        fee_gen.balance_amount -= paid_amount_new

        if fee_gen.balance_amount < 0:
            fee_gen.balance_amount = 0

        fee_gen.save()

        return Response({
            "message": "Deposit recorded successfully",
            "paid_amount": float(paid_amount_new),
            "remaining_balance": float(fee_gen.balance_amount)
        }, status=201)



class FeeDepositUpdateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def put(self, request, deposit_id):
        branch_id = get_branch_id(request)

        deposit = get_object_or_404(
            FeeDeposit.objects.select_related(
                "installment",
                "installment__fee_generation"
            ),
            id=deposit_id,
            is_active=True
        )

        installment = deposit.installment
        fee_gen = installment.fee_generation

        # 🔐 Branch check
        # if branch_id and fee_gen.branch_id != int(branch_id):
        #     return Response({"error": "Unauthorized"}, status=403)

        # if not can_access_fee_branch(
        #     request,
        #     fee_gen.branch_id,
        #     fee_gen.organization_id
        # ):
        #     return Response(
        #         {"error": "Unauthorized"},
        #         status=403
        #     )

        allowed, message = can_access_fee_branch(
            request,
            fee_gen.admission.branch_id
        )

        if not allowed:
            return Response(
                {
                    "error": "Unauthorized",
                    "reason": message
                },
                status=403
            )



        new_amount = Decimal(str(request.data.get("paid_amount", deposit.paid_amount)))
        old_amount = deposit.paid_amount
        diff = new_amount - old_amount

        # 🚨 Prevent overpayment
        if diff > 0 and diff > fee_gen.balance_amount:
            return Response({
                "error": f"Exceeds total balance. Max allowed: {fee_gen.balance_amount}"
            }, status=400)

        # Save deposit
        serializer = FeeDepositSerializer(deposit, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # =========================
        # 🔁 SAFE RECALCULATION
        # =========================

        # Installment
        total_paid = installment.deposits.filter(
            is_active=True
        ).aggregate(total=Sum("paid_amount"))["total"] or Decimal("0")

        installment.total_paid = total_paid
        installment.is_paid = total_paid >= installment.amount
        installment.save()

        # Fee
        total_paid_fee = FeeDeposit.objects.filter(
            installment__fee_generation=fee_gen,
            is_active=True
        ).aggregate(total=Sum("paid_amount"))["total"] or Decimal("0")

        fee_gen.balance_amount = fee_gen.total_fee - total_paid_fee
        if fee_gen.balance_amount < 0:
            fee_gen.balance_amount = Decimal("0")

        fee_gen.save()

        return Response({
            "message": "Deposit updated successfully",
            "updated_amount": float(new_amount),
            "balance": float(fee_gen.balance_amount)
        })



class FeeDepositDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def delete(self, request, deposit_id):

        user = request.user
        branch_id = get_branch_id(request)

        deposit = get_object_or_404(
            FeeDeposit.objects.select_related(
                "installment",
                "installment__fee_generation"
            ),
            id=deposit_id,
            is_active=True
        )

        installment = deposit.installment
        fee_generation = installment.fee_generation

        # 🔐 Branch check (SAFE)
        if branch_id and fee_generation.branch_id != int(branch_id):
            return Response({"error": "Unauthorized"}, status=403)

        paid_amount = deposit.paid_amount

        # -------------------------
        # ❌ Soft delete FIRST
        # -------------------------
        deposit.is_active = False
        deposit.save()

        # -------------------------
        # 🔁 Recalculate installment total_paid (SAFE WAY)
        # -------------------------
        total_paid = installment.deposits.filter(
            is_active=True
        ).aggregate(
            total=Sum("paid_amount")
        )["total"] or Decimal("0")

        installment.total_paid = total_paid
        installment.is_paid = total_paid >= installment.amount
        installment.save()

        # -------------------------
        # 🔁 Recalculate fee balance (SAFE WAY)
        # -------------------------
        total_paid_fee = FeeDeposit.objects.filter(
            installment__fee_generation=fee_generation,
            is_active=True
        ).aggregate(
            total=Sum("paid_amount")
        )["total"] or Decimal("0")

        fee_generation.balance_amount = fee_generation.total_fee - total_paid_fee

        if fee_generation.balance_amount < 0:
            fee_generation.balance_amount = Decimal("0")

        fee_generation.save()

        return Response({
            "message": "Deposit cancelled successfully",
            "reversed_amount": float(paid_amount),
            "installment_total_paid": float(installment.total_paid),
            "remaining_balance": float(fee_generation.balance_amount)
        }, status=status.HTTP_200_OK)


class GetDepositsByStudentAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, student_id):
        


        user = request.user
        branch_id = get_branch_id(request)

        if branch_id:
            student = get_object_or_404(
                Admission,
                id=student_id,
                branch_id=int(branch_id),
                is_active=True
            )
        else:
            student = get_object_or_404(
                Admission,
                id=student_id,
                is_active=True
            )
        branch_id = student.branch_id
        # -------------------------
        # Get active fee generations
        # -------------------------
        fee_generations = FeeGeneration.objects.filter(
            admission=student,
            branch=branch_id,
            is_active=True
        ).prefetch_related("installments")

        fees_data = []

        for fee in fee_generations:

            unpaid_installments = fee.installments.filter(
                is_paid=False,
                is_active=True
            ).order_by("due_date")

            if not unpaid_installments.exists():
                continue  # skip fully paid fees

            installment_data = [
                {
                    "installment_id": inst.id,
                    "installment_no": inst.installment_no,
                    "amount": inst.amount,
                    "due_date": inst.due_date,
                }
                for inst in unpaid_installments
            ]

            fees_data.append({
                "fee_id": fee.id,
                "generated_date": fee.generated_date,
                "total_fee": fee.total_fee,
                "balance_amount": fee.balance_amount,
                "installments": installment_data
            })

        return Response({
            "student": {
                "id": student.id,
                "admission_no": student.admission_code,
                "name": student.candidate_name,
                "mobile_no": student.mobile_no
            },
            "fees": fees_data
        }, status=status.HTTP_200_OK)

class GetDepositsByFeeAPIView(APIView):

    def get(self, request, fee_id):

        user = request.user
        branch_id = get_branch_id(request)

        fee = get_object_or_404(
            FeeGeneration,
            id=fee_id,
            # branch_id=branch_id if branch_id else None,
            is_active=True
        )

        # Client Admin case
        if not branch_id:
            branch_id = fee.branch_id

        # -------------------------
        # Fetch Deposits
        # -------------------------
        deposits = FeeDeposit.objects.select_related(
            "installment"
        ).filter(
            installment__fee_generation=fee,
            is_active=True
        ).order_by("-created_at")

        deposits_data = []

        for dep in deposits:
            deposits_data.append({
                "deposit_id": dep.id,
                "installment_no": dep.installment.installment_no,
                "installment_amount": dep.installment.amount,
                "payment_date": dep.payment_date,
                "payment_mode": dep.payment_mode.name,
                "paid_amount": dep.paid_amount,
                "ledger": dep.ledger,
                "reference_no": dep.reference_no,
                "reference_date": dep.reference_date,
                "bank_name": dep.bank_name,
            })

        return Response({
            "fee_id": fee.id,
            "total_fee": fee.total_fee,
            "balance_amount": fee.balance_amount,
            "deposits": deposits_data
        }, status=status.HTTP_200_OK)

class GenerateReceiptAPIView(APIView):

    def get(self, request, deposit_id):

        user = request.user
        branch_id = get_branch_id(request)

        deposit = get_object_or_404(
            FeeDeposit.objects.select_related(
                "installment",
                "installment__fee_generation",
                "installment__fee_generation__admission"
            ),
            id=deposit_id,
            is_active=True,
            installment__fee_generation__branch=branch_id
        )

        installment = deposit.installment
        fee = installment.fee_generation
        student = fee.admission

        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=pagesizes.A4
        )

        elements = []
        styles = getSampleStyleSheet()

        # -------------------------
        # Header
        # -------------------------
        elements.append(Paragraph(f"Receipt No: {deposit.id}", styles["Normal"]))
        elements.append(Paragraph(f"Receipt Date: {deposit.payment_date}", styles["Normal"]))
        elements.append(Spacer(1, 0.2 * inch))

        # -------------------------
        # Student Details
        # -------------------------
        student_data = [
            ["Admission No", student.admission_code],
            ["Student Name", student.candidate_name],
            ["Mobile No", student.mobile_no],
            ["Course(s)", ", ".join(student.courses.values_list("course_name", flat=True))]
        ]

        student_table = Table(student_data, hAlign="LEFT")
        student_table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
        ]))

        elements.append(student_table)
        elements.append(Spacer(1, 0.3 * inch))

        # -------------------------
        # Payment Details
        # -------------------------
        payment_data = [
            ["Installment No", installment.installment_no],
            ["Installment Amount", str(installment.amount)],
            ["Payment Mode", deposit.payment_mode],
            ["Paid Amount", str(deposit.paid_amount)],
            ["Balance Remaining", str(fee.balance_amount)],
        ]

        if deposit.reference_no:
            payment_data.append(["Reference No", deposit.reference_no])

        if deposit.bank_name:
            payment_data.append(["Bank Name", deposit.bank_name])

        payment_table = Table(payment_data, hAlign="LEFT")
        payment_table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
        ]))

        elements.append(payment_table)
        elements.append(Spacer(1, 0.5 * inch))

        elements.append(Paragraph("Thank you for your payment.", styles["Normal"]))

        # -------------------------
        # Build PDF
        # -------------------------
        doc.build(elements)

        buffer.seek(0)

        response = HttpResponse(
            buffer,
            content_type="application/pdf"
        )
        response["Content-Disposition"] = f'attachment; filename="receipt_{deposit.id}.pdf"'

        return response


#Updated

class FeeGenerationInsertUpdateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        user = request.user
        fee_id = request.data.get("id")
        admission_id = request.data.get("admission")
        fee_type = request.data.get("fee_type", "Installment")

        admission = get_object_or_404(Admission, id=admission_id, is_active=True)
        #course = admission.courses.first()

        
        # ====================================
        # FETCH COURSE FROM MAPPING TABLE
        # ====================================

        admission_course = AdmissionCourseBatch.objects.filter(
            admission=admission
        ).select_related("course").first()

        if not admission_course:
            return Response(
                {"error": "No course assigned to this admission"},
                status=400
            )

        course = admission_course.course

        if not course:
            return Response({"error": "No course linked"}, status=400)

        generated_date = datetime.strptime(
            request.data.get("generated_date", str(timezone.now().date())),
            "%Y-%m-%d"
        ).date()

        advance_amount = Decimal(str(request.data.get("advance_amount", 0)))

        # =========================
        # 🔵 MONTHLY LOGIC
        # =========================
        if fee_type == "Monthly":

            monthly_fee = Decimal(str(request.data.get("monthly_fee", 0)))
            months = request.data.get("months", [])

            if not months:
                return Response({"error": "months required"}, status=400)

            installment_count = len(months)
            course_fee = monthly_fee * installment_count

            extra_amount = discount = kit_charges = Decimal("0")
            gst_percentage = gst_amount = Decimal("0")

            billing_before_gst = course_fee
            total_fee = course_fee
            balance_amount = total_fee - advance_amount

        # =========================
        # 🟢 INSTALLMENT LOGIC
        # =========================
        else:
            course_fee = Decimal(str(
                request.data.get("course_fee", course.basic_course_fee)
            ))

            gst_percentage = Decimal(str(
                request.data.get("gst_percentage", course.gst_percentage)
            ))

            extra_amount = Decimal(str(request.data.get("extra_amount", 0)))
            discount = Decimal(str(request.data.get("discount", 0)))
            kit_charges = Decimal(str(request.data.get("kit_charges", 0)))
            installment_count = int(request.data.get("installment_count", 1))

            billing_before_gst = (course_fee + extra_amount) - discount
            gst_amount = (billing_before_gst * gst_percentage) / 100
            total_fee = billing_before_gst + gst_amount + kit_charges
            balance_amount = total_fee - advance_amount

        # =========================
        # CREATE / UPDATE
        # =========================
        fee, created = FeeGeneration.objects.update_or_create(
            id=fee_id,
            defaults={
                "admission": admission,
                "course": course,
                "organization": admission.organization,
                "branch": admission.branch,
                "generated_date": generated_date,
                "fee_type": fee_type,
                "course_fee": course_fee,
                "extra_amount": extra_amount,
                "discount": discount,
                "billing_before_gst": billing_before_gst,
                "gst_percentage": gst_percentage,
                "gst_amount": gst_amount,
                "kit_charges": kit_charges,
                "total_fee": total_fee,
                # ✅ BANK FIELDS
                "ledger": request.data.get("ledger"),
                "reference_no": request.data.get("reference_no"),
                "reference_date": request.data.get("reference_date"),
                "bank_name": request.data.get("bank_name"),

                "advance_amount": advance_amount,
                "balance_amount": balance_amount,
                "installment_count": installment_count,
                "payment_mode_id": request.data.get("payment_mode"),
                "updated_by": user,
            }
        )

        if created:
            fee.created_by = user
            fee.save(update_fields=["created_by"])

        # =========================
        # 🔥 MONTHLY DETAILS SAVE
        # =========================
        if fee_type == "Monthly":
            fee.monthly_details.all().delete()

            for m in request.data.get("months", []):
                FeeMonthlyDetail.objects.create(
                    fee_generation=fee,
                    month=m.get("month"),
                    year=m.get("year"),
                    due_date=m.get("due_date")
                )

        # =========================
        # 🔥 INSTALLMENT CREATION (UNIFIED)
        # =========================
        paid_installments = fee.installments.filter(deposits__isnull=False).distinct()

        total_paid = sum(
            inst.deposits.aggregate(Sum('paid_amount'))['paid_amount__sum'] or 0
            for inst in paid_installments
        )

        remaining = total_fee - total_paid

        # delete unpaid installments
        fee.installments.filter(deposits__isnull=True).delete()

        # ====================================
        # DELETE UNPAID INSTALLMENTS
        # ====================================

        fee.installments.filter(
            deposits__isnull=True
        ).delete()

        # ====================================
        # CREATE INSTALLMENTS FROM PAYLOAD
        # ====================================

        installment_payloads = request.data.get(
            "installments",
            []
        )

        for inst_data in installment_payloads:

            FeeInstallment.objects.create(
                fee_generation=fee,
                installment_no=inst_data.get("installment_no"),
                amount=Decimal(str(inst_data.get("amount"))),
                due_date=inst_data.get("due_date")
            )

        # =========================
        # ADVANCE PAYMENT
        # =========================
        # if created and advance_amount > 0:
        #     first_inst = fee.installments.order_by("installment_no").first()

        #     if first_inst:
        #         FeeDeposit.objects.create(
        #             installment=first_inst,
        #             payment_date=generated_date,
        #             payment_mode_id=request.data.get("payment_mode"),
        #             paid_amount=advance_amount,

        #             # ✅ IMPORTANT
        #             is_active=True,

        #             ledger=request.data.get("ledger"),
        #             reference_no=request.data.get("reference_no"),
        #             reference_date=request.data.get("reference_date"),
        #             bank_name=request.data.get("bank_name")
        #         )

        #         first_inst.total_paid += advance_amount
        #         first_inst.is_paid = first_inst.total_paid >= first_inst.amount
        #         first_inst.save()

        # =========================
        # ADVANCE PAYMENT AUTO ALLOCATION
        # =========================

        if created and advance_amount > 0:

            allocate_payment_to_installments(
                fee_generation=fee,
                amount=advance_amount,
                payment_data={
                    "payment_date": generated_date,
                    "payment_mode": request.data.get("payment_mode"),

                    "ledger": request.data.get("ledger"),
                    "reference_no": request.data.get("reference_no"),
                    "reference_date": request.data.get("reference_date"),
                    "bank_name": request.data.get("bank_name"),
                }
            )






        serializer = FeeGenerationSerializer(fee)

        return Response({
            "message": f"{fee_type} fee generated successfully",
            "data": serializer.data
        })



from rest_framework.generics import ListAPIView
from django.db.models import Q
from datetime import datetime



from django.db.models import Q, Sum
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

class FeeGenerationListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = FeeGeneration.objects.filter(is_active=True).select_related(
            "admission"
        ).prefetch_related(
            "monthly_details",
            "installments__deposits"
        )

        # =========================
        # ORGANIZATION FILTER
        # =========================

        organization_id = request.query_params.get(
            "organization"
        )

        if organization_id:

            queryset = queryset.filter(
                admission__organization_id=organization_id
            )

        # =========================
        # BRANCH FILTER
        # =========================

        branch_id = request.query_params.get(
            "branch"
        )

        if branch_id:

            queryset = queryset.filter(
                admission__branch_id=branch_id
            )

        # =========================
        # 🔍 FILTERS
        # =========================
        search = request.query_params.get("search")
        fee_type = request.query_params.get("fee_type")
        payment_mode = request.query_params.get("payment_mode")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        # ✅ NEW: YEAR FILTER
        from_year = request.query_params.get("from_year")
        to_year = request.query_params.get("to_year")

        if from_year:
            from_year = int(from_year)
        if to_year:
            to_year = int(to_year)

        if from_year and to_year:
            queryset = queryset.filter(
                admission__admission_date__year__gte=from_year,
                admission__admission_date__year__lte=to_year
            )
        elif from_year:
            queryset = queryset.filter(
                admission__admission_date__year__gte=from_year
            )
        elif to_year:
            queryset = queryset.filter(
                admission__admission_date__year__lte=to_year
            )

        # =========================
        # EXISTING FILTERS
        # =========================
        if search:
            queryset = queryset.filter(
                Q(admission__candidate_name__icontains=search) |
                Q(admission__admission_code__icontains=search) |
                Q(admission__mobile_no__icontains=search)
            )

        if fee_type:
            queryset = queryset.filter(fee_type=fee_type)

        if payment_mode:
            queryset = queryset.filter(payment_mode_id=payment_mode)

        if start_date and end_date:
            queryset = queryset.filter(
                generated_date__range=[start_date, end_date]
            )

        queryset = queryset.order_by("-created_at")

        data = []

        for fee in queryset:
            admission = fee.admission

            # =========================
            # 🧮 CALCULATIONS
            # =========================
            total_paid = fee.installments.aggregate(
                total=Sum("deposits__paid_amount")
            )["total"] or 0

            pending_amount = fee.total_fee - total_paid

            # =========================
            # 📅 FINANCIAL YEAR
            # =========================
            year = admission.admission_date.year
            month = admission.admission_date.month

            if month >= 4:
                financial_year = f"{year}-{year + 1}"
            else:
                financial_year = f"{year - 1}-{year}"

            # =========================
            # 🧾 MAIN DATA
            # =========================
            item = {
                "fee_id": fee.id,

                # =========================
                # 🎓 ADMISSION DETAILS
                # =========================
                "admission_no": admission.admission_code,
                "candidate_name": admission.candidate_name,
                "father_name": admission.father_name,
                "email": admission.email,
                "mobile_no": admission.mobile_no,
                "admission_date": admission.admission_date,

                # =========================
                # 📘 COURSE DETAILS
                # =========================
                "course_id": fee.course.id if fee.course else None,
                "course_name": fee.course.course_name if fee.course else None,
                "course_code": fee.course.course_code if fee.course else None,

                # =========================
                # 💰 FEE DETAILS
                # =========================
                "amount": float(fee.total_fee),
                "total_paid": float(total_paid),
                "pending_amount": float(pending_amount),
                "financial_year": financial_year,

                "generated_date": fee.generated_date,
                "fee_type": fee.fee_type,

                "course_fee": float(fee.course_fee),
                "extra_amount": float(fee.extra_amount),
                "discount": float(fee.discount),
                "gst_percentage": float(fee.gst_percentage),
                "gst_amount": float(fee.gst_amount),
                "kit_charges": float(fee.kit_charges),

                "advance_amount": float(fee.advance_amount),
                "balance_amount": float(fee.balance_amount),

                # =========================
                # 🏦 BANK DETAILS
                # =========================
                "payment_mode": fee.payment_mode.name if fee.payment_mode else None,
                "ledger": fee.ledger,
                "reference_no": fee.reference_no,
                "reference_date": fee.reference_date,
                "bank_name": fee.bank_name,
            }

            # =========================
            # 🔵 MONTHLY DETAILS
            # =========================
            if fee.fee_type == "Monthly":
                monthly_records = fee.monthly_details.all()

                item["monthly_details"] = {
                    "months": [
                        {
                            "month": m.month,
                            "year": m.year,
                            "due_date": m.due_date
                        }
                        for m in monthly_records
                    ],
                    "months_count": monthly_records.count(),
                    "monthly_fee": float(
                        fee.course_fee / monthly_records.count()
                    ) if monthly_records.exists() else 0
                }

            # =========================
            # 🟢 INSTALLMENTS
            # =========================
            if fee.fee_type == "Installment":
                installments = fee.installments.all().order_by("installment_no")

                item["installments"] = [
                    {
                        "installment_no": inst.installment_no,
                        "amount": float(inst.amount),
                        "due_date": inst.due_date,
                        "paid_amount": float(
                            inst.deposits.aggregate(
                                total=Sum("paid_amount")
                            )["total"] or 0
                        )
                    }
                    for inst in installments
                ]

            data.append(item)

        return Response(data)


# class FeeGenerationUpdateAPIView(APIView):
#     permission_classes = [IsAuthenticated]

#     @transaction.atomic
#     def put(self, request, fee_id):
#         user = request.user

#         fee = get_object_or_404(
#             FeeGeneration,
#             id=fee_id,
#             is_active=True
#         )

#         admission = fee.admission
#         course = fee.course

#         if not course:
#             return Response({"error": "Course not linked"}, status=400)

#         fee_type = request.data.get("fee_type", fee.fee_type)

#         # COMMON INPUTS
#         extra_amount = Decimal(str(request.data.get("extra_amount", fee.extra_amount)))
#         discount = Decimal(str(request.data.get("discount", fee.discount)))
#         kit_charges = Decimal(str(request.data.get("kit_charges", fee.kit_charges)))
#         advance_amount = Decimal(str(request.data.get("advance_amount", fee.advance_amount)))

#         generated_date_str = request.data.get("generated_date", str(fee.generated_date))
#         generated_date = datetime.strptime(generated_date_str, "%Y-%m-%d").date()

#         # =========================
#         # 🔵 MONTHLY LOGIC (FIXED)
#         # =========================
#         if fee_type == "Monthly":
#             monthly_fee = Decimal(str(request.data.get("monthly_fee", fee.course_fee)))
#             months = request.data.get("months", [])

#             if not months or not isinstance(months, list):
#                 return Response({"error": "Valid months list required"}, status=400)

#             months_count = len(months)

#             billing_before_gst = monthly_fee * months_count

#             # If you truly want no GST for monthly → keep 0
#             gst_percentage = Decimal("0")
#             gst_amount = Decimal("0")

#             total_fee = billing_before_gst
#             balance_amount = total_fee - advance_amount

#             installment_count = months_count

#         # =========================
#         # 🟢 INSTALLMENT LOGIC
#         # =========================
#         else:
#             course_fee = Decimal(str(request.data.get("course_fee", fee.course_fee)))
#             gst_percentage = Decimal(str(course.gst_percentage))

#             installment_count = int(
#                 request.data.get("installment_count", fee.installment_count or 1)
#             )

#             billing_before_gst = (course_fee + extra_amount) - discount
#             gst_amount = (billing_before_gst * gst_percentage) / 100

#             total_fee = billing_before_gst + gst_amount + kit_charges
#             balance_amount = total_fee - advance_amount

#         # =========================
#         # UPDATE MAIN RECORD
#         # =========================
#         fee.generated_date = generated_date
#         fee.fee_type = fee_type
#         fee.course_fee = monthly_fee if fee_type == "Monthly" else course_fee
#         fee.extra_amount = extra_amount
#         fee.discount = discount
#         fee.billing_before_gst = billing_before_gst
#         fee.gst_percentage = gst_percentage
#         fee.gst_amount = gst_amount
#         fee.kit_charges = kit_charges
#         fee.total_fee = total_fee
#         fee.advance_amount = advance_amount
#         fee.balance_amount = balance_amount
#         fee.installment_count = installment_count
#         fee.payment_mode_id = request.data.get("payment_mode", fee.payment_mode_id)
#         fee.ledger = request.data.get("ledger", fee.ledger)
#         fee.reference_no = request.data.get("reference_no", fee.reference_no)
#         fee.reference_date = request.data.get("reference_date", fee.reference_date)
#         fee.bank_name = request.data.get("bank_name", fee.bank_name)
#         fee.updated_by = user

#         fee.save()

#         # =========================
#         # 🔥 MONTHLY DETAILS UPDATE (MISSING BEFORE)
#         # =========================
#         if fee_type == "Monthly":

#             # 🚨 Prevent editing if payments exist (future safe)
#             has_payments = fee.installments.filter(deposits__isnull=False).exists()
#             if has_payments:
#                 return Response({
#                     "error": "Cannot modify monthly structure after payments"
#                 }, status=400)

#             # if has_payments:

#             #     # prevent changing months count
#             #     existing_months = fee.monthly_details.count()
#             #     new_months = len(months)

#             #     if existing_months != new_months:
#             #         return Response({
#             #             "error": "Cannot change months count after payments"
#             #         }, status=400)

#             # Reset months
#             fee.monthly_details.all().delete()

#             for m in months:
#                 FeeMonthlyDetail.objects.create(
#                     fee_generation=fee,
#                     month=m.get("month"),
#                     year=m.get("year"),
#                     due_date=m.get("due_date")
#                 )

#             # ❗ IMPORTANT: Remove installments if switching from installment → monthly
#             fee.installments.all().delete()

#         # =========================
#         # 🟢 INSTALLMENT RE-GENERATION
#         # =========================
#         if fee_type == "Installment":

#             paid_installments = fee.installments.filter(deposits__isnull=False).distinct()

#             total_paid = sum(
#                 inst.deposits.aggregate(Sum('paid_amount'))['paid_amount__sum'] or 0
#                 for inst in paid_installments
#             )

#             remaining_to_distribute = total_fee - total_paid

#             # delete unpaid installments
#             fee.installments.filter(deposits__isnull=True).delete()

#             current_paid_count = paid_installments.count()
#             new_needed = installment_count - current_paid_count

#             if new_needed > 0:
#                 inst_amt = (remaining_to_distribute / new_needed).quantize(
#                     Decimal("0.01"),
#                     rounding=ROUND_HALF_UP
#                 )

#                 installment_payloads = request.data.get("installments", [])

#                 for inst_data in installment_payloads:

#                     FeeInstallment.objects.create(
#                         fee_generation=fee,
#                         installment_no=inst_data.get("installment_no"),
#                         amount=Decimal(str(inst_data.get("amount"))),
#                         due_date=inst_data.get("due_date")
#                     )

#             # ❗ IMPORTANT: Remove monthly data if switching → installment
#             fee.monthly_details.all().delete()

#         return Response({
#             "message": "Fee updated successfully",
#             "fee_id": fee.id,
#             "fee_type": fee.fee_type,
#             "total_fee": float(total_fee),
#             "balance_due": float(balance_amount),
#             "installments": fee.installments.count() if fee_type == "Installment" else 0,
#             "months_count": fee.monthly_details.count() if fee_type == "Monthly" else 0
#         })


class FeeGenerationUpdateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def put(self, request, fee_id):

        user = request.user

        fee = get_object_or_404(
            FeeGeneration,
            id=fee_id,
            is_active=True
        )

        admission = fee.admission
        course = fee.course

        if not course:
            return Response(
                {"error": "Course not linked"},
                status=400
            )

        fee_type = request.data.get(
            "fee_type",
            fee.fee_type
        )

        # ==========================================
        # COMMON INPUTS
        # ==========================================

        extra_amount = Decimal(
            str(
                request.data.get(
                    "extra_amount",
                    fee.extra_amount
                )
            )
        )

        discount = Decimal(
            str(
                request.data.get(
                    "discount",
                    fee.discount
                )
            )
        )

        kit_charges = Decimal(
            str(
                request.data.get(
                    "kit_charges",
                    fee.kit_charges
                )
            )
        )

        advance_amount = Decimal(
            str(
                request.data.get(
                    "advance_amount",
                    fee.advance_amount
                )
            )
        )

        generated_date_str = request.data.get(
            "generated_date",
            str(fee.generated_date)
        )

        generated_date = datetime.strptime(
            generated_date_str,
            "%Y-%m-%d"
        ).date()

        # ==========================================
        # MONTHLY LOGIC
        # ==========================================

        if fee_type == "Monthly":

            monthly_fee = Decimal(
                str(
                    request.data.get(
                        "monthly_fee",
                        fee.course_fee
                    )
                )
            )

            months = request.data.get("months", [])

            if not months:
                return Response(
                    {"error": "Months required"},
                    status=400
                )

            months_count = len(months)

            billing_before_gst = (
                monthly_fee * months_count
            )

            gst_percentage = Decimal("0")
            gst_amount = Decimal("0")

            total_fee = billing_before_gst

            balance_amount = (
                total_fee - advance_amount
            )

            installment_count = months_count

        # ==========================================
        # INSTALLMENT LOGIC
        # ==========================================

        else:

            course_fee = Decimal(
                str(
                    request.data.get(
                        "course_fee",
                        fee.course_fee
                    )
                )
            )

            gst_percentage = Decimal(
                str(
                    request.data.get(
                        "gst_percentage",
                        course.gst_percentage
                    )
                )
            )

            installment_count = int(
                request.data.get(
                    "installment_count",
                    fee.installment_count or 1
                )
            )

            billing_before_gst = (
                (course_fee + extra_amount)
                - discount
            )

            gst_amount = (
                billing_before_gst
                * gst_percentage
            ) / 100

            total_fee = (
                billing_before_gst
                + gst_amount
                + kit_charges
            )

            balance_amount = (
                total_fee - advance_amount
            )

        # ==========================================
        # UPDATE MAIN RECORD
        # ==========================================

        fee.generated_date = generated_date
        fee.fee_type = fee_type

        fee.course_fee = (
            monthly_fee
            if fee_type == "Monthly"
            else course_fee
        )

        fee.extra_amount = extra_amount
        fee.discount = discount

        fee.billing_before_gst = (
            billing_before_gst
        )

        fee.gst_percentage = gst_percentage
        fee.gst_amount = gst_amount
        fee.kit_charges = kit_charges

        fee.total_fee = total_fee

        fee.advance_amount = advance_amount
        fee.balance_amount = balance_amount

        fee.installment_count = installment_count

        fee.payment_mode_id = request.data.get(
            "payment_mode",
            fee.payment_mode_id
        )

        fee.ledger = request.data.get(
            "ledger",
            fee.ledger
        )

        fee.reference_no = request.data.get(
            "reference_no",
            fee.reference_no
        )

        fee.reference_date = request.data.get(
            "reference_date",
            fee.reference_date
        )

        fee.bank_name = request.data.get(
            "bank_name",
            fee.bank_name
        )

        fee.updated_by = user

        fee.save()

        # ==========================================
        # MONTHLY UPDATE
        # ==========================================

        if fee_type == "Monthly":

            has_payments = fee.installments.filter(
                deposits__isnull=False
            ).exists()

            if has_payments:
                return Response({
                    "error": (
                        "Cannot modify monthly "
                        "structure after payments"
                    )
                }, status=400)

            fee.monthly_details.all().delete()

            for m in months:

                FeeMonthlyDetail.objects.create(
                    fee_generation=fee,
                    month=m.get("month"),
                    year=m.get("year"),
                    due_date=m.get("due_date")
                )

            fee.installments.all().delete()

        # ==========================================
        # INSTALLMENT UPDATE LOGIC
        # ==========================================

        if fee_type == "Installment":

            installment_payloads = request.data.get(
                "installments",
                []
            )

            if not installment_payloads:

                return Response(
                    {
                        "error":
                        "Installments required"
                    },
                    status=400
                )

            # ======================================
            # EXISTING INSTALLMENTS
            # ======================================

            existing_installments = {
                inst.installment_no: inst
                for inst in fee.installments.all()
            }

            payload_numbers = []

            # ======================================
            # UPDATE / CREATE INSTALLMENTS
            # ======================================

            for inst_data in installment_payloads:

                installment_no = inst_data.get(
                    "installment_no"
                )

                amount = Decimal(
                    str(inst_data.get("amount"))
                )

                due_date = inst_data.get(
                    "due_date"
                )

                payload_numbers.append(
                    installment_no
                )

                # ==================================
                # UPDATE EXISTING
                # ==================================

                if installment_no in existing_installments:

                    inst = existing_installments[
                        installment_no
                    ]

                    already_paid = Decimal(
                        str(inst.total_paid or 0)
                    )

                    # ==============================
                    # VALIDATION
                    # ==============================

                    if amount < already_paid:

                        return Response({
                            "error":
                            (
                                f"Installment "
                                f"{installment_no} "
                                f"amount cannot "
                                f"be less than "
                                f"already paid "
                                f"amount "
                                f"{already_paid}"
                            )
                        }, status=400)

                    inst.amount = amount
                    inst.due_date = due_date

                    inst.is_paid = (
                        already_paid >= amount
                    )

                    inst.save()

                # ==================================
                # CREATE NEW INSTALLMENT
                # ==================================

                else:

                    FeeInstallment.objects.create(
                        fee_generation=fee,
                        installment_no=installment_no,
                        amount=amount,
                        due_date=due_date
                    )

            # ======================================
            # DELETE REMOVED UNPAID INSTALLMENTS
            # ======================================

            for inst_no, inst in existing_installments.items():

                if inst_no not in payload_numbers:

                    already_paid = Decimal(
                        str(inst.total_paid or 0)
                    )

                    if already_paid > 0:

                        return Response({
                            "error":
                            (
                                f"Cannot delete "
                                f"installment "
                                f"{inst_no} "
                                f"because payment "
                                f"exists"
                            )
                        }, status=400)

                    inst.delete()

            # ======================================
            # VALIDATE TOTAL
            # ======================================

            latest_total = fee.installments.aggregate(
                total=Sum("amount")
            )["total"] or Decimal("0")

            if latest_total != total_fee:

                return Response({
                    "error":
                    (
                        f"Installment total "
                        f"{latest_total} "
                        f"does not match "
                        f"fee total "
                        f"{total_fee}"
                    )
                }, status=400)

            # ======================================
            # REMOVE MONTHLY DATA
            # ======================================

            fee.monthly_details.all().delete()

        # ==========================================
        # FINAL RESPONSE
        # ==========================================

        serializer = FeeGenerationSerializer(fee)

        return Response({
            "message": "Fee updated successfully",
            "data": serializer.data
        })


class FeeGenerationDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def delete(self, request, fee_id):
        user = request.user

        try:
            fee = FeeGeneration.objects.get(id=fee_id, is_active=True)
        except FeeGeneration.DoesNotExist:
            return Response({"error": "Fee not found"}, status=404)

        # 🚨 Check payments (Installment)
        has_installment_payments = fee.installments.filter(
            deposits__isnull=False
        ).exists()

        if has_installment_payments:
            return Response({
                "error": "Cannot delete fee. Payments already recorded."
            }, status=400)

        # 🔥 (Future-safe) Monthly payments check placeholder
        # if fee.monthly_payments.exists():  # if you add later
        #     return Response({"error": "Monthly payments exist"}, status=400)

        # ✅ Delete related data FIRST
        fee.installments.all().delete()
        fee.monthly_details.all().delete()   # 🔥 NEW FIX

        # ✅ Soft delete main fee
        fee.is_active = False
        fee.updated_by = user
        fee.save()

        return Response({
            "message": "Fee deleted successfully",
            "fee_id": fee_id
        }, status=200)




class BulkFeeDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def delete(self, request):
        user = request.user
        ids = request.data.get("fee_ids", [])

        if not ids:
            return Response({"error": "fee_ids required"}, status=400)

        results = []

        fees = FeeGeneration.objects.filter(id__in=ids, is_active=True)

        fee_map = {fee.id: fee for fee in fees}

        for fee_id in ids:
            fee = fee_map.get(fee_id)

            if not fee:
                results.append({
                    "fee_id": fee_id,
                    "deleted": False,
                    "error": "not found"
                })
                continue

            # 🚨 Check payments
            has_payments = fee.installments.filter(
                deposits__isnull=False
            ).exists()

            if has_payments:
                results.append({
                    "fee_id": fee_id,
                    "deleted": False,
                    "error": "has payments"
                })
                continue

            # ✅ Delete related data
            fee.installments.all().delete()
            fee.monthly_details.all().delete()   # 🔥 NEW FIX

            # ✅ Soft delete
            fee.is_active = False
            fee.updated_by = user
            fee.save()

            results.append({
                "fee_id": fee_id,
                "deleted": True
            })

        return Response({
            "message": "Bulk delete processed",
            "results": results
        })


class FeeGenerationInstallmentsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, fee_id):
        branch_id = get_branch_id(request)

        fee = get_object_or_404(
            FeeGeneration.objects.select_related("admission"),
            id=fee_id,
            is_active=True
        )

        if branch_id and fee.branch_id != int(branch_id):
            return Response({"error": "Unauthorized branch access"}, status=403)

        installments = FeeInstallment.objects.filter(
            fee_generation=fee,
            is_active=True
        ).order_by("installment_no")

        data = []

        for inst in installments:

            # ✅ FIXED HERE
            total_paid = inst.deposits.filter(
                is_active=True
            ).aggregate(
                total=Sum("paid_amount")
            )["total"] or 0

            remaining = inst.amount - total_paid

            data.append({
                "installment_id": inst.id,
                "installment_no": inst.installment_no,
                "due_date": inst.due_date,

                "amount": float(inst.amount),
                "total_paid": float(total_paid),

                # safety: avoid negative UI confusion
                "remaining_amount": float(max(remaining, 0)),

                "is_paid": total_paid >= inst.amount
            })

        return Response({
            "fee_id": fee.id,

            # ADMISSION DETAILS
            "admission_no": fee.admission.admission_code,
            "candidate_name": fee.admission.candidate_name,
            "father_name": fee.admission.father_name,
            "email": fee.admission.email,
            "mobile_no": fee.admission.mobile_no,
            "admission_date": fee.admission.admission_date,

            # COURSE DETAILS
            "course_id": fee.course.id if fee.course else None,
            "course_name": fee.course.course_name if fee.course else None,

            # FEE DETAILS
            "fee_type": fee.fee_type,
            "generated_date": fee.generated_date,

            "total_fee": float(fee.total_fee),
            "balance_amount": float(fee.balance_amount),

            # BANK DETAILS
            "payment_mode": fee.payment_mode.name if fee.payment_mode else None,
            "ledger": fee.ledger,
            "reference_no": fee.reference_no,
            "reference_date": fee.reference_date,
            "bank_name": fee.bank_name,

            # INSTALLMENTS
            "installments": data

        }, status=200)



class FeeGenerationInstallmentWithDepositsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, fee_id):
        branch_id = get_branch_id(request)

        fee = get_object_or_404(
            FeeGeneration.objects.select_related("admission"),
            id=fee_id,
            is_active=True
        )

        # 🔐 Branch check
        if branch_id and fee.branch_id != int(branch_id):
            return Response({"error": "Unauthorized"}, status=403)



        # =========================
        # INSTALLMENTS
        # =========================

        installments = FeeInstallment.objects.filter(
            fee_generation=fee,
            is_active=True
        ).order_by("installment_no")

        response_data = []

        for inst in installments:

            # ✅ ONLY ACTIVE DEPOSITS
            deposits = inst.deposits.filter(is_active=True)

            total_paid = deposits.aggregate(
                total=Sum("paid_amount")
            )["total"] or Decimal("0")

            deposit_list = [
                {
                    "deposit_id": d.id,
                    "paid_amount": float(d.paid_amount),

                    "payment_date": d.payment_date,

                    "payment_mode": (
                        d.payment_mode.name
                        if d.payment_mode else None
                    ),

                    # BANK DETAILS
                    "ledger": d.ledger,
                    "reference_no": d.reference_no,
                    "reference_date": d.reference_date,
                    "bank_name": d.bank_name,

                }
                for d in deposits
            ]

            response_data.append({
                "installment_id": inst.id,
                "installment_no": inst.installment_no,
                "due_date": inst.due_date,

                "amount": float(inst.amount),
                "total_paid": float(total_paid),
                "remaining_amount": float(inst.amount - total_paid),
                "is_paid": total_paid >= inst.amount,

                "deposits": deposit_list   # 🔥 THIS IS WHAT YOU WANT
            })

        # ✅ Correct total paid at fee level
        total_paid_fee = FeeDeposit.objects.filter(
            installment__fee_generation=fee,
            is_active=True
        ).aggregate(total=Sum("paid_amount"))["total"] or Decimal("0")

        return Response({
            "fee_id": fee.id,
            "candidate_name": fee.admission.candidate_name,
            "fee_type": fee.fee_type,

            "total_fee": float(fee.total_fee),
            "total_paid": float(total_paid_fee),
            "balance_amount": float(fee.total_fee - total_paid_fee),

            "installments": response_data
        }, status=200)





class RecentPaymentsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        branch_id = get_branch_id(request)
        limit = int(request.query_params.get("limit", 10))

        # Fetch recent active deposits
        queryset = FeeDeposit.objects.select_related(
            "installment__fee_generation__admission",
            "payment_mode"
        ).filter(is_active=True)

        if branch_id:
            queryset = queryset.filter(installment__fee_generation__branch_id=branch_id)

        recent_deposits = queryset.order_by("-created_at")[:limit]

        data = []
        for dep in recent_deposits:
            data.append({
                "id": dep.id,
                "student_name": dep.installment.fee_generation.admission.candidate_name,
                "admission_no": dep.installment.fee_generation.admission.admission_code,
                "amount": dep.paid_amount,
                "date": dep.payment_date,
                "mode": dep.payment_mode.name if dep.payment_mode else "N/A",
                "installment_no": dep.installment.installment_no
            })

        return Response(data, status=200)


from django.db.models import Count, Q

class AdmissionsWithoutFeeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            # 🔍 Base queryset
            queryset = Admission.objects.filter(is_active=True)

            # ✅ Annotate fee count
            queryset = queryset.annotate(
                fee_count=Count("fee_generations", filter=Q(fee_generations__is_active=True))
            ).filter(fee_count=0)

            # =========================
            # ORGANIZATION FILTER
            # =========================

            organization_id = request.query_params.get(
                "organization"
            )

            if organization_id:

                queryset = queryset.filter(
                    organization_id=organization_id
                )

            # =========================
            # BRANCH FILTER
            # =========================

            branch_id = request.query_params.get(
                "branch"
            )

            if branch_id:

                queryset = queryset.filter(
                    branch_id=branch_id
                )

            # =========================
            # ✅ YEAR FILTER (NEW)
            # =========================
            from_year = request.query_params.get("from_year")
            to_year = request.query_params.get("to_year")

            if from_year and to_year:
                queryset = queryset.filter(
                    admission_date__year__gte=from_year,
                    admission_date__year__lte=to_year
                )

            elif from_year:
                queryset = queryset.filter(
                    admission_date__year__gte=from_year
                )

            elif to_year:
                queryset = queryset.filter(
                    admission_date__year__lte=to_year
                )




            # 🔍 Optional search
            search = request.query_params.get("search")
            if search:
                queryset = queryset.filter(
                    Q(candidate_name__icontains=search) |
                    Q(admission_code__icontains=search) |
                    Q(mobile_no__icontains=search)
                )

            serializer = AdmissionSerializer(queryset, many=True)
            return Response(serializer.data)

        except Exception as e:
            return Response({"error": str(e)}, status=500)

from django.db.models import Count, Q

class AdmissionsWithFeeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            queryset = Admission.objects.filter(
                is_active=True
            )

            queryset = queryset.annotate(
                fee_count=Count(
                    "fee_generations",
                    filter=Q(
                        fee_generations__is_active=True
                    )
                )
            ).filter(
                fee_count__gt=0
            )

            # =========================
            # ORGANIZATION FILTER
            # =========================

            organization_id = request.query_params.get(
                "organization"
            )

            if organization_id:

                queryset = queryset.filter(
                    organization_id=organization_id
                )

            # =========================
            # BRANCH FILTER
            # =========================

            branch_id = request.query_params.get(
                "branch"
            )

            if branch_id:

                queryset = queryset.filter(
                    branch_id=branch_id
                )

            # 🔍 Optional search
            search = request.query_params.get("search")
            if search:
                queryset = queryset.filter(
                    Q(candidate_name__icontains=search) |
                    Q(admission_code__icontains=search) |
                    Q(mobile_no__icontains=search)
                )

            serializer = AdmissionSerializer(queryset, many=True)
            return Response(serializer.data)

        except Exception as e:
            return Response({"error": str(e)}, status=500)

from datetime import timedelta

from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from fee_details.models import FeeDeposit
from django.db.models import DecimalField, Value
from django.db.models.functions import Coalesce


class FeeDepositDashboardCountAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        organization_id = request.query_params.get(
            "organization_id"
        )

        branch_id = request.query_params.get(
            "branch_id"
        )

        queryset = FeeDeposit.objects.filter(
            is_active=True
        )

        # =====================================
        # ORGANIZATION FILTER
        # =====================================

        if organization_id:

            queryset = queryset.filter(
                installment__fee_generation__organization_id=
                organization_id
            )

        # =====================================
        # BRANCH FILTER
        # =====================================

        if branch_id:

            queryset = queryset.filter(
                installment__fee_generation__branch_id=
                branch_id
            )

        # =====================================
        # DATES
        # =====================================

        today = timezone.localdate()

        days_from_sunday = (
            today.weekday() + 1
        ) % 7

        week_start = today - timedelta(
            days=days_from_sunday
        )

        week_end = week_start + timedelta(
            days=6
        )

        month_start = today.replace(
            day=1
        )

        # =====================================
        # COUNTS
        # =====================================

        total_count = queryset.count()

        today_count = queryset.filter(
            created_at__date=today
        ).count()

        week_count = queryset.filter(
            created_at__date__range=[
                week_start,
                week_end
            ]
        ).count()

        month_count = queryset.filter(
            created_at__date__gte=month_start
        ).count()

        # =====================================
        # AMOUNTS
        # =====================================

        total_amount = (
            queryset.aggregate(
                total=Sum("paid_amount")
            )["total"] or 0
        )

        today_amount = (
            queryset.filter(
                created_at__date=today
            ).aggregate(
                total=Sum("paid_amount")
            )["total"] or 0
        )

        week_amount = (
            queryset.filter(
                created_at__date__range=[
                    week_start,
                    week_end
                ]
            ).aggregate(
                total=Sum("paid_amount")
            )["total"] or 0
        )

        month_amount = (
            queryset.filter(
                created_at__date__gte=month_start
            ).aggregate(
                total=Sum("paid_amount")
            )["total"] or 0
        )

        return Response({

            "success": True,

            "filters": {

                "organization_id":
                    organization_id,

                "branch_id":
                    branch_id
            },

            "deposit_counts": {

                "total_deposits":
                    total_count,

                "today_deposits":
                    today_count,

                "week_deposits":
                    week_count,

                "month_deposits":
                    month_count
            },

            "collection_amounts": {

                "total_collection":
                    total_amount,

                "today_collection":
                    today_amount,

                "week_collection":
                    week_amount,

                "month_collection":
                    month_amount
            },

            "date_range": {

                "today":
                    today,

                "week_start":
                    week_start,

                "week_end":
                    week_end,

                "month_start":
                    month_start
            }
        })



from datetime import timedelta

from django.db.models import (
    F,
    Sum,
    DecimalField,
    ExpressionWrapper
)

from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


class DueDashboardCountAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        organization_id = request.query_params.get(
            "organization"
        )

        branch_id = request.query_params.get(
            "branch"
        )

        queryset = FeeInstallment.objects.select_related(
            "fee_generation",
            "fee_generation__admission"
        ).filter(
            is_active=True,
            is_paid=False,
            fee_generation__is_active=True
        )

        # =====================================
        # ORGANIZATION FILTER
        # =====================================

        if organization_id:

            queryset = queryset.filter(
                fee_generation__admission__organization_id=
                organization_id
            )

        # =====================================
        # BRANCH FILTER
        # =====================================

        if branch_id:

            queryset = queryset.filter(
                fee_generation__admission__branch_id=
                branch_id
            )

        # =====================================
        # DUE AMOUNT CALCULATION
        # =====================================

        queryset = queryset.annotate(

            due_amount=ExpressionWrapper(

                F("amount") - F("total_paid"),

                output_field=DecimalField(
                    max_digits=18,
                    decimal_places=2
                )
            )
        )

        # =====================================
        # DATES
        # =====================================

        today = timezone.localdate()

        days_from_sunday = (
            today.weekday() + 1
        ) % 7

        week_start = today - timedelta(
            days=days_from_sunday
        )

        week_end = week_start + timedelta(
            days=6
        )

        month_start = today.replace(
            day=1
        )

        # =====================================
        # COUNTS
        # =====================================

        total_count = queryset.count()

        today_count = queryset.filter(
            due_date=today
        ).count()

        week_count = queryset.filter(
            due_date__range=[
                week_start,
                week_end
            ]
        ).count()

        month_count = queryset.filter(
            due_date__month=today.month,
            due_date__year=today.year
        ).count()

        # =====================================
        # AMOUNTS
        # =====================================

        total_due_amount = (

            queryset.aggregate(

                total=Sum(
                    "due_amount"
                )

            )["total"]

            or 0
        )

        today_due_amount = (

            queryset.filter(
                due_date=today
            ).aggregate(

                total=Sum(
                    "due_amount"
                )

            )["total"]

            or 0
        )

        week_due_amount = (

            queryset.filter(

                due_date__range=[
                    week_start,
                    week_end
                ]

            ).aggregate(

                total=Sum(
                    "due_amount"
                )

            )["total"]

            or 0
        )

        month_due_amount = (

            queryset.filter(

                due_date__month=today.month,
                due_date__year=today.year

            ).aggregate(

                total=Sum(
                    "due_amount"
                )

            )["total"]

            or 0
        )

        # =====================================
        # UPCOMING WEEK DUES
        # =====================================

        upcoming_week_due_amount = (

            queryset.filter(

                due_date__gt=today,
                due_date__lte=week_end

            ).aggregate(

                total=Sum(
                    "due_amount"
                )

            )["total"]

            or 0
        )

        upcoming_week_due_count = queryset.filter(

            due_date__gt=today,
            due_date__lte=week_end

        ).count()


        # =====================================
        # UPCOMING MONTH DUES
        # =====================================

        next_month_start = (
            month_start + timedelta(days=32)
        ).replace(day=1)

        next_month_end = (
            next_month_start + timedelta(days=32)
        ).replace(day=1) - timedelta(days=1)

        upcoming_month_due_amount = (

            queryset.filter(

                due_date__gte=next_month_start,
                due_date__lte=next_month_end

            ).aggregate(

                total=Sum(
                    "due_amount"
                )

            )["total"]

            or 0
        )

        upcoming_month_due_count = queryset.filter(

            due_date__gte=next_month_start,
            due_date__lte=next_month_end

        ).count()

        # =====================================
        # RESPONSE
        # =====================================

        return Response({

            "success": True,

            "filters": {

                "organization_id":
                    organization_id,

                "branch_id":
                    branch_id
            },

            "due_counts": {

                "total_dues":
                    total_count,

                "today_dues":
                    today_count,

                "week_dues":
                    week_count,

                "month_dues":
                    month_count,

                "upcoming_week_dues":
                    upcoming_week_due_count,

                "upcoming_month_dues":
                    upcoming_month_due_count
            },

            "due_amounts": {

                "total_due_amount":
                    total_due_amount,

                "today_due_amount":
                    today_due_amount,

                "week_due_amount":
                    week_due_amount,

                "month_due_amount":
                    month_due_amount,

                "upcoming_week_due_amount":
                    upcoming_week_due_amount,

                "upcoming_month_due_amount":
                    upcoming_month_due_amount
            },

            "date_range": {

                "today":
                    today,

                "week_start":
                    week_start,

                "week_end":
                    week_end,

                "month_start":
                    month_start
            }
        })