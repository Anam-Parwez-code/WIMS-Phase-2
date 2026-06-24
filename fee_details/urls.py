from django.urls import path
from .views import *

urlpatterns = [


    # -------------------------
    # FEE GENERATION
    # -------------------------
    path("fee-generation/insert-update/", FeeGenerationInsertUpdateAPIView.as_view(), name="fee-generation-insert-update"),
    path("fee-generation/list/", FeeGenerationListAPIView.as_view(), name="fee-generation-list"),
    # GET /api/fee-generation/list/?search=arya
    # GET /api/fee-generation/list/?fee_type=Monthly
    # GET /api/fee-generation/list/?start_date=2026-04-01&end_date=2026-04-30
    # GET /api/fee-generation/list/?payment_mode=1

    path("fee-generation/update/<int:fee_id>/", FeeGenerationUpdateAPIView.as_view()),
    path("fee-generation/delete/<int:fee_id>/", FeeGenerationDeleteAPIView.as_view()),
    path("fee-generation/delete-bulk/", BulkFeeDeleteAPIView.as_view(), name="fee-delete-bulk"),

    path("admissions/no-fee-generation/",AdmissionsWithoutFeeAPIView.as_view(),name="admissions-no-fee"),
    path("admissions/with-fee-generation/",AdmissionsWithFeeAPIView.as_view(),name="admissions-with-fee"),
    path("fee-generation/<int:fee_id>/installments/",FeeGenerationInstallmentsAPIView.as_view()),
    # 🔥 NEW (Installments + Deposits)
    path("fee-generation/<int:fee_id>/installments-with-deposits/",FeeGenerationInstallmentWithDepositsAPIView.as_view(),name="fee-generation-installments-with-deposits"),
    
    
    # -------------------------
    # DUES LIST
    # -------------------------
    path("payment/dues/", DuesListAPIView.as_view(),name="dues-list"),
    path("payment/dues/export/",DuesExportAPIView.as_view(),name="dues-export"),
    #GET /api/payment/dues/?organization=1&branch=7&mode=dues
    #GET /api/payment/dues/?organization=1&branch=7&mode=search&search=john
    #GET /api/payment/dues/export/?organization=1&mode=datewise&start_date=2026-01-01&end_date=2026-12-31

    # -------------------------
    # FEE DEPOSIT
    # -------------------------
    path("fee-deposit/insert-update/",FeeDepositInsertUpdateAPIView.as_view(),name="fee-deposit-insert-update"),
    path("fee-deposit/delete/<int:deposit_id>/",FeeDepositDeleteAPIView.as_view(),name="fee-deposit-delete"),
    path("fee-deposit/get-by-student/<int:student_id>/",GetDepositsByStudentAPIView.as_view(),name="fee-deposit-get-by-student"),
    path("fee-deposit/get-deposits/<int:fee_id>/",GetDepositsByFeeAPIView.as_view(),name="fee-deposit-get-by-fee"),
    path("fee-deposit/generate-receipt/<int:deposit_id>/",GenerateReceiptAPIView.as_view(),name="generate-receipt"),
    path("recent-payments/", RecentPaymentsAPIView.as_view(), name='recent_payments'),
    path("fee-deposit/",FeeDepositInsertUpdateAPIView.as_view(),name="fee-deposit"),    #Filters
    # 🔥 PUT (UPDATE)
    path("fee-deposit/<int:deposit_id>/",FeeDepositUpdateAPIView.as_view(),name="fee-deposit-update"),
    path("fee-deposit/dashboard-count/",FeeDepositDashboardCountAPIView.as_view(),name="fee-deposit-dashboard-count"),
    path("due-dashboard-count/",DueDashboardCountAPIView.as_view(),name="due-dashboard-count"),
]
