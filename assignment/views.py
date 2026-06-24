from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import FileResponse, Http404
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from staff.models import Employee
from course.models import Batch, Course
from admission.models import Admission
from .models import Assignment
from core.helper_function import get_branch_id
from .serializers import AssignmentSerializer

class AssignmentTeachersAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        branch_id = get_branch_id(request)
        if branch_id:
            teachers = Employee.objects.filter(
                designation__name__iexact="trainer",
                branch_id=branch_id,
                is_active=True
            )
        else:
            teachers = Employee.objects.filter(
                designation__name__iexact="trainer",
                is_active=True
            )

        data = [
            {"TeacherId": t.id, "TeacherName": t.name}
            for t in teachers
        ]

        return Response({"teachers": data})

class AssignmentBatchesAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, trainer_id):
        branch_id = get_branch_id(request)

        if branch_id:
            batches = Batch.objects.filter(
                trainer=trainer_id,
                branch=branch_id,
                is_active=True
            )
        else:
            batches = Batch.objects.filter(
                trainer=trainer_id,
                is_active=True
            )
        print(batches)

        data = [
            {"batch": b.id, "BatchCode": b.batch_code}
            for b in batches
        ]

        return Response({"batches": data})

class AssignmentCoursesAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, trainer_id, batch_id):

        branch_id = request.auth.get("branch_id")
        if branch_id:
            batch = get_object_or_404(
                Batch,
                id=batch_id,
                trainer_id=trainer_id,
                branch_id=branch_id,
                is_active=True
            )
        else:
            batch = get_object_or_404(
                Batch,
                id=batch_id,
                trainer_id=trainer_id,
                is_active=True
            )

        course = batch.course

        return Response({
            "courses": [
                {
                    "CourseId": course.id,
                    "CourseName": course.course_name
                }
            ],
            "autoSelect": True
        })


# class AssignmentListAPIView(APIView):
#     permission_classes = [IsAuthenticated]

#     def get(self, request):

#         branch_id = get_branch_id(request)

#         teacher_id = request.query_params.get("teacher")
#         batch_id = request.query_params.get("batch")

#         if not branch_id:
#             branch_id = request.query_params.get("branch_id")

#         assignments = Assignment.objects.filter(
#             is_active=True
#         )

#         if teacher_id:
#             assignments = assignments.filter(
#                 teacher_id=teacher_id
#             )

#         if batch_id:
#             assignments = assignments.filter(
#                 batch_id=batch_id
#             )

#         if branch_id:
#             assignments = assignments.filter(
#                 branch_id=branch_id
#             )

#         assignments = assignments.order_by("-created_at")

#         serializer = AssignmentSerializer(assignments, many=True)

#         return Response({
#             "count": assignments.count(),
#             "results": serializer.data
#         })

# class AssignmentSaveAPIView(APIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request):
#         branch_id = get_branch_id(request)
#         if branch_id== None:
#             branch_id = request.data.get("branch")
#             print('branch from payload')
#         print('branch_id', branch_id)
        
#         assignment_id = request.data.get("id")

#         if assignment_id:
#             if branch_id:
#                 assignment = get_object_or_404(
#                     Assignment,
#                     id=assignment_id,
#                     branch=branch_id,
#                     is_active=True
#                     )
#             else:
#                 assignment = get_object_or_404(
#                     Assignment,
#                     id=assignment_id,
#                     is_active=True
#                 )
#             serializer = AssignmentSerializer(
#                 assignment,
#                 data=request.data,
#                 partial=True,
#                 context={"request": request}
#             )
#         else:
#             serializer = AssignmentSerializer(data=request.data, context={"request": request})

#         if serializer.is_valid():
#             assignment = serializer.save()

#             return Response({
#                 "success": True,
#                 "assignmentId": assignment.id,
#                 "fileUrl": assignment.file.url if assignment.file else None
#             })

#         return Response(serializer.errors, status=400)

# views.py

from django.shortcuts import get_object_or_404
from django.db.models import Q

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (
    Assignment,
    AssignmentSubmission
)

from .serializers import (
    AssignmentSerializer,
    StudentAssignmentListSerializer,
    AssignmentSubmissionSerializer
)

from admission.models import (
    Admission,
    AdmissionCourseBatch
)


# =========================================================
# CREATE / UPDATE ASSIGNMENT
# =========================================================

class AssignmentSaveAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        assignment_id = request.data.get("id")

        if assignment_id:

            assignment = get_object_or_404(
                Assignment,
                id=assignment_id,
                is_active=True
            )

            serializer = AssignmentSerializer(
                assignment,
                data=request.data,
                partial=True,
                context={"request": request}
            )

        else:

            serializer = AssignmentSerializer(
                data=request.data,
                context={"request": request}
            )

        if serializer.is_valid():

            assignment = serializer.save()

            return Response({
                "success": True,
                "assignmentId": assignment.id,
                "fileUrl": (
                    assignment.file.url
                    if assignment.file
                    else None
                )
            })

        return Response(
            serializer.errors,
            status=400
        )


# =========================================================
# ASSIGNMENT LIST
# =========================================================

class AssignmentListAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        teacher_id = request.query_params.get("teacher")
        course_id = request.query_params.get("course")
        batch_id = request.query_params.get("batch")

        organization_id = request.query_params.get(
            "organization_id"
        )

        branch_id = request.query_params.get(
            "branch_id"
        )

        assignments = Assignment.objects.filter(
            is_active=True
        )

        # ==================================
        # ORGANIZATION FILTER
        # ==================================

        if organization_id:

            assignments = assignments.filter(
                branch__organization_id=organization_id
            )

        # ==================================
        # BRANCH FILTER
        # ==================================

        if branch_id:

            assignments = assignments.filter(
                branch_id=branch_id
            )

        # ==================================
        # TEACHER FILTER
        # ==================================

        if teacher_id:

            assignments = assignments.filter(
                teacher_id=teacher_id
            )

        # ==================================
        # COURSE FILTER
        # ==================================

        if course_id:

            assignments = assignments.filter(
                course_id=course_id
            )

        # ==================================
        # BATCH FILTER
        # ==================================

        if batch_id:

            assignments = assignments.filter(
                batch_id=batch_id
            )

        assignments = assignments.order_by(
            "-created_at"
        )

        serializer = AssignmentSerializer(
            assignments,
            many=True
        )

        return Response({
            "count": assignments.count(),
            "results": serializer.data
        })


# =========================================================
# STUDENT ASSIGNMENT LIST
# =========================================================

class StudentAssignmentListAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        admission_id = request.query_params.get("admission")

        if not admission_id:

            return Response({
                "success": False,
                "message": "admission is required"
            }, status=400)

        admission = get_object_or_404(
            Admission,
            id=admission_id,
            is_active=True
        )

        mappings = AdmissionCourseBatch.objects.filter(
            admission=admission,
            is_active=True
        )

        if not mappings.exists():

            return Response({
                "success": False,
                "message":
                "No course-batch mappings found"
            }, status=400)

        query = Q()

        for mapping in mappings:

            query |= Q(
                course_id=mapping.course_id,
                batch_id=mapping.batch_id
            )

        assignments = Assignment.objects.filter(
            query,
            is_active=True
        ).order_by("-created_at")

        serializer = StudentAssignmentListSerializer(
            assignments,
            many=True
        )

        return Response({
            "success": True,

            "admission": admission.id,

            "admission_code":
            admission.admission_code,

            "candidate_name":
            admission.candidate_name,

            "count": assignments.count(),

            "results": serializer.data
        })



# =========================================================
# SAVE SUBMISSION
# =========================================================

# class AssignmentSubmissionSaveAPIView(APIView):

#     permission_classes = [IsAuthenticated]

#     def post(self, request):

#         submission_id = request.data.get("id")

#         if submission_id:

#             submission = get_object_or_404(
#                 AssignmentSubmission,
#                 id=submission_id,
#                 is_active=True
#             )

#             serializer = AssignmentSubmissionSerializer(
#                 submission,
#                 data=request.data,
#                 partial=True
#             )

#         else:

#             serializer = AssignmentSubmissionSerializer(
#                 data=request.data
#             )

#         if serializer.is_valid():

#             submission = serializer.save()

#             return Response({
#                 "success": True,

#                 "submissionId":
#                 submission.id,

#                 "assignmentId":
#                 submission.assignment.id,

#                 "admissionId":
#                 submission.admission.id,

#                 "answerText":
#                 submission.answer_text,

