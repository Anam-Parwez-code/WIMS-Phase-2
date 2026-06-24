import uuid
import jwt
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.hashers import check_password, make_password
from datetime import datetime, timedelta
from django.conf import settings
from django.contrib.auth import get_user_model
from users.models import UserSession
from .utils import encrypt_value, decrypt_value
from .models import Client, ClientUser
from core.dbrouter import set_client_db
from django.db import connections

from admission.models import Admission, AdmissionCourseBatch
from staff.models import Employee, StaffUser

User = get_user_model()

class ClientSerializer(serializers.ModelSerializer):
    client_id = serializers.IntegerField(source="id", read_only=True)

    class Meta:
        model = Client
        fields = [
            "client_id",
            "client_name",
            "client_code",
            "database_name",
            "db_user",
            "db_password",
            "db_host",
            "db_port",
            "connection_string",
            "created_by",
            "created_date",
            "updated_by",
            "updated_date",
            "expiry_date",
            "client_logo",
            "email",
            "mobile_no",
            "address",
            "website_link",
            "password",
            "employee_name",
            "role",
            "is_active",
        ]
        extra_kwargs = {
            "password": {"write_only": True},  # don’t return password in API response
        }

    def validate(self, data):
        if "client_code" in data:
            qs = Client.objects.filter(client_code=data["client_code"])
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError({"client_code": "Client Code must be unique."})

        if "database_name" in data:
            qs = Client.objects.filter(database_name=data["database_name"])
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError({"database_name": "Database Name must be unique."})
        return data

    def create(self, validated_data):
        raw_password = validated_data.get("password")
        email = validated_data.get("email")

        # ✅ Encrypt sensitive fields
        if validated_data.get("connection_string"):
            validated_data["connection_string"] = encrypt_value(validated_data["connection_string"])

        # ✅ Hash password before saving in Client table
        if validated_data.get("password"):
            validated_data["password"] = make_password(validated_data["password"])

        # ✅ create client
        client = super().create(validated_data)
        from .tenant_db import create_tenant_database, migrate_tenant_database
        create_tenant_database(client.database_name)
        migrate_tenant_database(client.database_name)
        

        # ✅ auto-create client admin user in ClientUser
        if raw_password and email:
	        # 🔥 SWITCH TO TENANT DB FIRST
            db_key = f"client_{client.client_code}"
            if db_key not in connections.databases:
                connections.databases[db_key] = {
                    'ENGINE': 'django.db.backends.postgresql',
                    'NAME': client.database_name,
                    'USER': client.db_user,
                    'PASSWORD': client.db_password,
                    'HOST': client.db_host,
                    'PORT': client.db_port,
                     }
            set_client_db(db_key)

            client = super().create(validated_data)

            ClientUser.objects.using(db_key).create(
                client_code=client.client_code,
                user_id=email,
                password=make_password(raw_password),  # hashed again for ClientUser
                employee_name=validated_data.get("employee_name", "Admin"),
                is_admin=True,
                is_active=True,
            )
        

        return client

    def update(self, instance, validated_data):
        raw_password = None
        password = validated_data.get('password')
        
        if password:
            # Only hash if it's not already a Django hash
            if not password.startswith(('pbkdf2_sha256$', 'bcrypt$', 'argon2')):
                raw_password = password  # Store raw password before hashing
                validated_data["password"] = make_password(password)
            else:
                # If it is already a hash, don't re-hash it!
                validated_data.pop("password")
            
            # Update the client instance
            updated_client = super().update(instance, validated_data)
            
            # ✅ If password was changed, update the admin ClientUser too
            if raw_password and instance.email:
                try:
                    client_user = ClientUser.objects.get(
                        client=instance, 
                        user_id=instance.email
                    )
                    client_user.password = make_password(raw_password)
                    client_user.save()
                except ClientUser.DoesNotExist:
                    # If admin user doesn't exist, create it
                    ClientUser.objects.create(
                        client=instance,
                        user_id=instance.email,
                        password=make_password(raw_password),
                        employee_name=validated_data.get("employee_name", "Admin"),
                        is_admin=True,
                        is_active=True,
                    )
            
            return updated_client
    
