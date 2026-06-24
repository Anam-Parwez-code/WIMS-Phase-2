from fee_details.models import FeeDeposit

class FeeDepositReportAPIView(APIView):
    def post(self, request):
        data = request.data
        from_date = data.get('fromDate')
        to_date = data.get('toDate')
        adm_no = data.get('admissionNo')

        # Filter through relationship chain
        queryset = FeeDeposit.objects.filter(
            payment_date__range=[from_date, to_date],
            is_active=True
        ).select_related('installment__fee_generation__candidate')

        if adm_no:
            queryset = queryset.filter(installment__fee_generation__candidate__admission_code=adm_no)

        table_data = [["#", "Admission No", "Student Name", "Date", "Mode", "Amount Paid"]]
        for i, dep in enumerate(queryset, 1):
            adm = dep.installment.fee_generation.candidate
            table_data.append([
                i,
                adm.admission_code,
                adm.candidate_name,
                dep.payment_date.strftime('%d/%m/%Y'),
                dep.payment_mode,
                f"₹{dep.paid_amount:,.2f}"
            ])

        # PDF Logic... (Same as Admission example)