#                 "answerFile": (
#                     submission.answer_file.url
#                     if submission.answer_file
#                     else None
#                 )
#             })

#         return Response(
#             serializer.errors,
#             status=400
#         )

# views.py

from django.shortcuts import get_object_or_404

class AssignmentSubmissionSaveAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        submission_id = request.data.get("id")

        assignment_id = request.data.get(
            "assignment"
        )

        admission_id = request.data.get(
            "admission"
        )

        # =====================================
        # VALIDATIONS
        # =====================================

        if not assignment_id:

            return Response({
                "success": False,
                "message": "assignment is required"
            }, status=400)

        if not admission_id:

            return Response({
                "success": False,
                "message": "admission is required"
            }, status=400)

        # =====================================
        # EXPLICIT UPDATE USING ID
        # =====================================

        if submission_id:

            submission = get_object_or_404(
                AssignmentSubmission,
                id=submission_id
            )

            serializer = (
                AssignmentSubmissionSerializer(
                    submission,
                    data=request.data,
                    partial=True
                )
            )

        else:

            # =================================
            # CHECK EXISTING SUBMISSION
            # =================================

            existing_submission = (
                AssignmentSubmission.objects.filter(
                    assignment_id=assignment_id,
                    admission_id=admission_id
                ).first()
            )

            # ================================
            # UPDATE EXISTING
            # ================================

            if existing_submission:

                serializer = (
                    AssignmentSubmissionSerializer(
                        existing_submission,
                        data=request.data,
                        partial=True
                    )
                )

            # ================================
            # CREATE NEW
            # ================================

            else:

                serializer = (
                    AssignmentSubmissionSerializer(
                        data=request.data
                    )
                )

        # =====================================
        # SAVE
        # =====================================

        if serializer.is_valid():

            submission = serializer.save(
                is_active=True
            )

            return Response({

                "success": True,

                "submissionId":
                submission.id,

                "assignmentId":
                submission.assignment.id,

                "admissionId":
                submission.admission.id,

                "answerText":
                submission.answer_text,

                "answerFile":
                (
                    submission.answer_file.url
                    if submission.answer_file
                    else None
                ),

                "submittedAt":
                submission.submitted_at
            })

        return Response(
            serializer.errors,
            status=400
        )

# views.py

from django.utils import timezone


class AssignmentReviewAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):

        submission = get_object_or_404(

            AssignmentSubmission,

            id=pk,

            is_active=True
        )

        score = request.data.get("score")

        teacher_comment = request.data.get(
            "teacher_comment"
        )

        # =====================================
        # UPDATE REVIEW
        # =====================================

        submission.score = score

        submission.teacher_comment = (
            teacher_comment
        )

        submission.reviewed_by = request.user

        submission.reviewed_at = timezone.now()

        submission.is_reviewed = True

        submission.save()

        return Response({

            "success": True,

            "message":
            "Assignment reviewed successfully.",

            "submission_id":
            submission.id,

            "student":
            submission.admission.candidate_name,

            "assignment":
            submission.assignment.title,

            "score":
            submission.score,

            "teacher_comment":
            submission.teacher_comment,

            "reviewed_by":
            (
                request.user.email
                if request.user.email
                else request.user.username
            ),

            "reviewed_at":
            submission.reviewed_at
        })

# =========================================================
# SUBMISSION LIST
# =========================================================

class AssignmentSubmissionListAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        assignment_id = request.query_params.get(
            "assignment"
        )

        admission_id = request.query_params.get(
            "admission"
        )

        submissions = AssignmentSubmission.objects.filter(
            is_active=True
        )

        if assignment_id:

            submissions = submissions.filter(
                assignment_id=assignment_id
            )

        if admission_id:

            submissions = submissions.filter(
                admission_id=admission_id
            )

        submissions = submissions.order_by(
            "-submitted_at"
        )

        serializer = AssignmentSubmissionSerializer(
            submissions,
            many=True
        )

        return Response({
            "count": submissions.count(),
            "results": serializer.data
        })

# views.py

class AssignmentSubmissionDetailAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, submission_id):

        submission = get_object_or_404(
            AssignmentSubmission.objects.select_related(
                "assignment",
                "assignment__teacher",
                "assignment__course",
                "assignment__batch",
                "admission"
            ),
            id=submission_id,
            is_active=True
        )

        serializer = AssignmentSubmissionSerializer(submission)

        return Response({
            "success": True,
            "result": serializer.data
        })

