import io
from django.http import FileResponse
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Admission, CertificateApproval, Attendance
from .serializers import AdmissionSerializer, CertificateApprovalSerializer, AttendanceSerializer
from fee_details.models import FeeGeneration, FeeDeposit
from django.db.models import Sum
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from django.db.models import Q
from core.logging_utils import log_audit, log_activity, log_error
from users.models import User
from django.utils.crypto import get_random_string
from core.models import ClientUser, Client
from rest_framework.permissions import IsAuthenticated
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import portrait
from reportlab.lib.units import mm
from reportlab.lib import colors
from core.helper_function import get_branch_id
from .id_card_generator import generate_student_id_card
from django.db.models import Sum, Q
from .models import *
from fee_details.models import FeeGeneration, FeeDeposit
from .serializers import *
from datetime import date
from decimal import Decimal
from django.db import transaction
from io import BytesIO
from core.helper_function import get_branch_id

from django.utils import timezone

from .utils import (
    build_certificate_html,
    generate_certificate_pdf
)



class AdmissionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk=None):

        try:

            if pk:
                admission = get_object_or_404(
                    Admission,
                    pk=pk,
                    is_active=True
                )

                return Response(
                    AdmissionSerializer(admission).data
                )

            queryset = Admission.objects.filter(
                is_active=True
            )

            # ====================================
            # ORGANIZATION FILTER
            # ====================================
            organization_id = request.query_params.get(
                "organization_id"
            )

            if organization_id:
                queryset = queryset.filter(
                    organization_id=organization_id
                )

            # ====================================
            # BRANCH FILTER
            # ====================================
            branch_id = request.query_params.get(
                "branch_id"
            )

            if branch_id:
                queryset = queryset.filter(
                    branch_id=branch_id
                )

            # ====================================
            # SEARCH FILTER
            # ====================================
            search = request.query_params.get(
                "search"
            )

            if search:
                queryset = queryset.filter(
                    Q(candidate_name__icontains=search) |
                    Q(admission_code__icontains=search) |
                    Q(mobile_no__icontains=search) |
                    Q(aadhaar_no__icontains=search)
                )

            # ====================================
            # STATUS FILTER
            # ====================================
            status_filter = request.query_params.get(
                "status"
            )

            if status_filter:
                queryset = queryset.filter(
                    status=status_filter
                )

            serializer = AdmissionSerializer(
                queryset,
                many=True
            )

            return Response(serializer.data)

        except Exception as e:

            return Response(
                {"error": str(e)},
                status=500
            )

    # def post(self, request):
    #     branch_id = get_branch_id(request)
    #     if not branch_id:
    #         branch_id = request.data.get('branch', None)
            
                
    #     try:
    #         client_code = getattr(request.user, "client_code", None)

    #         serializer = AdmissionSerializer(
    #             data=request.data,
    #             context={"request": request, "branch_id": branch_id}
    #         )

    #         if serializer.is_valid():
    #             admission = serializer.save()

    #             credentials = None
    #             password = None
    #             student_email = admission.email

    #             if student_email:

    #                 user_obj, created = User.objects.get_or_create(
    #                     email=student_email,
    #                     defaults={
    #                         "first_name": admission.candidate_name,
    #                         "role": "user",
    #                         "client_code": client_code,
    #                         "is_active": True,
    #                     }
    #                 )

    #                 if created:
    #                     password = get_random_string(8)
    #                     user_obj.set_password(password)
    #                     user_obj.save()

    #                     credentials = {
    #                         "email": student_email,
    #                         "password": password,
    #                     }

    #                 ClientUser.objects.update_or_create(
    #                     client_code=client_code,
    #                     user_id=student_email,
    #                     defaults={
    #                         "password": user_obj.password,
    #                         "branch": admission.branch,
    #                         "role": "user",
    #                         "is_admin": False,
    #                         "employee_name": admission.candidate_name,
    #                         "is_active": True,
    #                     },
    #                 )

    #             # response_data = serializer.data
    #             response_data = AdmissionSerializer(admission).data

    #             if credentials:
    #                 response_data["credentials"] = credentials

    #             return Response(response_data, status=201)

    #         return Response(serializer.errors, status=400)

    #     except Exception as e:
    #         return Response({"error": str(e)}, status=500)

    def post(self, request):

        # branch_id = get_branch_id(request)

        # if not branch_id:
        #     branch_id = request.data.get('branch', None)

        branch_id = request.data.get("branch")

        if not branch_id:
            branch_id = get_branch_id(request)


        try:

            serializer = AdmissionSerializer(
                data=request.data,
                context={
                    "request": request,
                    "branch_id": branch_id
                }
            )

            if serializer.is_valid():

                admission = serializer.save()

                response_data = AdmissionSerializer(admission).data

                return Response(
                    response_data,
                    status=201
                )

            return Response(
                serializer.errors,
                status=400
            )

        except Exception as e:

            return Response(
                {"error": str(e)},
                status=500
            )




    def put(self, request, pk):
        try:
            admission = get_object_or_404(
                Admission,
                pk=pk,
                is_active=True
            )

            old_email = admission.email

            # branch_id = get_branch_id(request)
            # if not branch_id:
            #     branch_id = request.data.get("branch")

            branch_id = request.data.get("branch")

            if not branch_id:
                branch_id = get_branch_id(request)

            serializer = AdmissionSerializer(
                admission,
                data=request.data,
                partial=True,
                context={"request": request, "branch_id": branch_id}
            )

            if serializer.is_valid():
                admission = serializer.save()

                new_email = admission.email
                client_code = getattr(request.user, "client_code", None)

                # # 🔄 If email changed → update login
                # if old_email != new_email and new_email:

                #     user_obj = User.objects.filter(email=old_email).first()
                #     if user_obj:
                #         user_obj.email = new_email
                #         user_obj.save()

                #     ClientUser.objects.filter(
                #         client_code=client_code,
                #         user_id=old_email
                #     ).update(user_id=new_email)

                return Response(serializer.data)

            return Response(serializer.errors, status=400)

        except Exception as e:
            return Response({"error": str(e)}, status=500)



    def delete(self, request, pk):

        try:

            admission = get_object_or_404(
                Admission,
                pk=pk,
                is_active=True
            )

            client_code = getattr(
                request.user,
                "client_code",
                None
            )

            with transaction.atomic():

                # =====================================
                # SOFT DELETE ADMISSION
                # =====================================

                admission.is_active = False

                admission.save(
                    update_fields=["is_active"]
                )

                # =====================================
                # DEACTIVATE STAFF USER
                # =====================================

                from staff.models import StaffUser

                staff_users = StaffUser.objects.filter(
                    admission=admission,
                    is_active=True
                )

                for staff_user in staff_users:

                    staff_user.is_active = False

                    staff_user.save(
                        update_fields=["is_active"]
                    )

                    # =================================
                    # DEACTIVATE DJANGO USER
                    # =================================

                    User.objects.filter(
                        email=staff_user.username
                    ).update(
                        is_active=False
                    )

                    # =================================
                    # DEACTIVATE CLIENT USER
                    # =================================

                    ClientUser.objects.filter(
                        client_code=client_code,
                        user_id=staff_user.username
                    ).update(
                        is_active=False
                    )

            return Response(
                {
                    "message":
                        "Admission soft deleted successfully."
                },
                status=200
            )

        except Exception as e:

            return Response(
                {"error": str(e)},
                status=500
            )




class AdmissionByCourseBatchAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        course_id = request.query_params.get("course_id")
        batch_id = request.query_params.get("batch_id")

        branch_id = get_branch_id(request)

        # -----------------------------------
        # BASE QUERY
        # -----------------------------------

        mappings = AdmissionCourseBatch.objects.select_related(
            "admission",
            "course",
            "batch"
        ).filter(
            admission__is_active=True
        )

        # -----------------------------------
        # BRANCH FILTER
        # -----------------------------------

        if branch_id:
            mappings = mappings.filter(
                admission__branch_id=branch_id
            )

        # -----------------------------------
        # COURSE FILTER
        # -----------------------------------

        if course_id:
            mappings = mappings.filter(
                course_id=course_id
            )

        # -----------------------------------
        # BATCH FILTER
        # -----------------------------------

        if batch_id:
            mappings = mappings.filter(
                batch_id=batch_id
            )

        # -----------------------------------
        # DISTINCT ADMISSIONS
        # -----------------------------------

        admission_ids = mappings.values_list(
            "admission_id",
            flat=True
        ).distinct()

        admissions = Admission.objects.filter(
            id__in=admission_ids,
            is_active=True
        ).prefetch_related(
            "course_batches"
        )

        serializer = AdmissionSerializer(
            admissions,
            many=True
        )

        return Response({
            "count": admissions.count(),
            "results": serializer.data
        })

from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404


class AttendanceAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk=None):
        try:

            # =====================================
            # SINGLE RECORD
            # =====================================
            if pk:
                attendance = get_object_or_404(
                    Attendance.objects.select_related(
                        "admission",
                        "admission__organization",
                        "admission__branch"
                    ),
                    pk=pk,
                    admission__is_active=True
                )

                serializer = AttendanceSerializer(attendance)
                return Response(serializer.data)

            # =====================================
            # BASE QUERYSET
            # =====================================

            queryset = Attendance.objects.select_related(
                "admission",
                "admission__organization",
                "admission__branch"
            ).filter(
                admission__is_active=True
            )

            # =====================================
            # ORGANIZATION / BRANCH FILTERS
            # =====================================

            organization_id = request.query_params.get("organization")
            branch_id = request.query_params.get("branch")
            status = request.query_params.get("status")

            if status:
                queryset = queryset.filter(status=status)

            if organization_id and branch_id:

                queryset = queryset.filter(
                    admission__organization_id=organization_id,
                    admission__branch_id=branch_id
                )

            elif organization_id:

                queryset = queryset.filter(
                    admission__organization_id=organization_id
                )

            elif branch_id:

                queryset = queryset.filter(
                    admission__branch_id=branch_id
                )

            # =====================================
            # STUDENT FILTER
            # =====================================

            admission_id = request.query_params.get("admission_id")

            if admission_id:
                queryset = queryset.filter(
                    admission_id=admission_id
                )

            # =====================================
            # SEARCH FILTER
            # =====================================

            search = request.query_params.get("search")

            if search:
                queryset = queryset.filter(
                    Q(admission__candidate_name__icontains=search) |
                    Q(admission__admission_code__icontains=search) |
                    Q(admission__mobile_no__icontains=search)
                )

            # =====================================
            # DATE FILTERS
            # =====================================

            start_date = request.query_params.get("start_date")
            end_date = request.query_params.get("end_date")

            if start_date and end_date:
                queryset = queryset.filter(
                    date__range=[start_date, end_date]
                )

            # =====================================
            # ORDERING
            # =====================================

            queryset = queryset.order_by(
                "-date",
                "admission__candidate_name"
            )

            # serializer = AttendanceSerializer(
            #     queryset,
            #     many=True
            # )

            # return Response(serializer.data)

            # =====================================
            # SUMMARY
            # =====================================

            working_days = queryset.count()

            present_days = queryset.filter(
                status="present"
            ).count()

            absent_days = queryset.filter(
                status="absent"
            ).count()

            half_days = queryset.filter(
                status="half_day"
            ).count()

            leave_days = queryset.filter(
                status="on_leave"
            ).count()

            attendance_percentage = 0

            if working_days:

                attendance_percentage = round(
                    (
                        present_days +
                        (half_days * 0.5)
                    ) / working_days * 100,
                    2
                )

            serializer = AttendanceSerializer(
                queryset,
                many=True
            )

            return Response({

                "summary": {

                    "working_days": working_days,
                    "present_days": present_days,
                    "absent_days": absent_days,
                    "half_days": half_days,
                    "leave_days": leave_days,
                    "attendance_percentage": attendance_percentage

                },

                "records": serializer.data

            })

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=500
            )







    def post(self, request):
        try:
            serializer = AttendanceSerializer(data=request.data)
            if serializer.is_valid():
                admission = serializer.validated_data['admission']
                date = serializer.validated_data['date']

                # 1. Prevent marking attendance for soft-deleted students
                if not admission.is_active:
                    return Response({"error": "Cannot mark attendance for an inactive student."}, status=400)

                # 2. Duplicate Check
                if Attendance.objects.filter(admission=admission, date=date).exists():
                    return Response(
                        {"error": f"Attendance already marked for {admission.candidate_name} on {date}."},
                        status=400
                    )
                
                serializer.save(marked_by=request.user)
                return Response(serializer.data, status=201)
            
            return Response(serializer.errors, status=400)

        except Exception as e:
            return Response({"error": str(e)}, status=500)

    def put(self, request, pk):
        try:
            attendance = get_object_or_404(Attendance, pk=pk)
            serializer = AttendanceSerializer(attendance, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save(marked_by=request.user)
                return Response(serializer.data)
            return Response(serializer.errors, status=400)
        except Exception as e:
            return Response({"error": str(e)}, status=500)

    def delete(self, request, pk):
        try:
            attendance = get_object_or_404(Attendance, pk=pk)
            attendance.delete() # Or attendance.is_active = False if you prefer soft-delete here too
            return Response({"message": "Attendance record deleted successfully"}, status=200)
        except Exception as e:
            return Response({"error": str(e)}, status=500)


class StudentAttendanceAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, admission_id=None):

        try:

            # ==============================
            # SINGLE STUDENT ATTENDANCE
            # ==============================

            if admission_id:

                admission = get_object_or_404(
                    Admission,
                    id=admission_id,
                    is_active=True
                )

                


                attendance_records = admission.attendance_records.filter(
                    is_active=True
                )

                start_date = request.query_params.get("start_date")
                end_date = request.query_params.get("end_date")

                if start_date and end_date:

                    attendance_records = attendance_records.filter(
                        date__range=[start_date, end_date]
                    )

                elif start_date:

                    attendance_records = attendance_records.filter(
                        date__gte=start_date
                    )

                elif end_date:

                    attendance_records = attendance_records.filter(
                        date__lte=end_date
                    )

                working_days = attendance_records.count()

                present_days = attendance_records.filter(
                    status="present"
                ).count()

                absent_days = attendance_records.filter(
                    status="absent"
                ).count()

                half_days = attendance_records.filter(
                    status="half_day"
                ).count()

                leave_days = attendance_records.filter(
                    status="on_leave"
                ).count()

                attendance_percentage = 0

                if working_days:

                    attendance_percentage = round(
                        (
                            present_days +
                            (half_days * 0.5)
                        ) / working_days * 100,
                        2
                    )

                history = AttendanceSerializer(
                    attendance_records.order_by("-date"),
                    many=True
                ).data

                return Response({

                    "student": {

                        "id": admission.id,
                        "admission_code": admission.admission_code,
                        "candidate_name": admission.candidate_name,
                        "mobile_no": admission.mobile_no,
                        "email": admission.email

                    },

                    "summary": {

                        "working_days": working_days,
                        "present_days": present_days,
                        "absent_days": absent_days,
                        "half_days": half_days,
                        "leave_days": leave_days,
                        "attendance_percentage": attendance_percentage

                    },

                    "history": history

                })



            




            # ==============================
            # ALL STUDENTS WITH ATTENDANCE
            # ==============================

            queryset = Admission.objects.filter(
                is_active=True
            ).prefetch_related(
                "attendance_records"
            )



            # =====================================
            # ORGANIZATION FILTER
            # =====================================

            organization = request.query_params.get("organization")

            if organization:

                queryset = queryset.filter(
                    organization_id=organization
                )

            # =====================================
            # BRANCH FILTER
            # =====================================

            branch = request.query_params.get("branch")

            if branch:

                queryset = queryset.filter(
                    branch_id=branch
                )

            # =====================================
            # SEARCH FILTER
            # =====================================

            search = request.query_params.get("search")

            if search:

                queryset = queryset.filter(
                    Q(candidate_name__icontains=search) |
                    Q(admission_code__icontains=search) |
                    Q(mobile_no__icontains=search)
                )

            # =====================================
            # ORDERING
            # =====================================

            queryset = queryset.order_by(
                "candidate_name"
            )

          

            response = []

            for admission in queryset:

                attendance = admission.attendance_records.filter(
                    is_active=True
                )

                working_days = attendance.count()

                present_days = attendance.filter(
                    status="present"
                ).count()

                half_days = attendance.filter(
                    status="half_day"
                ).count()

                absent_days = attendance.filter(
                    status="absent"
                ).count()

                leave_days = attendance.filter(
                    status="on_leave"
                ).count()

                attendance_percentage = 0

                if working_days:

                    attendance_percentage = round(
                        (
                            present_days +
                            (half_days * 0.5)
                        ) / working_days * 100,
                        2
                    )

                response.append({

                    "id": admission.id,
                    "admission_code": admission.admission_code,
                    "candidate_name": admission.candidate_name,
                    "mobile_no": admission.mobile_no,
                    "email": admission.email,

                    "summary": {

                        "working_days": working_days,
                        "present_days": present_days,
                        "absent_days": absent_days,
                        "half_days": half_days,
                        "leave_days": leave_days,
                        "attendance_percentage": attendance_percentage

                    }

                })

            return Response(response)

        except Exception as e:

            return Response(
                {"error": str(e)},
                status=500
            )


class AttendanceRecordAPIView(APIView):

    permission_classes = [IsAuthenticated]

    # =====================================
    # GET
    # =====================================

    def get(self, request, pk=None):

        try:

            if pk:

                attendance = get_object_or_404(
                    Attendance,
                    pk=pk,
                    admission__is_active=True
                )

                serializer = AttendanceSerializer(
                    attendance
                )

                return Response(serializer.data)

            queryset = Attendance.objects.filter(
                admission__is_active=True
            ).order_by("-date")

            serializer = AttendanceSerializer(
                queryset,
                many=True
            )

            return Response(serializer.data)

        except Exception as e:

            return Response(
                {"error": str(e)},
                status=500
            )

    # =====================================
    # PUT
    # =====================================

    def put(self, request, pk):

        try:

            attendance = get_object_or_404(
                Attendance,
                pk=pk
            )

            serializer = AttendanceSerializer(
                attendance,
                data=request.data,
                partial=True
            )

            if serializer.is_valid():

                serializer.save(marked_by=request.user)

                return Response(
                    serializer.data,
                    status=200
                )

            return Response(
                serializer.errors,
                status=400
            )

        except Exception as e:

            return Response(
                {"error": str(e)},
                status=500
            )



class CertificateStudentSearchAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
            try:
                # 1. Tenant Isolation Logic
                user = request.user
                # If super_admin, they can see everything or pass a specific client header
                # Otherwise, they are locked to their own client_code
                client_code = (
                    request.headers.get("X-Client-Code")
                    if getattr(user, 'role', None) == "super_admin" 
                    else getattr(user, 'client_code', None)
                )

                search_temp = request.query_params.get('searchTerm', '')
                page_number = request.query_params.get('pageNumber', 1)
                page_size = request.query_params.get('pageSize', 10)
                
                # 2. Filter base queryset by active status and organization's client
                queryset = Admission.objects.filter(is_active=True).select_related('organization')
                
                if client_code:
                    queryset = queryset.filter(organization__client=client_code)
                elif getattr(user, 'role', None) != "super_admin":
                    # Safety check: if not super_admin and no client_code found, return empty
                    return Response({
                        "results": [],
                        "totalCount": 0,
                        "totalPages": 0,
                        "currentPage": int(page_number)
                    })

                # 3. Apply Search Filters
                if search_temp:
                    queryset = queryset.filter(
                        Q(candidate_name__icontains=search_temp) |
                        Q(admission_code__icontains=search_temp) |
                        Q(mobile_no__icontains=search_temp) |
                        Q(email__icontains=search_temp)
                    )

                # 4. Pagination
                paginator = Paginator(queryset, page_size)
                page_obj = paginator.get_page(page_number)
                
                results = []
                for student in page_obj:
                    # 5. Fetch Fee Balance (Scoped to the student)
                    fee_gen = FeeGeneration.objects.filter(
                        candidate=student, 
                        is_active=True
                    ).first()
                    
                    balance = fee_gen.balance_amount if fee_gen else 0
                    
                    results.append({
                        "id": student.id,
                        "admissionNo": student.admission_code,
                        "name": student.candidate_name,
                        "mobile": student.mobile_no,
                        "email": student.email,
                        "balance": balance
                    })
                    
                return Response({
                    "results": results,
                    "totalCount": paginator.count,
                    "totalPages": paginator.num_pages,
                    "currentPage": int(page_number)
                })

            except Exception as e:
                # Log the error with context
                if hasattr(self, 'log_error'):
                    log_error(request, "CertificateStudentSearchAPIView.get", str(e), e)
                print(f"Search Error: {e}") 
                return Response({"error": "An error occurred"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CertificateStudentDetailAPIView(APIView):
    def get(self, request, pk):
        try:
            user = request.user
            # Secure client_code logic
            client_code = (
                request.headers.get("X-Client-Code")
                if getattr(user, 'role', None) == "super_admin" 
                else getattr(user, 'client_code', None)
            )

            # Use filter + first instead of get_object_or_404 to handle client isolation manually
            admission = get_object_or_404(Admission, pk=pk)
            
            # Check access strictly
            if client_code and admission.organization and admission.organization.client != client_code:
                 return Response({"error": "Unauthorized access"}, status=status.HTTP_403_FORBIDDEN)
            elif not client_code and getattr(user, 'role', None) != "super_admin":
                 return Response({"error": "Configuration error: No client assigned to user"}, status=status.HTTP_403_FORBIDDEN)

            # Fee Summary
            fee_gen = FeeGeneration.objects.filter(candidate=admission, is_active=True).first()
            
            billing = 0
            collection = 0
            balance = 0
            
            if fee_gen:
                billing = fee_gen.total_fee
                balance = fee_gen.balance_amount
                total_deposits = FeeDeposit.objects.filter(installment__fee_generation=fee_gen).aggregate(total=Sum('paid_amount'))['total'] or 0
                collection = fee_gen.advance_amount + total_deposits

            fee_summary = {
                "billing": billing,
                "collection": collection,
                "balance": balance
            }
            
            # Deposit History (Last 5)
            deposit_history = []
            if fee_gen:
                deposits = FeeDeposit.objects.filter(installment__fee_generation=fee_gen).order_by('-payment_date')[:5]
                for dep in deposits:
                    deposit_history.append({
                        "date": dep.payment_date,
                        "amount": dep.paid_amount,
                        "mode": dep.payment_mode,
                         "receiptNo": dep.id 
                    })

            student_data = AdmissionSerializer(admission).data
            
            return Response({
                "student": student_data,
                "feeSummary": fee_summary,
                "depositHistory": deposit_history
            })

        except Exception as e:
            log_error(request, "CertificateStudentDetailAPIView.get", str(e), e)
            return Response({"error": "An error occurred"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CertificateApprovalAPIView(APIView):
    def post(self, request):
        try:
            # Serializer validation logic usually handles the client assignment inside .save()
            serializer = CertificateApprovalSerializer(data=request.data, context={'request': request})
            if serializer.is_valid():
                approval = serializer.save()
                log_activity(request, f"Approved certificate for admission {approval.admission.admission_code}")
                return Response({"success": True, "approvalId": approval.id}, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            log_error(request, "CertificateApprovalAPIView.post", str(e), e)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get(self, request): 
        try:
            user = request.user
            client_code = (
                request.headers.get("X-Client-Code")
                if getattr(user, 'role', None) == "super_admin" 
                else getattr(user, 'client_code', None)
            )

            page_number = request.query_params.get('pageNumber', 1)
            page_size = request.query_params.get('pageSize', 10)
            search_term = request.query_params.get('searchTerm', '')
            
            queryset = CertificateApproval.objects.filter(is_active=True).select_related('admission')
            
            # Strict Client Isolation
            if client_code:
                queryset = queryset.filter(admission__organization__client=client_code)
            elif getattr(user, 'role', None) != "super_admin":
                return Response({"results": [], "totalCount": 0}, status=status.HTTP_200_OK)

            if search_term:
                queryset = queryset.filter(
                    Q(admission__candidate_name__icontains=search_term) |
                    Q(admission__admission_code__icontains=search_term)
                )

            paginator = Paginator(queryset, page_size)
            page_obj = paginator.get_page(page_number)
            serializer = CertificateApprovalSerializer(page_obj, many=True)
            
            return Response({
                "results": serializer.data,
                "totalCount": paginator.count,
                "totalPages": paginator.num_pages,
                "currentPage": int(page_number)
            })
        except Exception as e:
            log_error(request, "CertificateApprovalAPIView.get", str(e), e)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CertificateInvoicesAPIView(APIView):
    def get(self, request, pk):
        try:
            user = request.user
            client_code = (
                request.headers.get("X-Client-Code")
                if getattr(user, 'role', None) == "super_admin" 
                else getattr(user, 'client_code', None)
            )

            admission = get_object_or_404(Admission, pk=pk)
            
            # Check access strictly
            if client_code and admission.organization and admission.organization.client != client_code:
                 return Response({"error": "Unauthorized access"}, status=status.HTTP_403_FORBIDDEN)
            elif not client_code and getattr(user, 'role', None) != "super_admin":
                 return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)
                 
            fee_gen = FeeGeneration.objects.filter(candidate=admission, is_active=True).first()
            invoices = []
            
            if fee_gen:
                deposits = FeeDeposit.objects.filter(installment__fee_generation=fee_gen).order_by('-payment_date')
                for dep in deposits:
                    invoices.append({
                        "receiptNo": dep.id,
                        "date": dep.payment_date,
                        "amount": dep.paid_amount,
                        "mode": dep.payment_mode,
                        "installment": dep.installment.installment_no if dep.installment else "N/A"
                    })
            
            return Response(invoices)
            
        except Exception as e:
            log_error(request, "CertificateInvoicesAPIView.get", str(e), e)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class StudentIDCardDataAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        # Attempt to get branch_id from helper or query params
        branch_id = get_branch_id(request)
        if not branch_id:
            branch_id = request.query_params.get("branch")

        # Fetch admission based on actual model fields
        # Using select_related for performance on branch and organization
        admission = get_object_or_404(
            Admission.objects.select_related('branch', 'organization').prefetch_related('courses'),
            pk=pk,
            branch_id=branch_id,
            is_active=True
        )

        # Since courses is a ManyToMany, we'll join them as a string
        course_names = ", ".join([course.course_name for course in admission.courses.all()])

        # Prepare the data dictionary mapped to your Admission model
        data = {
            "student_name": admission.candidate_name,
            "roll_number": admission.admission_code,
            "courses": course_names if course_names else "N/A",
            "emergency_contact": admission.mobile_no,
            "alternate_contact": admission.alternate_mobile_no,
            "blood_group": getattr(admission, 'blood_group', 'N/A'), # In case it's added later
            "photo_url": request.build_absolute_uri(admission.image.url) if admission.image else None,
            "school_name": admission.branch.name if admission.branch else (
                admission.organization.name if admission.organization else "WIMS Institute"
            ),
            "address": admission.address,
            "admission_date": admission.admission_date,
            # Placeholder for expiry if no session model exists in Admission
            "expiry_date": None, 
        }

        return Response(data, status=status.HTTP_200_OK)

# latest


# class CertificateIssueSaveAPIView(APIView):
#     permission_classes = [IsAuthenticated]
    
#     @transaction.atomic  # <--- Add this decorator here
#     def post(self, request):
#         serializer = CertificateIssueSerializer(data=request.data, context={"request": request})
        
#         if serializer.is_valid():
#             # Now select_for_update() will work correctly inside the transaction
#             prefix_obj = CodePrefix.objects.select_for_update().filter(
#                 module__iexact="certificate",
#                 form__iexact="Issue",
#                 is_active=True
#             ).first()
            
#             if prefix_obj:
#                 prefix_obj.current_number += 1
#                 prefix_obj.save(update_fields=["current_number"])
#                 cert_no = f"{prefix_obj.prefix}{str(prefix_obj.current_number).zfill(5)}"
#             else:
#                 last = CertificateIssue.objects.order_by("-id").first()
#                 next_id = (last.id + 1) if last else 1
#                 cert_no = f"CERT{str(next_id).zfill(5)}"
            
#             # Derived organization and branch from the student record is safer 
#             # than from request.user (if user is superadmin)
#             student = serializer.validated_data['student']
            
#             serializer.save(
#                 certificate_no=cert_no,
#                 created_by=request.user,
#                 organization=student.organization,
#                 branch=student.branch
#             )
#             return Response(serializer.data, status=201)
        
#         return Response(serializer.errors, status=400)


class CertificateIssueSaveAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):

        student_id = request.data.get("student")

        issue_date = request.data.get("issue_date")
        expiry_date = request.data.get("expiry_date")

        certificates = request.data.get("certificates", [])

        if not certificates:
            return Response(
                {
                    "error": "certificates list is required"
                },
                status=400
            )

        student = get_object_or_404(
            Admission,
            id=student_id,
            is_active=True
        )

        created_certificates = []

        for item in certificates:

            course_id = item.get("course")
            batch_id = item.get("batch")
            template_id = item.get("template")

            # =========================
            # VALIDATE COURSE/BATCH
            # =========================
            mapping_exists = AdmissionCourseBatch.objects.filter(
                admission=student,
                course_id=course_id,
                batch_id=batch_id,
                is_active=True
            ).exists()

            if not mapping_exists:
                return Response(
                    {
                        "error":
                            "Course/Batch not assigned to student."
                    },
                    status=400
                )

            # =========================
            # PREVENT DUPLICATE ISSUE
            # =========================
            already_issued = CertificateIssue.objects.filter(
                student=student,
                course_id=course_id,
                batch_id=batch_id,
                template_id=template_id,
                is_active=True
            ).exists()

            if already_issued:
                return Response(
                    {
                        "error":
                            f"Certificate already issued for course {course_id}"
                    },
                    status=400
                )

            template = get_object_or_404(
                CertificateTemplate,
                id=template_id,
                is_active=True
            )

            # =========================
            # TEMPLATE VALIDATION
            # =========================
            if template.course_id != int(course_id):
                return Response(
                    {
                        "error":
                            f"Template does not belong to course {course_id}"
                    },
                    status=400
                )

            # =========================
            # GENERATE CERTIFICATE NUMBER
            # =========================
            prefix_obj = CodePrefix.objects.select_for_update().filter(
                module__iexact="certificate",
                form__iexact="Issue",
                is_active=True
            ).first()

            if prefix_obj:

                prefix_obj.current_number += 1
                prefix_obj.save(update_fields=["current_number"])

                cert_no = (
                    f"{prefix_obj.prefix}"
                    f"{str(prefix_obj.current_number).zfill(5)}"
                )

            else:

                last = CertificateIssue.objects.order_by("-id").first()

                next_id = (last.id + 1) if last else 1

                cert_no = f"CERT{str(next_id).zfill(5)}"

            # =========================
            # CREATE CERTIFICATE
            # =========================
            cert = CertificateIssue.objects.create(
                student=student,
                course_id=course_id,
                batch_id=batch_id,
                template=template,

                certificate_no=cert_no,

                issue_date=issue_date,
                expiry_date=expiry_date,

                organization=student.organization,
                branch=student.branch,

                created_by=request.user
            )

            # ==========================================
            # GENERATE CERTIFICATE PDF
            # ==========================================

            html_content = build_certificate_html(
                template=template,

                student_name=student.candidate_name,

                course_name=cert.course.course_name,

                completion_date=cert.issue_date,

                batch_name=(
                    cert.batch.batch_name
                    if cert.batch
                    else ""
                )
            )

            pdf_relative_path = generate_certificate_pdf(
                cert,
                html_content
            )

            cert.certificate_pdf = pdf_relative_path

            cert.pdf_generated_at = timezone.now()

            cert.save(
                update_fields=[
                    "certificate_pdf",
                    "pdf_generated_at"
                ]
            )




            # created_certificates.append({
            #     "certificate_id": cert.id,
            #     "certificate_no": cert.certificate_no,
            #     "course_name": cert.course.course_name,
            #     "batch_name": (
            #         cert.batch.batch_name
            #         if cert.batch else None
            #     ),
            #     "template_name": cert.template.template_name
            # })

            created_certificates.append({
                "certificate_id": cert.id,

                "certificate_no": cert.certificate_no,

                "course_name": cert.course.course_name,

                "batch_name": (
                    cert.batch.batch_name
                    if cert.batch else None
                ),

                "template_name":
                    cert.template.template_name,

                "pdf_url":
                    request.build_absolute_uri(
                        cert.certificate_pdf.url
                    )
                    if cert.certificate_pdf
                    else None
            })

        # =========================
        # TOTAL FEES
        # =========================
        total_fee = FeeGeneration.objects.filter(
            admission=student,
            is_active=True
        ).aggregate(
            total=Sum("total_fee")
        )["total"] or 0

        pending_fee = FeeGeneration.objects.filter(
            admission=student,
            is_active=True
        ).aggregate(
            total=Sum("balance_amount")
        )["total"] or 0

        return Response({
            "success": True,

            "admission_id": student.id,
            "admission_code": student.admission_code,

            "student_name": student.candidate_name,
            "email": student.email,
            "mobile_no": student.mobile_no,

            "organization": (
                student.organization.name
                if student.organization else None
            ),

            "branch": (
                student.branch.name
                if student.branch else None
            ),

            "total_fee": float(total_fee),
            "pending_fee": float(pending_fee),

            "total_certificates_issued":
                len(created_certificates),

            "certificates":
                created_certificates

        }, status=201)





class CertificateDataAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, certificate_id):

        cert = get_object_or_404(
            CertificateIssue.objects.select_related(
                "student",
                "course",
                "batch",
                "template",
                "organization",
                "branch",
                "created_by",
                "updated_by"
            ),
            id=certificate_id,
            is_active=True
        )

        data = {

            # =========================
            # PRIMARY DETAILS
            # =========================
            "id": cert.id,

            "certificate_no": cert.certificate_no,

            "issue_date": cert.issue_date,
            "expiry_date": cert.expiry_date,

            "is_active": cert.is_active,

            "created_at": cert.created_at,
            "updated_at": cert.updated_at,

            # =========================
            # STUDENT DETAILS
            # =========================
            "student": cert.student.id,

            "student_name": cert.student.candidate_name,

            "admission_no": cert.student.admission_code,

            "email": cert.student.email,
            "mobile_no": cert.student.mobile_no,

            "father_name": cert.student.father_name,
            "mother_name": cert.student.mother_name,

            # =========================
            # COURSE / BATCH
            # =========================
            "course": cert.course.id,

            "course_name": cert.course.course_name,

            "batch": (
                cert.batch.id
                if cert.batch else None
            ),

            "batch_name": (
                cert.batch.batch_name
                if cert.batch else None
            ),
            

            # =========================
            # TEMPLATE
            # =========================
            "template": cert.template.id,

            "template_name": cert.template.template_name,

            # =========================
            # ORGANIZATION / BRANCH
            # =========================
            "organization": (
                cert.organization.id
                if cert.organization else None
            ),

            "organization_name": (
                cert.organization.name
                if cert.organization else None
            ),

            "branch": (
                cert.branch.id
                if cert.branch else None
            ),

            "branch_name": (
                cert.branch.name
                if cert.branch else None
            ),

            "branch_image": (
                request.build_absolute_uri(cert.branch.image.url)
                if cert.branch
                and cert.branch.image
                and hasattr(cert.branch.image, "url")
                else None
            ),

            # =========================
            # USER DETAILS
            # =========================
            "created_by": (
                cert.created_by.id
                if cert.created_by else None
            ),

            "created_by_name": (
                cert.created_by.email
                if cert.created_by else None
            ),

            "updated_by": (
                cert.updated_by.id
                if cert.updated_by else None
            ),

            "updated_by_name": (
                cert.updated_by.email
                if cert.updated_by else None
            ),

            # =========================
            # FRONTEND DISPLAY DATA
            # =========================
            "header": "CERTIFICATE OF COMPLETION",

            "recipient_name":
                cert.student.candidate_name,

            "certificate_title":
                cert.template.template_name,

            "metadata": {

                "template_id": cert.template.id,

                "student_id": cert.student.id,

                "course_id": cert.course.id,

                "batch_id": (
                    cert.batch.id
                    if cert.batch else None
                ),

                "is_verified": True
            }
        }

        return Response(
            data,
            status=status.HTTP_200_OK
        )

class DownloadCertificateAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, certificate_id):

        certificate = get_object_or_404(
            CertificateIssue,
            id=certificate_id,
            is_active=True
        )

        if not certificate.certificate_pdf:

            return Response(
                {
                    "success": False,
                    "message":
                        "PDF not generated."
                },
                status=404
            )

        return Response({
            "success": True,

            "certificate_id":
                certificate.id,

            "certificate_no":
                certificate.certificate_no,

            "pdf_url":
                request.build_absolute_uri(
                    certificate.certificate_pdf.url
                )
        })



# =========================================================
# 1. CERTIFICATE APPROVAL VIEWS
# =========================================================

class CertificateApprovalStudentSearchAPIView(APIView):
    permission_classes = [IsAuthenticated]
    """API #1: Search students for the magnifying glass modal"""
    def get(self, request):
        queryset = Admission.objects.filter(is_active=True)
        
        # Extract from query parameters
        branch_id = get_branch_id(request)  # or request.GET.get('branch_id')
        search_term = request.GET.get('search', '').strip()
        page_size = int(request.GET.get('pageSize', 10))
        page_number = request.GET.get('pageNumber', 1)
        
        if branch_id:
            queryset = queryset.filter(branch_id=branch_id)
        
        if search_term:
            queryset = queryset.filter(
                Q(admission_code__icontains=search_term) |
                Q(candidate_name__icontains=search_term) |
                Q(mobile_no__icontains=search_term)
            )
        
        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page_number)

        results = []
        for student in page_obj:
            # Calculate balance for each student in search
            balance = FeeGeneration.objects.filter(
                admission=student, is_active=True
            ).aggregate(total=Sum('balance_amount'))['total'] or 0
            
            results.append({
                "id": student.id,
                "AdmissionNo": student.admission_code,
                "Name": student.candidate_name,
                "Mobile": student.mobile_no,
                "Email": student.email,
                "Balance": balance
            })

        return Response({
            "total_records": paginator.count,
            "results": results
        })

class CertificateApprovalStudentDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]
    """API #2: Get full student + fee summary + deposit history"""
    
    def get(self, request, admissionNo):
        
        student = get_object_or_404(Admission, admission_code=admissionNo, is_active=True)
        fees = FeeGeneration.objects.filter(admission=student, is_active=True)
        billing = fees.aggregate(Sum('total_fee'))['total_fee__sum'] or 0
        balance = fees.aggregate(Sum('balance_amount'))['balance_amount__sum'] or 0
        collection = billing - balance
        deposits = FeeDeposit.objects.filter(
            installment__fee_generation__admission=student, is_active=True
        ).order_by('-payment_date')

        return Response({
            "student": {
                "id": student.id,
                "name": student.candidate_name,
                "admission_no": student.admission_code,
                "branch": student.branch.name if student.branch else None
            },
            "feeSummary": {"billing": billing, "collection": collection, "balance": balance},
            "depositHistory": [
                {"date": d.payment_date, "amount": d.paid_amount, "mode": d.payment_mode.name, "ref": d.reference_no} 
                for d in deposits
            ]
        })

class FullyPaidPendingCertificateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    """
    API:
    Get all fully paid students
    whose certificate is NOT yet approved
    """

    def get(self, request):

        admissions = Admission.objects.filter(
            is_active=True
        ).prefetch_related(
            "course_batches"
        ).select_related(
            "organization",
            "branch"
        )

        # =====================================
        # ORGANIZATION FILTER
        # =====================================

        organization_id = request.query_params.get(
            "organization"
        )

        if organization_id:

            admissions = admissions.filter(
                organization_id=organization_id
            )

        # =====================================
        # BRANCH FILTER
        # =====================================

        branch_id = request.query_params.get(
            "branch"
        )

        if branch_id:

            admissions = admissions.filter(
                branch_id=branch_id
            )

        # =========================================
        # ALREADY APPROVED ADMISSIONS
        # =========================================

        approved_admission_ids = CertificateApproval.objects.filter(
            is_active=True
        ).values_list("admission_id", flat=True)

        response_data = []

        for student in admissions:

            # =========================================
            # SKIP IF CERTIFICATE ALREADY APPROVED
            # =========================================

            if student.id in approved_admission_ids:
                continue

            # =========================================
            # TOTAL GENERATED FEE
            # =========================================

            total_fee = FeeGeneration.objects.filter(
                admission=student,
                is_active=True
            ).aggregate(
                total=Sum("total_fee")
            )["total"] or Decimal("0")

            # =========================================
            # TOTAL PAID
            # =========================================

            total_paid = FeeDeposit.objects.filter(
                installment__fee_generation__admission=student,
                is_active=True
            ).aggregate(
                total=Sum("paid_amount")
            )["total"] or Decimal("0")

            pending_amount = total_fee - total_paid

            # =========================================
            # ONLY FULLY PAID STUDENTS
            # =========================================

            if pending_amount == 0 and total_fee > 0:

                mappings = student.course_batches.filter(
                    is_active=True
                )

                course_details = []

                for mapping in mappings:

                    course_details.append({
                        "course_id": mapping.course.id,
                        "course_name": mapping.course.course_name,

                        "batch_id": mapping.batch.id,
                        "batch_name": mapping.batch.batch_name,
                    })

                response_data.append({

                    "student_id": student.id,

                    "admission_no": student.admission_code,

                    "candidate_name": student.candidate_name,

                    "mobile_no": student.mobile_no,

                    "email": student.email,

                    "organization": (
                        student.organization.name
                        if student.organization else None
                    ),

                    "branch": (
                        student.branch.name
                        if student.branch else None
                    ),

                    "total_fee": float(total_fee),

                    "total_paid": float(total_paid),

                    "pending_amount": float(pending_amount),

                    "courses": course_details
                })

        return Response({
            "count": len(response_data),
            "results": response_data
        })



