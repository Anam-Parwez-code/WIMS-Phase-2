from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Employee, StaffUser, Attendance, UserRole
from admission.models import Admission
from django.db.models.functions import Lower
from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.db.models import F
from settings_app.models import CodePrefix
from core.models import ClientUser
from master.models import Branch

User = get_user_model()

class EmployeeSerializer(serializers.ModelSerializer):
    organization_name = serializers.ReadOnlyField(source='organization.name')
    branch_name = serializers.ReadOnlyField(source='branch.name')
    department_name = serializers.ReadOnlyField(source='department.name')
    designation_name = serializers.ReadOnlyField(source='designation.name')
    country_name = serializers.ReadOnlyField(source='country.name')
    state_name = serializers.ReadOnlyField(source='state.name')
    city_name = serializers.ReadOnlyField(source='city.name')

    class Meta:
        model = Employee
        fields = [
            "id", "name", "employee_code", "email", "phone", "mobile",
            "organization", "organization_name", "branch", "branch_name",
            "department", "department_name",
            "designation", "designation_name",
            "country", "country_name",
            "state", "state_name",
            "city", "city_name",
            "address", "dob", "date_of_joining", "gender", "marital_status",
            "salary", "resume", "profile_photo", "is_active"
        ]
        read_only_fields = ["is_active", "employee_code"]

    def validate(self, data):
        # branch_id = self.context.get("branch_id")
        # if branch_id:
        #     try:
        #         # Assign the actual object, not just the ID
        #         data["branch"] = Branch.objects.get(id=branch_id)
        #     except Branch.DoesNotExist:
        #         raise serializers.ValidationError({"branch": "Invalid branch ID provided in context."})

        
        organization = data.get("organization") or getattr(self.instance, "organization", None)
        branch = data.get("branch") or getattr(self.instance, "branch", None)
        department = data.get("department") or getattr(self.instance, "department", None)
        designation = data.get("designation") or getattr(self.instance, "designation", None)
        country = data.get("country") or getattr(self.instance, "country", None)
        state = data.get("state") or getattr(self.instance, "state", None)
        city = data.get("city") or getattr(self.instance, "city", None)
        


        # Organization active check
        if organization and not organization.is_active:
            raise serializers.ValidationError({
                "organization": "Organization is inactive."
            })
        

        # ==========================
        # Branch belongs to Organization
        # ==========================
        if branch and organization:
            if branch.organization_id != organization.id:
                raise serializers.ValidationError({
                    "branch": "Selected branch does not belong to the selected organization."
                })
            

        # Department / Designation validation
        if designation and department and designation.department_id != department.id:
            raise serializers.ValidationError({
                "designation": "Designation does not belong to selected department."
            })

        # Country / State / City hierarchy
        if state and country and state.country_id != country.id:
            raise serializers.ValidationError({
                "state": "State does not belong to selected country."
            })

        if city and state and city.state_id != state.id:
            raise serializers.ValidationError({
                "city": "City does not belong to selected state."
            })

        return data

    def create(self, validated_data):

        with transaction.atomic():
            prefix_obj = CodePrefix.objects.select_for_update().filter(
                module__iexact="staff",
                form__iexact="Employee",
                is_active=True
            ).first()

            if not prefix_obj:
                raise serializers.ValidationError("Employee prefix configuration missing.")

            prefix_obj.current_number += 1

            if prefix_obj.current_number > 99999:
                raise serializers.ValidationError(
                    "Employee code limit exceeded."
                )

            prefix_obj.save()

            employee_code = (
                f"{prefix_obj.prefix}"
                f"{str(prefix_obj.current_number).zfill(5)}"
            )

            validated_data["employee_code"] = employee_code

            return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data.pop("employee_code", None)
        return super().update(instance, validated_data)




class UserRoleSerializer(serializers.ModelSerializer):

    class Meta:
        model = UserRole
        fields = "__all__"
        read_only_fields = ["is_active"]

    def validate_name(self, value):

        qs = UserRole.objects.annotate(
            name_lower=Lower("name")
        ).filter(
            name_lower=value.lower(),
            is_active=True
        )

        if self.instance:
            qs = qs.exclude(id=self.instance.id)

        if qs.exists():
            raise serializers.ValidationError(
                "User role name must be unique."
            )

        return value