# views.py

class CourseBatchAssignmentListAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        course_id = request.query_params.get(
            "course"
        )

        batch_id = request.query_params.get(
            "batch"
        )

        teacher_id = request.query_params.get(
            "teacher"
        )

        # =====================================
        # VALIDATIONS
        # =====================================

        if not course_id:

            return Response({
                "success": False,
                "message": "course is required"
            }, status=400)

        if not batch_id:

            return Response({
                "success": False,
                "message": "batch is required"
            }, status=400)

        # =====================================
        # BASE QUERY
        # =====================================

        assignments = Assignment.objects.select_related(
            "teacher",
            "course",
            "batch",
            "branch"
        ).filter(
            course_id=course_id,
            batch_id=batch_id,
            is_active=True
        )

        # =====================================
        # TEACHER FILTER
        # =====================================

        if teacher_id:

            assignments = assignments.filter(
                teacher_id=teacher_id
            )

        # =====================================
        # ORDERING
        # =====================================

        assignments = assignments.order_by(
            "-created_at"
        )

        serializer = AssignmentSerializer(
            assignments,
            many=True
        )

        return Response({

            "success": True,

            "course": course_id,

            "batch": batch_id,

            "teacher": teacher_id,

            "count": assignments.count(),

            "results": serializer.data
        })

# views.py

class AssignmentSubmissionStudentListAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        assignment_id = request.query_params.get(
            "assignment"
        )

        if not assignment_id:

            return Response({
                "success": False,
                "message": "assignment is required"
            }, status=400)

        # =====================================
        # ASSIGNMENT
        # =====================================

        assignment = get_object_or_404(
            Assignment.objects.select_related(
                "course",
                "batch"
            ),
            id=assignment_id,
            is_active=True
        )

        # =====================================
        # ALL STUDENTS UNDER COURSE + BATCH
        # =====================================

        mappings = AdmissionCourseBatch.objects.select_related(
            "admission"
        ).filter(
            course=assignment.course,
            batch=assignment.batch,
            admission__is_active=True,
            is_active=True
        )

        # =====================================
        # SUBMITTED STUDENTS IDS
        # =====================================

        submitted_admission_ids = AssignmentSubmission.objects.filter(
            assignment=assignment,
            is_active=True
        ).values_list(
            "admission_id",
            flat=True
        )

        # =====================================
        # SUBMITTED STUDENTS
        # =====================================

        submitted_students = mappings.filter(
            admission_id__in=submitted_admission_ids
        )

        # =====================================
        # NOT SUBMITTED STUDENTS
        # =====================================

        not_submitted_students = mappings.exclude(
            admission_id__in=submitted_admission_ids
        )

        # =====================================
        # RESPONSE FORMAT
        # =====================================

        submitted_data = []

        for item in submitted_students:

            submission = AssignmentSubmission.objects.filter(
                assignment=assignment,
                admission=item.admission,
                is_active=True
            ).first()

            submitted_data.append({

                "admission_id":
                item.admission.id,

                "admission_code":
                item.admission.admission_code,

                "candidate_name":
                item.admission.candidate_name,

                "mobile_no":
                item.admission.mobile_no,

                "email":
                item.admission.email,

                "submitted": True,

                "submission_id":
                submission.id if submission else None,

                "submitted_at":
                submission.submitted_at
                if submission else None,

                "answer_file":
                (
                    submission.answer_file.url
                    if (
                        submission
                        and submission.answer_file
                    )
                    else None
                )
            })

        # =====================================
        # NOT SUBMITTED DATA
        # =====================================

        not_submitted_data = []

        for item in not_submitted_students:

            not_submitted_data.append({

                "admission_id":
                item.admission.id,

                "admission_code":
                item.admission.admission_code,

                "candidate_name":
                item.admission.candidate_name,

                "mobile_no":
                item.admission.mobile_no,

                "email":
                item.admission.email,

                "submitted": False
            })

        return Response({

            "success": True,

            "assignment": assignment.id,

            "assignment_title":
            assignment.title,

            "course":
            assignment.course.id,

            "course_name":
            assignment.course.course_name,

            "batch":
            assignment.batch.id,

            "batch_name":
            assignment.batch.batch_name,

            # =================================
            # COUNTS
            # =================================

            "total_students":
            mappings.count(),

            "submitted_count":
            len(submitted_data),

            "not_submitted_count":
            len(not_submitted_data),

            # =================================
            # DATA
            # =================================

            "submitted_students":
            submitted_data,

            "not_submitted_students":
            not_submitted_data
        })

