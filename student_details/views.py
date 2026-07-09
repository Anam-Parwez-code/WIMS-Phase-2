from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework import serializers
from .models import Enquiry, EnquiryFollowUp, Registration
from .serializers import EnquirySerializer, EnquiryFollowUpSerializer, RegistrationSerializer
from django.shortcuts import get_object_or_404
from django.db.models import Q
from core.logging_utils import log_audit, log_activity, log_error
import pandas as pd
import io
import csv
from django.http import HttpResponse
from rest_framework.parsers import MultiPartParser, FormParser
from core.permissions import IsSuperAdminOrClientAdmin
from rest_framework.permissions import IsAuthenticated


# ------------------ Enquiry -------------------
class EnquiryAPIView(APIView):
    #permission_classes = [IsSuperAdminOrClientAdmin]
    permission_classes = [IsAuthenticated]
    def get(self, request, pk=None):
        try:
            if pk:
                enquiry = get_object_or_404(
                    Enquiry,
                    pk=pk
                )

                serializer = EnquirySerializer(enquiry)

                log_activity(
                    request,
                    f"Viewed enquiry {pk}"
                )

                return Response(serializer.data)

            include_inactive = (
                request.query_params.get(
                    "include_inactive",
                    "false"
                ).lower() == "true"
            )

            queryset = (
                Enquiry.objects.all()
                if include_inactive
                else Enquiry.objects.filter(
                    is_active=True
                )
            )

            # =====================================
            # ORGANIZATION FILTER
            # =====================================

            organization_id = request.query_params.get(
                "organization"
            )

            if organization_id:

                queryset = queryset.filter(
                    courses__organization_id=organization_id
                )

            # =====================================
            # BRANCH FILTER
            # =====================================

            branch_id = request.query_params.get(
                "branch"
            )

            if branch_id:

                queryset = queryset.filter(
                    courses__branch_id=branch_id
                )

            # =====================================
            # SEARCH
            # =====================================

            search = request.query_params.get(
                "search"
            )

            if search:

                queryset = queryset.filter(
                    Q(candidate_name__icontains=search) |
                    Q(enquiry_code__icontains=search) |
                    Q(mobile_no__icontains=search)
                )

            queryset = queryset.distinct()

            serializer = EnquirySerializer(
                queryset,
                many=True
            )

            log_activity(
                request,
                "Viewed enquiry list"
            )

            return Response(serializer.data)

        except Exception as e:

            log_error(
                request,
                "EnquiryAPIView.get",
                str(e),
                e
            )

            return Response(
                {"error": "An error occurred"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
    def post(self, request):
        try:
            serializer = EnquirySerializer(data=request.data, context={'request': request})
            if serializer.is_valid():
                enquiry = serializer.save()
                log_audit(request, "Create", f"Created enquiry {enquiry.enquiry_code}", "Enquiry", "Mst_Enquiry", enquiry.id)
                log_activity(request, f"Added new enquiry {enquiry.enquiry_code}")
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            log_error(request, "EnquiryAPIView.post", str(e), e)
            return Response({"error": "An error occurred"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request, pk):
        try:
            enquiry = get_object_or_404(Enquiry, pk=pk, is_active=True)
            serializer = EnquirySerializer(enquiry, data=request.data, partial=True, context={'request': request})
            if serializer.is_valid():
                serializer.save()
                log_audit(request, "Update", f"Updated enquiry {enquiry.enquiry_code}", "Enquiry", "Mst_Enquiry", enquiry.id)
                log_activity(request, f"Updated enquiry {enquiry.enquiry_code}")
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            log_error(request, "EnquiryAPIView.put", str(e), e)
            return Response({"error": "An error occurred"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request, pk):
        try:
            enquiry = get_object_or_404(Enquiry, pk=pk, is_active=True)
            enquiry.is_active = False
            enquiry.save()
            log_audit(request, "Delete", f"Soft deleted enquiry {enquiry.enquiry_code}", "Enquiry", "Mst_Enquiry", enquiry.id)
            log_activity(request, f"Deleted enquiry {enquiry.enquiry_code}")
            return Response({"message":"Deleted Successfully"}, status=status.HTTP_200_OK)
        except Exception as e:
            log_error(request, "EnquiryAPIView.delete", str(e), e)
            return Response({"error": "An error occurred"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ------------------ EnquiryFollowUp -------------------
class EnquiryFollowUpDetailAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, enquiry_id):

        enquiry = get_object_or_404(
            Enquiry,
            id=enquiry_id,
            is_active=True
        )

        data = {

            "enquiry": enquiry.id,

            "enquiry_code":
            enquiry.enquiry_code,

            "enquiry_date":
            enquiry.enquiry_date,

            "client_name":
            enquiry.candidate_name,

            "email":
            enquiry.email,

            "mobile_no":
            enquiry.mobile_no,

            "address":
            enquiry.address,

            # Editable
            "assigned_to":
            enquiry.assigned_to.id
            if enquiry.assigned_to else None,

            "assigned_to_name":
            enquiry.assigned_to.name
            if enquiry.assigned_to else None,
        }

        return Response({
            "success": True,
            "result": data
        })

# views.py

class EnquiryFollowUpSaveAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        followup_id = request.data.get("id")

        if followup_id:

            followup = get_object_or_404(
                EnquiryFollowUp,
                id=followup_id,
                is_active=True
            )

            serializer = EnquiryFollowUpSerializer(
                followup,
                data=request.data,
                partial=True,
                context={"request": request}
            )

        else:

            serializer = EnquiryFollowUpSerializer(
                data=request.data,
                context={"request": request}
            )

        if serializer.is_valid():

            followup = serializer.save()

            return Response({
                "success": True,
                "followupId": followup.id
            })

        return Response(
            serializer.errors,
            status=400
        )


# views.py

# class EnquiryFollowUpListAPIView(APIView):

#     permission_classes = [IsAuthenticated]

#     def get(self, request):

#         enquiry_id = request.query_params.get("enquiry")

#         status_id = request.query_params.get("status")

#         interest_level_id = request.query_params.get(
#             "interest_level"
#         )

#         # =====================================
#         # DATE FILTERS
#         # =====================================

#         next_followup_from = request.query_params.get(
#             "next_followup_from"
#         )

#         next_followup_to = request.query_params.get(
#             "next_followup_to"
#         )

#         single_date = request.query_params.get(
#             "single_date"
#         )

#         # =====================================
#         # BASE QUERY
#         # =====================================

#         followups = EnquiryFollowUp.objects.filter(
#             is_active=True
#         )

#         # =====================================
#         # FILTER BY ENQUIRY
#         # =====================================

#         if enquiry_id:

#             followups = followups.filter(
#                 enquiry_id=enquiry_id
#             )

#         # =====================================
#         # FILTER BY STATUS
#         # =====================================

#         if status_id:

#             followups = followups.filter(
#                 status_id=status_id
#             )

#         # =====================================
#         # FILTER BY INTEREST LEVEL
#         # =====================================

#         if interest_level_id:

#             followups = followups.filter(
#                 interest_level_id=interest_level_id
#             )

#         # =====================================
#         # SINGLE DATE FILTER
#         # =====================================

#         if single_date:

#             followups = followups.filter(
#                 next_followup_date=single_date
#             )

#         # =====================================
#         # DATE RANGE FILTER
#         # =====================================

#         if (
#             next_followup_from
#             and next_followup_to
#         ):

#             followups = followups.filter(
#                 next_followup_date__range=[
#                     next_followup_from,
#                     next_followup_to
#                 ]
#             )

#         elif next_followup_from:

#             followups = followups.filter(
#                 next_followup_date__gte=
#                 next_followup_from
#             )

#         elif next_followup_to:

#             followups = followups.filter(
#                 next_followup_date__lte=
#                 next_followup_to
#             )

#         # =====================================
#         # ORDERING
#         # =====================================

#         followups = followups.order_by(
#             "next_followup_date"
#         )

#         # =====================================
#         # SERIALIZER
#         # =====================================

#         serializer = EnquiryFollowUpSerializer(
#             followups,
#             many=True
#         )

#         return Response({
#             "count": followups.count(),
#             "results": serializer.data
#         })

class EnquiryFollowUpListAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        enquiry_id = request.query_params.get("enquiry")

        status_id = request.query_params.get("status")

        interest_level_id = request.query_params.get(
            "interest_level"
        )

        organization_id = request.query_params.get(
            "organization"
        )

        branch_id = request.query_params.get(
            "branch"
        )

        # =====================================
        # DATE FILTERS
        # =====================================

        next_followup_from = request.query_params.get(
            "next_followup_from"
        )

        next_followup_to = request.query_params.get(
            "next_followup_to"
        )

        single_date = request.query_params.get(
            "single_date"
        )

        # =====================================
        # BASE QUERY
        # =====================================

        followups = EnquiryFollowUp.objects.filter(
            is_active=True
        ).select_related(
            "enquiry",
            "status",
            "interest_level",
            "assigned_to",
            "followup_medium"
        ).prefetch_related(
            "enquiry__courses"
        )

        # =====================================
        # ORGANIZATION FILTER
        # =====================================

        if organization_id:

            followups = followups.filter(
                enquiry__courses__organization_id=
                organization_id
            )

        # =====================================
        # BRANCH FILTER
        # =====================================

        if branch_id:

            followups = followups.filter(
                enquiry__courses__branch_id=
                branch_id
            )

        # =====================================
        # FILTER BY ENQUIRY
        # =====================================

        if enquiry_id:

            followups = followups.filter(
                enquiry_id=enquiry_id
            )

        # =====================================
        # FILTER BY STATUS
        # =====================================

        if status_id:

            followups = followups.filter(
                status_id=status_id
            )

        # =====================================
        # FILTER BY INTEREST LEVEL
        # =====================================

        if interest_level_id:

            followups = followups.filter(
                interest_level_id=interest_level_id
            )

        # =====================================
        # SINGLE DATE FILTER
        # =====================================

        if single_date:

            followups = followups.filter(
                next_followup_date=single_date
            )

        # =====================================
        # DATE RANGE FILTER
        # =====================================

        if (
            next_followup_from
            and next_followup_to
        ):

            followups = followups.filter(
                next_followup_date__range=[
                    next_followup_from,
                    next_followup_to
                ]
            )

        elif next_followup_from:

            followups = followups.filter(
                next_followup_date__gte=
                next_followup_from
            )

        elif next_followup_to:

            followups = followups.filter(
                next_followup_date__lte=
                next_followup_to
            )

        # =====================================
        # REMOVE DUPLICATES
        # =====================================

        followups = followups.distinct()

        # =====================================
        # ORDERING
        # =====================================

        followups = followups.order_by(
            "next_followup_date"
        )

        # =====================================
        # SERIALIZER
        # =====================================

        serializer = EnquiryFollowUpSerializer(
            followups,
            many=True
        )

        return Response({
            "count": followups.count(),
            "results": serializer.data
        })

# ------------------ Registration -------------------

class RegistrationAPIView(APIView):
    #permission_classes = [IsSuperAdminOrClientAdmin]
    permission_classes = [IsAuthenticated]
    def get(self, request, pk=None):
        try:

            if pk:

                reg = get_object_or_404(
                    Registration,
                    pk=pk
                )

                serializer = RegistrationSerializer(reg)

                log_activity(
                    request,
                    f"Viewed registration {pk}"
                )

                return Response(serializer.data)

            include_inactive = (
                request.query_params.get(
                    "include_inactive",
                    "false"
                ).lower() == "true"
            )

            queryset = (
                Registration.objects.all()
                if include_inactive
                else Registration.objects.filter(
                    is_active=True
                )
            )

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

            # =====================================
            # BATCH FILTER
            # =====================================

            batch_id = request.query_params.get(
                "batch_id"
            )

            if batch_id:

                queryset = queryset.filter(
                    batch_id=batch_id
                )

            # =====================================
            # SEARCH FILTER
            # =====================================

            search = request.query_params.get(
                "search"
            )

            if search:

                queryset = queryset.filter(

                    Q(candidate_name__icontains=search) |

                    Q(registration_code__icontains=search) |

                    Q(mobile_no__icontains=search) |

                    Q(aadhar_no__icontains=search)
                )

            queryset = queryset.order_by(
                "-created_at"
            )

            serializer = RegistrationSerializer(
                queryset,
                many=True
            )

            log_activity(
                request,
                "Viewed registration list"
            )

            return Response(serializer.data)

        except Exception as e:

            log_error(
                request,
                "RegistrationAPIView.get",
                str(e),
                e
            )

            return Response(
                {"error": "An error occurred"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        

    def post(self, request):
        try:
            serializer = RegistrationSerializer(data=request.data, context={'request': request})
            if serializer.is_valid():
                reg = serializer.save()
                log_audit(request, "Create", f"Created registration {reg.registration_code}", "Registration", "Mst_Registration", reg.id)
                log_activity(request, f"Added new registration {reg.registration_code}")
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except serializers.ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            log_error(request, "RegistrationAPIView.post", str(e), e)
            return Response({"error": "An error occurred"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request, pk):
        try:
            reg = get_object_or_404(Registration, pk=pk, is_active=True)
            serializer = RegistrationSerializer(reg, data=request.data, partial=True, context={'request': request})
            if serializer.is_valid():
                serializer.save()
                log_audit(request, "Update", f"Updated registration {reg.registration_code}", "Registration", "Mst_Registration", reg.id)
                log_activity(request, f"Updated registration {reg.registration_code}")
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            log_error(request, "RegistrationAPIView.put", str(e), e)
            return Response({"error": "An error occurred"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request, pk):
        try:
            reg = get_object_or_404(Registration, pk=pk, is_active=True)
            reg.is_active = False
            reg.save()
            log_audit(request, "Delete", f"Soft deleted registration {reg.registration_code}", "Registration", "Mst_Registration", reg.id)
            log_activity(request, f"Deleted registration {reg.registration_code}")
            return Response({"message":"Deleted Successfully"}, status=status.HTTP_200_OK)
        except Exception as e:
            log_error(request, "RegistrationAPIView.delete", str(e), e)
            return Response({"error": "An error occurred"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class RegistrationBulkImportView(APIView):
    #permission_classes = [IsSuperAdminOrClientAdmin]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            decoded_file = file.read().decode('utf-8')
            io_string = io.StringIO(decoded_file)
            reader = csv.DictReader(io_string)
            
            created_count = 0
            errors = []
            
            for row in reader:
                serializer = RegistrationSerializer(data=row, context={'request': request})
                if serializer.is_valid():
                    serializer.save()
                    created_count += 1
                else:
                    errors.append({"row": row, "errors": serializer.errors})
            
            log_audit(request, "Bulk Import", f"Imported {created_count} registrations", "Registration", "Mst_Registration")
            log_activity(request, f"Bulk imported {created_count} registrations")
            
            return Response({
                "success": True, 
                "created_count": created_count, 
                "errors": errors
            }, status=status.HTTP_201_CREATED if created_count > 0 else status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            log_error(request, "RegistrationBulkImportView.post", str(e), e)
            return Response({"error": f"Import failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class RegistrationExportView(APIView):
    #permission_classes = [IsSuperAdminOrClientAdmin]
    permission_classes = [IsAuthenticated]
    def get(self, request):
        try:
            regs = Registration.objects.filter(is_active=True)
            serializer = RegistrationSerializer(regs, many=True)
            df = pd.DataFrame(serializer.data)
            
            output = io.BytesIO()
            df.to_csv(output, index=False)
            output.seek(0)
            
            response = HttpResponse(output, content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="registrations.csv"'
            
            log_activity(request, "Exported registrations")
            return response
            
        except Exception as e:
            log_error(request, "RegistrationExportView.get", str(e), e)
            return Response({"error": "Export failed"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class PublicRegistrationAPIView(APIView):
    #permission_classes = [permissions.AllowAny]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            # For public registration, we expect client_code in headers or body
            # ClientMiddleware should handle the DB routing if X-Client-Code is in headers
            serializer = RegistrationSerializer(data=request.data, context={'request': request})
            if serializer.is_valid():
                reg = serializer.save()
                log_audit(None, "Public Create", f"Public registration {reg.registration_code}", "Registration", "Mst_Registration", reg.id)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # We use None for request here to avoid issues with unauthenticated IP logging if desired, 
            # but log_error handles it.
            log_error(request, "PublicRegistrationAPIView.post", str(e), e)
            return Response({"error": "An error occurred during registration"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




from datetime import timedelta
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from student_details.models import Enquiry


class EnquiryDashboardCountAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        organization_id = request.query_params.get("organization_id")
        branch_id = request.query_params.get("branch_id")

        queryset = Enquiry.objects.filter(
            is_active=True
        )

        # Organization filter
        if organization_id:

            queryset = queryset.filter(
                courses__organization_id=organization_id
            )

        # Branch filter
        if branch_id:

            queryset = queryset.filter(
                courses__branch_id=branch_id
            )

        queryset = queryset.distinct()

        today = timezone.localdate()

        days_from_sunday = (
            today.weekday() + 1
        ) % 7

        week_start = today - timedelta(
            days=days_from_sunday
        )

        week_end = week_start + timedelta(days=6)

        month_start = today.replace(day=1)

        return Response({

            "success": True,

            "counts": {

                "total_enquiries":
                    queryset.count(),

                "today_enquiries":
                    queryset.filter(
                        created_at__date=today
                    ).count(),

                "week_enquiries":
                    queryset.filter(
                        created_at__date__range=[
                            week_start,
                            week_end
                        ]
                    ).count(),

                "month_enquiries":
                    queryset.filter(
                        created_at__date__gte=month_start
                    ).count(),
            }
        })

from datetime import timedelta

from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import EnquiryFollowUp


class FollowUpDashboardCountAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        organization_id = request.query_params.get(
            "organization_id"
        )

        branch_id = request.query_params.get(
            "branch_id"
        )

        queryset = EnquiryFollowUp.objects.filter(
            is_active=True
        )

        # =====================================
        # ORGANIZATION FILTER
        # =====================================

        if organization_id:

            queryset = queryset.filter(
                enquiry__courses__organization_id=
                organization_id
            )

        # =====================================
        # BRANCH FILTER
        # =====================================

        if branch_id:

            queryset = queryset.filter(
                enquiry__courses__branch_id=
                branch_id
            )

        # Prevent duplicates
        queryset = queryset.distinct()

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
            created_at__date__gte=
            month_start
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

                "total_followups":
                    total_count,

                "today_followups":
                    today_count,

                "week_followups":
                    week_count,

                "month_followups":
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