# class AttendanceSerializer(serializers.ModelSerializer):
#     employee_name = serializers.ReadOnlyField(source='employee.name')
#     employee_code = serializers.ReadOnlyField(source='employee.employee_code')

#     class Meta:
#         model = Attendance
#         fields = [
#             "id", "date", "present",
#             "employee", "employee_name", "employee_code",
#             "is_active"
#         ]
#         read_only_fields = ["is_active"]

#     def validate(self, data):

#         employee = data.get("employee") or getattr(self.instance, "employee", None)
#         date = data.get("date") or getattr(self.instance, "date", None)

#         if not employee:
#             raise serializers.ValidationError({"employee": "Employee is required."})

#         if not date:
#             raise serializers.ValidationError({"date": "Date is required."})

#         if not employee.is_active:
#             raise serializers.ValidationError({
#                 "employee": "Employee is inactive."
#             })

#         qs = Attendance.objects.filter(
#             employee=employee,
#             date=date,
#             is_active=True
#         )

#         if self.instance:
#             qs = qs.exclude(id=self.instance.id)

#         if qs.exists():
#             raise serializers.ValidationError({
#                 "non_field_errors": "Attendance already marked for this employee on this date."
#             })

#         return data

from datetime import datetime
from rest_framework import serializers

class AttendanceSerializer(serializers.ModelSerializer):

    employee_name = serializers.ReadOnlyField(
        source="employee.name"
    )

    employee_code = serializers.ReadOnlyField(
        source="employee.employee_code"
    )

    # Display formatted duration
    total_hours = serializers.SerializerMethodField()

    # Display email instead of user id
    marked_by = serializers.SerializerMethodField()

    # Display day name
    day = serializers.SerializerMethodField()

    class Meta:

        model = Attendance

        fields = [

            "id",

            "employee",
            "employee_name",
            "employee_code",

            "date",
            "day",

            "status",

            "time_in",
            "time_out",

            "total_hours",

            "remark",

            "marked_by",

            "is_active"

        ]

        read_only_fields = (
            "is_active",
            "total_hours",
            "marked_by"
        )

    # =====================================
    # DAY
    # =====================================

    def get_day(self, obj):

        if obj.date:
            return obj.date.strftime("%A")

        return None

    # =====================================
    # TOTAL HOURS
    # =====================================

    def get_total_hours(self, obj):

        if not obj.time_in or not obj.time_out:
            return None

        start = datetime.combine(
            obj.date,
            obj.time_in
        )

        end = datetime.combine(
            obj.date,
            obj.time_out
        )

        diff = end - start

        total_seconds = int(diff.total_seconds())

        hours = total_seconds // 3600

        minutes = (total_seconds % 3600) // 60

        return f"{hours} hr {minutes} min"

    # =====================================
    # MARKED BY
    # =====================================

    def get_marked_by(self, obj):

        if obj.marked_by:
            return obj.marked_by.email

        return None

    # =====================================
    # VALIDATION
    # =====================================

    def validate(self, data):

        employee = data.get(
            "employee",
            self.instance.employee if self.instance else None
        )

        date = data.get(
            "date",
            self.instance.date if self.instance else None
        )

        status = data.get(
            "status",
            self.instance.status if self.instance else None
        )

        time_in = data.get(
            "time_in",
            self.instance.time_in if self.instance else None
        )

        time_out = data.get(
            "time_out",
            self.instance.time_out if self.instance else None
        )

        # =====================================
        # REQUIRED VALIDATIONS
        # =====================================

        if not employee:

            raise serializers.ValidationError({
                "employee": "Employee is required."
            })

        if not date:

            raise serializers.ValidationError({
                "date": "Date is required."
            })

        if not employee.is_active:

            raise serializers.ValidationError({
                "employee": "Employee is inactive."
            })

        # =====================================
        # DUPLICATE CHECK
        # =====================================

        qs = Attendance.objects.filter(
            employee=employee,
            date=date,
            is_active=True
        )

        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():

            raise serializers.ValidationError({
                "non_field_errors":
                    "Attendance already marked for this employee on this date."
            })

        # =====================================
        # PARSE TIME STRINGS
        # =====================================

        if isinstance(time_in, str):

            try:
                time_in = datetime.strptime(
                    time_in,
                    "%H:%M"
                ).time()

            except ValueError:
                time_in = datetime.strptime(
                    time_in,
                    "%H:%M:%S"
                ).time()

            data["time_in"] = time_in

        if isinstance(time_out, str):

            try:
                time_out = datetime.strptime(
                    time_out,
                    "%H:%M"
                ).time()

            except ValueError:
                time_out = datetime.strptime(
                    time_out,
                    "%H:%M:%S"
                ).time()

            data["time_out"] = time_out

        # =====================================
        # ABSENT / ON LEAVE
        # =====================================

        if status in ["absent", "on_leave"]:

            data["time_in"] = None
            data["time_out"] = None
            data["total_hours"] = None

            return data

        # =====================================
        # PRESENT / HALF DAY
        # =====================================

        if status in ["present", "half_day"]:

            if not data.get("time_in"):

                raise serializers.ValidationError({

                    "time_in":
                    "Time In is required for Present/Half Day."

                })

        # =====================================
        # TIME VALIDATION
        # =====================================

        if data.get("time_in") and data.get("time_out"):

            if data["time_out"] <= data["time_in"]:

                raise serializers.ValidationError({

                    "time_out":
                    "Time Out must be greater than Time In."

                })

        return data