# views.py

class StudentAssignmentsByCourseBatchAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        admission_id = request.query_params.get(
            "admission"
        )

        course_id = request.query_params.get(
            "course"
        )

        batch_id = request.query_params.get(
            "batch"
        )

        # =====================================
        # VALIDATION
        # =====================================

        if not admission_id:

            return Response({
                "success": False,
                "message": "admission is required"
            }, status=400)

        # =====================================
        # ADMISSION
        # =====================================

        admission = get_object_or_404(
            Admission,
            id=admission_id,
            is_active=True
        )

        # =====================================
        # STUDENT COURSE-BATCH MAPPINGS
        # =====================================

        mappings = AdmissionCourseBatch.objects.filter(
            admission=admission,
            is_active=True
        )

        # =====================================
        # FILTER BY COURSE
        # =====================================

        if course_id:

            mappings = mappings.filter(
                course_id=course_id
            )

        # =====================================
        # FILTER BY BATCH
        # =====================================

        if batch_id:

            mappings = mappings.filter(
                batch_id=batch_id
            )

        # =====================================
        # NO MAPPINGS
        # =====================================

        if not mappings.exists():

            return Response({
                "success": False,
                "message":
                "No course/batch mappings found."
            }, status=404)

        # =====================================
        # FETCH ASSIGNMENTS
        # =====================================

        assignments = Assignment.objects.none()

        for mapping in mappings:

            assignment_qs = Assignment.objects.select_related(
                "teacher",
                "course",
                "batch",
                "branch"
            ).filter(
                course=mapping.course,
                batch=mapping.batch,
                is_active=True
            )

            assignments = assignments | assignment_qs

        assignments = assignments.distinct().order_by(
            "-created_at"
        )

        # =====================================
        # PREPARE RESPONSE
        # =====================================

        results = []

        for assignment in assignments:

            submission = AssignmentSubmission.objects.filter(
                assignment=assignment,
                admission=admission,
                is_active=True
            ).first()

            results.append({

                "assignment_id":
                assignment.id,

                "title":
                assignment.title,

                "description":
                assignment.description,

                "assignment_file":
                (
                    assignment.file.url
                    if assignment.file
                    else None
                ),

                "assignment_start_date":
                assignment.assignment_start_date,

                "submission_last_date":
                assignment.submission_last_date,

                # =============================
                # COURSE
                # =============================

                "course":
                assignment.course.id,

                "course_name":
                assignment.course.course_name,

                # =============================
                # BATCH
                # =============================

                "batch":
                assignment.batch.id,

                "batch_name":
                assignment.batch.batch_name,

                # =============================
                # TEACHER
                # =============================

                "teacher":
                assignment.teacher.id,

                "teacher_name":
                assignment.teacher.name,

                # =============================
                # SUBMISSION STATUS
                # =============================

                "submitted":
                True if submission else False,

                "submission_id":
                submission.id
                if submission else None,

                "submitted_at":
                submission.submitted_at
                if submission else None,

                "answer_file":
                (
                    submission.answer_file.url
                    if (
                        submission
                        and submission.answer_file
                    )
                    else None
                ),

                "answer_text":
                (
                    submission.answer_text
                    if submission
                    else None
                ),

                # =============================
                # CREATED
                # =============================

                "created_at":
                assignment.created_at
            })

        return Response({

            "success": True,

            # =================================
            # STUDENT
            # =================================

            "admission":
            admission.id,

            "admission_code":
            admission.admission_code,

            "candidate_name":
            admission.candidate_name,

            # =================================
            # FILTERS
            # =================================

            "course_filter":
            course_id,

            "batch_filter":
            batch_id,

            # =================================
            # COUNTS
            # =================================

            "count":
            len(results),

            # =================================
            # DATA
            # =================================

            "results":
            results
        })

# views.py 247

# class StudentAssignmentsByCourseBatchAPIView(APIView):

#     permission_classes = [IsAuthenticated]

