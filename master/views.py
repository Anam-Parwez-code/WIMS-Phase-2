from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from core.models import Client
from .models import Department, Designation, Country, EmailConfigurations, SMSConfiguration, State, City, FollowUpMedium, InterestLevel, Organization, Branch, Source, Status, Nationality, FormDesign, PaymentMethod
from .serializers import DepartmentSerializer, DesignationSerializer, CountrySerializer, EmailConfigurationsSerializer, SMSConfigurationSerializer, StateSerializer, CitySerializer, FollowUpMediumSerializer, InterestLevelSerializer, OrganizationSerializer, BranchSerializer, SourceSerializer, StatusSerializer, NationalitySerializer, FormDesignSerializer, PaymentMethodSerializer
from rest_framework.permissions import IsAuthenticated
from core import permissions
from rest_framework import permissions
from core.permissions import IsSuperAdmin, IsSuperAdminOrClientAdmin, IsClientAdminOnly   # Import IsSuperAdmin
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.db.models.functions import Lower


class CountryListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="List Countries",
        operation_description="Retrieve all active countries for the current tenant.",
        responses={
            200: openapi.Response(
                description="List of countries",
                schema=CountrySerializer(many=True)
            )
        }
    )
    def get(self, request):
        countries = Country.objects.filter(is_active=True)
        serializer = CountrySerializer(countries, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="Create Country",
        operation_description="Create a new country inside the current tenant database.",
        request_body=CountrySerializer,
        responses={
            201: openapi.Response(
                description="Country created successfully",
                schema=CountrySerializer
            ),
            400: "Validation Error"
        }
    )
    def post(self, request):
        serializer = CountrySerializer(data=request.data)
        if serializer.is_valid():
            country = serializer.save()
            return Response(
                CountrySerializer(country).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CountryDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        return get_object_or_404(
            Country,
            pk=pk,
            is_active=True
        )

    @swagger_auto_schema(
        operation_summary="Retrieve Country",
        operation_description="Retrieve a specific country by ID from the current tenant database.",
        responses={
            200: openapi.Response(
                description="Country details",
                schema=CountrySerializer
            ),
            404: "Not Found"
        }
    )
    def get(self, request, pk):
        country = self.get_object(pk)
        serializer = CountrySerializer(country)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="Update Country",
        operation_description="Update a specific country inside the current tenant database.",
        request_body=CountrySerializer,
        responses={
            200: openapi.Response(
                description="Country updated successfully",
                schema=CountrySerializer
            ),
            400: "Validation Error",
            404: "Not Found"
        }
    )
    def put(self, request, pk):
        country = self.get_object(pk)
        serializer = CountrySerializer(country, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_summary="Delete Country",
        operation_description="Soft delete a country and cascade soft delete related states, cities, and nationalities.",
        responses={
            204: "Country deleted successfully",
            404: "Not Found"
        }
    )
    def delete(self, request, pk):
        country = self.get_object(pk)

        country.is_active = False
        country.save()

        State.objects.filter(
            country=country,
            is_active=True
        ).update(is_active=False)

        City.objects.filter(
            state__country=country,
            is_active=True
        ).update(is_active=False)

        Nationality.objects.filter(
            country=country,
            is_active=True
        ).update(is_active=False)

        return Response(
            {"message": "Country deleted successfully (soft deleted with cascade)."},
            status=status.HTTP_204_NO_CONTENT
        )

class StateListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="List States",
        operation_description="Retrieve all active states for the current tenant database.",
        responses={200: StateSerializer(many=True)}
    )
    def get(self, request):
        states = State.objects.select_related("country").filter(is_active=True)
        serializer = StateSerializer(states, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="Create State",
        operation_description="Create a new state inside the current tenant database.",
        request_body=StateSerializer,
        responses={
            201: StateSerializer,
            400: "Validation Error"
        }
    )
    def post(self, request):
        serializer = StateSerializer(data=request.data)
        if serializer.is_valid():
            state = serializer.save()
            return Response(StateSerializer(state).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class StateDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        return get_object_or_404(
            State,
            pk=pk,
            is_active=True
        )

    @swagger_auto_schema(
        operation_summary="Retrieve State",
        operation_description="Retrieve a specific state by ID.",
        responses={200: StateSerializer}
    )
    def get(self, request, pk):
        state = self.get_object(pk)
        serializer = StateSerializer(state)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="Update State",
        operation_description="Update a specific state.",
        request_body=StateSerializer,
        responses={
            200: StateSerializer,
            400: "Validation Error"
        }
    )
    def put(self, request, pk):
        state = self.get_object(pk)
        serializer = StateSerializer(state, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_summary="Delete State",
        operation_description="Soft delete a state and cascade delete related cities.",
        responses={204: "Deleted Successfully"}
    )
    def delete(self, request, pk):
        state = self.get_object(pk)

        state.is_active = False
        state.save()

        City.objects.filter(
            state=state,
            is_active=True
        ).update(is_active=False)

        return Response(
            {"message": "State deleted successfully (soft deleted with cascade)."},
            status=status.HTTP_204_NO_CONTENT
        )

class CityListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="List Cities",
        operation_description="Retrieve all active cities with state and country names.",
        responses={200: CitySerializer(many=True)}
    )
    def get(self, request):
        cities = City.objects.select_related(
            "country",
            "state"
        ).filter(is_active=True)

        serializer = CitySerializer(cities, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="Create City",
        operation_description="Create a new city inside the current tenant database.",
        request_body=CitySerializer,
        responses={
            201: CitySerializer,
            400: "Validation Error"
        }
    )
    def post(self, request):
        serializer = CitySerializer(data=request.data)
        if serializer.is_valid():
            city = serializer.save()
            return Response(CitySerializer(city).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CityDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        return get_object_or_404(
            City,
            pk=pk,
            is_active=True
        )

    @swagger_auto_schema(
        operation_summary="Retrieve City",
        operation_description="Retrieve a specific city by ID.",
        responses={200: CitySerializer}
    )
    def get(self, request, pk):
        city = self.get_object(pk)
        serializer = CitySerializer(city)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="Update City",
        operation_description="Update a specific city.",
        request_body=CitySerializer,
        responses={
            200: CitySerializer,
            400: "Validation Error"
        }
    )
    def put(self, request, pk):
        city = self.get_object(pk)
        serializer = CitySerializer(city, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_summary="Delete City",
        operation_description="Soft delete a city.",
        responses={204: "Deleted Successfully"}
    )
    def delete(self, request, pk):
        city = self.get_object(pk)

        city.is_active = False
        city.save()

        return Response(
            {"message": "City deleted successfully."},
            status=status.HTTP_204_NO_CONTENT
        )

class DepartmentListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="List Departments",
        operation_description="Retrieve all active departments.",
        responses={200: DepartmentSerializer(many=True)}
    )
    def get(self, request):
        departments = Department.objects.filter(is_active=True)
        serializer = DepartmentSerializer(departments, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="Create Department",
        operation_description="Create a new department.",
        request_body=DepartmentSerializer,
        responses={
            201: DepartmentSerializer,
            400: "Validation Error"
        }
    )
    def post(self, request):
        serializer = DepartmentSerializer(data=request.data)
        if serializer.is_valid():
            dept = serializer.save()
            return Response(
                DepartmentSerializer(dept).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class DepartmentDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        return get_object_or_404(
            Department,
            pk=pk,
            is_active=True
        )

    @swagger_auto_schema(
        operation_summary="Retrieve Department",
        operation_description="Retrieve a specific department.",
        responses={200: DepartmentSerializer}
    )
    def get(self, request, pk):
        department = self.get_object(pk)
        serializer = DepartmentSerializer(department)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="Update Department",
        operation_description="Update a department.",
        request_body=DepartmentSerializer,
        responses={
            200: DepartmentSerializer,
            400: "Validation Error"
        }
    )
    def put(self, request, pk):
        department = self.get_object(pk)
        serializer = DepartmentSerializer(department, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_summary="Delete Department",
        operation_description="Soft delete department and cascade delete related designations.",
        responses={204: "Deleted Successfully"}
    )
    def delete(self, request, pk):
        department = self.get_object(pk)
        department.is_active = False
        department.save()

        Designation.objects.filter(
            department=department,
            is_active=True
        ).update(is_active=False)

        return Response(
            {"message": "Department deleted successfully."},
            status=status.HTTP_204_NO_CONTENT
        )

class DesignationListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="List Designations",
        operation_description="Retrieve all active designations with department name.",
        responses={200: DesignationSerializer(many=True)}
    )
    def get(self, request):
        designations = Designation.objects.select_related(
            "department"
        ).filter(is_active=True)

        serializer = DesignationSerializer(designations, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="Create Designation",
        operation_description="Create a new designation.",
        request_body=DesignationSerializer,
        responses={
            201: DesignationSerializer,
            400: "Validation Error"
        }
    )
    def post(self, request):
        serializer = DesignationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class DesignationDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        return get_object_or_404(
            Designation,
            pk=pk,
            is_active=True
        )

    @swagger_auto_schema(
        operation_summary="Retrieve Designation",
        operation_description="Retrieve a specific designation.",
        responses={200: DesignationSerializer}
    )
    def get(self, request, pk):
        designation = self.get_object(pk)
        serializer = DesignationSerializer(designation)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="Update Designation",
        operation_description="Update a designation.",
        request_body=DesignationSerializer,
        responses={
            200: DesignationSerializer,
            400: "Validation Error"
        }
    )
    def put(self, request, pk):
        designation = self.get_object(pk)
        serializer = DesignationSerializer(designation, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_summary="Delete Designation",
        operation_description="Soft delete a designation.",
        responses={204: "Deleted Successfully"}
    )
    def delete(self, request, pk):
        designation = self.get_object(pk)
        designation.is_active = False
        designation.save()

        return Response(
            {"message": "Designation deleted successfully."},
            status=status.HTTP_204_NO_CONTENT
        )

class FollowUpMediumListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        responses={200: FollowUpMediumSerializer(many=True)}
    )
    def get(self, request):
        mediums = FollowUpMedium.objects.filter(is_active=True)
        serializer = FollowUpMediumSerializer(
            mediums,
            many=True,
            context={"request": request}
        )
        return Response(serializer.data)

    @swagger_auto_schema(
        request_body=FollowUpMediumSerializer,
        responses={201: FollowUpMediumSerializer}
    )
    def post(self, request):
        serializer = FollowUpMediumSerializer(
            data=request.data,
            context={"request": request}
        )
        if serializer.is_valid():
            medium = serializer.save()
            return Response(
                FollowUpMediumSerializer(medium).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class FollowUpMediumDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        return get_object_or_404(
            FollowUpMedium,
            pk=pk,
            is_active=True
        )

    @swagger_auto_schema(responses={200: FollowUpMediumSerializer})
    def get(self, request, pk):
        medium = self.get_object(pk)
        serializer = FollowUpMediumSerializer(medium)
        return Response(serializer.data)

    @swagger_auto_schema(
        request_body=FollowUpMediumSerializer,
        responses={200: FollowUpMediumSerializer}
    )
    def put(self, request, pk):
        medium = self.get_object(pk)
        serializer = FollowUpMediumSerializer(
            medium,
            data=request.data,
            context={"request": request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(responses={204: "Deleted"})
    def delete(self, request, pk):
        medium = self.get_object(pk)
        medium.is_active = False
        medium.save()
        return Response(
            {"message": "Follow-up medium deleted successfully."},
            status=status.HTTP_204_NO_CONTENT
        )

class InterestLevelListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        responses={200: InterestLevelSerializer(many=True)}
    )
    def get(self, request):
        levels = InterestLevel.objects.filter(is_active=True)
        serializer = InterestLevelSerializer(levels, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        request_body=InterestLevelSerializer,
        responses={201: InterestLevelSerializer}
    )
    def post(self, request):
        level_name = request.data.get("level")

        # Restore soft-deleted level
        if level_name:
            existing = InterestLevel.objects.annotate(
                level_lower=Lower("level")
            ).filter(
                level_lower=level_name.lower(),
                is_active=False
            ).first()

            if existing:
                existing.is_active = True
                existing.save()
                serializer = InterestLevelSerializer(existing)
                return Response(serializer.data, status=status.HTTP_200_OK)

        serializer = InterestLevelSerializer(
            data=request.data,
            context={"request": request}
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class InterestLevelDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        return get_object_or_404(
            InterestLevel,
            pk=pk,
            is_active=True
        )

    @swagger_auto_schema(responses={200: InterestLevelSerializer})
    def get(self, request, pk):
        level = self.get_object(pk)
        serializer = InterestLevelSerializer(level)
        return Response(serializer.data)

    @swagger_auto_schema(
        request_body=InterestLevelSerializer,
        responses={200: InterestLevelSerializer}
    )
    def put(self, request, pk):
        level = self.get_object(pk)
        serializer = InterestLevelSerializer(
            level,
            data=request.data,
            context={"request": request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(responses={204: "Deleted"})
    def delete(self, request, pk):
        level = self.get_object(pk)
        level.is_active = False
        level.save()
        return Response(
            {"message": "Interest level deleted successfully."},
            status=status.HTTP_204_NO_CONTENT
        )

class OrganizationListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        responses={200: OrganizationSerializer(many=True)}
    )
    def get(self, request):
        organizations = Organization.objects.filter(is_active=True)
        serializer = OrganizationSerializer(organizations, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        request_body=OrganizationSerializer,
        responses={201: OrganizationSerializer}
    )
    def post(self, request):
        serializer = OrganizationSerializer(
            data=request.data,
            context={"request": request}
        )
        if serializer.is_valid():
            org = serializer.save()
            return Response(
                OrganizationSerializer(org).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class OrganizationDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        return get_object_or_404(
            Organization,
            pk=pk,
            is_active=True
        )

    @swagger_auto_schema(responses={200: OrganizationSerializer})
    def get(self, request, pk):
        organization = self.get_object(pk)
        serializer = OrganizationSerializer(organization)
        return Response(serializer.data)

    @swagger_auto_schema(
        request_body=OrganizationSerializer,
        responses={200: OrganizationSerializer}
    )
    def put(self, request, pk):
        organization = self.get_object(pk)

        serializer = OrganizationSerializer(
            organization,
            data=request.data,
            context={"request": request}
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(responses={204: "Deleted"})
    def delete(self, request, pk):
        organization = self.get_object(pk)

        # Soft delete
        organization.is_active = False
        organization.save()

        # Soft delete cascade (Branches)
        Branch.objects.filter(
            organization=organization,
            is_active=True
        ).update(is_active=False)

        return Response(
            {"message": "Organization deleted successfully."},
            status=status.HTTP_204_NO_CONTENT
        )




class BranchListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        responses={
            200: openapi.Response(
                description="Branch list",
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                            "name": openapi.Schema(type=openapi.TYPE_STRING),
                            "organization": openapi.Schema(type=openapi.TYPE_INTEGER),
                            "country": openapi.Schema(type=openapi.TYPE_INTEGER),
                            "state": openapi.Schema(type=openapi.TYPE_INTEGER),
                            "city": openapi.Schema(type=openapi.TYPE_INTEGER),
                            "is_active": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                            "created_at": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                            "updated_at": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                        }
                    )
                )
            )
        }
    )
    def get(self, request):
        branches = Branch.objects.filter(is_active=True)
        serializer = BranchSerializer(branches, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["name", "organization"],
            properties={
                "name": openapi.Schema(type=openapi.TYPE_STRING),
                "organization": openapi.Schema(type=openapi.TYPE_INTEGER),
                "country": openapi.Schema(type=openapi.TYPE_INTEGER),
                "state": openapi.Schema(type=openapi.TYPE_INTEGER),
                "city": openapi.Schema(type=openapi.TYPE_INTEGER),
            }
        ),
        responses={
            201: openapi.Response(
                description="Branch created successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "name": openapi.Schema(type=openapi.TYPE_STRING),
                        "organization": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "country": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "state": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "city": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "is_active": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "created_at": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                        "updated_at": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                    }
                )
            )
        }
    )
    # def post(self, request):
    #     serializer = BranchSerializer(data=request.data, context={"request": request})
    #     if serializer.is_valid():
    #         branch = serializer.save()
    #         return Response(
    #             BranchSerializer(branch).data,
    #             status=status.HTTP_201_CREATED
    #         )
    #     return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


    def post(self, request):

        serializer = BranchSerializer(
            data=request.data,
            context={"request": request}
        )

        if serializer.is_valid():

            branch = serializer.save()

            return Response({

                "success": True,

                "message":
                    "Branch created successfully! "
                    "Here are the login credentials "
                    "for this branch. Please save "
                    "them and share with the "
                    "branch super admin.",

                "branch": BranchSerializer(branch).data,

                "credentials": {

                    "username":
                        getattr(
                            branch,
                            "generated_username",
                            None
                        ),

                    "password":
                        getattr(
                            branch,
                            "generated_password",
                            None
                        )
                }

            }, status=status.HTTP_201_CREATED)

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

