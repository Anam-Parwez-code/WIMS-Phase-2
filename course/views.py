from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import Course, Batch, Module, Topic, CourseTracker
from .serializers import CourseSerializer, BatchSerializer, ModuleSerializer, TopicSerializer, CourseTrackerSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from core.permissions import IsSuperAdminOrClientAdmin
from .models import Course
from .serializers import CourseSerializer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi



class CourseListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="List all active courses.",
        responses={200: CourseSerializer(many=True)}
    )
    # def get(self, request):
    #     courses = Course.objects.filter(is_active=True)
    #     serializer = CourseSerializer(courses, many=True)
    #     return Response(serializer.data)

    def get(self, request):

        queryset = Course.objects.filter(
            is_active=True
        )

        # =====================================
        # FILTER BY ORGANIZATION
        # =====================================

        organization_id = request.query_params.get(
            "organization"
        )

        if organization_id:

            queryset = queryset.filter(
                organization_id=organization_id
            )

        # =====================================
        # OPTIONAL: FILTER BY BRANCH
        # =====================================

        branch_id = request.query_params.get(
            "branch"
        )

        if branch_id:

            queryset = queryset.filter(
                branch_id=branch_id
            )

        serializer = CourseSerializer(
            queryset,
            many=True
        )

        return Response(serializer.data)




    @swagger_auto_schema(
        operation_description="Create a new course.",
        request_body=CourseSerializer,
        responses={201: CourseSerializer}
    )
    def post(self, request):
        serializer = CourseSerializer(
            data=request.data,
            context={"request": request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CourseDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        return get_object_or_404(
            Course,
            pk=pk,
            is_active=True
        )

    @swagger_auto_schema(responses={200: CourseSerializer})
    def get(self, request, pk):
        course = self.get_object(pk)
        return Response(CourseSerializer(course).data)

    @swagger_auto_schema(request_body=CourseSerializer)
    def put(self, request, pk):
        course = self.get_object(pk)
        serializer = CourseSerializer(
            course,
            data=request.data,
            context={"request": request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        course = self.get_object(pk)
        course.is_active = False
        course.save(update_fields=["is_active"])
        return Response(
            {"message": "Course disabled successfully."},
            status=status.HTTP_204_NO_CONTENT
        )

class BatchListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="List all active batches.",
        responses={200: BatchSerializer(many=True)}
    )
    def get(self, request):

        queryset = Batch.objects.filter(
            is_active=True
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

        serializer = BatchSerializer(
            queryset,
            many=True
        )

        return Response(serializer.data)

    @swagger_auto_schema(
        operation_description="Create a new batch.",
        request_body=BatchSerializer,
        responses={201: BatchSerializer}
    )
    def post(self, request):
        serializer = BatchSerializer(
            data=request.data,
            context={"request": request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class BatchDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        return get_object_or_404(
            Batch,
            pk=pk,
            is_active=True
        )

    @swagger_auto_schema(responses={200: BatchSerializer})
    def get(self, request, pk):
        batch = self.get_object(pk)
        return Response(BatchSerializer(batch).data)

    @swagger_auto_schema(request_body=BatchSerializer)
    def put(self, request, pk):
        batch = self.get_object(pk)
        serializer = BatchSerializer(
            batch,
            data=request.data,
            context={"request": request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        batch = self.get_object(pk)
        batch.is_active = False
        batch.save(update_fields=["is_active"])
        return Response(
            {"message": "Batch disabled successfully."},
            status=status.HTTP_204_NO_CONTENT
        )

class CourseBatchesAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, course_id):
        course = get_object_or_404(
            Course,
            id=course_id,
            is_active=True
        )

        batches = Batch.objects.select_related(
            "trainer"
        ).filter(
            course=course,
            is_active=True
        )

        data = {
            "course_id": course.id,
            "course_name": course.course_name,
            "course_code": course.course_code,
            "batches": [
                {
                    "id": b.id,
                    "batch_code": b.batch_code,
                    "batch_name": b.batch_name,
                    "start_date": b.start_date,
                    "completion_date": b.completion_date,
                    "batch_time": b.batch_time,
                    # ✅ Trainer details
                    "trainer": b.trainer.id if b.trainer else None,
                    "trainer_name": b.trainer.name if b.trainer else None,
                    "batch_size": b.batch_size,
                    "batch_status": b.batch_status

                }
                for b in batches
            ]
        }

        return Response(data)

class ModuleListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="List all active modules.",
        responses={200: ModuleSerializer(many=True)}
    )
    def get(self, request):
        modules = Module.objects.filter(is_active=True)
        return Response(ModuleSerializer(modules, many=True).data)

    @swagger_auto_schema(
        operation_description="Create a new module.",
        request_body=ModuleSerializer,
        responses={201: ModuleSerializer}
    )
    def post(self, request):
        serializer = ModuleSerializer(
            data=request.data,
            context={"request": request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ModuleDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        return get_object_or_404(
            Module,
            pk=pk,
            is_active=True
        )

    @swagger_auto_schema(responses={200: ModuleSerializer})
    def get(self, request, pk):
        module = self.get_object(pk)
        return Response(ModuleSerializer(module).data)

    @swagger_auto_schema(request_body=ModuleSerializer)
    def put(self, request, pk):
        module = self.get_object(pk)
        serializer = ModuleSerializer(
            module,
            data=request.data,
            context={"request": request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        module = self.get_object(pk)
        module.is_active = False
        module.save(update_fields=["is_active"])
        return Response(
            {"message": "Module disabled successfully."},
            status=status.HTTP_204_NO_CONTENT
        )

class TopicListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="List all active topics.",
        responses={200: TopicSerializer(many=True)}
    )
    def get(self, request):
        topics = Topic.objects.filter(is_active=True)
        return Response(TopicSerializer(topics, many=True).data)

    @swagger_auto_schema(
        operation_description="Create a new topic.",
        request_body=TopicSerializer,
        responses={201: TopicSerializer}
    )
    def post(self, request):
        serializer = TopicSerializer(
            data=request.data,
            context={"request": request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class TopicDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        return get_object_or_404(
            Topic,
            pk=pk,
            is_active=True
        )

    @swagger_auto_schema(responses={200: TopicSerializer})
    def get(self, request, pk):
        topic = self.get_object(pk)
        return Response(TopicSerializer(topic).data)

    @swagger_auto_schema(request_body=TopicSerializer)
    def put(self, request, pk):
        topic = self.get_object(pk)
        serializer = TopicSerializer(
            topic,
            data=request.data,
            context={"request": request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        topic = self.get_object(pk)
        topic.is_active = False
        topic.save(update_fields=["is_active"])
        return Response(
            {"message": "Topic disabled successfully."},
            status=status.HTTP_204_NO_CONTENT
        )

from django.db.models import Q

class CourseTrackerListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="List all active course trackers.",
        responses={200: CourseTrackerSerializer(many=True)}
    )
    def get(self, request):

        queryset = CourseTracker.objects.select_related(
            "organization",
            "branch",
            "trainer",
            "batch",
            "course"
        ).filter(
            is_active=True
        )

        # =====================================
        # ORGANIZATION / BRANCH FILTERS
        # =====================================

        organization_id = request.query_params.get("organization")
        branch_id = request.query_params.get("branch")

        if organization_id and branch_id:

            queryset = queryset.filter(
                organization_id=organization_id,
                branch_id=branch_id
            )

        elif organization_id:

            queryset = queryset.filter(
                organization_id=organization_id
            )

        elif branch_id:

            queryset = queryset.filter(
                branch_id=branch_id
            )

        # =====================================
        # COURSE FILTER
        # =====================================

        course_id = request.query_params.get("course")

        if course_id:
            queryset = queryset.filter(
                course_id=course_id
            )

        # =====================================
        # BATCH FILTER
        # =====================================

        batch_id = request.query_params.get("batch")

        if batch_id:
            queryset = queryset.filter(
                batch_id=batch_id
            )

        # =====================================
        # TRAINER FILTER
        # =====================================

        trainer_id = request.query_params.get("trainer")

        if trainer_id:
            queryset = queryset.filter(
                trainer_id=trainer_id
            )

        # =====================================
        # STATUS FILTER
        # =====================================

        status_value = request.query_params.get("status")

        if status_value:
            queryset = queryset.filter(
                status__iexact=status_value
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
        # SEARCH
        # =====================================

        search = request.query_params.get("search")

        if search:
            queryset = queryset.filter(
                Q(course__course_name__icontains=search) |
                Q(course__course_code__icontains=search) |
                Q(batch__batch_name__icontains=search) |
                Q(batch__batch_code__icontains=search) |
                Q(trainer__name__icontains=search) |
                Q(status__icontains=search)
            )

        queryset = queryset.order_by(
            "-date",
            "course__course_name"
        )

        serializer = CourseTrackerSerializer(
            queryset,
            many=True
        )

        return Response(serializer.data)

    @swagger_auto_schema(
        operation_description="Create a new course tracker.",
        request_body=CourseTrackerSerializer,
        responses={201: CourseTrackerSerializer}
    )
    def post(self, request):
        serializer = CourseTrackerSerializer(
            data=request.data,
            context={"request": request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CourseTrackerDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        return get_object_or_404(
            CourseTracker,
            pk=pk,
            is_active=True
        )

    @swagger_auto_schema(responses={200: CourseTrackerSerializer})
    def get(self, request, pk):
        tracker = self.get_object(pk)
        return Response(CourseTrackerSerializer(tracker).data)

    @swagger_auto_schema(request_body=CourseTrackerSerializer)
    def put(self, request, pk):
        tracker = self.get_object(pk)
        # partial=True allows you to send only {'status': 'Completed'} without sending everything else
        serializer = CourseTrackerSerializer(
            tracker,
            data=request.data,
            context={"request": request},
            partial=True 
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    def delete(self, request, pk):
        tracker = self.get_object(pk)
        tracker.is_active = False
        tracker.save(update_fields=["is_active"])
        return Response(
            {"message": "Course tracker disabled successfully."},
            status=status.HTTP_204_NO_CONTENT
        )


from datetime import timedelta

from django.utils import timezone

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Course


class CourseDashboardCountAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        organization_id = request.query_params.get(
            "organization_id"
        )

        branch_id = request.query_params.get(
            "branch_id"
        )

        queryset = Course.objects.filter(
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

        return Response({

            "success": True,

            "filters": {

                "organization_id":
                    organization_id,

                "branch_id":
                    branch_id
            },

            "counts": {

                "total_courses":
                    total_count,

                "today_courses":
                    today_count,

                "week_courses":
                    week_count,

                "month_courses":
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
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Batch


class BatchDashboardCountAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        organization_id = request.query_params.get(
            "organization_id"
        )

        branch_id = request.query_params.get(
            "branch_id"
        )

        queryset = Batch.objects.filter(
            is_active=True
        )

        # =========================
        # ORGANIZATION FILTER
        # =========================

        if organization_id:

            queryset = queryset.filter(
                organization_id=organization_id
            )

        # =========================
        # BRANCH FILTER
        # =========================

        if branch_id:

            queryset = queryset.filter(
                branch_id=branch_id
            )

        today = timezone.localdate()

        # Sunday → Saturday

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
                "organization_id": organization_id,
                "branch_id": branch_id
            },

            "counts": {

                "total_batches":
                    total_count,

                "today_batches":
                    today_count,

                "week_batches":
                    week_count,

                "month_batches":
                    month_count
            }
        })