#     def get(self, request):

#         admission_id = request.query_params.get(
#             "admission"
#         )

#         course_id = request.query_params.get(
#             "course"
#         )

#         batch_id = request.query_params.get(
#             "batch"
#         )

#         # =====================================
#         # VALIDATION
#         # =====================================

#         if not admission_id:

#             return Response({
#                 "success": False,
#                 "message": "admission is required"
#             }, status=400)

#         # =====================================
#         # ADMISSION
#         # =====================================

#         admission = get_object_or_404(
#             Admission,
#             id=admission_id,
#             is_active=True
#         )

#         # =====================================
#         # STUDENT COURSE-BATCH MAPPINGS
#         # =====================================

#         mappings = AdmissionCourseBatch.objects.filter(
#             admission=admission,
#             is_active=True
#         )

#         # =====================================
#         # FILTER BY COURSE
#         # =====================================

#         if course_id:

#             mappings = mappings.filter(
#                 course_id=course_id
#             )

#         # =====================================
#         # FILTER BY BATCH
#         # =====================================

#         if batch_id:

#             mappings = mappings.filter(
#                 batch_id=batch_id
#             )

#         # =====================================
#         # NO MAPPINGS
#         # =====================================

#         if not mappings.exists():

#             return Response({
#                 "success": False,
#                 "message":
#                 "No course/batch mappings found."
#             }, status=404)

#         # =====================================
#         # FETCH ASSIGNMENTS
#         # =====================================

#         assignments = Assignment.objects.none()

#         for mapping in mappings:

#             assignment_qs = Assignment.objects.select_related(
#                 "teacher",
#                 "course",
#                 "batch",
#                 "branch"
#             ).filter(
#                 course=mapping.course,
#                 batch=mapping.batch,
#                 is_active=True
#             )

#             assignments = assignments | assignment_qs

#         assignments = assignments.distinct().order_by(
#             "-created_at"
#         )

#         # =====================================
#         # PREPARE RESPONSE
#         # =====================================

#         results = []

#         for assignment in assignments:

#             submission = AssignmentSubmission.objects.filter(
#                 assignment=assignment,
#                 admission=admission,
#                 is_active=True
#             ).first()

#             results.append({

#                 "assignment_id":
#                 assignment.id,

#                 "title":
#                 assignment.title,

#                 "description":
#                 assignment.description,

#                 "assignment_file":
#                 (
#                     assignment.file.url
#                     if assignment.file
#                     else None
#                 ),

#                 # =============================
#                 # COURSE
#                 # =============================

#                 "course":
#                 assignment.course.id,

#                 "course_name":
#                 assignment.course.course_name,

#                 # =============================
#                 # BATCH
#                 # =============================

#                 "batch":
#                 assignment.batch.id,

#                 "batch_name":
#                 assignment.batch.batch_name,

#                 # =============================
#                 # TEACHER
#                 # =============================

#                 "teacher":
#                 assignment.teacher.id,

#                 "teacher_name":
#                 assignment.teacher.name,

#                 # =============================
#                 # SUBMISSION STATUS
#                 # =============================

#                 "submitted":
#                 True if submission else False,

#                 "submission_id":
#                 submission.id
#                 if submission else None,

#                 "submitted_at":
#                 submission.submitted_at
#                 if submission else None,

#                 "answer_file":
#                 (
#                     submission.answer_file.url
#                     if (
#                         submission
#                         and submission.answer_file
#                     )
#                     else None
#                 ),

#                 "answer_text":
#                 (
#                     submission.answer_text
#                     if submission
#                     else None
#                 ),

#                 # =============================
#                 # CREATED
#                 # =============================

#                 "created_at":
#                 assignment.created_at
#             })

#         return Response({

#             "success": True,

#             # =================================
#             # STUDENT
#             # =================================

#             "admission":
#             admission.id,

#             "admission_code":
#             admission.admission_code,

#             "candidate_name":
#             admission.candidate_name,

#             # =================================
#             # FILTERS
#             # =================================

#             "course_filter":
#             course_id,

#             "batch_filter":
#             batch_id,

#             # =================================
#             # COUNTS
#             # =================================

#             "count":
#             len(results),

#             # =================================
#             # DATA
#             # =================================

#             "results":
#             results
#         })
    
# views.py

