from django.shortcuts import render
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import generics
from rest_framework import status
from django.db.models import Sum, Count, Q, F, Avg
from datetime import datetime, timedelta
from django.utils.dateparse import parse_date
from decimal import Decimal
from admission.models import Admission, CertificateApproval
from fee_details.models import FeeGeneration, FeeInstallment, FeeDeposit
from student_details.models import Registration
from course.models import Course
from master.models import Organization
from .pdf_base import BaseReportPDF
from datetime import datetime, timedelta
from decimal import Decimal
from reportlab.lib.units import inch 
from reportlab.platypus import Spacer
from admission.models import Admission, CertificateApproval
from rest_framework.permissions import IsAuthenticated
from master.models import Branch
from student_details.models import Enquiry, EnquiryFollowUp
from django.db.models import Exists, OuterRef
from django.db import models
from core.helper_function import get_branch_id
from staff.models import Attendance
from course.models import CourseTracker
from .serializers import AttendanceReportSerializer, CourseTrackerReportSerializer



class CourseWiseAdmissionReportAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        data = request.data

        from_date = data.get('fromDate')
        to_date = data.get('toDate')

        organization_id = data.get('organizationId')
        course_id = data.get('courseId')

        branch_id = get_branch_id(request)

        if not branch_id:
            branch_id = data.get('branch', None)

        courses = Course.objects.filter(
            is_active=True
        )

        if course_id:
            courses = courses.filter(id=course_id)

        course_data = []

        total_admissions = 0
        total_male = 0
        total_female = 0

        for course in courses:

            admissions = Admission.objects.filter(
                course_batches__course=course,
                admission_date__range=[from_date, to_date],
                is_active=True,
                status='Admitted'
            ).distinct()

            if organization_id:
                admissions = admissions.filter(
                    organization_id=organization_id
                )

            if branch_id:
                admissions = admissions.filter(
                    branch_id=branch_id
                )

            count = admissions.count()

            if count > 0:

                male_count = admissions.filter(
                    gender='Male'
                ).count()

                female_count = admissions.filter(
                    gender='Female'
                ).count()

                course_data.append({

                    'course_id': course.id,

                    'course_code': course.course_code,

                    'course_name': course.course_name,

                    'male': male_count,

                    'female': female_count,

                    'total': count,
                })

                total_admissions += count
                total_male += male_count
                total_female += female_count

        course_data.sort(
            key=lambda x: x['total'],
            reverse=True
        )

        return Response({

            "report_metadata": {

                "from_date": from_date,

                "to_date": to_date,

                "branch": (
                    branch_id
                    if branch_id else "All Branches"
                ),

                "generated_at": datetime.now().isoformat()
            },

            "summary": {

                "total_courses_with_data": len(course_data),

                "grand_total_admissions": total_admissions,

                "grand_total_male": total_male,

                "grand_total_female": total_female
            },

            "results": course_data

        }, status=status.HTTP_200_OK)