# class BulkAttendanceSerializer(serializers.Serializer):
#     date = serializers.DateField()
#     records = serializers.ListField(
#         child=serializers.DictField()
#     )

#     def validate(self, data):

#         date = data["date"]
#         records = data["records"]

#         if not records:
#             raise serializers.ValidationError("Attendance records cannot be empty.")

#         employee_ids = [r.get("employee") for r in records]

#         employees = Employee.objects.filter(
#             id__in=employee_ids,
#             is_active=True
#         )

#         if employees.count() != len(employee_ids):
#             raise serializers.ValidationError(
#                 "One or more employees are invalid or inactive."
#             )

#         return data


from datetime import datetime

class BulkAttendanceSerializer(serializers.Serializer):

    date = serializers.DateField()

    records = serializers.ListField(
        child=serializers.DictField()
    )

    def validate(self, data):

        date = data["date"]
        records = data["records"]

        # =====================================
        # RECORDS EMPTY
        # =====================================

        if not records:

            raise serializers.ValidationError(
                "Attendance records cannot be empty."
            )

        # =====================================
        # EMPLOYEE IDS
        # =====================================

        employee_ids = [
            record.get("employee")
            for record in records
        ]

        # =====================================
        # DUPLICATE EMPLOYEE IN REQUEST
        # =====================================

        if len(employee_ids) != len(set(employee_ids)):

            raise serializers.ValidationError(
                "Duplicate employees found in attendance records."
            )

        # =====================================
        # VALID EMPLOYEES
        # =====================================

        employees = Employee.objects.filter(
            id__in=employee_ids,
            is_active=True
        )

        if employees.count() != len(employee_ids):

            raise serializers.ValidationError(
                "One or more employees are invalid or inactive."
            )

        # =====================================
        # ATTENDANCE ALREADY EXISTS
        # =====================================

        existing = Attendance.objects.filter(
            employee_id__in=employee_ids,
            date=date,
            is_active=True
        ).values_list(
            "employee_id",
            flat=True
        )

        if existing:

            raise serializers.ValidationError(
                f"Attendance already exists for employee(s): {list(existing)}"
            )

        # =====================================
        # VALIDATE EACH RECORD
        # =====================================

        for record in records:

            status = record.get(
                "status",
                "present"
            )

            time_in = record.get("time_in")

            time_out = record.get("time_out")

            # -----------------------------
            # Convert string -> time object
            # -----------------------------

            if isinstance(time_in, str):

                try:

                    time_in = datetime.strptime(
                        time_in,
                        "%H:%M"
                    ).time()

                except ValueError:

                    time_in = datetime.strptime(
                        time_in,
                        "%H:%M:%S"
                    ).time()

                record["time_in"] = time_in

            if isinstance(time_out, str):

                try:

                    time_out = datetime.strptime(
                        time_out,
                        "%H:%M"
                    ).time()

                except ValueError:

                    time_out = datetime.strptime(
                        time_out,
                        "%H:%M:%S"
                    ).time()

                record["time_out"] = time_out

            # -----------------------------
            # Absent / Leave
            # -----------------------------

            if status in ["absent", "on_leave"]:

                record["time_in"] = None
                record["time_out"] = None

                continue

            # -----------------------------
            # Present / Half Day
            # -----------------------------

            if status in ["present", "half_day"]:

                if not record.get("time_in"):

                    raise serializers.ValidationError(
                        {
                            "time_in":
                            f"Time In is required for Employee ID {record.get('employee')}."
                        }
                    )

            # -----------------------------
            # Time Validation
            # -----------------------------

            if record.get("time_in") and record.get("time_out"):

                if record["time_out"] <= record["time_in"]:

                    raise serializers.ValidationError(
                        {
                            "time_out":
                            f"Time Out must be greater than Time In for Employee ID {record.get('employee')}."
                        }
                    )

        return data