class CertificateApprovalSaveAPIView(APIView):
    permission_classes = [IsAuthenticated]
    """API #3: Save approval with Zero-Balance validation"""
    def post(self, request):
        serializer = CertificateApprovalSaveSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            # Derived branch/org logic
            student = serializer.validated_data['admission']
            serializer.save(
                approved_by=request.user,
                organization=student.organization,
                branch=student.branch
            )
            return Response({
                "success": True,
                "data": CertificateApprovalSerializer(
                    serializer.instance
                ).data
            }, status=201)
        return Response(serializer.errors, status=400)


class CertificateApprovalListAPIView(APIView):
    permission_classes = [IsAuthenticated]
    """API #4: Main table for approved certificates"""
    def get(self, request):

        try:

            queryset = CertificateApproval.objects.filter(
                is_active=True
            ).order_by(
                '-created_at'
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

        except Exception as e:

            print(f'error fetching query - {e}')

            queryset = []

        paginator = Paginator(
            queryset,
            request.GET.get("pageSize", 10)
        )

        page = paginator.get_page(
            request.GET.get("pageNumber", 1)
        )

        data = []

        for obj in page:

            # =========================
            # FEES
            # =========================
            fee_qs = FeeGeneration.objects.filter(
                admission=obj.admission,
                is_active=True
            )

            total_fee = fee_qs.aggregate(
                total=Sum("total_fee")
            )["total"] or 0

            pending_fee = fee_qs.aggregate(
                total=Sum("balance_amount")
            )["total"] or 0

            amount_paid = total_fee - pending_fee

            # =========================
            # COURSE + BATCH
            # =========================
            mappings = AdmissionCourseBatch.objects.filter(
                admission=obj.admission,
                is_active=True
            ).select_related("course", "batch")

            course_batch_details = [
                {
                    "course_id": m.course.id,
                    "course_name": m.course.course_name,

                    "batch_id": m.batch.id,
                    "batch_name": m.batch.batch_name,
                }
                for m in mappings
            ]

            data.append({
                "id": obj.id,

                "admission_no": obj.admission.admission_code,
                "admission_id": obj.admission.id,
                "student_name": obj.admission.candidate_name,

                "email": obj.admission.email,
                "mobile_no": obj.admission.mobile_no,

                "organization_name": (
                    obj.organization.name
                    if obj.organization else None
                ),

                "branch_name": (
                    obj.branch.name
                    if obj.branch else None
                ),

                "approval_date": obj.approval_date,

                "approved_by": (
                    obj.approved_by.email
                    if obj.approved_by else "System"
                ),

                "remarks": obj.remarks,

                "total_fee": float(total_fee),
                "pending_fee": float(pending_fee),
                "amount_paid": float(amount_paid),

                "course_batch_details": course_batch_details
            })
        

        return Response({"total": paginator.count, "results": data})




class CertificateApprovalDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, approval_id):

        branch_id = get_branch_id(request)

        approval = get_object_or_404(
            CertificateApproval.objects.select_related(
                "admission",
                "organization",
                "branch",
                "approved_by"
            ),
            id=approval_id,
            is_active=True
        )

        # 🔐 Branch Security
        if branch_id and approval.branch_id != int(branch_id):
            return Response(
                {"error": "Unauthorized access"},
                status=403
            )

        # =========================
        # FEES
        # =========================
        fee_qs = FeeGeneration.objects.filter(
            admission=approval.admission,
            is_active=True
        )

        total_fee = fee_qs.aggregate(
            total=Sum("total_fee")
        )["total"] or 0

        pending_fee = fee_qs.aggregate(
            total=Sum("balance_amount")
        )["total"] or 0

        amount_paid = total_fee - pending_fee

        # =========================
        # COURSE + BATCH
        # =========================
        mappings = AdmissionCourseBatch.objects.filter(
            admission=approval.admission,
            is_active=True
        ).select_related("course", "batch")

        course_batch_details = [
            {
                "course_id": m.course.id,
                "course_name": m.course.course_name,

                "batch_id": m.batch.id,
                "batch_name": m.batch.batch_name,
            }
            for m in mappings
        ]

        return Response({
            "id": approval.id,

            "admission_no": approval.admission.admission_code,
            "admission_id": approval.admission.id,
            "student_name": approval.admission.candidate_name,

            "email": approval.admission.email,
            "mobile_no": approval.admission.mobile_no,

            "organization_name": (
                approval.organization.name
                if approval.organization else None
            ),

            "branch_name": (
                approval.branch.name
                if approval.branch else None
            ),

            "approval_date": approval.approval_date,

            "approved_by": (
                approval.approved_by.email
                if approval.approved_by else "System"
            ),

            "remarks": approval.remarks,

            "total_fee": float(total_fee),
            "pending_fee": float(pending_fee),
            "amount_paid": float(amount_paid),

            "course_batch_details": course_batch_details
        })





# views.py

class CertificateApprovalDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, approval_id):

        branch_id = get_branch_id(request)

        approval = get_object_or_404(
            CertificateApproval,
            id=approval_id,
            is_active=True
        )

        # =========================
        # 🔐 BRANCH SECURITY
        # =========================
        if branch_id and approval.branch_id != int(branch_id):
            return Response(
                {"error": "Unauthorized access"},
                status=403
            )

        # =========================
        # SOFT DELETE
        # =========================
        approval.is_active = False
        approval.save(update_fields=["is_active"])

        return Response({
            "success": True,
            "message": "Certificate approval deleted successfully",
            "approval_id": approval.id,
            "student_name": approval.admission.candidate_name,
            "admission_no": approval.admission.admission_code
        }, status=200)



from decimal import Decimal
from django.db.models import Sum
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

class CertificateIssueStudentListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        queryset = Admission.objects.filter(
            is_active=True
        ).prefetch_related(
            "course_batches"
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

        data = []

        for student in queryset:

            fee_generations = FeeGeneration.objects.filter(
                admission=student,
                is_active=True
            ).select_related("course")

            course_batch_details = []

            overall_total_fee = Decimal("0")
            overall_amount_paid = Decimal("0")

            # ============================================
            # COURSE WISE FEES
            # ============================================

            for fee in fee_generations:

                total_course_fee = fee.total_fee or Decimal("0")

                amount_paid = FeeDeposit.objects.filter(
                    installment__fee_generation=fee,
                    is_active=True
                ).aggregate(
                    total=Sum("paid_amount")
                )["total"] or Decimal("0")

                pending_amount = (
                    total_course_fee - amount_paid
                )

                overall_total_fee += total_course_fee
                overall_amount_paid += amount_paid

                # ============================================
                # COURSE/BATCH MAPPING
                # ============================================

                mappings = student.course_batches.filter(
                    course=fee.course,
                    is_active=True
                )

                batch_details = []

                for mapping in mappings:
                    batch_details.append({
                        "batch_id": mapping.batch.id,
                        "batch_name": mapping.batch.batch_name,
                    })

                course_batch_details.append({

                    "course_id": (
                        fee.course.id
                        if fee.course else None
                    ),

                    "course_name": (
                        fee.course.course_name
                        if fee.course else None
                    ),

                    "batches": batch_details,

                    "total_course_fee": float(total_course_fee),

                    "amount_paid": float(amount_paid),

                    "pending_amount": float(pending_amount),
                })

            overall_pending_amount = (
                overall_total_fee - overall_amount_paid
            )

            data.append({

                "StudentId": student.id,

                "AdmissionNo": student.admission_code,

                "Name": student.candidate_name,

                "mobile_no": student.mobile_no,

                "email": student.email,

                "OrganizationId": (
                    student.organization.id
                    if student.organization else None
                ),

                "OrganizationName": (
                    student.organization.name
                    if student.organization else None
                ),

                "BranchId": (
                    student.branch.id
                    if student.branch else None
                ),

                "BranchName": (
                    student.branch.name
                    if student.branch else None
                ),

                "overall_total_fee": float(overall_total_fee),

                "overall_amount_paid": float(overall_amount_paid),

                "overall_pending_amount": float(overall_pending_amount),

                "CourseBatchDetails": course_batch_details
            })

        return Response(data)


from decimal import Decimal

from django.db.models import Sum
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

# =========================================================
# ✅ STUDENTS WITH FULL PAYMENT COMPLETED
# =========================================================

class FullyPaidStudentsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        admissions = Admission.objects.filter(
            is_active=True
        ).prefetch_related(
            "course_batches"
        )

        # =====================================
        # ORGANIZATION FILTER
        # =====================================

        organization_id = request.query_params.get(
            "organization"
        )

        if organization_id:

            admissions = admissions.filter(
                organization_id=organization_id
            )

        # =====================================
        # BRANCH FILTER
        # =====================================

        branch_id = request.query_params.get(
            "branch"
        )

        if branch_id:

            admissions = admissions.filter(
                branch_id=branch_id
            )

        response_data = []

        for student in admissions:

            # =========================================
            # TOTAL GENERATED FEE
            # =========================================

            total_fee = FeeGeneration.objects.filter(
                admission=student,
                is_active=True
            ).aggregate(
                total=Sum("total_fee")
            )["total"] or Decimal("0")

            # =========================================
            # TOTAL PAID
            # =========================================

            total_paid = FeeDeposit.objects.filter(
                installment__fee_generation__admission=student,
                is_active=True
            ).aggregate(
                total=Sum("paid_amount")
            )["total"] or Decimal("0")

            pending_amount = total_fee - total_paid

            # =========================================
            # ONLY FULLY PAID
            # =========================================

            if pending_amount == 0 and total_fee > 0:

                course_details = []

                mappings = student.course_batches.filter(
                    is_active=True
                )

                for mapping in mappings:

                    course_details.append({
                        "course_id": mapping.course.id,
                        "course_name": mapping.course.course_name,

                        "batch_id": mapping.batch.id,
                        "batch_name": mapping.batch.batch_name,
                    })

                response_data.append({

                    "student_id": student.id,

                    "admission_no": student.admission_code,

                    "candidate_name": student.candidate_name,

                    "mobile_no": student.mobile_no,

                    "email": student.email,

                    "organization": (
                        student.organization.name
                        if student.organization else None
                    ),

                    "branch": (
                        student.branch.name
                        if student.branch else None
                    ),

                    "total_fee": float(total_fee),

                    "total_paid": float(total_paid),

                    "pending_amount": float(pending_amount),

                    "courses": course_details
                })

        return Response({
            "count": len(response_data),
            "results": response_data
        })





from decimal import Decimal

from django.db.models import Sum
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


# =========================================================
# ✅ STUDENTS WITH PENDING FEES
# =========================================================

class PendingFeeStudentsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        branch_id = get_branch_id(request)

        admissions = Admission.objects.filter(
            is_active=True
        ).prefetch_related(
            "course_batches"
        )

        if branch_id:
            admissions = admissions.filter(branch_id=branch_id)

        response_data = []

        for student in admissions:

            # =========================================
            # TOTAL GENERATED FEE
            # =========================================

            total_fee = FeeGeneration.objects.filter(
                admission=student,
                is_active=True
            ).aggregate(
                total=Sum("total_fee")
            )["total"] or Decimal("0")

            # =========================================
            # TOTAL PAID
            # =========================================

            total_paid = FeeDeposit.objects.filter(
                installment__fee_generation__admission=student,
                is_active=True
            ).aggregate(
                total=Sum("paid_amount")
            )["total"] or Decimal("0")

            pending_amount = total_fee - total_paid

            # =========================================
            # ONLY PENDING STUDENTS
            # =========================================

            if pending_amount > 0:

                course_details = []

                mappings = student.course_batches.filter(
                    is_active=True
                )

                for mapping in mappings:

                    course_details.append({
                        "course_id": mapping.course.id,
                        "course_name": mapping.course.course_name,

                        "batch_id": mapping.batch.id,
                        "batch_name": mapping.batch.batch_name,
                    })

                response_data.append({

                    "student_id": student.id,

                    "admission_no": student.admission_code,

                    "candidate_name": student.candidate_name,

                    "mobile_no": student.mobile_no,

                    "email": student.email,

                    "organization": (
                        student.organization.name
                        if student.organization else None
                    ),

                    "branch": (
                        student.branch.name
                        if student.branch else None
                    ),

                    "total_fee": float(total_fee),

                    "total_paid": float(total_paid),

                    "pending_amount": float(pending_amount),

                    "courses": course_details
                })

        return Response({
            "count": len(response_data),
            "results": response_data
        })



from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.response import Response
from rest_framework import status


    

class CertificateTemplateListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        course_id = request.query_params.get("course_id")

        templates = CertificateTemplate.objects.filter(
            is_active=True
        )

        # =========================
        # FILTER BY COURSE
        # =========================
        if course_id:
            templates = templates.filter(course_id=course_id)

        serializer = CertificateTemplateSerializer(
            templates,
            many=True,
            context={"request": request}
        )

        return Response(serializer.data)

    # def post(self, request):

    #     serializer = CertificateTemplateSerializer(data=request.data)

    #     if serializer.is_valid():

    #         try:
    #             serializer.save()

    #             return Response(
    #                 serializer.data,
    #                 status=status.HTTP_201_CREATED
    #             )

    #         except DjangoValidationError as e:

    #             return Response(
    #                 {
    #                     "success": False,
    #                     "errors": e.message_dict
    #                 },
    #                 status=status.HTTP_400_BAD_REQUEST
    #             )

    #     return Response(
    #         serializer.errors,
    #         status=status.HTTP_400_BAD_REQUEST
    #     )

    def post(self, request):

        serializer = CertificateTemplateSerializer(
            data=request.data,
            context={"request": request}
        )

        if serializer.is_valid():

            course = serializer.validated_data.get("course")

            if not course:
                return Response(
                    {
                        "success": False,
                        "message": "Course is required."
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            branch = course.branch

            existing_template = CertificateTemplate.objects.filter(
                course__branch=branch,
                is_active=True
            ).first()

            # ======================================
            # TEMPLATE ALREADY EXISTS
            # ======================================

            if existing_template:

                return Response(
                    {
                        "success": False,
                        "overwrite_required": True,
                        "existing_template_id": existing_template.id,
                        "message":
                            "A template already exists. Do you want to overwrite it?"
                    },
                    status=status.HTTP_409_CONFLICT
                )

            try:

                serializer.save()

                return Response(
                    {
                        "success": True,
                        "message":
                            "Certificate template saved successfully.",
                        "data": serializer.data
                    },
                    status=status.HTTP_201_CREATED
                )

            except DjangoValidationError as e:

                return Response(
                    {
                        "success": False,
                        "errors": e.message_dict
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )



class CertificateTemplateDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):

        return get_object_or_404(
            CertificateTemplate,
            pk=pk,
            is_active=True
        )

    # =========================
    # GET SINGLE TEMPLATE
    # =========================
    def get(self, request, pk):

        template = self.get_object(pk)

        #serializer = CertificateTemplateSerializer(template)

        serializer = CertificateTemplateSerializer(
            template,
            context={"request": request}
        )

        return Response(serializer.data)


    # def put(self, request, pk):

    #     template = self.get_object(pk)

    #     serializer = CertificateTemplateSerializer(
    #         template,
    #         data=request.data,
    #         partial=True
    #     )

    #     if serializer.is_valid():

    #         try:
    #             serializer.save()

    #             return Response(
    #                 serializer.data,
    #                 status=status.HTTP_200_OK
    #             )

    #         except DjangoValidationError as e:

    #             return Response(
    #                 {
    #                     "success": False,
    #                     "errors": e.message_dict
    #                 },
    #                 status=status.HTTP_400_BAD_REQUEST
    #             )

    #     return Response(
    #         serializer.errors,
    #         status=status.HTTP_400_BAD_REQUEST
    #     )

    def put(self, request, pk):

        template = self.get_object(pk)

        serializer = CertificateTemplateSerializer(
            template,
            data=request.data,
            partial=True,
            context={"request": request}
        )

        if serializer.is_valid():

            try:

                serializer.save()

                return Response(
                    {
                        "success": True,
                        "message":
                            "Certificate template updated successfully.",
                        "data": serializer.data
                    },
                    status=status.HTTP_200_OK
                )

            except DjangoValidationError as e:

                return Response(
                    {
                        "success": False,
                        "errors": e.message_dict
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


    def delete(self, request, pk):

        template = self.get_object(pk)

        template.is_active = False
        template.save()

        return Response(
            {
                "message":
                    "Certificate template deleted successfully"
            },
            status=status.HTTP_200_OK
        )



from datetime import date
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


class CertificateTemplatePreviewAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        body_text = request.data.get("body_text", "")

        preview_text = (
            body_text
            .replace("{{student_name}}", "John Doe")
            .replace("{{course_name}}", "Sample Course")
            .replace(
                "{{completion_date}}",
                date.today().strftime("%d-%m-%Y")
            )
            .replace("{{batch_name}}", "Batch A")
        )

        return Response(
            {
                "success": True,

                "preview": {
                    "student_name": "John Doe",
                    "course_name": "Sample Course",
                    "completion_date":
                        date.today().strftime("%d-%m-%Y"),
                    "batch_name": "Batch A",

                    "certificate_title":
                        request.data.get(
                            "certificate_title",
                            "Certificate of Completion"
                        ),

                    "institute_name":
                        request.data.get(
                            "institute_name",
                            ""
                        ),

                    "body_text":
                        preview_text,

                    "logo_position":
                        request.data.get(
                            "logo_position"
                        ),

                    "stamp_position":
                        request.data.get(
                            "stamp_position"
                        ),

                    "border_style":
                        request.data.get(
                            "border_style"
                        ),

                    "background_type":
                        request.data.get(
                            "background_type"
                        )
                }
            }
        )

class BranchCertificateTemplateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, branch_id):

        template = CertificateTemplate.objects.filter(
            course__branch_id=branch_id,
            is_active=True
        ).first()

        if not template:
            return Response(
                {
                    "success": False,
                    "message": "No certificate template found for this branch."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = CertificateTemplateSerializer(
            template,
            context={"request": request}
        )

        return Response(
            {
                "success": True,
                "data": serializer.data
            }
        )

class CurrentBranchCertificateTemplateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        branch_id = get_branch_id(request)

        template = CertificateTemplate.objects.filter(
            course__branch_id=branch_id,
            is_active=True
        ).first()

        if not template:
            return Response(
                {
                    "success": False,
                    "message": "No certificate template found."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = CertificateTemplateSerializer(
            template,
            context={"request": request}
        )

        return Response(serializer.data)

from django.core.paginator import Paginator
from django.db.models import Sum
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

class CertificateIssueListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    """
    List certificates grouped by Admission
    """

    def get(self, request):

        queryset = CertificateIssue.objects.filter(
            is_active=True
        ).select_related(
            "student",
            "course",
            "batch",
            "template",
            "organization",
            "branch"
        ).order_by("-created_at")

        # =====================================
        # ORGANIZATION FILTER
        # =====================================

        organization_id = request.query_params.get(
            "organization"
        )

        if organization_id:

            queryset = queryset.filter(
                organization_id=organization_id
            )

        # =====================================
        # BRANCH FILTER
        # =====================================

        branch_id = request.query_params.get(
            "branch"
        )

        if branch_id:

            queryset = queryset.filter(
                branch_id=branch_id
            )

        # =========================
        # GROUP BY STUDENT
        # =========================
        grouped_data = {}

        for cert in queryset:

            student = cert.student

            if student.id not in grouped_data:

                # =========================
                # FEE DETAILS
                # =========================
                total_fee = FeeGeneration.objects.filter(
                    admission=student,
                    is_active=True
                ).aggregate(
                    total=Sum("total_fee")
                )["total"] or 0

                pending_fee = FeeGeneration.objects.filter(
                    admission=student,
                    is_active=True
                ).aggregate(
                    total=Sum("balance_amount")
                )["total"] or 0

                grouped_data[student.id] = {

                    "admission_id": student.id,
                    "admission_code": student.admission_code,

                    "student_name": student.candidate_name,
                    "email": student.email,
                    "mobile_no": student.mobile_no,

                    "organization": (
                        student.organization.name
                        if student.organization else None
                    ),

                    "branch": (
                        student.branch.name
                        if student.branch else None
                    ),

                    "total_fee": float(total_fee),
                    "pending_fee": float(pending_fee),

                    "total_certificates": 0,

                    "certificates": []
                }

            # =========================
            # APPEND CERTIFICATE
            # =========================
            grouped_data[student.id]["certificates"].append({

                "certificate_id": cert.id,

                "certificate_no": cert.certificate_no,

                # "course_id": cert.course.id,
                # "course_name": cert.course.course_name,
                "course_id": (
                    cert.course.id
                    if cert.course else None
                ),

                "course_name": (
                    cert.course.course_name
                    if cert.course else None
                ),

                "batch_id": cert.batch.id if cert.batch else None,
                "batch_name": (
                    cert.batch.batch_name
                    if cert.batch else None
                ),

                "template_id": cert.template.id,
                "template_name": cert.template.template_name,

                "issue_date": cert.issue_date,
                "expiry_date": cert.expiry_date,
            })

            grouped_data[student.id]["total_certificates"] += 1

        # =========================
        # PAGINATION
        # =========================
        grouped_list = list(grouped_data.values())

        paginator = Paginator(
            grouped_list,
            request.GET.get("pageSize", 10)
        )

        page = paginator.get_page(
            request.GET.get("pageNumber", 1)
        )

        return Response({
            "total": paginator.count,
            "results": list(page)
        })





class CertificateIssueDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]
    """Issue API #5: Get for Edit"""
    def get_object(self, certificateId):
        return get_object_or_404(
            CertificateIssue,
            id=certificateId,
            is_active=True
        )

    def get(self, request, certificateId):
        cert = get_object_or_404(CertificateIssue, id=certificateId, is_active=True)
        serializer = CertificateIssueSerializer(cert)
        return Response(serializer.data)

    def put(self, request, certificateId):
        """Full update"""
        cert = self.get_object(certificateId)
        serializer = CertificateIssueSerializer(cert, data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, certificateId):
        """Partial update"""
        cert = self.get_object(certificateId)
        serializer = CertificateIssueSerializer(cert, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# class CertificateIssueDeleteAPIView(APIView):
#     permission_classes = [IsAuthenticated]
#     """Issue API #6: Soft Delete"""
#     def delete(self, request, certificateId):
#         cert = get_object_or_404(CertificateIssue, id=certificateId)
#         cert.is_active = False
#         cert.save()
#         return Response({"success": True})
        
class CertificateIssueDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, certificateId):

        cert = get_object_or_404(
            CertificateIssue,
            id=certificateId,
            is_active=True
        )

        cert.is_active = False
        cert.updated_by = request.user
        cert.save()

        return Response({
            "success": True,
            "message": "Certificate deleted successfully",
            "certificate_id": cert.id,
            "certificate_no": cert.certificate_no,
            "student": cert.student.candidate_name,
            "course": cert.course.course_name
        }, status=200)


from django.db.models import Sum
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

class PendingCertificateIssueListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    """
    List:
    1. Approved students with NO certificates issued
    2. Approved students with PARTIAL certificates issued
    """

    def get(self, request):

        approvals = CertificateApproval.objects.filter(
            is_active=True
        ).select_related(
            "admission",
            "organization",
            "branch"
        )

        # =====================================
        # ORGANIZATION FILTER
        # =====================================

        organization_id = request.query_params.get(
            "organization"
        )

        if organization_id:

            approvals = approvals.filter(
                organization_id=organization_id
            )

        # =====================================
        # BRANCH FILTER
        # =====================================

        branch_id = request.query_params.get(
            "branch"
        )

        if branch_id:

            approvals = approvals.filter(
                branch_id=branch_id
            )

        response_data = []

        for approval in approvals:

            student = approval.admission

            # =========================
            # TOTAL ASSIGNED COURSES
            # =========================
            course_batches = AdmissionCourseBatch.objects.filter(
                admission=student,
                is_active=True
            ).select_related(
                "course",
                "batch"
            )

            total_courses = course_batches.count()

            # =========================
            # ISSUED CERTIFICATES
            # =========================
            issued_certificates = CertificateIssue.objects.filter(
                student=student,
                is_active=True
            )

            issued_count = issued_certificates.count()

            # =========================
            # PENDING CASES ONLY
            # =========================
            if issued_count >= total_courses:
                continue

            # =========================
            # FEE DETAILS
            # =========================
            total_fee = FeeGeneration.objects.filter(
                admission=student,
                is_active=True
            ).aggregate(
                total=Sum("total_fee")
            )["total"] or 0

            pending_fee = FeeGeneration.objects.filter(
                admission=student,
                is_active=True
            ).aggregate(
                total=Sum("balance_amount")
            )["total"] or 0

            # =========================
            # COURSE DETAILS
            # =========================
            course_data = []

            for cb in course_batches:

                # Check certificate issued or not
                issued = CertificateIssue.objects.filter(
                    student=student,
                    course=cb.course,
                    batch=cb.batch,
                    is_active=True
                ).exists()

                course_data.append({
                    "course_id": cb.course.id,
                    "course_name": cb.course.course_name,

                    "batch_id": cb.batch.id if cb.batch else None,
                    "batch_name": (
                        cb.batch.batch_name
                        if cb.batch else None
                    ),

                    "certificate_issued": issued
                })

            # =========================
            # FINAL RESPONSE
            # =========================
            response_data.append({

                "approval_id": approval.id,

                "admission_id": student.id,
                "admission_code": student.admission_code,

                "student_name": student.candidate_name,
                "email": student.email,
                "mobile_no": student.mobile_no,

                "organization": (
                    student.organization.name
                    if student.organization else None
                ),

                "branch": (
                    student.branch.name
                    if student.branch else None
                ),

                "approval_date": approval.approval_date,

                "total_fee": float(total_fee),
                "pending_fee": float(pending_fee),

                "total_courses": total_courses,
                "issued_certificates": issued_count,
                "pending_certificates":
                    total_courses - issued_count,

                "courses": course_data
            })

        return Response({
            "count": len(response_data),
            "results": response_data
        })





#Not updated

class StudentCourseListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, student_id):

        mappings = AdmissionCourseBatch.objects.filter(
            admission_id=student_id,
            is_active=True
        ).select_related("course", "batch")

        data = [
            {
                "course_id": m.course.id,
                "course_name": m.course.course_name,

                "batch_id": m.batch.id if m.batch else None,
                "batch_name": (
                    m.batch.batch_name
                    if m.batch else None
                )
            }
            for m in mappings
        ]

        return Response(data)


from datetime import timedelta

from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Admission


class AdmissionDashboardCountAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        organization_id = request.query_params.get(
            "organization_id"
        )

        branch_id = request.query_params.get(
            "branch_id"
        )

        queryset = Admission.objects.filter(
            is_active=True
        )

        # =====================================
        # ORGANIZATION FILTER
        # =====================================

        if organization_id:

            queryset = queryset.filter(
                organization_id=organization_id
            )

        # =====================================
        # BRANCH FILTER
        # =====================================

        if branch_id:

            queryset = queryset.filter(
                branch_id=branch_id
            )

        # =====================================
        # TODAY
        # =====================================

        today = timezone.localdate()

        # =====================================
        # WEEK (SUNDAY → SATURDAY)
        # =====================================

        days_from_sunday = (
            today.weekday() + 1
        ) % 7

        week_start = today - timedelta(
            days=days_from_sunday
        )

        week_end = week_start + timedelta(
            days=6
        )

        # =====================================
        # MONTH
        # =====================================

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

        return Response({

            "success": True,

            "filters": {

                "organization_id":
                    organization_id,

                "branch_id":
                    branch_id
            },

            "counts": {

                "total_admissions":
                    total_count,

                "today_admissions":
                    today_count,

                "week_admissions":
                    week_count,

                "month_admissions":
                    month_count
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
from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from admission.models import Admission
from admission.models import CertificateApproval
from fee_details.models import FeeGeneration, FeeDeposit


class CertificateApprovalDashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        organization_id = request.query_params.get(
            "organization_id"
        )

        branch_id = request.query_params.get(
            "branch_id"
        )

        # =====================================
        # DATE RANGES
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
        # APPROVED QUERYSET
        # =====================================

        approved_qs = CertificateApproval.objects.filter(
            is_active=True
        )

        if organization_id:
            approved_qs = approved_qs.filter(
                organization_id=organization_id
            )

        if branch_id:
            approved_qs = approved_qs.filter(
                branch_id=branch_id
            )

        approved_total = approved_qs.count()

        approved_today = approved_qs.filter(
            created_at__date=today
        ).count()

        approved_week = approved_qs.filter(
            created_at__date__range=[
                week_start,
                week_end
            ]
        ).count()

        approved_month = approved_qs.filter(
            created_at__date__gte=month_start
        ).count()

        # =====================================
        # PENDING CERTIFICATE APPROVALS
        # =====================================

        admissions = Admission.objects.filter(
            is_active=True
        )

        if organization_id:
            admissions = admissions.filter(
                organization_id=organization_id
            )

        if branch_id:
            admissions = admissions.filter(
                branch_id=branch_id
            )

        approved_ids = set(
            CertificateApproval.objects.filter(
                is_active=True
            ).values_list(
                "admission_id",
                flat=True
            )
        )

        pending_total = 0
        pending_today = 0
        pending_week = 0
        pending_month = 0

        for student in admissions:

            if student.id in approved_ids:
                continue

            total_fee = FeeGeneration.objects.filter(
                admission=student,
                is_active=True
            ).aggregate(
                total=Sum("total_fee")
            )["total"] or Decimal("0")

            total_paid = FeeDeposit.objects.filter(
                installment__fee_generation__admission=student,
                is_active=True
            ).aggregate(
                total=Sum("paid_amount")
            )["total"] or Decimal("0")

            pending_amount = total_fee - total_paid

            if (
                pending_amount == 0
                and total_fee > 0
            ):

                pending_total += 1

                admission_date = (
                    student.admission_date
                )

                if admission_date == today:
                    pending_today += 1

                if (
                    week_start
                    <= admission_date
                    <= week_end
                ):
                    pending_week += 1

                if (
                    admission_date.month
                    == today.month
                    and admission_date.year
                    == today.year
                ):
                    pending_month += 1

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

            "pending_certificate_approvals": {

                "total":
                    pending_total,

                "today":
                    pending_today,

                "week":
                    pending_week,

                "month":
                    pending_month
            },

            "approved_certificates": {

                "total":
                    approved_total,

                "today":
                    approved_today,

                "week":
                    approved_week,

                "month":
                    approved_month
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

from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from admission.models import AdmissionCourseBatch
from admission.models import (
    CertificateApproval,
    CertificateIssue
)


class CertificateIssueDashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        organization_id = request.query_params.get(
            "organization_id"
        )

        branch_id = request.query_params.get(
            "branch_id"
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
        # APPROVED STUDENTS
        # =====================================

        approvals = CertificateApproval.objects.filter(
            is_active=True
        ).select_related(
            "admission"
        )

        if organization_id:

            approvals = approvals.filter(
                organization_id=organization_id
            )

        if branch_id:

            approvals = approvals.filter(
                branch_id=branch_id
            )

        # =====================================
        # PENDING TO ISSUE COUNTS
        # =====================================

        pending_total = 0
        pending_today = 0
        pending_week = 0
        pending_month = 0

        for approval in approvals:

            student = approval.admission

            total_courses = AdmissionCourseBatch.objects.filter(
                admission=student,
                is_active=True
            ).count()

            issued_count = CertificateIssue.objects.filter(
                student=student,
                is_active=True
            ).count()

            # Fully issued -> skip
            if issued_count >= total_courses:
                continue

            pending_total += 1

            approval_date = approval.approval_date

            if approval_date == today:
                pending_today += 1

            if (
                week_start
                <= approval_date
                <= week_end
            ):
                pending_week += 1

            if (
                approval_date.month == today.month
                and approval_date.year == today.year
            ):
                pending_month += 1

        # =====================================
        # ISSUED CERTIFICATES
        # =====================================

        issued_qs = CertificateIssue.objects.filter(
            is_active=True
        )

        if organization_id:

            issued_qs = issued_qs.filter(
                organization_id=organization_id
            )

        if branch_id:

            issued_qs = issued_qs.filter(
                branch_id=branch_id
            )

        issued_total = issued_qs.count()

        issued_today = issued_qs.filter(
            issue_date=today
        ).count()

        issued_week = issued_qs.filter(
            issue_date__range=[
                week_start,
                week_end
            ]
        ).count()

        issued_month = issued_qs.filter(
            issue_date__gte=month_start
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

            "pending_to_issue": {

                "total":
                    pending_total,

                "today":
                    pending_today,

                "week":
                    pending_week,

                "month":
                    pending_month
            },

            "issued_certificates": {

                "total":
                    issued_total,

                "today":
                    issued_today,

                "week":
                    issued_week,

                "month":
                    issued_month
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

from django.db.models import Count, Q
from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Attendance


class AttendanceDashboardAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        organization_id = request.query_params.get(
            "organization_id"
        )

        branch_id = request.query_params.get(
            "branch_id"
        )

        admission_id = request.query_params.get(
            "admission_id"
        )

        queryset = Attendance.objects.select_related(
            "admission"
        ).filter(
            is_active=True,
            admission__is_active=True
        )

        # =====================================
        # ORGANIZATION FILTER
        # =====================================

        if organization_id:

            queryset = queryset.filter(
                admission__organization_id=
                organization_id
            )

        # =====================================
        # BRANCH FILTER
        # =====================================

        if branch_id:

            queryset = queryset.filter(
                admission__branch_id=
                branch_id
            )

        # =====================================
        # BATCH FILTER
        # =====================================

        batch_id = request.query_params.get(
            "batch_id"
        )

        if batch_id:

            queryset = queryset.filter(
                admission__course_batches__batch_id=batch_id,
                admission__course_batches__is_active=True
            ).distinct()

        # =====================================
        # STUDENT FILTER
        # =====================================

        if admission_id:

            queryset = queryset.filter(
                admission_id=admission_id
            )

        # =====================================
        # DATE RANGE
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
        # OVERALL
        # =====================================

        total_records = queryset.count()

        total_present = queryset.filter(
            present=True
        ).count()

        total_absent = queryset.filter(
            present=False
        ).count()

        attendance_percentage = 0

        if total_records > 0:

            attendance_percentage = round(
                (total_present / total_records) * 100,
                2
            )

        # =====================================
        # TODAY
        # =====================================

        today_queryset = queryset.filter(
            date=today
        )

        # =====================================
        # WEEK
        # =====================================

        week_queryset = queryset.filter(
            date__range=[
                week_start,
                week_end
            ]
        )

        # =====================================
        # MONTH
        # =====================================

        month_queryset = queryset.filter(
            date__gte=month_start
        )

        return Response({

            "success": True,

            "filters": {

                "organization_id":
                    organization_id,

                "branch_id":
                    branch_id,

                "admission_id":
                    admission_id
            },

            "overall": {

                "total_records":
                    total_records,

                "present":
                    total_present,

                "absent":
                    total_absent,

                "attendance_percentage":
                    attendance_percentage
            },

            "today": {

                "total":
                    today_queryset.count(),

                "present":
                    today_queryset.filter(
                        present=True
                    ).count(),

                "absent":
                    today_queryset.filter(
                        present=False
                    ).count()
            },

            "week": {

                "total":
                    week_queryset.count(),

                "present":
                    week_queryset.filter(
                        present=True
                    ).count(),

                "absent":
                    week_queryset.filter(
                        present=False
                    ).count()
            },

            "month": {

                "total":
                    month_queryset.count(),

                "present":
                    month_queryset.filter(
                        present=True
                    ).count(),

                "absent":
                    month_queryset.filter(
                        present=False
                    ).count()
            }
        })