class RegistrationReportAPIView(APIView):
    """
    Generate registration report data in JSON format
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):

        try:

            data = request.data

            from_date = data.get("fromDate")
            to_date = data.get("toDate")
            organization_id = data.get("organizationId")
            branch_id = data.get("branchId")

            if not from_date or not to_date:
                return Response(
                    {
                        "error": "fromDate and toDate are required"
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # ============================================
            # CHECK ADMISSION EXISTS
            # ============================================

            admission_exists = Admission.objects.filter(
                registration=OuterRef("pk"),
                is_active=True
            )

            # ============================================
            # BASE QUERYSET
            # ============================================

            queryset = Registration.objects.filter(
                registration_date__range=[from_date, to_date],
                is_active=True
            ).annotate(
                is_admitted=Exists(admission_exists)
            ).select_related(
                "organization",
                "branch"
            ).prefetch_related(
                "courses"
            ).order_by("-registration_date")

            # ============================================
            # FILTERS
            # ============================================

            if organization_id:
                queryset = queryset.filter(
                    organization_id=organization_id
                )

            if branch_id:
                queryset = queryset.filter(
                    branch_id=branch_id
                )

            # ============================================
            # SUMMARY
            # ============================================

            total_registrations = queryset.count()

            converted_to_admission = queryset.filter(
                is_admitted=True
            ).count()

            conversion_rate = 0

            if total_registrations > 0:
                conversion_rate = (
                    converted_to_admission
                    / total_registrations
                ) * 100

            # ============================================
            # RESULTS
            # ============================================

            registrations_list = []

            for reg in queryset:

                course_names = list(
                    reg.courses.values_list(
                        "course_name",
                        flat=True
                    )
                )

                registrations_list.append({

                    "id": reg.id,

                    "registration_code":
                        reg.registration_code,

                    "candidate_name":
                        reg.candidate_name,

                    "mobile_no":
                        reg.mobile_no,

                    "email":
                        reg.email or "-",

                    "gender":
                        reg.gender,

                    "registration_date":
                        reg.registration_date.strftime("%Y-%m-%d"),

                    "organization":
                        reg.organization.name
                        if reg.organization else None,

                    "branch":
                        reg.branch.name
                        if reg.branch else None,

                    "courses":
                        course_names,

                    "is_admitted":
                        reg.is_admitted
                })

            # ============================================
            # FINAL RESPONSE
            # ============================================

            return Response({

                "report_metadata": {

                    "report_name":
                        "Registration Report",

                    "from_date":
                        from_date,

                    "to_date":
                        to_date,

                    "generated_at":
                        datetime.now().isoformat()
                },

                "summary": {

                    "total_registrations":
                        total_registrations,

                    "converted_to_admission":
                        converted_to_admission,

                    "conversion_rate":
                        round(conversion_rate, 2)
                },

                "results":
                    registrations_list

            }, status=status.HTTP_200_OK)

        except Exception as e:

            return Response(
                {
                    "error": str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )




class CertificateApprovalReportAPIView(APIView):
    """
    Generate report of certificate approvals in JSON format
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):

        try:

            data = request.data

            from_date = data.get("fromDate")
            to_date = data.get("toDate")
            organization_id = data.get("organizationId")
            branch_id = data.get("branchId")

            # ============================================
            # VALIDATION
            # ============================================

            if not from_date or not to_date:

                return Response(
                    {
                        "error":
                            "fromDate and toDate are required"
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # ============================================
            # QUERYSET
            # ============================================

            queryset = CertificateApproval.objects.filter(
                approval_date__range=[from_date, to_date],
                is_active=True
            ).select_related(
                "admission",
                "admission__organization",
                "admission__branch",
                "approved_by"
            ).order_by("-approval_date")

            # ============================================
            # FILTERS
            # ============================================

            if organization_id:

                queryset = queryset.filter(
                    admission__organization_id=organization_id
                )

            if branch_id:

                queryset = queryset.filter(
                    admission__branch_id=branch_id
                )

            # ============================================
            # RESULTS
            # ============================================

            approvals_list = []

            for cert in queryset:

                approved_by_name = "N/A"

                if cert.approved_by:

                    approved_by_name = (
                        cert.approved_by.first_name
                        or cert.approved_by.username
                    )

                approvals_list.append({

                    "id":
                        cert.id,

                    "admission_no":
                        cert.admission.admission_code
                        if cert.admission else None,

                    "student_name":
                        cert.admission.candidate_name
                        if cert.admission else None,

                    "organization":
                        cert.admission.organization.name
                        if cert.admission and cert.admission.organization
                        else None,

                    "branch":
                        cert.admission.branch.name
                        if cert.admission and cert.admission.branch
                        else None,

                    "approval_date":
                        cert.approval_date.strftime("%Y-%m-%d")
                        if cert.approval_date else None,

                    "approved_by":
                        approved_by_name,

                    "remarks":
                        cert.remarks or ""
                })

            # ============================================
            # RESPONSE
            # ============================================

            return Response({

                "metadata": {

                    "report_name":
                        "Certificate Approval Report",

                    "from_date":
                        from_date,

                    "to_date":
                        to_date,

                    "generated_at":
                        datetime.now().isoformat()
                },

                "summary": {

                    "total_certificates_approved":
                        queryset.count()
                },

                "results":
                    approvals_list

            }, status=status.HTTP_200_OK)

        except Exception as e:

            return Response(
                {
                    "error": str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

from datetime import datetime

from django.db import models
from django.db.models import Count, Q
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from admission.models import Admission
from course.models import Course




class GenerateAdmissionReportAPIView(APIView):
    """
    Generate detailed admission report statistics and data
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):

        try:

            data = request.data

            from_date = data.get("fromDate")
            to_date = data.get("toDate")

            admission_no = data.get("admissionNo")
            organization_id = data.get("organizationId")

            status_filter = data.get("status")
            gender_filter = data.get("gender")

            branch_id = get_branch_id(request)

            if not branch_id:
                branch_id = data.get("branch")

            # ============================================
            # VALIDATION
            # ============================================

            if not from_date or not to_date:

                return Response(
                    {
                        "error":
                            "fromDate and toDate are required"
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # ============================================
            # BASE QUERYSET
            # ============================================

            queryset = Admission.objects.filter(
                admission_date__range=[
                    from_date,
                    to_date
                ],
                is_active=True
            )

            # ============================================
            # FILTERS
            # ============================================

            if admission_no:

                queryset = queryset.filter(
                    admission_code__icontains=admission_no
                )

            if organization_id:

                queryset = queryset.filter(
                    organization_id=organization_id
                )

            if branch_id:

                queryset = queryset.filter(
                    branch_id=branch_id
                )

            if status_filter:

                queryset = queryset.filter(
                    status=status_filter
                )

            if gender_filter:

                queryset = queryset.filter(
                    gender=gender_filter
                )

            # ============================================
            # OPTIMIZATION
            # ============================================

            queryset = queryset.select_related(
                "organization",
                "branch"
            ).prefetch_related(
                "course_batches__course",
                "course_batches__batch"
            ).distinct()

            # ============================================
            # SUMMARY
            # ============================================

            total_admissions = queryset.count()

            stats = queryset.aggregate(

                male=Count(
                    "id",
                    filter=Q(gender="Male")
                ),

                female=Count(
                    "id",
                    filter=Q(gender="Female")
                ),

                admitted=Count(
                    "id",
                    filter=Q(status="Admitted")
                ),

                cancelled=Count(
                    "id",
                    filter=Q(status="Cancelled")
                )
            )

            # ============================================
            # COURSE WISE BREAKDOWN
            # ============================================

            course_breakdown = (

                queryset.values(
                    "course_batches__course__id",
                    "course_batches__course__course_name",
                    "course_batches__course__course_code"
                )

                .annotate(
                    student_count=Count(
                        "id",
                        distinct=True
                    )
                )

                .exclude(
                    course_batches__course__id__isnull=True
                )

                .order_by("-student_count")
            )

            # ============================================
            # STUDENT LIST
            # ============================================

            admissions_list = []

            for adm in queryset:

                # ========================================
                # COURSE + BATCH GROUPING
                # ========================================

                course_map = {}

                for cb in adm.course_batches.all():

                    course_id = cb.course.id

                    if course_id not in course_map:

                        course_map[course_id] = {

                            "course_id": cb.course.id,

                            "course_name": cb.course.course_name,

                            "course_code": cb.course.course_code,

                            "batches": []
                        }

                    course_map[course_id]["batches"].append({

                        "batch_id": cb.batch.id,

                        "batch_name": cb.batch.batch_name,

                        "batch_code": cb.batch.batch_code
                    })

                admissions_list.append({

                    "id": adm.id,

                    "admission_code": adm.admission_code,

                    "student_name": adm.candidate_name,

                    "mobile_no": adm.mobile_no,

                    "alternate_mobile_no": adm.alternate_mobile_no,

                    "email": adm.email or "-",

                    "gender": adm.gender,

                    "admission_date": adm.admission_date.strftime(
                        "%Y-%m-%d"
                    ),

                    "father_name": adm.father_name,

                    "mother_name": adm.mother_name,

                    "qualification": adm.qualification,

                    "aadhaar_no": adm.aadhaar_no,

                    "address": adm.address,

                    "status": adm.status,

                    # ====================================
                    # ORGANIZATION
                    # ====================================

                    "organization": {

                        "id": (
                            adm.organization.id
                            if adm.organization else None
                        ),

                        "name": (
                            adm.organization.name
                            if adm.organization else None
                        )
                    },

                    # ====================================
                    # BRANCH
                    # ====================================

                    "branch": {

                        "id": (
                            adm.branch.id
                            if adm.branch else None
                        ),

                        "name": (
                            adm.branch.name
                            if adm.branch else None
                        )
                    },

                    # ====================================
                    # COURSE DETAILS
                    # ====================================

                    "courses": list(course_map.values())
                })

            # ============================================
            # RESPONSE
            # ============================================

            return Response({

                "metadata": {

                    "report_name": "Admission Report",

                    "from_date": from_date,

                    "to_date": to_date,

                    "generated_at": datetime.now().isoformat(),

                    "branch_id": branch_id,

                    "organization_id": organization_id
                },

                "summary": {

                    "total_admissions": total_admissions,

                    "gender_split": {

                        "male": stats["male"],

                        "female": stats["female"]
                    },

                    "status_split": {

                        "admitted": stats["admitted"],

                        "cancelled": stats["cancelled"]
                    },

                    "course_wise_breakdown": [

                        {
                            "course_id":
                                item[
                                    "course_batches__course__id"
                                ],

                            "course_name":
                                item[
                                    "course_batches__course__course_name"
                                ],

                            "course_code":
                                item[
                                    "course_batches__course__course_code"
                                ],

                            "student_count":
                                item["student_count"]
                        }

                        for item in course_breakdown
                    ]
                },

                "results": admissions_list

            }, status=status.HTTP_200_OK)

        except Exception as e:

            return Response(
                {
                    "error": str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )



class FeeDepositReportAPIView(APIView):
    """
    Generate detailed fee deposit/payment report in JSON format
    """
    
    def post(self, request):
        try:
            data = request.data
            from_date = data.get('fromDate')
            to_date = data.get('toDate')
            adm_no = data.get('admissionNo')
            payment_mode_id = data.get('paymentMode')  # Now expecting ID
            organization_id = data.get('organizationId')

            # 1. Validation
            if not from_date or not to_date:
                return Response(
                    {"error": "fromDate and toDate are required"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 2. Build Queryset
            # Using select_related to navigate the deep relationship: Deposit -> Installment -> FeeGen -> Admission
            queryset = FeeDeposit.objects.filter(
                payment_date__range=[from_date, to_date],
                is_active=True
            ).select_related(
                'payment_mode',
                'installment__fee_generation__admission'
            ).order_by('payment_date')

            if adm_no:
                queryset = queryset.filter(
                    installment__fee_generation__admission__admission_code=adm_no
                )
            
            if payment_mode_id:
                queryset = queryset.filter(payment_mode_id=payment_mode_id)
            
            if organization_id:
                queryset = queryset.filter(
                    installment__fee_generation__admission__organization_id=organization_id
                )

            # 3. Aggregated Summary Statistics
            summary_stats = queryset.aggregate(
                total_count=Count('id'),
                total_collected=Sum('paid_amount')
            )
            
            # Payment mode breakdown (Now grouping by the related PaymentMethod name)
            mode_breakdown = queryset.values('payment_mode__name').annotate(
                count=Count('id'),
                total=Sum('paid_amount')
            ).order_by('-total')

            # 4. Format Detailed Results
            results = []
            for dep in queryset:
                # Safe navigation for related objects
                inst = dep.installment
                fee_gen = inst.fee_generation if inst else None
                adm = fee_gen.admission if fee_gen else None
                
                results.append({
                    "id": dep.id,
                    "payment_date": dep.payment_date.strftime('%Y-%m-%d'),
                    "admission_no": adm.admission_code if adm else "N/A",
                    "student_name": adm.candidate_name if adm else "N/A",
                    "installment_no": inst.installment_no if inst else "N/A",
                    "payment_mode": dep.payment_mode.name if dep.payment_mode else "N/A",
                    "paid_amount": float(dep.paid_amount),
                    "reference_no": dep.reference_no or "-",
                    "bank_name": dep.bank_name or "-"
                })

            # 5. Return JSON Response
            return Response({
                "metadata": {
                    "report_name": "Fee Collection Report",
                    "from_date": from_date,
                    "to_date": to_date,
                    "generated_at": datetime.now().isoformat()
                },
                "summary": {
                    "total_deposits": summary_stats['total_count'] or 0,
                    "total_amount_collected": float(summary_stats['total_collected'] or 0),
                    "mode_wise_breakdown": [
                        {
                            "mode": item['payment_mode__name'],
                            "count": item['count'],
                            "total_amount": float(item['total'])
                        } for item in mode_breakdown
                    ]
                },
                "results": results
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class OutstandingFeeReportAPIView(APIView):
    """
    Generate JSON report of students with outstanding fees filtered by date range.
    """
    
    def post(self, request):
        try:
            data = request.data
            organization_id = data.get('organizationId')
            branch_id = get_branch_id(request)
            min_outstanding = Decimal(str(data.get('minOutstanding', 0)))
            
            # Extract Dates
            from_date = data.get('fromDate')
            to_date = data.get('toDate')

            # 1. Build Queryset
            queryset = FeeGeneration.objects.filter(
                is_active=True,
                admission__is_active=True,
                balance_amount__gte=min_outstanding
            ).select_related('admission', 'admission__organization').order_by('-balance_amount')
            
            # Apply Date Filters (Using admission_date as the primary timeline)
            if from_date:
                queryset = queryset.filter(admission__admission_date__gte=parse_date(from_date))
            if to_date:
                queryset = queryset.filter(admission__admission_date__lte=parse_date(to_date))
            
            if organization_id:
                queryset = queryset.filter(admission__organization_id=organization_id)
            
            if branch_id:
                queryset = queryset.filter(branch_id=branch_id)

            # 2. Aggregated Summary
            summary_stats = queryset.aggregate(
                grand_total_outstanding=Sum('balance_amount'),
                student_count=models.Count('id')
            )

            # 3. Format Results
            outstanding_list = []
            for fee_gen in queryset:
                adm = fee_gen.admission
                outstanding_list.append({
                    "id": fee_gen.id,
                    "admission_code": adm.admission_code,
                    "student_name": adm.candidate_name,
                    "mobile": adm.mobile_no,
                    "total_fee": float(fee_gen.total_fee),
                    "paid_amount": float(fee_gen.total_fee - fee_gen.balance_amount),
                    "outstanding_amount": float(fee_gen.balance_amount),
                    "installment_count": fee_gen.installment_count,
                    "last_updated": fee_gen.updated_at.strftime('%Y-%m-%d'),
                    "admission_date": adm.admission_date.strftime('%Y-%m-%d')
                })

            # 4. Final JSON Response
            return Response({
                "metadata": {
                    "report_name": "Outstanding Fee Report",
                    "from_date": from_date,
                    "to_date": to_date,
                    "min_outstanding_filter": float(min_outstanding),
                    "generated_at": datetime.now().isoformat()
                },
                "summary": {
                    "total_students_with_outstanding": summary_stats['student_count'] or 0,
                    "total_outstanding_amount": float(summary_stats['grand_total_outstanding'] or 0)
                },
                "results": outstanding_list
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class EnquiryReportAPIView(APIView):
    """
    Generate JSON report for Enquiries stored in student_details
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            data = request.data
            from_date = data.get('fromDate')
            to_date = data.get('toDate')
            org_id = data.get('organizationId')

            if not from_date or not to_date:
                return Response({"error": "fromDate and toDate are required"}, status=400)

            # 1. Fetch Enquiries with related master data
            queryset = Enquiry.objects.filter(
                enquiry_date__range=[from_date, to_date],
                is_active=True
            ).select_related(
                'enquiry_source', 
                'status', 
                'assigned_to', 
                'followup_medium'
            ).prefetch_related('courses')

            # Filter by Organization (via the Assigned Employee)
            if org_id:
                queryset = queryset.filter(assigned_to__organization_id=org_id)

            # 2. Aggregated Statistics for Charts/Summary
            source_stats = queryset.values('enquiry_source__name').annotate(count=Count('id'))
            status_stats = queryset.values('status__name').annotate(count=Count('id'))

            # 3. Format result list
            results = []
            for enq in queryset:
                results.append({
                    "id": enq.id,
                    "enquiry_code": enq.enquiry_code,
                    "date": enq.enquiry_date.strftime('%Y-%m-%d'),
                    "candidate_name": enq.candidate_name,
                    "mobile": enq.mobile_no,
                    "source": enq.enquiry_source.name if enq.enquiry_source else "Direct",
                    "status": enq.status.name if enq.status else "Open",
                    "assigned_to": enq.assigned_to.name if enq.assigned_to else "Unassigned",
                    "courses": [c.course_name for c in enq.courses.all()],
                    "next_followup": enq.next_followup_date.strftime('%Y-%m-%d') if enq.next_followup_date else None
                })

            return Response({
                "summary": {
                    "total_enquiries": queryset.count(),
                    "by_source": {item['enquiry_source__name']: item['count'] for item in source_stats if item['enquiry_source__name']},
                    "by_status": {item['status__name']: item['count'] for item in status_stats if item['status__name']}
                },
                "results": results
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({"error": str(e)}, status=500)

class FollowUpReportAPIView(APIView):
    """
    Generate JSON report for Enquiry Follow-ups
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            data = request.data
            from_date = data.get('fromDate')
            to_date = data.get('toDate')
            org_id = data.get('organizationId')

            # Query followups through the OneToOne relation
            queryset = EnquiryFollowUp.objects.filter(
                followup_date__range=[from_date, to_date],
                is_active=True
            ).select_related('enquiry', 'status', 'enquiry__assigned_to')

            if org_id:
                queryset = queryset.filter(enquiry__assigned_to__organization_id=org_id)

            results = []
            for follow in queryset:
                results.append({
                    "id": follow.id,
                    "followup_date": follow.followup_date.strftime('%Y-%m-%d'),
                    "enquiry_code": follow.enquiry.enquiry_code,
                    "candidate_name": follow.enquiry.candidate_name,
                    "mobile": follow.enquiry.mobile_no,
                    "remark": follow.remark,
                    "status": follow.status.name if follow.status else "No Status"
                })

            return Response({
                "summary": {"total_followups": len(results)},
                "results": results
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=500)

class AttendanceReportView(generics.ListAPIView):
    """
    Generate JSON report for Attendance
    """
    permission_classes = [IsAuthenticated]
    serializer_class = AttendanceReportSerializer

    def get_queryset(self):
        # Start with active records and optimize DB hits with select_related
        queryset = Attendance.objects.filter(is_active=True).select_related('employee')
        
        # Grab date strings from the URL query params
        from_date = self.request.query_params.get('from_date')
        to_date = self.request.query_params.get('to_date')
        employee_id = self.request.query_params.get('employee')

        # Filter by Date Range (Optional)
        if from_date:
            queryset = queryset.filter(date__gte=from_date)
        if to_date:
            queryset = queryset.filter(date__lte=to_date)
            
        # Filter by Employee (Optional)
        if employee_id:
            queryset = queryset.filter(employee_id=employee_id)

        return queryset.order_by('-date')


class CourseTrackerReportView(generics.ListAPIView):

    serializer_class = CourseTrackerReportSerializer

    def get_queryset(self):

        queryset = CourseTracker.objects.filter(
            is_active=True
        ).select_related(
            "organization",
            "branch",
            "trainer",
            "batch",
            "course"
        )

        from_date = self.request.query_params.get("from_date")
        to_date = self.request.query_params.get("to_date")
        branch_id = self.request.query_params.get("branch")
        trainer_id = self.request.query_params.get("trainer")
        status_value = self.request.query_params.get("status")

        # =====================================
        # DATE FILTERS
        # =====================================

        if from_date:
            queryset = queryset.filter(
                date__gte=from_date
            )

        if to_date:
            queryset = queryset.filter(
                date__lte=to_date
            )

        # =====================================
        # BRANCH FILTER
        # =====================================

        if branch_id and str(branch_id).isdigit():

            queryset = queryset.filter(
                branch_id=int(branch_id)
            )

        # =====================================
        # TRAINER FILTER
        # =====================================

        if trainer_id and str(trainer_id).isdigit():

            queryset = queryset.filter(
                trainer_id=int(trainer_id)
            )

        # =====================================
        # STATUS FILTER
        # =====================================

        if status_value:

            queryset = queryset.filter(
                status__iexact=status_value.strip()
            )

        return queryset.order_by("-date")