class ClientSelectSerializer(serializers.Serializer):
    client_code = serializers.CharField(max_length=100)

    def validate_client_code(self, value):
        if not value.strip():
            raise serializers.ValidationError("Client Code must not be empty.")
        return value



class ClientLoginSerializer(serializers.Serializer):
    user_id = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)

    def validate(self, data):
        request = self.context.get("request")
        if not request:
            raise serializers.ValidationError("Invalid request context")

        # Extract client_code from token
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth_header.startswith("Bearer "):
            raise serializers.ValidationError("Missing or invalid Authorization header")

        token = auth_header.split(" ")[1]
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            client_code = payload.get("client_code")
        except jwt.ExpiredSignatureError:
            raise serializers.ValidationError("Token has expired")
        except jwt.InvalidTokenError:
            raise serializers.ValidationError("Invalid token")

        if not client_code:
            raise serializers.ValidationError("No client_code found in token")

        # 1. Find client
        try:
            client = Client.objects.get(client_code=client_code, is_active=True)
        except Client.DoesNotExist:
            raise serializers.ValidationError("Invalid or inactive client")
        
        # DEBUG: Print all user_ids for this client
        
        db_key = f"client_{client.client_code}"

        if db_key not in connections.databases:
            connections.databases[db_key] = {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': client.database_name,
                'USER': client.db_user,
                'PASSWORD': client.db_password,
                'HOST': client.db_host,
                'PORT': client.db_port,
            }


        set_client_db(db_key)
        # 2. Find user inside client DB
        try:
            client_user = ClientUser.objects.get(client_code=client.client_code, user_id=data["user_id"])
            
        except ClientUser.DoesNotExist:
            raise serializers.ValidationError("Invalid User ID")

        if not client_user.is_active:
            raise serializers.ValidationError("User is inactive")
            
        if not check_password(data["password"], client_user.password):
            raise serializers.ValidationError("Invalid password")

        # 3. Determine admin status (compare with Client.email/password)
        is_admin = client_user.is_admin
        
        # 🔹 Get role_id from StaffUser
        from staff.models import StaffUser

        try:
            staff_user = StaffUser.objects.using(db_key).get(
                username=client_user.user_id,
                is_active=True
            )
            role_id = staff_user.role_id
        except StaffUser.DoesNotExist:
            role_id = None


        # 4. Generate login token with session_id
        
        session_id = str(uuid.uuid4())
        refresh = RefreshToken()
        refresh["user_id"] = client_user.user_id
        refresh["client_code"] = client.client_code
        refresh["is_admin"] = is_admin
        refresh["role"] = client_user.role   # ✅ ADD THIS
        refresh["role_id"] = role_id   # ✅ ADD THIS
        refresh["session_id"] = session_id
        refresh["organization_id"] = (
            client_user.branch.organization_id
            if client_user.branch
            else None
        )
        refresh["branch_id"] = client_user.branch_id
        #refresh["is_main_branch_admin"] = client_user.is_main_branch_admin
        refresh["is_main_branch_admin"] = (
            client_user.branch.is_main_branch
            if client_user.branch
            else False
        )
        refresh["is_branch_super_admin"] = (
            client_user.is_branch_super_admin
        )
                

        access_token = str(refresh.access_token)

        UserSession.objects.create(
            user=None,  # not a Django user
            client_user_id=client_user.user_id,
            client_code=client.client_code,
            session_id=session_id,
            is_active=True,
        )

        # =========================
        # EXTRA USER DETAILS
        # =========================

        employee_data = None
        admission_data = None
        courses_data = []

        # =========================
        # STAFF USER DETAILS
        # =========================

        try:

            staff_user = StaffUser.objects.using(db_key).select_related(
                "employee",
                "employee__organization",
                "employee__branch",
                "role",
                "admission",
                "admission__organization",
                "admission__branch"
            ).get(
                username=client_user.user_id
            )

            # =====================================
            # EMPLOYEE BASED STAFF USER
            # =====================================
            if staff_user.employee:

                employee = staff_user.employee

                employee_data = {
                    "staff_user_id": staff_user.id,

                    "login_type": "employee",

                    "employee_id": employee.id,
                    "employee_code": employee.employee_code,
                    "employee_name": employee.name,

                    "email": employee.email,
                    "mobile": employee.mobile,

                    "organization_id":
                        employee.organization.id
                        if employee.organization else None,

                    "organization_name":
                        employee.organization.name
                        if employee.organization else None,

                    "branch_id":
                        employee.branch.id
                        if employee.branch else None,

                    "branch_name":
                        employee.branch.name
                        if employee.branch else None,

                    "role_id":
                        staff_user.role.id
                        if staff_user.role else None,

                    "role_name":
                        staff_user.role.name
                        if staff_user.role else None,

                    "expiry_date": staff_user.expiry_date
                }

            # =====================================
            # ADMISSION BASED STUDENT USER
            # =====================================
            elif staff_user.admission:

                admission = staff_user.admission

                ########NEW#########
                from staff.models import StudentLoginHistory

                StudentLoginHistory.objects.using(db_key).create(
                    admission=admission,
                    organization=admission.organization,
                    branch=admission.branch
                )
                ########NEW#########

                admission_data = {
                    "login_type": "student",

                    "admission_id": admission.id,

                    "admission_no": admission.admission_code,

                    "student_name": admission.candidate_name,

                    "email": admission.email,

                    "mobile_no": admission.mobile_no,

                    "organization_id":
                        admission.organization.id
                        if admission.organization else None,

                    "organization_name":
                        admission.organization.name
                        if admission.organization else None,

                    "branch_id":
                        admission.branch.id
                        if admission.branch else None,

                    "branch_name":
                        admission.branch.name
                        if admission.branch else None,
                }

                # =========================
                # COURSE + BATCH DETAILS
                # =========================
                mappings = AdmissionCourseBatch.objects.using(db_key).select_related(
                    "course",
                    "batch"
                ).filter(
                    admission=admission,
                    is_active=True
                )

                for mapping in mappings:

                    courses_data.append({
                        "course_id":
                            mapping.course.id
                            if mapping.course else None,

                        "course_name":
                            mapping.course.course_name
                            if mapping.course else None,

                        "batch_id":
                            mapping.batch.id
                            if mapping.batch else None,

                        "batch_name":
                            mapping.batch.batch_name
                            if mapping.batch else None,
                    })

        except StaffUser.DoesNotExist:
            pass



        return {
            "success": True,
            "message": "Login successful",
            "access": access_token,
            "refresh": str(refresh),
            "session_id": session_id,
            "client": {
                "id": client.id,
                "name": client.client_name,
                "code": client.client_code,
                "database_name": client.database_name,
                "logo": client.client_logo,
                "expiry_date": client.expiry_date,
                "email": client.email,
            },
            # "user": {
            #     "user_id": client_user.user_id,
            #     "is_admin": is_admin,
            #     "role": client_user.role,   # ✅ ADD THIS
            #     #"role_name": dict(ClientUser.ROLE_CHOICES).get(client_user.role)
            # }

            "user": {
                "user_id": client_user.user_id,

                "employee_name": client_user.employee_name,

                "is_admin": is_admin,

                "role": client_user.role,

                "branch_id": client_user.branch_id,

                "branch_name":
                    client_user.branch.name
                    if client_user.branch else None,

                # =====================================
                # ORGANIZATION
                # =====================================

                "organization_id":
                    client_user.branch.organization.id
                    if (
                        client_user.branch
                        and client_user.branch.organization
                    ) else None,

                "organization_name":
                    client_user.branch.organization.name
                    if (
                        client_user.branch
                        and client_user.branch.organization
                    ) else None,

                "is_branch_super_admin":
                    client_user.is_branch_super_admin,

                "is_main_branch_admin": (
                    client_user.branch.is_main_branch
                    if client_user.branch
                    else False
                ),

                "employee_details": employee_data,

                "admission_details": admission_data,

                "courses": courses_data
            }
        }