from django.db import transaction

class BranchDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        return get_object_or_404(
            Branch,
            pk=pk,
            is_active=True
        )

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                "pk",
                openapi.IN_PATH,
                description="Branch ID",
                type=openapi.TYPE_INTEGER,
            )
        ],
        responses={
            200: openapi.Response(
                description="Branch details",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "name": openapi.Schema(type=openapi.TYPE_STRING),
                        "organization": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "country": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "state": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "city": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "is_active": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "created_at": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                        "updated_at": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                    }
                )
            )
        }
    )
    def get(self, request, pk):
        branch = self.get_object(pk)
        return Response(BranchSerializer(branch).data)

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                "pk",
                openapi.IN_PATH,
                description="Branch ID",
                type=openapi.TYPE_INTEGER,
            )
        ],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "name": openapi.Schema(type=openapi.TYPE_STRING),
                "organization": openapi.Schema(type=openapi.TYPE_INTEGER),
                "country": openapi.Schema(type=openapi.TYPE_INTEGER),
                "state": openapi.Schema(type=openapi.TYPE_INTEGER),
                "city": openapi.Schema(type=openapi.TYPE_INTEGER),
                "is_active": openapi.Schema(type=openapi.TYPE_BOOLEAN),
            }
        ),
        responses={200: openapi.Response(description="Branch updated successfully")}
    )
    def put(self, request, pk):
        branch = self.get_object(pk)
        serializer = BranchSerializer(
            branch,
            data=request.data,
            context={"request": request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                "pk",
                openapi.IN_PATH,
                description="Branch ID",
                type=openapi.TYPE_INTEGER,
            )
        ],
        responses={204: openapi.Response(description="Branch deleted successfully")}
    )
    def delete(self, request, pk):

        branch = self.get_object(pk)

        with transaction.atomic():

            # ==========================================
            # IF MAIN BRANCH IS DELETED
            # ASSIGN ANOTHER BRANCH AS MAIN
            # ==========================================

            if branch.is_main_branch:

                another_branch = Branch.objects.filter(
                    organization=branch.organization,
                    is_active=True
                ).exclude(
                    id=branch.id
                ).order_by("id").first()

                if another_branch:

                    another_branch.is_main_branch = True

                    another_branch.save()

            # ==========================================
            # SOFT DELETE
            # ==========================================

            branch.is_active = False

            branch.is_main_branch = False

            branch.save()

        return Response(
            {"message": "Branch deleted successfully."},
            status=status.HTTP_204_NO_CONTENT
        )

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.models import ClientUser
from master.models import Branch


class BranchDropdownAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        # =====================================
        # TOKEN DATA
        # =====================================

        token = request.auth

        client_code = token.get("client_code")

        user_id = token.get("user_id")

        db_key = f"client_{client_code}"

        # =====================================
        # FETCH CLIENT USER
        # =====================================

        user = ClientUser.objects.using(
            db_key
        ).select_related(
            "branch",
            "branch__organization"
        ).get(
            user_id=user_id,
            is_active=True
        )

        branch_id = user.branch_id

        # =====================================
        # MAIN BRANCH ADMIN
        # =====================================

        if user.branch and user.branch.is_main_branch:

            branches = Branch.objects.filter(
                organization_id=user.branch.organization_id,
                is_active=True
            )

            can_switch = True

        # =====================================
        # REGULAR USERS
        # =====================================

        else:

            branches = Branch.objects.filter(
                id=branch_id,
                is_active=True
            )

            can_switch = False

        data = []

        for branch in branches:

            data.append({
                "id": branch.id,
                "name": branch.name
            })

        return Response({

            "success": True,

            "can_switch_branch": can_switch,

            "selected_branch_id": branch_id,

            "organization_id":
                user.branch.organization_id
                if user.branch else None,

            "organization_name":
                user.branch.organization.name
                if user.branch and user.branch.organization
                else None,

            "results": data
        })


class OrganizationBranchListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organization_id):

        # Check organization exists
        organization = get_object_or_404(
            Organization,
            id=organization_id,
            is_active=True
        )

        # Get branches under organization
        branches = Branch.objects.filter(
            organization=organization,
            is_active=True
        )

        serializer = BranchSerializer(
            branches,
            many=True
        )

        return Response(serializer.data)






class SourceListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        responses={
            200: openapi.Response(
                description="Source list",
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                            "name": openapi.Schema(type=openapi.TYPE_STRING),
                            "is_active": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                            "created_at": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                            "updated_at": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                        }
                    )
                )
            )
        }
    )
    def get(self, request):
        items = Source.objects.filter(is_active=True)
        serializer = SourceSerializer(items, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        request_body=SourceSerializer,
        responses={201: SourceSerializer}
    )
    def post(self, request):
        serializer = SourceSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            source = serializer.save()
            return Response(SourceSerializer(source).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class SourceDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        return get_object_or_404(Source, pk=pk, is_active=True)

    @swagger_auto_schema(responses={200: SourceSerializer})
    def get(self, request, pk):
        item = self.get_object(pk)
        return Response(SourceSerializer(item).data)

    @swagger_auto_schema(request_body=SourceSerializer, responses={200: SourceSerializer})
    def put(self, request, pk):
        item = self.get_object(pk)
        serializer = SourceSerializer(item, data=request.data, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(responses={204: "Deleted successfully"})
    def delete(self, request, pk):
        item = self.get_object(pk)
        item.is_active = False
        item.save()
        return Response({"message": "Source deleted successfully."}, status=status.HTTP_204_NO_CONTENT)

class StatusListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        responses={
            200: openapi.Response(
                description="Status list",
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                            "name": openapi.Schema(type=openapi.TYPE_STRING),
                            "is_active": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                            "created_at": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                            "updated_at": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                        }
                    )
                )
            )
        }
    )
    def get(self, request):
        items = Status.objects.filter(is_active=True)
        serializer = StatusSerializer(items, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(request_body=StatusSerializer, responses={201: StatusSerializer})
    def post(self, request):
        serializer = StatusSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            status_obj = serializer.save()
            return Response(StatusSerializer(status_obj).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class StatusDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        return get_object_or_404(Status, pk=pk, is_active=True)

    @swagger_auto_schema(responses={200: StatusSerializer})
    def get(self, request, pk):
        instance = self.get_object(pk)
        return Response(StatusSerializer(instance).data)

    @swagger_auto_schema(request_body=StatusSerializer, responses={200: StatusSerializer})
    def put(self, request, pk):
        instance = self.get_object(pk)
        serializer = StatusSerializer(instance, data=request.data, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(responses={204: "Deleted successfully"})
    def delete(self, request, pk):
        instance = self.get_object(pk)
        instance.is_active = False
        instance.save()
        return Response({"message": "Status deleted successfully."}, status=status.HTTP_204_NO_CONTENT)

class NationalityListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        responses={
            200: openapi.Response(
                description="Nationality list",
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                            "name": openapi.Schema(type=openapi.TYPE_STRING),
                            "country": openapi.Schema(type=openapi.TYPE_INTEGER),
                            "is_active": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                            "created_at": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                            "updated_at": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                        }
                    )
                )
            )
        }
    )
    def get(self, request):
        items = Nationality.objects.filter(is_active=True)
        serializer = NationalitySerializer(items, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["name", "country"],
            properties={
                "name": openapi.Schema(type=openapi.TYPE_STRING),
                "country": openapi.Schema(type=openapi.TYPE_INTEGER),
            }
        ),
        responses={
            201: openapi.Response(
                description="Nationality created successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "name": openapi.Schema(type=openapi.TYPE_STRING),
                        "country": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "is_active": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "created_at": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                        "updated_at": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                    }
                )
            )
        }
    )
    def post(self, request):
        serializer = NationalitySerializer(
            data=request.data,
            context={"request": request}
        )
        if serializer.is_valid():
            nationality = serializer.save()
            return Response(
                NationalitySerializer(nationality).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class NationalityDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        return get_object_or_404(
            Nationality,
            pk=pk,
            is_active=True
        )

    @swagger_auto_schema(
        responses={
            200: openapi.Response(
                description="Nationality details",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "name": openapi.Schema(type=openapi.TYPE_STRING),
                        "country": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "is_active": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "created_at": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                        "updated_at": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                    }
                )
            )
        }
    )
    def get(self, request, pk):
        instance = self.get_object(pk)
        return Response(NationalitySerializer(instance).data)

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "name": openapi.Schema(type=openapi.TYPE_STRING),
                "country": openapi.Schema(type=openapi.TYPE_INTEGER),
                "is_active": openapi.Schema(type=openapi.TYPE_BOOLEAN),
            }
        ),
        responses={
            200: openapi.Response(
                description="Nationality updated successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "name": openapi.Schema(type=openapi.TYPE_STRING),
                        "country": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "is_active": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "created_at": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                        "updated_at": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                    }
                )
            )
        }
    )
    def put(self, request, pk):
        instance = self.get_object(pk)

        serializer = NationalitySerializer(
            instance,
            data=request.data,
            context={"request": request}
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        responses={
            204: openapi.Response(
                description="Nationality deleted successfully"
            )
        }
    )
    def delete(self, request, pk):
        instance = self.get_object(pk)

        instance.is_active = False
        instance.save()

        return Response(
            {"message": "Nationality deleted successfully."},
            status=status.HTTP_204_NO_CONTENT
        )

class FormDesignListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        responses={
            200: openapi.Response(
                description="Form designs list",
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                            "name": openapi.Schema(type=openapi.TYPE_STRING),
                            "is_active": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                            "created_at": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                            "updated_at": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                        }
                    )
                )
            )
        }
    )
    def get(self, request):
        items = FormDesign.objects.all()
        serializer = FormDesignSerializer(items, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["name"],
            properties={
                "name": openapi.Schema(type=openapi.TYPE_STRING),
                "is_active": openapi.Schema(type=openapi.TYPE_BOOLEAN),
            }
        ),
        responses={
            201: openapi.Response(
                description="Form design created successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "name": openapi.Schema(type=openapi.TYPE_STRING),
                        "is_active": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "created_at": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                        "updated_at": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                    }
                )
            )
        }
    )
    def post(self, request):
        serializer = FormDesignSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class FormDesignDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        return get_object_or_404(FormDesign, pk=pk)

    @swagger_auto_schema(
        responses={
            200: openapi.Response(
                description="Form design details",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "name": openapi.Schema(type=openapi.TYPE_STRING),
                        "is_active": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "created_at": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                        "updated_at": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                    }
                )
            )
        }
    )
    def get(self, request, pk):
        item = self.get_object(pk)
        serializer = FormDesignSerializer(item)
        return Response(serializer.data)

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "name": openapi.Schema(type=openapi.TYPE_STRING),
                "is_active": openapi.Schema(type=openapi.TYPE_BOOLEAN),
            }
        ),
        responses={
            200: openapi.Response(
                description="Form design updated successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "name": openapi.Schema(type=openapi.TYPE_STRING),
                        "is_active": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "created_at": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                        "updated_at": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                    }
                )
            )
        }
    )
    def put(self, request, pk):
        item = self.get_object(pk)
        serializer = FormDesignSerializer(item, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        responses={
            204: openapi.Response(
                description="Form design deleted successfully"
            )
        }
    )
    def delete(self, request, pk):
        item = self.get_object(pk)
        item.delete()
        return Response(
            {"message": "Deleted successfully."},
            status=status.HTTP_204_NO_CONTENT
        )

class EmailConfigurationListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        responses={
            200: openapi.Response(
                description="Email configurations list",
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                            "smtp_host": openapi.Schema(type=openapi.TYPE_STRING),
                            "sender_email": openapi.Schema(type=openapi.TYPE_STRING),
                            "is_active": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                            "created_at": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                            "updated_at": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                        }
                    )
                )
            )
        }
    )
    def get(self, request):
        items = EmailConfigurations.objects.filter(is_active=True)
        serializer = EmailConfigurationsSerializer(items, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        request_body=EmailConfigurationsSerializer,
        responses={
            201: openapi.Response(
                description="Email configuration created successfully",
                schema=EmailConfigurationsSerializer
            )
        }
    )
    def post(self, request):
        serializer = EmailConfigurationsSerializer(
            data=request.data,
            context={"request": request}
        )
        if serializer.is_valid():
            config = serializer.save()
            return Response(
                EmailConfigurationsSerializer(config).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class EmailConfigurationDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        return get_object_or_404(
            EmailConfigurations,
            id=pk,
            is_active=True
        )

    @swagger_auto_schema(
        responses={
            200: openapi.Response(
                description="Email configuration details",
                schema=EmailConfigurationsSerializer
            )
        }
    )
    def get(self, request, pk):
        item = self.get_object(pk)
        serializer = EmailConfigurationsSerializer(item)
        return Response(serializer.data)

    @swagger_auto_schema(
        request_body=EmailConfigurationsSerializer,
        responses={
            200: openapi.Response(
                description="Email configuration updated successfully",
                schema=EmailConfigurationsSerializer
            )
        }
    )
    def put(self, request, pk):
        item = self.get_object(pk)

        serializer = EmailConfigurationsSerializer(
            item,
            data=request.data,
            context={"request": request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        responses={
            204: openapi.Response(
                description="Email configuration deleted successfully"
            )
        }
    )
    def delete(self, request, pk):
        item = self.get_object(pk)

        # 🔒 Soft delete
        item.is_active = False
        item.save(update_fields=["is_active"])

        return Response(
            {"detail": "Email configuration deleted successfully."},
            status=status.HTTP_204_NO_CONTENT
        )

class SMSConfigurationListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        responses={
            200: openapi.Response(
                description="SMS configurations list",
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                            "provider_name": openapi.Schema(type=openapi.TYPE_STRING),
                            "sender_id": openapi.Schema(type=openapi.TYPE_STRING),
                            "is_active": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                            "created_at": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                            "updated_at": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                        }
                    )
                )
            )
        }
    )
    def get(self, request):
        items = SMSConfiguration.objects.filter(is_active=True)
        serializer = SMSConfigurationSerializer(items, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "provider_name": openapi.Schema(type=openapi.TYPE_STRING),
                "sender_id": openapi.Schema(type=openapi.TYPE_STRING),
                "username": openapi.Schema(type=openapi.TYPE_STRING),
                "password": openapi.Schema(type=openapi.TYPE_STRING),
                "api_key": openapi.Schema(type=openapi.TYPE_STRING),
            }
        ),
        responses={
            201: openapi.Response(
                description="SMS configuration created successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "provider_name": openapi.Schema(type=openapi.TYPE_STRING),
                        "sender_id": openapi.Schema(type=openapi.TYPE_STRING),
                        "is_active": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "created_at": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                        "updated_at": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                    }
                )
            )
        }
    )
    def post(self, request):
        serializer = SMSConfigurationSerializer(
            data=request.data,
            context={"request": request}
        )

        if serializer.is_valid():
            sms_config = serializer.save()
            return Response(
                SMSConfigurationSerializer(sms_config).data,
                status=status.HTTP_201_CREATED
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class SMSConfigurationDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        return get_object_or_404(
            SMSConfiguration,
            id=pk,
            is_active=True
        )

    @swagger_auto_schema(
        responses={
            200: openapi.Response(
                description="SMS configuration details",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "provider_name": openapi.Schema(type=openapi.TYPE_STRING),
                        "sender_id": openapi.Schema(type=openapi.TYPE_STRING),
                        "is_active": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "created_at": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                        "updated_at": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                    }
                )
            )
        }
    )
    def get(self, request, pk):
        item = self.get_object(pk)
        serializer = SMSConfigurationSerializer(item)
        return Response(serializer.data)

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "provider_name": openapi.Schema(type=openapi.TYPE_STRING),
                "sender_id": openapi.Schema(type=openapi.TYPE_STRING),
                "username": openapi.Schema(type=openapi.TYPE_STRING),
                "password": openapi.Schema(type=openapi.TYPE_STRING),
                "api_key": openapi.Schema(type=openapi.TYPE_STRING),
                "is_active": openapi.Schema(type=openapi.TYPE_BOOLEAN),
            }
        ),
        responses={
            200: openapi.Response(
                description="SMS configuration updated successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "provider_name": openapi.Schema(type=openapi.TYPE_STRING),
                        "sender_id": openapi.Schema(type=openapi.TYPE_STRING),
                        "is_active": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "created_at": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                        "updated_at": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                    }
                )
            )
        }
    )
    def put(self, request, pk):
        item = self.get_object(pk)

        serializer = SMSConfigurationSerializer(
            item,
            data=request.data,
            context={"request": request}
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        responses={
            204: openapi.Response(
                description="SMS configuration deleted successfully"
            )
        }
    )
    def delete(self, request, pk):
        item = self.get_object(pk)

        # 🔒 Soft delete
        item.is_active = False
        item.save(update_fields=["is_active"])

        return Response(
            {"detail": "SMS configuration deleted successfully."},
            status=status.HTTP_204_NO_CONTENT
        )


class PaymentMethodListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated] # Add your custom permission classes here

    @swagger_auto_schema(
        operation_summary="List Payment Methods",
        operation_description="Retrieve all active payment methods (Cash, Bank, UPI, etc.).",
        responses={
            200: openapi.Response(
                description="List of payment methods",
                schema=PaymentMethodSerializer(many=True)
            )
        }
    )
    def get(self, request):
        # You can filter by organization/branch if PaymentMethod is tenant-specific
        methods = PaymentMethod.objects.filter(is_active=True).order_by('name')
        serializer = PaymentMethodSerializer(methods, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Create Payment Method",
        operation_description="Add a new payment method to the system.",
        request_body=PaymentMethodSerializer,
        responses={
            201: openapi.Response(
                description="Created successfully",
                schema=PaymentMethodSerializer
            ),
            400: "Validation Error"
        }
    )
    def post(self, request):
        serializer = PaymentMethodSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PaymentMethodDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        return get_object_or_404(PaymentMethod, pk=pk, is_active=True)

    @swagger_auto_schema(
        operation_summary="Retrieve Payment Method",
        responses={200: PaymentMethodSerializer, 404: "Not Found"}
    )
    def get(self, request, pk):
        method = self.get_object(pk)
        serializer = PaymentMethodSerializer(method)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="Update Payment Method",
        request_body=PaymentMethodSerializer,
        responses={200: PaymentMethodSerializer, 400: "Validation Error"}
    )
    def put(self, request, pk):
        method = self.get_object(pk)
        serializer = PaymentMethodSerializer(method, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_summary="Delete Payment Method",
        operation_description="Soft delete a payment method.",
        responses={204: "Deleted successfully"}
    )
    def delete(self, request, pk):
        method = self.get_object(pk)
        # Soft delete
        method.is_active = False
        method.save()
        return Response(
            {"message": "Payment method deactivated successfully."},
            status=status.HTTP_204_NO_CONTENT
        )



# from datetime import timedelta

# from django.db.models import Sum

# from django.utils import timezone

# from rest_framework.views import APIView
# from rest_framework.permissions import IsAuthenticated
# from rest_framework.response import Response

# from student_details.models import (
#     Enquiry,
#     EnquiryFollowUp
    
# )

# from staff.models import Employee
# from course.models import Course, Batch

# from fee_details.models import (
#     FeeGeneration,
#     FeeDeposit,
#     FeeInstallment
# )

# from admission.models import (
#     Admission,
#     CertificateApproval,
#     CertificateIssue
# )

# from assignment.models import (
#     AssignmentSubmission
# )

# from admission.models import Attendance as StudentAttendance

# from staff.models import Attendance as StaffAttendance

# from staff.models import StudentLoginHistory



# class MasterDashboardAPIView(APIView):

#     permission_classes = [IsAuthenticated]

#     def get(self, request):

#         organization_id = request.query_params.get(
#             "organization_id"
#         )

#         branch_id = request.query_params.get(
#             "branch_id"
#         )

#         today = timezone.localdate()

#         days_from_sunday = (
#             today.weekday() + 1
#         ) % 7

#         week_start = today - timedelta(
#             days=days_from_sunday
#         )

#         week_end = week_start + timedelta(
#             days=6
#         )

#         month_start = today.replace(
#             day=1
#         )

#         # =====================================
#         # HELPER
#         # =====================================

#         from django.db.models import DateField, DateTimeField

#         def get_counts(queryset, field_name):

#             field = queryset.model._meta.get_field(
#                 field_name
#             )

#             is_date_only = (
#                 isinstance(field, DateField)
#                 and not isinstance(field, DateTimeField)
#             )

#             if is_date_only:

#                 today_count = queryset.filter(
#                     **{
#                         field_name: today
#                     }
#                 ).count()

#                 week_count = queryset.filter(
#                     **{
#                         f"{field_name}__range":
#                         [week_start, week_end]
#                     }
#                 ).count()

#                 month_count = queryset.filter(
#                     **{
#                         f"{field_name}__gte":
#                         month_start
#                     }
#                 ).count()

#             else:

#                 today_count = queryset.filter(
#                     **{
#                         f"{field_name}__date": today
#                     }
#                 ).count()

#                 week_count = queryset.filter(
#                     **{
#                         f"{field_name}__date__range":
#                         [week_start, week_end]
#                     }
#                 ).count()

#                 month_count = queryset.filter(
#                     **{
#                         f"{field_name}__date__gte":
#                         month_start
#                     }
#                 ).count()

#             return {
#                 "total": queryset.count(),
#                 "today": today_count,
#                 "week": week_count,
#                 "month": month_count
#             }

#         # =====================================
#         # ENQUIRY
#         # =====================================

#         enquiries = Enquiry.objects.filter(
#             is_active=True
#         )

#         if organization_id:
#             enquiries = enquiries.filter(
#                 organization_id=organization_id
#             )

#         if branch_id:
#             enquiries = enquiries.filter(
#                 branch_id=branch_id
#             )

#         # =====================================
#         # FOLLOWUP
#         # =====================================

#         followups = EnquiryFollowUp.objects.filter(
#             is_active=True
#         )

#         if organization_id:
#             followups = followups.filter(
#                 enquiry__organization_id=organization_id
#             )

#         if branch_id:
#             followups = followups.filter(
#                 enquiry__branch_id=branch_id
#             )

#         # =====================================
#         # COURSES
#         # =====================================

#         courses = Course.objects.filter(
#             is_active=True
#         )

#         if organization_id:
#             courses = courses.filter(
#                 organization_id=organization_id
#             )

#         if branch_id:
#             courses = courses.filter(
#                 branch_id=branch_id
#             )

#         # =====================================
#         # BATCHES
#         # =====================================

#         batches = Batch.objects.filter(
#             is_active=True
#         )

#         if organization_id:
#             batches = batches.filter(
#                 organization_id=organization_id
#             )

#         if branch_id:
#             batches = batches.filter(
#                 branch_id=branch_id
#             )

#         # =====================================
#         # ADMISSIONS
#         # =====================================

#         admissions = Admission.objects.filter(
#             is_active=True
#         )

#         if organization_id:
#             admissions = admissions.filter(
#                 organization_id=organization_id
#             )

#         if branch_id:
#             admissions = admissions.filter(
#                 branch_id=branch_id
#             )

#         # =====================================
#         # EMPLOYEES
#         # =====================================

#         employees = Employee.objects.filter(
#             is_active=True
#         )

#         if organization_id:
#             employees = employees.filter(
#                 organization_id=organization_id
#             )

#         if branch_id:
#             employees = employees.filter(
#                 branch_id=branch_id
#             )

