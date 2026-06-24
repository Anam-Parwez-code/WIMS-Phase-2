from rest_framework.views import APIView
from django.http import HttpResponse
from admission.models import Admission
from master.models import Organization
from ..utils.pdf_base import BaseReportPDF

class GenerateAdmissionReportAPIView(APIView):
    def post(self, request):
        data = request.data
        admission_no = data.get('admissionNo')
        from_date = data.get('fromDate')
        to_date = data.get('toDate')

        # 1. Fetch Data
        queryset = Admission.objects.filter(
            admission_date__range=[from_date, to_date],
            is_active=True
        )
        
        if admission_no:
            queryset = queryset.filter(admission_code=admission_no)

        # 2. Prepare Table Data
        table_data = [["Admission No", "Student Name", "Mobile", "Email", "Date", "Course"]]
        for adm in queryset:
            course_names = ", ".join([c.course_name for c in adm.courses.all()])
            table_data.append([
                adm.admission_code,
                adm.candidate_name,
                adm.mobile_no,
                adm.email or "-",
                adm.admission_date.strftime('%d/%m/%Y'),
                course_names
            ])

        # 3. Generate PDF
        # Branch/Org info usually comes from the first record or logged-in user context
        branch_name = request.user.organization.name if hasattr(request.user, 'organization') else "Main Branch"
        date_str = f"From {from_date} To {to_date}"
        
        pdf_gen = BaseReportPDF("Admission Report", branch_name, date_str)
        pdf_gen.build_table(table_data)
        pdf_content = pdf_gen.get_pdf()

        # 4. Return as Download
        response = HttpResponse(content_type='application/pdf')
        filename = f"AdmissionReport_{from_date}_{to_date}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response.write(pdf_content)
        return response