class AssignmentSubmissionDeleteAPIView(
    APIView
):

    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):

        admission_id = request.query_params.get(
            "admission"
        )

        if not admission_id:

            return Response({

                "success": False,

                "message":
                "admission is required"

            }, status=400)

        # =====================================
        # FETCH SUBMISSION
        # =====================================

        submission = get_object_or_404(

            AssignmentSubmission,

            id=pk,

            admission_id=admission_id,

            is_active=True
        )

        # =====================================
        # OPTIONAL DEADLINE CHECK
        # =====================================

        if (
            submission.assignment.submission_last_date
            and timezone.now().date()
            >
            submission.assignment.submission_last_date
        ):

            return Response({

                "success": False,

                "message":
                "Submission delete deadline crossed."

            }, status=400)

        # =====================================
        # SOFT DELETE
        # =====================================

        submission.is_active = False

        submission.save()

        return Response({

            "success": True,

            "message":
            "Assignment submission deleted successfully."
        })



from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Assignment
from .serializers import AssignmentSerializer


class AssignmentDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):

        branch_id = get_branch_id(request)

        # fallback from query params
        if not branch_id:
            branch_id = request.query_params.get("branch_id")

        queryset = Assignment.objects.filter(
            id=pk,
            is_active=True
        )

        # Apply branch filter if available
        if branch_id:
            queryset = queryset.filter(
                branch_id=branch_id
            )

        assignment = get_object_or_404(queryset)

        serializer = AssignmentSerializer(assignment)

        return Response(serializer.data)

class AssignmentDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, assignmentId):

        # 1. Try token
        branch_id = get_branch_id(request)

        # 2. Fallback from query params
        if not branch_id:
            branch_id = request.query_params.get("branch_id")

        queryset = Assignment.objects.filter(
            id=assignmentId,
            is_active=True
        )

        # Apply branch filter only if available
        if branch_id:
            queryset = queryset.filter(
                branch_id=branch_id
            )

        assignment = get_object_or_404(queryset)

        # Soft delete
        assignment.is_active = False
        assignment.save(update_fields=["is_active"])

        return Response({
            "success": True,
            "message": "Assignment deleted successfully."
        })

class AssignmentDownloadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, assignmentId):
        branch_id = get_branch_id(request)

        assignment = get_object_or_404(
            Assignment,
            id=assignmentId,
           # branch_id=branch_id,
            is_active=True
        )

        if not assignment.file:
            return Response({"error": "File not found"}, status=404)

        return FileResponse(
            assignment.file.open("rb"),
            content_type="application/pdf",
            as_attachment=True,
            filename=assignment.file.name.split("/")[-1]
        )


from datetime import timedelta

from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import AssignmentSubmission


class AssignmentReviewDashboardAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        trainer_id = request.query_params.get(
            "trainer_id"
        )

        organization_id = request.query_params.get(
            "organization_id"
        )

        branch_id = request.query_params.get(
            "branch_id"
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
        # PENDING REVIEWS
        # =====================================

        queryset = AssignmentSubmission.objects.filter(
            is_active=True,
            is_reviewed=False
        )

        # =====================================
        # TRAINER FILTER
        # =====================================

        if trainer_id:

            queryset = queryset.filter(
                assignment__teacher_id=trainer_id
            )

        # =====================================
        # ORGANIZATION FILTER
        # =====================================

        if organization_id:

            queryset = queryset.filter(
                assignment__branch__organization_id=
                organization_id
            )

        # =====================================
        # BRANCH FILTER
        # =====================================

        if branch_id:

            queryset = queryset.filter(
                assignment__branch_id=branch_id
            )

        # =====================================
        # COUNTS
        # =====================================

        total_count = queryset.count()

        today_count = queryset.filter(
            submitted_at__date=today
        ).count()

        week_count = queryset.filter(
            submitted_at__date__range=[
                week_start,
                week_end
            ]
        ).count()

        month_count = queryset.filter(
            submitted_at__date__gte=month_start
        ).count()

        return Response({

            "success": True,

            "filters": {

                "trainer_id":
                    trainer_id,

                "organization_id":
                    organization_id,

                "branch_id":
                    branch_id
            },

            "pending_assignment_reviews": {

                "total":
                    total_count,

                "today":
                    today_count,

                "week":
                    week_count,

                "month":
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