#         # =====================================
#         # FEE DEPOSITS
#         # =====================================

#         deposits = FeeDeposit.objects.filter(
#             is_active=True
#         )

#         if organization_id:
#             deposits = deposits.filter(
#                 installment__fee_generation__organization_id=
#                 organization_id
#             )

#         if branch_id:
#             deposits = deposits.filter(
#                 installment__fee_generation__branch_id=
#                 branch_id
#             )

#         # =====================================
#         # DUES
#         # =====================================

#         dues = FeeInstallment.objects.filter(
#             is_active=True,
#             is_paid=False
#         )

#         if organization_id:
#             dues = dues.filter(
#                 fee_generation__organization_id=
#                 organization_id
#             )

#         if branch_id:
#             dues = dues.filter(
#                 fee_generation__branch_id=
#                 branch_id
#             )

#         # =====================================
#         # CERTIFICATE APPROVALS
#         # =====================================

#         approvals = CertificateApproval.objects.filter(
#             is_active=True
#         )

#         if organization_id:
#             approvals = approvals.filter(
#                 organization_id=organization_id
#             )

#         if branch_id:
#             approvals = approvals.filter(
#                 branch_id=branch_id
#             )

#         # =====================================
#         # CERTIFICATE ISSUED
#         # =====================================

#         certificates = CertificateIssue.objects.filter(
#             is_active=True
#         )

#         if organization_id:
#             certificates = certificates.filter(
#                 organization_id=organization_id
#             )

#         if branch_id:
#             certificates = certificates.filter(
#                 branch_id=branch_id
#             )

#         # =====================================
#         # ASSIGNMENT REVIEW PENDING
#         # =====================================

#         assignments_pending = AssignmentSubmission.objects.filter(
#             is_active=True,
#             is_reviewed=False
#         )

#         # =====================================
#         # STUDENT ATTENDANCE
#         # =====================================

#         student_attendance = StudentAttendance.objects.filter(
#             is_active=True
#         )

#         if organization_id:
#             student_attendance = student_attendance.filter(
#                 admission__organization_id=organization_id
#             )

#         if branch_id:
#             student_attendance = student_attendance.filter(
#                 admission__branch_id=branch_id
#             )

#         # =====================================
#         # STAFF ATTENDANCE
#         # =====================================

#         staff_attendance = StaffAttendance.objects.filter(
#             is_active=True
#         )

#         if organization_id:
#             staff_attendance = staff_attendance.filter(
#                 employee__organization_id=organization_id
#             )

#         if branch_id:
#             staff_attendance = staff_attendance.filter(
#                 employee__branch_id=branch_id
#             )

#         # =====================================
#         # STUDENT LOGINS
#         # =====================================

#         student_logins = StudentLoginHistory.objects.filter(
#             is_active=True
#         )

#         if organization_id:
#             student_logins = student_logins.filter(
#                 organization_id=organization_id
#             )

#         if branch_id:
#             student_logins = student_logins.filter(
#                 branch_id=branch_id
#             )

#         return Response({

#             "success": True,

#             "filters": {
#                 "organization_id": organization_id,
#                 "branch_id": branch_id
#             },

#             "dashboard": {

#                 "enquiries":
#                     get_counts(
#                         enquiries,
#                         "created_at"
#                     ),

#                 "followups":
#                     get_counts(
#                         followups,
#                         "created_at"
#                     ),

#                 "courses":
#                     get_counts(
#                         courses,
#                         "created_at"
#                     ),

#                 "batches":
#                     get_counts(
#                         batches,
#                         "created_at"
#                     ),

#                 "admissions":
#                     get_counts(
#                         admissions,
#                         "created_at"
#                     ),

#                 "employees":
#                     get_counts(
#                         employees,
#                         "created_at"
#                     ),

#                 "fee_deposits":
#                     get_counts(
#                         deposits,
#                         "created_at"
#                     ),

#                 "dues":
#                     get_counts(
#                         dues,
#                         "created_at"
#                     ),

#                 "certificate_approvals":
#                     get_counts(
#                         approvals,
#                         "created_at"
#                     ),

#                 "certificates_issued":
#                     get_counts(
#                         certificates,
#                         "created_at"
#                     ),

#                 "assignment_review_pending":
#                     get_counts(
#                         assignments_pending,
#                         "submitted_at"
#                     ),

#                 "student_attendance":
#                     get_counts(
#                         student_attendance,
#                         "date"
#                     ),

#                 "staff_attendance":
#                     get_counts(
#                         staff_attendance,
#                         "date"
#                     ),

#                 "student_logins":
#                     get_counts(
#                         student_logins,
#                         "login_datetime"
#                     ),

#                 "total_collection": (
#                     deposits.aggregate(
#                         total=Sum("paid_amount")
#                     )["total"] or 0
#                 )
#             }
#         })
    


from datetime import timedelta

from django.db.models import Sum
from django.db.models import DateField, DateTimeField
from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from student_details.models import (
    Enquiry,
    EnquiryFollowUp
)

from staff.models import (
    Employee,
    Attendance as StaffAttendance,
    StudentLoginHistory
)

from course.models import (
    Course,
    Batch
)

from fee_details.models import (
    FeeGeneration,
    FeeDeposit,
    FeeInstallment
)

from admission.models import (
    Admission,
    CertificateApproval,
    CertificateIssue,
    Attendance as StudentAttendance
)

from assignment.models import (
    AssignmentSubmission
)


# =====================================
# FILTER HELPER
# =====================================

def apply_org_branch_filter(
    queryset,
    organization_id=None,
    branch_id=None,
    org_path=None,
    branch_path=None
):

    if organization_id and org_path:
        queryset = queryset.filter(
            **{
                org_path: organization_id
            }
        )

    if branch_id and branch_path:
        queryset = queryset.filter(
            **{
                branch_path: branch_id
            }
        )

    return queryset


# =====================================
# COUNT HELPER
# =====================================

def get_counts(
    queryset,
    field_name,
    today,
    week_start,
    week_end,
    month_start
):

    field = queryset.model._meta.get_field(
        field_name
    )

    is_date_only = (
        isinstance(field, DateField)
        and not isinstance(field, DateTimeField)
    )

    if is_date_only:

        today_count = queryset.filter(
            **{
                field_name: today
            }
        ).count()

        week_count = queryset.filter(
            **{
                f"{field_name}__range":
                [week_start, week_end]
            }
        ).count()

        month_count = queryset.filter(
            **{
                f"{field_name}__gte":
                month_start
            }
        ).count()

    else:

        today_count = queryset.filter(
            **{
                f"{field_name}__date": today
            }
        ).count()

        week_count = queryset.filter(
            **{
                f"{field_name}__date__range":
                [week_start, week_end]
            }
        ).count()

        month_count = queryset.filter(
            **{
                f"{field_name}__date__gte":
                month_start
            }
        ).count()

    return {
        "total": queryset.count(),
        "today": today_count,
        "week": week_count,
        "month": month_count
    }


class MasterDashboardAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        organization_id = request.query_params.get(
            "organization_id"
        )

        branch_id = request.query_params.get(
            "branch_id"
        )

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
        # ENQUIRIES
        # NOTE:
        # Update these paths according to your
        # Enquiry model relationships.
        # =====================================

        enquiries = apply_org_branch_filter(
            Enquiry.objects.filter(
                is_active=True
            ),
            organization_id,
            branch_id,
            "assigned_to__organization_id",
            "assigned_to__branch_id"
        )

        followups = apply_org_branch_filter(
            EnquiryFollowUp.objects.filter(
                is_active=True
            ),
            organization_id,
            branch_id,
            "assigned_to__organization_id",
            "assigned_to__branch_id"
        )

        # =====================================
        # COURSES
        # =====================================

        courses = apply_org_branch_filter(
            Course.objects.filter(
                is_active=True
            ),
            organization_id,
            branch_id,
            "organization_id",
            "branch_id"
        )

        # =====================================
        # BATCHES
        # =====================================

        batches = apply_org_branch_filter(
            Batch.objects.filter(
                is_active=True
            ),
            organization_id,
            branch_id,
            "organization_id",
            "branch_id"
        )

        # =====================================
        # ADMISSIONS
        # =====================================

        admissions = apply_org_branch_filter(
            Admission.objects.filter(
                is_active=True
            ),
            organization_id,
            branch_id,
            "organization_id",
            "branch_id"
        )

        # =====================================
        # EMPLOYEES
        # =====================================

        employees = apply_org_branch_filter(
            Employee.objects.filter(
                is_active=True
            ),
            organization_id,
            branch_id,
            "organization_id",
            "branch_id"
        )

        # =====================================
        # FEE GENERATION
        # =====================================

        fee_generations = apply_org_branch_filter(
            FeeGeneration.objects.filter(
                is_active=True
            ),
            organization_id,
            branch_id,
            "organization_id",
            "branch_id"
        )

        # =====================================
        # FEE DEPOSITS
        # =====================================

        deposits = apply_org_branch_filter(
            FeeDeposit.objects.filter(
                is_active=True
            ),
            organization_id,
            branch_id,
            "installment__fee_generation__organization_id",
            "installment__fee_generation__branch_id"
        )

        # =====================================
        # DUES
        # =====================================

        dues = apply_org_branch_filter(
            FeeInstallment.objects.filter(
                is_active=True,
                is_paid=False
            ),
            organization_id,
            branch_id,
            "fee_generation__organization_id",
            "fee_generation__branch_id"
        )

        # =====================================
        # CERTIFICATE APPROVALS
        # =====================================

        approvals = apply_org_branch_filter(
            CertificateApproval.objects.filter(
                is_active=True
            ),
            organization_id,
            branch_id,
            "organization_id",
            "branch_id"
        )

        # =====================================
        # CERTIFICATE ISSUED
        # =====================================

        certificates = apply_org_branch_filter(
            CertificateIssue.objects.filter(
                is_active=True
            ),
            organization_id,
            branch_id,
            "organization_id",
            "branch_id"
        )

        # =====================================
        # ASSIGNMENT REVIEW PENDING
        # =====================================

        assignments_pending = apply_org_branch_filter(
            AssignmentSubmission.objects.filter(
                is_active=True,
                is_reviewed=False
            ),
            organization_id,
            branch_id,
            "assignment__teacher__organization_id",
            "assignment__teacher__branch_id"
        )

        # =====================================
        # STUDENT ATTENDANCE
        # =====================================

        student_attendance = apply_org_branch_filter(
            StudentAttendance.objects.filter(
                is_active=True
            ),
            organization_id,
            branch_id,
            "admission__organization_id",
            "admission__branch_id"
        )

        # =====================================
        # STAFF ATTENDANCE
        # =====================================

        staff_attendance = apply_org_branch_filter(
            StaffAttendance.objects.filter(
                is_active=True
            ),
            organization_id,
            branch_id,
            "employee__organization_id",
            "employee__branch_id"
        )

        # =====================================
        # STUDENT LOGIN HISTORY
        # =====================================

        student_logins = apply_org_branch_filter(
            StudentLoginHistory.objects.filter(
                is_active=True
            ),
            organization_id,
            branch_id,
            "organization_id",
            "branch_id"
        )

        return Response({

            "success": True,

            "filters": {
                "organization_id": organization_id,
                "branch_id": branch_id
            },

            "dashboard": {

                "enquiries": get_counts(
                    enquiries,
                    "created_at",
                    today,
                    week_start,
                    week_end,
                    month_start
                ),

                "followups": get_counts(
                    followups,
                    "created_at",
                    today,
                    week_start,
                    week_end,
                    month_start
                ),

                "courses": get_counts(
                    courses,
                    "created_at",
                    today,
                    week_start,
                    week_end,
                    month_start
                ),

                "batches": get_counts(
                    batches,
                    "created_at",
                    today,
                    week_start,
                    week_end,
                    month_start
                ),

                "admissions": get_counts(
                    admissions,
                    "created_at",
                    today,
                    week_start,
                    week_end,
                    month_start
                ),

                "employees": get_counts(
                    employees,
                    "created_at",
                    today,
                    week_start,
                    week_end,
                    month_start
                ),

                "fee_generations": get_counts(
                    fee_generations,
                    "created_at",
                    today,
                    week_start,
                    week_end,
                    month_start
                ),

                "fee_deposits": get_counts(
                    deposits,
                    "created_at",
                    today,
                    week_start,
                    week_end,
                    month_start
                ),

                "dues": get_counts(
                    dues,
                    "due_date",
                    today,
                    week_start,
                    week_end,
                    month_start
                ),

                "certificate_approvals": get_counts(
                    approvals,
                    "created_at",
                    today,
                    week_start,
                    week_end,
                    month_start
                ),

                "certificates_issued": get_counts(
                    certificates,
                    "created_at",
                    today,
                    week_start,
                    week_end,
                    month_start
                ),

                "assignment_review_pending": get_counts(
                    assignments_pending,
                    "submitted_at",
                    today,
                    week_start,
                    week_end,
                    month_start
                ),

                "student_attendance": get_counts(
                    student_attendance,
                    "date",
                    today,
                    week_start,
                    week_end,
                    month_start
                ),

                "staff_attendance": get_counts(
                    staff_attendance,
                    "date",
                    today,
                    week_start,
                    week_end,
                    month_start
                ),

                "student_logins": get_counts(
                    student_logins,
                    "login_datetime",
                    today,
                    week_start,
                    week_end,
                    month_start
                ),

                "total_collection": (
                    deposits.aggregate(
                        total=Sum("paid_amount")
                    )["total"] or 0
                )
            }
        })

    