class RoleMembersListSerializer(serializers.ModelSerializer):
    staff_users = serializers.SerializerMethodField()
    admitted_students = serializers.SerializerMethodField()

    class Meta:
        model = UserRole
        fields = ["id", "name", "staff_users", "admitted_students"]

    def get_staff_users(self, obj):
        # Fetches staff linked to this role
        staff = StaffUser.objects.filter(role=obj, is_active=True)
        return [{"id": s.id, "username": s.username, "type": "Staff"} for s in staff]

    def get_admitted_students(self, obj):
        # Fetches admissions/students linked to this role
        students = Admission.objects.filter(role=obj, is_active=True)
        return [{"id": stu.id, "name": stu.candidate_name, "code": stu.admission_code, "type": "Student"} for stu in students]


from rest_framework import serializers
from django.db import transaction
from django.contrib.auth.hashers import make_password
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password

User = get_user_model()
from django.db.models.functions import Lower

from .models import StaffUser
from .models import Employee

from .models import UserRole
from admission.models import Admission
from core.models import ClientUser


class StaffUserSerializer(serializers.ModelSerializer):

    confirm_password = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True)

    # ========================================
    # EMPLOYEE DETAILS
    # ========================================

    employee_name = serializers.ReadOnlyField(
        source='employee.name'
    )

    # ========================================
    # STUDENT / ADMISSION DETAILS
    # ========================================

    admission_no = serializers.ReadOnlyField(
        source='admission.admission_code'
    )

    student_name = serializers.ReadOnlyField(
        source='admission.candidate_name'
    )

    # ========================================
    # ROLE
    # ========================================

    role_name = serializers.ReadOnlyField(
        source='role.name'
    )

    class Meta:

        model = StaffUser

        fields = [

            "id",

            # EMPLOYEE
            "employee",
            "employee_name",

            # ADMISSION
            "admission",
            "admission_no",
            "student_name",

            # LOGIN
            "username",
            "raw_password_store",

            "password",
            "confirm_password",

            # ROLE
            "role",
            "role_name",

            # EXPIRY
            "expiry_date",

            # STATUS
            "is_active"
        ]

        read_only_fields = ["is_active"]

    # ========================================
    # RESPONSE FORMAT
    # ========================================

    def to_representation(self, instance):

        data = super().to_representation(instance)

        return data

    # ========================================
    # VALIDATION
    # ========================================

    def validate(self, data):

        employee = (
            data.get("employee")
            or getattr(self.instance, "employee", None)
        )

        admission = (
            data.get("admission")
            or getattr(self.instance, "admission", None)
        )

        username = (
            data.get("username")
            or getattr(self.instance, "username", None)
        )

        password = data.get("password")

        confirm_password = data.get("confirm_password")

        role = data.get("role")

        # ========================================
        # ROLE REQUIRED
        # ========================================

        if not role:

            raise serializers.ValidationError({
                "role": "Role is required."
            })

        # ========================================
        # REQUIRE EMPLOYEE OR ADMISSION
        # ========================================

        if not employee and not admission:

            raise serializers.ValidationError({
                "error":
                    "Either employee or admission is required."
            })

        # ========================================
        # PREVENT BOTH
        # ========================================

        if employee and admission:

            raise serializers.ValidationError({
                "error":
                    "Only one of employee or admission can be provided."
            })

        # ========================================
        # PASSWORD VALIDATION
        # ========================================

        if self.instance is None:

            if not password or not confirm_password:

                raise serializers.ValidationError({
                    "password":
                        "Password and confirm_password are required."
                })

        if password and password != confirm_password:

            raise serializers.ValidationError({
                "confirm_password":
                    "Passwords do not match."
            })

        # ========================================
        # USERNAME UNIQUE IN STAFFUSER
        # ========================================

        qs = StaffUser.objects.annotate(
            username_l=Lower("username")
        ).filter(
            username_l=username.lower()
            #is_active=True
        )

        if self.instance:

            qs = qs.exclude(id=self.instance.id)

        if qs.exists():

            raise serializers.ValidationError({
                "username":
                    "Username already exists."
            })

        # ========================================
        # USERNAME UNIQUE IN DJANGO USER
        # ========================================

        django_user_qs = User.objects.annotate(
            email_l=Lower("email")
        ).filter(
            email_l=username.lower()
        )

        if django_user_qs.exists() and self.instance is None:

            existing_staff = StaffUser.objects.filter(
                username__iexact=username
            ).first()

            if not existing_staff or not existing_staff.is_active:

                pass
            else:
                raise serializers.ValidationError({
                    "username":
                        "This username already exists in authentication system."
                })

        # ========================================
        # EMPLOYEE VALIDATION
        # ========================================

        if employee:

            if not employee.is_active:

                raise serializers.ValidationError({
                    "employee":
                        "Employee is inactive."
                })

            emp_qs = StaffUser.objects.filter(
                employee=employee,
                is_active=True
            )

            if self.instance:

                emp_qs = emp_qs.exclude(id=self.instance.id)

            if emp_qs.exists():

                raise serializers.ValidationError({
                    "employee":
                        "This employee already has a login account."
                })

        # ========================================
        # ADMISSION VALIDATION
        # ========================================

        if admission:

            if not admission.is_active:

                raise serializers.ValidationError({
                    "admission":
                        "Admission is inactive."
                })

            admission_qs = StaffUser.objects.filter(
                admission=admission,
                is_active=True
            )

            if self.instance:

                admission_qs = admission_qs.exclude(id=self.instance.id)

            if admission_qs.exists():

                raise serializers.ValidationError({
                    "admission":
                        "This admission already has a login account."
                })

        return data

    # ========================================
    # CREATE
    # ========================================

    def create(self, validated_data):

        request = self.context["request"]

        client_code = getattr(
            request.user,
            "client_code",
            None
        )

        raw_password = validated_data.pop("password")

        validated_data.pop("confirm_password", None)

        with transaction.atomic():

            # ========================================
            # HASH PASSWORD
            # ========================================

            validated_data["password"] = make_password(
                raw_password
            )

            validated_data["raw_password_store"] = raw_password

            # ========================================
            # CREATE STAFF USER
            # ========================================

            staff_user = super().create(validated_data)

            # ========================================
            # BRANCH / NAME
            # ========================================

            branch = None
            employee_name = None

            if staff_user.employee:

                branch = staff_user.employee.branch

                employee_name = (
                    staff_user.employee.name
                )

            elif staff_user.admission:

                branch = (
                    staff_user.admission.branch
                )

                employee_name = (
                    staff_user.admission.candidate_name
                )

            # ========================================
            # DJANGO USER
            # ========================================

            existing_user = User.objects.filter(
                email=staff_user.username
            ).first()

            if existing_user:

                existing_user.password = make_password(
                    raw_password
                )

                existing_user.is_active = True

                if hasattr(existing_user, "branch"):
                    existing_user.branch = branch

                existing_user.client_code = client_code

                existing_user.save()

                django_user = existing_user

            else:

                django_user = User.objects.create(
                    email=staff_user.username,
                    password=make_password(raw_password),
                    is_active=True,
                    client_code=client_code
                )

                # OPTIONAL
                if hasattr(django_user, "branch"):
                    django_user.branch = branch

                django_user.save()

            # ========================================
            # CLIENT USER
            # ========================================

            existing_client_user = ClientUser.objects.filter(
                client_code=client_code,
                user_id=staff_user.username
            ).first()

            if existing_client_user:

                existing_client_user.password = make_password(
                    raw_password
                )

                existing_client_user.branch = branch

                existing_client_user.employee_name = employee_name

                existing_client_user.role = (
                    staff_user.role.name.lower()
                    if staff_user.role
                    else "user"
                )

                existing_client_user.is_active = True

                existing_client_user.save()

            else:

                ClientUser.objects.create(

                    client_code=client_code,

                    user_id=staff_user.username,

                    password=make_password(raw_password),

                    branch=branch,

                    role=(
                        staff_user.role.name.lower()
                        if staff_user.role
                        else "user"
                    ),

                    is_admin=False,

                    employee_name=employee_name,

                    is_active=True,
                )

        return staff_user

    # ========================================
    # UPDATE
    # ========================================

    def update(self, instance, validated_data):

        request = self.context["request"]

        client_code = getattr(
            request.user,
            "client_code",
            None
        )

        raw_password = validated_data.pop(
            "password",
            None
        )

        validated_data.pop(
            "confirm_password",
            None
        )

        old_username = instance.username

        with transaction.atomic():

            # ========================================
            # UPDATE PASSWORD
            # ========================================

            if raw_password:

                validated_data["password"] = make_password(
                    raw_password
                )

                validated_data["raw_password_store"] = (
                    raw_password
                )

            # ========================================
            # UPDATE STAFF USER
            # ========================================

            staff_user = super().update(
                instance,
                validated_data
            )

            # ========================================
            # BRANCH / NAME
            # ========================================

            branch = None
            employee_name = None

            if staff_user.employee:

                branch = staff_user.employee.branch

                employee_name = (
                    staff_user.employee.name
                )

            elif staff_user.admission:

                branch = (
                    staff_user.admission.branch
                )

                employee_name = (
                    staff_user.admission.candidate_name
                )

            # ========================================
            # UPDATE DJANGO USER
            # ========================================

            try:

                django_user = User.objects.get(
                    email=old_username
                )

            except User.DoesNotExist:

                django_user = None

            if django_user:

                django_user.email = (
                    staff_user.username
                )

                if hasattr(django_user, "branch"):
                    django_user.branch = branch

                django_user.client_code = client_code

                if raw_password:

                    django_user.password = make_password(
                        raw_password
                    )

                django_user.save()

            # ========================================
            # UPDATE CLIENT USER
            # ========================================

            try:

                client_user = ClientUser.objects.get(
                    client_code=client_code,
                    user_id=old_username
                )

                client_user.user_id = (
                    staff_user.username
                )

                if raw_password:

                    client_user.password = make_password(
                        raw_password
                    )

                client_user.employee_name = (
                    employee_name
                )

                client_user.branch = (
                    branch
                )

                client_user.is_active = (
                    staff_user.is_active
                )

                client_user.role = (
                    staff_user.role.name.lower()
                    if staff_user.role
                    else "user"
                )

                client_user.save()

            except ClientUser.DoesNotExist:

                pass

        return staff_user
   
    

class EmployeeByRoleSerializer(serializers.ModelSerializer):
    employee_id = serializers.ReadOnlyField(source='employee.id')
    employee_name = serializers.ReadOnlyField(source='employee.name')
    employee_code = serializers.ReadOnlyField(source='employee.employee_code')
    role_name = serializers.ReadOnlyField(source='role.name')

    class Meta:
        model = StaffUser
        fields = ["id", "employee_id", "employee_name", "employee_code", "role_name"]        

class EmployeeDropdownSerializer(serializers.ModelSerializer):
    designation_name = serializers.ReadOnlyField(source='designation.name')
    department_name = serializers.ReadOnlyField(source='department.name')

    class Meta:
        model = Employee
        fields = ["id", "employee_code", "name", "designation", "designation_name", "department_name"]

